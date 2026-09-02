from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.dashboard import (
    DashboardAdapter,
    DashboardProjection,
    create_dashboard_server,
    dashboard_handler,
)
from orbital_team.errors import TeamRuntimeError
from orbital_team.im_context import FixtureIMProvider, IMContextWorkflow
from orbital_team.manager_integration import JobStore
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager, stable_uuid4, utc_now
from orbital_team.schema import validate
from orbital_team.storage import (
    ImmutableProjectObjectStore,
    ProjectStore,
    RunRecordStore,
    RuntimeLock,
    atomic_write_private_text,
    private_mode,
)

from tests.test_runtime_kernel import GitRepository, git_env


REPO_ROOT = Path(__file__).resolve().parents[1]
IM_FIXTURE = REPO_ROOT / "demo" / "im-fixtures" / "messages.json"


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home_dir = tempfile.TemporaryDirectory()
        environment = git_env()
        environment["ORBITAL_TEAM_HOME"] = self.home_dir.name
        self.environment = mock.patch.dict(os.environ, environment, clear=True)
        self.environment.start()
        self.repo = GitRepository()
        self.manager = RuntimeManager(self.repo.repository)
        self.runtime_root = Path(self.manager.init_project("Apollo")["runtime_root"])
        self.member = MemberWorkflow(self.repo.repository)
        self.discovery = IMContextWorkflow(self.repo.repository)
        self.projection = DashboardProjection(self.repo.repository)
        self.adapter = DashboardAdapter(
            self.repo.repository, "human:default-manager"
        )

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()
        self.home_dir.cleanup()

    def ingest(self) -> dict[str, object]:
        return self.discovery.ingest("apollo", FixtureIMProvider(IM_FIXTURE))

    def test_projection_keeps_three_work_types_distinct_and_refreshes_from_files(self) -> None:
        task = self.member.create_task("apollo", "Confirmed delivery")["task"]
        ingested = self.ingest()
        first = self.projection.snapshot("apollo")
        self.assertEqual([task["id"]], [item["id"] for item in first["tasks"]])
        self.assertEqual(
            [ingested["potential_tasks"][0]["id"]],
            [item["id"] for item in first["potential_tasks"]],
        )
        self.assertEqual(
            [ingested["questions"][0]["id"]],
            [item["id"] for item in first["open_questions"]],
        )
        self.assertNotEqual(first["tasks"], first["potential_tasks"])
        external = self.member.create_task("apollo", "External file update")["task"]
        refreshed = self.projection.snapshot("apollo")
        self.assertIn(external["id"], [item["id"] for item in refreshed["tasks"]])
        self.assertNotEqual(first["projection_revision"], refreshed["projection_revision"])
        restarted = DashboardProjection(self.repo.repository).snapshot("apollo")
        self.assertEqual(refreshed["projection_revision"], restarted["projection_revision"])

    def test_adapter_delegates_task_question_and_potential_transitions(self) -> None:
        created = self.adapter.command(
            "apollo",
            "task.create",
            {
                "title": "Dashboard-created task",
                "description": "Created through the bound adapter.",
                "acceptance_criteria": ["Projection refreshes"],
                "request_id": "dashboard-create",
            },
        )["task"]
        edited = self.adapter.command(
            "apollo",
            "task.edit",
            {
                "task_id": created["id"],
                "title": "Edited Dashboard task",
                "labels": ["dashboard"],
            },
        )["task"]
        self.assertEqual("draft", edited["state"])
        self.assertEqual(["dashboard"], edited["labels"])
        question = self.adapter.command(
            "apollo",
            "question.add",
            {
                "blocking": True,
                "owner": "human:default-manager",
                "question": "Is the dashboard acceptance complete?",
                "task_ids": [created["id"]],
            },
        )["question"]
        with self.assertRaises(TeamRuntimeError) as raised:
            self.adapter.command(
                "apollo", "task.ready", {"task_id": created["id"]}
            )
        self.assertEqual("E_BLOCKING_QUESTION", raised.exception.code)
        self.adapter.command(
            "apollo",
            "question.answer",
            {"answer": "Yes.", "question_id": question["id"]},
        )
        ready = self.adapter.command(
            "apollo", "task.ready", {"task_id": created["id"]}
        )["task"]
        self.assertEqual("ready", ready["state"])

        potential = self.ingest()["potential_tasks"][0]
        self.adapter.command(
            "apollo",
            "potential.triage",
            {"note": "Reviewed", "potential_id": potential["id"]},
        )
        promoted = self.adapter.command(
            "apollo", "potential.promote", {"potential_id": potential["id"]}
        )
        self.assertEqual("draft", promoted["task"]["state"])
        self.assertEqual(
            potential["id"], promoted["task"]["source_potential_task_id"]
        )
        for value, schema_name in (
            (promoted["task"], "task"),
            (promoted["potential_task"], "potentialTask"),
        ):
            validate(schema_name, value)

    def test_actor_binding_rejects_unknown_override_and_cross_actor_writes(self) -> None:
        unknown = DashboardAdapter(self.repo.repository, "human:unknown")
        self.assertTrue(unknown.bootstrap()["projects"][0]["access"]["read_only"])
        with self.assertRaises(TeamRuntimeError) as raised:
            unknown.command("apollo", "task.create", {"title": "Spoof"})
        self.assertEqual("E_READ_ONLY", raised.exception.code)
        with self.assertRaises(TeamRuntimeError) as raised:
            self.adapter.command(
                "apollo", "task.create", {"actor": "human:other", "title": "Spoof"}
            )
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)
        with self.assertRaises(TeamRuntimeError) as raised:
            self.adapter.command(
                "apollo",
                "task.create",
                {"title": "Spoof"},
                request_actor="human:other",
            )
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)

        self.manager.init_project("Beacon")
        project_store = ProjectStore(
            self.runtime_root, "beacon", "project.json", "project"
        )

        def handoff(value: dict[str, object]) -> None:
            value["active_manager_id"] = "other-manager"
            value["revision"] = int(value["revision"]) + 1

        project_store.update(handoff)
        with self.assertRaises(TeamRuntimeError) as raised:
            self.adapter.command("beacon", "task.create", {"title": "Cross actor"})
        self.assertEqual("E_READ_ONLY", raised.exception.code)

    def test_projection_includes_jobs_knowledge_previews_and_activity(self) -> None:
        task = self.member.create_task("apollo", "Integration projection")["task"]
        timestamp = utc_now()
        report_id = f"{task['id']}-R-0001"
        job_id = "apollo-J-123456789abc"
        job = {
            "attempt": 0,
            "block_kind": None,
            "created_at": timestamp,
            "id": job_id,
            "idempotency_key": f"integration:{report_id}",
            "merge_commit": None,
            "project_slug": "apollo",
            "report_id": report_id,
            "revision": 0,
            "run_id": None,
            "state": "queued",
            "task_id": task["id"],
            "updated_at": timestamp,
        }
        with RuntimeLock(self.runtime_root / "locks" / "project-apollo.lock"):
            JobStore(self.runtime_root).write_locked(job)
        memory = self.repo.repository / "orbital"
        memory.mkdir()
        (memory / "PROJECT_STATE.md").write_text(
            "# PROJECT_STATE\n\n- Dashboard projection verified.\n", encoding="utf-8"
        )
        proposal_id = f"{job_id}-KP-0001"
        summary = {
            "actor": "manager:default-manager",
            "applied_at": timestamp,
            "changes": [
                {
                    "category": "state",
                    "operation": "updated",
                    "path": "orbital/PROJECT_STATE.md",
                    "summary": "Recorded dashboard projection.",
                }
            ],
            "job_id": job_id,
            "knowledge_commit": None,
            "project_slug": "apollo",
            "proposal_id": proposal_id,
            "report_id": report_id,
            "schema_version": "1.0",
            "source_commit": "a" * 40,
            "summary_id": f"{proposal_id}-KS-0001",
        }
        with RuntimeLock(self.runtime_root / "locks" / "project-apollo.lock"):
            ImmutableProjectObjectStore(
                self.runtime_root,
                "apollo",
                "knowledge-summaries",
                "knowledgeChangeSummary",
                id_field="summary_id",
            ).create_locked(summary)
        snapshot = self.projection.snapshot("apollo")
        self.assertEqual([job_id], snapshot["tasks"][0]["integration_job_ids"])
        self.assertTrue(snapshot["manager"]["slot_busy"])
        self.assertEqual(job_id, snapshot["integrations"][0]["id"])
        preview = snapshot["knowledge"][0]["changes"][0]["preview"]
        self.assertTrue(preview["available"])
        self.assertIn("Dashboard projection verified", preview["content"])
        self.assertTrue(any(event["type"] == "task.created" for event in snapshot["activity"]))

    def test_run_logs_are_bounded_private_and_path_guarded(self) -> None:
        run_id = f"apollo-RUN-{stable_uuid4('dashboard-run')}"
        run_root = self.runtime_root / "projects" / "apollo" / "runs" / run_id
        stdout = run_root / "stdout.log"
        stderr = run_root / "stderr.log"
        atomic_write_private_text(stdout, "safe <script>alert(1)</script> output\n")
        atomic_write_private_text(stderr, "local error\n")
        record = {
            "actor": "manager:default-manager",
            "agent_type": "fixture",
            "ended_at": None,
            "id": run_id,
            "job_id": None,
            "log_paths": {
                "stderr": f"runs/{run_id}/stderr.log",
                "stdout": f"runs/{run_id}/stdout.log",
                "transcript": "/tmp/external-transcript.jsonl",
            },
            "project_slug": "apollo",
            "provider_session_id": None,
            "revision": 0,
            "started_at": utc_now(),
            "state": "running",
            "task_id": None,
        }
        with RuntimeLock(self.runtime_root / "locks" / "project-apollo.lock"):
            RunRecordStore(self.runtime_root, "apollo").write_locked(record)
        self.assertEqual(0o600, private_mode(stdout))
        result = self.projection.run_log("apollo", run_id, "stdout")
        self.assertTrue(result["available"])
        self.assertIn("<script>", result["content"])
        self.assertTrue(result["sensitive_local_data"])
        transcript = self.projection.run_log("apollo", run_id, "transcript")
        self.assertFalse(transcript["available"])
        self.assertEqual("path_outside_run", transcript["reason"])
        record["log_paths"]["transcript"] = "project.json"
        record["revision"] += 1
        with RuntimeLock(self.runtime_root / "locks" / "project-apollo.lock"):
            RunRecordStore(self.runtime_root, "apollo").write_locked(record)
        unrelated = self.projection.run_log("apollo", run_id, "transcript")
        self.assertFalse(unrelated["available"])
        self.assertEqual("path_outside_run", unrelated["reason"])

    def _raw_http(self, request: bytes) -> tuple[int, bytes, dict[str, str]]:
        class MemorySocket:
            def __init__(self, payload: bytes) -> None:
                self.input = io.BytesIO(payload)
                self.output = io.BytesIO()

            def makefile(self, mode: str, *args: object, **kwargs: object) -> io.BytesIO:
                return self.input if "r" in mode else self.output

            def sendall(self, payload: bytes) -> None:
                self.output.write(payload)

        class Server:
            server_name = "127.0.0.1"
            server_port = 8765

        connection = MemorySocket(request)
        dashboard_handler(self.adapter)(connection, ("127.0.0.1", 12345), Server())
        header, body = connection.output.getvalue().split(b"\r\n\r\n", 1)
        lines = header.decode().split("\r\n")
        status = int(lines[0].split()[1])
        headers = {
            key.strip(): value.strip()
            for key, value in (line.split(":", 1) for line in lines[1:] if ":" in line)
        }
        return status, body, headers

    def test_http_handler_smoke_static_write_poll_and_actor_rejection(self) -> None:
        status, page, headers = self._raw_http(
            b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        )
        self.assertEqual(200, status)
        self.assertIn(b"Team Dashboard", page)
        self.assertIn("text/html", headers["Content-Type"])
        status, script, _ = self._raw_http(
            b"GET /assets/app.js HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        )
        self.assertEqual(200, status)
        self.assertIn(b"setInterval(refresh, 2000)", script)
        status, payload, _ = self._raw_http(
            b"GET /api/bootstrap HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        )
        self.assertEqual(200, status)
        self.assertFalse(json.loads(payload)["projects"][0]["access"]["read_only"])
        body = json.dumps({"title": "HTTP-created Draft"}).encode()
        request = (
            b"POST /api/projects/apollo/commands/task.create HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\nContent-Type: application/json\r\n"
            + f"Content-Length: {len(body)}\r\n\r\n".encode()
            + body
        )
        status, payload, _ = self._raw_http(request)
        self.assertEqual(200, status)
        task_id = json.loads(payload)["task"]["id"]
        status, payload, _ = self._raw_http(
            b"GET /api/projects/apollo HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n"
        )
        self.assertEqual(200, status)
        self.assertIn(task_id, [item["id"] for item in json.loads(payload)["tasks"]])
        spoof = json.dumps({"title": "Header spoof"}).encode()
        request = (
            b"POST /api/projects/apollo/commands/task.create HTTP/1.1\r\n"
            b"Host: 127.0.0.1\r\nContent-Type: application/json\r\n"
            b"X-Orbital-Actor: human:other\r\n"
            + f"Content-Length: {len(spoof)}\r\n\r\n".encode()
            + spoof
        )
        status, payload, _ = self._raw_http(request)
        self.assertEqual(403, status)
        self.assertEqual("E_FORBIDDEN_ACTOR", json.loads(payload)["error"]["code"])
        restarted = DashboardAdapter(
            self.repo.repository, "human:default-manager"
        ).snapshot("apollo")
        self.assertIn(task_id, [item["id"] for item in restarted["tasks"]])

    def test_non_loopback_bind_is_rejected(self) -> None:
        with self.assertRaises(TeamRuntimeError) as raised:
            create_dashboard_server(
                self.repo.repository,
                actor="human:default-manager",
                host="0.0.0.0",
                port=0,
            )
        self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)

    def test_corrupt_runtime_returns_error_without_overwriting_source(self) -> None:
        self.member.create_task("apollo", "Visible before corruption")
        tasks_path = self.runtime_root / "projects" / "apollo" / "tasks.json"
        tasks_path.write_text('{"broken":', encoding="utf-8")
        before = tasks_path.read_bytes()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.adapter.snapshot("apollo")
        self.assertEqual("E_CORRUPT_RUNTIME", raised.exception.code)
        self.assertEqual(before, tasks_path.read_bytes())

    def test_file_projection_lists_canonical_tree_and_refuses_escapes(self) -> None:
        (self.repo.repository / "app").mkdir()
        (self.repo.repository / "app" / "module.py").write_text("VALUE = 1\n", encoding="utf-8")

        listing = self.projection.file_tree("apollo", "")
        names = [entry["name"] for entry in listing["entries"]]
        self.assertIn("app", names)
        self.assertIn("tracked.txt", names)
        self.assertNotIn(".git", names)
        self.assertEqual("directory", listing["entries"][0]["type"])

        nested = self.projection.file_tree("apollo", "app")
        self.assertEqual(
            [{"name": "module.py", "size": 10, "type": "file"}], nested["entries"]
        )

        content = self.projection.file_content("apollo", "app/module.py")
        self.assertTrue(content["available"])
        self.assertEqual("VALUE = 1\n", content["content"])
        self.assertNotIn("sensitive_local_data", content)

        for escape in ("..", "../outside", "/etc", ".git", ".git/config"):
            with self.assertRaises(TeamRuntimeError) as raised:
                self.projection.file_tree("apollo", escape)
            self.assertIn(raised.exception.code, {"E_USAGE", "E_TASK_NOT_FOUND"})
        with self.assertRaises(TeamRuntimeError):
            self.projection.file_content("apollo", "")
        with self.assertRaises(TeamRuntimeError):
            self.projection.file_content("apollo", "../outside")

    def test_static_assets_have_accessible_landmarks_and_no_direct_json_writes(self) -> None:
        static = REPO_ROOT / "src" / "orbital_team" / "dashboard_static"
        html = (static / "index.html").read_text(encoding="utf-8")
        script = (static / "app.js").read_text(encoding="utf-8")
        for marker in ("<main", "<nav", 'role="alert"', 'aria-live="polite"', "<label"):
            self.assertIn(marker, html)
        self.assertNotIn("innerHTML", script)
        self.assertNotIn("potential-tasks.json", script)
        self.assertNotIn("open-questions.json", script)
        self.assertNotIn("tasks.json", script)
        self.assertIn("/commands/", script)

    def test_create_project_on_plain_folder_initializes_git_and_registers(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / "gemini-notes"
            folder.mkdir()
            (folder / "notes.md").write_text("hello\n", encoding="utf-8")
            result = self.adapter.create_project(
                {"name": "Gemini", "workspace": os.fspath(folder)}
            )
            self.assertTrue(result["created"])
            self.assertEqual("gemini", result["project"]["slug"])

            resolved = folder.resolve()
            head = subprocess.run(
                ["git", "-C", os.fspath(resolved), "log", "--format=%s", "-1"],
                capture_output=True, text=True,
            )
            self.assertEqual(0, head.returncode)
            self.assertIn("Initialize Orbital Team project", head.stdout)
            tracked = subprocess.run(
                ["git", "-C", os.fspath(resolved), "ls-files"],
                capture_output=True, text=True,
            )
            self.assertIn("notes.md", tracked.stdout)

            bootstrap = self.adapter.bootstrap()
            slugs = {item["slug"]: item for item in bootstrap["projects"]}
            self.assertIn("apollo", slugs)
            self.assertIn("gemini", slugs)
            self.assertEqual(os.fspath(resolved), slugs["gemini"]["workspace"])
            # The creating actor becomes the manager, so the project is writable.
            self.assertFalse(slugs["gemini"]["access"]["read_only"])

            snapshot = self.adapter.snapshot("gemini")
            self.assertEqual(
                "default-manager", snapshot["manager"]["active_manager_id"]
            )
            listing = self.adapter.file_tree("gemini", "")
            self.assertIn(
                "notes.md", [entry["name"] for entry in listing["entries"]]
            )

            # A second adapter (fresh process) finds the project via the home
            # registry alone.
            fresh = DashboardAdapter(None, "human:default-manager")
            self.assertIn(
                "gemini",
                [item["slug"] for item in fresh.bootstrap()["projects"]],
            )

    def test_create_project_rejects_conflicts_and_bad_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            other = Path(raw) / "other"
            other.mkdir()
            with self.assertRaises(TeamRuntimeError) as conflict:
                self.adapter.create_project(
                    {"name": "Apollo", "workspace": os.fspath(other)}
                )
            self.assertEqual("E_IDEMPOTENCY_CONFLICT", conflict.exception.code)

            with self.assertRaises(TeamRuntimeError) as missing:
                self.adapter.create_project(
                    {"name": "Ghost", "workspace": os.fspath(Path(raw) / "absent")}
                )
            self.assertEqual("E_TASK_NOT_FOUND", missing.exception.code)

            with self.assertRaises(TeamRuntimeError) as relative:
                self.adapter.create_project({"name": "Rel", "workspace": "relative/path"})
            self.assertEqual("E_USAGE", relative.exception.code)

            nested = self.repo.repository / "nested"
            nested.mkdir()
            with self.assertRaises(TeamRuntimeError) as inside:
                self.adapter.create_project(
                    {"name": "Nested", "workspace": os.fspath(nested)}
                )
            self.assertEqual("E_USAGE", inside.exception.code)

            readonly = DashboardAdapter(self.repo.repository, None)
            with self.assertRaises(TeamRuntimeError) as unauthorized:
                readonly.create_project(
                    {"name": "Blocked", "workspace": os.fspath(other)}
                )
            self.assertEqual("E_READ_ONLY", unauthorized.exception.code)

    def test_runner_selection_probes_and_updates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw) / "headless"
            folder.mkdir()
            result = self.adapter.create_project(
                {"name": "Headless", "runner": "claude-code", "workspace": os.fspath(folder)}
            )
            self.assertEqual("headless", result["project"]["slug"])
            snapshot = self.adapter.snapshot("headless")
            self.assertEqual("claude-code", snapshot["project"]["runner"])
            # The bundled manifest resolves from the orbital-team checkout even
            # though the new folder has no demo/runners of its own.
            self.assertTrue(snapshot["manager"]["runner"]["available"])
            self.assertEqual(0, snapshot["manager"]["queued_jobs"])
            self.assertEqual(0, snapshot["manager"]["running_jobs"])

            other = Path(raw) / "invalid-runner"
            other.mkdir()
            with self.assertRaises(TeamRuntimeError) as unknown:
                self.adapter.create_project(
                    {"name": "Bad", "runner": "no-such-runner", "workspace": os.fspath(other)}
                )
            self.assertEqual("E_RUNNER_UNAVAILABLE", unknown.exception.code)

            switched = self.adapter.command("headless", "project.runner", {"runner": "manual"})
            self.assertEqual("manual", switched["project"]["runner"])
            back = self.adapter.command("headless", "project.runner", {"runner": "codex"})
            self.assertEqual("codex", back["project"]["runner"])
            with self.assertRaises(TeamRuntimeError) as invalid:
                self.adapter.command("headless", "project.runner", {"runner": "no-such-runner"})
            self.assertEqual("E_RUNNER_UNAVAILABLE", invalid.exception.code)

            agents = self.adapter.platform_agents()
            for key in ("claude-code", "codex"):
                self.assertIn(key, agents["agents"])
                self.assertIsInstance(agents["agents"][key]["cli"], bool)
                self.assertIsInstance(agents["agents"][key]["signed_in"], bool)
                self.assertTrue(agents["agents"][key]["login_hint"])

    def test_platform_browse_and_mkdir_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "alpha").mkdir()
            (root / ".hidden").mkdir()
            (root / "file.txt").write_text("x", encoding="utf-8")

            listing = self.adapter.platform_browse(os.fspath(root))
            self.assertEqual(
                ["alpha"], [entry["name"] for entry in listing["entries"]]
            )
            self.assertFalse(listing["is_git_repo"])
            repo_listing = self.adapter.platform_browse(
                os.fspath(self.repo.repository)
            )
            self.assertTrue(repo_listing["is_git_repo"])

            with self.assertRaises(TeamRuntimeError) as relative:
                self.adapter.platform_browse("relative")
            self.assertEqual("E_USAGE", relative.exception.code)

            made = self.adapter.platform_mkdir(
                {"path": os.fspath(root / "beta")}
            )
            self.assertTrue(Path(made["path"]).is_dir())
            with self.assertRaises(TeamRuntimeError) as exists:
                self.adapter.platform_mkdir({"path": os.fspath(root / "beta")})
            self.assertEqual("E_IDEMPOTENCY_CONFLICT", exists.exception.code)
            with self.assertRaises(TeamRuntimeError) as orphan:
                self.adapter.platform_mkdir(
                    {"path": os.fspath(root / "absent" / "leaf")}
                )
            self.assertEqual("E_USAGE", orphan.exception.code)

            readonly = DashboardAdapter(self.repo.repository, None)
            with self.assertRaises(TeamRuntimeError) as unauthorized:
                readonly.platform_browse(os.fspath(root))
            self.assertEqual("E_READ_ONLY", unauthorized.exception.code)


if __name__ == "__main__":
    unittest.main()
