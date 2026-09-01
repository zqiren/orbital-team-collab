from __future__ import annotations

import argparse
import copy
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from .constants import SCHEMA_VERSION
from .errors import TeamRuntimeError
from .member_workflow import MemberWorkflow
from .models import Event
from .runtime import stable_uuid4, utc_now
from .storage import (
    EventLog,
    RunRecordStore,
    RuntimeLock,
    secure_empty_file,
)


MAX_SESSION_SUMMARY_BYTES = 4096
PROTECTED_INPUT_OPTIONS = ("--actor", "--member", "--workspace")
REPORT_VALUE_OPTIONS = {
    "--commit",
    "--knowledge-candidate",
    "--request-id",
    "--risk",
    "--summary",
    "--validation",
}


@dataclass(frozen=True, slots=True)
class TeamCommand:
    action: str
    cli_argv: tuple[str, ...]


def _usage(message: str) -> TeamRuntimeError:
    return TeamRuntimeError("E_USAGE", message)


def _reject_identity_options(tokens: Sequence[str]) -> None:
    rejected = [
        token
        for token in tokens
        if any(token == name or token.startswith(name + "=") for name in PROTECTED_INPUT_OPTIONS)
    ]
    if rejected:
        raise TeamRuntimeError(
            "E_FORBIDDEN_ACTOR",
            "The /team adapter derives identity and workspace from the current worktree.",
            {"options": rejected},
        )


def _report_args(tokens: Sequence[str]) -> list[str]:
    if not tokens:
        raise _usage("Usage: /team report <task-id> [report options]")
    argv = ["report", "submit", tokens[0]]
    index = 1
    while index < len(tokens):
        option = tokens[index]
        if option not in REPORT_VALUE_OPTIONS or index + 1 >= len(tokens):
            raise _usage(f"Unsupported or incomplete /team report option: {option}")
        argv.extend((option, tokens[index + 1]))
        index += 2
    return argv


def parse_team_command(text: str) -> TeamCommand:
    try:
        tokens = shlex.split(text)
    except ValueError as exc:
        raise _usage(f"Invalid /team quoting: {exc}") from exc
    if tokens and tokens[0] == "/team":
        tokens = tokens[1:]
    if not tokens:
        raise _usage(
            "Usage: /team claim|start|report|block|status|questions|manager ..."
        )
    _reject_identity_options(tokens)
    action, arguments = tokens[0], tokens[1:]
    if action == "claim":
        if len(arguments) < 2:
            raise _usage("Usage: /team claim <project-name> <task-id-or-query>")
        cli = ["claim", "--project", arguments[0], "--query", " ".join(arguments[1:])]
    elif action == "start":
        if len(arguments) != 1:
            raise _usage("Usage: /team start <task-id>")
        cli = ["task", "start", arguments[0]]
    elif action == "report":
        cli = _report_args(arguments)
    elif action == "block":
        if len(arguments) < 2:
            raise _usage("Usage: /team block <task-id> <reason>")
        reason = arguments[1:]
        if reason[0] == "--reason":
            reason = reason[1:]
        if not reason:
            raise _usage("Block reason must not be empty.")
        cli = ["task", "block", arguments[0], "--reason", " ".join(reason)]
    elif action == "status":
        if len(arguments) > 1:
            raise _usage("Usage: /team status [task-id]")
        cli = ["task", "status", *arguments]
    elif action == "questions":
        if len(arguments) != 1:
            raise _usage("Usage: /team questions <project-name>")
        cli = ["question", "list", "--project", arguments[0]]
    elif action == "manager":
        if not arguments:
            arguments = ["inbox"]
        if arguments[0] != "inbox" or len(arguments) > 2:
            raise _usage("Usage: /team manager inbox [project-name]")
        cli = ["manager", "inbox"]
        if len(arguments) == 2:
            cli.extend(("--project", arguments[1]))
    else:
        raise _usage(f"Unknown /team action: {action}")
    return TeamCommand(action=action, cli_argv=tuple(cli))


Executor = Callable[..., subprocess.CompletedProcess[str]]


def dispatch_team_command(
    text: str,
    workspace: str | os.PathLike[str],
    *,
    executor: Executor = subprocess.run,
) -> subprocess.CompletedProcess[str]:
    command = parse_team_command(text)
    root = Path(workspace).resolve()
    argv = [sys.executable, "-m", "orbital_team", *command.cli_argv, "--workspace", os.fspath(root)]
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    source_root = Path(__file__).resolve().parents[1]
    prior_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        [os.fspath(source_root), prior_pythonpath] if prior_pythonpath else [os.fspath(source_root)]
    )
    return executor(
        argv,
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def _project_lock(workflow: MemberWorkflow, slug: str) -> Path:
    return workflow.paths.locks / f"project-{slug}.lock"


def _existing_event(events: EventLog, key: str) -> dict[str, Any] | None:
    return next(
        (item for item in events.read().events if item["idempotency_key"] == key),
        None,
    )


def _append_run_event(
    events: EventLog,
    *,
    actor: str,
    data: dict[str, Any],
    event_type: str,
    key: str,
    slug: str,
    timestamp: str,
) -> str:
    existing = _existing_event(events, key)
    if existing is not None:
        return existing["timestamp"]
    try:
        events.append(
            Event(
                actor=actor,
                data=data,
                id=stable_uuid4(key),
                idempotency_key=key,
                project_slug=slug,
                schema_version=SCHEMA_VERSION,
                timestamp=timestamp,
                type=event_type,
            )
        )
    except TeamRuntimeError as exc:
        if exc.code != "E_IDEMPOTENCY_CONFLICT":
            raise
        raced = _existing_event(events, key)
        if raced is None:
            raise
        return raced["timestamp"]
    return timestamp


def _active_task(tasks: Sequence[dict[str, Any]]) -> dict[str, Any] | None:
    priority = {
        "in_progress": 0,
        "claimed": 1,
        "blocked": 2,
        "changes_requested": 3,
        "submitted": 4,
        "integrating": 5,
    }
    return min(tasks, key=lambda item: (priority.get(item["state"], 99), item["id"]), default=None)


def record_member_session(
    workspace: str | os.PathLike[str],
    hook_input: dict[str, Any],
    *,
    provider: str = "agent-neutral",
) -> list[dict[str, Any]]:
    hook_event = hook_input.get("hook_event_name")
    if hook_event is not None and hook_event != "SessionStart":
        raise TeamRuntimeError(
            "E_USAGE", "Member session adapter only accepts SessionStart lifecycle input."
        )
    workflow = MemberWorkflow(workspace)
    bindings = workflow.workspace_bindings()
    session_value = hook_input.get("session_id")
    provider_session_id = (
        session_value.strip()
        if isinstance(session_value, str) and session_value.strip()
        else None
    )
    transcript_value = hook_input.get("transcript_path")
    transcript_path = (
        transcript_value
        if isinstance(transcript_value, str) and transcript_value.strip()
        else None
    )
    source_value = hook_input.get("source")
    source = source_value if isinstance(source_value, str) and source_value else "startup"
    events = EventLog(workflow.runtime_root)
    recorded: list[dict[str, Any]] = []
    for binding in bindings:
        slug = binding["project"]["slug"]
        member = binding["member"]
        task = _active_task(binding["tasks"])
        local_identity = provider_session_id or (
            f"unavailable:{os.getppid()}:{member['id']}:{member['branch']}"
        )
        run_id = f"{slug}-RUN-{stable_uuid4(f'member-run:{slug}:{local_identity}')}"
        store = RunRecordStore(workflow.runtime_root, slug)
        actor = f"member:{member['id']}"
        now = utc_now()
        log_root = store.root / run_id
        with RuntimeLock(_project_lock(workflow, slug)):
            current = store.read(run_id) if store.exists(run_id) else None
            secure_empty_file(log_root / "stdout.log")
            secure_empty_file(log_root / "stderr.log")
            if current is None:
                record = {
                    "actor": actor,
                    "agent_type": member["agent_type"] or provider,
                    "ended_at": None,
                    "id": run_id,
                    "job_id": None,
                    "log_paths": {
                        "stderr": f"runs/{run_id}/stderr.log",
                        "stdout": f"runs/{run_id}/stdout.log",
                        "transcript": transcript_path,
                    },
                    "project_slug": slug,
                    "provider_session_id": provider_session_id,
                    "revision": 0,
                    "started_at": now,
                    "state": "running",
                    "task_id": task["id"] if task else None,
                }
            else:
                if current["actor"] != actor:
                    raise TeamRuntimeError(
                        "E_FORBIDDEN_ACTOR",
                        "Provider session is already bound to another member actor.",
                    )
                record = copy.deepcopy(current)
                desired_task = task["id"] if task else None
                changed = False
                if record["task_id"] != desired_task:
                    record["task_id"] = desired_task
                    changed = True
                if transcript_path and record["log_paths"]["transcript"] != transcript_path:
                    record["log_paths"]["transcript"] = transcript_path
                    changed = True
                if changed:
                    record["revision"] += 1
            store.write_locked(record)
        started_key = f"member:run:started:{run_id}"
        _append_run_event(
            events,
            actor=actor,
            data={"branch": member["branch"], "run_id": run_id},
            event_type="run.started",
            key=started_key,
            slug=slug,
            timestamp=record["started_at"],
        )
        seen_key = f"member:run:seen:{run_id}:{source}:{record['task_id'] or 'none'}"
        last_seen = _append_run_event(
            events,
            actor=actor,
            data={
                "branch": member["branch"],
                "provider": provider,
                "run_id": run_id,
                "task_id": record["task_id"],
            },
            event_type="run.seen",
            key=seen_key,
            slug=slug,
            timestamp=now,
        )
        recorded.append({"binding": binding, "last_seen": last_seen, "run": record})
    return recorded


def _bounded_summary(text: str) -> str:
    payload = text.encode("utf-8")
    if len(payload) <= MAX_SESSION_SUMMARY_BYTES:
        return text
    return payload[: MAX_SESSION_SUMMARY_BYTES - 4].decode("utf-8", errors="ignore").rstrip() + " ..."


def session_start_summary(
    workspace: str | os.PathLike[str],
    hook_input: dict[str, Any],
    *,
    provider: str = "agent-neutral",
) -> str:
    records = record_member_session(workspace, hook_input, provider=provider)
    if not records:
        return _bounded_summary(
            "Orbital Team: this worktree has no joined member identity. "
            "Ask the project owner to run `teamctl member join --project <project> "
            "--member <id> --agent <agent-type>` here; no task was claimed."
        )
    lines = ["# Orbital Team Member Context"]
    for item in records:
        binding = item["binding"]
        member = binding["member"]
        lines.extend(
            [
                "",
                f"- Project: {binding['project']['display_name']} ({binding['project']['slug']})",
                f"- Identity: member:{member['id']} · agent {member['agent_type']}",
                f"- Worktree branch: {member['branch']}",
                f"- Member run: {item['run']['id']} · last seen {item['last_seen']}",
            ]
        )
        tasks = binding["tasks"][:8]
        lines.append("- Assigned tasks: " + (
            "; ".join(f"{task['id']} [{task['state']}] {task['title']}" for task in tasks)
            if tasks
            else "none"
        ))
        questions = binding["questions"][:8]
        lines.append("- Pending questions: " + (
            "; ".join(f"{question['id']} [{question['state']}] {question['question']}" for question in questions)
            if questions
            else "none"
        ))
    lines.extend(
        [
            "",
            "Use `/team claim|start|report|block|status|questions|manager`; "
            "identity always comes from this worktree binding. SessionStart did not claim a task.",
        ]
    )
    return _bounded_summary("\n".join(lines))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orbital-team-member-adapter")
    commands = parser.add_subparsers(dest="command", required=True)
    dispatch = commands.add_parser("dispatch")
    dispatch.add_argument("--workspace", default=".")
    dispatch.add_argument("--command", required=True, dest="team_command")
    session = commands.add_parser("session-start")
    session.add_argument("--workspace", default=".")
    session.add_argument("--provider", default="claude-code")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "dispatch":
            result = dispatch_team_command(arguments.team_command, arguments.workspace)
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
        try:
            hook_input = json.load(sys.stdin)
        except json.JSONDecodeError as exc:
            raise TeamRuntimeError("E_USAGE", "SessionStart input must be JSON.") from exc
        if not isinstance(hook_input, dict):
            raise TeamRuntimeError("E_USAGE", "SessionStart input must be a JSON object.")
        print(
            session_start_summary(
                arguments.workspace, hook_input, provider=arguments.provider
            )
        )
        return 0
    except TeamRuntimeError as exc:
        print(json.dumps(exc.response(), sort_keys=True), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
