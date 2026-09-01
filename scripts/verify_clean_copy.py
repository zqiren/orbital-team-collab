#!/usr/bin/env python3
"""Verify install/tests/demo from a disposable clean copy without touching source."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


IGNORED_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "orbital-src",
}
IGNORED_ORBITAL = {
    "approval_history.jsonl",
    "ledger",
    "output",
    "queue.json",
    "sessions",
    "tool-results",
}


def _ignored(directory: str, names: list[str]) -> set[str]:
    current = Path(directory)
    ignored = {
        name
        for name in names
        if name in IGNORED_NAMES
        or name.endswith((".pyc", ".pyo", ".egg-info"))
    }
    if current.name == "orbital":
        ignored.update(IGNORED_ORBITAL.intersection(names))
    if current.name != "sub_agents" and "sub_agents" in current.parts:
        # inside one agent's directory only MEMORY.md is a delivery file
        ignored.update(name for name in names if name != "MEMORY.md")
    return ignored


def _files(root: Path) -> list[Path]:
    values: list[Path] = []
    for directory, dirnames, filenames in os.walk(root):
        ignored = _ignored(directory, [*dirnames, *filenames])
        dirnames[:] = sorted(name for name in dirnames if name not in ignored)
        values.extend(
            Path(directory) / name
            for name in sorted(filenames)
            if name not in ignored
        )
    return values


def fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for file_path in _files(root):
        relative = file_path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8") + b"\0")
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def copy_clean_source(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=_ignored)


def _run(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout: int = 360,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"[clean-copy] {json.dumps(list(argv))}", file=sys.stderr, flush=True)
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode and not allow_failure:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {argv}\n"
            f"stdout:\n{completed.stdout[-4000:]}\n"
            f"stderr:\n{completed.stderr[-4000:]}"
        )
    return completed


def verify(
    source: Path,
    *,
    dashboard_policy: str = "require",
    keep: bool = False,
) -> dict[str, Any]:
    source = source.resolve()
    before = fingerprint(source)
    temporary = Path(tempfile.mkdtemp(prefix="orbital-team-clean-copy-"))
    copy_root = temporary / "repo"
    venv = temporary / "venv"
    demo_root = temporary / "demo-run"
    result: dict[str, Any] = {
        "clean_copy": os.fspath(copy_root),
        "dashboard": {"policy": dashboard_policy},
        "kept": keep,
        "ok": False,
        "source_unchanged": False,
    }
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    try:
        copy_clean_source(source, copy_root)
        _run(["git", "init", "-b", "main"], cwd=copy_root, environment=environment)
        _run(["git", "config", "user.name", "Clean Copy Verifier"], cwd=copy_root, environment=environment)
        _run(["git", "config", "user.email", "verifier@orbital-team.invalid"], cwd=copy_root, environment=environment)
        _run(["git", "add", "."], cwd=copy_root, environment=environment)
        _run(["git", "commit", "-m", "clean copy input"], cwd=copy_root, environment=environment)
        _run([sys.executable, "-m", "venv", "--system-site-packages", os.fspath(venv)], cwd=copy_root, environment=environment)
        python = venv / "bin" / "python"
        _run(
            [os.fspath(python), "-m", "pip", "install", "-e", ".", "--no-deps", "--no-build-isolation"],
            cwd=copy_root,
            environment=environment,
        )
        tests = _run([os.fspath(python), "-m", "pytest", "-q"], cwd=copy_root, environment=environment)
        result["pytest"] = tests.stdout.strip().splitlines()[-1]
        for argv in (
            [os.fspath(python), "-m", "orbital_team", "--help"],
            [os.fspath(venv / "bin" / "teamd"), "--help"],
            [os.fspath(python), "demo/scripts/team_demo.py", "--help"],
        ):
            _run(argv, cwd=copy_root, environment=environment)
        doctor = _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "doctor", "--runner", "builtin"],
            cwd=copy_root,
            environment=environment,
        )
        result["doctor"] = json.loads(doctor.stdout)
        setup = _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "setup", "--root", os.fspath(demo_root)],
            cwd=copy_root,
            environment=environment,
        )
        setup_value = json.loads(setup.stdout)
        started = _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "start", "--root", os.fspath(demo_root)],
            cwd=copy_root,
            environment=environment,
        )
        start_value = json.loads(started.stdout)
        status = _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "status", "--root", os.fspath(demo_root)],
            cwd=copy_root,
            environment=environment,
        )
        status_value = json.loads(status.stdout)
        replay = _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "replay"],
            cwd=copy_root,
            environment=environment,
        )
        replay_value = json.loads(replay.stdout)
        if not start_value["ok"] or start_value["knowledge_summaries"] != 2:
            raise RuntimeError("demo start did not complete the two knowledge summaries")
        expected_tasks = {"apollo-T-0001": "done", "apollo-T-0002": "done"}
        if any(start_value["tasks"].get(key) != value for key, value in expected_tasks.items()):
            raise RuntimeError("seed Tasks did not reach Done")
        if {item["state"] for item in start_value["integrations"]} != {"done"}:
            raise RuntimeError("Integration Jobs did not all reach Done")
        if replay_value.get("mode") != "simulated-replay" or replay_value.get("live_success") is not False:
            raise RuntimeError("replay was not explicitly marked simulated")
        result["demo"] = {
            "dashboard_url": setup_value["dashboard_url"],
            "events": start_value["events"],
            "integrations": start_value["integrations"],
            "knowledge_summaries": start_value["knowledge_summaries"],
            "projection_mode": status_value["mode"],
            "tasks": start_value["tasks"],
        }

        bind = _run(
            [
                os.fspath(python),
                "-c",
                (
                    "from orbital_team.dashboard import create_dashboard_server; "
                    f"server=create_dashboard_server({os.fspath(demo_root / 'canonical')!r}, "
                    "actor='human:demo-manager', host='127.0.0.1', port=0); "
                    "print(server.server_address[1]); server.server_close()"
                ),
            ],
            cwd=copy_root,
            environment=environment,
            allow_failure=dashboard_policy in {"allow", "skip"},
        ) if dashboard_policy != "skip" else None
        if bind is None:
            result["dashboard"].update(attempted=False, available=None)
        elif bind.returncode == 0:
            result["dashboard"].update(
                attempted=True, available=True, port=int(bind.stdout.strip())
            )
        else:
            result["dashboard"].update(
                attempted=True,
                available=False,
                error=(bind.stderr or bind.stdout).strip()[-1000:],
            )

        _run(
            [os.fspath(python), "demo/scripts/team_demo.py", "reset", "--root", os.fspath(demo_root)],
            cwd=copy_root,
            environment=environment,
        )
        if demo_root.exists():
            raise RuntimeError("demo reset did not remove the exact temporary root")
        clean = _run(["git", "status", "--porcelain"], cwd=copy_root, environment=environment)
        if clean.stdout.strip():
            raise RuntimeError(f"clean copy was polluted: {clean.stdout}")
        result["source_unchanged"] = fingerprint(source) == before
        if not result["source_unchanged"]:
            raise RuntimeError("source repo fingerprint changed during clean-copy verification")
        result["ok"] = True
        return result
    finally:
        if keep:
            result["temporary_root"] = os.fspath(temporary)
        else:
            shutil.rmtree(temporary, ignore_errors=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--dashboard-policy",
        choices=("require", "allow", "skip"),
        default="require",
        help="require bind success, allow an explicitly recorded failure, or skip the attempt",
    )
    parser.add_argument("--keep", action="store_true", help="keep the exact temporary root")
    arguments = parser.parse_args(argv)
    try:
        value = verify(
            arguments.source,
            dashboard_policy=arguments.dashboard_policy,
            keep=arguments.keep,
        )
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"error": str(exc), "ok": False}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
