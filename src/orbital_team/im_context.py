from __future__ import annotations

import copy
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .models import Event
from .runtime import RuntimeManager, stable_uuid4, utc_now
from .schema import validate
from .storage import (
    EventLog,
    IdempotencyGuard,
    ProjectStore,
    RuntimeLock,
    canonical_json,
)


EXTRACTOR_VERSION = "fixture-v1"
DEFAULT_FIXTURE = Path("demo/im-fixtures/messages.json")
_ACTOR = re.compile(r"^(?:human|manager|member|system):[^:]+$")


@runtime_checkable
class IMContextProvider(Protocol):
    """Read-only seam implemented by fixture v1 and future IM adapters."""

    name: str

    def list_conversations(self) -> list[dict[str, str]]: ...

    def fetch_messages(self, conversation_id: str) -> list[dict[str, Any]]: ...

    def message_reference(self, message: dict[str, Any]) -> str: ...


class FixtureIMProvider:
    """Offline provider for synthetic, versioned fixture messages."""

    name = "fixture"

    def __init__(self, fixture_path: str | os.PathLike[str]) -> None:
        self.path = Path(fixture_path)
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "IM fixture could not be read.",
                {"fixture": os.fspath(self.path), "reason": str(exc)},
            ) from exc
        if (
            not isinstance(value, dict)
            or value.get("kind") != "orbital-team-im-fixture"
            or value.get("version") != 1
            or not isinstance(value.get("conversations"), list)
        ):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "IM fixture envelope is invalid."
            )
        self._conversations: dict[str, dict[str, Any]] = {}
        for conversation in value["conversations"]:
            if not isinstance(conversation, dict):
                raise TeamRuntimeError("E_VALIDATION_FAILED", "Conversation is invalid.")
            conversation_id = conversation.get("id")
            messages = conversation.get("messages")
            if (
                not isinstance(conversation_id, str)
                or not conversation_id
                or conversation_id in self._conversations
                or not isinstance(messages, list)
            ):
                raise TeamRuntimeError(
                    "E_VALIDATION_FAILED", "Conversation identity or messages are invalid."
                )
            normalized: list[dict[str, Any]] = []
            seen: set[str] = set()
            for raw in messages:
                if not isinstance(raw, dict):
                    raise TeamRuntimeError("E_VALIDATION_FAILED", "Fixture message is invalid.")
                message = copy.deepcopy(raw)
                message.setdefault("provider", self.name)
                message.setdefault("conversation_id", conversation_id)
                try:
                    validate("imMessage", message)
                except TeamRuntimeError as exc:
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED",
                        "Fixture message does not match ContextItem schema.",
                        {"conversation_id": conversation_id, **exc.details},
                    ) from exc
                if message["provider"] != self.name or message["conversation_id"] != conversation_id:
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED", "Fixture message binding is inconsistent."
                    )
                if message["message_id"] in seen:
                    raise TeamRuntimeError(
                        "E_VALIDATION_FAILED", "Fixture message IDs must be unique per conversation."
                    )
                seen.add(message["message_id"])
                normalized.append(message)
            self._conversations[conversation_id] = {
                "display_name": str(conversation.get("display_name", conversation_id)),
                "messages": normalized,
            }

    def list_conversations(self) -> list[dict[str, str]]:
        return [
            {"display_name": value["display_name"], "id": conversation_id}
            for conversation_id, value in sorted(self._conversations.items())
        ]

    def fetch_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        conversation = self._conversations.get(conversation_id)
        if conversation is None:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "Fixture conversation was not found.",
                {"conversation_id": conversation_id},
            )
        return copy.deepcopy(conversation["messages"])

    def message_reference(self, message: dict[str, Any]) -> str:
        return message.get("permalink") or (
            f"fixture:{message['conversation_id']}:{message['message_id']}"
        )


class IMProviderRegistry:
    """Explicit provider registry; v1 registers no network-backed adapters."""

    def __init__(self) -> None:
        self._providers: dict[str, IMContextProvider] = {}

    def register(self, provider: IMContextProvider) -> None:
        if not isinstance(provider, IMContextProvider) or not provider.name:
            raise TeamRuntimeError("E_VALIDATION_FAILED", "IM provider is invalid.")
        if provider.name in self._providers:
            raise TeamRuntimeError(
                "E_IDEMPOTENCY_CONFLICT", "IM provider is already registered."
            )
        self._providers[provider.name] = provider

    def get(self, name: str) -> IMContextProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED",
                "IM provider is unavailable; v1 supports fixture only.",
                {"provider": name},
            )
        return provider


def _field(text: str, name: str) -> str | None:
    prefix = f"{name}:"
    for line in text.splitlines():
        if line.upper().startswith(prefix):
            value = line[len(prefix) :].strip()
            return value or None
    return None


def extract_fixture_candidates(message: dict[str, Any]) -> list[dict[str, Any]]:
    """Deterministic bounded extractor for the documented synthetic fixture grammar."""
    validate("imMessage", message)
    text = message["text"].strip()
    if not text:
        raise TeamRuntimeError("E_VALIDATION_FAILED", "ContextItem text is empty.")
    if len(text) > 2000:
        raise TeamRuntimeError(
            "E_VALIDATION_FAILED", "Fixture extraction input exceeds 2000 characters."
        )
    evidence = {
        "conversation_id": message["conversation_id"],
        "message_id": message["message_id"],
        "permalink": message["permalink"],
        "provider": message["provider"],
        "quote": text,
    }
    candidates: list[dict[str, Any]] = []
    title = _field(text, "TASK")
    summary = _field(text, "SUMMARY")
    if title or summary:
        if not title or not summary:
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Potential Task requires TASK and SUMMARY fields."
            )
        candidates.append(
            {
                "confidence": 0.9,
                "evidence": [evidence],
                "kind": "potential_task",
                "summary": summary,
                "suggested_title": title,
            }
        )
    question = _field(text, "QUESTION")
    if question:
        owner = _field(text, "OWNER") or "human:default-manager"
        blocking_text = (_field(text, "BLOCKING") or "false").casefold()
        if blocking_text not in {"true", "false"} or not _ACTOR.fullmatch(owner):
            raise TeamRuntimeError(
                "E_VALIDATION_FAILED", "Open Question owner or blocking value is invalid."
            )
        candidates.append(
            {
                "blocking": blocking_text == "true",
                "evidence": [evidence],
                "kind": "open_question",
                "owner": owner,
                "question": question,
                "relate_to_message_potential": title is not None,
            }
        )
    return candidates


class IMContextWorkflow:
    """Provider ingest and Potential Task/Open Question domain commands."""

    def __init__(self, workspace: str | os.PathLike[str]) -> None:
        self.manager = RuntimeManager(workspace)
        self.paths = self.manager.paths
        self.runtime_root = self.paths.runtime_root
        self.events = EventLog(self.runtime_root)

    def _project(self, query: str) -> tuple[str, dict[str, Any]]:
        registration = self.manager._resolve_registration(self.manager._registry(), query)
        slug = registration["slug"]
        return slug, self._store(slug, "project.json", "project").read()

    def project_query(self, query: str | None) -> str:
        if query is not None:
            return query
        registrations = list(self.manager._registry()["projects"].values())
        if len(registrations) != 1:
            raise TeamRuntimeError(
                "E_PROJECT_AMBIGUOUS",
                "--project is required when the runtime has multiple projects.",
                {"projects": sorted(item["slug"] for item in registrations)},
            )
        return registrations[0]["slug"]

    def _store(self, slug: str, filename: str, schema_name: str) -> ProjectStore:
        return ProjectStore(self.runtime_root, slug, filename, schema_name)

    def _lock(self, slug: str) -> Path:
        return self.paths.locks / f"project-{slug}.lock"

    def _guard(self, slug: str) -> IdempotencyGuard:
        return IdempotencyGuard(
            self.runtime_root / "projects" / slug / "operations", self._lock(slug)
        )

    @staticmethod
    def _request_key(command: str, request_id: str | None, payload: Any) -> str:
        suffix = request_id or hashlib.sha256(canonical_json(payload)).hexdigest()
        return f"command:{command}:{suffix}"

    def _prepare(
        self, slug: str, command: str, request_id: str | None, payload: Any
    ) -> tuple[IdempotencyGuard, str, dict[str, Any] | None]:
        key = self._request_key(command, request_id, payload)
        guard = self._guard(slug)
        record = guard.prepare(key, payload, stable_uuid4(key))
        if record.state == "Committed":
            if record.result is None:
                raise TeamRuntimeError("E_CORRUPT_RUNTIME", "Operation result is missing.")
            return guard, key, record.result
        return guard, key, None

    def _event(
        self,
        slug: str,
        event_type: str,
        event_key: str,
        actor: str,
        data: dict[str, Any],
        timestamp: str,
    ) -> None:
        prior = next(
            (
                item
                for item in self.events.read().events
                if item["idempotency_key"] == event_key
            ),
            None,
        )
        if prior is not None:
            if (
                prior["project_slug"] != slug
                or prior["type"] != event_type
                or prior["actor"] != actor
                or prior["data"] != data
            ):
                raise TeamRuntimeError(
                    "E_IDEMPOTENCY_CONFLICT",
                    "Existing event does not match the recovered transition.",
                    {"idempotency_key": event_key},
                )
            return
        self.events.append(
            Event(
                actor=actor,
                data=data,
                id=stable_uuid4(event_key),
                idempotency_key=event_key,
                project_slug=slug,
                schema_version=SCHEMA_VERSION,
                timestamp=timestamp,
                type=event_type,
            )
        )

    @staticmethod
    def _next_id(slug: str, marker: str, items: dict[str, Any]) -> str:
        values = [int(item_id.rsplit("-", 1)[1]) for item_id in items]
        return f"{slug}-{marker}-{max(values, default=0) + 1:04d}"

    def _potential(self, potential_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        match = re.fullmatch(r"(.+)-P-[0-9]{4,}", potential_id)
        if match is None:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Potential Task was not found.")
        slug, project = self._project(match.group(1))
        item = self._store(slug, "potential-tasks.json", "potentialTaskStore").read()["items"].get(potential_id)
        if item is None:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Potential Task was not found.")
        return slug, project, item

    def _question(self, question_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
        match = re.fullmatch(r"(.+)-Q-[0-9]{4,}", question_id)
        if match is None:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Open Question was not found.")
        slug, project = self._project(match.group(1))
        item = self._store(slug, "open-questions.json", "openQuestionStore").read()["items"].get(question_id)
        if item is None:
            raise TeamRuntimeError("E_TASK_NOT_FOUND", "Open Question was not found.")
        return slug, project, item

    @staticmethod
    def _actor(project: dict[str, Any]) -> str:
        return f"human:{project['active_manager_id']}"

    def ingest(
        self,
        project: str | None,
        provider: IMContextProvider,
        *,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        slug, _ = self._project(self.project_query(project))
        messages: list[dict[str, Any]] = []
        for conversation in provider.list_conversations():
            messages.extend(provider.fetch_messages(conversation["id"]))
        for message in messages:
            validate("imMessage", message)
            if message["provider"] != provider.name:
                raise TeamRuntimeError("E_VALIDATION_FAILED", "Provider binding is inconsistent.")
            if message["access_scope"] not in {"fixture", f"project:{slug}"}:
                raise TeamRuntimeError(
                    "E_FORBIDDEN_ACTOR",
                    "ContextItem is not accessible to this project.",
                    {"message_id": message["message_id"]},
                )
        payload = {"extractor_version": EXTRACTOR_VERSION, "messages": messages, "project_slug": slug, "provider": provider.name}
        guard, key, replay = self._prepare(slug, "context.ingest", request_id, payload)
        if replay is not None:
            return replay
        potential_store = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        question_store = self._store(slug, "open-questions.json", "openQuestionStore")
        produced_potential: list[dict[str, Any]] = []
        produced_questions: list[dict[str, Any]] = []
        with RuntimeLock(self._lock(slug)):
            potentials = potential_store.read()
            questions = question_store.read()
            for message in messages:
                candidates = extract_fixture_candidates(message)
                if not candidates:
                    continue
                message_potential: dict[str, Any] | None = None
                for candidate in candidates:
                    evidence = candidate["evidence"]
                    base = f"im:{provider.name}:{message['conversation_id']}:{message['message_id']}:{EXTRACTOR_VERSION}"
                    if candidate["kind"] == "potential_task":
                        dedupe_key = f"{base}:potential_task"
                        existing = next((item for item in potentials["items"].values() if item["dedupe_key"] == dedupe_key), None)
                        if existing is None:
                            now = utc_now()
                            potential_id = self._next_id(slug, "P", potentials["items"])
                            existing = {
                                "confidence": candidate["confidence"],
                                "created_at": now,
                                "created_by": "system:fixture",
                                "dedupe_key": dedupe_key,
                                "evidence": evidence,
                                "id": potential_id,
                                "project_slug": slug,
                                "promoted_task_id": None,
                                "revision": 0,
                                "state": "new",
                                "summary": candidate["summary"],
                                "suggested_title": candidate["suggested_title"],
                            }
                            validate("potentialTask", existing)
                            potentials["items"][potential_id] = existing
                            potentials["revision"] += 1
                            potential_store.write_locked(potentials)
                        elif (
                            existing["evidence"] != evidence
                            or existing["summary"] != candidate["summary"]
                            or existing["suggested_title"] != candidate["suggested_title"]
                        ):
                            raise TeamRuntimeError(
                                "E_IDEMPOTENCY_CONFLICT",
                                "A message identity produced different Potential Task content.",
                                {"dedupe_key": dedupe_key},
                            )
                        message_potential = existing
                        produced_potential.append(existing)
                        self._event(slug, "potential_task.created", f"{base}:potential_task", "system:fixture", {"potential_task_id": existing["id"]}, existing["created_at"])
                    else:
                        existing_question = next(
                            (
                                item for item in questions["items"].values()
                                if item["question"] == candidate["question"]
                                and any(e["provider"] == provider.name and e["conversation_id"] == message["conversation_id"] and e["message_id"] == message["message_id"] for e in item["evidence"])
                            ),
                            None,
                        )
                        if existing_question is None:
                            now = utc_now()
                            question_id = self._next_id(slug, "Q", questions["items"])
                            potential_ids = [message_potential["id"]] if candidate["relate_to_message_potential"] and message_potential else []
                            existing_question = {
                                "answer": None,
                                "blocking": candidate["blocking"],
                                "created_at": now,
                                "created_by": "system:fixture",
                                "evidence": evidence,
                                "id": question_id,
                                "owner": candidate["owner"],
                                "project_slug": slug,
                                "question": candidate["question"],
                                "related": {"job_ids": [], "potential_task_ids": potential_ids, "proposal_ids": [], "task_ids": []},
                                "revision": 0,
                                "state": "open",
                            }
                            validate("openQuestion", existing_question)
                            questions["items"][question_id] = existing_question
                            questions["revision"] += 1
                            question_store.write_locked(questions)
                        elif (
                            existing_question["evidence"] != evidence
                            or existing_question["blocking"] != candidate["blocking"]
                            or existing_question["owner"] != candidate["owner"]
                        ):
                            raise TeamRuntimeError(
                                "E_IDEMPOTENCY_CONFLICT",
                                "A message identity produced different Open Question content.",
                                {"message_id": message["message_id"]},
                            )
                        produced_questions.append(existing_question)
                        self._event(slug, "question.created", f"{base}:open_question", "system:fixture", {"question_id": existing_question["id"]}, existing_question["created_at"])
        result = {
            "context_items": len(messages),
            "ok": True,
            "potential_tasks": sorted(produced_potential, key=lambda item: item["id"]),
            "project_slug": slug,
            "questions": sorted(produced_questions, key=lambda item: item["id"]),
            "schema_version": SCHEMA_VERSION,
        }
        guard.commit(key, payload, result)
        return result

    def list_potential(self, project: str | None) -> dict[str, Any]:
        slug, _ = self._project(self.project_query(project))
        items = self._store(slug, "potential-tasks.json", "potentialTaskStore").read()["items"]
        return {"ok": True, "potential_tasks": sorted(items.values(), key=lambda item: item["id"]), "project_slug": slug, "schema_version": SCHEMA_VERSION}

    def triage(self, potential_id: str, note: str, *, request_id: str | None = None) -> dict[str, Any]:
        clean = note.strip()
        if not clean:
            raise TeamRuntimeError("E_USAGE", "Triage note is required.")
        slug, project, _ = self._potential(potential_id)
        payload = {"note": clean, "potential_task_id": potential_id}
        guard, key, replay = self._prepare(slug, "potential.triage", request_id, payload)
        if replay is not None:
            return replay
        store = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        with RuntimeLock(self._lock(slug)):
            values = store.read()
            current = values["items"][potential_id]
            if current["state"] == "triaged" and current.get("triage_note") == clean:
                updated = current
            else:
                if current["state"] != "new":
                    raise TeamRuntimeError("E_INVALID_TRANSITION", "Only a New Potential Task can be triaged.")
                updated = copy.deepcopy(current)
                updated.update(state="triaged", triage_note=clean, revision=current["revision"] + 1)
                values["items"][potential_id] = updated
                values["revision"] += 1
                store.write_locked(values)
            self._event(slug, "potential_task.triaged", f"potential:triaged:{potential_id}", self._actor(project), {"potential_task_id": potential_id}, utc_now())
        result = {"ok": True, "potential_task": updated, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def promote(self, potential_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        slug, project, _ = self._potential(potential_id)
        payload = {"potential_task_id": potential_id}
        guard, key, replay = self._prepare(slug, "potential.promote", request_id, payload)
        if replay is not None:
            return replay
        potential_store = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        task_store = self._store(slug, "tasks.json", "taskStore")
        question_store = self._store(slug, "open-questions.json", "openQuestionStore")
        with RuntimeLock(self._lock(slug)):
            potentials = potential_store.read()
            tasks = task_store.read()
            questions = question_store.read()
            current = potentials["items"][potential_id]
            existing_task = next((task for task in tasks["items"].values() if task.get("source_potential_task_id") == potential_id), None)
            if current["state"] == "promoted":
                if existing_task is None or current["promoted_task_id"] != existing_task["id"]:
                    raise TeamRuntimeError("E_CORRUPT_RUNTIME", "Promoted Potential Task has no matching Task.")
                task = existing_task
                updated = current
            else:
                if current["state"] != "triaged":
                    raise TeamRuntimeError("E_INVALID_TRANSITION", "Potential Task must be Triaged before Promote.")
                if not current["evidence"]:
                    raise TeamRuntimeError("E_VALIDATION_FAILED", "Potential Task source evidence is required.")
                now = utc_now()
                related_questions = [item for item in questions["items"].values() if potential_id in item["related"]["potential_task_ids"]]
                if existing_task is None:
                    task_id = self._next_id(slug, "T", tasks["items"])
                    task = {
                        "acceptance_criteria": [], "assignee": None,
                        "blocking_question_ids": sorted(item["id"] for item in related_questions if item["blocking"] and item["state"] in {"open", "deferred"}),
                        "created_at": now, "created_by": self._actor(project), "dependencies": [],
                        "description": current["summary"], "id": task_id, "labels": ["im-potential"], "paths": [],
                        "project_slug": slug, "revision": 0, "source_potential_task_id": potential_id,
                        "state": "draft", "title": current["suggested_title"], "updated_at": now,
                    }
                    validate("task", task)
                    tasks["items"][task_id] = task
                    tasks["revision"] += 1
                    task_store.write_locked(tasks)
                else:
                    task = existing_task
                changed_questions = False
                for item in related_questions:
                    if task["id"] not in item["related"]["task_ids"]:
                        item["related"]["task_ids"].append(task["id"])
                        item["related"]["task_ids"].sort()
                        item["revision"] += 1
                        changed_questions = True
                if changed_questions:
                    questions["revision"] += 1
                    question_store.write_locked(questions)
                updated = copy.deepcopy(current)
                updated.update(state="promoted", promoted_task_id=task["id"], revision=current["revision"] + 1)
                potentials["items"][potential_id] = updated
                potentials["revision"] += 1
                potential_store.write_locked(potentials)
            self._event(slug, "task.created", f"potential:promoted:{potential_id}:task", self._actor(project), {"potential_task_id": potential_id, "task_id": task["id"]}, task["created_at"])
            self._event(slug, "potential_task.promoted", f"potential:promoted:{potential_id}", self._actor(project), {"potential_task_id": potential_id, "task_id": task["id"]}, task["created_at"])
        result = {"ok": True, "potential_task": updated, "schema_version": SCHEMA_VERSION, "task": task}
        guard.commit(key, payload, result)
        return result

    def _terminal_potential(self, potential_id: str, state: str, field: str, value: str, event_type: str, *, request_id: str | None = None) -> dict[str, Any]:
        slug, project, _ = self._potential(potential_id)
        payload = {field: value, "potential_task_id": potential_id}
        guard, key, replay = self._prepare(slug, f"potential.{state}", request_id, payload)
        if replay is not None:
            return replay
        store = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        with RuntimeLock(self._lock(slug)):
            values = store.read()
            current = values["items"][potential_id]
            if current["state"] == state and current.get(field) == value:
                updated = current
            else:
                if current["state"] not in {"new", "triaged"}:
                    raise TeamRuntimeError("E_INVALID_TRANSITION", "Potential Task is already terminal.")
                updated = copy.deepcopy(current)
                updated.update(state=state, revision=current["revision"] + 1)
                updated[field] = value
                values["items"][potential_id] = updated
                values["revision"] += 1
                store.write_locked(values)
            self._event(slug, event_type, f"potential:{state}:{potential_id}", self._actor(project), {"potential_task_id": potential_id}, utc_now())
        result = {"ok": True, "potential_task": updated, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def dismiss(self, potential_id: str, reason: str, *, request_id: str | None = None) -> dict[str, Any]:
        clean = reason.strip()
        if not clean:
            raise TeamRuntimeError("E_USAGE", "Dismissal reason is required.")
        return self._terminal_potential(potential_id, "dismissed", "dismissal_reason", clean, "potential_task.dismissed", request_id=request_id)

    def duplicate(self, potential_id: str, target_id: str, *, request_id: str | None = None) -> dict[str, Any]:
        if potential_id == target_id:
            raise TeamRuntimeError("E_VALIDATION_FAILED", "Potential Task cannot duplicate itself.")
        slug, _, _ = self._potential(potential_id)
        target_slug, _, _ = self._potential(target_id)
        if slug != target_slug:
            raise TeamRuntimeError("E_VALIDATION_FAILED", "Duplicate target must belong to the same project.")
        return self._terminal_potential(potential_id, "duplicate", "duplicate_of", target_id, "potential_task.duplicated", request_id=request_id)

    def convert_to_question(self, potential_id: str, owner: str, question: str, *, request_id: str | None = None) -> dict[str, Any]:
        clean = question.strip()
        if not clean or not _ACTOR.fullmatch(owner):
            raise TeamRuntimeError("E_USAGE", "Question and valid owner are required.")
        slug, project, _ = self._potential(potential_id)
        payload = {"owner": owner, "potential_task_id": potential_id, "question": clean}
        guard, key, replay = self._prepare(slug, "potential.question", request_id, payload)
        if replay is not None:
            return replay
        potential_store = self._store(slug, "potential-tasks.json", "potentialTaskStore")
        question_store = self._store(slug, "open-questions.json", "openQuestionStore")
        with RuntimeLock(self._lock(slug)):
            potentials = potential_store.read(); questions = question_store.read(); current = potentials["items"][potential_id]
            existing = next((item for item in questions["items"].values() if potential_id in item["related"]["potential_task_ids"] and item["question"] == clean), None)
            if current["state"] == "dismissed" and current.get("converted_question_id"):
                question_value = questions["items"].get(current["converted_question_id"])
                if question_value is None:
                    raise TeamRuntimeError("E_CORRUPT_RUNTIME", "Converted Open Question is missing.")
                updated = current
            else:
                if current["state"] not in {"new", "triaged"}:
                    raise TeamRuntimeError("E_INVALID_TRANSITION", "Potential Task is already terminal.")
                now = utc_now()
                if existing is None:
                    question_id = self._next_id(slug, "Q", questions["items"])
                    question_value = {"answer": None, "blocking": False, "created_at": now, "created_by": self._actor(project), "evidence": current["evidence"], "id": question_id, "owner": owner, "project_slug": slug, "question": clean, "related": {"job_ids": [], "potential_task_ids": [potential_id], "proposal_ids": [], "task_ids": []}, "revision": 0, "state": "open"}
                    validate("openQuestion", question_value)
                    questions["items"][question_id] = question_value; questions["revision"] += 1; question_store.write_locked(questions)
                else:
                    question_value = existing
                updated = copy.deepcopy(current)
                updated.update(state="dismissed", dismissal_reason="Converted to Open Question", converted_question_id=question_value["id"], revision=current["revision"] + 1)
                potentials["items"][potential_id] = updated; potentials["revision"] += 1; potential_store.write_locked(potentials)
            self._event(slug, "question.created", f"potential:question:{potential_id}:created", self._actor(project), {"question_id": question_value["id"]}, question_value["created_at"])
            self._event(slug, "potential_task.converted_to_question", f"potential:question:{potential_id}", self._actor(project), {"potential_task_id": potential_id, "question_id": question_value["id"]}, question_value["created_at"])
        result = {"ok": True, "potential_task": updated, "question": question_value, "schema_version": SCHEMA_VERSION}
        guard.commit(key, payload, result)
        return result

    def add_question(self, project: str, question: str, owner: str, *, blocking: bool = False, task_ids: list[str] | None = None, request_id: str | None = None) -> dict[str, Any]:
        slug, project_value = self._project(project); clean = question.strip(); related_tasks = sorted(set(task_ids or []))
        if not clean or not _ACTOR.fullmatch(owner):
            raise TeamRuntimeError("E_USAGE", "Question and valid owner are required.")
        payload = {"blocking": blocking, "owner": owner, "question": clean, "task_ids": related_tasks}
        guard, key, replay = self._prepare(slug, "question.add", request_id, payload)
        if replay is not None: return replay
        question_store = self._store(slug, "open-questions.json", "openQuestionStore"); task_store = self._store(slug, "tasks.json", "taskStore")
        with RuntimeLock(self._lock(slug)):
            questions = question_store.read(); tasks = task_store.read()
            missing = [task_id for task_id in related_tasks if task_id not in tasks["items"]]
            if missing: raise TeamRuntimeError("E_TASK_NOT_FOUND", "Related Task was not found.", {"task_ids": missing})
            now = utc_now(); question_id = self._next_id(slug, "Q", questions["items"])
            value = {"answer": None, "blocking": blocking, "created_at": now, "created_by": self._actor(project_value), "evidence": [], "id": question_id, "owner": owner, "project_slug": slug, "question": clean, "related": {"job_ids": [], "potential_task_ids": [], "proposal_ids": [], "task_ids": related_tasks}, "revision": 0, "state": "open"}
            validate("openQuestion", value); questions["items"][question_id] = value; questions["revision"] += 1; question_store.write_locked(questions)
            self._event(slug, "question.created", f"question:created:{key}", self._actor(project_value), {"question_id": question_id}, now)
        result = {"ok": True, "question": value, "schema_version": SCHEMA_VERSION}; guard.commit(key, payload, result); return result

    def transition_question(self, question_id: str, action: str, *, text: str, deferred_until: str | None = None, request_id: str | None = None) -> dict[str, Any]:
        slug, project, observed = self._question(question_id); clean = text.strip()
        if not clean: raise TeamRuntimeError("E_USAGE", f"Question {action} text is required.")
        payload = {"action": action, "deferred_until": deferred_until, "question_id": question_id, "text": clean}
        guard, key, replay = self._prepare(slug, f"question.{action}", request_id, payload)
        if replay is not None: return replay
        actor = self._actor(project)
        if actor != observed["owner"]: raise TeamRuntimeError("E_FORBIDDEN_ACTOR", "Only the Open Question owner can change it.")
        store = self._store(slug, "open-questions.json", "openQuestionStore")
        transitions = {"answer": ({"open", "deferred"}, "answered", "question.answered"), "defer": ({"open"}, "deferred", "question.deferred"), "reopen": ({"deferred"}, "open", "question.reopened"), "close": ({"answered", "deferred"}, "closed", "question.closed")}
        if action not in transitions: raise TeamRuntimeError("E_USAGE", "Unknown question transition.")
        allowed, target, event_type = transitions[action]
        with RuntimeLock(self._lock(slug)):
            values = store.read(); current = values["items"][question_id]
            if current["state"] == target and (action != "answer" or current["answer"] == clean): updated = current
            else:
                if current["state"] not in allowed: raise TeamRuntimeError("E_INVALID_TRANSITION", "Open Question cannot transition from its current state.")
                updated = copy.deepcopy(current); updated.update(state=target, revision=current["revision"] + 1)
                if action == "answer": updated["answer"] = clean
                if action == "defer": updated["deferred_until"] = deferred_until
                values["items"][question_id] = updated; values["revision"] += 1; store.write_locked(values)
            now = utc_now()
            event_data = {"question_id": question_id}
            if action != "answer":
                event_data["reason"] = clean
            self._event(slug, event_type, f"question:{action}:{question_id}:r{updated['revision']}", actor, event_data, now)
            if action == "answer":
                for job_id in updated["related"]["job_ids"]:
                    from .manager_integration import ManagerIntegrationWorkflow

                    job = ManagerIntegrationWorkflow(self.paths.repository_root).jobs.read(job_id)
                    if job["state"] == "blocked" and job["block_kind"] == "knowledge":
                        self._event(slug, "knowledge.resume_requested", f"knowledge:resume_requested:{job_id}:q{question_id}:r{updated['revision']}", actor, {"job_id": job_id, "question_id": question_id}, now)
        result = {"ok": True, "question": updated, "schema_version": SCHEMA_VERSION}; guard.commit(key, payload, result); return result
