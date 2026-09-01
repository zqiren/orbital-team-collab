"""Built-in scripted Manager: a deterministic, fully verifiable runner adapter.

Invoked as ``python3 -m orbital_team.manager_proc <request.json>`` by the
``CommandManagerRunner`` adapter. It follows the exact contract every agent
runner must follow: read one schema-valid request file, use only declared
policies, merge through the controlled Manager command, propose knowledge
through the controlled knowledge command, and write one schema-valid result
file. It never mutates Git or runtime JSON directly.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .runtime import utc_now
from .schema import validate
from .storage import atomic_write_json, read_json


def _policy(request: dict[str, Any], policy_id: str) -> dict[str, Any] | None:
    return next(
        (
            policy
            for policy in request["allowed_commands"]
            if policy["id"] == policy_id
        ),
        None,
    )


def _run_policy(
    argv: list[str], cwd: str, timeout: int
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_CONFIG_GLOBAL"] = "/dev/null"
    environment["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return subprocess.run(
        argv,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _result(
    request: dict[str, Any],
    outcome: str,
    *,
    merge_commit: str | None = None,
    proposal_id: str | None = None,
    validation: list[dict[str, str]] | None = None,
    changes: list[str] | None = None,
    risk: str | None = None,
) -> dict[str, Any]:
    return {
        "changes_requested": changes or [],
        "completed_at": utc_now(),
        "job_id": request["job_id"],
        "merge_commit": merge_commit,
        "open_question_ids": [],
        "outcome": outcome,
        "proposal_id": proposal_id,
        "risk_summary": risk,
        "run_id": request["run_id"],
        "schema_version": request["schema_version"],
        "validation": validation or [],
    }


def integrate(request: dict[str, Any]) -> dict[str, Any]:
    context = read_json(Path(request["input_paths"]["context"]))
    validation_records: list[dict[str, str]] = []
    validate_policy = _policy(request, "validate")
    timeout = max(1, request["timeout_seconds"] - 5)
    if validate_policy is not None and context.get("report_worktree"):
        completed = _run_policy(
            validate_policy["argv_prefix"], context["report_worktree"], timeout
        )
        outcome = "passed" if completed.returncode == 0 else "failed"
        validation_records.append(
            {
                "command": " ".join(validate_policy["argv_prefix"]),
                "outcome": outcome,
                "summary": (completed.stdout + completed.stderr).strip()[-500:]
                or f"exit {completed.returncode}",
            }
        )
        if outcome == "failed":
            return _result(
                request,
                "changes_requested",
                validation=validation_records,
                changes=["Validation command failed on the report worktree."],
                risk="Validation failed before merge.",
            )
    else:
        return _result(
            request,
            "blocked",
            risk="The report worktree or required validation policy is unavailable.",
        )
    merge_policy = _policy(request, "manager-merge")
    if merge_policy is None:
        return _result(
            request,
            "blocked",
            validation=validation_records,
            risk="No controlled merge policy was provided to the runner.",
        )
    merge_argv = [
        *merge_policy["argv_prefix"],
        request["job_id"],
        "--expected-head",
        context["target_head"],
    ]
    for record in validation_records:
        merge_argv.extend(["--validation", json.dumps(record)])
    completed = _run_policy(merge_argv, request["workspace"], timeout)
    if completed.returncode == 0:
        merge_result = json.loads(completed.stdout.strip().splitlines()[-1])
        return _result(
            request,
            "merged",
            merge_commit=merge_result["merge_commit"],
            validation=validation_records,
        )
    try:
        error = json.loads(completed.stderr.strip().splitlines()[-1])["error"]
    except (json.JSONDecodeError, KeyError, IndexError):
        error = {"code": "E_INTERNAL", "message": completed.stderr.strip()[-500:], "retryable": True}
    if error.get("retryable"):
        return _result(
            request,
            "retryable",
            validation=validation_records,
            risk=f"Controlled merge returned {error.get('code')}: {error.get('message')}",
        )
    return _result(
        request,
        "blocked",
        validation=validation_records,
        risk=f"Controlled merge refused: {error.get('code')}: {error.get('message')}",
    )


def compile_knowledge(request: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic proposal through the SPEC-05 domain command."""
    context = read_json(Path(request["input_paths"]["context"]))
    pack = context["pack"]
    relative = "orbital/PROJECT_STATE.md"
    memory_path = Path(request["input_paths"]["memory_project_state"])
    current = memory_path.read_text(encoding="utf-8")
    entry = (
        f"- Demo integration `{request['task_id']}` completed from "
        f"`{context['source_commit']}`."
    )
    patches: list[dict[str, Any]] = []
    if entry not in current.splitlines():
        content = current.rstrip() + "\n\n" + entry + "\n"
        patches.append(
            {
                "base_sha256": pack["current_memory_hashes"][relative],
                "content": content,
                "operation": "updated",
                "path": relative,
            }
        )
    policy = _policy(request, "knowledge-propose")
    if policy is None:
        return _result(
            request,
            "blocked",
            risk="No controlled knowledge proposal policy was provided.",
        )
    argv = [
        *policy["argv_prefix"],
        request["job_id"],
        "--summary",
        (
            f"Record deterministic demo completion for {request['task_id']}."
            if patches
            else f"No additional durable knowledge for {request['task_id']}."
        ),
        "--request-id",
        f"builtin-knowledge-{request['job_id']}",
    ]
    for patch in patches:
        argv.extend(["--patch", json.dumps(patch, sort_keys=True)])
    completed = _run_policy(
        argv,
        request["workspace"],
        max(1, request["timeout_seconds"] - 5),
    )
    if completed.returncode == 0:
        proposal = json.loads(completed.stdout.strip().splitlines()[-1])["proposal"]
        return _result(
            request,
            "proposed" if patches else "no_change",
            proposal_id=proposal["id"],
        )
    try:
        error = json.loads(completed.stderr.strip().splitlines()[-1])["error"]
    except (json.JSONDecodeError, KeyError, IndexError):
        error = {
            "code": "E_INTERNAL",
            "message": completed.stderr.strip()[-500:],
            "retryable": True,
        }
    return _result(
        request,
        "retryable" if error.get("retryable") else "blocked",
        risk=(
            f"Controlled knowledge proposal returned {error.get('code')}: "
            f"{error.get('message')}"
        ),
    )


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 1:
        print("usage: python3 -m orbital_team.manager_proc <request.json>", file=sys.stderr)
        return 2
    request_path = Path(arguments[0])
    request = read_json(request_path)
    validate("managerRunRequest", request)
    result = (
        integrate(request)
        if request["phase"] == "integration"
        else compile_knowledge(request)
    )
    validate("managerRunResult", result)
    atomic_write_json(Path(request["result_path"]), result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
