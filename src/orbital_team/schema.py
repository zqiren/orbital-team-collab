from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from .errors import TeamRuntimeError


def _schema_candidates() -> list[Path]:
    candidates: list[Path] = []
    override = os.environ.get("ORBITAL_TEAM_SCHEMA")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            Path(__file__).resolve().parents[2]
            / "schemas"
            / "v1"
            / "orbital-team.schema.json",
            Path(sys.prefix)
            / "share"
            / "orbital-team"
            / "schemas"
            / "v1"
            / "orbital-team.schema.json",
        ]
    )
    return candidates


@lru_cache(maxsize=1)
def schema_bundle() -> tuple[dict[str, Any], Path]:
    for candidate in _schema_candidates():
        if candidate.is_file():
            try:
                bundle = json.loads(candidate.read_text(encoding="utf-8"))
                Draft202012Validator.check_schema(bundle)
            except (OSError, json.JSONDecodeError, SchemaError) as exc:
                raise TeamRuntimeError(
                    "E_CORRUPT_RUNTIME",
                    "The protocol schema bundle is invalid.",
                    {"schema": str(candidate), "reason": str(exc)},
                ) from exc
            return bundle, candidate
    raise TeamRuntimeError(
        "E_CORRUPT_RUNTIME",
        "The protocol schema bundle could not be located.",
    )


@lru_cache(maxsize=None)
def validator(definition: str) -> Draft202012Validator:
    bundle, _ = schema_bundle()
    if definition not in bundle.get("$defs", {}):
        raise TeamRuntimeError(
            "E_INTERNAL", f"Unknown schema definition: {definition}."
        )
    fragment = {
        "$schema": bundle["$schema"],
        "$defs": bundle["$defs"],
        "$ref": f"#/$defs/{definition}",
    }
    return Draft202012Validator(fragment)


def validate(definition: str, value: Any) -> None:
    try:
        validator(definition).validate(value)
    except ValidationError as exc:
        location = "/".join(str(part) for part in exc.absolute_path)
        raise TeamRuntimeError(
            "E_CORRUPT_RUNTIME",
            f"Data does not match the {definition} schema.",
            {"location": location, "reason": exc.message},
        ) from exc
