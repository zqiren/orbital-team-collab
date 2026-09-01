from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .constants import RUNTIME_DIR_NAME
from .errors import TeamRuntimeError


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    workspace: Path
    repository_root: Path
    git_common_dir: Path
    runtime_root: Path

    @property
    def registry(self) -> Path:
        return self.runtime_root / "registry.json"

    @property
    def events(self) -> Path:
        return self.runtime_root / "events.jsonl"

    @property
    def locks(self) -> Path:
        return self.runtime_root / "locks"

    @property
    def projects(self) -> Path:
        return self.runtime_root / "projects"


def _git(workspace: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", os.fspath(workspace), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        stderr = getattr(exc, "stderr", "") or ""
        raise TeamRuntimeError(
            "E_NOT_GIT_REPO",
            "Workspace is not inside a Git worktree.",
            {"workspace": os.fspath(workspace), "reason": stderr.strip()},
        ) from exc
    return result.stdout.strip()


def resolve_runtime_paths(workspace: str | os.PathLike[str]) -> RuntimePaths:
    candidate = Path(workspace).expanduser().resolve()
    if not candidate.is_dir():
        raise TeamRuntimeError(
            "E_NOT_GIT_REPO",
            "Workspace is not an existing directory.",
            {"workspace": os.fspath(candidate)},
        )
    inside = _git(candidate, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        raise TeamRuntimeError(
            "E_NOT_GIT_REPO", "Workspace is not inside a Git worktree."
        )
    common = Path(
        _git(
            candidate,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    ).resolve()
    repository = Path(
        _git(candidate, "rev-parse", "--show-toplevel")
    ).resolve()
    runtime = common / RUNTIME_DIR_NAME
    if runtime.parent != common or runtime.name != RUNTIME_DIR_NAME:
        raise TeamRuntimeError(
            "E_GUARDRAIL_VIOLATION", "Resolved runtime path is not safe."
        )
    return RuntimePaths(candidate, repository, common, runtime)

