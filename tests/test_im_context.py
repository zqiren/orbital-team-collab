from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

from orbital_team.cli import main as cli_main
from orbital_team.errors import TeamRuntimeError
from orbital_team.im_context import (
    FixtureIMProvider,
    IMContextProvider,
    IMProviderRegistry,
    IMContextWorkflow,
)
from orbital_team.member_workflow import MemberWorkflow
from orbital_team.runtime import RuntimeManager
from orbital_team.schema import validate
from orbital_team.storage import EventLog, ProjectStore

from tests.test_runtime_kernel import GitRepository, git_env


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "demo" / "im-fixtures" / "messages.json"


class IMContextWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = mock.patch.dict(os.environ, git_env(), clear=True)
        self.environment.start()
        self.repo = GitRepository()
        self.runtime = RuntimeManager(self.repo.repository)
        self.runtime_root = Path(self.runtime.init_project("Apollo")["runtime_root"])
        self.workflow = IMContextWorkflow(self.repo.repository)
        self.provider = FixtureIMProvider(FIXTURE)

    def tearDown(self) -> None:
        self.repo.close()
        self.environment.stop()

    def ingest(self, *, request_id: str | None = None) -> dict[str, object]:
        return self.workflow.ingest("apollo", self.provider, request_id=request_id)

    def write_fixture(
        self,
        filename: str,
        messages: list[dict[str, object]],
    ) -> Path:
        path = self.repo.root / filename
        value = {
            "conversations": [
                {
                    "display_name": "Synthetic test conversation",
                    "id": "fixture-test",
                    "messages": messages,
                }
            ],
            "kind": "orbital-team-im-fixture",
            "version": 1,
        }
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    @staticmethod
    def message(
        message_id: str,
        text: str,
        *,
        access_scope: str = "fixture",
    ) -> dict[str, object]:
        return {
            "access_scope": access_scope,
            "conversation_id": "fixture-test",
            "message_id": message_id,
            "permalink": None,
            "provider": "fixture",
            "sender": "synthetic-user",
            "text": text,
            "timestamp": "2026-09-01T10:00:00Z",
        }

    def test_fixture_provider_contract_and_context_item_schema(self) -> None:
        self.assertIsInstance(self.provider, IMContextProvider)
        registry = IMProviderRegistry()
        registry.register(self.provider)
        self.assertIs(self.provider, registry.get("fixture"))
        with self.assertRaises(TeamRuntimeError):
            registry.get("network-provider")
        conversations = self.provider.list_conversations()
        self.assertEqual(["fixture-planning"], [item["id"] for item in conversations])
        messages = self.provider.fetch_messages("fixture-planning")
        self.assertEqual(2, len(messages))
        for message in messages:
            validate("imMessage", message)
            self.assertTrue(self.provider.message_reference(message).startswith("fixture:"))

    def test_ingest_extracts_separate_evidenced_potential_and_question(self) -> None:
        result = self.ingest()
        self.assertEqual(2, result["context_items"])
        self.assertEqual(1, len(result["potential_tasks"]))
        self.assertEqual(1, len(result["questions"]))
        potential = result["potential_tasks"][0]
        question = result["questions"][0]
        validate("potentialTask", potential)
        validate("openQuestion", question)
        self.assertEqual("new", potential["state"])
        self.assertEqual([potential["id"]], question["related"]["potential_task_ids"])
        self.assertEqual("fixture-message-001", potential["evidence"][0]["message_id"])
        self.assertTrue(question["blocking"])

    def test_repeat_ingest_deduplicates_candidates_and_events(self) -> None:
        first = self.ingest(request_id="same-ingest")
        second = self.ingest(request_id="same-ingest")
        third = self.ingest(request_id="different-request")
        self.assertEqual(first, second)
        self.assertEqual(first["potential_tasks"], third["potential_tasks"])
        potentials = ProjectStore(
            self.runtime_root, "apollo", "potential-tasks.json", "potentialTaskStore"
        ).read()
        questions = ProjectStore(
            self.runtime_root, "apollo", "open-questions.json", "openQuestionStore"
        ).read()
        self.assertEqual(1, len(potentials["items"]))
        self.assertEqual(1, len(questions["items"]))
        event_types = [event["type"] for event in EventLog(self.runtime_root).read().events]
        self.assertEqual(1, event_types.count("potential_task.created"))
        self.assertEqual(1, event_types.count("question.created"))

    def test_source_validation_rejects_empty_missing_and_inaccessible_messages(self) -> None:
        invalid_messages = [
            self.message("empty", ""),
            {key: value for key, value in self.message("missing", "TASK: X\nSUMMARY: Y").items() if key != "permalink"},
        ]
        for index, message in enumerate(invalid_messages):
            fixture = self.write_fixture(f"invalid-{index}.json", [message])
            with self.assertRaises(TeamRuntimeError) as raised:
                FixtureIMProvider(fixture)
            self.assertEqual("E_VALIDATION_FAILED", raised.exception.code)
        denied = self.write_fixture(
            "denied.json",
            [self.message("denied", "TASK: X\nSUMMARY: Y", access_scope="private:other")],
        )
        with self.assertRaises(TeamRuntimeError) as raised:
            self.workflow.ingest("apollo", FixtureIMProvider(denied))
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)
        self.assertEqual([], self.workflow.list_potential("apollo")["potential_tasks"])

    def test_potential_is_not_claimable_and_promote_requires_triage(self) -> None:
        potential = self.ingest()["potential_tasks"][0]
        MemberWorkflow(self.repo.repository).join_member("apollo", "fixture-member", "test")
        with self.assertRaises(TeamRuntimeError) as raised:
            MemberWorkflow(self.repo.repository).claim("apollo", potential["id"])
        self.assertEqual("E_TASK_NOT_FOUND", raised.exception.code)
        with self.assertRaises(TeamRuntimeError) as raised:
            self.workflow.promote(potential["id"])
        self.assertEqual("E_INVALID_TRANSITION", raised.exception.code)
        tasks = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual({}, tasks["items"])

    def test_promote_creates_one_draft_then_blocking_question_gates_ready(self) -> None:
        potential = self.ingest()["potential_tasks"][0]
        self.workflow.triage(potential["id"], "Scope is useful and needs a decision.")
        first = self.workflow.promote(potential["id"], request_id="promote")
        second = self.workflow.promote(potential["id"], request_id="promote")
        self.assertEqual(first, second)
        task = first["task"]
        self.assertEqual("draft", task["state"])
        self.assertEqual(potential["id"], task["source_potential_task_id"])
        self.assertEqual(first["potential_task"]["promoted_task_id"], task["id"])
        with self.assertRaises(TeamRuntimeError) as raised:
            MemberWorkflow(self.repo.repository).ready_task(task["id"])
        self.assertEqual("E_BLOCKING_QUESTION", raised.exception.code)
        question_id = task["blocking_question_ids"][0]
        self.workflow.transition_question(question_id, "answer", text="Group by provider.")
        ready = MemberWorkflow(self.repo.repository).ready_task(task["id"])["task"]
        self.assertEqual("ready", ready["state"])
        tasks = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual(1, len(tasks["items"]))

    def test_promote_recovers_after_task_write_without_duplicate(self) -> None:
        potential = self.ingest()["potential_tasks"][0]
        self.workflow.triage(potential["id"], "Approved for promotion.")
        original = ProjectStore.write_locked
        failed = False

        def interrupt(store: ProjectStore, value: dict[str, object]) -> dict[str, object]:
            nonlocal failed
            if store.path.name == "potential-tasks.json" and not failed:
                failed = True
                raise RuntimeError("simulated crash after task write")
            return original(store, value)

        with mock.patch.object(ProjectStore, "write_locked", interrupt):
            with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                self.workflow.promote(potential["id"], request_id="recover-promote")
        recovered = self.workflow.promote(potential["id"], request_id="recover-promote")
        self.assertEqual("promoted", recovered["potential_task"]["state"])
        tasks = ProjectStore(self.runtime_root, "apollo", "tasks.json", "taskStore").read()
        self.assertEqual(1, len(tasks["items"]))
        events = EventLog(self.runtime_root).read().events
        self.assertEqual(1, sum(event["type"] == "task.created" for event in events))
        self.assertEqual(1, sum(event["type"] == "potential_task.promoted" for event in events))

    def test_dismiss_duplicate_and_convert_are_terminal_and_idempotent(self) -> None:
        first = self.ingest()["potential_tasks"][0]
        extra_fixture = self.write_fixture(
            "extra.json",
            [self.message("extra", "TASK: Add timeout metric\nSUMMARY: Record timeout totals.")],
        )
        second = self.workflow.ingest("apollo", FixtureIMProvider(extra_fixture))["potential_tasks"][0]
        duplicate = self.workflow.duplicate(second["id"], first["id"], request_id="duplicate")
        self.assertEqual("duplicate", duplicate["potential_task"]["state"])
        self.assertEqual(first["id"], duplicate["potential_task"]["duplicate_of"])
        self.assertEqual(duplicate, self.workflow.duplicate(second["id"], first["id"], request_id="duplicate"))

        third_fixture = self.write_fixture(
            "third.json",
            [self.message("third", "TASK: Clarify retention\nSUMMARY: Decide metric retention.")],
        )
        third = self.workflow.ingest("apollo", FixtureIMProvider(third_fixture))["potential_tasks"][0]
        dismissed = self.workflow.dismiss(third["id"], "Not planned", request_id="dismiss")
        self.assertEqual("dismissed", dismissed["potential_task"]["state"])
        self.assertEqual(dismissed, self.workflow.dismiss(third["id"], "Not planned", request_id="dismiss"))

        fourth_fixture = self.write_fixture(
            "fourth.json",
            [self.message("fourth", "TASK: Choose dashboard color\nSUMMARY: Select the status palette.")],
        )
        fourth = self.workflow.ingest("apollo", FixtureIMProvider(fourth_fixture))["potential_tasks"][0]
        converted = self.workflow.convert_to_question(
            fourth["id"], "human:default-manager", "Which status palette is approved?"
        )
        self.assertEqual("dismissed", converted["potential_task"]["state"])
        self.assertEqual(converted["question"]["id"], converted["potential_task"]["converted_question_id"])

    def test_question_lifecycle_and_owner_spoof_are_enforced(self) -> None:
        added = self.workflow.add_question(
            "apollo", "Which deployment window?", "human:default-manager"
        )["question"]
        deferred = self.workflow.transition_question(
            added["id"], "defer", text="Waiting for release plan."
        )["question"]
        self.assertEqual("deferred", deferred["state"])
        reopened = self.workflow.transition_question(
            added["id"], "reopen", text="Release plan is available."
        )["question"]
        self.assertEqual("open", reopened["state"])
        answered = self.workflow.transition_question(
            added["id"], "answer", text="Tuesday 10:00 UTC."
        )["question"]
        self.assertEqual("answered", answered["state"])
        closed = self.workflow.transition_question(
            added["id"], "close", text="Decision recorded."
        )["question"]
        self.assertEqual("closed", closed["state"])
        foreign = self.workflow.add_question(
            "apollo", "Owner-only question", "human:someone-else"
        )["question"]
        with self.assertRaises(TeamRuntimeError) as raised:
            self.workflow.transition_question(foreign["id"], "answer", text="Spoofed")
        self.assertEqual("E_FORBIDDEN_ACTOR", raised.exception.code)

    def test_cli_fixture_ingest_and_potential_list(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli_main(
                [
                    "context", "ingest", "--provider", "fixture", "--project", "apollo",
                    "--fixture", os.fspath(FIXTURE), "--workspace", os.fspath(self.repo.repository),
                ]
            )
        self.assertEqual(0, code)
        self.assertEqual(1, len(json.loads(stdout.getvalue())["potential_tasks"]))
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli_main(["potential", "list", "--workspace", os.fspath(self.repo.repository)])
        self.assertEqual(0, code)
        self.assertEqual(1, len(json.loads(stdout.getvalue())["potential_tasks"]))


if __name__ == "__main__":
    unittest.main()
