from __future__ import annotations

import hashlib
import os
import unittest
import uuid
from pathlib import Path
from unittest import mock

from orbital_team.errors import TeamRuntimeError
from orbital_team.knowledge_workflow import KnowledgeWorkflow
from orbital_team.manager_integration import ManagerIntegrationWorkflow, job_id_for_report
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager, utc_now
from orbital_team.storage import EventLog, ProjectStore, atomic_write_json
from orbital_team.teamd import TeamDaemon

from tests.test_runtime_kernel import GitRepository, git, git_env


MEMORY_CONTENT = {
    "orbital/PROJECT_STATE.md": "# PROJECT_STATE\n\n- Initial project state.\n",
    "orbital/DECISIONS.md": "# DECISIONS\n\n- Initial decision.\n",
    "orbital/LESSONS.md": "# LESSONS\n\n- Initial lesson.\n",
    "orbital/INDEX.md": "# INDEX\n\n- tracked.txt — Fixture file.\n",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NoChangeKnowledgeRunner:
    agent_type = "test-knowledge-manager"
    phases = frozenset({"knowledge"})

    def __init__(self) -> None:
        self.calls = 0

    def run(self, request: dict[str, object], request_path: Path) -> None:
        if request["phase"] != "knowledge":
            raise AssertionError(f"unexpected runner phase: {request['phase']}")
        self.calls += 1
        proposal = KnowledgeWorkflow(str(request["workspace"])).propose(
            str(request["job_id"]),
            [],
            "No durable project knowledge change is needed.",
            request_id=f"fake-knowledge:{request['job_id']}",
        )["proposal"]
        result = {
            "changes_requested": [],
            "completed_at": utc_now(),
            "job_id": request["job_id"],
            "merge_commit": None,
            "open_question_ids": [],
            "outcome": "no_change",
            "proposal_id": proposal["id"],
            "risk_summary": None,
            "run_id": request["run_id"],
            "schema_version": request["schema_version"],
            "validation": [],
        }
        atomic_write_json(Path(str(request["result_path"])), result)


class KnowledgeWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, git_env(), clear=True)
        self.environment.start()
        self.repo = GitRepository()
        for relative, content in MEMORY_CONTENT.items():
            target = self.repo.repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        git(self.repo.repository, "add", "orbital")
        git(self.repo.repository, "commit", "-m", "add canonical memory fixture")

        self.manager = RuntimeManager(self.repo.repository)
        self.runtime_root = Path(self.manager.init_project("Apollo")["runtime_root"])
        self.alice_worktree, _ = self.repo.worktrees()
        self.manager_workflow = MemberWorkflow(self.repo.repository)
        self.alice = MemberWorkflow(self.alice_worktree)
        self.alice.join_member("apollo", "alice", "codex")
        self.integration = ManagerIntegrationWorkflow(self.repo.repository)
        self.knowledge = KnowledgeWorkflow(self.repo.repository)

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def prepare_awaiting_knowledge(
        self,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        task = self.manager_workflow.create_task(
            "apollo",
            "Add knowledge fixture feature",
            description="Add a source file that produces a knowledge candidate.",
            acceptance_criteria=["Feature is merged"],
            paths=["src/feature.py"],
        )["task"]
        task = self.manager_workflow.ready_task(task["id"])["task"]
        self.alice.claim("apollo", task["id"])
        self.alice.start_task(task["id"])
        source = self.alice_worktree / "src" / "feature.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("FEATURE_READY = True\n", encoding="utf-8")
        git(self.alice_worktree, "add", "src/feature.py")
        git(self.alice_worktree, "commit", "-m", "add knowledge fixture feature")
        report = self.alice.submit_report(
            task["id"],
            summary="Feature is ready and should be reflected in project memory.",
            validation=[
                {
                    "command": "fixture validation",
                    "outcome": "passed",
                    "summary": "fixture passed",
                }
            ],
            knowledge_candidates=["The fixture feature is available."],
        )["report"]
        job = self.integration.create_job(report["id"])["job"]
        run_id = f"apollo-RUN-{uuid.uuid4()}"
        job = self.integration.start_job(job["id"], run_id)["job"]
        expected_head = git(self.repo.repository, "rev-parse", "HEAD")
        job = self.integration.merge_job(
            job["id"],
            expected_head=expected_head,
            validation=[
                {
                    "command": "fixture validation",
                    "outcome": "passed",
                    "summary": "fixture passed",
                }
            ],
        )["job"]
        job = self.integration.prepare_knowledge_pack(job["id"])["job"]
        self.assertEqual("awaiting_knowledge", job["state"])
        return task, report, job

    def updated_patch(self, relative: str, content: str) -> dict[str, object]:
        target = self.repo.repository / relative
        return {
            "base_sha256": sha256(target),
            "content": content,
            "operation": "updated",
            "path": relative,
        }

    def tasks(self) -> dict[str, object]:
        return ProjectStore(
            self.runtime_root, "apollo", "tasks.json", "taskStore"
        ).read()["items"]

    def events(self) -> list[dict[str, object]]:
        return list(EventLog(self.runtime_root).read().events)

    def test_allowlisted_apply_creates_separate_commit_and_completes_job(self) -> None:
        task, report, job = self.prepare_awaiting_knowledge()
        source_commit = str(job["merge_commit"])
        content = "# PROJECT_STATE\n\n- The fixture feature is merged and available.\n"
        proposal = self.knowledge.propose(
            job["id"],
            [self.updated_patch("orbital/PROJECT_STATE.md", content)],
            "Record the merged fixture feature.",
        )["proposal"]

        result = self.knowledge.apply_proposal(proposal["id"])

        knowledge_commit = result["summary"]["knowledge_commit"]
        event_types = [event["type"] for event in self.events()]
        changed = git(
            self.repo.repository,
            "show",
            "--pretty=format:",
            "--name-only",
            str(knowledge_commit),
        ).splitlines()
        self.assertIsNotNone(knowledge_commit)
        self.assertNotEqual(source_commit, knowledge_commit)
        self.assertEqual(source_commit, git(self.repo.repository, "show", "-s", "--format=%P", str(knowledge_commit)))
        self.assertEqual(["orbital/PROJECT_STATE.md"], changed)
        self.assertEqual(content, (self.repo.repository / "orbital/PROJECT_STATE.md").read_text(encoding="utf-8"))
        self.assertEqual("done", result["job"]["state"])
        self.assertEqual("done", result["task"]["state"])
        self.assertEqual("done", self.tasks()[task["id"]]["state"])
        self.assertEqual(source_commit, result["summary"]["source_commit"])
        self.assertEqual(str(report["id"]), result["summary"]["report_id"])
        self.assertEqual("", git(self.repo.repository, "status", "--porcelain"))
        self.assertIn("knowledge.applied", event_types)
        self.assertIn("task.completed", event_types)
        self.assertEqual(1, event_types.count("integration.completed"))

    def test_no_change_completes_without_empty_commit(self) -> None:
        task, _, job = self.prepare_awaiting_knowledge()
        source_commit = str(job["merge_commit"])
        proposal = self.knowledge.propose(
            job["id"], [], "No durable project knowledge change is needed."
        )["proposal"]

        result = self.knowledge.apply_proposal(proposal["id"])

        self.assertEqual(source_commit, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertIsNone(result["summary"]["knowledge_commit"])
        self.assertEqual([], result["summary"]["changes"])
        self.assertEqual("done", result["job"]["state"])
        self.assertEqual("done", self.tasks()[task["id"]]["state"])
        self.assertEqual(1, [e["type"] for e in self.events()].count("integration.completed"))

    def test_dirty_workspace_blocks_knowledge_but_task_stays_integrating(self) -> None:
        task, _, job = self.prepare_awaiting_knowledge()
        source_commit = str(job["merge_commit"])
        proposal = self.knowledge.propose(
            job["id"],
            [
                self.updated_patch(
                    "orbital/PROJECT_STATE.md",
                    "# PROJECT_STATE\n\n- The fixture feature is now available.\n",
                )
            ],
            "Update current project state.",
        )["proposal"]
        (self.repo.repository / "scratch.txt").write_text(
            "unrelated local work\n", encoding="utf-8"
        )

        with self.assertRaises(TeamRuntimeError) as raised:
            self.knowledge.apply_proposal(proposal["id"])

        observed_job = self.integration.jobs.read(job["id"])
        observed_proposal = self.knowledge._proposal(proposal["id"])
        questions = ProjectStore(
            self.runtime_root,
            "apollo",
            "open-questions.json",
            "openQuestionStore",
        ).read()["items"]
        self.assertEqual("E_DIRTY_WORKSPACE", raised.exception.code)
        self.assertEqual(source_commit, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertEqual("blocked", observed_job["state"])
        self.assertEqual("knowledge", observed_job["block_kind"])
        self.assertEqual("blocked", observed_proposal["state"])
        self.assertEqual("integrating", self.tasks()[task["id"]]["state"])
        self.assertTrue(any(job["id"] in q["related"]["job_ids"] for q in questions.values()))
        self.assertNotIn("integration.completed", [e["type"] for e in self.events()])

    def test_changed_memory_baseline_marks_old_proposal_stale(self) -> None:
        task, _, job = self.prepare_awaiting_knowledge()
        proposal = self.knowledge.propose(
            job["id"],
            [
                self.updated_patch(
                    "orbital/PROJECT_STATE.md",
                    "# PROJECT_STATE\n\n- Proposed project state.\n",
                )
            ],
            "Propose a project state update.",
        )["proposal"]
        (self.repo.repository / "orbital/PROJECT_STATE.md").write_text(
            "# PROJECT_STATE\n\n- Concurrent human update.\n", encoding="utf-8"
        )

        with self.assertRaises(TeamRuntimeError) as raised:
            self.knowledge.validate_proposal(proposal["id"])

        self.assertEqual("E_STALE_PROPOSAL", raised.exception.code)
        self.assertEqual("stale", self.knowledge._proposal(proposal["id"])["state"])
        self.assertEqual("awaiting_knowledge", self.integration.jobs.read(job["id"])["state"])
        self.assertEqual("integrating", self.tasks()[task["id"]]["state"])
        self.assertIn("knowledge.stale", [e["type"] for e in self.events()])
        self.assertNotIn("integration.completed", [e["type"] for e in self.events()])

    def test_repeated_apply_is_idempotent(self) -> None:
        _, _, job = self.prepare_awaiting_knowledge()
        proposal = self.knowledge.propose(
            job["id"],
            [
                self.updated_patch(
                    "orbital/LESSONS.md",
                    "# LESSONS\n\n- Recovered knowledge apply is idempotent.\n",
                )
            ],
            "Record the apply idempotency lesson.",
        )["proposal"]

        first = self.knowledge.apply_proposal(proposal["id"], request_id="first")
        first_head = git(self.repo.repository, "rev-parse", "HEAD")
        second = self.knowledge.apply_proposal(proposal["id"], request_id="second")

        completed = [
            event
            for event in self.events()
            if event["type"] == "integration.completed"
            and event["data"]["job_id"] == job["id"]
        ]
        summaries = self.knowledge._summaries("apollo").list()
        self.assertEqual(first["summary"], second["summary"])
        self.assertEqual(first_head, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertEqual(1, len(summaries))
        self.assertEqual(1, len(completed))

    def test_crash_after_knowledge_commit_recovers_without_duplicate_commit(self) -> None:
        _, _, job = self.prepare_awaiting_knowledge()
        proposal = self.knowledge.propose(
            job["id"],
            [
                self.updated_patch(
                    "orbital/DECISIONS.md",
                    "# DECISIONS\n\n- The fixture feature is a settled project capability.\n",
                )
            ],
            "Record the settled fixture capability.",
        )["proposal"]

        with mock.patch.object(
            self.knowledge,
            "_finalize_apply",
            side_effect=RuntimeError("simulated crash after git commit"),
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                self.knowledge.apply_proposal(
                    proposal["id"], request_id="recoverable-apply"
                )

        committed_head = git(self.repo.repository, "rev-parse", "HEAD")
        self.assertEqual("validated", self.knowledge._proposal(proposal["id"])["state"])
        self.assertEqual("awaiting_knowledge", self.integration.jobs.read(job["id"])["state"])

        recovered = KnowledgeWorkflow(self.repo.repository).apply_proposal(
            proposal["id"], request_id="recoverable-apply"
        )

        matching_commits = git(
            self.repo.repository,
            "log",
            "--format=%H",
            "--fixed-strings",
            f"--grep=Knowledge proposal {proposal['id']}",
        ).splitlines()
        self.assertEqual(committed_head, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertEqual([committed_head], matching_commits)
        self.assertEqual(committed_head, recovered["summary"]["knowledge_commit"])
        self.assertEqual("done", recovered["job"]["state"])
        self.assertEqual(1, [e["type"] for e in self.events()].count("integration.completed"))

    def test_validation_rejects_disallowed_path_and_invalid_memory(self) -> None:
        _, _, job = self.prepare_awaiting_knowledge()
        state_hash = sha256(self.repo.repository / "orbital/PROJECT_STATE.md")
        disallowed = self.knowledge.propose(
            job["id"],
            [
                {
                    "base_sha256": None,
                    "content": "# Instructions\n",
                    "operation": "created",
                    "path": "orbital/instructions/generated.md",
                }
            ],
            "Attempt an out-of-scope memory write.",
        )["proposal"]
        with self.assertRaises(TeamRuntimeError) as disallowed_error:
            self.knowledge.validate_proposal(disallowed["id"])
        self.assertEqual("E_GUARDRAIL_VIOLATION", disallowed_error.exception.code)

        invalid = self.knowledge.propose(
            job["id"],
            [
                {
                    "base_sha256": state_hash,
                    "content": "Missing required heading and final newline",
                    "operation": "updated",
                    "path": "orbital/PROJECT_STATE.md",
                }
            ],
            "Attempt invalid canonical memory content.",
        )["proposal"]
        with self.assertRaises(TeamRuntimeError) as invalid_error:
            self.knowledge.validate_proposal(invalid["id"])
        self.assertEqual("E_VALIDATION_FAILED", invalid_error.exception.code)
        self.assertEqual("awaiting_knowledge", self.integration.jobs.read(job["id"])["state"])
        self.assertNotIn("integration.completed", [e["type"] for e in self.events()])

    def test_teamd_drives_injected_knowledge_runner_end_to_end_once(self) -> None:
        task, _, job = self.prepare_awaiting_knowledge()
        project_store = ProjectStore(
            self.runtime_root, "apollo", "project.json", "project"
        )

        def select_runner(project: dict[str, object]) -> None:
            project["runner"] = "knowledge-fake"
            project["revision"] = int(project["revision"]) + 1

        project_store.update(select_runner)
        runner = NoChangeKnowledgeRunner()
        daemon = TeamDaemon(
            self.repo.repository, runners={"knowledge-fake": runner}
        )

        summary = daemon.run_once()
        daemon.run_once()

        completed = [
            event
            for event in self.events()
            if event["type"] == "integration.completed"
            and event["data"]["job_id"] == job["id"]
        ]
        self.assertEqual(1, runner.calls)
        self.assertEqual(1, summary["knowledge_started"])
        self.assertEqual(1, summary["knowledge_applied"])
        self.assertEqual("done", daemon.workflow.jobs.read(job["id"])["state"])
        self.assertEqual("done", self.tasks()[task["id"]]["state"])
        self.assertEqual(1, len(completed))


if __name__ == "__main__":
    unittest.main()
