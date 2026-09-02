"""Runner manifest discovery shared by teamd and the dashboard.

Manifests are looked up first inside the project's canonical workspace (a
project-local override), then in the orbital-team checkout's own
`demo/runners/`, so projects created on arbitrary folders can use the bundled
runners without copying files around.
"""

from __future__ import annotations

import os
from pathlib import Path


def runner_manifest_dirs(canonical_workspace: str | os.PathLike[str]) -> list[Path]:
    dirs = [Path(canonical_workspace) / "demo" / "runners"]
    checkout = Path(__file__).resolve().parents[2] / "demo" / "runners"
    if checkout.is_dir() and checkout not in dirs:
        dirs.append(checkout)
    return dirs


def find_runner_manifest(
    name: str, canonical_workspace: str | os.PathLike[str]
) -> Path | None:
    if name == "manual":
        return None
    for directory in runner_manifest_dirs(canonical_workspace):
        manifest = directory / f"{name}.json"
        if manifest.is_file():
            return manifest
    return None
