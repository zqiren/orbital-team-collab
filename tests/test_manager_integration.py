from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.errors import TeamRuntimeError
from orbital_team.manager_integration import job_id_for_report
from orbital_team.manager_proc import integrate
from orbital_team.manager_runner import (
    CommandManagerRunner,
    RunnerSupervisor,
    assert_policy_guardrails,
)
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager
from orbital_team.storage import EventLog, ProjectStore, atomic_write_json
from orbital_team.storage import private_mode, read_json
from orbital_team.teamd import TeamDaemon

from tests.test_runtime_kernel import GitRepository, git, git_env


PASS_VALIDATION = [sys.executable, "-c", "raise SystemExit(0)"]
FAIL_VALIDATION = [sys.executable, "-c", "raise SystemExit(1)"]
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"


class ScriptedRunner:
    """In-process deterministic runner used to observe daemon serialization."""

    agent_type = "test-scripted-manager"

    def __init__(self, workflow) -> None:
        self.workflow = workflow
        self.calls: list[str] = []

    def run(self, request: dict[str, object], request_path: Path) -> None:
        running = [
            job
            for job in self.workflow.jobs.list(request["project_slug"])
            if job["state"] == "running"
        ]
        if len(running) != 1 or running[0]["id"] != request["job_id"]:
            raise AssertionError(f"integration slot was not serialized: {running!r}")
        self.calls.append(str(request["job_id"]))
        with mock.patch.dict(
            os.environ, {"PYTHONPATH": os.fspath(SOURCE_ROOT)}, clear=False
        ):
            result = integrate(request)
        atomic_write_json(Path(str(request["result_path"])), result)


class CrashRunner:
    agent_type = "test-crashing-manager"

    def run(self, request: dict[str, object], request_path: Path) -> None:
        raise RuntimeError("simulated runner process crash")


class MergeThenCrashRunner:
    """Crash after the controlled merge persisted, before result.json exists."""

    agent_type = "test-post-merge-crash"

    def run(self, request: dict[str, object], request_path: Path) -> None:
        with mock.patch.dict(
            os.environ, {"PYTHONPATH": os.fspath(SOURCE_ROOT)}, clear=False
        ):
            integrate(request)
        raise RuntimeError("simulated crash after controlled merge")


class ManagerIntegrationTests(unittest.TestCase):
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
        self.bob.join_member("apollo", "bob", "claude-code")
        self.set_runner("builtin")

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def set_runner(self, runner: str) -> None:
        store = ProjectStore(
            self.runtime_root, "apollo", "project.json", "project"
        )

        def update(project: dict[str, object]) -> None:
            project["runner"] = runner
            project["revision"] = int(project["revision"]) + 1

        store.update(update)

    def create_submitted_report(
        self,
        member: MemberWorkflow,
        *,
        title: str,
        filename: str,
        content: str,
    ) -> tuple[dict[str, object], dict[str, object]]:
        task = self.manager_workflow.create_task(
            "apollo",
            title,
            description=f"Implement {title}.",
            acceptance_criteria=[f"{filename} is committed"],
            paths=[filename],
        )["task"]
        task = self.manager_workflow.ready_task(task["id"])["task"]
        member.claim("apollo", task["id"])
        member.start_task(task["id"])
        target = member.paths.repository_root / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        git(member.paths.repository_root, "add", filename)
        git(member.paths.repository_root, "commit", "-m", title)
        report = member.submit_report(
            task["id"],
            summary=title,
            validation=[
                {
                    "command": "fixture validation",
                    "outcome": "passed",
                    "summary": "fixture passed before submission",
                }
            ],
        )["report"]
        return task, report

    def builtin_daemon(self, *, validation_argv=None) -> TeamDaemon:
        runner = CommandManagerRunner(
            [sys.executable, "-m", "orbital_team.manager_proc"],
            agent_type="builtin-scripted-manager",
        )
        return TeamDaemon(
            self.repo.repository,
            runners={"builtin": runner},
            validation_argv=validation_argv or PASS_VALIDATION,
        )

    def tasks(self) -> dict[str, object]:
        return ProjectStore(
            self.runtime_root, "apollo", "tasks.json", "taskStore"
        ).read()["items"]

    def events(self) -> list[dict[str, object]]:
        return list(EventLog(self.runtime_root).read().events)

    def test_report_event_drives_builtin_runner_to_real_clean_merge(self) -> None:
        task, report = self.create_submitted_report(
            self.alice,
            title="Add health module",
            filename="src/health.py",
            content="def health():\n    return 200\n",
        )
        report_commit = str(report["commit"])
        original_head = git(self.repo.repository, "rev-parse", "HEAD")

        summary = self.builtin_daemon().run_once()

        job_id = job_id_for_report("apollo", str(report["id"]))
        job = self.builtin_daemon().workflow.jobs.read(job_id)
        merged_head = git(self.repo.repository, "rev-parse", "HEAD")
        parents = git(self.repo.repository, "rev-list", "--parents", "-n", "1", merged_head).split()
        event_types = [event["type"] for event in self.events()]
        run = RunnerSupervisor(self.builtin_daemon().workflow).read_run(
            "apollo", str(job["run_id"])
        )

        self.assertEqual("awaiting_knowledge", job["state"])
        self.assertEqual(merged_head, job["merge_commit"])
        self.assertEqual([merged_head, original_head, report_commit], parents)
        self.assertEqual("integrating", self.tasks()[task["id"]]["state"])
        self.assertEqual("succeeded", run["state"])
        self.assertGreaterEqual(summary["jobs_started"], 1)
        self.assertIn("integration.merged", event_types)
        self.assertIn("knowledge.prepared", event_types)
        self.assertNotIn("integration.completed", event_types)

    def test_replayed_report_does_not_duplicate_job_merge_or_event(self) -> None:
        _, report = self.create_submitted_report(
            self.alice,
            title="Add retry helper",
            filename="src/retry.py",
            content="def retry():\n    return True\n",
        )
        daemon = self.builtin_daemon()
        daemon.run_once()
        job_id = job_id_for_report("apollo", str(report["id"]))
        first_job = daemon.workflow.jobs.read(job_id)
        first_head = git(self.repo.repository, "rev-parse", "HEAD")

        daemon._cursor_path.unlink()
        TeamDaemon(
            self.repo.repository,
            runners={"builtin": daemon.runners["builtin"]},
            validation_argv=PASS_VALIDATION,
        ).run_once()

        jobs = daemon.workflow.jobs.list("apollo")
        merged_events = [
            event
            for event in self.events()
            if event["type"] == "integration.merged"
            and event["data"]["job_id"] == job_id
        ]
        self.assertEqual(1, len(jobs))
        self.assertEqual(first_job, jobs[0])
        self.assertEqual(first_head, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertEqual(1, len(merged_events))

    def test_failed_validation_requests_changes_and_never_marks_done(self) -> None:
        task, report = self.create_submitted_report(
            self.alice,
            title="Add invalid endpoint",
            filename="src/invalid.py",
            content="BROKEN = True\n",
        )
        original_head = git(self.repo.repository, "rev-parse", "HEAD")

        self.builtin_daemon(validation_argv=FAIL_VALIDATION).run_once()

        job = self.builtin_daemon().workflow.jobs.read(
            job_id_for_report("apollo", str(report["id"]))
        )
        event_types = [event["type"] for event in self.events()]
        self.assertEqual("changes_requested", job["state"])
        self.assertEqual("changes_requested", self.tasks()[task["id"]]["state"])
        self.assertEqual(original_head, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertIn("integration.changes_requested", event_types)
        self.assertNotIn("integration.merged", event_types)
        self.assertNotIn("integration.completed", event_types)

    def test_merge_conflict_is_blocked_and_task_is_not_done(self) -> None:
        task, report = self.create_submitted_report(
            self.alice,
            title="Change tracked file in member branch",
            filename="tracked.txt",
            content="member version\n",
        )
        (self.repo.repository / "tracked.txt").write_text(
            "canonical version\n", encoding="utf-8"
        )
        git(self.repo.repository, "add", "tracked.txt")
        git(self.repo.repository, "commit", "-m", "conflicting canonical change")
        canonical_head = git(self.repo.repository, "rev-parse", "HEAD")

        self.builtin_daemon().run_once()

        job = self.builtin_daemon().workflow.jobs.read(
            job_id_for_report("apollo", str(report["id"]))
        )
        questions = ProjectStore(
            self.runtime_root,
            "apollo",
            "open-questions.json",
            "openQuestionStore",
        ).read()["items"]
        event_types = [event["type"] for event in self.events()]
        self.assertEqual("blocked", job["state"])
        self.assertEqual("integration", job["block_kind"])
        self.assertEqual("blocked", self.tasks()[task["id"]]["state"])
        self.assertNotEqual("done", self.tasks()[task["id"]]["state"])
        self.assertEqual(canonical_head, git(self.repo.repository, "rev-parse", "HEAD"))
        self.assertTrue(any(job["id"] in q["related"]["job_ids"] for q in questions.values()))
        self.assertIn("integration.blocked", event_types)
        self.assertNotIn("integration.completed", event_types)

    def test_runner_crash_is_retryable_and_new_daemon_resumes_from_files(self) -> None:
        _, report = self.create_submitted_report(
            self.alice,
            title="Add crash recovery module",
            filename="src/recover.py",
            content="RECOVERED = True\n",
        )
        self.set_runner("crashy")
        first_daemon = TeamDaemon(
            self.repo.repository,
            runners={"crashy": CrashRunner()},
            validation_argv=PASS_VALIDATION,
        )

        first_daemon.tick()

        job_id = job_id_for_report("apollo", str(report["id"]))
        crashed = first_daemon.workflow.jobs.read(job_id)
        self.assertEqual("retryable", crashed["state"])
        self.assertEqual(1, crashed["attempt"])
        first_run = RunnerSupervisor(first_daemon.workflow).read_run(
            "apollo", str(crashed["run_id"])
        )
        self.assertEqual("failed", first_run["state"])

        replacement = CommandManagerRunner(
            [sys.executable, "-m", "orbital_team.manager_proc"],
            agent_type="builtin-scripted-manager",
        )
        TeamDaemon(
            self.repo.repository,
            runners={"crashy": replacement},
            validation_argv=PASS_VALIDATION,
        ).run_once()

        recovered = first_daemon.workflow.jobs.read(job_id)
        event_types = [event["type"] for event in self.events()]
        self.assertEqual("awaiting_knowledge", recovered["state"])
        self.assertEqual(2, recovered["attempt"])
        self.assertNotEqual(crashed["run_id"], recovered["run_id"])
        self.assertIn("integration.retryable", event_types)
        self.assertIn("integration.requeued", event_types)
        self.assertIn("integration.merged", event_types)

    def test_two_reports_are_integrated_serially_in_submission_order(self) -> None:
        first_task, first_report = self.create_submitted_report(
            self.alice,
            title="Add first module",
            filename="src/first.py",
            content="FIRST = True\n",
        )
        second_task, second_report = self.create_submitted_report(
            self.bob,
            title="Add second module",
            filename="src/second.py",
            content="SECOND = True\n",
        )
        self.set_runner("recording")
        daemon = TeamDaemon(
            self.repo.repository,
            runners={},
            validation_argv=PASS_VALIDATION,
        )
        runner = ScriptedRunner(daemon.workflow)
        daemon.runners["recording"] = runner

        daemon.run_once()

        first_job_id = job_id_for_report("apollo", str(first_report["id"]))
        second_job_id = job_id_for_report("apollo", str(second_report["id"]))
        jobs = {job["id"]: job for job in daemon.workflow.jobs.list("apollo")}
        started = [
            event["data"]["job_id"]
            for event in self.events()
            if event["type"] == "integration.started"
        ]
        self.assertEqual([first_job_id, second_job_id], runner.calls)
        self.assertEqual([first_job_id, second_job_id], started)
        self.assertEqual("awaiting_knowledge", jobs[first_job_id]["state"])
        self.assertEqual("awaiting_knowledge", jobs[second_job_id]["state"])
        self.assertEqual("integrating", self.tasks()[first_task["id"]]["state"])
        self.assertEqual("integrating", self.tasks()[second_task["id"]]["state"])
        self.assertFalse(daemon.workflow.occupying_jobs("apollo"))

    def test_runner_policy_guardrail_rejects_raw_git_mutations(self) -> None:
        for subcommand in ("merge", "commit", "push"):
            with self.subTest(subcommand=subcommand):
                with self.assertRaises(TeamRuntimeError) as raised:
                    assert_policy_guardrails(
                        [
                            {
                                "allow_additional_args": True,
                                "argv_prefix": ["git", subcommand],
                                "cwd_scope": "canonical_workspace",
                                "id": f"raw-{subcommand}",
                            }
                        ]
                    )
                self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)

        policies = RunnerSupervisor(self.builtin_daemon().workflow).build_policies(
            PASS_VALIDATION
        )
        self.assertTrue(any(policy["id"] == "manager-merge" for policy in policies))
        self.assertFalse(
            any(
                Path(policy["argv_prefix"][0]).name == "git"
                and any(
                    token in {"merge", "commit", "push"}
                    for token in policy["argv_prefix"][1:]
                )
                for policy in policies
            )
        )

    def test_run_brief_contains_task_contract_and_private_inputs(self) -> None:
        task, report = self.create_submitted_report(
            self.alice,
            title="Add task-aware review",
            filename="src/task_review.py",
            content="TASK_AWARE = True\n",
        )
        daemon = self.builtin_daemon()
        job = daemon.workflow.create_job(str(report["id"]))["job"]
        context = RunnerSupervisor(daemon.workflow).prepare_run(
            job, validation_argv=PASS_VALIDATION
        )

        brief_path = Path(context.request["brief_path"])
        task_path = Path(context.request["input_paths"]["task"])
        brief = brief_path.read_text(encoding="utf-8")
        task_snapshot = read_json(task_path)
        context_snapshot = read_json(Path(context.request["input_paths"]["context"]))

        self.assertIn("## Task contract", brief)
        self.assertIn("src/task_review.py is committed", brief)
        self.assertEqual(task["id"], task_snapshot["id"])
        self.assertEqual(task["acceptance_criteria"], context_snapshot["task"]["acceptance_criteria"])
        if os.name == "posix":
            for private_file in (
                brief_path,
                task_path,
                context.request_path,
                Path(context.request["input_paths"]["context"]),
            ):
                self.assertEqual(0o600, private_mode(private_file), private_file.name)

    def test_runner_environment_cannot_override_git_protections(self) -> None:
        for variable in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "HOME", "PYTHONPATH"):
            with self.subTest(variable=variable):
                with self.assertRaises(TeamRuntimeError) as raised:
                    CommandManagerRunner(
                        [sys.executable, "-c", "raise SystemExit(0)"],
                        extra_env={variable: "unsafe"},
                    )
                self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)

    @unittest.skipUnless(os.name == "posix", "process-group termination is POSIX-specific")
    def test_runner_timeout_kills_spawned_process_group(self) -> None:
        marker = self.repo.root / "orphan-child-finished"
        child_code = (
            "import pathlib,time; time.sleep(1.5); "
            f"pathlib.Path({os.fspath(marker)!r}).write_text('orphaned')"
        )
        parent_code = (
            "import subprocess,sys,time; "
            f"subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
            "time.sleep(30)"
        )
        run_dir = self.repo.root / "timeout-run"
        run_dir.mkdir()
        request_path = run_dir / "request.json"
        atomic_write_json(request_path, {})
        request = {
            "input_paths": {
                "stderr_log": os.fspath(run_dir / "stderr.log"),
                "stdout_log": os.fspath(run_dir / "stdout.log"),
            },
            "timeout_seconds": 1,
            "workspace": os.fspath(self.repo.repository),
        }
        runner = CommandManagerRunner([sys.executable, "-c", parent_code])

        with self.assertRaises(TeamRuntimeError) as raised:
            runner.run(request, request_path)
        self.assertEqual("E_RUNNER_TIMEOUT", raised.exception.code)
        time.sleep(1.0)
        self.assertFalse(marker.exists())

    def test_partial_job_creation_is_reconciled_after_restart(self) -> None:
        task, report = self.create_submitted_report(
            self.alice,
            title="Add transaction recovery",
            filename="src/transaction_recovery.py",
            content="RECOVER_PARTIAL = True\n",
        )
        daemon = self.builtin_daemon()
        with mock.patch.object(
            daemon.workflow,
            "_tasks_write",
            side_effect=RuntimeError("crash after Job persistence"),
        ):
            with self.assertRaises(RuntimeError):
                daemon.workflow.create_job(str(report["id"]))

        job_id = job_id_for_report("apollo", str(report["id"]))
        self.assertEqual("queued", daemon.workflow.jobs.read(job_id)["state"])
        self.assertEqual("submitted", self.tasks()[task["id"]]["state"])

        summary = self.builtin_daemon().run_once()

        recovered = daemon.workflow.jobs.read(job_id)
        queued_events = [
            event for event in self.events()
            if event["type"] == "integration.queued"
            and event["data"]["job_id"] == job_id
        ]
        self.assertGreaterEqual(summary["reconciled"], 1)
        self.assertEqual("awaiting_knowledge", recovered["state"])
        self.assertEqual("integrating", self.tasks()[task["id"]]["state"])
        self.assertEqual(1, len(queued_events))

    def test_post_merge_runner_crash_never_remerges_bound_commit(self) -> None:
        _, report = self.create_submitted_report(
            self.alice,
            title="Add post-merge recovery",
            filename="src/post_merge.py",
            content="POST_MERGE = True\n",
        )
        self.set_runner("post-merge-crash")
        daemon = TeamDaemon(
            self.repo.repository,
            runners={"post-merge-crash": MergeThenCrashRunner()},
            validation_argv=PASS_VALIDATION,
        )

        daemon.run_once()

        job_id = job_id_for_report("apollo", str(report["id"]))
        job = daemon.workflow.jobs.read(job_id)
        merged_events = [
            event for event in self.events()
            if event["type"] == "integration.merged"
            and event["data"]["job_id"] == job_id
        ]
        self.assertEqual("awaiting_knowledge", job["state"])
        self.assertEqual(1, len(merged_events))
        self.assertFalse(any(event["type"] == "integration.retryable" for event in self.events()))


if __name__ == "__main__":
    unittest.main()
