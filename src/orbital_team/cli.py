from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Sequence, TextIO

from .errors import TeamRuntimeError
from .knowledge_workflow import KnowledgeWorkflow
from .manager_integration import ManagerIntegrationWorkflow
from .member_workflow import DEFAULT_CONTEXT_BUDGET, MemberWorkflow
from .runtime import RuntimeManager


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="teamctl")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize a project runtime")
    init.add_argument("--project", required=True)
    init.add_argument("--workspace", required=True)
    init.add_argument("--seed")

    status = commands.add_parser("status", help="read runtime status")
    status.add_argument("--project")
    status.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    reset = commands.add_parser("reset", help="remove only the local runtime")
    reset.add_argument("--runtime-only", action="store_true", required=True)
    reset.add_argument("--project", required=True)
    reset.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    reset.add_argument("--yes", action="store_true")

    member = commands.add_parser("member", help="manage project members")
    member_commands = member.add_subparsers(dest="member_command", required=True)
    join = member_commands.add_parser("join", help="join the current worktree")
    join.add_argument("--project", required=True)
    join.add_argument("--member", required=True)
    join.add_argument("--agent", required=True)
    join.add_argument("--request-id")
    join.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    claim = commands.add_parser("claim", help="atomically claim one Ready task")
    claim.add_argument("--project", required=True)
    claim.add_argument("query", nargs="?")
    claim.add_argument("--query", dest="query_option")
    claim.add_argument("--request-id")
    claim.add_argument("--context-budget", type=int, default=DEFAULT_CONTEXT_BUDGET)
    claim.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    task = commands.add_parser("task", help="manage Confirmed Tasks")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    create = task_commands.add_parser("create", help="create a Draft task")
    create.add_argument("--project", required=True)
    create.add_argument("--title", required=True)
    create.add_argument("--description", default="")
    create.add_argument("--acceptance", action="append", default=[])
    create.add_argument("--path", action="append", default=[])
    create.add_argument("--label", action="append", default=[])
    create.add_argument("--dependency", action="append", default=[])
    create.add_argument("--request-id")
    create.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    ready = task_commands.add_parser("ready", help="validate a Draft task as Ready")
    ready.add_argument("task_id")
    ready.add_argument("--request-id")
    ready.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    start = task_commands.add_parser("start", help="start a claimed task")
    start.add_argument("task_id")
    start.add_argument("--request-id")
    start.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    task_status = task_commands.add_parser("status", help="show member task status")
    task_status.add_argument("task_id", nargs="?")
    task_status.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    block = task_commands.add_parser("block", help="block an In Progress task")
    block.add_argument("task_id")
    block.add_argument("--reason", required=True)
    block.add_argument("--request-id")
    block.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    report = commands.add_parser("report", help="submit immutable member reports")
    report_commands = report.add_subparsers(dest="report_command", required=True)
    submit = report_commands.add_parser("submit", help="submit the current branch HEAD")
    submit.add_argument("task_id")
    submit.add_argument("--summary")
    submit.add_argument(
        "--validation",
        action="append",
        default=[],
        help='JSON object with command/outcome/summary; repeat for multiple checks',
    )
    submit.add_argument("--knowledge-candidate", action="append", default=[])
    submit.add_argument("--risk", action="append", default=[])
    submit.add_argument("--commit")
    submit.add_argument("--request-id")
    submit.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    question = commands.add_parser("question", help="inspect Open Questions")
    question_commands = question.add_subparsers(dest="question_command", required=True)
    question_list = question_commands.add_parser("list", help="list project questions")
    question_list.add_argument("--project", required=True)
    question_list.add_argument("--workspace", default=".", help=argparse.SUPPRESS)

    manager = commands.add_parser("manager", help="manager integration commands")
    manager_commands = manager.add_subparsers(dest="manager_command", required=True)
    inbox = manager_commands.add_parser("inbox", help="pending reports and jobs")
    inbox.add_argument("--project")
    inbox.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    review = manager_commands.add_parser("review", help="read-only review packet")
    review.add_argument("job_id")
    review.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    merge = manager_commands.add_parser(
        "merge", help="guarded merge of the job's bound report commit"
    )
    merge.add_argument("job_id")
    merge.add_argument("--expected-head", required=True)
    merge.add_argument(
        "--validation",
        action="append",
        default=[],
        help="JSON object with command/outcome/summary; repeat for multiple checks",
    )
    merge.add_argument("--request-id")
    merge.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    request_changes = manager_commands.add_parser(
        "request-changes", help="end the job with structured requested changes"
    )
    request_changes.add_argument("job_id")
    request_changes.add_argument("--change", action="append", default=[], required=True)
    request_changes.add_argument("--reason")
    request_changes.add_argument("--request-id")
    request_changes.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    block = manager_commands.add_parser(
        "block", help="block the job and open a linked Open Question"
    )
    block.add_argument("job_id")
    block.add_argument("--reason", required=True)
    block.add_argument("--question", required=True)
    block.add_argument("--owner")
    block.add_argument("--request-id")
    block.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    resume = manager_commands.add_parser(
        "resume", help="requeue an integration-blocked job once resolved"
    )
    resume.add_argument("job_id")
    resume.add_argument("--request-id")
    resume.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    knowledge = manager_commands.add_parser(
        "knowledge", help="compile merged work into canonical project memory"
    )
    knowledge_commands = knowledge.add_subparsers(
        dest="knowledge_command", required=True
    )
    propose = knowledge_commands.add_parser(
        "propose", help="persist a structured Knowledge Proposal"
    )
    propose.add_argument("job_id")
    propose.add_argument("--summary", required=True)
    propose.add_argument(
        "--patch",
        action="append",
        default=[],
        help="JSON knowledgePatch object; repeat for multiple canonical files",
    )
    propose.add_argument("--request-id")
    propose.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    validate_knowledge = knowledge_commands.add_parser(
        "validate", help="validate proposal paths, content, and base hashes"
    )
    validate_knowledge.add_argument("proposal_id")
    validate_knowledge.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    apply_knowledge = knowledge_commands.add_parser(
        "apply", help="apply and locally commit a validated proposal"
    )
    apply_knowledge.add_argument("proposal_id")
    apply_knowledge.add_argument("--request-id")
    apply_knowledge.add_argument("--workspace", default=".", help=argparse.SUPPRESS)
    return parser


def _validation_values(values: Sequence[str]) -> list[dict[str, str]]:
    parsed: list[dict[str, str]] = []
    for value in values:
        try:
            item = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TeamRuntimeError(
                "E_USAGE", "--validation must be a JSON object."
            ) from exc
        if not isinstance(item, dict):
            raise TeamRuntimeError("E_USAGE", "--validation must be a JSON object.")
        parsed.append(item)
    return parsed


def _knowledge_patches(values: Sequence[str]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    for value in values:
        try:
            item = json.loads(value)
        except json.JSONDecodeError as exc:
            raise TeamRuntimeError("E_USAGE", "--patch must be a JSON object.") from exc
        if not isinstance(item, dict):
            raise TeamRuntimeError("E_USAGE", "--patch must be a JSON object.")
        parsed.append(item)
    return parsed


def _emit(value: object, *, stream: TextIO | None = None) -> None:
    target = sys.stdout if stream is None else stream
    print(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        file=target,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
        manager = RuntimeManager(arguments.workspace)
        if arguments.command == "init":
            result = manager.init_project(arguments.project, seed=arguments.seed)
        elif arguments.command == "status":
            result = manager.status(arguments.project)
        elif arguments.command == "reset":
            result = manager.reset_runtime(
                arguments.project, confirmed=arguments.yes
            )
        elif arguments.command == "member" and arguments.member_command == "join":
            result = MemberWorkflow(arguments.workspace).join_member(
                arguments.project,
                arguments.member,
                arguments.agent,
                request_id=arguments.request_id,
            )
        elif arguments.command == "claim":
            if arguments.query and arguments.query_option:
                raise TeamRuntimeError(
                    "E_USAGE", "Provide the task query once, positionally or with --query."
                )
            query = arguments.query or arguments.query_option
            if not query:
                raise TeamRuntimeError("E_USAGE", "A task ID or query is required.")
            result = MemberWorkflow(arguments.workspace).claim(
                arguments.project,
                query,
                request_id=arguments.request_id,
                context_budget=arguments.context_budget,
            )
        elif arguments.command == "task":
            workflow = MemberWorkflow(arguments.workspace)
            if arguments.task_command == "create":
                result = workflow.create_task(
                    arguments.project,
                    arguments.title,
                    description=arguments.description,
                    acceptance_criteria=arguments.acceptance,
                    paths=arguments.path,
                    labels=arguments.label,
                    dependencies=arguments.dependency,
                    request_id=arguments.request_id,
                )
            elif arguments.task_command == "ready":
                result = workflow.ready_task(
                    arguments.task_id, request_id=arguments.request_id
                )
            elif arguments.task_command == "start":
                result = workflow.start_task(
                    arguments.task_id, request_id=arguments.request_id
                )
            elif arguments.task_command == "status":
                result = workflow.task_status(arguments.task_id)
            elif arguments.task_command == "block":
                result = workflow.block_task(
                    arguments.task_id,
                    arguments.reason,
                    request_id=arguments.request_id,
                )
            else:  # pragma: no cover
                parser.error("unknown task command")
                return 2
        elif arguments.command == "report" and arguments.report_command == "submit":
            result = MemberWorkflow(arguments.workspace).submit_report(
                arguments.task_id,
                summary=arguments.summary,
                validation=_validation_values(arguments.validation),
                knowledge_candidates=arguments.knowledge_candidate,
                risks=arguments.risk,
                commit=arguments.commit,
                request_id=arguments.request_id,
            )
        elif arguments.command == "question" and arguments.question_command == "list":
            result = MemberWorkflow(arguments.workspace).list_questions(
                arguments.project
            )
        elif arguments.command == "manager":
            integration = ManagerIntegrationWorkflow(arguments.workspace)
            if arguments.manager_command == "inbox":
                result = integration.inbox(arguments.project)
            elif arguments.manager_command == "review":
                result = integration.review_packet(arguments.job_id)
            elif arguments.manager_command == "merge":
                result = integration.merge_job(
                    arguments.job_id,
                    expected_head=arguments.expected_head,
                    validation=_validation_values(arguments.validation),
                    request_id=arguments.request_id,
                )
            elif arguments.manager_command == "request-changes":
                result = integration.request_changes(
                    arguments.job_id,
                    arguments.change,
                    reason=arguments.reason,
                    request_id=arguments.request_id,
                )
            elif arguments.manager_command == "block":
                result = integration.block_job(
                    arguments.job_id,
                    arguments.reason,
                    question=arguments.question,
                    owner=arguments.owner,
                    request_id=arguments.request_id,
                )
            elif arguments.manager_command == "resume":
                result = integration.resume_job(
                    arguments.job_id, request_id=arguments.request_id
                )
            elif arguments.manager_command == "knowledge":
                knowledge = KnowledgeWorkflow(arguments.workspace)
                if arguments.knowledge_command == "propose":
                    result = knowledge.propose(
                        arguments.job_id,
                        _knowledge_patches(arguments.patch),
                        arguments.summary,
                        request_id=arguments.request_id,
                    )
                elif arguments.knowledge_command == "validate":
                    result = knowledge.validate_proposal(arguments.proposal_id)
                elif arguments.knowledge_command == "apply":
                    result = knowledge.apply_proposal(
                        arguments.proposal_id, request_id=arguments.request_id
                    )
                else:  # pragma: no cover
                    parser.error("unknown manager knowledge command")
                    return 2
            else:  # pragma: no cover
                parser.error("unknown manager command")
                return 2
        else:  # pragma: no cover - argparse makes this unreachable
            parser.error("unknown command")
            return 2
        _emit(result)
        return 0
    except TeamRuntimeError as exc:
        _emit(exc.response(), stream=sys.stderr)
        return exc.exit_code
    except KeyboardInterrupt:
        error = TeamRuntimeError("E_INTERNAL", "Operation interrupted.", retryable=True)
        _emit(error.response(), stream=sys.stderr)
        return error.exit_code
    except Exception:
        error = TeamRuntimeError("E_INTERNAL", "Unexpected internal error.")
        _emit(error.response(), stream=sys.stderr)
        return error.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
