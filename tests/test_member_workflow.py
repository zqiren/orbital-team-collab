from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.cli import _parser, main as cli_main
from orbital_team.errors import TeamRuntimeError
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager, utc_now
from orbital_team.schema import validate
from orbital_team.storage import EventLog, ProjectStore

from tests.test_runtime_kernel import GitRepository, git, git_env


class MemberWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, git_env(), clear=True)
        self.environment.start()
        self.repo = GitRepository()
        self.manager = RuntimeManager(self.repo.repository)
        self.runtime_root = Path(self.manager.init_project("Apollo")["runtime_root"])
        self.alice_worktree, self.bob_worktree = self.repo.worktrees()
        self.manager_workflow = MemberWorkflow(self.repo.repository)
        self.alice = MemberWorkflow(self.alice_worktree)
        self.bob = MemberWorkflow(self.bob_worktree)
        self.alice.join_member("apollo", "alice", "codex")
        self.bob.join_member("Apollo", "bob", "claude-code")

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def create_task(
        self,
        title: str = "Add health endpoint",
        *,
        ready: bool = True,
        request_id: str | None = None,
        labels: tuple[str, ...] = ("backend",),
        dependencies: tuple[str, ...] = (),
    ) -> dict[str, object]:
        task = self.manager_workflow.create_task(
            "apollo",
            title,
            description="Add a deterministic health endpoint.",
            acceptance_criteria=["GET /health returns 200"],
            paths=["src/health.py", "tests/test_health.py"],
            labels=labels,
            dependencies=dependencies,
            request_id=request_id,
        )["task"]
        if ready:
            task = self.manager_workflow.ready_task(task["id"])["task"]
        return task

    def add_blocking_question(self, task_id: str) -> dict[str, object]:
        question = {
            "answer": None,
            "blocking": True,
            "created_at": utc_now(),
            "created_by": "human:lead",
            "evidence": [],
            "id": "apollo-Q-0001",
            "owner": "human:lead",
            "project_slug": "apollo",
            "question": "Which health response format is approved?",
            "related": {
                "job_ids": [],
                "potential_task_ids": [],
                "proposal_ids": [],
                "task_ids": [task_id],
            },
            "revision": 0,
            "state": "open",
        }
        store = ProjectStore(
            self.runtime_root, "apollo", "open-questions.json", "openQuestionStore"
        )

        def add(value: dict[str, object]) -> None:
            items = value["items"]
            assert isinstance(items, dict)
            items[question["id"]] = question
            value["revision"] = int(value["revision"]) + 1

        store.update(add)
        return question

    def commit_alice_change(self, filename: str = "health.py") -> str:
        target = self.alice_worktree / filename
        target.write_text("def health():\n    return 200\n", encoding="utf-8")
        git(self.alice_worktree, "add", filename)
        git(self.alice_worktree, "commit", "-m", "implement health endpoint")
        return git(self.alice_worktree, "rev-parse", "HEAD")

    def test_member_join_records_git_binding_and_event(self) -> None:
        members = ProjectStore(
            self.runtime_root, "apollo", "members.json", "memberStore"
        ).read()
        self.assertEqual("worker-one", members["items"]["alice"]["branch"])
        self.assertEqual(
            self.alice_worktree.resolve(),
            Path(members["items"]["alice"]["worktree"]).resolve(),
        )
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(2, sum(event["type"] == "member.joined" for event in events))

    def test_repeat_member_join_is_idempotent(self) -> None:
        first = self.alice.join_member("apollo", "alice", "codex")
        second = self.alice.join_member("apollo", "alice", "codex")
        self.assertEqual(first, second)
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(1, sum(event["data"].get("member_id") == "alice" for event in events))

    def test_task_ids_are_project_scoped_sequences_and_start_draft(self) -> None:
        first = self.create_task("One", ready=False, request_id="one")
        second = self.create_task("Two", ready=False, request_id="two")
        self.assertEqual("apollo-T-0001", first["id"])
        self.assertEqual("apollo-T-0002", second["id"])
        self.assertEqual("draft", first["state"])

    def test_task_ready_transition_is_idempotent(self) -> None:
        task = self.create_task(ready=False)
        first = self.manager_workflow.ready_task(task["id"])
        second = self.manager_workflow.ready_task(task["id"])
        self.assertEqual(first, second)
        self.assertEqual("ready", first["task"]["state"])

    def test_unique_normalized_title_claims_task(self) -> None:
        task = self.create_task("Add   Health Endpoint")
        result = self.alice.claim("Apollo", "add health endpoint")
        self.assertEqual(task["id"], result["task"]["id"])
        self.assertEqual("alice", result["task"]["assignee"])
        self.assertEqual("claimed", result["task"]["state"])

    def test_repeat_claim_returns_original_context_without_duplicate_event(self) -> None:
        task = self.create_task()
        first = self.alice.claim("apollo", task["id"], request_id="claim-once")
        second = self.alice.claim("apollo", task["id"], request_id="claim-once")
        self.assertEqual(first, second)
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(1, sum(event["type"] == "task.claimed" for event in events))

    def test_ambiguous_query_returns_candidates_without_mutation(self) -> None:
        first = self.create_task("Health read endpoint", request_id="read", labels=("health",))
        second = self.create_task("Health write endpoint", request_id="write", labels=("health",))
        before = ProjectStore(
            self.runtime_root, "apollo", "tasks.json", "taskStore"
        ).read()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.claim("apollo", "health")
        self.assertEqual("E_TASK_AMBIGUOUS", raised.exception.code)
        self.assertEqual([first["id"], second["id"]], raised.exception.details["candidates"])
        after = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual(before, after)

    def test_not_found_query_has_no_side_effect(self) -> None:
        self.create_task()
        store = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore")
        before = store.read()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.claim("apollo", "database migration")
        self.assertEqual("E_TASK_NOT_FOUND", raised.exception.code)
        self.assertEqual(before, store.read())

    def test_blocking_open_question_prevents_claim_without_mutation(self) -> None:
        task = self.create_task()
        question = self.add_blocking_question(task["id"])
        store = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore")
        before = store.read()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.claim("apollo", task["id"])
        self.assertEqual("E_BLOCKING_QUESTION", raised.exception.code)
        self.assertEqual(question["id"], raised.exception.details["questions"][0]["id"])
        self.assertEqual(before, store.read())

    def test_incomplete_dependency_prevents_ready(self) -> None:
        dependency = self.create_task("Dependency", ready=False)
        task = self.create_task(
            "Dependent", ready=False, request_id="dependent", dependencies=(dependency["id"],)
        )
        with self.assertRaises(TeamRuntimeError) as raised:
            self.manager_workflow.ready_task(task["id"])
        self.assertEqual("E_DEPENDENCY_INCOMPLETE", raised.exception.code)

    def test_only_ready_tasks_can_be_claimed(self) -> None:
        task = self.create_task(ready=False)
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.claim("apollo", task["id"])
        self.assertEqual("E_TASK_NOT_READY", raised.exception.code)

    def test_two_processes_atomically_claim_one_task(self) -> None:
        task = self.create_task()
        barrier = self.repo.root / "claim-start"
        script = """
import json, pathlib, sys, time
from orbital_team.errors import TeamRuntimeError
from orbital_team.member_workflow import MemberWorkflow
while not pathlib.Path(sys.argv[3]).exists():
    time.sleep(0.01)
try:
    result = MemberWorkflow(sys.argv[1]).claim("apollo", sys.argv[2])
    print(json.dumps([True, result["task"]["assignee"]]))
except TeamRuntimeError as exc:
    print(json.dumps([False, exc.code]))
"""
        environment = git_env()
        environment["PYTHONPATH"] = os.fspath(Path(__file__).resolve().parents[1] / "src")
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", script, os.fspath(worktree), task["id"], os.fspath(barrier)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=environment,
            )
            for worktree in (self.alice_worktree, self.bob_worktree)
        ]
        barrier.write_text("go\n", encoding="utf-8")
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=20)
            self.assertEqual(0, process.returncode, stderr)
            results.append(json.loads(stdout))
        successes = [value for ok, value in results if ok]
        failures = [value for ok, value in results if not ok]
        self.assertEqual(1, len(successes), results)
        self.assertEqual(["E_TASK_ALREADY_CLAIMED"], failures)
        stored = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual(successes[0], stored["items"][task["id"]]["assignee"])
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(1, sum(event["type"] == "task.claimed" for event in events))

    def test_context_pack_is_bounded_and_points_to_project_memory(self) -> None:
        memory = self.repo.repository / "orbital"
        memory.mkdir()
        (memory / "PROJECT_STATE.md").write_text("state " * 10000, encoding="utf-8")
        task = self.create_task()
        context = self.alice.claim("apollo", task["id"])["context"]
        self.assertLessEqual(len(json.dumps(context, sort_keys=True, separators=(",", ":")).encode()), 32 * 1024)
        self.assertLessEqual(context["serialized_bytes"], context["budget_bytes"])
        self.assertTrue(context["truncated"])
        self.assertIn("report_requirements", context)
        self.assertTrue(any(pointer["path"] == "orbital/PROJECT_STATE.md" for pointer in context["memory_pointers"]))

    def test_assignee_can_start_and_repeat_start(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        first = self.alice.start_task(task["id"])
        second = self.alice.start_task(task["id"])
        self.assertEqual(first, second)
        self.assertEqual("in_progress", first["task"]["state"])

    def test_non_assignee_cannot_start(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        with self.assertRaises(TeamRuntimeError) as raised:
            self.bob.start_task(task["id"])
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)

    def test_branch_mismatch_prevents_start(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        git(self.alice_worktree, "checkout", "-b", "unexpected-branch")
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.start_task(task["id"])
        self.assertEqual("E_WORKTREE_MISMATCH", raised.exception.code)

    def test_member_block_records_reason_in_event(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        result = self.alice.block_task(task["id"], "Waiting for test fixture")
        self.assertEqual("blocked", result["task"]["state"])
        self.assertEqual("in_progress", result["task"]["blocked_from"])
        event = EventLog(self.runtime_root).read().events[-1]
        self.assertEqual("task.blocked", event["type"])
        self.assertEqual("Waiting for test fixture", event["data"]["reason"])

    def test_block_from_claimed_is_invalid_transition(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.block_task(task["id"], "too early")
        self.assertEqual("E_INVALID_TRANSITION", raised.exception.code)

    def test_claimed_to_submitted_is_rejected(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.commit_alice_change()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.submit_report(task["id"], summary="Should be rejected")
        self.assertEqual("E_INVALID_TRANSITION", raised.exception.code)
        stored = self.alice.task_status(task["id"])["task"]
        self.assertEqual("claimed", stored["state"])

    def test_report_collects_git_metadata_validates_schema_and_submits(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        commit = self.commit_alice_change()
        result = self.alice.submit_report(
            task["id"],
            summary="Implemented health endpoint.",
            validation=[
                {"command": "python -m unittest", "outcome": "passed", "summary": "24 passed"}
            ],
            knowledge_candidates=["Health checks stay deterministic."],
        )
        report = result["report"]
        validate("report", report)
        self.assertEqual(commit, report["commit"])
        self.assertEqual("worker-one", report["branch"])
        self.assertEqual(["health.py"], report["changed_files"])
        self.assertNotEqual(report["base_commit"], report["commit"])
        self.assertIn("health.py", report["diff_summary"])
        self.assertEqual("submitted", result["task"]["state"])
        self.assertTrue((self.runtime_root / "projects" / "apollo" / "reports" / f"{report['id']}.json").is_file())
        self.assertEqual("report.submitted", EventLog(self.runtime_root).read().events[-1]["type"])

    def test_same_task_commit_report_returns_original_without_duplicate_event(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        self.commit_alice_change()
        first = self.alice.submit_report(task["id"], summary="First summary")
        second = self.alice.submit_report(task["id"], summary="Different retry text")
        self.assertEqual(first["report"], second["report"])
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(1, sum(event["type"] == "report.submitted" for event in events))

    def test_wrong_report_commit_is_rejected(self) -> None:
        task = self.create_task()
        base = git(self.alice_worktree, "rev-parse", "HEAD")
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        self.commit_alice_change()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.submit_report(task["id"], commit=base)
        self.assertEqual("E_COMMIT_MISMATCH", raised.exception.code)

    def test_non_assignee_cannot_report(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        with self.assertRaises(TeamRuntimeError) as raised:
            self.bob.submit_report(task["id"])
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)

    def test_schema_invalid_report_validation_is_rejected_without_state_change(self) -> None:
        task = self.create_task()
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        self.commit_alice_change()
        with self.assertRaises(TeamRuntimeError) as raised:
            self.alice.submit_report(
                task["id"],
                validation=[{"command": "pytest", "outcome": "unknown", "summary": "bad"}],
            )
        self.assertEqual("E_VALIDATION_FAILED", raised.exception.code)
        self.assertEqual("in_progress", self.alice.task_status(task["id"])["task"]["state"])

    def test_task_status_and_question_list_are_read_only(self) -> None:
        task = self.create_task()
        question = self.add_blocking_question(task["id"])
        before = EventLog(self.runtime_root).read().events
        status = self.alice.task_status(task["id"])
        questions = self.alice.list_questions("Apollo")
        after = EventLog(self.runtime_root).read().events
        self.assertEqual(question["id"], status["blocking_questions"][0]["id"])
        self.assertEqual(question["id"], questions["questions"][0]["id"])
        self.assertEqual(before, after)

    def test_cli_member_flow_and_help(self) -> None:
        help_text = _parser().format_help()
        self.assertIn("claim", help_text)
        self.assertIn("report", help_text)
        task = self.create_task("CLI task")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(
                [
                    "claim",
                    "--project",
                    "apollo",
                    task["id"],
                    "--workspace",
                    os.fspath(self.alice_worktree),
                ]
            )
        self.assertEqual(0, code)
        self.assertEqual("claimed", json.loads(output.getvalue())["task"]["state"])


if __name__ == "__main__":
    unittest.main()
