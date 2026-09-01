from __future__ import annotations

import hashlib
import ipaddress
import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .im_context import IMContextWorkflow
from .manager_integration import JobStore
from .member_workflow import MemberWorkflow
from .runtime import RuntimeManager
from .storage import (
    EventLog,
    ImmutableProjectObjectStore,
    ProjectStore,
    RegistryStore,
    RunRecordStore,
    canonical_json,
)


STATIC_ROOT = Path(__file__).with_name("dashboard_static")
MAX_REQUEST_BYTES = 64 * 1024
MAX_LOG_BYTES = 64 * 1024
MAX_PREVIEW_BYTES = 8 * 1024
MAX_FILE_BYTES = 64 * 1024
MAX_TREE_ENTRIES = 500
KNOWLEDGE_PATHS = {
    "orbital/PROJECT_STATE.md",
    "orbital/DECISIONS.md",
    "orbital/LESSONS.md",
    "orbital/INDEX.md",
}
ACTOR_PATTERN = re.compile(r"^human:[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")
PROJECT_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
RUN_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,31}-RUN-[0-9a-fA-F-]{36}$")


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TeamRuntimeError("E_USAGE", f"{field} must be an array of strings.")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TeamRuntimeError("E_USAGE", f"{field} is required.")
    return value


def _optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TeamRuntimeError("E_USAGE", f"{field} must be a string.")
    return value


def _read_bounded(root: Path, relative: str, limit: int) -> dict[str, Any]:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        return {"available": False, "reason": "path_outside_runtime"}
    try:
        resolved_root = root.resolve()
        target = (root / candidate).resolve()
        if target == resolved_root or resolved_root not in target.parents:
            return {"available": False, "reason": "path_outside_runtime"}
        if target.is_symlink() or not target.is_file():
            return {"available": False, "reason": "unavailable"}
        with target.open("rb") as stream:
            payload = stream.read(limit + 1)
    except OSError:
        return {"available": False, "reason": "unavailable"}
    truncated = len(payload) > limit
    if truncated:
        payload = payload[:limit]
    return {
        "available": True,
        "content": payload.decode("utf-8", errors="replace"),
        "sensitive_local_data": True,
        "truncated": truncated,
    }


def _member_installer_path() -> str | None:
    """Absolute path of the member-adapter installer, when running from a checkout."""
    installer = (
        Path(__file__).resolve().parents[2]
        / "skills"
        / "orbital-team-member"
        / "scripts"
        / "install_adapter.py"
    )
    return os.fspath(installer) if installer.is_file() else None


def _read_run_log(
    project_root: Path, run_id: str, relative: str, limit: int
) -> dict[str, Any]:
    candidate = Path(relative)
    expected = ("runs", run_id)
    if candidate.is_absolute() or candidate.parts[:2] != expected:
        return {"available": False, "reason": "path_outside_run"}
    return _read_bounded(project_root, relative, limit)


class DashboardProjection:
    """Rebuildable read model over canonical runtime files; it stores nothing."""

    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.manager = RuntimeManager(workspace)
        self.paths = self.manager.paths
        self.runtime_root = self.paths.runtime_root

    def projects(self) -> list[dict[str, Any]]:
        registry = RegistryStore(self.runtime_root).read()
        return [
            {
                "created_at": registration["created_at"],
                "display_name": registration["display_name"],
                "slug": registration["slug"],
            }
            for registration in sorted(
                registry["projects"].values(), key=lambda item: item["slug"]
            )
        ]

    def _store(self, slug: str, filename: str, schema_name: str) -> dict[str, Any]:
        return ProjectStore(self.runtime_root, slug, filename, schema_name).read()

    def _project(self, query: str) -> tuple[str, dict[str, Any]]:
        registry = RegistryStore(self.runtime_root).read()
        registration = self.manager._resolve_registration(registry, query)
        slug = registration["slug"]
        return slug, self._store(slug, "project.json", "project")

    def _knowledge(self, slug: str, project: dict[str, Any]) -> list[dict[str, Any]]:
        summaries = ImmutableProjectObjectStore(
            self.runtime_root,
            slug,
            "knowledge-summaries",
            "knowledgeChangeSummary",
            id_field="summary_id",
        ).list()
        canonical = Path(project["canonical_workspace"])
        projected: list[dict[str, Any]] = []
        for summary in sorted(
            summaries, key=lambda item: item["applied_at"], reverse=True
        ):
            value = dict(summary)
            value["changes"] = []
            for change in summary["changes"]:
                item = dict(change)
                preview = (
                    _read_bounded(canonical, change["path"], MAX_PREVIEW_BYTES)
                    if change["path"] in KNOWLEDGE_PATHS
                    else {"available": False, "reason": "path_not_allowlisted"}
                )
                preview.pop("sensitive_local_data", None)
                item["preview"] = preview
                value["changes"].append(item)
            projected.append(value)
        return projected

    @staticmethod
    def _runner_status(project: dict[str, Any]) -> dict[str, Any]:
        runner = project["runner"]
        if runner == "manual":
            return {
                "available": False,
                "detail": "Manual runner: no automatic Manager process is configured.",
                "runner": runner,
            }
        manifest = (
            Path(project["canonical_workspace"]) / "demo" / "runners" / f"{runner}.json"
        )
        return {
            "available": manifest.is_file(),
            "detail": "Runner manifest found." if manifest.is_file() else "Runner manifest unavailable.",
            "runner": runner,
        }

    def snapshot(self, project_query: str) -> dict[str, Any]:
        slug, project = self._project(project_query)
        members = self._store(slug, "members.json", "memberStore")
        tasks = self._store(slug, "tasks.json", "taskStore")
        potentials = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        questions = self._store(slug, "open-questions.json", "openQuestionStore")
        reports = ImmutableProjectObjectStore(
            self.runtime_root, slug, "reports", "report"
        ).list()
        jobs = JobStore(self.runtime_root).list(slug)
        runs = RunRecordStore(self.runtime_root, slug).list()
        event_result = EventLog(self.runtime_root).read()
        project_events = [
            event for event in event_result.events if event["project_slug"] == slug
        ][-250:]
        jobs_by_task: dict[str, list[str]] = {}
        for job in jobs:
            jobs_by_task.setdefault(job["task_id"], []).append(job["id"])
        reports_by_task: dict[str, list[str]] = {}
        for report in reports:
            reports_by_task.setdefault(report["task_id"], []).append(report["id"])
        task_values: list[dict[str, Any]] = []
        for task in sorted(tasks["items"].values(), key=lambda item: item["id"]):
            value = dict(task)
            value["integration_job_ids"] = sorted(jobs_by_task.get(task["id"], []))
            value["report_ids"] = sorted(reports_by_task.get(task["id"], []))
            value["blocking_questions"] = sorted(
                [
                    question["id"]
                    for question in questions["items"].values()
                    if question["blocking"]
                    and question["state"] in {"open", "deferred"}
                    and (
                        task["id"] in question["related"]["task_ids"]
                        or question["id"] in task["blocking_question_ids"]
                    )
                ]
            )
            value["claimable"] = (
                task["state"] == "ready"
                and task["assignee"] is None
                and not value["blocking_questions"]
            )
            task_values.append(value)
        run_values: list[dict[str, Any]] = []
        for run in sorted(runs, key=lambda item: item["started_at"], reverse=True):
            value = dict(run)
            value["log_availability"] = {
                kind: bool(relative)
                and _read_run_log(
                    self.runtime_root / "projects" / slug,
                    run["id"],
                    relative,
                    1,
                )["available"]
                for kind, relative in run["log_paths"].items()
            }
            value["sensitive_local_data"] = True
            run_values.append(value)
        knowledge = self._knowledge(slug, project)
        snapshot: dict[str, Any] = {
            "activity": project_events,
            "errors": (
                [
                    {
                        "code": "E_CORRUPT_RUNTIME",
                        "message": "Event log has an incomplete trailing record; source was preserved.",
                    }
                ]
                if event_result.trailing_corruption
                else []
            ),
            "integrations": jobs,
            "knowledge": knowledge,
            "manager": {
                "active_manager_id": project["active_manager_id"],
                "pending_jobs": sum(job["state"] not in {"done", "blocked", "changes_requested"} for job in jobs),
                "runner": self._runner_status(project),
                "slot_busy": any(job["state"] in {"queued", "running", "retryable"} for job in jobs),
            },
            "member_installer": _member_installer_path(),
            "members": sorted(members["items"].values(), key=lambda item: item["id"]),
            "open_questions": sorted(questions["items"].values(), key=lambda item: item["id"]),
            "potential_tasks": sorted(potentials["items"].values(), key=lambda item: item["id"]),
            "project": project,
            "reports": sorted(reports, key=lambda item: item["submitted_at"], reverse=True),
            "runs": run_values,
            "schema_version": SCHEMA_VERSION,
            "tasks": task_values,
        }
        snapshot["projection_revision"] = hashlib.sha256(canonical_json(snapshot)).hexdigest()
        return snapshot

    def run_log(self, slug: str, run_id: str, kind: str) -> dict[str, Any]:
        if not PROJECT_PATTERN.fullmatch(slug) or not RUN_PATTERN.fullmatch(run_id):
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Run log was not found.")
        if kind not in {"stdout", "stderr", "transcript"}:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Run log was not found.")
        self._project(slug)
        record = RunRecordStore(self.runtime_root, slug).read(run_id)
        relative = record["log_paths"][kind]
        if relative is None:
            return {
                "available": False,
                "kind": kind,
                "reason": "transcript_unavailable",
                "run_id": run_id,
                "sensitive_local_data": True,
            }
        result = _read_run_log(
            self.runtime_root / "projects" / slug, run_id, relative, MAX_LOG_BYTES
        )
        return {"kind": kind, "run_id": run_id, **result}

    # ------------------------------------------------------------------
    # canonical workspace files (read-only projection, like the run logs)
    # ------------------------------------------------------------------

    def _canonical_tree_target(self, slug: str, relative: str) -> tuple[Path, Path]:
        if not PROJECT_PATTERN.fullmatch(slug):
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Project was not found.")
        _, project = self._project(slug)
        root = Path(project["canonical_workspace"]).resolve()
        candidate = Path(relative) if relative else Path(".")
        if candidate.is_absolute() or ".." in candidate.parts or ".git" in candidate.parts:
            raise TeamRuntimeError(
                "E_USAGE", "File path must stay inside the canonical workspace."
            )
        target = (root / candidate).resolve()
        if target != root and root not in target.parents:
            raise TeamRuntimeError(
                "E_USAGE", "File path must stay inside the canonical workspace."
            )
        return root, target

    def file_tree(self, slug: str, relative: str) -> dict[str, Any]:
        root, target = self._canonical_tree_target(slug, relative)
        if target.is_symlink() or not target.is_dir():
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Directory was not found.")
        entries: list[dict[str, Any]] = []
        try:
            children = sorted(target.iterdir(), key=lambda item: item.name)
        except OSError:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Directory was not found.")
        for child in children:
            if child.name == ".git" or child.is_symlink():
                continue
            if len(entries) >= MAX_TREE_ENTRIES:
                break
            if child.is_dir():
                entries.append({"name": child.name, "type": "directory"})
            elif child.is_file():
                entries.append(
                    {"name": child.name, "size": child.stat().st_size, "type": "file"}
                )
        entries.sort(key=lambda item: (item["type"] != "directory", item["name"]))
        return {
            "entries": entries,
            "ok": True,
            "path": os.fspath(target.relative_to(root)) if target != root else "",
            "schema_version": SCHEMA_VERSION,
        }

    def file_content(self, slug: str, relative: str) -> dict[str, Any]:
        root, target = self._canonical_tree_target(slug, relative)
        if target == root:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "File was not found.")
        result = _read_bounded(root, os.fspath(target.relative_to(root)), MAX_FILE_BYTES)
        result.pop("sensitive_local_data", None)
        return {
            "ok": True,
            "path": os.fspath(target.relative_to(root)),
            "schema_version": SCHEMA_VERSION,
            **result,
        }


class DashboardAdapter:
    """Actor-bound command adapter shared by HTTP routes and tests."""

    COMMAND_FIELDS = {
        "task.create": {"acceptance_criteria", "dependencies", "description", "labels", "paths", "request_id", "title"},
        "task.edit": {"acceptance_criteria", "dependencies", "description", "labels", "paths", "request_id", "task_id", "title"},
        "task.ready": {"request_id", "task_id"},
        "potential.triage": {"note", "potential_id", "request_id"},
        "potential.promote": {"potential_id", "request_id"},
        "potential.dismiss": {"potential_id", "reason", "request_id"},
        "potential.duplicate": {"duplicate_of", "potential_id", "request_id"},
        "potential.question": {"owner", "potential_id", "question", "request_id"},
        "question.add": {"blocking", "owner", "question", "request_id", "task_ids"},
        "question.answer": {"answer", "question_id", "request_id"},
        "question.defer": {"deferred_until", "question_id", "reason", "request_id"},
        "question.reopen": {"question_id", "reason", "request_id"},
        "question.close": {"question_id", "reason", "request_id"},
    }

    def __init__(self, workspace: str | os.PathLike[str], actor: str | None) -> None:
        self.projection = DashboardProjection(workspace)
        self.workspace = os.fspath(workspace)
        self.actor = actor if isinstance(actor, str) and ACTOR_PATTERN.fullmatch(actor) else None

    def _access(self, slug: str) -> dict[str, Any]:
        _, project = self.projection._project(slug)
        members = self.projection._store(slug, "members.json", "memberStore")
        actor_id = self.actor.split(":", 1)[1] if self.actor else None
        recognized = actor_id is not None and (
            actor_id == project["active_manager_id"]
            or actor_id in members["items"]
        )
        writable = recognized and actor_id == project["active_manager_id"]
        return {
            "actor": self.actor,
            "read_only": not writable,
            "recognized": recognized,
        }

    def bootstrap(self) -> dict[str, Any]:
        projects = self.projection.projects()
        for project in projects:
            project["access"] = self._access(project["slug"])
        return {
            "actor": self.actor,
            "ok": True,
            "projects": projects,
            "schema_version": SCHEMA_VERSION,
        }

    def snapshot(self, slug: str) -> dict[str, Any]:
        result = self.projection.snapshot(slug)
        result["access"] = self._access(slug)
        return result

    def _authorize(self, slug: str, payload: dict[str, Any], request_actor: str | None) -> None:
        if "actor" in payload or request_actor is not None:
            raise TeamRuntimeError(
                "E_FORBIDDEN_ACTOR",
                "Dashboard requests cannot override the server-bound actor.",
            )
        if self._access(slug)["read_only"]:
            raise TeamRuntimeError(
                "E_READ_ONLY", "Dashboard actor is unknown or lacks Human write authority."
            )

    def command(
        self,
        slug: str,
        command: str,
        payload: dict[str, Any],
        *,
        request_actor: str | None = None,
    ) -> dict[str, Any]:
        if command not in self.COMMAND_FIELDS:
            raise TeamRuntimeError("E_READ_ONLY", "Dashboard command is not allowed.")
        if not isinstance(payload, dict):
            raise TeamRuntimeError("E_USAGE", "Dashboard command body must be an object.")
        self._authorize(slug, payload, request_actor)
        unknown = sorted(set(payload) - self.COMMAND_FIELDS[command])
        if unknown:
            raise TeamRuntimeError(
                "E_USAGE", "Dashboard command contains unknown fields.", {"fields": unknown}
            )
        request_id = _optional_string(payload.get("request_id"), "request_id")
        member = MemberWorkflow(self.workspace)
        discovery = IMContextWorkflow(self.workspace)
        if command == "task.create":
            return member.create_task(
                slug,
                _required_string(payload.get("title"), "title"),
                description=_optional_string(payload.get("description"), "description") or "",
                acceptance_criteria=_string_list(payload.get("acceptance_criteria"), "acceptance_criteria"),
                paths=_string_list(payload.get("paths"), "paths"),
                labels=_string_list(payload.get("labels"), "labels"),
                dependencies=_string_list(payload.get("dependencies"), "dependencies"),
                request_id=request_id,
            )
        if command == "task.edit":
            return member.edit_task(
                _required_string(payload.get("task_id"), "task_id"),
                title=_optional_string(payload.get("title"), "title"),
                description=_optional_string(payload.get("description"), "description"),
                acceptance_criteria=_string_list(payload["acceptance_criteria"], "acceptance_criteria") if "acceptance_criteria" in payload else None,
                paths=_string_list(payload["paths"], "paths") if "paths" in payload else None,
                labels=_string_list(payload["labels"], "labels") if "labels" in payload else None,
                dependencies=_string_list(payload["dependencies"], "dependencies") if "dependencies" in payload else None,
                request_id=request_id,
            )
        if command == "task.ready":
            return member.ready_task(_required_string(payload.get("task_id"), "task_id"), request_id=request_id)
        if command == "potential.triage":
            return discovery.triage(_required_string(payload.get("potential_id"), "potential_id"), _required_string(payload.get("note"), "note"), request_id=request_id)
        if command == "potential.promote":
            return discovery.promote(_required_string(payload.get("potential_id"), "potential_id"), request_id=request_id)
        if command == "potential.dismiss":
            return discovery.dismiss(_required_string(payload.get("potential_id"), "potential_id"), _required_string(payload.get("reason"), "reason"), request_id=request_id)
        if command == "potential.duplicate":
            return discovery.duplicate(_required_string(payload.get("potential_id"), "potential_id"), _required_string(payload.get("duplicate_of"), "duplicate_of"), request_id=request_id)
        if command == "potential.question":
            return discovery.convert_to_question(_required_string(payload.get("potential_id"), "potential_id"), _required_string(payload.get("owner"), "owner"), _required_string(payload.get("question"), "question"), request_id=request_id)
        if command == "question.add":
            return discovery.add_question(slug, _required_string(payload.get("question"), "question"), _required_string(payload.get("owner"), "owner"), blocking=payload.get("blocking") is True, task_ids=_string_list(payload.get("task_ids"), "task_ids"), request_id=request_id)
        action = command.split(".", 1)[1]
        text_field = "answer" if action == "answer" else "reason"
        return discovery.transition_question(
            _required_string(payload.get("question_id"), "question_id"),
            action,
            text=_required_string(payload.get(text_field), text_field),
            deferred_until=_optional_string(payload.get("deferred_until"), "deferred_until"),
            request_id=request_id,
        )


def _http_status(error: TeamRuntimeError) -> int:
    if error.code in {"E_FORBIDDEN_ACTOR", "E_READ_ONLY"}:
        return HTTPStatus.FORBIDDEN
    if error.code in {"E_PROJECT_NOT_FOUND", "E_TASK_NOT_FOUND"}:
        return HTTPStatus.NOT_FOUND
    if error.code in {"E_CORRUPT_RUNTIME", "E_SCHEMA_VERSION", "E_INTERNAL"}:
        return HTTPStatus.INTERNAL_SERVER_ERROR
    if error.code in {"E_LOCK_TIMEOUT", "E_IDEMPOTENCY_CONFLICT"}:
        return HTTPStatus.CONFLICT
    return HTTPStatus.BAD_REQUEST


def dashboard_handler(
    adapter: DashboardAdapter, static_root: Path = STATIC_ROOT
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "OrbitalTeamDashboard/1.0"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, status: int, value: Any) -> None:
            payload = canonical_json(value)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def _error(self, error: TeamRuntimeError) -> None:
            self._json(_http_status(error), error.response())

        def _static(self, relative: str) -> None:
            target = static_root / relative
            try:
                root = static_root.resolve()
                resolved = target.resolve()
                if root not in resolved.parents or not resolved.is_file():
                    raise FileNotFoundError
                payload = resolved.read_bytes()
            except OSError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            split = urlsplit(self.path)
            path = unquote(split.path)
            try:
                if path == "/api/bootstrap":
                    self._json(HTTPStatus.OK, adapter.bootstrap())
                    return
                parts = [part for part in path.split("/") if part]
                if len(parts) == 3 and parts[:2] == ["api", "projects"]:
                    self._json(HTTPStatus.OK, adapter.snapshot(parts[2]))
                    return
                if len(parts) == 7 and parts[:2] == ["api", "projects"] and parts[3] == "runs" and parts[5] == "logs":
                    self._json(HTTPStatus.OK, adapter.projection.run_log(parts[2], parts[4], parts[6]))
                    return
                if len(parts) in (4, 5) and parts[:2] == ["api", "projects"] and parts[3] == "files":
                    relative = parse_qs(split.query).get("path", [""])[0]
                    if len(parts) == 4:
                        self._json(HTTPStatus.OK, adapter.projection.file_tree(parts[2], relative))
                        return
                    if parts[4] == "content":
                        self._json(HTTPStatus.OK, adapter.projection.file_content(parts[2], relative))
                        return
                if path == "/":
                    self._static("index.html")
                    return
                if path.startswith("/assets/") and "/../" not in path:
                    self._static(path.removeprefix("/assets/"))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except TeamRuntimeError as exc:
                self._error(exc)

        def do_POST(self) -> None:
            path = unquote(urlsplit(self.path).path)
            parts = [part for part in path.split("/") if part]
            if len(parts) != 5 or parts[:2] != ["api", "projects"] or parts[3] != "commands":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if self.headers.get_content_type() != "application/json":
                self._error(TeamRuntimeError("E_USAGE", "Content-Type must be application/json."))
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_REQUEST_BYTES:
                self._error(TeamRuntimeError("E_USAGE", "Dashboard request body is too large."))
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._error(TeamRuntimeError("E_USAGE", "Dashboard request is invalid JSON."))
                return
            try:
                result = adapter.command(
                    parts[2],
                    parts[4],
                    payload,
                    request_actor=self.headers.get("X-Orbital-Actor"),
                )
                self._json(HTTPStatus.OK, result)
            except TeamRuntimeError as exc:
                self._error(exc)

    return Handler


class DashboardHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_dashboard_server(
    workspace: str | os.PathLike[str],
    *,
    actor: str | None,
    host: str = "127.0.0.1",
    port: int = 8765,
    server_factory: Callable[..., ThreadingHTTPServer] = DashboardHTTPServer,
) -> ThreadingHTTPServer:
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION", "Dashboard host must be a loopback IP literal."
        ) from exc
    if not address.is_loopback or address.version != 4:
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION", "Dashboard may listen only on IPv4 loopback."
        )
    if port < 0 or port > 65535:
        raise TeamRuntimeError("E_USAGE", "Dashboard port must be between 0 and 65535.")
    adapter = DashboardAdapter(workspace, actor)
    try:
        return server_factory((host, port), dashboard_handler(adapter))
    except OSError as exc:
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION",
            "Dashboard loopback listener could not be started.",
            {"host": host, "port": port, "reason": str(exc)},
        ) from exc


def serve_dashboard(
    workspace: str | os.PathLike[str],
    *,
    actor: str | None,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> None:
    server = create_dashboard_server(workspace, actor=actor, host=host, port=port)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
