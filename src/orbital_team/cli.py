from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Sequence, TextIO

from .errors import TeamRuntimeError
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
    return parser


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
