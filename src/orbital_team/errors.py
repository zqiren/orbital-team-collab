from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EXIT_CODES = {
    "E_USAGE": 2,
    "E_NOT_GIT_REPO": 3,
    "E_PROJECT_NOT_FOUND": 3,
    "E_PROJECT_AMBIGUOUS": 3,
    "E_IDEMPOTENCY_CONFLICT": 4,
    "E_LOCK_TIMEOUT": 4,
    "E_GUARDRAIL_VIOLATION": 5,
    "E_SCHEMA_VERSION": 6,
    "E_CORRUPT_RUNTIME": 6,
    "E_INTERNAL": 8,
}


@dataclass(slots=True)
class TeamRuntimeError(Exception):
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

    def __str__(self) -> str:
        return self.message

    @property
    def exit_code(self) -> int:
        return EXIT_CODES.get(self.code, EXIT_CODES["E_INTERNAL"])

    def response(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "details": self.details,
                "message": self.message,
                "retryable": self.retryable,
            },
            "ok": False,
            "schema_version": "1.0",
        }

