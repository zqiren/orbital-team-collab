from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock, Timeout

from .constants import (
    DEFAULT_LOCK_TIMEOUT,
    PRIVATE_DIR_MODE,
    PRIVATE_FILE_MODE,
    SCHEMA_VERSION,
)
from .errors import TeamRuntimeError
from .models import Event, EventReadResult, IdempotencyRecord
from .schema import validate


def canonical_json(value: Any, *, newline: bool = False) -> bytes:
    suffix = "\n" if newline else ""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + suffix
    ).encode("utf-8")


def secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=PRIVATE_DIR_MODE)
    if os.name == "posix":
        path.chmod(PRIVATE_DIR_MODE)


def secure_empty_file(path: Path) -> None:
    secure_directory(path.parent)
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_APPEND | os.O_WRONLY,
        PRIVATE_FILE_MODE,
    )
    os.close(descriptor)
    if os.name == "posix":
        path.chmod(PRIVATE_FILE_MODE)


def append_private_text(path: Path, text: str) -> None:
    secure_directory(path.parent)
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_APPEND | os.O_WRONLY,
        PRIVATE_FILE_MODE,
    )
    try:
        os.write(descriptor, text.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if os.name == "posix":
        path.chmod(PRIVATE_FILE_MODE)


def _fsync_directory(path: Path) -> None:
    if os.name != "posix":
        return
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, value: Any) -> None:
    secure_directory(path.parent)
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{os.urandom(8).hex()}"
    )
    descriptor = os.open(
        temporary,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        PRIVATE_FILE_MODE,
    )
    try:
        payload = canonical_json(value, newline=True)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name == "posix":
            path.chmod(PRIVATE_FILE_MODE)
        _fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise TeamRuntimeError(
            "E_CORRUPT_RUNTIME",
            "Runtime JSON could not be read.",
            {"path": os.fspath(path), "reason": str(exc)},
        ) from exc


class RuntimeLock(AbstractContextManager["RuntimeLock"]):
    """Cross-process lock; an abandoned lock file is safe after OS lock release."""

    def __init__(
        self, path: Path, timeout: float = DEFAULT_LOCK_TIMEOUT
    ) -> None:
        self.path = path
        self.timeout = timeout
        secure_directory(path.parent)
        self._lock = FileLock(path, timeout=timeout, mode=PRIVATE_FILE_MODE)

    def __enter__(self) -> "RuntimeLock":
        try:
            self._lock.acquire()
        except Timeout as exc:
            raise TeamRuntimeError(
                "E_LOCK_TIMEOUT",
                "Timed out waiting for a runtime lock.",
                {"lock": os.fspath(self.path)},
                retryable=True,
            ) from exc
        if os.name == "posix":
            self.path.chmod(PRIVATE_FILE_MODE)
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._lock.release()


class JsonStore:
    def __init__(self, path: Path, schema_name: str, lock_path: Path) -> None:
        self.path = path
        self.schema_name = schema_name
        self.lock_path = lock_path

    def _validate_value(self, value: dict[str, Any]) -> None:
        validate(self.schema_name, value)

    def read(self) -> dict[str, Any]:
        value = read_json(self.path)
        self._validate_value(value)
        return value

    def update(
        self,
        transform: Callable[[dict[str, Any]], dict[str, Any] | None],
        *,
        expected_revision: int | None = None,
        timeout: float = DEFAULT_LOCK_TIMEOUT,
    ) -> dict[str, Any]:
        with RuntimeLock(self.lock_path, timeout):
            current = self.read()
            if expected_revision is not None and current.get("revision") != expected_revision:
                raise TeamRuntimeError(
                    "E_IDEMPOTENCY_CONFLICT",
                    "Store revision does not match the expected revision.",
                    {
                        "actual_revision": current.get("revision"),
                        "expected_revision": expected_revision,
                        "path": os.fspath(self.path),
                    },
                )
            working = copy.deepcopy(current)
            replacement = transform(working)
            updated = working if replacement is None else replacement
            if updated.get("revision") != current.get("revision", -1) + 1:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "A mutable store update must increment revision exactly once.",
                    {"path": os.fspath(self.path)},
                )
            self._validate_value(updated)
            atomic_write_json(self.path, updated)
            return updated


class RegistryStore(JsonStore):
    def __init__(self, runtime_root: Path) -> None:
        super().__init__(
            runtime_root / "registry.json",
            "registry",
            runtime_root / "locks" / "registry.lock",
        )

    def _validate_value(self, value: dict[str, Any]) -> None:
        super()._validate_value(value)
        for slug, registration in value["projects"].items():
            if slug != registration.get("slug"):
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Registry key does not match the registered project slug.",
                    {"project_slug": slug},
                )


class ProjectStore(JsonStore):
    def __init__(
        self,
        runtime_root: Path,
        project_slug: str,
        filename: str,
        schema_name: str,
    ) -> None:
        if Path(filename).name != filename:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Project store filename must not contain a path.",
                {"filename": filename},
            )
        super().__init__(
            runtime_root / "projects" / project_slug / filename,
            schema_name,
            runtime_root / "locks" / f"project-{project_slug}.lock",
        )
        self.project_slug = project_slug

    def _validate_value(self, value: dict[str, Any]) -> None:
        super()._validate_value(value)
        actual_slug = value.get("project_slug", value.get("slug"))
        if actual_slug != self.project_slug:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Project store belongs to a different project.",
                {"project_slug": self.project_slug},
            )
        for item_id, item in value.get("items", {}).items():
            if item.get("id") != item_id:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Project store key does not match its object ID.",
                    {"item_id": item_id},
                )

    def write_locked(self, value: dict[str, Any]) -> dict[str, Any]:
        """Validate and replace a value while the caller holds the project lock."""
        self._validate_value(value)
        atomic_write_json(self.path, value)
        return value


class ImmutableProjectObjectStore:
    """Schema-valid immutable objects written under a caller-held project lock."""

    def __init__(
        self,
        runtime_root: Path,
        project_slug: str,
        directory: str,
        schema_name: str,
    ) -> None:
        if Path(directory).name != directory:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Project object directory must not contain a path.",
                {"directory": directory},
            )
        self.root = runtime_root / "projects" / project_slug / directory
        self.project_slug = project_slug
        self.schema_name = schema_name
        secure_directory(self.root)

    def _path(self, object_id: str) -> Path:
        if not object_id or Path(object_id).name != object_id:
            raise TeamRuntimeError(
                "E_GUARDRAIL_VIOLATION",
                "Project object ID must not contain a path.",
                {"object_id": object_id},
            )
        return self.root / f"{object_id}.json"

    def read(self, object_id: str) -> dict[str, Any]:
        value = read_json(self._path(object_id))
        validate(self.schema_name, value)
        if (
            value.get("id") != object_id
            or value.get("project_slug") != self.project_slug
        ):
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Immutable project object has inconsistent identity.",
                {"object_id": object_id},
            )
        return value

    def list(self) -> list[dict[str, Any]]:
        values = [self.read(path.stem) for path in sorted(self.root.glob("*.json"))]
        return values

    def create_locked(self, value: dict[str, Any]) -> dict[str, Any]:
        validate(self.schema_name, value)
        object_id = value.get("id")
        if not isinstance(object_id, str):
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME", "Immutable project object is missing its ID."
            )
        if value.get("project_slug") != self.project_slug:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Immutable project object belongs to a different project.",
                {"object_id": object_id},
            )
        path = self._path(object_id)
        if path.exists():
            existing = self.read(object_id)
            if canonical_json(existing) == canonical_json(value):
                return existing
            raise TeamRuntimeError(
                "E_IDEMPOTENCY_CONFLICT",
                "Immutable project object ID already has a different payload.",
                {"object_id": object_id},
            )
        atomic_write_json(path, value)
        return value


class EventLog:
    def __init__(self, runtime_root: Path) -> None:
        self.path = runtime_root / "events.jsonl"
        self.lock_path = runtime_root / "locks" / "events.lock"

    def read(self) -> EventReadResult:
        if not self.path.exists():
            return EventReadResult(())
        try:
            payload = self.path.read_bytes()
        except OSError as exc:
            raise TeamRuntimeError(
                "E_CORRUPT_RUNTIME",
                "Event log could not be read.",
                {"path": os.fspath(self.path), "reason": str(exc)},
            ) from exc
        lines = payload.splitlines(keepends=True)
        events: list[dict[str, Any]] = []
        trailing_corruption = False
        for index, line in enumerate(lines):
            complete = line.endswith(b"\n")
            try:
                event = json.loads(line)
                validate("event", event)
            except (json.JSONDecodeError, UnicodeDecodeError, TeamRuntimeError) as exc:
                if index == len(lines) - 1 and not complete:
                    trailing_corruption = True
                    break
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Event log contains a corrupt complete line.",
                    {"line": index + 1, "reason": str(exc)},
                ) from exc
            if not complete:
                trailing_corruption = True
                break
            events.append(event)
        return EventReadResult(tuple(events), trailing_corruption)

    def append(self, event: Event | dict[str, Any]) -> bool:
        value = event.to_dict() if isinstance(event, Event) else event
        validate("event", value)
        with RuntimeLock(self.lock_path):
            existing = self.read()
            if existing.trailing_corruption:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Event log has an incomplete trailing record; preserve it for recovery.",
                    {"path": os.fspath(self.path)},
                )
            encoded = canonical_json(value, newline=True)
            for prior in existing.events:
                same_id = prior["id"] == value["id"]
                same_key = prior["idempotency_key"] == value["idempotency_key"]
                if same_id or same_key:
                    if canonical_json(prior) == canonical_json(value):
                        return False
                    raise TeamRuntimeError(
                        "E_IDEMPOTENCY_CONFLICT",
                        "Event ID or idempotency key already has a different payload.",
                        {
                            "event_id": value["id"],
                            "idempotency_key": value["idempotency_key"],
                        },
                    )
            secure_directory(self.path.parent)
            descriptor = os.open(
                self.path,
                os.O_CREAT | os.O_APPEND | os.O_WRONLY,
                PRIVATE_FILE_MODE,
            )
            try:
                written = os.write(descriptor, encoded)
                if written != len(encoded):
                    raise OSError("short append")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if os.name == "posix":
                self.path.chmod(PRIVATE_FILE_MODE)
            return True


class IdempotencyGuard:
    def __init__(
        self, operations_dir: Path, project_lock: Path
    ) -> None:
        self.operations_dir = operations_dir
        self.project_lock = project_lock
        secure_directory(operations_dir)

    @staticmethod
    def payload_hash(payload: Any) -> str:
        return hashlib.sha256(canonical_json(payload)).hexdigest()

    def _path(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.operations_dir / f"{digest}.json"

    def prepare(
        self,
        key: str,
        payload: Any,
        event_id: str,
        *,
        object_refs: list[str] | None = None,
        target_hashes: dict[str, str | None] | None = None,
        target_revisions: dict[str, int] | None = None,
    ) -> IdempotencyRecord:
        digest = self.payload_hash(payload)
        expected_metadata = {
            "object_refs": sorted(object_refs or []),
            "target_hashes": target_hashes or {},
            "target_revisions": target_revisions or {},
        }
        with RuntimeLock(self.project_lock):
            path = self._path(key)
            if path.exists():
                record = read_json(path)
                actual_metadata = {
                    field: record.get(field, default)
                    for field, default in (
                        ("object_refs", []),
                        ("target_hashes", {}),
                        ("target_revisions", {}),
                    )
                }
                if (
                    record.get("key") != key
                    or record.get("payload_hash") != digest
                    or actual_metadata != expected_metadata
                ):
                    raise TeamRuntimeError(
                        "E_IDEMPOTENCY_CONFLICT",
                        "Idempotency key was reused with a different payload.",
                        {"key": key},
                    )
                return IdempotencyRecord(**record)
            record = {
                "event_id": event_id,
                "key": key,
                **expected_metadata,
                "payload_hash": digest,
                "result": None,
                "state": "Prepared",
            }
            atomic_write_json(path, record)
            return IdempotencyRecord(**record)

    def commit(self, key: str, payload: Any, result: dict[str, Any]) -> IdempotencyRecord:
        digest = self.payload_hash(payload)
        with RuntimeLock(self.project_lock):
            path = self._path(key)
            if not path.exists():
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "Cannot commit an operation that was not prepared.",
                    {"key": key},
                )
            record = read_json(path)
            if record.get("key") != key or record.get("payload_hash") != digest:
                raise TeamRuntimeError(
                    "E_IDEMPOTENCY_CONFLICT",
                    "Idempotency key was reused with a different payload.",
                    {"key": key},
                )
            if record.get("state") == "Committed":
                if record.get("result") != result:
                    raise TeamRuntimeError(
                        "E_IDEMPOTENCY_CONFLICT",
                        "Committed idempotency result does not match.",
                        {"key": key},
                    )
                return IdempotencyRecord(**record)
            record["state"] = "Committed"
            record["result"] = result
            atomic_write_json(path, record)
            return IdempotencyRecord(**record)


def private_mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)
