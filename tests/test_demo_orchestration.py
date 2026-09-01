from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.demo_orchestration import (
    _launch_members,
    doctor_demo,
    replay_demo,
    reset_demo,
    setup_demo,
    start_demo,
    status_demo,
)
from orbital_team.errors import TeamRuntimeError
from orbital_team.im_context import IMContextWorkflow
from orbital_team.manager_runner import CommandManagerRunner
from orbital_team.paths import resolve_runtime_paths
from orbital_team.runtime import RuntimeManager
from orbital_team.schema import validate
from orbital_team.storage import EventLog, ProjectStore
from orbital_team.teamd import TeamDaemon

from tests.test_runtime_kernel import git_env


REPO_ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DemoOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, git_env(), clear=True)
        self.environment.start()
        self.temporary = tempfile.TemporaryDirectory(prefix="orbital-spec08-")
        self.root = Path(self.temporary.name) / "demo"

    def tearDown(self) -> None:
        if self.root.is_dir():
            try:
                reset_demo(self.root)
            except TeamRuntimeError:
                shutil.rmtree(self.root)
        self.temporary.cleanup()
        self.environment.stop()

    def setup_demo(self) -> dict[str, object]:
        return setup_demo(self.root, fixture_root=REPO_ROOT)

    def test_versioned_seed_and_fixtures_are_schema_valid_and_synthetic(self) -> None:
        seed = REPO_ROOT / "demo" / "seed"
        manifest = json.loads((seed / "seed.json").read_text(encoding="utf-8"))
        self.assertEqual("builtin", manifest["runner"])
        self.assertTrue(manifest["demo"])
        for filename, schema_name in (
            ("members.json", "memberStore"),
            ("tasks.json", "taskStore"),
            ("potential-tasks.json", "potentialTaskStore"),
            ("open-questions.json", "openQuestionStore"),
        ):
            value = json.loads((seed / filename).read_text(encoding="utf-8"))
            validate(schema_name, value)
            self.assertNotIn(os.fspath(Path.home()), json.dumps(value))
        tasks = json.loads((seed / "tasks.json").read_text(encoding="utf-8"))["items"]
        self.assertEqual({"ready"}, {item["state"] for item in tasks.values()})
        self.assertEqual(2, len(tasks))

    def test_doctor_reports_builtin_and_missing_runner_and_replay_is_labeled(self) -> None:
        self.assertTrue(doctor_demo(REPO_ROOT, runner="builtin")["ok"])
        missing = doctor_demo(REPO_ROOT, runner="does-not-exist")
        self.assertFalse(missing["ok"])
        self.assertFalse(missing["checks"][-1]["available"])
        replay = replay_demo(REPO_ROOT)
        self.assertEqual("simulated-replay", replay["mode"])
        self.assertFalse(replay["live_success"])
        self.assertIn("not evidence", replay["description"])

    def test_setup_shares_runtime_installs_skills_and_keeps_im_objects_separate(self) -> None:
        result = self.setup_demo()
        canonical = Path(result["canonical"])
        alice = Path(result["members"]["alice"])
        bob = Path(result["members"]["bob"])
        roots = {
            resolve_runtime_paths(path).runtime_root
            for path in (canonical, alice, bob)
        }
        self.assertEqual(1, len(roots))
        for worktree in (alice, bob):
            self.assertTrue(
                (worktree / ".agents/skills/orbital-team-member/SKILL.md").is_file()
            )
        snapshot = status_demo(self.root)["snapshot"]
        seeded = [item for item in snapshot["tasks"] if item["id"] in {"apollo-T-0001", "apollo-T-0002"}]
        self.assertEqual({"ready"}, {item["state"] for item in seeded})
        self.assertEqual(1, len(snapshot["potential_tasks"]))
        self.assertEqual("new", snapshot["potential_tasks"][0]["state"])
        self.assertEqual(1, len(snapshot["open_questions"]))
        self.assertTrue(snapshot["open_questions"][0]["blocking"])
        self.assertNotIn(
            snapshot["potential_tasks"][0]["id"], {item["id"] for item in snapshot["tasks"]}
        )

    def test_full_parallel_flow_merges_code_state_and_knowledge_without_source_pollution(self) -> None:
        protected = [
            REPO_ROOT / "demo/seed/seed.json",
            REPO_ROOT / "demo/seed/tasks.json",
            REPO_ROOT / "demo/sample-app/app/greeting.py",
            REPO_ROOT / "demo/im-fixtures/demo-messages.json",
        ]
        before = {path: digest(path) for path in protected}
        setup = self.setup_demo()
        result = start_demo(self.root)
        self.assertTrue(result["ok"])
        self.assertEqual(2, result["daemon"]["jobs_created"])
        self.assertEqual(2, result["daemon"]["knowledge_applied"])
        self.assertEqual(2, result["knowledge_summaries"])
        self.assertEqual("done", result["tasks"]["apollo-T-0001"])
        self.assertEqual("done", result["tasks"]["apollo-T-0002"])
        self.assertEqual(2, len([item for item in result["members"] if "report_id" in item]))

        canonical = Path(setup["canonical"])
        events = EventLog(resolve_runtime_paths(canonical).runtime_root).read().events
        types = [event["type"] for event in events]
        self.assertEqual(2, types.count("integration.merged"))
        self.assertEqual(2, types.count("knowledge.applied"))
        self.assertEqual(2, types.count("integration.completed"))
        for completed_index in [index for index, value in enumerate(types) if value == "integration.completed"]:
            self.assertIn("knowledge.applied", types[:completed_index])
        self.assertIn('return f"Hello, {name}!"', (canonical / "app/greeting.py").read_text())
        self.assertIn('"status": "ok"', (canonical / "app/health.py").read_text())
        self.assertIn("Demo integration", (canonical / "orbital/PROJECT_STATE.md").read_text())
        self.assertEqual(before, {path: digest(path) for path in protected})

    def test_reset_requires_exact_marker_and_two_runs_start_from_clean_seed(self) -> None:
        unsafe = Path(self.temporary.name) / "unsafe"
        unsafe.mkdir()
        sentinel = unsafe / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")
        with self.assertRaises(TeamRuntimeError) as raised:
            reset_demo(unsafe)
        self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)
        self.assertTrue(sentinel.is_file())

        for _ in range(2):
            self.setup_demo()
            snapshot = status_demo(self.root)["snapshot"]
            seeded = [item for item in snapshot["tasks"] if item["id"] in {"apollo-T-0001", "apollo-T-0002"}]
            self.assertEqual({"ready"}, {item["state"] for item in seeded})
            removed = reset_demo(self.root)
            self.assertEqual(self.root.resolve(), Path(removed["removed"]))
            self.assertFalse(self.root.exists())

    def test_member_crash_is_visible_and_does_not_claim_live_success(self) -> None:
        self.setup_demo()
        result = start_demo(self.root, crash_member="bob")
        self.assertFalse(result["ok"])
        bob = next(item for item in result["members"] if item["member"] == "bob")
        self.assertTrue(bob["crashed"])
        self.assertEqual("in_progress", result["tasks"]["apollo-T-0002"])
        self.assertEqual("done", result["tasks"]["apollo-T-0001"])

    def test_manager_retry_reuses_teamd_and_completes_once(self) -> None:
        setup = self.setup_demo()
        canonical = Path(setup["canonical"])
        discovery = IMContextWorkflow(canonical)
        potential = discovery.list_potential("apollo")["potential_tasks"][0]
        discovery.triage(potential["id"], "Retry test triage.", request_id="retry-triage")
        discovery.promote(potential["id"], request_id="retry-promote")
        _launch_members(self.root, None)

        delegate = CommandManagerRunner.from_manifest(canonical / "demo/runners/builtin.json")

        class FlakyRunner:
            agent_type = "fake-flaky-then-builtin"
            phases = frozenset({"integration", "knowledge"})

            def __init__(self) -> None:
                self.failed = False

            def run(self, request: dict[str, object], request_path: Path) -> None:
                if request["phase"] == "integration" and not self.failed:
                    self.failed = True
                    return
                delegate.run(request, request_path)

        daemon = TeamDaemon(canonical, runners={"builtin": FlakyRunner()})
        first = daemon.tick()
        self.assertEqual(1, first["invalid_results"])
        result = daemon.run_once()
        self.assertGreaterEqual(result["requeued"], 1)
        snapshot = status_demo(self.root)["snapshot"]
        jobs = snapshot["integrations"]
        self.assertEqual(2, len(jobs))
        self.assertEqual({"done"}, {item["state"] for item in jobs})
        event_types = [
            event["type"]
            for event in EventLog(resolve_runtime_paths(canonical).runtime_root).read().events
        ]
        self.assertEqual(2, event_types.count("integration.completed"))


if __name__ == "__main__":
    unittest.main()
