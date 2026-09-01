from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .constants import (
    RUNTIME_DIR_NAME,
    RUNTIME_MAGIC,
    RUNTIME_MARKER,
    RUNTIME_VERSION,
    SCHEMA_VERSION,
    STORE_SCHEMAS,
)
from .errors import TeamRuntimeError
from .models import Event
from .paths import RuntimePaths, resolve_runtime_paths
from .schema import validate
from .storage import (
    EventLog,
    RegistryStore,
    RuntimeLock,
    atomic_write_json,
    canonical_json,
    read_json,
    secure_directory,
    secure_empty_file,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def project_slug(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    if not slug:
        raise TeamRuntimeError("E_USAGE", "Project name cannot produce a valid slug.")
    if len(slug) < 2:
        slug = f"{slug}-project"
    slug = slug[:32].rstrip("-")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,31}", slug):
        raise TeamRuntimeError(
            "E_USAGE", "Project name cannot produce a valid project slug."
        )
    return slug


def _empty_store(slug: str) -> dict[str, Any]:
    return {
        "items": {},
        "project_slug": slug,
        "revision": 0,
        "schema_version": SCHEMA_VERSION,
    }


def stable_uuid4(value: str) -> str:
    """Return deterministic bytes with RFC 4122 version-4 and variant bits."""
    raw = bytearray(hashlib.sha256(value.encode("utf-8")).digest()[:16])
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))


class RuntimeManager:
    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.paths = resolve_runtime_paths(workspace)

    def _read_seed(
        self, seed: str | os.PathLike[str] | None, slug: str
    ) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        if seed is None:
            return (
                {
                    "active_manager_id": "default-manager",
                    "demo": False,
                    "runner": "manual",
                    "seed_id": None,
                },
                {name: _empty_store(slug) for name in STORE_SCHEMAS},
            )
        seed_root = Path(seed).expanduser().resolve()
        manifest_path = seed_root / "seed.json"
        if not seed_root.is_dir() or not manifest_path.is_file():
            raise TeamRuntimeError(
                "E_USAGE",
                "Seed must be a directory containing seed.json.",
                {"seed": os.fspath(seed_root)},
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Seed manifest is invalid JSON.",
                {"seed": os.fspath(seed_root), "reason": str(exc)},
            ) from exc
        if (
            manifest.get("kind") != "orbital-team-seed"
            or manifest.get("schema_version") != SCHEMA_VERSION
            or manifest.get("project_slug") != slug
        ):
            raise TeamRuntimeError(
                "E_SCHEMA_VERSION",
                "Seed kind, schema version, or project slug is incompatible.",
                {"project_slug": slug, "seed": os.fspath(seed_root)},
            )
        stores: dict[str, dict[str, Any]] = {}
        for filename, schema_name in STORE_SCHEMAS.items():
            path = seed_root / filename
            value = read_json(path)
            validate(schema_name, value)
            if value["project_slug"] != slug:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Seed store belongs to a different project.",
                    {"path": os.fspath(path)},
                )
            for item_id, item in value["items"].items():
                if item.get("id") != item_id:
                    raise TeamRuntimeError(
                        "E_CORRUPT_RUNTIME",
                        "Seed item key does not match its object ID.",
                        {"item_id": item_id, "path": os.fspath(path)},
                    )
            stores[filename] = value
        normalized = {
            "active_manager_id": manifest.get(
                "active_manager_id", "default-manager"
            ),
            "demo": manifest.get("demo") is True,
            "runner": manifest.get("runner", "manual"),
            "seed_id": manifest.get("seed_id"),
        }
        return normalized, stores

    def _create_layout(self) -> None:
        root = self.paths.runtime_root
        for directory in (
            root,
            root / "locks",
            root / "consumers",
            root / "jobs",
            root / "projects",
        ):
            secure_directory(directory)
        secure_empty_file(root / "events.jsonl")

    def _load_marker(self) -> dict[str, Any]:
        marker_path = self.paths.runtime_root / RUNTIME_MARKER
        marker = read_json(marker_path)
        if (
            marker.get("kind") != RUNTIME_MAGIC
            or marker.get("runtime_version") != RUNTIME_VERSION
            or marker.get("schema_version") != SCHEMA_VERSION
        ):
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Runtime safety marker is missing or incompatible.",
                {"marker": os.fspath(marker_path)},
            )
        return marker

    def _write_project_created_event(
        self, project: dict[str, Any], *, demo: bool
    ) -> None:
        slug = project["slug"]
        event_id = stable_uuid4(
            f"orbital-team:project.created:{slug}:{project['created_at']}"
        )
        event = Event(
            actor="system:fixture" if demo else "human:default-manager",
            data={"display_name": project["display_name"]},
            id=event_id,
            idempotency_key=f"project:init:{slug}",
            project_slug=slug,
            schema_version=SCHEMA_VERSION,
            timestamp=project["created_at"],
            type="project.created",
        )
        EventLog(self.paths.runtime_root).append(event)

    def init_project(
        self,
        name: str,
        *,
        seed: str | os.PathLike[str] | None = None,
    ) -> dict[str, Any]:
        display_name = name.strip()
        if not display_name or len(display_name) > 80:
            raise TeamRuntimeError(
                "E_USAGE", "Project name must contain 1 to 80 characters."
            )
        slug = project_slug(display_name)
        seed_manifest, seed_stores = self._read_seed(seed, slug)
        try:
            self._create_layout()
        except OSError as exc:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Git common directory is not writable for runtime initialization.",
                {"git_common_dir": os.fspath(self.paths.git_common_dir)},
            ) from exc
        registry_lock = self.paths.locks / "registry.lock"
        created = False
        with RuntimeLock(registry_lock):
            marker_path = self.paths.runtime_root / RUNTIME_MARKER
            registry_path = self.paths.registry
            if marker_path.exists():
                marker = self._load_marker()
            else:
                marker = {
                    "created_at": utc_now(),
                    "demo": bool(seed_manifest["demo"]),
                    "kind": RUNTIME_MAGIC,
                    "runtime_version": RUNTIME_VERSION,
                    "schema_version": SCHEMA_VERSION,
                }
                atomic_write_json(marker_path, marker)
            if registry_path.exists():
                registry = RegistryStore(self.paths.runtime_root).read()
            else:
                registry = {
                    "projects": {},
                    "revision": 0,
                    "schema_version": SCHEMA_VERSION,
                }
                atomic_write_json(registry_path, registry)
            registration = registry["projects"].get(slug)
            project_dir = self.paths.projects / slug
            project_path = project_dir / "project.json"
            if registration is not None:
                if registration["display_name"] != display_name:
                    raise TeamRuntimeError(
                        "E_IDEMPOTENCY_CONFLICT",
                        "Project slug is already registered with a different name.",
                        {"project_slug": slug},
                    )
                project = read_json(project_path)
                validate("project", project)
            else:
                secure_directory(project_dir)
                for directory in (
                    project_dir / "operations",
                    project_dir / "reports",
                    project_dir / "integrations",
                    project_dir / "knowledge-packs",
                    project_dir / "knowledge-proposals",
                    project_dir / "knowledge-summaries",
                    project_dir / "runs",
                ):
                    secure_directory(directory)
                created_at = utc_now()
                project = {
                    "active_manager_id": seed_manifest["active_manager_id"],
                    "allowed_worktree_roots": [
                        os.fspath(self.paths.repository_root)
                    ],
                    "canonical_workspace": os.fspath(self.paths.repository_root),
                    "created_at": created_at,
                    "display_name": display_name,
                    "revision": 0,
                    "runner": seed_manifest["runner"],
                    "schema_version": SCHEMA_VERSION,
                    "seed_provenance": seed_manifest["seed_id"],
                    "slug": slug,
                }
                validate("project", project)
                if project_path.exists():
                    existing_project = read_json(project_path)
                    validate("project", existing_project)
                    if existing_project["slug"] != slug:
                        raise TeamRuntimeError(
                            "E_CORRUPT_RUNTIME",
                            "Partial project runtime belongs to a different project.",
                        )
                    project = existing_project
                else:
                    atomic_write_json(project_path, project)
                for filename, schema_name in STORE_SCHEMAS.items():
                    store_path = project_dir / filename
                    if store_path.exists():
                        validate(schema_name, read_json(store_path))
                    else:
                        atomic_write_json(store_path, seed_stores[filename])
                registration = {
                    "created_at": project["created_at"],
                    "display_name": display_name,
                    "project_file": f"projects/{slug}/project.json",
                    "slug": slug,
                }
                registry["projects"][slug] = registration
                registry["revision"] += 1
                validate("registry", registry)
                atomic_write_json(registry_path, registry)
                if len(registry["projects"]) > 1 and marker.get("demo"):
                    marker["demo"] = False
                    atomic_write_json(marker_path, marker)
                created = True
            self._write_project_created_event(
                project, demo=bool(marker.get("demo"))
            )
        return {
            "created": created,
            "ok": True,
            "project": project,
            "runtime_root": os.fspath(self.paths.runtime_root),
            "schema_version": SCHEMA_VERSION,
        }

    def _registry(self) -> dict[str, Any]:
        if not self.paths.registry.is_file():
            raise TeamRuntimeError(
                "E_PROJECT_NOT_FOUND", "Team runtime is not initialized."
            )
        self._load_marker()
        return RegistryStore(self.paths.runtime_root).read()

    @staticmethod
    def _resolve_registration(
        registry: dict[str, Any], query: str
    ) -> dict[str, Any]:
        direct = registry["projects"].get(query)
        if direct is not None:
            return direct
        folded = query.casefold()
        matches = [
            value
            for value in registry["projects"].values()
            if value["display_name"].casefold() == folded
        ]
        if not matches:
            raise TeamRuntimeError(
                "E_PROJECT_NOT_FOUND",
                "Project was not found.",
                {"project": query},
            )
        if len(matches) > 1:
            raise TeamRuntimeError(
                "E_PROJECT_AMBIGUOUS",
                "Project name matched multiple projects.",
                {"projects": [item["slug"] for item in matches]},
            )
        return matches[0]

    def status(self, project: str | None = None) -> dict[str, Any]:
        if not self.paths.runtime_root.exists():
            return {
                "initialized": False,
                "ok": True,
                "runtime_root": os.fspath(self.paths.runtime_root),
                "schema_version": SCHEMA_VERSION,
            }
        registry = self._registry()
        registrations = list(registry["projects"].values())
        projects: list[dict[str, Any]] = []
        if project is not None:
            registrations = [self._resolve_registration(registry, project)]
        for registration in registrations:
            project_path = self.paths.runtime_root / registration["project_file"]
            value = read_json(project_path)
            validate("project", value)
            projects.append(value)
        event_result = EventLog(self.paths.runtime_root).read()
        return {
            "event_count": len(event_result.events),
            "event_log_trailing_corruption": event_result.trailing_corruption,
            "git_common_dir": os.fspath(self.paths.git_common_dir),
            "initialized": True,
            "ok": True,
            "projects": projects,
            "registry_revision": registry["revision"],
            "runtime_root": os.fspath(self.paths.runtime_root),
            "schema_version": SCHEMA_VERSION,
        }

    def reset_runtime(self, project: str, *, confirmed: bool = False) -> dict[str, Any]:
        root = self.paths.runtime_root
        expected = self.paths.git_common_dir / RUNTIME_DIR_NAME
        if (
            not root.exists()
            or root.is_symlink()
            or root.resolve() != expected.resolve()
            or root.parent.resolve() != self.paths.git_common_dir.resolve()
        ):
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Reset target is not the exact resolved orbital-team runtime.",
                {"runtime_root": os.fspath(root)},
            )
        marker = self._load_marker()
        registry = self._registry()
        registration = self._resolve_registration(registry, project)
        if not confirmed and marker.get("demo") is not True:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Runtime reset requires --yes unless the runtime has a demo marker.",
                {"project_slug": registration["slug"]},
            )
        lock_path = self.paths.locks / "registry.lock"
        with RuntimeLock(lock_path):
            marker = self._load_marker()
            registry = RegistryStore(self.paths.runtime_root).read()
            self._resolve_registration(registry, registration["slug"])
            shutil.rmtree(root)
        return {
            "ok": True,
            "project_slug": registration["slug"],
            "removed": os.fspath(root),
            "schema_version": SCHEMA_VERSION,
        }


def seed_digest(seed_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(seed_root.glob("*.json")):
        digest.update(path.name.encode("utf-8"))
        digest.update(canonical_json(read_json(path)))
    return digest.hexdigest()
