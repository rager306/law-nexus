"""Shared helpers for bounded retrieval proof wrappers.

These helpers validate proof output shape and payload safety only. They do not
prove retrieval quality, answer faithfulness, legal correctness, or production
readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ALLOWED_RESULT_STATES = frozenset({"accepted", "accepted_scoped_no_answer", "rejected"})
BOUNDED_DIAGNOSTIC_FIELDS = frozenset({"field_path", "case_id", "retrieval_output_id", "scope_id"})
MAX_SAFE_FIELD_LENGTH = 160


def bounded_path(path: Path, *, root: Path, max_length: int = MAX_SAFE_FIELD_LENGTH) -> str:
    """Return a bounded repository-relative path for proof reports."""

    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)[:max_length]


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object or raise a deterministic value error."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JSON payload must be an object")
    return payload


def error_summary(
    *,
    fixtures: Path,
    root: Path,
    schema_version: str,
    phase: str,
    code: str,
    detail: str | None = None,
    max_length: int = MAX_SAFE_FIELD_LENGTH,
) -> dict[str, Any]:
    """Build the common mismatch summary used by retrieval proof wrappers."""

    error: dict[str, Any] = {
        "phase": phase,
        "code": code,
        "fixture_path": bounded_path(fixtures, root=root, max_length=max_length),
    }
    if detail:
        error["detail"] = detail[:max_length]
    return {
        "schema_version": schema_version,
        "fixture_path": bounded_path(fixtures, root=root, max_length=max_length),
        "total_cases": 0,
        "accepted_count": 0,
        "rejected_count": 0,
        "mismatch_count": 1,
        "diagnostic_code_inventory": [],
        "mismatches": [error],
    }


def diagnostic_codes(result: Any) -> list[str]:
    """Return diagnostic codes from a citation-safe validator result."""

    return [diagnostic.code for diagnostic in result.diagnostics]


def diagnostic_payloads(result: Any) -> list[Mapping[str, Any]]:
    """Return serializable diagnostic payloads from a validator result."""

    return [diagnostic.to_dict() for diagnostic in result.diagnostics]


def safe_payload_errors(
    *,
    case_id: str,
    result: Any,
    safe_fields: set[str],
    known_codes: set[str],
    allowed_result_states: frozenset[str] = ALLOWED_RESULT_STATES,
    bounded_fields: frozenset[str] = BOUNDED_DIAGNOSTIC_FIELDS,
    max_length: int = MAX_SAFE_FIELD_LENGTH,
) -> list[dict[str, Any]]:
    """Check validator output for bounded, known diagnostic payload fields."""

    errors: list[dict[str, Any]] = []
    if result.result not in allowed_result_states:
        errors.append(
            {
                "phase": "diagnostic_safety",
                "case_id": case_id,
                "code": "malformed_output_shape",
                "field_path": "result",
                "actual_result": str(result.result)[:max_length],
            }
        )
    for index, payload in enumerate(diagnostic_payloads(result)):
        extra_fields = sorted(set(payload) - safe_fields)
        if extra_fields:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id,
                    "code": "unsafe_diagnostic_field",
                    "field_path": f"diagnostics[{index}]",
                    "actual_codes": extra_fields,
                }
            )
        diagnostic_code = payload.get("code")
        if diagnostic_code not in known_codes:
            errors.append(
                {
                    "phase": "diagnostic_safety",
                    "case_id": case_id,
                    "code": "unknown_diagnostic_code",
                    "field_path": f"diagnostics[{index}].code",
                    "actual_codes": [str(diagnostic_code)[:max_length]],
                }
            )
        for field in bounded_fields:
            value = payload.get(field)
            if not isinstance(value, str) or len(value) > max_length:
                errors.append(
                    {
                        "phase": "diagnostic_safety",
                        "case_id": case_id,
                        "code": "malformed_output_shape",
                        "field_path": f"diagnostics[{index}].{field}",
                    }
                )
    return errors
