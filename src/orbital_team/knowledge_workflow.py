from __future__ import annotations

import copy
import hashlib
import os
import re
import stat
from pathlib import Path
from typing import Any, Sequence

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .manager_integration import MEMORY_PATHS, ManagerIntegrationWorkflow
from .runtime import utc_now
from .schema import validate
from .storage import (
    ImmutableProjectObjectStore,
    MutableProjectObjectStore,
    RuntimeLock,
    atomic_write_text,
    canonical_json,
)


PROPOSAL_PATTERN = re.compile(
    r"^([a-z][a-z0-9-]{1,31})-J-[a-f0-9]{12}-KP-[0-9]{4,}$"
)
MEMORY_HEADINGS = {
    "orbital/PROJECT_STATE.md": "# PROJECT_STATE",
    "orbital/DECISIONS.md": "# DECISIONS",
    "orbital/LESSONS.md": "# LESSONS",
    "orbital/INDEX.md": "# INDEX",
}
MEMORY_CATEGORIES = {
    "orbital/PROJECT_STATE.md": "state",
    "orbital/DECISIONS.md": "decision",
    "orbital/LESSONS.md": "lesson",
    "orbital/INDEX.md": "index",
}
KNOWLEDGE_IDENTITY = (
    "-c",
    "user.name=Orbital Team Manager",
    "-c",
    "user.email=manager@orbital-team.invalid",
)
MAX_MEMORY_BYTES = 1024 * 1024


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


class KnowledgeWorkflow:
    """Knowledge Proposal domain commands layered on the SPEC-04 workflow."""

    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.integration = ManagerIntegrationWorkflow(workspace)
        self.runtime_root = self.integration.runtime_root
        self.paths = self.integration.paths

    def _proposals(self, slug: str) -> MutableProjectObjectStore:
        return MutableProjectObjectStore(
            self.runtime_root, slug, "knowledge-proposals", "knowledgeProposal"
        )

    def _summaries(self, slug: str) -> ImmutableProjectObjectStore:
        return ImmutableProjectObjectStore(
            self.runtime_root,
            slug,
            "knowledge-summaries",
            "knowledgeChangeSummary",
            id_field="summary_id",
        )

    def _packs(self, slug: str) -> ImmutableProjectObjectStore:
        return ImmutableProjectObjectStore(
            self.runtime_root, slug, "knowledge-packs", "knowledgePack"
        )

    @staticmethod
    def _proposal_slug(proposal_id: str) -> str:
        match = PROPOSAL_PATTERN.fullmatch(proposal_id)
        if match is None:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND",
                "Knowledge Proposal was not found.",
                {"proposal_id": proposal_id},
            )
        return match.group(1)

    def _proposal(self, proposal_id: str) -> dict[str, Any]:
        slug = self._proposal_slug(proposal_id)
        return self._proposals(slug).read(proposal_id)

    def _pack(self, job: dict[str, Any]) -> dict[str, Any]:
        return self._packs(job["project_slug"]).read(f"{job['id']}-PACK")

    def _summary_for_proposal(
        self, slug: str, proposal_id: str
    ) -> dict[str, Any] | None:
        return next(
            (
                item
                for item in self._summaries(slug).list()
                if item["proposal_id"] == proposal_id
            ),
            None,
        )

    def _canonical(self, slug: str) -> Path:
        return Path(self.integration._project(slug)["canonical_workspace"])

    @staticmethod
    def _next_proposal_id(job_id: str, proposals: Sequence[dict[str, Any]]) -> str:
        numbers = [
            int(item["id"].rsplit("-", 1)[1])
            for item in proposals
            if item["job_id"] == job_id
        ]
        return f"{job_id}-KP-{max(numbers, default=0) + 1:04d}"

    @staticmethod
    def _normalize_patches(patches: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = [copy.deepcopy(item) for item in patches]
        paths = [item.get("path") for item in normalized]
        if len(paths) != len(set(paths)):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Knowledge Proposal paths must be unique."
            )
        for patch in normalized:
            try:
                validate("knowledgePatch", patch)
            except TeamRuntimeError as exc:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED",
                    "Knowledge patch is schema-invalid.",
                    exc.details,
                ) from exc
        return normalized

    def propose(
        self,
        job_id: str,
        patches: Sequence[dict[str, Any]],
        summary: str,
        *,
        actor: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        clean_summary = summary.strip()
        if not clean_summary:
            raise TeamRuntimeError("E_USAGE", "Knowledge Proposal summary is required.")
        normalized = self._normalize_patches(patches)
        job = self.integration.jobs.read(job_id)
        slug = job["project_slug"]
        project = self.integration._project(slug)
        actor = actor or f"manager:{project['active_manager_id']}"
        payload = {"job_id": job_id, "patches": normalized, "summary": clean_summary}
        key = self.integration._request_key("knowledge.propose", request_id, payload)
        guard, _, replay = self.integration._prepare(
            slug, key, payload, f"knowledge:propose:{key}"
        )
        if replay is not None:
            return replay
        store = self._proposals(slug)
        with RuntimeLock(self.integration._project_lock(slug)):
            job = self.integration.jobs.read(job_id)
            if job["state"] != "awaiting_knowledge":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Knowledge can only be proposed for an Awaiting Knowledge job.",
                    {"job_id": job_id, "state": job["state"]},
                )
            proposal_id = self._next_proposal_id(job_id, store.list())
            now = utc_now()
            proposal = {
                "created_at": now,
                "created_by": actor,
                "id": proposal_id,
                "job_id": job_id,
                "patches": normalized,
                "project_slug": slug,
                "report_id": job["report_id"],
                "revision": 0,
                "state": "proposed",
                "summary": clean_summary,
                "task_id": job["task_id"],
            }
            try:
                validate("knowledgeProposal", proposal)
            except TeamRuntimeError as exc:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED",
                    "Knowledge Proposal is schema-invalid.",
                    exc.details,
                ) from exc
            store.create_locked(proposal)
            self.integration._append_event(
                actor=actor,
                data={"job_id": job_id, "proposal_id": proposal_id},
                event_key=f"knowledge:proposed:{proposal_id}",
                event_type="knowledge.proposed",
                slug=slug,
                timestamp=now,
            )
        result = {"ok": True, "proposal": proposal, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    @staticmethod
    def _validate_memory_content(path: str, content: Any, existing: Path) -> None:
        if not isinstance(content, str):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Created/updated knowledge patch needs content."
            )
        if len(content.encode("utf-8")) > MAX_MEMORY_BYTES:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Canonical memory file exceeds the v1 size limit."
            )
        if not content.endswith("\n"):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Canonical memory content must end with a newline."
            )
        heading = MEMORY_HEADINGS[path]
        visible = [line for line in content.splitlines() if line and not line.startswith("<!--")]
        if heading not in visible or visible.count(heading) != 1:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Canonical memory must preserve its single required H1.",
                {"path": path, "required_heading": heading},
            )
        if existing.is_file():
            current = existing.read_text(encoding="utf-8")
            if current.startswith("<!--format "):
                format_line = current.splitlines()[0]
                if not content.startswith(format_line + "\n"):
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED",
                        "Canonical memory format contract comment must be preserved.",
                        {"path": path},
                    )
            current_mem_comments = re.findall(r"<!--mem\s+.*?-->", current)
            proposed_mem_comments = re.findall(r"<!--mem\s+.*?-->", content)
            if proposed_mem_comments != current_mem_comments:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED",
                    "Daemon-managed memory comments must remain byte-for-byte unchanged.",
                    {"path": path},
                )
        if path == "orbital/INDEX.md":
            for line in content.splitlines():
                stripped = line.strip()
                if (
                    stripped
                    and not stripped.startswith(("<!--", "#", "- "))
                ):
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED",
                        "INDEX may only contain headings, comments, and path bullets.",
                        {"line": stripped[:120]},
                    )
                if stripped.startswith("- ") and " — " not in stripped:
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED",
                        "INDEX bullets must use 'path — description'.",
                        {"line": stripped[:120]},
                    )

    def _target(self, canonical: Path, relative: str) -> Path:
        if relative not in MEMORY_PATHS:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Knowledge patch path is outside the canonical memory allowlist.",
                {"path": relative},
            )
        target = canonical / relative
        if target.is_symlink() or target.parent.is_symlink():
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Knowledge patch must not traverse a symlink.",
                {"path": relative},
            )
        try:
            target.parent.resolve().relative_to(canonical.resolve())
        except ValueError as exc:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Knowledge patch escapes the canonical workspace.",
                {"path": relative},
            ) from exc
        return target

    def _baseline_error(
        self, proposal: dict[str, Any]
    ) -> TeamRuntimeError | None:
        slug = proposal["project_slug"]
        job = self.integration.jobs.read(proposal["job_id"])
        pack = self._pack(job)
        canonical = self._canonical(slug)
        if not proposal["patches"]:
            current = {
                relative: digest
                for relative in MEMORY_PATHS
                if (digest := _sha256(self._target(canonical, relative))) is not None
            }
            if current != pack["current_memory_hashes"]:
                return TeamRuntimeError(
                    "E_STALE_PROPOSAL",
                    "Canonical memory changed after the no-change proposal baseline.",
                    {"proposal_id": proposal["id"]},
                    retryable=True,
                )
            return None
        for patch in proposal["patches"]:
            relative = patch["path"]
            target = self._target(canonical, relative)
            if patch["operation"] not in ("created", "updated"):
                raise TeamRuntimeError(
                    "E_GUARDRAIL_VIOLATION",
                    "v1 canonical memory files cannot be deleted or moved.",
                    {"operation": patch["operation"], "path": relative},
                )
            current_hash = _sha256(target)
            if patch["operation"] == "created":
                if patch["base_sha256"] is not None or current_hash is not None:
                    return TeamRuntimeError(
                        "E_STALE_PROPOSAL",
                        "Created knowledge target no longer matches its missing baseline.",
                        {"path": relative},
                        retryable=True,
                    )
            elif patch["base_sha256"] != current_hash:
                return TeamRuntimeError(
                    "E_STALE_PROPOSAL",
                    "Canonical memory hash changed after proposal creation.",
                    {"actual": current_hash, "expected": patch["base_sha256"], "path": relative},
                    retryable=True,
                )
            self._validate_memory_content(relative, patch.get("content"), target)
        return None

    def _set_proposal_state(
        self, proposal: dict[str, Any], state: str
    ) -> dict[str, Any]:
        updated = copy.deepcopy(proposal)
        updated["state"] = state
        updated["revision"] = proposal["revision"] + 1
        return self._proposals(proposal["project_slug"]).write_locked(updated)

    def _mark_stale_locked(
        self, proposal: dict[str, Any], error: TeamRuntimeError
    ) -> dict[str, Any]:
        if proposal["state"] != "stale":
            proposal = self._set_proposal_state(proposal, "stale")
        self.integration._append_event(
            actor="system:teamd",
            data={"proposal_id": proposal["id"], "reason": error.message},
            event_key=f"knowledge:stale:{proposal['id']}:r{proposal['revision']}",
            event_type="knowledge.stale",
            slug=proposal["project_slug"],
            timestamp=utc_now(),
        )
        return proposal

    def validate_proposal(self, proposal_id: str) -> dict[str, Any]:
        slug = self._proposal_slug(proposal_id)
        with RuntimeLock(self.integration._project_lock(slug)):
            proposal = self._proposal(proposal_id)
            if proposal["state"] in ("validated", "applied"):
                return {"ok": True, "proposal": proposal, "schema_version": SCHEMA_VERSION}
            if proposal["state"] != "proposed":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Only a Proposed Knowledge Proposal can be validated.",
                    {"proposal_id": proposal_id, "state": proposal["state"]},
                )
            error = self._baseline_error(proposal)
            if error is not None:
                self._mark_stale_locked(proposal, error)
                raise error
            proposal = self._set_proposal_state(proposal, "validated")
            self.integration._append_event(
                actor="system:teamd",
                data={"job_id": proposal["job_id"], "proposal_id": proposal_id},
                event_key=f"knowledge:validated:{proposal_id}",
                event_type="knowledge.validated",
                slug=slug,
                timestamp=utc_now(),
            )
        return {"ok": True, "proposal": proposal, "schema_version": SCHEMA_VERSION}

    def start_knowledge_run(self, job_id: str, run_id: str) -> dict[str, Any]:
        job = self.integration.jobs.read(job_id)
        slug = job["project_slug"]
        with RuntimeLock(self.integration._project_lock(slug)):
            job = self.integration.jobs.read(job_id)
            if job["state"] != "awaiting_knowledge":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Knowledge run requires an Awaiting Knowledge job.",
                    {"job_id": job_id, "state": job["state"]},
                )
            if job["run_id"] != run_id:
                job = self.integration._update_job(job, run_id=run_id)
        return {"job": job, "ok": True, "schema_version": SCHEMA_VERSION}

    def block_knowledge(
        self,
        job_id: str,
        reason: str,
        *,
        question: str,
        proposal_id: str | None = None,
        owner: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        job = self.integration.jobs.read(job_id)
        slug = job["project_slug"]
        project = self.integration._project(slug)
        actor = actor or f"manager:{project['active_manager_id']}"
        owner = owner or f"human:{project['active_manager_id']}"
        questions_store = self.integration._store(
            slug, "open-questions.json", "openQuestionStore"
        )
        with RuntimeLock(self.integration._project_lock(slug)):
            job = self.integration.jobs.read(job_id)
            if job["state"] == "blocked" and job["block_kind"] == "knowledge":
                questions = questions_store.read()
                linked = next(
                    item for item in questions["items"].values()
                    if job_id in item["related"]["job_ids"]
                )
                return {"job": job, "ok": True, "question": linked}
            if job["state"] != "awaiting_knowledge":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Only an Awaiting Knowledge job can be knowledge-blocked.",
                    {"job_id": job_id, "state": job["state"]},
                )
            now = utc_now()
            questions = questions_store.read()
            question_id = self.integration._next_question_id(slug, questions)
            value = {
                "answer": None,
                "blocking": True,
                "created_at": now,
                "created_by": actor,
                "evidence": [],
                "id": question_id,
                "owner": owner,
                "project_slug": slug,
                "question": question.strip(),
                "related": {
                    "job_ids": [job_id],
                    "potential_task_ids": [],
                    "proposal_ids": [proposal_id] if proposal_id else [],
                    "task_ids": [job["task_id"]],
                },
                "revision": 0,
                "state": "open",
            }
            validate("openQuestion", value)
            questions["items"][question_id] = value
            questions["revision"] += 1
            questions_store.write_locked(questions)
            if proposal_id:
                proposal = self._proposal(proposal_id)
                if proposal["state"] in ("proposed", "validated"):
                    self._set_proposal_state(proposal, "blocked")
            job = self.integration._update_job(
                job, state="blocked", block_kind="knowledge"
            )
            self.integration._append_event(
                actor=actor,
                data={"job_id": job_id, "proposal_id": proposal_id, "question_id": question_id},
                event_key=f"knowledge:blocked:{job_id}:r{job['revision']}",
                event_type="knowledge.blocked",
                slug=slug,
                timestamp=now,
            )
            self.integration._append_event(
                actor=actor,
                data={"job_id": job_id, "question_id": question_id},
                event_key=f"question:created:{question_id}",
                event_type="question.created",
                slug=slug,
                timestamp=now,
            )
        return {"job": job, "ok": True, "question": value}

    def answer_question(
        self, question_id: str, answer: str, *, actor: str
    ) -> dict[str, Any]:
        clean = answer.strip()
        if not clean:
            raise TeamRuntimeError("E_USAGE", "Question answer is required.")
        slug = question_id.rsplit("-Q-", 1)[0]
        store = self.integration._store(
            slug, "open-questions.json", "openQuestionStore"
        )
        with RuntimeLock(self.integration._project_lock(slug)):
            questions = store.read()
            question = questions["items"].get(question_id)
            if question is None:
                raise TeamRuntimeError("E_TASK_NOT_FOUND", "Open Question was not found.")
            if actor != question["owner"]:
                raise TeamRuntimeError(
                    "E_FORBIDDEN_ACTOR", "Only the Open Question owner can answer it."
                )
            if question["state"] == "answered" and question["answer"] == clean:
                return {"ok": True, "question": question}
            if question["state"] not in ("open", "deferred"):
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION", "Question cannot be answered from its state."
                )
            updated = copy.deepcopy(question)
            updated.update(answer=clean, state="answered", revision=question["revision"] + 1)
            questions["items"][question_id] = updated
            questions["revision"] += 1
            store.write_locked(questions)
            now = utc_now()
            self.integration._append_event(
                actor=actor,
                data={"question_id": question_id},
                event_key=f"question:answered:{question_id}:r{updated['revision']}",
                event_type="question.answered",
                slug=slug,
                timestamp=now,
            )
            for job_id in updated["related"]["job_ids"]:
                job = self.integration.jobs.read(job_id)
                if job["state"] == "blocked" and job["block_kind"] == "knowledge":
                    self.integration._append_event(
                        actor=actor,
                        data={"job_id": job_id, "question_id": question_id},
                        event_key=f"knowledge:resume_requested:{job_id}:q{question_id}:r{updated['revision']}",
                        event_type="knowledge.resume_requested",
                        slug=slug,
                        timestamp=now,
                    )
        return {"ok": True, "question": updated}

    def resume_knowledge_job(self, job_id: str) -> dict[str, Any]:
        job = self.integration.jobs.read(job_id)
        slug = job["project_slug"]
        questions_store = self.integration._store(
            slug, "open-questions.json", "openQuestionStore"
        )
        with RuntimeLock(self.integration._project_lock(slug)):
            job = self.integration.jobs.read(job_id)
            if job["state"] == "awaiting_knowledge":
                return {"job": job, "ok": True}
            if job["state"] != "blocked" or job["block_kind"] != "knowledge":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION", "Job is not blocked in knowledge compilation."
                )
            unresolved = [
                item["id"]
                for item in questions_store.read()["items"].values()
                if job_id in item["related"]["job_ids"]
                and item["state"] in ("open", "deferred")
            ]
            if unresolved:
                raise TeamRuntimeError(
                    "E_BLOCKING_QUESTION",
                    "Knowledge questions remain unresolved.",
                    {"questions": sorted(unresolved)},
                )
            job = self.integration._update_job(
                job, state="awaiting_knowledge", block_kind=None, run_id=None
            )
            self.integration._append_event(
                actor="system:teamd",
                data={"job_id": job_id},
                event_key=f"knowledge:resumed:{job_id}:r{job['revision']}",
                event_type="knowledge.resumed",
                slug=slug,
                timestamp=job["updated_at"],
            )
        return {"job": job, "ok": True}

    def _knowledge_commit(self, canonical: Path, proposal_id: str) -> str | None:
        result = self.integration._git(
            canonical,
            "log",
            "--format=%H",
            "--fixed-strings",
            f"--grep=Knowledge proposal {proposal_id}",
            "-n",
            "1",
            check=False,
        )
        commit = result.stdout.strip()
        if not commit:
            return None
        ancestor = self.integration._git(
            canonical, "merge-base", "--is-ancestor", commit, "HEAD", check=False
        )
        return commit if ancestor.returncode == 0 else None

    @staticmethod
    def _patches_present(canonical: Path, patches: Sequence[dict[str, Any]]) -> bool:
        return all(
            (canonical / patch["path"]).is_file()
            and (canonical / patch["path"]).read_text(encoding="utf-8") == patch["content"]
            for patch in patches
        )

    def _dirty_paths(self, canonical: Path) -> list[str]:
        output = self.integration._git_out(canonical, "status", "--porcelain")
        return [line[3:] for line in output.splitlines() if len(line) >= 4]

    def _apply_git(self, proposal: dict[str, Any]) -> str | None:
        canonical = self._canonical(proposal["project_slug"])
        job = self.integration.jobs.read(proposal["job_id"])
        source_ancestor = self.integration._git(
            canonical,
            "merge-base",
            "--is-ancestor",
            job["merge_commit"],
            "HEAD",
            check=False,
        )
        if source_ancestor.returncode != 0:
            raise TeamRuntimeError(
                "E_COMMIT_MISMATCH",
                "Source merge commit is no longer an ancestor of canonical HEAD.",
                {"source_commit": job["merge_commit"]},
            )
        existing_commit = self._knowledge_commit(canonical, proposal["id"])
        if existing_commit:
            dirty = self._dirty_paths(canonical)
            if dirty:
                raise TeamRuntimeError(
                    "E_DIRTY_WORKSPACE",
                    "Canonical workspace changed after the Knowledge Proposal commit.",
                    {"entries": dirty[:20]},
                )
            changed = set(
                self.integration._git_out(
                    canonical,
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    existing_commit,
                ).splitlines()
            )
            expected = {patch["path"] for patch in proposal["patches"]}
            if changed != expected:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Recovered knowledge commit changed unexpected paths.",
                    {"actual": sorted(changed), "expected": sorted(expected)},
                )
            return existing_commit
        dirty = self._dirty_paths(canonical)
        expected_paths = {patch["path"] for patch in proposal["patches"]}
        if dirty:
            if set(dirty) != expected_paths or not self._patches_present(
                canonical, proposal["patches"]
            ):
                if set(dirty).issubset(expected_paths):
                    error = self._baseline_error(proposal)
                    if error is not None:
                        raise error
                raise TeamRuntimeError(
                    "E_DIRTY_WORKSPACE",
                    "Canonical workspace has changes outside this Knowledge Proposal.",
                    {"entries": dirty[:20]},
                )
        else:
            error = self._baseline_error(proposal)
            if error is not None:
                raise error
            for patch in proposal["patches"]:
                target = self._target(canonical, patch["path"])
                mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
                atomic_write_text(target, patch["content"], mode=mode)
        if not proposal["patches"]:
            return None
        paths = sorted(expected_paths)
        self.integration._git(canonical, "add", "--", *paths)
        staged = set(
            self.integration._git_out(
                canonical, "diff", "--cached", "--name-only", "--", *paths
            ).splitlines()
        )
        if staged != expected_paths:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Knowledge apply staged paths outside or short of its allowlist.",
                {"actual": sorted(staged), "expected": paths},
            )
        self.integration._git(
            canonical,
            *KNOWLEDGE_IDENTITY,
            "commit",
            "-m",
            f"Knowledge proposal {proposal['id']}",
            "--",
            *paths,
            code="E_INTERNAL",
        )
        return self.integration._git_out(canonical, "rev-parse", "HEAD")

    def _finalize_apply(
        self, proposal: dict[str, Any], knowledge_commit: str | None
    ) -> dict[str, Any]:
        slug = proposal["project_slug"]
        job = self.integration.jobs.read(proposal["job_id"])
        summary_id = f"{proposal['id']}-KS-0001"
        existing_summary = self._summary_for_proposal(slug, proposal["id"])
        if existing_summary is not None:
            if existing_summary["knowledge_commit"] != knowledge_commit:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Knowledge summary commit does not match recovered apply state.",
                    {"proposal_id": proposal["id"]},
                )
            summary = existing_summary
            applied_at = summary["applied_at"]
        else:
            applied_at = utc_now()
            changes = [
                {
                    "category": MEMORY_CATEGORIES[patch["path"]],
                    "operation": patch["operation"],
                    "path": patch["path"],
                    "summary": proposal["summary"],
                }
                for patch in proposal["patches"]
            ]
            summary = {
                "actor": proposal["created_by"],
                "applied_at": applied_at,
                "changes": changes,
                "job_id": job["id"],
                "knowledge_commit": knowledge_commit,
                "project_slug": slug,
                "proposal_id": proposal["id"],
                "report_id": job["report_id"],
                "schema_version": SCHEMA_VERSION,
                "source_commit": job["merge_commit"],
                "summary_id": summary_id,
            }
            validate("knowledgeChangeSummary", summary)
            self._summaries(slug).create_locked(summary)
        proposal = self._proposal(proposal["id"])
        if proposal["state"] != "applied":
            proposal = self._set_proposal_state(proposal, "applied")
        tasks_store = self.integration._store(slug, "tasks.json", "taskStore")
        tasks = tasks_store.read()
        task = tasks["items"][job["task_id"]]
        if task["state"] != "done":
            if task["state"] != "integrating":
                raise TeamRuntimeError(
                    "E_INVALID_TRANSITION",
                    "Task must remain Integrating until knowledge apply.",
                    {"state": task["state"], "task_id": task["id"]},
                )
            task = self.integration._tasks_write(
                tasks_store, tasks, task, applied_at, state="done"
            )
        job = self.integration.jobs.read(job["id"])
        if job["state"] != "done":
            job = self.integration._update_job(job, state="done", block_kind=None)
        event_data = {
            "job_id": job["id"],
            "proposal_id": proposal["id"],
            "summary_id": summary_id,
            "task_id": task["id"],
        }
        self.integration._append_event(
            actor="system:teamd",
            data=event_data,
            event_key=f"knowledge:applied:{proposal['id']}",
            event_type="knowledge.applied",
            slug=slug,
            timestamp=applied_at,
        )
        self.integration._append_event(
            actor="system:teamd",
            data=event_data,
            event_key=f"task:completed:{task['id']}:{proposal['id']}",
            event_type="task.completed",
            slug=slug,
            timestamp=applied_at,
        )
        self.integration._append_event(
            actor="system:teamd",
            data=event_data,
            event_key=f"integration:completed:{job['id']}",
            event_type="integration.completed",
            slug=slug,
            timestamp=applied_at,
        )
        return {"job": job, "proposal": proposal, "summary": summary, "task": task}

    def apply_proposal(
        self, proposal_id: str, *, request_id: str | None = None
    ) -> dict[str, Any]:
        observed = self._proposal(proposal_id)
        if observed["state"] == "proposed":
            self.validate_proposal(proposal_id)
            observed = self._proposal(proposal_id)
        slug = observed["project_slug"]
        payload = {"proposal_id": proposal_id}
        key = self.integration._request_key("knowledge.apply", request_id, payload)
        guard, _, replay = self.integration._prepare(
            slug, key, payload, f"knowledge:apply:{proposal_id}"
        )
        if replay is not None:
            return replay
        try:
            with RuntimeLock(self.integration._project_lock(slug)):
                proposal = self._proposal(proposal_id)
                existing_summary = self._summary_for_proposal(slug, proposal_id)
                if existing_summary is not None and proposal["state"] == "applied":
                    finalized = self._finalize_apply(
                        proposal, existing_summary["knowledge_commit"]
                    )
                else:
                    if proposal["state"] != "validated":
                        raise TeamRuntimeError(
                            "E_INVALID_TRANSITION",
                            "Only a Validated Knowledge Proposal can be applied.",
                            {"proposal_id": proposal_id, "state": proposal["state"]},
                        )
                    with RuntimeLock(self.integration._git_lock(slug)):
                        knowledge_commit = self._apply_git(proposal)
                        finalized = self._finalize_apply(proposal, knowledge_commit)
        except TeamRuntimeError as exc:
            if exc.code == "E_STALE_PROPOSAL":
                with RuntimeLock(self.integration._project_lock(slug)):
                    proposal = self._proposal(proposal_id)
                    if proposal["state"] in ("proposed", "validated"):
                        self._mark_stale_locked(proposal, exc)
            elif exc.code == "E_DIRTY_WORKSPACE":
                self.block_knowledge(
                    observed["job_id"],
                    exc.message,
                    question="How should the existing canonical workspace changes be handled?",
                    proposal_id=proposal_id,
                    actor="system:teamd",
                )
            raise
        result = {"ok": True, "schema_version": SCHEMA_VERSION, **finalized}
        guard.commit(key, payload, result)
        return result

    def apply_runner_result(
        self, job_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        try:
            validate("managerRunResult", result)
        except TeamRuntimeError as exc:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Knowledge runner result is schema-invalid.", exc.details
            ) from exc
        job = self.integration.jobs.read(job_id)
        if result["job_id"] != job_id or result["run_id"] != job["run_id"]:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Knowledge result does not belong to the active run."
            )
        outcome = result["outcome"]
        if outcome not in ("proposed", "no_change", "blocked", "stale"):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Runner outcome is not valid for knowledge compilation.",
                {"outcome": outcome},
            )
        if outcome in ("proposed", "no_change"):
            proposal_id = result["proposal_id"]
            if not proposal_id:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "Knowledge outcome requires a Proposal ID."
                )
            proposal = self._proposal(proposal_id)
            if proposal["job_id"] != job_id:
                raise TeamRuntimeError(
                    "E_GUARDRAIL_VIOLATION", "Knowledge Proposal belongs to another Job."
                )
            if outcome == "no_change" and proposal["patches"]:
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "no_change Proposal must have no patches."
                )
            return self.apply_proposal(proposal_id)
        if outcome == "blocked":
            risk = result["risk_summary"] or "Knowledge compilation needs human judgment."
            return self.block_knowledge(job_id, risk, question=risk)
        proposal_id = result["proposal_id"]
        if proposal_id:
            proposal = self._proposal(proposal_id)
            error = TeamRuntimeError(
                "E_STALE_PROPOSAL", result["risk_summary"] or "Knowledge baseline is stale."
            )
            with RuntimeLock(self.integration._project_lock(job["project_slug"])):
                self._mark_stale_locked(proposal, error)
        return {"job": job, "ok": True, "stale": True}
