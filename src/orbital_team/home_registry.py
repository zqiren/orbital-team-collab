"""Cross-folder project directory stored in the user's home.

Each entry points one project slug at the local folder holding its git-native
runtime (`<folder>/.git/orbital-team/`). The folder's own registry remains the
source of truth for project data; this file only lets one dashboard find
projects that live in different folders, mirroring Orbital's projects.json.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .storage import atomic_write_json, read_json

HOME_ENV = "ORBITAL_TEAM_HOME"


def home_root() -> Path:
    override = os.environ.get(HOME_ENV)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".orbital-team"


def registry_path() -> Path:
    return home_root() / "projects.json"


def read_home_projects() -> dict[str, dict[str, Any]]:
    path = registry_path()
    if not path.is_file():
        return {}
    value = read_json(path)
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("projects"), dict)
        or value.get("schema_version") != SCHEMA_VERSION
    ):
        raise TeamRuntimeError(
            "E_CORRUPT_RUNTIME",
            "Home project directory is invalid.",
            {"path": os.fspath(path)},
        )
    projects: dict[str, dict[str, Any]] = {}
    for slug, entry in value["projects"].items():
        if (
            not isinstance(entry, dict)
            or entry.get("slug") != slug
            or not isinstance(entry.get("workspace"), str)
        ):
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Home project directory entry is invalid.",
                {"path": os.fspath(path), "project_slug": str(slug)},
            )
        projects[slug] = entry
    return projects


def register_home_project(slug: str, display_name: str, workspace: str) -> None:
    projects = read_home_projects()
    projects[slug] = {
        "display_name": display_name,
        "slug": slug,
        "workspace": workspace,
    }
    root = home_root()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    atomic_write_json(
        registry_path(),
        {
            "projects": {key: projects[key] for key in sorted(projects)},
            "schema_version": SCHEMA_VERSION,
        },
    )
