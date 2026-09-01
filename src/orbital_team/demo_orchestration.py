"""Safe, offline SPEC-08 composition of the existing Orbital Team primitives."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

from .dashboard import DashboardProjection
from .errors import TeamRuntimeError
from .im_context import FixtureIMProvider, IMContextWorkflow
from .member_workflow import MemberWorkflow
from .runtime import RuntimeManager
from .storage import EventLog, atomic_write_json, atomic_write_private_text
from .teamd import TeamDaemon


DEMO_MARKER = ".orbital-team-demo-root"
DEMO_MAGIC = "orbital-team-demo-v1"
PROJECT = "apollo"
MEMBERS = {"alice": "apollo-T-0001", "bob": "apollo-T-0002"}
MEMBER_CHANGES = {
    "alice": (
        "app/greeting.py",
        '"""Greeting delivered by Alice in the synthetic demo."""\n\n\ndef greeting(name: str) -> str:\n    return f"Hello, {name}!"\n',
    ),
    "bob": (
        "app/health.py",
        '"""Health response delivered by Bob in the synthetic demo."""\n\n\ndef health() -> dict[str, str]:\n    return {"status": "ok"}\n',
    ),
}


def source_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(workspace: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return subprocess.run(
        ["git", "-C", os.fspath(workspace), *args],
        check=check,
        capture_output=True,
        text=True,
        env=environment,
    )


def _marker_content(root: Path) -> str:
    return f"{DEMO_MAGIC}\nroot={root.resolve()}\n"


def _validate_root(root: str | os.PathLike[str]) -> Path:
    candidate = Path(root)
    if not candidate.is_absolute():
        raise TeamRuntimeError("E_GUARDRAIL_VIOLATION", "Demo root must be absolute.")
    if candidate.is_symlink() or not candidate.is_dir():
        raise TeamRuntimeError("E_GUARDRAIL_VIOLATION", "Demo root is missing or unsafe.")
    resolved = candidate.resolve()
    marker = resolved / DEMO_MARKER
    if marker.is_symlink() or not marker.is_file():
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION", "Exact demo safety marker is missing."
        )
    if marker.read_text(encoding="utf-8") != _marker_content(resolved):
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION", "Demo safety marker does not bind this exact root."
        )
    if resolved == Path.home().resolve() or resolved.parent == resolved:
        raise TeamRuntimeError("E_GUARDRAIL_VIOLATION", "Refusing a broad demo root.")
    return resolved


def _create_root(root: str | os.PathLike[str] | None) -> Path:
    if root is None:
        created = Path(tempfile.mkdtemp(prefix="orbital-team-demo-"))
    else:
        created = Path(root)
        if not created.is_absolute():
            raise TeamRuntimeError("E_GUARDRAIL_VIOLATION", "Demo root must be absolute.")
        if created.exists() and any(created.iterdir()):
            raise TeamRuntimeError("E_GUARDRAIL_VIOLATION", "Demo root must be empty.")
        created.mkdir(mode=0o700, parents=False, exist_ok=True)
    atomic_write_private_text(created / DEMO_MARKER, _marker_content(created))
    return _validate_root(created)


def _configure_repository(canonical: Path) -> None:
    _git(canonical, "init", "-b", "main")
    _git(canonical, "config", "user.name", "Orbital Demo")
    _git(canonical, "config", "user.email", "demo@orbital-team.invalid")
    _git(canonical, "add", ".")
    _git(canonical, "commit", "-m", "seed synthetic Apollo demo")


def _install_member_skill(source: Path, worktree: Path) -> None:
    installer = source / "skills" / "orbital-team-member" / "scripts" / "install_adapter.py"
    completed = subprocess.run(
        [
            sys.executable,
            os.fspath(installer),
            "--agent",
            "generic",
            "--target",
            os.fspath(worktree),
            "--mode",
            "copy",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise TeamRuntimeError(
            "E_INTERNAL",
            "Member Skill installation failed.",
            {"stderr": completed.stderr.strip(), "worktree": os.fspath(worktree)},
        )


def setup_demo(
    root: str | os.PathLike[str] | None = None,
    *,
    fixture_root: str | os.PathLike[str] | None = None,
    runner: str = "builtin",
) -> dict[str, Any]:
    source = Path(fixture_root).resolve() if fixture_root else source_root()
    doctor_result = doctor_demo(source, runner=runner)
    if not doctor_result["ok"]:
        raise TeamRuntimeError(
            "E_RUNNER_UNAVAILABLE",
            "Demo prerequisites are unavailable.",
            {"checks": doctor_result["checks"]},
            retryable=True,
        )
    demo_root = _create_root(root)
    canonical = demo_root / "canonical"
    shutil.copytree(source / "demo" / "sample-app", canonical)
    shutil.copytree(source / "demo" / "runners", canonical / "demo" / "runners")
    _configure_repository(canonical)

    seed = source / "demo" / "seed"
    if runner != "builtin":
        seed = demo_root / "selected-seed"
        shutil.copytree(source / "demo" / "seed", seed)
        manifest = json.loads((seed / "seed.json").read_text(encoding="utf-8"))
        manifest["runner"] = runner
        atomic_write_json(seed / "seed.json", manifest)
    RuntimeManager(canonical).init_project("Apollo", seed=seed)

    worktrees: dict[str, Path] = {}
    for member in MEMBERS:
        worktree = demo_root / member
        _git(canonical, "worktree", "add", "-b", f"demo/{member}", os.fspath(worktree))
        _install_member_skill(source, worktree)
        MemberWorkflow(worktree).join_member(PROJECT, member, "generic-fixture")
        worktrees[member] = worktree

    fixture = FixtureIMProvider(source / "demo" / "im-fixtures" / "demo-messages.json")
    ingest = IMContextWorkflow(canonical).ingest(PROJECT, fixture, request_id="demo-ingest-v1")
    projection = DashboardProjection(canonical).snapshot(PROJECT)
    return {
        "canonical": os.fspath(canonical),
        "dashboard_url": "http://127.0.0.1:8765/?project=apollo",
        "im": {
            "potential_tasks": [item["id"] for item in ingest["potential_tasks"]],
            "questions": [item["id"] for item in ingest["questions"]],
        },
        "members": {key: os.fspath(value) for key, value in worktrees.items()},
        "mode": "live-scripted",
        "ok": True,
        "root": os.fspath(demo_root),
        "runner": runner,
        "tasks": [item["id"] for item in projection["tasks"] if item["id"] in MEMBERS.values()],
    }


def _member_worker(
    worktree: Path, member: str, task_id: str, barrier: Path, *, crash: bool = False
) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while not barrier.is_file():
        if time.monotonic() >= deadline:
            raise TeamRuntimeError("E_INTERNAL", "Member barrier timed out.")
        time.sleep(0.01)
    workflow = MemberWorkflow(worktree)
    workflow.claim(PROJECT, task_id, request_id=f"demo-{member}-claim")
    workflow.start_task(task_id, request_id=f"demo-{member}-start")
    if crash:
        raise TeamRuntimeError("E_INTERNAL", f"Synthetic {member} crash after start.")
    relative, content = MEMBER_CHANGES[member]
    target = worktree / relative
    target.write_text(content, encoding="utf-8")
    _git(worktree, "add", relative)
    _git(worktree, "commit", "-m", f"complete {task_id} as {member}")
    commit = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    report = workflow.submit_report(
        task_id,
        summary=f"{member.title()} completed the synthetic {task_id} change.",
        validation=[
            {
                "command": "python3 -m pytest -q",
                "outcome": "passed",
                "summary": "Synthetic sample-app regression passed.",
            }
        ],
        knowledge_candidates=[f"Demo task {task_id} completed deterministically."],
        commit=commit,
        request_id=f"demo-{member}-report",
    )
    return {"commit": commit, "member": member, "report_id": report["report"]["id"]}


def _launch_members(demo_root: Path, crash_member: str | None) -> list[dict[str, Any]]:
    barrier = demo_root / ".members-start"
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    environment["PYTHONPATH"] = os.fspath(Path(__file__).resolve().parents[1])
    processes: list[tuple[str, subprocess.Popen[str]]] = []
    for member, task_id in MEMBERS.items():
        argv = [
            sys.executable,
            "-m",
            "orbital_team.demo_orchestration",
            "_member",
            "--worktree",
            os.fspath(demo_root / member),
            "--member",
            member,
            "--task",
            task_id,
            "--barrier",
            os.fspath(barrier),
        ]
        if crash_member == member:
            argv.append("--crash")
        processes.append(
            (
                member,
                subprocess.Popen(
                    argv,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ),
            )
        )
    atomic_write_private_text(barrier, "go\n")
    results: list[dict[str, Any]] = []
    for member, process in processes:
        stdout, stderr = process.communicate(timeout=60)
        if process.returncode:
            if member == crash_member:
                results.append({"crashed": True, "member": member})
                continue
            raise TeamRuntimeError(
                "E_INTERNAL",
                "Synthetic member process failed.",
                {"member": member, "stderr": stderr.strip()},
            )
        results.append(json.loads(stdout.strip().splitlines()[-1]))
    return sorted(results, key=lambda item: item["member"])


def start_demo(
    root: str | os.PathLike[str], *, crash_member: str | None = None
) -> dict[str, Any]:
    demo_root = _validate_root(root)
    canonical = demo_root / "canonical"
    discovery = IMContextWorkflow(canonical)
    potentials = discovery.list_potential(PROJECT)["potential_tasks"]
    for potential in potentials:
        if potential["state"] == "new":
            discovery.triage(
                potential["id"], "Synthetic demo triage confirmed.", request_id="demo-triage-v1"
            )
            discovery.promote(potential["id"], request_id="demo-promote-v1")
    members = _launch_members(demo_root, crash_member)
    daemon_summary = TeamDaemon(canonical).run_once()
    snapshot = DashboardProjection(canonical).snapshot(PROJECT)
    return {
        "daemon": daemon_summary,
        "dashboard_url": "http://127.0.0.1:8765/?project=apollo",
        "events": len(snapshot["activity"]),
        "integrations": [
            {"id": item["id"], "state": item["state"]}
            for item in snapshot["integrations"]
        ],
        "knowledge_summaries": len(snapshot["knowledge"]),
        "members": members,
        "mode": "live-scripted",
        "ok": crash_member is None,
        "root": os.fspath(demo_root),
        "tasks": {item["id"]: item["state"] for item in snapshot["tasks"]},
    }


def status_demo(root: str | os.PathLike[str]) -> dict[str, Any]:
    demo_root = _validate_root(root)
    canonical = demo_root / "canonical"
    snapshot = DashboardProjection(canonical).snapshot(PROJECT)
    dashboard_argv = [
        sys.executable,
        "-m",
        "orbital_team",
        "dashboard",
        "--workspace",
        os.fspath(canonical),
        "--actor",
        "human:demo-manager",
        "--host",
        "127.0.0.1",
        "--port",
        "8765",
    ]
    return {
        "canonical": os.fspath(canonical),
        "dashboard_argv": dashboard_argv,
        "dashboard_command": " ".join(shlex.quote(item) for item in dashboard_argv),
        "dashboard_url": "http://127.0.0.1:8765/?project=apollo",
        "mode": "live-projection",
        "ok": True,
        "root": os.fspath(demo_root),
        "snapshot": snapshot,
    }


def reset_demo(root: str | os.PathLike[str]) -> dict[str, Any]:
    demo_root = _validate_root(root)
    canonical = demo_root / "canonical"
    if canonical.is_dir():
        runtime = RuntimeManager(canonical)
        if runtime.paths.runtime_root.exists():
            runtime.reset_runtime(PROJECT, confirmed=False)
    removed = os.fspath(demo_root)
    shutil.rmtree(demo_root)
    return {"ok": True, "removed": removed, "recoverable": False}


def doctor_demo(
    fixture_root: str | os.PathLike[str] | None = None, *, runner: str = "builtin"
) -> dict[str, Any]:
    source = Path(fixture_root).resolve() if fixture_root else source_root()
    checks: list[dict[str, Any]] = []
    git_path = shutil.which("git")
    checks.append({"available": git_path is not None, "component": "git", "detail": git_path})
    for relative in (
        "demo/seed/seed.json",
        "demo/sample-app/orbital/PROJECT_STATE.md",
        "demo/im-fixtures/demo-messages.json",
        "skills/orbital-team-member/scripts/install_adapter.py",
    ):
        present = (source / relative).is_file()
        checks.append({"available": present, "component": relative, "detail": "found" if present else "missing"})
    manifest_path = source / "demo" / "runners" / f"{runner}.json"
    manifest: dict[str, Any] | None = None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    runner_available = manifest is not None
    detail = "runner manifest missing or invalid"
    if manifest is not None:
        executable = manifest.get("argv", [""])[0]
        phases = set(manifest.get("phases", ["integration"]))
        runner_available = shutil.which(executable) is not None and {
            "integration",
            "knowledge",
        }.issubset(phases)
        detail = (
            "integration and knowledge phases available"
            if runner_available
            else "executable missing or integration/knowledge phases incomplete"
        )
    checks.append({"available": runner_available, "component": f"runner:{runner}", "detail": detail})
    return {"checks": checks, "ok": all(item["available"] for item in checks), "runner": runner}


def replay_demo(fixture_root: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    source = Path(fixture_root).resolve() if fixture_root else source_root()
    value = json.loads((source / "demo" / "replay" / "dashboard.json").read_text(encoding="utf-8"))
    value.update(live_success=False, mode="simulated-replay", ok=True)
    return value


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="team-demo")
    parser.add_argument("--fixture-root", type=Path, default=source_root())
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor")
    doctor.add_argument("--runner", default="builtin")
    setup = commands.add_parser("setup")
    setup.add_argument("--root", type=Path)
    setup.add_argument("--runner", default="builtin")
    start = commands.add_parser("start")
    start.add_argument("--root", type=Path, required=True)
    start.add_argument("--member-crash", choices=tuple(MEMBERS))
    status = commands.add_parser("status")
    status.add_argument("--root", type=Path, required=True)
    reset = commands.add_parser("reset")
    reset.add_argument("--root", type=Path, required=True)
    commands.add_parser("replay")
    member = commands.add_parser("_member", help=argparse.SUPPRESS)
    member.add_argument("--worktree", type=Path, required=True)
    member.add_argument("--member", choices=tuple(MEMBERS), required=True)
    member.add_argument("--task", required=True)
    member.add_argument("--barrier", type=Path, required=True)
    member.add_argument("--crash", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "doctor":
            result = doctor_demo(arguments.fixture_root, runner=arguments.runner)
        elif arguments.command == "setup":
            result = setup_demo(arguments.root, fixture_root=arguments.fixture_root, runner=arguments.runner)
        elif arguments.command == "start":
            result = start_demo(arguments.root, crash_member=arguments.member_crash)
        elif arguments.command == "status":
            result = status_demo(arguments.root)
        elif arguments.command == "reset":
            result = reset_demo(arguments.root)
        elif arguments.command == "replay":
            result = replay_demo(arguments.fixture_root)
        else:
            result = _member_worker(
                arguments.worktree,
                arguments.member,
                arguments.task,
                arguments.barrier,
                crash=arguments.crash,
            )
        _emit(result)
        return 0
    except TeamRuntimeError as exc:
        print(json.dumps(exc.response(), sort_keys=True), file=sys.stderr)
        return exc.exit_code
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        error = TeamRuntimeError("E_INTERNAL", "Demo orchestration failed.", {"reason": str(exc)})
        print(json.dumps(error.response(), sort_keys=True), file=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
