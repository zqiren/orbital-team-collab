from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, TypedDict


class Registry(TypedDict):
    schema_version: str
    revision: int
    projects: dict[str, dict[str, Any]]


class RevisionedStore(TypedDict):
    schema_version: str
    project_slug: str
    revision: int
    items: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Event:
    actor: str
    data: dict[str, Any]
    id: str
    idempotency_key: str
    project_slug: str
    schema_version: str
    timestamp: str
    type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EventReadResult:
    events: tuple[dict[str, Any], ...]
    trailing_corruption: bool = False


@dataclass(frozen=True, slots=True)
class IdempotencyRecord:
    key: str
    payload_hash: str
    event_id: str
    object_refs: list[str]
    target_hashes: dict[str, str | None]
    target_revisions: dict[str, int]
    state: str
    result: dict[str, Any] | None
