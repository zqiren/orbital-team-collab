from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from orbital_team.cli import main as cli_main
from orbital_team.constants import PRIVATE_DIR_MODE, PRIVATE_FILE_MODE, STORE_SCHEMAS
from orbital_team.errors import TeamRuntimeError
from orbital_team.models import Event
from orbital_team.paths import resolve_runtime_paths
from orbital_team.runtime import RuntimeManager, utc_now
from orbital_team.schema import validate
from orbital_team.storage import (
    EventLog,
    IdempotencyGuard,
    ProjectStore,
    RegistryStore,
    RuntimeLock,
    append_private_text,
    atomic_write_json,
    private_mode,
    read_json,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEMO_SEED = REPOSITORY_ROOT / "demo" / "seed"


def git_env() -> dict[str, str]:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return environment


def git(repository: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", os.fspath(repository), *args],
        check=True,
        capture_output=True,
        text=True,
        env=git_env(),
    ).stdout.strip()


class GitRepository:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        git(self.repository, "init", "-b", "main")
        git(self.repository, "config", "user.name", "Runtime Test")
        git(self.repository, "config", "user.email", "runtime@example.invalid")
        (self.repository / "tracked.txt").write_text("keep\n", encoding="utf-8")
        git(self.repository, "add", "tracked.txt")
        git(self.repository, "commit", "-m", "test fixture")

    def worktrees(self) -> tuple[Path, Path]:
        first = self.root / "worktree-one"
        second = self.root / "worktree-two"
        git(self.repository, "worktree", "add", "-b", "worker-one", os.fspath(first))
        git(self.repository, "worktree", "add", "-b", "worker-two", os.fspath(second))
        return first, second

    def close(self) -> None:
        self.temporary.cleanup()


class RuntimeKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, git_env(), clear=True)
        self.environment.start()
        self.repo = GitRepository()

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def manager(self) -> RuntimeManager:
        return RuntimeManager(self.repo.repository)

    @staticmethod
    def event(index: int, *, key: str | None = None, event_id: str | None = None) -> Event:
        return Event(
            actor="system:fixture",
            data={"index": index},
            id=event_id or str(uuid.uuid4()),
            idempotency_key=key or f"test:event:{index}",
            project_slug="apollo",
            schema_version="1.0",
            timestamp=utc_now(),
            type="task.created",
        )

    def test_non_git_workspace_is_rejected(self) -> None:
        outside = self.repo.root / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(TeamRuntimeError, "Git worktree") as raised:
            resolve_runtime_paths(outside)
        self.assertEqual("E_NOT_GIT_REPO", raised.exception.code)

    def test_resolver_uses_one_common_directory_for_two_worktrees(self) -> None:
        first, second = self.repo.worktrees()
        manager_paths = resolve_runtime_paths(self.repo.repository)
        first_paths = resolve_runtime_paths(first)
        second_paths = resolve_runtime_paths(second)
        self.assertEqual(manager_paths.git_common_dir, first_paths.git_common_dir)
        self.assertEqual(first_paths.git_common_dir, second_paths.git_common_dir)
        self.assertEqual(manager_paths.runtime_root, first_paths.runtime_root)
        self.assertEqual(first_paths.runtime_root, second_paths.runtime_root)

    def test_init_creates_complete_schema_valid_runtime(self) -> None:
        result = self.manager().init_project("Apollo")
        self.assertTrue(result["created"])
        root = Path(result["runtime_root"])
        expected_global = [
            ".runtime-marker.json",
            "registry.json",
            "events.jsonl",
            "locks",
            "consumers",
            "jobs",
        ]
        for relative in expected_global:
            self.assertTrue((root / relative).exists(), relative)
        project_root = root / "projects" / "apollo"
        for filename in ["project.json", *STORE_SCHEMAS]:
            self.assertTrue((project_root / filename).is_file(), filename)
        for directory in (
            "operations",
            "reports",
            "integrations",
            "knowledge-packs",
            "knowledge-proposals",
            "knowledge-summaries",
            "runs",
        ):
            self.assertTrue((project_root / directory).is_dir(), directory)
        validate("registry", read_json(root / "registry.json"))
        validate("project", read_json(project_root / "project.json"))
        self.assertEqual(1, len(EventLog(root).read().events))

    def test_repeat_init_is_idempotent_and_preserves_store(self) -> None:
        manager = self.manager()
        first = manager.init_project("Apollo")
        root = Path(first["runtime_root"])
        tasks = ProjectStore(root, "apollo", "tasks.json", "taskStore")

        def increment(value: dict[str, object]) -> None:
            value["revision"] = int(value["revision"]) + 1

        tasks.update(increment)
        second = manager.init_project("Apollo")
        self.assertFalse(second["created"])
        self.assertEqual(1, tasks.read()["revision"])
        self.assertEqual(1, len(EventLog(root).read().events))

    def test_project_store_rejects_filename_escape(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        with self.assertRaises(TeamRuntimeError) as raised:
            ProjectStore(root, "apollo", "../registry.json", "registry")
        self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)

    def test_registry_update_rejects_key_slug_mismatch_without_writing(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        registry = RegistryStore(root)
        before = registry.read()

        def corrupt(value: dict[str, object]) -> None:
            projects = value["projects"]
            assert isinstance(projects, dict)
            projects["wrong"] = projects.pop("apollo")
            value["revision"] = int(value["revision"]) + 1

        with self.assertRaises(TeamRuntimeError) as raised:
            registry.update(corrupt)
        self.assertEqual("E_CORRUPT_RUNTIME", raised.exception.code)
        self.assertEqual(before, registry.read())

    def test_seed_is_validated_and_marks_demo_runtime(self) -> None:
        result = self.manager().init_project("Apollo", seed=DEMO_SEED)
        root = Path(result["runtime_root"])
        marker = read_json(root / ".runtime-marker.json")
        project = result["project"]
        self.assertTrue(marker["demo"])
        self.assertEqual("demo-apollo-v1", project["seed_provenance"])
        self.assertEqual("demo-manager", project["active_manager_id"])

    def test_seed_project_mismatch_is_rejected_before_runtime_creation(self) -> None:
        manager = self.manager()
        with self.assertRaises(TeamRuntimeError) as raised:
            manager.init_project("Different", seed=DEMO_SEED)
        self.assertEqual("E_SCHEMA_VERSION", raised.exception.code)
        self.assertFalse(manager.paths.runtime_root.exists())

    def test_two_worktrees_read_and_write_same_project_store(self) -> None:
        first, second = self.repo.worktrees()
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        first_root = resolve_runtime_paths(first).runtime_root
        second_root = resolve_runtime_paths(second).runtime_root
        store = ProjectStore(first_root, "apollo", "tasks.json", "taskStore")

        def increment(value: dict[str, object]) -> None:
            value["revision"] = int(value["revision"]) + 1

        store.update(increment)
        observed = ProjectStore(
            second_root, "apollo", "tasks.json", "taskStore"
        ).read()
        self.assertEqual(root, first_root)
        self.assertEqual(1, observed["revision"])

    def test_concurrent_json_updates_remain_valid(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])

        def update_once(_: int) -> None:
            store = ProjectStore(root, "apollo", "tasks.json", "taskStore")

            def increment(value: dict[str, object]) -> None:
                value["revision"] = int(value["revision"]) + 1

            store.update(increment)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(update_once, range(40)))
        final = ProjectStore(root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual(40, final["revision"])
        validate("taskStore", final)

    def test_concurrent_event_append_has_unique_complete_lines(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        events = [self.event(index) for index in range(40)]

        def append(event: Event) -> bool:
            return EventLog(root).append(event)

        with ThreadPoolExecutor(max_workers=8) as executor:
            outcomes = list(executor.map(append, events))
        self.assertTrue(all(outcomes))
        duplicate = self.event(100)
        with ThreadPoolExecutor(max_workers=8) as executor:
            duplicate_outcomes = list(executor.map(append, [duplicate] * 8))
        self.assertEqual(1, sum(duplicate_outcomes))
        result = EventLog(root).read()
        ids = [event["id"] for event in result.events]
        self.assertFalse(result.trailing_corruption)
        self.assertEqual(42, len(ids))  # includes project.created and one duplicate
        self.assertEqual(len(ids), len(set(ids)))
        for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines():
            validate("event", json.loads(line))

    def test_duplicate_event_is_idempotent_and_conflicts_are_rejected(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        event = self.event(1)
        log = EventLog(root)
        self.assertTrue(log.append(event))
        self.assertFalse(log.append(event))
        conflict = self.event(2, key=event.idempotency_key)
        with self.assertRaises(TeamRuntimeError) as raised:
            log.append(conflict)
        self.assertEqual("E_IDEMPOTENCY_CONFLICT", raised.exception.code)

    def test_reader_reports_and_preserves_incomplete_trailing_event(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        event = self.event(1)
        log = EventLog(root)
        log.append(event)
        with log.path.open("ab") as stream:
            stream.write(b'{"actor":"system:fixture"')
        result = log.read()
        self.assertTrue(result.trailing_corruption)
        self.assertEqual(2, len(result.events))
        with self.assertRaises(TeamRuntimeError) as raised:
            log.append(self.event(2))
        self.assertEqual("E_CORRUPT_RUNTIME", raised.exception.code)
        self.assertTrue(log.path.read_bytes().endswith(b'"system:fixture"'))

    def test_atomic_replace_failure_preserves_last_valid_json(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        target = root / "projects" / "apollo" / "tasks.json"
        before = read_json(target)
        changed = {**before, "revision": 1}
        with mock.patch("orbital_team.storage.os.replace", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                atomic_write_json(target, changed)
        self.assertEqual(before, read_json(target))
        self.assertEqual([], list(target.parent.glob(f".{target.name}.tmp-*")))

    def test_stale_lock_file_is_reusable_and_live_lock_times_out(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        lock_path = root / "locks" / "stale.lock"
        lock_path.write_text("abandoned owner metadata", encoding="utf-8")
        with RuntimeLock(lock_path, timeout=0.2):
            with self.assertRaises(TeamRuntimeError) as raised:
                with RuntimeLock(lock_path, timeout=0.05):
                    self.fail("live lock should not be acquired")
        self.assertEqual("E_LOCK_TIMEOUT", raised.exception.code)
        with RuntimeLock(lock_path, timeout=0.2):
            pass

    def test_idempotency_journal_replays_and_detects_payload_conflict(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        guard = IdempotencyGuard(
            root / "projects" / "apollo" / "operations",
            root / "locks" / "project-apollo.lock",
        )
        metadata = {
            "object_refs": ["tasks.json:apollo-T-0001"],
            "target_hashes": {"tasks.json": "a" * 64},
            "target_revisions": {"tasks.json": 2},
        }
        first = guard.prepare("request-1", {"value": 1}, "event-1", **metadata)
        replay = guard.prepare("request-1", {"value": 1}, "event-1", **metadata)
        self.assertEqual(first, replay)
        committed = guard.commit("request-1", {"value": 1}, {"ok": True})
        self.assertEqual("Committed", committed.state)
        self.assertEqual(
            committed,
            guard.commit("request-1", {"value": 1}, {"ok": True}),
        )
        with self.assertRaises(TeamRuntimeError) as raised:
            guard.prepare("request-1", {"value": 2}, "event-2", **metadata)
        self.assertEqual("E_IDEMPOTENCY_CONFLICT", raised.exception.code)

    @unittest.skipUnless(os.name == "posix", "POSIX mode bits are unavailable")
    def test_runtime_and_sensitive_files_are_private(self) -> None:
        root = Path(self.manager().init_project("Apollo")["runtime_root"])
        log = root / "projects" / "apollo" / "runs" / "run-1" / "stdout.log"
        append_private_text(log, "sensitive\n")
        self.assertEqual(PRIVATE_DIR_MODE, private_mode(root))
        self.assertEqual(PRIVATE_FILE_MODE, private_mode(root / "registry.json"))
        self.assertEqual(PRIVATE_FILE_MODE, private_mode(root / "events.jsonl"))
        self.assertEqual(PRIVATE_DIR_MODE, private_mode(log.parent))
        self.assertEqual(PRIVATE_FILE_MODE, private_mode(log))
        self.assertEqual(0, private_mode(log) & 0o077)

    def test_runtime_is_outside_git_status(self) -> None:
        self.manager().init_project("Apollo")
        self.assertEqual("", git(self.repo.repository, "status", "--porcelain"))

    def test_status_reads_project_without_mutation(self) -> None:
        manager = self.manager()
        manager.init_project("Apollo")
        status = manager.status("apollo")
        self.assertTrue(status["initialized"])
        self.assertEqual("apollo", status["projects"][0]["slug"])
        self.assertEqual(1, status["event_count"])
        self.assertEqual(1, status["registry_revision"])

    def test_reset_requires_confirmation_for_non_demo_runtime(self) -> None:
        manager = self.manager()
        manager.init_project("Apollo")
        with self.assertRaises(TeamRuntimeError) as raised:
            manager.reset_runtime("apollo")
        self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)
        self.assertTrue(manager.paths.runtime_root.is_dir())

    def test_reset_removes_only_exact_runtime_and_preserves_repository(self) -> None:
        manager = self.manager()
        manager.init_project("Apollo")
        untracked = self.repo.repository / "do-not-delete.txt"
        untracked.write_text("still here\n", encoding="utf-8")
        git_head = self.repo.repository / ".git" / "HEAD"
        manager.reset_runtime("apollo", confirmed=True)
        self.assertFalse(manager.paths.runtime_root.exists())
        self.assertTrue(self.repo.repository.is_dir())
        self.assertTrue(untracked.is_file())
        self.assertTrue(git_head.is_file())

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_reset_refuses_symlink_target(self) -> None:
        manager = self.manager()
        manager.init_project("Apollo")
        root = manager.paths.runtime_root
        real_runtime = root.with_name("saved-runtime")
        root.rename(real_runtime)
        outside = self.repo.root / "outside-runtime"
        outside.mkdir()
        sentinel = outside / "sentinel.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        root.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(TeamRuntimeError) as raised:
            manager.reset_runtime("apollo", confirmed=True)
        self.assertEqual("E_GUARDRAIL_VIOLATION", raised.exception.code)
        self.assertTrue(sentinel.is_file())

    def test_demo_runtime_reset_accepts_marker_without_yes(self) -> None:
        manager = self.manager()
        manager.init_project("Apollo", seed=DEMO_SEED)
        manager.reset_runtime("apollo")
        self.assertFalse(manager.paths.runtime_root.exists())

    def test_cli_init_status_and_reset(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(
                [
                    "init",
                    "--project",
                    "Apollo",
                    "--workspace",
                    os.fspath(self.repo.repository),
                ]
            )
        self.assertEqual(0, code)
        self.assertTrue(json.loads(output.getvalue())["created"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(
                [
                    "status",
                    "--project",
                    "apollo",
                    "--workspace",
                    os.fspath(self.repo.repository),
                ]
            )
        self.assertEqual(0, code)
        self.assertTrue(json.loads(output.getvalue())["initialized"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = cli_main(
                [
                    "reset",
                    "--runtime-only",
                    "--project",
                    "apollo",
                    "--workspace",
                    os.fspath(self.repo.repository),
                    "--yes",
                ]
            )
        self.assertEqual(0, code)
        self.assertFalse(resolve_runtime_paths(self.repo.repository).runtime_root.exists())


if __name__ == "__main__":
    unittest.main()
