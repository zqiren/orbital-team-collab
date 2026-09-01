from __future__ import annotations

import copy
import json
import os
import signal
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from .constants import PRIVATE_FILE_MODE, SCHEMA_VERSION
from .errors import TeamRuntimeError
from .manager_integration import ManagerIntegrationWorkflow
from .runtime import utc_now
from .schema import validate
from .storage import (
    RuntimeLock,
    atomic_write_json,
    atomic_write_private_text,
    read_json,
    secure_directory,
)


DEFAULT_RUN_TIMEOUT = 600
FORBIDDEN_GIT_SUBCOMMANDS = {"merge", "commit", "push", "reset", "rebase"}
DEFAULT_VALIDATION_ARGV = ["python3", "-m", "pytest", "-q"]
SKILL_PATH = Path(__file__).resolve().parent / "skills" / "manager-integration.md"
REQUEST_PATH_PLACEHOLDER = "{request_path}"
PROTECTED_ENV_NAMES = {
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
    "HOME",
    "PATH",
    "PYTHONPATH",
}


def knowledge_skill_path() -> Path:
    candidates = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "orbital-team-manager"
        / "SKILL.md",
        Path(sys.prefix)
        / "share"
        / "orbital-team"
        / "skills"
        / "orbital-team-manager"
        / "SKILL.md",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise TeamRuntimeError(
        "E_RUNNER_UNAVAILABLE", "Orbital Team Manager knowledge Skill was not found."
    )


def assert_policy_guardrails(policies: list[dict[str, Any]]) -> None:
    """Reject command policies that would hand the runner a raw Git mutation."""
    for policy in policies:
        argv = policy["argv_prefix"]
        program = Path(argv[0]).name
        if program == "git" and any(
            token in FORBIDDEN_GIT_SUBCOMMANDS for token in argv[1:]
        ):
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Runner policies must not expose raw git merge/commit/push.",
                {"policy": policy["id"]},
            )


class ManagerRunner(Protocol):
    """A runner receives one schema-valid request file and writes one result file."""

    def run(self, request: dict[str, Any], request_path: Path) -> None: ...


@dataclass(frozen=True, slots=True)
class RunContext:
    run_id: str
    run_dir: Path
    request: dict[str, Any]
    request_path: Path
    result_path: Path
    stdout_path: Path
    stderr_path: Path


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    argv = manifest.get("argv")
    if (
        not isinstance(argv, list)
        or not argv
        or not all(isinstance(item, str) and item for item in argv)
    ):
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Runner manifest must define a non-empty argv list.",
            {"manifest": os.fspath(path)},
        )
    if manifest.get("kind") != "orbital-team-runner":
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Runner manifest kind is not orbital-team-runner.",
            {"manifest": os.fspath(path)},
        )
    pass_request_as = manifest.get("pass_request_as", "argument")
    if pass_request_as not in ("argument", "placeholder"):
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Runner manifest pass_request_as must be argument or placeholder.",
            {"manifest": os.fspath(path)},
        )
    if pass_request_as == "placeholder" and not any(
        REQUEST_PATH_PLACEHOLDER in item for item in argv
    ):
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Placeholder runner manifest does not reference {request_path}.",
            {"manifest": os.fspath(path)},
        )
    extra_env = manifest.get("env", {})
    if not isinstance(extra_env, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in extra_env.items()
    ):
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Runner manifest env must contain only string keys and values.",
            {"manifest": os.fspath(path)},
        )
    protected = sorted(PROTECTED_ENV_NAMES.intersection(extra_env))
    if protected:
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION",
            "Runner manifest cannot override protected execution environment values.",
            {"manifest": os.fspath(path), "variables": protected},
        )
    phases = manifest.get("phases", ["integration"])
    if (
        not isinstance(phases, list)
        or not phases
        or not set(phases).issubset({"integration", "knowledge"})
    ):
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Runner manifest phases must contain integration and/or knowledge.",
            {"manifest": os.fspath(path)},
        )
    return manifest


class CommandManagerRunner:
    """Adapter that launches any agent CLI or scripted manager via argv (never a shell)."""

    def __init__(
        self,
        argv: list[str],
        *,
        agent_type: str = "custom",
        pass_request_as: str = "argument",
        extra_env: dict[str, str] | None = None,
        phases: Sequence[str] = ("integration",),
    ) -> None:
        self.argv = list(argv)
        self.agent_type = agent_type
        self.pass_request_as = pass_request_as
        self.extra_env = dict(extra_env or {})
        self.phases = frozenset(phases)
        protected = sorted(PROTECTED_ENV_NAMES.intersection(self.extra_env))
        if protected:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Runner cannot override protected execution environment values.",
                {"variables": protected},
            )

    @classmethod
    def from_manifest(cls, path: Path) -> "CommandManagerRunner":
        manifest = load_manifest(path)
        return cls(
            manifest["argv"],
            agent_type=manifest.get("agent_type", path.stem),
            pass_request_as=manifest.get("pass_request_as", "argument"),
            extra_env=manifest.get("env", {}),
            phases=manifest.get("phases", ["integration"]),
        )

    def _environment(self) -> dict[str, str]:
        package_root = Path(__file__).resolve().parents[1]
        environment = {
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_SYSTEM": "/dev/null",
            "HOME": os.environ.get("HOME", ""),
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": os.fspath(package_root),
        }
        if os.environ.get("ORBITAL_TEAM_SCHEMA"):
            environment["ORBITAL_TEAM_SCHEMA"] = os.environ["ORBITAL_TEAM_SCHEMA"]
        environment.update(self.extra_env)
        return environment

    def run(self, request: dict[str, Any], request_path: Path) -> None:
        argv = list(self.argv)
        if self.pass_request_as == "argument":
            argv.append(os.fspath(request_path))
        elif self.pass_request_as == "placeholder":
            argv = [
                item.replace(REQUEST_PATH_PLACEHOLDER, os.fspath(request_path))
                for item in argv
            ]
        else:  # constructed adapters receive the same guard as manifests
            raise TeamRuntimeError(
                "E_RUNNER_UNAVAILABLE",
                "Runner pass_request_as must be argument or placeholder.",
            )
        stdout_path = Path(request["input_paths"]["stdout_log"])
        stderr_path = Path(request["input_paths"]["stderr_log"])
        timeout = request["timeout_seconds"]
        with open(
            stdout_path, "ab", opener=lambda p, f: os.open(p, f, PRIVATE_FILE_MODE)
        ) as stdout, open(
            stderr_path, "ab", opener=lambda p, f: os.open(p, f, PRIVATE_FILE_MODE)
        ) as stderr:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=request["workspace"],
                    env=self._environment(),
                    stdout=stdout,
                    stderr=stderr,
                    start_new_session=os.name == "posix",
                )
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                if os.name == "posix":
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:  # process groups require platform-specific job objects
                    process.kill()
                process.wait()
                raise TeamRuntimeError(
                    "E_RUNNER_TIMEOUT",
                    "Manager runner process group exceeded its timeout and was terminated.",
                    {"argv": argv, "timeout_seconds": timeout},
                    retryable=True,
                ) from exc
            except OSError as exc:
                raise TeamRuntimeError(
                    "E_RUNNER_UNAVAILABLE",
                    "Manager runner executable could not be launched.",
                    {"argv": argv, "reason": str(exc)},
                    retryable=True,
                ) from exc
        if returncode != 0:
            raise TeamRuntimeError(
                "E_RUNNER_UNAVAILABLE",
                "Manager runner exited with a non-zero status.",
                {"argv": argv, "returncode": returncode},
                retryable=True,
            )


class RunnerSupervisor:
    """Prepares run inputs, persists run records/logs, and reads structured results."""

    def __init__(self, workflow: ManagerIntegrationWorkflow) -> None:
        self.workflow = workflow
        self.runtime_root = workflow.runtime_root

    def _runs_root(self, slug: str) -> Path:
        return self.runtime_root / "projects" / slug / "runs"

    def _write_run_record(self, slug: str, record: dict[str, Any]) -> dict[str, Any]:
        validate("runRecord", record)
        path = self._runs_root(slug) / record["id"] / "run.json"
        atomic_write_json(path, record)
        return record

    def build_policies(
        self, validation_argv: list[str] | None = None
    ) -> list[dict[str, Any]]:
        policies = [
            {
                "allow_additional_args": True,
                "argv_prefix": ["git", "--no-pager", "diff"],
                "cwd_scope": "canonical_workspace",
                "id": "inspect-diff",
            },
            {
                "allow_additional_args": True,
                "argv_prefix": ["git", "--no-pager", "log"],
                "cwd_scope": "canonical_workspace",
                "id": "inspect-log",
            },
            {
                "allow_additional_args": False,
                "argv_prefix": list(validation_argv or DEFAULT_VALIDATION_ARGV),
                "cwd_scope": "report_worktree",
                "id": "validate",
            },
            {
                "allow_additional_args": True,
                "argv_prefix": [
                    sys.executable or "python3",
                    "-m",
                    "orbital_team",
                    "manager",
                    "merge",
                ],
                "cwd_scope": "canonical_workspace",
                "id": "manager-merge",
            },
        ]
        for policy in policies:
            validate("commandPolicy", policy)
        assert_policy_guardrails(policies)
        return policies

    def build_knowledge_policies(self) -> list[dict[str, Any]]:
        policies = [
            {
                "allow_additional_args": True,
                "argv_prefix": ["git", "--no-pager", "show"],
                "cwd_scope": "canonical_workspace",
                "id": "inspect-merged-diff",
            },
            {
                "allow_additional_args": True,
                "argv_prefix": [
                    sys.executable or "python3",
                    "-m",
                    "orbital_team",
                    "manager",
                    "knowledge",
                    "propose",
                ],
                "cwd_scope": "canonical_workspace",
                "id": "knowledge-propose",
            },
        ]
        for policy in policies:
            validate("commandPolicy", policy)
        assert_policy_guardrails(policies)
        return policies

    def _report_worktree(self, slug: str, report: dict[str, Any]) -> str | None:
        members = self.workflow._store(slug, "members.json", "memberStore").read()
        member_id = report["submitted_by"].split(":", 1)[1]
        member = members["items"].get(member_id)
        return member["worktree"] if member else None

    def prepare_run(
        self,
        job: dict[str, Any],
        *,
        agent_type: str = "custom",
        timeout_seconds: int = DEFAULT_RUN_TIMEOUT,
        validation_argv: list[str] | None = None,
    ) -> RunContext:
        slug = job["project_slug"]
        project = self.workflow._project(slug)
        report = self.workflow._report(slug, job["report_id"])
        tasks = self.workflow._store(slug, "tasks.json", "taskStore").read()
        task = tasks["items"].get(job["task_id"])
        if task is None:
            raise TeamRuntimeError(
                "E_TASK_NOT_FOUND",
                "Manager run Task was not found.",
                {"job_id": job["id"], "task_id": job["task_id"]},
            )
        run_id = f"{slug}-RUN-{uuid.uuid4()}"
        run_dir = self._runs_root(slug) / run_id
        secure_directory(run_dir)
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        request_path = run_dir / "request.json"
        result_path = run_dir / "result.json"
        brief_path = run_dir / "brief.md"
        context_path = run_dir / "context.json"
        task_path = run_dir / "task.json"
        canonical = Path(project["canonical_workspace"])
        target_head = self.workflow._git_out(canonical, "rev-parse", "HEAD")
        context = {
            "base_commit": report["base_commit"],
            "bound_branch": report["branch"],
            "bound_commit": report["commit"],
            "canonical_workspace": os.fspath(canonical),
            "changed_files": report["changed_files"],
            "report_worktree": self._report_worktree(slug, report),
            "task": task,
            "target_head": target_head,
        }
        atomic_write_json(context_path, context)
        atomic_write_json(task_path, task)
        actor = f"manager:{project['active_manager_id']}"
        policies = self.build_policies(validation_argv)
        request = {
            "actor": actor,
            "allowed_commands": policies,
            "allowed_worktree_roots": project["allowed_worktree_roots"],
            "brief_path": os.fspath(brief_path),
            "input_paths": {
                "context": os.fspath(context_path),
                "job": os.fspath(self.workflow.jobs._path(job["id"])),
                "report": os.fspath(
                    self.workflow._reports(slug).root / f"{job['report_id']}.json"
                ),
                "stderr_log": os.fspath(stderr_path),
                "stdout_log": os.fspath(stdout_path),
                "task": os.fspath(task_path),
            },
            "job_id": job["id"],
            "manager_skill_path": os.fspath(SKILL_PATH),
            "phase": "integration",
            "project_slug": slug,
            "result_path": os.fspath(result_path),
            "run_id": run_id,
            "schema_version": SCHEMA_VERSION,
            "task_id": job["task_id"],
            "timeout_seconds": timeout_seconds,
            "workspace": os.fspath(canonical),
        }
        validate("managerRunRequest", request)
        atomic_write_json(request_path, request)
        atomic_write_private_text(
            brief_path, self._brief(project, job, report, context, request)
        )
        record = {
            "actor": actor,
            "agent_type": agent_type,
            "ended_at": None,
            "id": run_id,
            "job_id": job["id"],
            "log_paths": {
                "stderr": f"runs/{run_id}/stderr.log",
                "stdout": f"runs/{run_id}/stdout.log",
                "transcript": None,
            },
            "project_slug": slug,
            "provider_session_id": None,
            "revision": 0,
            "started_at": utc_now(),
            "state": "starting",
            "task_id": job["task_id"],
        }
        with RuntimeLock(self.workflow._project_lock(slug)):
            self._write_run_record(slug, record)
        self.workflow._append_event(
            actor="system:teamd",
            data={"job_id": job["id"], "run_id": run_id},
            event_key=f"run:started:{run_id}",
            event_type="run.started",
            slug=slug,
            timestamp=record["started_at"],
        )
        return RunContext(
            run_id=run_id,
            run_dir=run_dir,
            request=request,
            request_path=request_path,
            result_path=result_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    def prepare_knowledge_run(
        self,
        job: dict[str, Any],
        *,
        agent_type: str = "custom",
        timeout_seconds: int = DEFAULT_RUN_TIMEOUT,
    ) -> RunContext:
        slug = job["project_slug"]
        project = self.workflow._project(slug)
        report = self.workflow._report(slug, job["report_id"])
        tasks = self.workflow._store(slug, "tasks.json", "taskStore").read()
        task = tasks["items"].get(job["task_id"])
        if task is None:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Knowledge run Task was not found.")
        pack_path = (
            self.runtime_root
            / "projects"
            / slug
            / "knowledge-packs"
            / f"{job['id']}-PACK.json"
        )
        pack = read_json(pack_path)
        validate("knowledgePack", pack)
        run_id = f"{slug}-RUN-{uuid.uuid4()}"
        run_dir = self._runs_root(slug) / run_id
        secure_directory(run_dir)
        stdout_path = run_dir / "stdout.log"
        stderr_path = run_dir / "stderr.log"
        request_path = run_dir / "request.json"
        result_path = run_dir / "result.json"
        brief_path = run_dir / "brief.md"
        context_path = run_dir / "context.json"
        task_path = run_dir / "task.json"
        canonical = Path(project["canonical_workspace"])
        memory_paths = {
            Path(relative).stem.lower(): os.fspath(canonical / relative)
            for relative in (
                "orbital/PROJECT_STATE.md",
                "orbital/DECISIONS.md",
                "orbital/LESSONS.md",
                "orbital/INDEX.md",
            )
        }
        context = {
            "current_head": self.workflow._git_out(canonical, "rev-parse", "HEAD"),
            "memory_paths": memory_paths,
            "pack": pack,
            "source_commit": job["merge_commit"],
            "task": task,
        }
        atomic_write_json(context_path, context)
        atomic_write_json(task_path, task)
        actor = f"manager:{project['active_manager_id']}"
        input_paths = {
            "context": os.fspath(context_path),
            "job": os.fspath(self.workflow.jobs._path(job["id"])),
            "knowledge_pack": os.fspath(pack_path),
            "report": os.fspath(
                self.workflow._reports(slug).root / f"{job['report_id']}.json"
            ),
            "stderr_log": os.fspath(stderr_path),
            "stdout_log": os.fspath(stdout_path),
            "task": os.fspath(task_path),
            **{f"memory_{name}": value for name, value in memory_paths.items()},
        }
        request = {
            "actor": actor,
            "allowed_commands": self.build_knowledge_policies(),
            "allowed_worktree_roots": project["allowed_worktree_roots"],
            "brief_path": os.fspath(brief_path),
            "input_paths": input_paths,
            "job_id": job["id"],
            "manager_skill_path": os.fspath(knowledge_skill_path()),
            "phase": "knowledge",
            "project_slug": slug,
            "result_path": os.fspath(result_path),
            "run_id": run_id,
            "schema_version": SCHEMA_VERSION,
            "task_id": job["task_id"],
            "timeout_seconds": timeout_seconds,
            "workspace": os.fspath(canonical),
        }
        validate("managerRunRequest", request)
        atomic_write_json(request_path, request)
        atomic_write_private_text(
            brief_path,
            self._knowledge_brief(project, job, report, task, pack, request),
        )
        record = {
            "actor": actor,
            "agent_type": agent_type,
            "ended_at": None,
            "id": run_id,
            "job_id": job["id"],
            "log_paths": {
                "stderr": f"runs/{run_id}/stderr.log",
                "stdout": f"runs/{run_id}/stdout.log",
                "transcript": None,
            },
            "project_slug": slug,
            "provider_session_id": None,
            "revision": 0,
            "started_at": utc_now(),
            "state": "starting",
            "task_id": job["task_id"],
        }
        with RuntimeLock(self.workflow._project_lock(slug)):
            self._write_run_record(slug, record)
        self.workflow._append_event(
            actor="system:teamd",
            data={"job_id": job["id"], "phase": "knowledge", "run_id": run_id},
            event_key=f"run:started:{run_id}",
            event_type="run.started",
            slug=slug,
            timestamp=record["started_at"],
        )
        return RunContext(
            run_id=run_id,
            run_dir=run_dir,
            request=request,
            request_path=request_path,
            result_path=result_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
        )

    @staticmethod
    def _knowledge_brief(
        project: dict[str, Any],
        job: dict[str, Any],
        report: dict[str, Any],
        task: dict[str, Any],
        pack: dict[str, Any],
        request: dict[str, Any],
    ) -> str:
        return (
            f"# Manager Knowledge Brief — {job['id']}\n\n"
            f"Project: {project['slug']} · Task: {task['id']} · Report: {report['id']}\n\n"
            f"Source merge commit: `{job['merge_commit']}`\n\n"
            f"Report summary: {report['summary']}\n\n"
            f"Merged diff summary:\n\n```text\n{pack['diff_summary']}\n```\n\n"
            f"Read `{request['manager_skill_path']}` and every declared canonical memory file. "
            f"Use only the `knowledge-propose` controlled command to persist full-file patches, "
            f"then write one schema-valid knowledge result to `{request['result_path']}`.\n"
        )

    @staticmethod
    def _brief(
        project: dict[str, Any],
        job: dict[str, Any],
        report: dict[str, Any],
        context: dict[str, Any],
        request: dict[str, Any],
    ) -> str:
        task = context["task"]
        changed = "\n".join(f"- {path}" for path in report["changed_files"]) or "- (none)"
        risks = "\n".join(f"- {risk}" for risk in report["risks"]) or "- (none reported)"
        acceptance = (
            "\n".join(f"- {criterion}" for criterion in task["acceptance_criteria"])
            or "- (none specified)"
        )
        task_paths = "\n".join(f"- {path}" for path in task["paths"]) or "- (none specified)"
        return (
            f"# Manager Integration Brief — {job['id']}\n\n"
            f"Project: {project['slug']} · Task: {job['task_id']} · Report: {report['id']}\n"
            f"Submitted by {report['submitted_by']} on branch `{report['branch']}`.\n\n"
            f"## Review target\n\n"
            f"- Bound commit: `{report['commit']}` (base `{report['base_commit']}`)\n"
            f"- Canonical HEAD at review time: `{context['target_head']}`\n"
            f"- Summary: {report['summary']}\n\n"
            f"## Task contract\n\n"
            f"- Title: {task['title']}\n"
            f"- Description: {task['description'] or '(none)'}\n\n"
            f"### Acceptance criteria\n\n{acceptance}\n\n"
            f"### Declared paths\n\n{task_paths}\n\n"
            f"## Changed files\n\n{changed}\n\n"
            f"## Reported risks\n\n{risks}\n\n"
            f"## Required procedure\n\n"
            f"1. Review the bound diff only (`git --no-pager diff {report['base_commit']} {report['commit']}`).\n"
            f"2. Run the allowed validation command; never mark success on failing tests.\n"
            f"3. Merge exclusively through the controlled command "
            f"`{' '.join(request['allowed_commands'][-1]['argv_prefix'])} {job['id']} "
            f"--expected-head {context['target_head']} --validation <json>`.\n"
            f"4. Write one schema-valid result JSON to `{request['result_path']}`.\n\n"
            f"## Guardrails\n\n"
            f"- No raw `git merge/commit/push`, no remote push, no writes outside the repo.\n"
            f"- A failing validation must end in `changes_requested` or `blocked`.\n"
            f"- Structured result files are the only channel that changes state.\n"
        )

    def mark_running(self, slug: str, run_id: str) -> None:
        self._transition_run(slug, run_id, "running")

    def finish_run(self, slug: str, run_id: str, state: str) -> None:
        self._transition_run(slug, run_id, state, ended=True)

    def _transition_run(
        self, slug: str, run_id: str, state: str, *, ended: bool = False
    ) -> None:
        path = self._runs_root(slug) / run_id / "run.json"
        with RuntimeLock(self.workflow._project_lock(slug)):
            record = read_json(path)
            if record["state"] == state:
                return
            updated = copy.deepcopy(record)
            updated["state"] = state
            updated["revision"] = record["revision"] + 1
            if ended:
                updated["ended_at"] = utc_now()
            self._write_run_record(slug, updated)
        if ended:
            self.workflow._append_event(
                actor="system:teamd",
                data={"run_id": run_id, "state": state},
                event_key=f"run:finished:{run_id}",
                event_type="run.finished",
                slug=slug,
                timestamp=updated["ended_at"],
            )

    def read_run(self, slug: str, run_id: str) -> dict[str, Any]:
        record = read_json(self._runs_root(slug) / run_id / "run.json")
        validate("runRecord", record)
        return record

    def load_result(self, context: RunContext) -> dict[str, Any] | None:
        """Return the schema-valid structured result, or None for retryable policy input."""
        if not context.result_path.is_file():
            return None
        try:
            result = read_json(context.result_path)
            validate("managerRunResult", result)
        except TeamRuntimeError:
            return None
        if (
            result["job_id"] != context.request["job_id"]
            or result["run_id"] != context.run_id
        ):
            return None
        return result
