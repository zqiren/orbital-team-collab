#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any


HOOK_COMMAND = (
    'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/orbital_team_session_start.py" '
    '--workspace "$CLAUDE_PROJECT_DIR"'
)
HOOK_ENTRY = {
    "matcher": "startup|resume|clear|compact",
    "hooks": [{"type": "command", "command": HOOK_COMMAND, "timeout": 10}],
}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _read_settings(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Refusing to overwrite invalid Claude settings: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("Refusing to overwrite non-object Claude settings.")
    return value


def _install_path(source: Path, destination: Path, mode: str) -> None:
    if destination.exists() or destination.is_symlink():
        raise SystemExit(f"Install target already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mode == "link":
        destination.symlink_to(os.path.relpath(source, destination.parent), target_is_directory=source.is_dir())
    elif source.is_dir():
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    else:
        shutil.copy2(source, destination)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path)


def _guard_destination(target: Path, destination: Path) -> None:
    try:
        relative_parent = destination.parent.relative_to(target)
    except ValueError as exc:
        raise SystemExit(f"Install target is outside the project: {destination}") from exc
    cursor = target
    for part in relative_parent.parts:
        cursor /= part
        if cursor.is_symlink():
            raise SystemExit(f"Install target escapes through a symlink: {cursor}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        destination.parent.resolve().relative_to(target)
    except ValueError as exc:
        raise SystemExit(f"Install target escapes through a symlink: {destination}") from exc


def _safe_installed_path(target: Path, relative: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise SystemExit("Adapter manifest contains an unsafe path.")
    candidate = target / relative_path
    try:
        candidate.parent.resolve(strict=False).relative_to(target)
    except ValueError as exc:
        raise SystemExit("Adapter manifest contains an unsafe path.") from exc
    return candidate


def _settings_add(path: Path) -> None:
    settings = _read_settings(path)
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit("Claude settings hooks must be an object.")
    entries = hooks.setdefault("SessionStart", [])
    if not isinstance(entries, list):
        raise SystemExit("Claude SessionStart hooks must be a list.")
    if HOOK_ENTRY not in entries:
        entries.append(HOOK_ENTRY)
    _write_json(path, settings)


def _settings_remove(path: Path) -> None:
    if not path.is_file():
        return
    settings = _read_settings(path)
    hooks = settings.get("hooks")
    if isinstance(hooks, dict):
        entries = hooks.get("SessionStart")
        if isinstance(entries, list):
            hooks["SessionStart"] = [entry for entry in entries if entry != HOOK_ENTRY]
            if not hooks["SessionStart"]:
                hooks.pop("SessionStart")
        if not hooks:
            settings.pop("hooks", None)
    if settings:
        _write_json(path, settings)
    else:
        path.unlink(missing_ok=True)


def install(target: Path, agent: str, mode: str, skill_root: Path) -> dict[str, Any]:
    target = target.resolve()
    if agent == "claude-code":
        base = target / ".claude"
        installed = [
            (skill_root, base / "skills" / "orbital-team-member"),
            (
                skill_root / "assets" / "claude-code" / "commands" / "team.md",
                base / "commands" / "team.md",
            ),
            (
                skill_root
                / "assets"
                / "claude-code"
                / "hooks"
                / "orbital_team_session_start.py",
                base / "hooks" / "orbital_team_session_start.py",
            ),
        ]
        manifest = base / "orbital-team-member-install.json"
        settings = base / "settings.json"
    else:
        base = target / ".agents"
        installed = [(skill_root, base / "skills" / "orbital-team-member")]
        manifest = base / "orbital-team-member-install.json"
        settings = None
    if manifest.exists():
        raise SystemExit(f"Adapter is already installed: {manifest}")
    completed: list[Path] = []
    try:
        for source, destination in installed:
            _guard_destination(target, destination)
            _install_path(source, destination, mode)
            completed.append(destination)
        if settings is not None:
            _guard_destination(target, settings)
            _settings_add(settings)
        value = {
            "agent": agent,
            "installed_paths": [os.fspath(path.relative_to(target)) for path in completed],
            "mode": mode,
            "settings": os.fspath(settings.relative_to(target)) if settings else None,
        }
        _write_json(manifest, value)
        return value
    except BaseException:
        for destination in reversed(completed):
            _remove_path(destination)
        if settings is not None:
            _settings_remove(settings)
        raise


def uninstall(target: Path, agent: str) -> dict[str, Any]:
    target = target.resolve()
    base = target / (".claude" if agent == "claude-code" else ".agents")
    manifest = base / "orbital-team-member-install.json"
    if not manifest.is_file():
        raise SystemExit(f"Adapter install manifest was not found: {manifest}")
    value = json.loads(manifest.read_text(encoding="utf-8"))
    if value.get("agent") != agent:
        raise SystemExit("Adapter manifest agent does not match uninstall request.")
    for relative in value.get("installed_paths", []):
        _remove_path(_safe_installed_path(target, relative))
    settings_value = value.get("settings")
    if isinstance(settings_value, str):
        _settings_remove(_safe_installed_path(target, settings_value))
    manifest.unlink()
    return {"agent": agent, "removed": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install or remove the Orbital Team Member adapter.")
    parser.add_argument("--agent", choices=("claude-code", "generic"), required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--mode", choices=("copy", "link"), default="copy")
    parser.add_argument("--uninstall", action="store_true")
    arguments = parser.parse_args()
    skill_root = Path(__file__).resolve().parents[1]
    result = (
        uninstall(arguments.target, arguments.agent)
        if arguments.uninstall
        else install(arguments.target, arguments.agent, arguments.mode, skill_root)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
