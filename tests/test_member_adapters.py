from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.errors import TeamRuntimeError
from orbital_team.member_adapter import (
    MAX_SESSION_SUMMARY_BYTES,
    dispatch_team_command,
    parse_team_command,
    session_start_summary,
)
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager
from orbital_team.storage import EventLog, ProjectStore, RunRecordStore, private_mode

from tests.test_runtime_kernel import GitRepository, git, git_env


SOURCE_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = (
    SOURCE_ROOT / "skills" / "orbital-team-member" / "scripts" / "install_adapter.py"
)
CLAUDE_HOOK = (
    SOURCE_ROOT
    / "skills"
    / "orbital-team-member"
    / "assets"
    / "claude-code"
    / "hooks"
    / "orbital_team_session_start.py"
)


class MemberAdapterTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def create_task(self, title: str = "Add health endpoint") -> dict[str, object]:
        task = self.manager_workflow.create_task(
            "apollo",
            title,
            description="Implement the adapter fixture.",
            acceptance_criteria=["fixture passes"],
            paths=["adapter_fixture.py"],
        )["task"]
        return self.manager_workflow.ready_task(task["id"])["task"]

    def tasks(self) -> dict[str, object]:
        return ProjectStore(
            self.runtime_root, "apollo", "tasks.json", "taskStore"
        ).read()["items"]

    def test_slash_parser_maps_all_frozen_commands(self) -> None:
        cases = {
            "/team claim Apollo add health endpoint": (
                "claim",
                "--project",
                "Apollo",
                "--query",
                "add health endpoint",
            ),
            "/team start apollo-T-0001": ("task", "start", "apollo-T-0001"),
            "/team report apollo-T-0001 --summary 'done now' --risk 'migration risk'": (
                "report",
                "submit",
                "apollo-T-0001",
                "--summary",
                "done now",
                "--risk",
                "migration risk",
            ),
            "/team block apollo-T-0001 waiting for API approval": (
                "task",
                "block",
                "apollo-T-0001",
                "--reason",
                "waiting for API approval",
            ),
            "/team status": ("task", "status"),
            "/team status apollo-T-0001": ("task", "status", "apollo-T-0001"),
            "/team questions Apollo": ("question", "list", "--project", "Apollo"),
            "/team manager": ("manager", "inbox"),
            "/team manager inbox Apollo": ("manager", "inbox", "--project", "Apollo"),
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(expected, parse_team_command(text).cli_argv)

    def test_parser_rejects_actor_member_and_workspace_spoofing(self) -> None:
        commands = (
            "/team claim Apollo health --member bob",
            "/team status --actor member:bob",
            "/team questions Apollo --workspace /tmp/other",
        )
        for text in commands:
            with self.subTest(text=text), self.assertRaises(TeamRuntimeError) as raised:
                parse_team_command(text)
            self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)

    def test_dispatch_uses_argv_shell_false_and_protected_environment(self) -> None:
        observed: dict[str, object] = {}

        def fake_executor(argv, **kwargs):
            observed["argv"] = argv
            observed.update(kwargs)
            return subprocess.CompletedProcess(argv, 0, '{"ok":true}\n', "")

        result = dispatch_team_command(
            "/team claim Apollo 'add health endpoint'",
            self.alice_worktree,
            executor=fake_executor,
        )
        argv = observed["argv"]
        self.assertEqual(0, result.returncode)
        self.assertNotIn("shell", observed)
        self.assertNotIn("--member", argv)
        self.assertEqual("/dev/null", observed["env"]["GIT_CONFIG_GLOBAL"])
        self.assertEqual("/dev/null", observed["env"]["GIT_CONFIG_SYSTEM"])
        self.assertEqual(os.fspath(self.alice_worktree.resolve()), argv[-1])

    def test_real_fallback_claim_derives_alice_actor_from_worktree(self) -> None:
        task = self.create_task()

        result = dispatch_team_command(
            f"/team claim Apollo {task['id']}", self.alice_worktree
        )

        payload = json.loads(result.stdout)
        events = EventLog(self.runtime_root).read().events
        claimed = next(event for event in events if event["type"] == "task.claimed")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("alice", payload["task"]["assignee"])
        self.assertEqual("member:alice", claimed["actor"])

    def test_other_worktree_cannot_start_or_spoof_assignee(self) -> None:
        task = self.create_task()
        dispatch_team_command(f"/team claim Apollo {task['id']}", self.alice_worktree)
        before = self.tasks()[task["id"]]

        forbidden = dispatch_team_command(
            f"/team start {task['id']}", self.bob_worktree
        )
        with self.assertRaises(TeamRuntimeError) as spoofed:
            parse_team_command(f"/team start {task['id']} --member alice")

        self.assertEqual(5, forbidden.returncode)
        self.assertEqual("E_FORBIDDEN_ACTOR", json.loads(forbidden.stderr)["error"]["code"])
        self.assertEqual("E_FORBIDDEN_ACTOR", spoofed.exception.code)
        self.assertEqual(before, self.tasks()[task["id"]])

    def test_report_requires_start_then_uses_bound_commit_and_actor(self) -> None:
        task = self.create_task()
        dispatch_team_command(f"/team claim Apollo {task['id']}", self.alice_worktree)
        target = self.alice_worktree / "adapter_fixture.py"
        target.write_text("READY = True\n", encoding="utf-8")
        git(self.alice_worktree, "add", "adapter_fixture.py")
        git(self.alice_worktree, "commit", "-m", "implement adapter fixture")

        skipped = dispatch_team_command(
            f"/team report {task['id']} --summary 'fixture ready'", self.alice_worktree
        )
        self.assertEqual(4, skipped.returncode)
        self.assertEqual("E_INVALID_TRANSITION", json.loads(skipped.stderr)["error"]["code"])

        self.assertEqual(
            0,
            dispatch_team_command(f"/team start {task['id']}", self.alice_worktree).returncode,
        )
        validation = json.dumps(
            {"command": "fixture check", "outcome": "passed", "summary": "passed"}
        )
        reported = dispatch_team_command(
            f"/team report {task['id']} --summary 'fixture ready' "
            f"--validation {shlex_quote(validation)} --knowledge-candidate 'adapter mapping' "
            "--risk none",
            self.alice_worktree,
        )
        payload = json.loads(reported.stdout)
        self.assertEqual(0, reported.returncode, reported.stderr)
        self.assertEqual("member:alice", payload["report"]["submitted_by"])
        self.assertEqual("passed", payload["report"]["validation"][0]["outcome"])

    def test_session_start_is_bounded_idempotent_and_never_claims(self) -> None:
        task = self.create_task()
        dispatch_team_command(f"/team claim Apollo {task['id']}", self.alice_worktree)
        before = self.tasks()
        transcript = self.repo.root / "claude-transcript.jsonl"
        transcript.write_text("{}\n", encoding="utf-8")
        hook_input = {
            "hook_event_name": "SessionStart",
            "session_id": "claude-session-001",
            "source": "startup",
            "transcript_path": os.fspath(transcript),
        }

        first = session_start_summary(
            self.alice_worktree, hook_input, provider="claude-code"
        )
        second = session_start_summary(
            self.alice_worktree, hook_input, provider="claude-code"
        )

        runs = RunRecordStore(self.runtime_root, "apollo").list()
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(first, second)
        self.assertLessEqual(len(first.encode("utf-8")), MAX_SESSION_SUMMARY_BYTES)
        self.assertIn("member:alice", first)
        self.assertIn(str(task["id"]), first)
        self.assertEqual(before, self.tasks())
        self.assertEqual(1, len(runs))
        self.assertEqual("member:alice", runs[0]["actor"])
        self.assertEqual(task["id"], runs[0]["task_id"])
        self.assertEqual("claude-session-001", runs[0]["provider_session_id"])
        self.assertEqual(os.fspath(transcript), runs[0]["log_paths"]["transcript"])
        self.assertEqual(1, sum(event["type"] == "run.started" for event in events))
        self.assertEqual(0o600, private_mode(RunRecordStore(self.runtime_root, "apollo").root / runs[0]["id"] / "stdout.log"))

    def test_session_start_without_join_only_prints_join_guidance(self) -> None:
        task = self.create_task()
        before = self.tasks()

        summary = session_start_summary(
            self.repo.repository,
            {"session_id": "unjoined-manager-session", "source": "startup"},
            provider="claude-code",
        )

        self.assertIn("no joined member identity", summary)
        self.assertIn("no task was claimed", summary)
        self.assertEqual(before, self.tasks())

    def test_claude_session_start_hook_entrypoint_accepts_provider_json(self) -> None:
        task = self.create_task()
        dispatch_team_command(f"/team claim Apollo {task['id']}", self.alice_worktree)
        environment = git_env()
        environment["PYTHONPATH"] = os.fspath(SOURCE_ROOT / "src")
        result = subprocess.run(
            [
                sys.executable,
                os.fspath(CLAUDE_HOOK),
                "--workspace",
                os.fspath(self.alice_worktree),
            ],
            input=json.dumps(
                {
                    "hook_event_name": "SessionStart",
                    "session_id": "claude-hook-fixture",
                    "source": "startup",
                }
            ),
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("member:alice", result.stdout)
        self.assertIn(str(task["id"]), result.stdout)
        runs = RunRecordStore(self.runtime_root, "apollo").list()
        self.assertEqual("claude-hook-fixture", runs[0]["provider_session_id"])

    def test_claude_copy_install_and_uninstall_preserve_other_settings(self) -> None:
        target = self.repo.root / "claude-install"
        settings = target / ".claude" / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text('{"permissions":{"allow":[]}}\n', encoding="utf-8")

        installed = subprocess.run(
            [
                sys.executable,
                os.fspath(INSTALLER),
                "--agent",
                "claude-code",
                "--target",
                os.fspath(target),
                "--mode",
                "copy",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        configured = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual("claude-code", json.loads(installed.stdout)["agent"])
        self.assertTrue((target / ".claude/commands/team.md").is_file())
        self.assertTrue((target / ".claude/hooks/orbital_team_session_start.py").is_file())
        self.assertTrue((target / ".claude/skills/orbital-team-member/SKILL.md").is_file())
        self.assertEqual(1, len(configured["hooks"]["SessionStart"]))

        subprocess.run(
            [
                sys.executable,
                os.fspath(INSTALLER),
                "--agent",
                "claude-code",
                "--target",
                os.fspath(target),
                "--uninstall",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        remaining = json.loads(settings.read_text(encoding="utf-8"))
        self.assertEqual({"permissions": {"allow": []}}, remaining)
        self.assertFalse((target / ".claude/commands/team.md").exists())

    def test_generic_link_install_is_agent_neutral_and_reversible(self) -> None:
        target = self.repo.root / "generic-install"
        subprocess.run(
            [
                sys.executable,
                os.fspath(INSTALLER),
                "--agent",
                "generic",
                "--target",
                os.fspath(target),
                "--mode",
                "link",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        link = target / ".agents/skills/orbital-team-member"
        self.assertTrue(link.is_symlink())
        self.assertTrue((link / "SKILL.md").is_file())

        subprocess.run(
            [
                sys.executable,
                os.fspath(INSTALLER),
                "--agent",
                "generic",
                "--target",
                os.fspath(target),
                "--uninstall",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertFalse(link.exists())
        self.assertFalse(link.is_symlink())


def shlex_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


if __name__ == "__main__":
    unittest.main()
