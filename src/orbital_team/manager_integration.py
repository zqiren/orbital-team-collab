from __future__ import annotations

import copy
import hashlib
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

from .constants import SCHEMA_VERSION
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
    atomic_write_json,
    canonical_json,
    read_json,
    secure_directory,
)


SLOT_STATES = ("queued", "running", "retryable")
OPEN_QUESTION_STATES = ("open", "deferred")
DEFAULT_MAX_ATTEMPTS = 3
DIFF_SUMMARY_LIMIT = 4000
MEMORY_PATHS = (
    "orbital/PROJECT_STATE.md",
    "orbital/DECISIONS.md",
    "orbital/LESSONS.md",
    "orbital/INDEX.md",
)
MERGE_IDENTITY = (
    "-c",
    "user.name=Orbital Team Manager",
    "-c",
    "user.email=manager@orbital-team.invalid",
)
INTEGRATION_OUTCOMES = ("merged", "changes_requested", "blocked", "retryable")
REPORT_ID_PATTERN = re.compile(r"^([a-z][a-z0-9-]{1,31})-T-[0-9]{4,}-R-[0-9]{4,}$")


def job_id_for_report(project_slug: str, report_id: str) -> str:
    digest = hashlib.sha256(report_id.encode("utf-8")).hexdigest()[:12]
    return f"{project_slug}-J-{digest}"


class JobStore:
    """Canonical Integration Job files under <runtime>/jobs; mutate under the project lock."""

    def __init__(self, runtime_root: Path) -> None:
        self.root = runtime_root / "jobs"
        secure_directory(self.root)

    def _path(self, job_id: str) -> Path:
        if not job_id or Path(job_id).name != job_id:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Job ID must not contain a path.",
                {"job_id": job_id},
            )
        return self.root / f"{job_id}.json"

    def exists(self, job_id: str) -> bool:
        return self._path(job_id).is_file()

    def read(self, job_id: str) -> dict[str, Any]:
        path = self._path(job_id)
        if not path.is_file():
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND",
                "Integration Job was not found.",
                {"job_id": job_id},
            )
        value = read_json(path)
        validate("integrationJob", value)
        if value["id"] != job_id:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Integration Job file does not match its own ID.",
                {"job_id": job_id},
            )
        return value

    def list(self, project_slug: str | None = None) -> list[dict[str, Any]]:
        jobs = []
        for path in sorted(self.root.glob("*.json")):
            job = self.read(path.stem)
            if project_slug is None or job["project_slug"] == project_slug:
                jobs.append(job)
        return jobs

    def write_locked(self, value: dict[str, Any]) -> dict[str, Any]:
        validate("integrationJob", value)
        atomic_write_json(self._path(value["id"]), value)
        return value


class ManagerIntegrationWorkflow:
    """Manager-side Integration Job domain commands backed only by the file runtime."""

    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.manager = RuntimeManager(workspace)
        self.paths = self.manager.paths
        self.runtime_root = self.paths.runtime_root
        self.events = EventLog(self.runtime_root)
        self.jobs = JobStore(self.runtime_root)

    # ------------------------------------------------------------------
    # shared helpers
    # ------------------------------------------------------------------

    def _store(self, slug: str, filename: str, schema_name: str) -> ProjectStore:
        return ProjectStore(self.runtime_root, slug, filename, schema_name)

    def _reports(self, slug: str) -> ImmutableProjectObjectStore:
        return ImmutableProjectObjectStore(
            self.runtime_root, slug, "reports", "report"
        )

    def _project_lock(self, slug: str) -> Path:
        return self.paths.locks / f"project-{slug}.lock"

    def _git_lock(self, slug: str) -> Path:
        return self.paths.locks / f"git-{slug}.lock"

    def manager_lock(self, slug: str) -> Path:
        """Return the process-ownership lock used by one live Manager run.

        This lock is deliberately separate from the short-lived project data
        lock: teamd holds it while an external runner is alive so another
        daemon can distinguish active work from a crash-released Running job.
        """
        return self.paths.locks / f"manager-{slug}.lock"

    def _guard(self, slug: str) -> IdempotencyGuard:
        return IdempotencyGuard(
            self.runtime_root / "projects" / slug / "operations",
            self._project_lock(slug),
        )

    def _project(self, slug: str) -> dict[str, Any]:
        registry = self.manager._registry()
        if slug not in registry["projects"]:
            raise TeamRuntimeError(
                "E_PROJECT_NOT_FOUND", "Project was not found.", {"project": slug}
            )
        return self._store(slug, "project.json", "project").read()

    def _slug_for_report(self, report_id: str) -> str:
        match = REPORT_ID_PATTERN.fullmatch(report_id)
        if match is None:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND", "Report was not found.", {"report_id": report_id}
            )
        return match.group(1)

    def _report(self, slug: str, report_id: str) -> dict[str, Any]:
        store = self._reports(slug)
        if not (store.root / f"{report_id}.json").is_file():
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND", "Report was not found.", {"report_id": report_id}
            )
        return store.read(report_id)

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

    def _event(self, event_key: str) -> dict[str, Any] | None:
        return next(
            (
                event
                for event in self.events.read().events
                if event["idempotency_key"] == event_key
            ),
            None,
        )

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
        if self._event(event_key) is not None:
            return
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

    @staticmethod
    def _git(
        workspace: Path | str,
        *args: str,
        code: str = "E_COMMIT_MISMATCH",
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
        environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
        try:
            result = subprocess.run(
                ["git", "-C", os.fspath(workspace), *args],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
        except OSError as exc:
            raise TeamRuntimeError(
                code,
                "Git command could not be executed.",
                {"workspace": os.fspath(workspace), "reason": str(exc)},
            ) from exc
        if check and result.returncode != 0:
            raise TeamRuntimeError(
                code,
                "Git command failed.",
                {
                    "args": list(args),
                    "reason": result.stderr.strip(),
                    "workspace": os.fspath(workspace),
                },
            )
        return result

    def _git_out(self, workspace: Path | str, *args: str, code: str = "E_COMMIT_MISMATCH") -> str:
        return self._git(workspace, *args, code=code).stdout.strip()

    def _update_job(self, job: dict[str, Any], **changes: Any) -> dict[str, Any]:
        updated = copy.deepcopy(job)
        updated.update(changes)
        updated["revision"] = job["revision"] + 1
        updated["updated_at"] = utc_now()
        return self.jobs.write_locked(updated)

    def _record_path(self, slug: str, job_id: str) -> Path:
        return (
            self.runtime_root
            / "projects"
            / slug
            / "integrations"
            / f"{job_id}.json"
        )

    def _append_record(self, slug: str, job_id: str, entry: dict[str, Any]) -> None:
        """Append one structured entry to the Job's integration record (caller holds project lock)."""
        path = self._record_path(slug, job_id)
        if path.is_file():
            record = read_json(path)
        else:
            record = {
                "entries": [],
                "job_id": job_id,
                "project_slug": slug,
                "schema_version": SCHEMA_VERSION,
            }
        if entry in record["entries"]:
            return
        record["entries"].append(entry)
        atomic_write_json(path, record)

    def read_record(self, job_id: str) -> dict[str, Any] | None:
        job = self.jobs.read(job_id)
        path = self._record_path(job["project_slug"], job_id)
        return read_json(path) if path.is_file() else None

    def occupying_jobs(self, slug: str) -> list[dict[str, Any]]:
        return [job for job in self.jobs.list(slug) if job["state"] in SLOT_STATES]

    def _tasks_write(
        self,
        store: ProjectStore,
        tasks: dict[str, Any],
        task: dict[str, Any],
        now: str,
        **changes: Any,
    ) -> dict[str, Any]:
        updated = copy.deepcopy(task)
        updated.update(changes)
        updated["revision"] = task["revision"] + 1
        updated["updated_at"] = now
        tasks["items"][task["id"]] = updated
        tasks["revision"] += 1
        store.write_locked(tasks)
        return updated

    # ------------------------------------------------------------------
    # job lifecycle (teamd scheduling transitions, actor system:teamd)
    # ------------------------------------------------------------------

    def pending_reports(self, slug: str) -> list[dict[str, Any]]:
        """Submitted reports whose task is Submitted and that have no Integration Job yet."""
        tasks = self._store(slug, "tasks.json", "taskStore").read()
        pending = []
        for report in self._reports(slug).list():
            task = tasks["items"].get(report["task_id"])
            if task is None or task["state"] != "submitted":
                continue
            if self.jobs.exists(job_id_for_report(slug, report["id"])):
                continue
            pending.append(report)
        pending.sort(key=lambda item: (item["submitted_at"], item["id"]))
        return pending

    def create_job(
        self, report_id: str, *, request_id: str | None = None
    ) -> dict[str, Any]:
        slug = self._slug_for_report(report_id)
        self._project(slug)
        report = self._report(slug, report_id)
        job_id = job_id_for_report(slug, report_id)
        payload = {"job_id": job_id, "report_id": report_id}
        key = self._request_key("integration.create", request_id, payload)
        event_key = f"integration:queued:{job_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            tasks = tasks_store.read()
            task = tasks["items"].get(report["task_id"])
            if task is None:
                raise TeamRuntimeError(
                    "E_TASK_NOT_FOUND",
                    "Report task was not found.",
                    {"task_id": report["task_id"]},
                )
            if self.jobs.exists(job_id):
                job = self.jobs.read(job_id)
                if job["report_id"] != report_id:
                    raise TeamRuntimeError(
                        "E_CORRUPT_RUNTIME",
                        "Job ID collision with a different report.",
                        {"job_id": job_id},
                    )
                if task["state"] == "submitted":
                    self._tasks_write(
                        tasks_store, tasks, task, utc_now(), state="integrating"
                    )
            else:
                if task["state"] != "submitted":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Task must be Submitted before integration can be queued.",
                        {"state": task["state"], "task_id": task["id"]},
                    )
                occupying = self.occupying_jobs(slug)
                if occupying:
                    raise TeamRuntimeError(
                        "E_INTEGRATION_SLOT_BUSY",
                        "Another Integration Job occupies the project slot.",
                        {"jobs": [item["id"] for item in occupying]},
                        retryable=True,
                    )
                now = utc_now()
                job = {
                    "attempt": 0,
                    "block_kind": None,
                    "created_at": now,
                    "id": job_id,
                    "idempotency_key": f"integration:{report_id}",
                    "merge_commit": None,
                    "project_slug": slug,
                    "report_id": report_id,
                    "revision": 0,
                    "run_id": None,
                    "state": "queued",
                    "task_id": task["id"],
                    "updated_at": now,
                }
                self.jobs.write_locked(job)
                self._tasks_write(tasks_store, tasks, task, now, state="integrating")
            self._append_event(
                actor="system:teamd",
                data={
                    "job_id": job_id,
                    "report_id": report_id,
                    "task_id": job["task_id"],
                },
                event_key=event_key,
                event_type="integration.queued",
                slug=slug,
                timestamp=job["created_at"],
            )
        result = {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def start_job(self, job_id: str, run_id: str) -> dict[str, Any]:
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] == "running" and job["run_id"] == run_id:
                pass
            else:
                if job["state"] != "queued":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Queued job can start running.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                others = [
                    item
                    for item in self.occupying_jobs(slug)
                    if item["id"] != job_id
                ]
                if others:
                    raise TeamRuntimeError(
                        "E_INTEGRATION_SLOT_BUSY",
                        "Another Integration Job occupies the project slot.",
                        {"jobs": [item["id"] for item in others]},
                        retryable=True,
                    )
                job = self._update_job(
                    job,
                    state="running",
                    run_id=run_id,
                    attempt=job["attempt"] + 1,
                )
            self._append_event(
                actor="system:teamd",
                data={
                    "attempt": job["attempt"],
                    "job_id": job_id,
                    "run_id": run_id,
                },
                event_key=f"integration:started:{job_id}:{job['attempt']}",
                event_type="integration.started",
                slug=slug,
                timestamp=job["updated_at"],
            )
        return {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}

    def mark_retryable(self, job_id: str, reason: str) -> dict[str, Any]:
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] != "retryable":
                if job["state"] != "running":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Running job can become Retryable.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                job = self._update_job(job, state="retryable")
                self._append_record(
                    slug,
                    job_id,
                    {
                        "attempt": job["attempt"],
                        "reason": reason,
                        "recorded_at": job["updated_at"],
                        "type": "retryable",
                    },
                )
            self._append_event(
                actor="system:teamd",
                data={"attempt": job["attempt"], "job_id": job_id, "reason": reason},
                event_key=f"integration:retryable:{job_id}:{job['attempt']}",
                event_type="integration.retryable",
                slug=slug,
                timestamp=job["updated_at"],
            )
        return {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}

    def requeue_job(self, job_id: str) -> dict[str, Any]:
        """Retry policy transition retryable -> queued (system:teamd)."""
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] == "queued":
                event_key = f"integration:requeued:{job_id}:{job['attempt']}"
            else:
                if job["state"] != "retryable":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Retryable job can be requeued by retry policy.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                job = self._update_job(job, state="queued", run_id=None)
                event_key = f"integration:requeued:{job_id}:{job['attempt']}"
            self._append_event(
                actor="system:teamd",
                data={"attempt": job["attempt"], "job_id": job_id},
                event_key=event_key,
                event_type="integration.requeued",
                slug=slug,
                timestamp=job["updated_at"],
            )
        return {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}

    # ------------------------------------------------------------------
    # manager review outcomes
    # ------------------------------------------------------------------

    def request_changes(
        self,
        job_id: str,
        changes: Sequence[str],
        *,
        reason: str | None = None,
        actor: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        clean_changes = [item.strip() for item in changes if item.strip()]
        if not clean_changes:
            raise TeamRuntimeError(
                "E_USAGE", "At least one structured requested change is required."
            )
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        actor = actor or f"manager:{project['active_manager_id']}"
        payload = {"changes": clean_changes, "job_id": job_id, "reason": reason}
        key = self._request_key("manager.request_changes", request_id, payload)
        event_key = f"integration:changes_requested:{job_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] != "changes_requested":
                if job["state"] not in ("queued", "running"):
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Queued or Running job can request changes.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                job = self._update_job(job, state="changes_requested")
                self._append_record(
                    slug,
                    job_id,
                    {
                        "actor": actor,
                        "changes": clean_changes,
                        "reason": reason,
                        "recorded_at": job["updated_at"],
                        "type": "changes_requested",
                    },
                )
                tasks = tasks_store.read()
                task = tasks["items"][job["task_id"]]
                if task["state"] == "integrating":
                    self._tasks_write(
                        tasks_store,
                        tasks,
                        task,
                        job["updated_at"],
                        state="changes_requested",
                    )
            self._append_event(
                actor=actor,
                data={
                    "changes": clean_changes,
                    "job_id": job_id,
                    "report_id": job["report_id"],
                    "task_id": job["task_id"],
                },
                event_key=event_key,
                event_type="integration.changes_requested",
                slug=slug,
                timestamp=job["updated_at"],
            )
        result = {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def _next_question_id(self, slug: str, questions: dict[str, Any]) -> str:
        sequences = [
            int(question_id.rsplit("-", 1)[1])
            for question_id in questions["items"]
        ]
        return f"{slug}-Q-{max(sequences, default=0) + 1:04d}"

    def block_job(
        self,
        job_id: str,
        reason: str,
        *,
        question: str,
        owner: str | None = None,
        actor: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        clean_reason = reason.strip()
        clean_question = question.strip()
        if not clean_reason or not clean_question:
            raise TeamRuntimeError(
                "E_USAGE", "Blocking a job requires a reason and an Open Question."
            )
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        actor = actor or f"manager:{project['active_manager_id']}"
        owner = owner or f"human:{project['active_manager_id']}"
        payload = {
            "job_id": job_id,
            "owner": owner,
            "question": clean_question,
            "reason": clean_reason,
        }
        key = self._request_key("manager.block", request_id, payload)
        guard, _, replay = self._prepare(slug, key, payload, f"integration:blocked:{job_id}:{key}")
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        questions_store = self._store(slug, "open-questions.json", "openQuestionStore")
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] == "blocked":
                questions = questions_store.read()
                question_value = next(
                    (
                        item
                        for item in questions["items"].values()
                        if job_id in item["related"]["job_ids"]
                        and item["question"] == clean_question
                    ),
                    None,
                )
            else:
                if job["state"] not in SLOT_STATES:
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Queued, Running, or Retryable job can be blocked.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                if job["merge_commit"] is not None:
                    raise TeamRuntimeError(
                        "E_GUARDRAIL_VIOLATION",
                        "A job with a persisted merge commit cannot take an integration block.",
                        {"job_id": job_id},
                    )
                now = utc_now()
                questions = questions_store.read()
                question_id = self._next_question_id(slug, questions)
                question_value = {
                    "answer": None,
                    "blocking": True,
                    "created_at": now,
                    "created_by": actor,
                    "evidence": [],
                    "id": question_id,
                    "owner": owner,
                    "project_slug": slug,
                    "question": clean_question,
                    "related": {
                        "job_ids": [job_id],
                        "potential_task_ids": [],
                        "proposal_ids": [],
                        "task_ids": [job["task_id"]],
                    },
                    "revision": 0,
                    "state": "open",
                }
                validate("openQuestion", question_value)
                questions["items"][question_id] = question_value
                questions["revision"] += 1
                questions_store.write_locked(questions)
                job = self._update_job(job, state="blocked", block_kind="integration")
                self._append_record(
                    slug,
                    job_id,
                    {
                        "actor": actor,
                        "question_id": question_id,
                        "reason": clean_reason,
                        "recorded_at": job["updated_at"],
                        "type": "blocked",
                    },
                )
                tasks = tasks_store.read()
                task = tasks["items"][job["task_id"]]
                if task["state"] == "integrating":
                    self._tasks_write(
                        tasks_store,
                        tasks,
                        task,
                        job["updated_at"],
                        state="blocked",
                        blocked_from="integrating",
                    )
                self._append_event(
                    actor=actor,
                    data={"job_id": job_id, "question_id": question_id},
                    event_key=f"question:created:{question_id}",
                    event_type="question.created",
                    slug=slug,
                    timestamp=now,
                )
            self._append_event(
                actor=actor,
                data={
                    "job_id": job_id,
                    "question_id": question_value["id"] if question_value else None,
                    "reason": clean_reason,
                    "task_id": job["task_id"],
                },
                event_key=f"integration:blocked:{job_id}:r{job['revision']}",
                event_type="integration.blocked",
                slug=slug,
                timestamp=job["updated_at"],
            )
        result = {
            "job": job,
            "ok": True,
            "question": question_value,
            "schema_version": SCHEMA_VERSION,
        }
        guard.commit(key, payload, result)
        return result

    def resume_job(self, job_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        """Human/Manager transition blocked -> queued once the integration block is resolved."""
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        payload = {"job_id": job_id, "resume_revision": job["revision"]}
        key = self._request_key("manager.resume", request_id, payload)
        guard, _, replay = self._prepare(slug, key, payload, f"integration:resume:{job_id}:{key}")
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        questions_store = self._store(slug, "open-questions.json", "openQuestionStore")
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] != "blocked" or job["block_kind"] != "integration":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Only an integration-blocked job can be requeued.",
                    {"block_kind": job["block_kind"], "job_id": job_id, "state": job["state"]},
                )
            if job["merge_commit"] is not None:
                raise TeamRuntimeError(
                    "E_GUARDRAIL_VIOLATION",
                    "A merged job cannot re-enter the integration queue.",
                    {"job_id": job_id},
                )
            questions = questions_store.read()
            unresolved = [
                item["id"]
                for item in questions["items"].values()
                if job_id in item["related"]["job_ids"]
                and item["state"] in OPEN_QUESTION_STATES
            ]
            if unresolved:
                raise TeamRuntimeError(
                    "E_BLOCKING_QUESTION",
                    "Open Questions related to the job are unresolved.",
                    {"job_id": job_id, "questions": sorted(unresolved)},
                )
            occupying = self.occupying_jobs(slug)
            if occupying:
                raise TeamRuntimeError(
                    "E_INTEGRATION_SLOT_BUSY",
                    "Another Integration Job occupies the project slot.",
                    {"jobs": [item["id"] for item in occupying]},
                    retryable=True,
                )
            job = self._update_job(job, state="queued", block_kind=None, run_id=None)
            tasks = tasks_store.read()
            task = tasks["items"][job["task_id"]]
            if task["state"] == "blocked":
                self._tasks_write(
                    tasks_store,
                    tasks,
                    task,
                    job["updated_at"],
                    state="integrating",
                    blocked_from=None,
                )
            self._append_event(
                actor="system:teamd",
                data={"attempt": job["attempt"], "job_id": job_id},
                event_key=f"integration:requeued:{job_id}:r{job['revision']}",
                event_type="integration.requeued",
                slug=slug,
                timestamp=job["updated_at"],
            )
        result = {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    # ------------------------------------------------------------------
    # guarded merge (the only Git mutation path)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_validation(validations: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        records = [dict(item) for item in validations]
        if not records:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Merge requires at least one validation record.",
            )
        for record in records:
            try:
                validate("validation", record)
            except TeamRuntimeError as exc:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED",
                    "Validation record is schema-invalid.",
                    exc.details,
                ) from exc
        failed = [item for item in records if item["outcome"] == "failed"]
        if failed:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Merge is forbidden while validation is failing.",
                {"failed": [item["command"] for item in failed]},
            )
        if not any(item["outcome"] == "passed" for item in records):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Merge requires at least one passed validation record.",
            )
        return records

    def merge_job(
        self,
        job_id: str,
        *,
        expected_head: str,
        validation: Sequence[dict[str, Any]],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        records = self._check_validation(validation)
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        actor = f"manager:{project['active_manager_id']}"
        payload = {
            "expected_head": expected_head,
            "job_id": job_id,
            "validation": records,
        }
        key = self._request_key("manager.merge", request_id, payload)
        event_key = f"integration:merged:{job_id}"
        guard, _, replay = self._prepare(slug, key, payload, event_key)
        if replay is not None:
            return replay
        tasks_store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] in ("merged", "awaiting_knowledge") and job["merge_commit"]:
                merge_commit = job["merge_commit"]
            else:
                if job["state"] != "running":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Running job can merge.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                report = self._report(slug, job["report_id"])
                tasks = tasks_store.read()
                task = tasks["items"].get(job["task_id"])
                if task is None or task["state"] != "integrating":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Task is not Integrating for this job.",
                        {"job_id": job_id, "task_id": job["task_id"]},
                    )
                canonical = Path(project["canonical_workspace"])
                canonical_paths = resolve_runtime_paths(canonical)
                if canonical_paths.git_common_dir != self.paths.git_common_dir:
                    raise TeamRuntimeError(
                        "E_WORKTREE_MISMATCH",
                        "Canonical workspace belongs to another repository.",
                    )
                with RuntimeLock(self._git_lock(slug)):
                    merge_commit = self._guarded_merge(
                        canonical, report, expected_head
                    )
                job = self._update_job(job, state="merged", merge_commit=merge_commit)
                self._append_record(
                    slug,
                    job_id,
                    {
                        "actor": actor,
                        "expected_head": expected_head,
                        "merge_commit": merge_commit,
                        "recorded_at": job["updated_at"],
                        "type": "merged",
                        "validation": records,
                    },
                )
            self._append_event(
                actor=actor,
                data={
                    "job_id": job_id,
                    "merge_commit": merge_commit,
                    "report_id": job["report_id"],
                    "task_id": job["task_id"],
                },
                event_key=event_key,
                event_type="integration.merged",
                slug=slug,
                timestamp=job["updated_at"],
            )
        result = {
            "job": job,
            "merge_commit": merge_commit,
            "ok": True,
            "schema_version": SCHEMA_VERSION,
        }
        guard.commit(key, payload, result)
        return result

    def _guarded_merge(
        self, canonical: Path, report: dict[str, Any], expected_head: str
    ) -> str:
        """Re-validate every binding inside the git lock and perform the only allowed merge."""
        head = self._git_out(canonical, "rev-parse", "HEAD")
        if head != expected_head:
            parents = self._git_out(
                canonical, "rev-list", "--parents", "-n", "1", "HEAD"
            ).split()
            if parents == [head, expected_head, report["commit"]]:
                return head  # crash recovery: the merge commit already exists
            raise TeamRuntimeError(
                "E_COMMIT_MISMATCH",
                "Canonical HEAD moved since the review baseline; re-review is required.",
                {"actual_head": head, "expected_head": expected_head},
                retryable=True,
            )
        branch = self._git_out(
            canonical,
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
            code="E_GUARDRAIL_VIOLATION",
        )
        if not branch:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Canonical workspace must be on a named branch to merge.",
            )
        status = self._git_out(canonical, "status", "--porcelain")
        if status:
            raise TeamRuntimeError(
                "E_DIRTY_WORKSPACE",
                "Canonical workspace has uncommitted changes outside the pipeline.",
                {"entries": status.splitlines()[:20]},
            )
        self._git(
            canonical,
            "rev-parse",
            "--verify",
            f"{report['commit']}^{{commit}}",
        )
        bound_branch = self._git(
            canonical,
            "rev-parse",
            "--verify",
            f"refs/heads/{report['branch']}",
            check=False,
        )
        if bound_branch.returncode != 0:
            raise TeamRuntimeError(
                "E_COMMIT_MISMATCH",
                "Report bound branch no longer exists.",
                {"branch": report["branch"]},
            )
        ancestor = self._git(
            canonical,
            "merge-base",
            "--is-ancestor",
            report["commit"],
            f"refs/heads/{report['branch']}",
            check=False,
        )
        if ancestor.returncode != 0:
            raise TeamRuntimeError(
                "E_COMMIT_MISMATCH",
                "Report commit is not bound to its report branch.",
                {"branch": report["branch"], "commit": report["commit"]},
            )
        message = (
            f"Merge report {report['id']} ({report['branch']}) for {report['task_id']}"
        )
        merge = self._git(
            canonical,
            *MERGE_IDENTITY,
            "merge",
            "--no-ff",
            "--no-edit",
            "-m",
            message,
            report["commit"],
            check=False,
        )
        if merge.returncode != 0:
            self._git(canonical, "merge", "--abort", check=False)
            raise TeamRuntimeError(
                "E_MERGE_CONFLICT",
                "Merge produced conflicts and was aborted.",
                {
                    "commit": report["commit"],
                    "reason": (merge.stdout + merge.stderr).strip()[:2000],
                },
            )
        return self._git_out(canonical, "rev-parse", "HEAD")

    # ------------------------------------------------------------------
    # knowledge pack preparation (mechanical, SPEC-05 consumes it)
    # ------------------------------------------------------------------

    def prepare_knowledge_pack(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        pack_id = f"{job_id}-PACK"
        pack_path = (
            self.runtime_root / "projects" / slug / "knowledge-packs" / f"{pack_id}.json"
        )
        with RuntimeLock(self._project_lock(slug)):
            job = self.jobs.read(job_id)
            if job["state"] == "awaiting_knowledge":
                pack = read_json(pack_path) if pack_path.is_file() else None
            else:
                if job["state"] != "merged":
                    raise TeamRuntimeError(
                        "E_INVALID_TRANSITION",
                        "Only a Merged job can prepare its Knowledge Pack.",
                        {"job_id": job_id, "state": job["state"]},
                    )
                canonical = Path(project["canonical_workspace"])
                hashes = {}
                for relative in MEMORY_PATHS:
                    target = canonical / relative
                    if target.is_file():
                        hashes[relative] = hashlib.sha256(
                            target.read_bytes()
                        ).hexdigest()
                diff_summary = self._git_out(
                    canonical,
                    "show",
                    "--stat",
                    "--format=",
                    job["merge_commit"],
                )[:DIFF_SUMMARY_LIMIT]
                pack = {
                    "current_memory_hashes": hashes,
                    "diff_summary": diff_summary,
                    "id": pack_id,
                    "job_id": job_id,
                    "project_slug": slug,
                    "report_id": job["report_id"],
                    "task_id": job["task_id"],
                }
                validate("knowledgePack", pack)
                atomic_write_json(pack_path, pack)
                job = self._update_job(job, state="awaiting_knowledge")
            self._append_event(
                actor="system:teamd",
                data={"job_id": job_id, "pack_id": pack_id},
                event_key=f"knowledge:prepared:{job_id}",
                event_type="knowledge.prepared",
                slug=slug,
                timestamp=job["updated_at"],
            )
        return {"job": job, "ok": True, "pack": pack, "schema_version": SCHEMA_VERSION}

    # ------------------------------------------------------------------
    # runner result intake (structured results only, never stdout)
    # ------------------------------------------------------------------

    def apply_runner_result(
        self, job_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            validate("managerRunResult", result)
        except TeamRuntimeError as exc:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Runner result is schema-invalid.",
                exc.details,
            ) from exc
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        actor = f"manager:{project['active_manager_id']}"
        if result["job_id"] != job_id or result["run_id"] != job["run_id"]:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Runner result does not belong to the active run.",
                {"job_id": job_id, "result_run_id": result["run_id"], "run_id": job["run_id"]},
            )
        outcome = result["outcome"]
        if outcome not in INTEGRATION_OUTCOMES:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Runner outcome is not valid for the integration phase.",
                {"outcome": outcome},
            )
        with RuntimeLock(self._project_lock(slug)):
            self._append_record(
                slug,
                job_id,
                {"recorded_at": utc_now(), "result": result, "type": "runner_result"},
            )
        if outcome == "merged":
            job = self.jobs.read(job_id)
            if (
                job["state"] not in ("merged", "awaiting_knowledge")
                or job["merge_commit"] != result["merge_commit"]
            ):
                raise TeamRuntimeError(
                    "E_GUARDRAIL_VIOLATION",
                    "Runner claimed a merge that the controlled merge command did not perform.",
                    {
                        "job_id": job_id,
                        "job_merge_commit": job["merge_commit"],
                        "result_merge_commit": result["merge_commit"],
                        "state": job["state"],
                    },
                )
            return {"applied": "merged", "job": job, "ok": True}
        if outcome == "changes_requested":
            changes = result["changes_requested"]
            if not changes:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED",
                    "A changes_requested result must list requested changes.",
                )
            applied = self.request_changes(
                job_id, changes, reason=result["risk_summary"], actor=actor
            )
            return {"applied": "changes_requested", "job": applied["job"], "ok": True}
        if outcome == "blocked":
            risk = result["risk_summary"] or "Manager run reported a blocking risk."
            applied = self.block_job(
                job_id,
                risk,
                question=risk,
                actor=actor,
            )
            return {"applied": "blocked", "job": applied["job"], "ok": True}
        applied = self.mark_retryable(job_id, result["risk_summary"] or "Runner requested a retry.")
        return {"applied": "retryable", "job": applied["job"], "ok": True}

    # ------------------------------------------------------------------
    # read-only projections
    # ------------------------------------------------------------------

    def inbox(self, project: str | None = None) -> dict[str, Any]:
        registry = self.manager._registry()
        slugs = sorted(registry["projects"])
        if project is not None:
            registration = self.manager._resolve_registration(registry, project)
            slugs = [registration["slug"]]
        projects = []
        for slug in slugs:
            jobs = self.jobs.list(slug)
            projects.append(
                {
                    "jobs": jobs,
                    "pending_reports": [
                        {
                            "id": item["id"],
                            "submitted_at": item["submitted_at"],
                            "submitted_by": item["submitted_by"],
                            "task_id": item["task_id"],
                        }
                        for item in self.pending_reports(slug)
                    ],
                    "project_slug": slug,
                    "slot_busy": any(job["state"] in SLOT_STATES for job in jobs),
                }
            )
        return {"ok": True, "projects": projects, "schema_version": SCHEMA_VERSION}

    def review_packet(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.read(job_id)
        slug = job["project_slug"]
        project = self._project(slug)
        report = self._report(slug, job["report_id"])
        tasks = self._store(slug, "tasks.json", "taskStore").read()
        task = tasks["items"].get(job["task_id"])
        canonical = Path(project["canonical_workspace"])
        target_head = self._git_out(canonical, "rev-parse", "HEAD")
        diff_stat = self._git_out(
            canonical,
            "diff",
            "--stat",
            report["base_commit"],
            report["commit"],
            "--",
        )[:DIFF_SUMMARY_LIMIT]
        return {
            "diff_stat": diff_stat,
            "job": job,
            "ok": True,
            "report": report,
            "schema_version": SCHEMA_VERSION,
            "target_head": target_head,
            "task": task,
        }
