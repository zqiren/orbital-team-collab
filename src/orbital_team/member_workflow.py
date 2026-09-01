from __future__ import annotations

import copy
import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .constants import DEFAULT_LOCK_TIMEOUT, SCHEMA_VERSION
from .errors import TeamRuntimeError
from .models import Event, IdempotencyRecord
from .paths import resolve_runtime_paths
from .runtime import RuntimeManager, stable_uuid4, utc_now
from .schema import validate
from .storage import (
    EventLog,
    IdempotencyGuard,
    ImmutableProjectObjectStore,
    ProjectStore,
    RuntimeLock,
    canonical_json,
)


TERMINAL_TASK_STATES = {"done", "cancelled"}
OPEN_BLOCKING_STATES = {"open", "deferred"}
DEFAULT_CONTEXT_BUDGET = 32 * 1024
MAX_CONTEXT_BUDGET = 64 * 1024
MEMORY_PATHS = (
    "orbital/PROJECT_STATE.md",
    "orbital/DECISIONS.md",
    "orbital/LESSONS.md",
    "orbital/INDEX.md",
)


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _clip(value: str, limit: int) -> tuple[str, bool]:
    if len(value) <= limit:
        return value, False
    return value[: max(0, limit - 1)].rstrip() + "…", True


class MemberWorkflow:
    """Shared member-facing domain commands backed only by the file runtime."""

    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.manager = RuntimeManager(workspace)
        self.paths = self.manager.paths
        self.runtime_root = self.paths.runtime_root
        self.events = EventLog(self.runtime_root)

    def _project(self, query: str) -> tuple[str, dict[str, Any]]:
        registry = self.manager._registry()
        registration = self.manager._resolve_registration(registry, query)
        slug = registration["slug"]
        project = ProjectStore(
            self.runtime_root, slug, "project.json", "project"
        ).read()
        return slug, project

    def _project_for_task(self, task_id: str) -> tuple[str, dict[str, Any]]:
        match = re.fullmatch(r"(.+)-T-[0-9]{4,}", task_id)
        if match is None:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND", "Task was not found.", {"task_id": task_id}
            )
        return self._project(match.group(1))

    def _store(self, slug: str, filename: str, schema_name: str) -> ProjectStore:
        return ProjectStore(self.runtime_root, slug, filename, schema_name)

    def _project_lock(self, slug: str) -> Path:
        return self.paths.locks / f"project-{slug}.lock"

    def _guard(self, slug: str) -> IdempotencyGuard:
        return IdempotencyGuard(
            self.runtime_root / "projects" / slug / "operations",
            self._project_lock(slug),
        )

    @staticmethod
    def _request_key(command: str, request_id: str | None, payload: Any) -> str:
        if request_id:
            return f"command:{command}:{request_id}"
        digest = hashlib.sha256(canonical_json(payload)).hexdigest()
        return f"command:{command}:auto:{digest}"

    def _prepare(
        self, slug: str, key: str, payload: Any, event_key: str
    ) -> tuple[IdempotencyGuard, IdempotencyRecord, dict[str, Any] | None]:
        guard = self._guard(slug)
        record = guard.prepare(key, payload, stable_uuid4(event_key))
        if record.state == "Committed":
            if record.result is None:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Committed operation is missing its result.",
                    {"key": key},
                )
            return guard, record, record.result
        return guard, record, None

    def _append_event(
        self,
        *,
        actor: str,
        data: dict[str, Any],
        event_key: str,
        event_type: str,
        slug: str,
        timestamp: str,
    ) -> None:
        self.events.append(
            Event(
                actor=actor,
                data=data,
                id=stable_uuid4(event_key),
                idempotency_key=event_key,
                project_slug=slug,
                schema_version=SCHEMA_VERSION,
                timestamp=timestamp,
                type=event_type,
            )
        )

    def _event(self, event_key: str) -> dict[str, Any] | None:
        return next(
            (
                event
                for event in self.events.read().events
                if event["idempotency_key"] == event_key
            ),
            None,
        )

    @staticmethod
    def _git(workspace: Path, *args: str, code: str = "E_WORKTREE_MISMATCH") -> str:
        environment = os.environ.copy()
        environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
        environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
        try:
            result = subprocess.run(
                ["git", "-C", os.fspath(workspace), *args],
                check=True,
                capture_output=True,
                text=True,
                env=environment,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            reason = (getattr(exc, "stderr", "") or "").strip()
            raise TeamRuntimeError(
                code,
                "Git worktree or commit binding could not be verified.",
                {"reason": reason, "workspace": os.fspath(workspace)},
            ) from exc
        return result.stdout.strip()

    def _current_branch(self) -> str:
        branch = self._git(
            self.paths.repository_root,
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        )
        if not branch:
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH", "Member worktree must be on a named branch."
            )
        return branch

    def _member_for_workspace(self, slug: str) -> dict[str, Any]:
        members = self._store(slug, "members.json", "memberStore").read()
        current = self.paths.repository_root.resolve()
        matches = []
        for member in members["items"].values():
            try:
                member_root = Path(member["worktree"]).resolve()
            except (OSError, TypeError):
                continue
            if member_root == current:
                matches.append(member)
        if not matches:
            raise TeamRuntimeError(
                "E_MEMBER_NOT_FOUND",
                "Current worktree is not joined to the project.",
                {"project_slug": slug, "worktree": os.fspath(current)},
            )
        if len(matches) > 1:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Multiple members are bound to the current worktree.",
                {"project_slug": slug},
            )
        return matches[0]

    def _verify_member_binding(
        self, member: dict[str, Any], task: dict[str, Any] | None = None
    ) -> None:
        if Path(member["worktree"]).resolve() != self.paths.repository_root.resolve():
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH", "Member is bound to a different worktree."
            )
        branch = self._current_branch()
        if branch != member["branch"]:
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH",
                "Current branch does not match the member binding.",
                {"actual_branch": branch, "expected_branch": member["branch"]},
            )
        if task is not None and task.get("branch") != branch:
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH",
                "Current branch does not match the claimed task binding.",
                {"actual_branch": branch, "task_branch": task.get("branch")},
            )

    @staticmethod
    def _resolve_task(store: dict[str, Any], query: str) -> dict[str, Any]:
        tasks = {
            task_id: task
            for task_id, task in store["items"].items()
            if task["state"] not in TERMINAL_TASK_STATES
        }
        direct = tasks.get(query)
        if direct is not None:
            return direct
        normalized_query = _normalized(query)
        if not normalized_query:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Task was not found.")
        exact_titles = [
            task for task in tasks.values() if _normalized(task["title"]) == normalized_query
        ]
        if len(exact_titles) == 1:
            return exact_titles[0]
        matches = exact_titles
        if not matches:
            tokens = normalized_query.split()
            matches = []
            for task in tasks.values():
                searchable = _normalized(
                    " ".join([task["id"], task["title"], *task["labels"]])
                )
                if all(token in searchable for token in tokens):
                    matches.append(task)
        matches.sort(key=lambda item: item["id"])
        if not matches:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND", "Task query did not match any task.", {"query": query}
            )
        if len(matches) > 1:
            raise TeamRuntimeError(
                "E_TASK_AMBIGUOUS",
                "Task query matched multiple tasks.",
                {"candidates": [item["id"] for item in matches], "query": query},
            )
        return matches[0]

    @staticmethod
    def _task(store: dict[str, Any], task_id: str) -> dict[str, Any]:
        task = store["items"].get(task_id)
        if task is None:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND", "Task was not found.", {"task_id": task_id}
            )
        return task

    def _blocking_questions(
        self, slug: str, task: dict[str, Any], question_store: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        questions = question_store or self._store(
            slug, "open-questions.json", "openQuestionStore"
        ).read()
        blocking = []
        indexed = set(task.get("blocking_question_ids", []))
        for question in questions["items"].values():
            related = task["id"] in question["related"]["task_ids"]
            if (
                question["blocking"]
                and question["state"] in OPEN_BLOCKING_STATES
                and (question["id"] in indexed or related)
            ):
                blocking.append(question)
        return sorted(blocking, key=lambda item: item["id"])

    @staticmethod
    def _check_dependencies(task: dict[str, Any], task_store: dict[str, Any]) -> None:
        incomplete = [
            dependency
            for dependency in task["dependencies"]
            if task_store["items"].get(dependency, {}).get("state") != "done"
        ]
        if incomplete:
            raise TeamRuntimeError(
                "E_DEPENDENCY_INCOMPLETE",
                "Task dependencies are not complete.",
                {"dependencies": incomplete, "task_id": task["id"]},
            )

    def join_member(
        self,
        project: str,
        member_id: str,
        agent_type: str,
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        slug, project_value = self._project(project)
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", member_id):
            raise TeamRuntimeError("E_USAGE", "Member ID is invalid.")
        if not agent_type.strip() or len(agent_type) > 64:
            raise TeamRuntimeError("E_USAGE", "Agent type is invalid.")
        canonical_paths = resolve_runtime_paths(project_value["canonical_workspace"])
        if canonical_paths.git_common_dir != self.paths.git_common_dir:
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH", "Worktree belongs to a different Git repository."
            )
        now = utc_now()
        member = {
            "agent_type": agent_type.strip(),
            "branch": self._current_branch(),
            "id": member_id,
            "joined_at": now,
            "role": "member",
            "worktree": os.fspath(self.paths.repository_root),
        }
        payload = {key: value for key, value in member.items() if key != "joined_at"}
        key = self._request_key("member.join", request_id, {"project": slug, **payload})
        event_key = f"member:join:{slug}:{member_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        members_store = self._store(slug, "members.json", "memberStore")
        project_store = self._store(slug, "project.json", "project")
        with RuntimeLock(self._project_lock(slug)):
            members = members_store.read()
            existing = members["items"].get(member_id)
            if existing is not None:
                comparable = {key: value for key, value in existing.items() if key != "joined_at"}
                if comparable != payload:
                    raise TeamRuntimeError(
                        "E_IDEMPOTENCY_CONFLICT",
                        "Member ID is already joined with a different binding.",
                        {"member_id": member_id},
                    )
                member = existing
            else:
                for other in members["items"].values():
                    if Path(other["worktree"]).resolve() == self.paths.repository_root.resolve():
                        raise TeamRuntimeError(
                            "E_IDEMPOTENCY_CONFLICT",
                            "Current worktree is already bound to another member.",
                            {"member_id": other["id"]},
                        )
                members["items"][member_id] = member
                members["revision"] += 1
                members_store.write_locked(members)
                current_project = project_store.read()
                worktree = os.fspath(self.paths.repository_root)
                if worktree not in current_project["allowed_worktree_roots"]:
                    current_project["allowed_worktree_roots"].append(worktree)
                    current_project["allowed_worktree_roots"].sort()
                    current_project["revision"] += 1
                    project_store.write_locked(current_project)
            if self._event(event_key) is None:
                self._append_event(
                    actor=f"human:{project_value['active_manager_id']}",
                    data={"agent_type": member["agent_type"], "member_id": member_id},
                    event_key=event_key,
                    event_type="member.joined",
                    slug=slug,
                    timestamp=member["joined_at"],
                )
        result = {"member": member, "ok": True, "project_slug": slug, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def create_task(
        self,
        project: str,
        title: str,
        *,
        description: str = "",
        acceptance_criteria: Sequence[str] = (),
        paths: Sequence[str] = (),
        labels: Sequence[str] = (),
        dependencies: Sequence[str] = (),
        request_id: str | None = None,
    ) -> dict[str, Any]:
        slug, project_value = self._project(project)
        clean_title = title.strip()
        if not clean_title or len(clean_title) > 200:
            raise TeamRuntimeError("E_USAGE", "Task title must contain 1 to 200 characters.")
        payload = {
            "acceptance_criteria": list(dict.fromkeys(acceptance_criteria)),
            "dependencies": list(dict.fromkeys(dependencies)),
            "description": description,
            "labels": list(dict.fromkeys(labels)),
            "paths": list(dict.fromkeys(paths)),
            "project_slug": slug,
            "title": clean_title,
        }
        key = self._request_key("task.create", request_id, payload)
        event_key = key
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        store = self._store(slug, "tasks.json", "taskStore")
        now = utc_now()
        with RuntimeLock(self._project_lock(slug)):
            tasks = store.read()
            sequences = [int(task_id.rsplit("-", 1)[1]) for task_id in tasks["items"]]
            task_id = f"{slug}-T-{max(sequences, default=0) + 1:04d}"
            task = {
                **payload,
                "assignee": None,
                "blocking_question_ids": [],
                "created_at": now,
                "created_by": f"human:{project_value['active_manager_id']}",
                "id": task_id,
                "revision": 0,
                "state": "draft",
                "updated_at": now,
            }
            try:
                validate("task", task)
            except TeamRuntimeError as exc:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "Task input is invalid.", exc.details
                ) from exc
            tasks["items"][task_id] = task
            tasks["revision"] += 1
            store.write_locked(tasks)
            self._append_event(
                actor=task["created_by"],
                data={"task_id": task_id},
                event_key=event_key,
                event_type="task.created",
                slug=slug,
                timestamp=now,
            )
        result = {"ok": True, "schema_version": SCHEMA_VERSION, "task": task}
        guard.commit(key, payload, result)
        return result

    def edit_task(
        self,
        task_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        acceptance_criteria: Sequence[str] | None = None,
        paths: Sequence[str] | None = None,
        labels: Sequence[str] | None = None,
        dependencies: Sequence[str] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Edit human-owned Draft fields; adapters must not mutate Task JSON."""
        slug, project = self._project_for_task(task_id)
        changes: dict[str, Any] = {}
        if title is not None:
            clean_title = title.strip()
            if not clean_title or len(clean_title) > 200:
                raise TeamRuntimeError(
                    "E_USAGE", "Task title must contain 1 to 200 characters."
                )
            changes["title"] = clean_title
        if description is not None:
            changes["description"] = description
        for field, values in (
            ("acceptance_criteria", acceptance_criteria),
            ("paths", paths),
            ("labels", labels),
            ("dependencies", dependencies),
        ):
            if values is not None:
                changes[field] = list(dict.fromkeys(values))
        if not changes:
            raise TeamRuntimeError("E_USAGE", "At least one Task field is required.")
        payload = {"changes": changes, "task_id": task_id}
        key = self._request_key("task.edit", request_id, payload)
        event_key = key
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            tasks = store.read()
            task = self._task(tasks, task_id)
            if task["state"] != "draft" or task["assignee"] is not None:
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Only an unassigned Draft task can be edited.",
                    {"state": task["state"], "task_id": task_id},
                )
            if task_id in changes.get("dependencies", []):
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "A Task cannot depend on itself."
                )
            now = utc_now()
            updated = copy.deepcopy(task)
            updated.update(changes)
            updated.update(revision=task["revision"] + 1, updated_at=now)
            try:
                validate("task", updated)
            except TeamRuntimeError as exc:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "Task edit is invalid.", exc.details
                ) from exc
            tasks["items"][task_id] = updated
            tasks["revision"] += 1
            store.write_locked(tasks)
            self._append_event(
                actor=f"human:{project['active_manager_id']}",
                data={"fields": sorted(changes), "task_id": task_id},
                event_key=event_key,
                event_type="task.updated",
                slug=slug,
                timestamp=now,
            )
        result = {"ok": True, "schema_version": SCHEMA_VERSION, "task": updated}
        guard.commit(key, payload, result)
        return result

    def ready_task(self, task_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        slug, project = self._project_for_task(task_id)
        payload = {"task_id": task_id}
        key = self._request_key("task.ready", request_id, payload)
        event_key = f"task:ready:{task_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            tasks = tasks_store.read()
            task = self._task(tasks, task_id)
            if task["state"] == "ready":
                updated = task
                now = task["updated_at"]
            else:
                if task["state"] != "draft":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Draft task can become Ready.",
                        {"state": task["state"], "task_id": task_id},
                    )
                self._check_dependencies(task, tasks)
                blocking = self._blocking_questions(slug, task)
                if blocking:
                    raise TeamRuntimeError(
                        "E_BLOCKING_QUESTION",
                        "Blocking Open Questions prevent the task from becoming Ready.",
                        {"questions": [item["id"] for item in blocking], "task_id": task_id},
                    )
                now = utc_now()
                updated = copy.deepcopy(task)
                updated.update(state="ready", revision=task["revision"] + 1, updated_at=now)
                tasks["items"][task_id] = updated
                tasks["revision"] += 1
                tasks_store.write_locked(tasks)
            if self._event(event_key) is None:
                self._append_event(
                    actor=f"human:{project['active_manager_id']}",
                    data={"task_id": task_id},
                    event_key=event_key,
                    event_type="task.ready",
                    slug=slug,
                    timestamp=now,
                )
        result = {"ok": True, "schema_version": SCHEMA_VERSION, "task": updated}
        guard.commit(key, payload, result)
        return result

    def claim(
        self,
        project: str,
        query: str,
        *,
        request_id: str | None = None,
        context_budget: int = DEFAULT_CONTEXT_BUDGET,
    ) -> dict[str, Any]:
        slug, _ = self._project(project)
        member = self._member_for_workspace(slug)
        initial_tasks = self._store(slug, "tasks.json", "taskStore").read()
        initial_task = self._resolve_task(initial_tasks, query)
        payload = {"member_id": member["id"], "project_slug": slug, "query": query}
        key = self._request_key("task.claim", request_id, payload)
        event_key = f"task:claim:{initial_task['id']}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        questions_store = self._store(slug, "open-questions.json", "openQuestionStore")
        with RuntimeLock(self._project_lock(slug), timeout=DEFAULT_LOCK_TIMEOUT):
            tasks = tasks_store.read()
            task = self._resolve_task(tasks, query)
            if task["id"] != initial_task["id"]:
                raise TeamRuntimeError(
                    "E_IDEMPOTENCY_CONFLICT", "Task resolution changed while claiming."
                )
            prior_event = self._event(event_key)
            recovering = (
                task["state"] == "claimed"
                and task["assignee"] == member["id"]
                and (
                    prior_event is None
                    or prior_event["data"].get("operation_key") == key
                )
            )
            if recovering:
                claimed = task
                now = task["updated_at"]
            else:
                if task["state"] != "ready" or task["assignee"] is not None:
                    code = (
                        "E_TASK_ALREADY_CLAIMED"
                        if task["assignee"] is not None
                        else "E_TASK_NOT_READY"
                    )
                    raise TeamRuntimeError(
                        code,
                        "Task is already claimed."
                        if task["assignee"] is not None
                        else "Task is not Ready.",
                        {
                            "assignee": task["assignee"],
                            "state": task["state"],
                            "task_id": task["id"],
                        },
                    )
                self._check_dependencies(task, tasks)
                questions = questions_store.read()
                blocking = self._blocking_questions(slug, task, questions)
                if blocking:
                    raise TeamRuntimeError(
                        "E_BLOCKING_QUESTION",
                        "Blocking Open Questions prevent task claim.",
                        {
                            "questions": [
                                {
                                    "id": item["id"],
                                    "question": item["question"],
                                    "state": item["state"],
                                }
                                for item in blocking
                            ],
                            "task_id": task["id"],
                        },
                    )
                now = utc_now()
                claimed = copy.deepcopy(task)
                claimed.update(
                    assignee=member["id"],
                    branch=member["branch"],
                    revision=task["revision"] + 1,
                    state="claimed",
                    updated_at=now,
                )
                tasks["items"][task["id"]] = claimed
                tasks["revision"] += 1
                tasks_store.write_locked(tasks)
            if prior_event is None:
                self._append_event(
                    actor=f"member:{member['id']}",
                    data={
                        "branch": member["branch"],
                        "operation_key": key,
                        "task_id": task["id"],
                    },
                    event_key=event_key,
                    event_type="task.claimed",
                    slug=slug,
                    timestamp=now,
                )
        context = self.build_context_pack(slug, claimed, member, max_bytes=context_budget)
        result = {
            "context": context,
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "task": claimed,
        }
        guard.commit(key, payload, result)
        return result

    def start_task(self, task_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        slug, _ = self._project_for_task(task_id)
        member = self._member_for_workspace(slug)
        payload = {"member_id": member["id"], "task_id": task_id}
        key = self._request_key("task.start", request_id, payload)
        event_key = f"task:start:{task_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            tasks = store.read()
            task = self._task(tasks, task_id)
            if task["assignee"] != member["id"]:
                raise TeamRuntimeError(
                    "E_FORBIDDEN_ACTOR", "Only the current assignee can start the task."
                )
            self._verify_member_binding(member, task)
            if task["state"] == "in_progress":
                updated = task
                now = task["updated_at"]
            else:
                if task["state"] != "claimed":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Task must be Claimed before it can start.",
                        {"state": task["state"], "task_id": task_id},
                    )
                now = utc_now()
                updated = copy.deepcopy(task)
                updated.update(state="in_progress", revision=task["revision"] + 1, updated_at=now)
                tasks["items"][task_id] = updated
                tasks["revision"] += 1
                store.write_locked(tasks)
            if self._event(event_key) is None:
                self._append_event(
                    actor=f"member:{member['id']}",
                    data={"task_id": task_id},
                    event_key=event_key,
                    event_type="task.started",
                    slug=slug,
                    timestamp=now,
                )
        result = {"ok": True, "schema_version": SCHEMA_VERSION, "task": updated}
        guard.commit(key, payload, result)
        return result

    def block_task(
        self, task_id: str, reason: str, *, request_id: str | None = None
    ) -> dict[str, Any]:
        clean_reason = reason.strip()
        if not clean_reason:
            raise TeamRuntimeError("E_USAGE", "Block reason must not be empty.")
        slug, _ = self._project_for_task(task_id)
        member = self._member_for_workspace(slug)
        payload = {"member_id": member["id"], "reason": clean_reason, "task_id": task_id}
        key = self._request_key("task.block", request_id, payload)
        guard, _, replay = self._prepare(slug, key, payload, key)
        if replay is not None:
            return replay
        store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            tasks = store.read()
            task = self._task(tasks, task_id)
            if task["assignee"] != member["id"]:
                raise TeamRuntimeError(
                    "E_FORBIDDEN_ACTOR", "Only the current assignee can block the task."
                )
            self._verify_member_binding(member, task)
            if task["state"] != "in_progress":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Only an In Progress task can be blocked by a member.",
                    {"state": task["state"], "task_id": task_id},
                )
            now = utc_now()
            updated = copy.deepcopy(task)
            updated.update(
                blocked_from="in_progress",
                revision=task["revision"] + 1,
                state="blocked",
                updated_at=now,
            )
            tasks["items"][task_id] = updated
            tasks["revision"] += 1
            store.write_locked(tasks)
            self._append_event(
                actor=f"member:{member['id']}",
                data={"reason": clean_reason, "task_id": task_id},
                event_key=key,
                event_type="task.blocked",
                slug=slug,
                timestamp=now,
            )
        result = {"ok": True, "reason": clean_reason, "schema_version": SCHEMA_VERSION, "task": updated}
        guard.commit(key, payload, result)
        return result

    def _git_metadata(
        self,
        project: dict[str, Any],
        member: dict[str, Any],
        task: dict[str, Any],
        expected_commit: str | None,
    ) -> dict[str, Any]:
        self._verify_member_binding(member, task)
        workspace = self.paths.repository_root
        commit = self._git(workspace, "rev-parse", "HEAD", code="E_COMMIT_MISMATCH")
        if expected_commit is not None:
            verified = self._git(
                workspace,
                "rev-parse",
                "--verify",
                f"{expected_commit}^{{commit}}",
                code="E_COMMIT_MISMATCH",
            )
            if verified != commit:
                raise TeamRuntimeError(
                    "E_COMMIT_MISMATCH",
                    "Report commit must be the current branch HEAD.",
                    {"actual_commit": commit, "expected_commit": verified},
                )
        canonical = Path(project["canonical_workspace"])
        canonical_paths = resolve_runtime_paths(canonical)
        if canonical_paths.git_common_dir != self.paths.git_common_dir:
            raise TeamRuntimeError(
                "E_WORKTREE_MISMATCH", "Canonical workspace belongs to another repository."
            )
        canonical_head = self._git(canonical, "rev-parse", "HEAD", code="E_COMMIT_MISMATCH")
        base_commit = self._git(
            workspace, "merge-base", canonical_head, commit, code="E_COMMIT_MISMATCH"
        )
        changed_output = self._git(
            workspace,
            "diff",
            "--name-only",
            base_commit,
            commit,
            "--",
            code="E_COMMIT_MISMATCH",
        )
        changed_files = sorted({line for line in changed_output.splitlines() if line})
        diff_summary = self._git(
            workspace,
            "diff",
            "--stat",
            base_commit,
            commit,
            "--",
            code="E_COMMIT_MISMATCH",
        )
        if not diff_summary:
            diff_summary = "No file changes between base and report commit."
        return {
            "base_commit": base_commit,
            "branch": member["branch"],
            "changed_files": changed_files,
            "commit": commit,
            "diff_summary": diff_summary,
        }

    def submit_report(
        self,
        task_id: str,
        *,
        summary: str | None = None,
        validation: Sequence[dict[str, str]] = (),
        knowledge_candidates: Sequence[str] = (),
        risks: Sequence[str] = (),
        commit: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        slug, project = self._project_for_task(task_id)
        member = self._member_for_workspace(slug)
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        observed_task = self._task(tasks_store.read(), task_id)
        if observed_task["assignee"] != member["id"]:
            raise TeamRuntimeError(
                "E_FORBIDDEN_ACTOR", "Only the current assignee can submit a report."
            )
        metadata = self._git_metadata(project, member, observed_task, commit)
        validations = list(validation) or [
            {
                "command": "not provided",
                "outcome": "skipped",
                "summary": "No validation evidence was provided.",
            }
        ]
        clean_summary = (summary or self._git(
            self.paths.repository_root,
            "show",
            "-s",
            "--format=%s",
            metadata["commit"],
            code="E_COMMIT_MISMATCH",
        )).strip()
        if not clean_summary:
            raise TeamRuntimeError("E_VALIDATION_FAILED", "Report summary must not be empty.")
        payload = {
            "commit": metadata["commit"],
            "knowledge_candidates": list(dict.fromkeys(knowledge_candidates)),
            "member_id": member["id"],
            "risks": list(dict.fromkeys(risks)),
            "summary": clean_summary,
            "task_id": task_id,
            "validation": validations,
        }
        key = self._request_key("report.submit", request_id, payload)
        event_key = f"report:{task_id}:{metadata['commit']}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        reports = ImmutableProjectObjectStore(self.runtime_root, slug, "reports", "report")
        with RuntimeLock(self._project_lock(slug)):
            tasks = tasks_store.read()
            task = self._task(tasks, task_id)
            if task["assignee"] != member["id"]:
                raise TeamRuntimeError(
                    "E_FORBIDDEN_ACTOR", "Only the current assignee can submit a report."
                )
            existing = next(
                (
                    item
                    for item in reports.list()
                    if item["task_id"] == task_id and item["commit"] == metadata["commit"]
                ),
                None,
            )
            if existing is not None:
                if existing["submitted_by"] != f"member:{member['id']}":
                    raise TeamRuntimeError(
                        "E_FORBIDDEN_ACTOR", "Existing report belongs to another actor."
                    )
                report = existing
                if task["state"] == "in_progress":
                    task = copy.deepcopy(task)
                    task.update(state="submitted", revision=task["revision"] + 1, updated_at=report["submitted_at"])
                    tasks["items"][task_id] = task
                    tasks["revision"] += 1
                    tasks_store.write_locked(tasks)
            else:
                if task["state"] != "in_progress":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Task must be In Progress before report submission.",
                        {"state": task["state"], "task_id": task_id},
                    )
                report_numbers = [
                    int(item["id"].rsplit("-", 1)[1])
                    for item in reports.list()
                    if item["task_id"] == task_id
                ]
                report_id = f"{task_id}-R-{max(report_numbers, default=0) + 1:04d}"
                now = utc_now()
                report = {
                    **metadata,
                    "id": report_id,
                    "knowledge_candidates": payload["knowledge_candidates"],
                    "project_slug": slug,
                    "risks": payload["risks"],
                    "submitted_at": now,
                    "submitted_by": f"member:{member['id']}",
                    "summary": clean_summary,
                    "task_id": task_id,
                    "validation": validations,
                }
                try:
                    validate("report", report)
                except TeamRuntimeError as exc:
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED", "Report input is schema-invalid.", exc.details
                    ) from exc
                reports.create_locked(report)
                task = copy.deepcopy(task)
                task.update(state="submitted", revision=task["revision"] + 1, updated_at=now)
                tasks["items"][task_id] = task
                tasks["revision"] += 1
                tasks_store.write_locked(tasks)
            if self._event(event_key) is None:
                self._append_event(
                    actor=f"member:{member['id']}",
                    data={
                        "commit": report["commit"],
                        "report_id": report["id"],
                        "task_id": task_id,
                    },
                    event_key=event_key,
                    event_type="report.submitted",
                    slug=slug,
                    timestamp=report["submitted_at"],
                )
        result = {
            "ok": True,
            "report": report,
            "schema_version": SCHEMA_VERSION,
            "task": task,
        }
        guard.commit(key, payload, result)
        return result

    def task_status(self, task_id: str | None = None) -> dict[str, Any]:
        if task_id is not None:
            slug, _ = self._project_for_task(task_id)
            task = self._task(self._store(slug, "tasks.json", "taskStore").read(), task_id)
            questions = self._blocking_questions(slug, task)
            reports = ImmutableProjectObjectStore(
                self.runtime_root, slug, "reports", "report"
            ).list()
            return {
                "blocking_questions": questions,
                "ok": True,
                "reports": [item["id"] for item in reports if item["task_id"] == task_id],
                "schema_version": SCHEMA_VERSION,
                "task": task,
            }
        registry = self.manager._registry()
        assigned: list[dict[str, Any]] = []
        for slug in sorted(registry["projects"]):
            try:
                member = self._member_for_workspace(slug)
            except TeamRuntimeError as exc:
                if exc.code == "E_MEMBER_NOT_FOUND":
                    continue
                raise
            tasks = self._store(slug, "tasks.json", "taskStore").read()
            assigned.extend(
                task for task in tasks["items"].values() if task["assignee"] == member["id"]
            )
        return {
            "ok": True,
            "schema_version": SCHEMA_VERSION,
            "tasks": sorted(assigned, key=lambda item: item["id"]),
        }

    def list_questions(self, project: str) -> dict[str, Any]:
        slug, _ = self._project(project)
        store = self._store(slug, "open-questions.json", "openQuestionStore").read()
        return {
            "ok": True,
            "project_slug": slug,
            "questions": sorted(store["items"].values(), key=lambda item: item["id"]),
            "schema_version": SCHEMA_VERSION,
        }

    def workspace_bindings(self) -> list[dict[str, Any]]:
        """Return read-only project/member context derived from this worktree."""
        bindings: list[dict[str, Any]] = []
        registry = self.manager._registry()
        for slug in sorted(registry["projects"]):
            try:
                member = self._member_for_workspace(slug)
            except TeamRuntimeError as exc:
                if exc.code == "E_MEMBER_NOT_FOUND":
                    continue
                raise
            self._verify_member_binding(member)
            project = self._store(slug, "project.json", "project").read()
            tasks = self._store(slug, "tasks.json", "taskStore").read()
            questions = self._store(
                slug, "open-questions.json", "openQuestionStore"
            ).read()
            assigned = [
                task
                for task in tasks["items"].values()
                if task["assignee"] == member["id"]
                and task["state"] not in TERMINAL_TASK_STATES
            ]
            pending_questions = [
                question
                for question in questions["items"].values()
                if question["state"] in OPEN_BLOCKING_STATES
            ]
            bindings.append(
                {
                    "member": copy.deepcopy(member),
                    "project": {
                        "display_name": project["display_name"],
                        "slug": slug,
                    },
                    "questions": sorted(
                        pending_questions, key=lambda item: item["id"]
                    ),
                    "tasks": sorted(assigned, key=lambda item: item["id"]),
                }
            )
        return bindings

    def build_context_pack(
        self,
        slug: str,
        task: dict[str, Any],
        member: dict[str, Any],
        *,
        max_bytes: int = DEFAULT_CONTEXT_BUDGET,
    ) -> dict[str, Any]:
        if max_bytes < 1024 or max_bytes > MAX_CONTEXT_BUDGET:
            raise TeamRuntimeError(
                "E_USAGE",
                "Context budget must be between 1024 and 65536 bytes.",
                {"max_bytes": max_bytes},
            )
        project = self._store(slug, "project.json", "project").read()
        tasks = self._store(slug, "tasks.json", "taskStore").read()
        questions = self._store(slug, "open-questions.json", "openQuestionStore").read()
        related_questions = [
            question
            for question in questions["items"].values()
            if task["id"] in question["related"]["task_ids"]
            or question["id"] in task["blocking_question_ids"]
        ]
        dependency_context = [
            {
                "id": dependency,
                "state": tasks["items"].get(dependency, {}).get("state", "missing"),
                "title": tasks["items"].get(dependency, {}).get("title"),
            }
            for dependency in task["dependencies"][:20]
        ]
        clipped = False
        description, was_clipped = _clip(task["description"], 4096)
        clipped |= was_clipped
        compact_task = copy.deepcopy(task)
        compact_task["description"] = description
        for field in ("acceptance_criteria", "labels", "paths"):
            values = compact_task[field]
            compact_task[field] = values[:20]
            clipped |= len(values) > 20
        pack: dict[str, Any] = {
            "budget_bytes": max_bytes,
            "dependencies": dependency_context,
            "member": member,
            "memory_pointers": [],
            "omitted_count": 0,
            "omitted_paths": [],
            "open_questions": [],
            "project": {"display_name": project["display_name"], "slug": slug},
            "report_requirements": {
                "git_metadata": ["base_commit", "branch", "changed_files", "commit", "diff_summary"],
                "required_state": "in_progress",
                "schema": "#/$defs/report",
                "validation_evidence": True,
            },
            "schema_version": SCHEMA_VERSION,
            "serialized_bytes": 0,
            "task": compact_task,
            "truncated": clipped,
        }
        for question in sorted(related_questions, key=lambda item: item["id"])[:10]:
            question_text, was_clipped = _clip(question["question"], 500)
            pack["truncated"] |= was_clipped
            pack["open_questions"].append(
                {
                    "blocking": question["blocking"],
                    "id": question["id"],
                    "owner": question["owner"],
                    "question": question_text,
                    "state": question["state"],
                }
            )
        if len(related_questions) > 10:
            pack["truncated"] = True
            pack["omitted_count"] += len(related_questions) - 10
        canonical = Path(project["canonical_workspace"])
        for relative in MEMORY_PATHS:
            target = canonical / relative
            try:
                content = target.read_text(encoding="utf-8")
                summary, was_clipped = _clip(content.strip(), 2048)
            except OSError:
                summary, was_clipped = "", False
            pointer = {"path": relative, "summary": summary}
            trial = copy.deepcopy(pack)
            trial["memory_pointers"].append(pointer)
            if len(canonical_json(trial)) <= max_bytes - 256:
                pack["memory_pointers"].append(pointer)
                pack["truncated"] |= was_clipped
            else:
                pack["omitted_paths"].append(relative)
                pack["omitted_count"] += 1
                pack["truncated"] = True
        for _ in range(4):
            size = len(canonical_json(pack))
            pack["serialized_bytes"] = size
        if len(canonical_json(pack)) > max_bytes:
            for pointer in pack["memory_pointers"]:
                if pointer["summary"]:
                    pointer["summary"] = ""
                    pack["truncated"] = True
            pack["task"]["description"], _ = _clip(pack["task"]["description"], 500)
            pack["open_questions"] = pack["open_questions"][:3]
            pack["dependencies"] = pack["dependencies"][:5]
            for _ in range(4):
                pack["serialized_bytes"] = len(canonical_json(pack))
        if len(canonical_json(pack)) > max_bytes:
            raise TeamRuntimeError(
                "E_INTERNAL", "Context Pack could not fit within its configured budget."
            )
        return pack
