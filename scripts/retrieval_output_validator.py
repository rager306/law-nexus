from __future__ import annotations

import json
from pathlib import Path

from law_nexus.application.citation_safe_answer_validator import (
    KNOWN_DIAGNOSTIC_CODES,
    RESULT_ACCEPTED,
    RESULT_ACCEPTED_SCOPED_NO_ANSWER,
    RESULT_REJECTED,
    SAFE_DIAGNOSTIC_FIELDS,
    Diagnostic,
    Fixture,
    ValidationResult,
    _check_forbidden_fields,
    _check_id_namespace,
    _check_required_mapping,
    _edition_valid_for_date,
    _finalize,
    _has_allowed_prefix,
    _has_error,
    _join_path,
    _optional_safe_id,
    _safe_id,
    _scope_id,
    _validate_answer_claim,
    _validate_citation,
    build_fixture,
    validate_case,
    validate_output,
)


def load_fixture_file(path: str | Path) -> Fixture:
    fixture_path = Path(path)
    with fixture_path.open(encoding="utf-8") as fixture_file:
        data = json.load(fixture_file)
    if not isinstance(data, dict):
        raise ValueError("fixture root must be an object")
    artifact = data.get("fixture_artifact", fixture_path.as_posix())
    return build_fixture(data, fixture_artifact=str(artifact))


__all__ = [
    "Diagnostic",
    "Fixture",
    "KNOWN_DIAGNOSTIC_CODES",
    "RESULT_ACCEPTED",
    "RESULT_ACCEPTED_SCOPED_NO_ANSWER",
    "RESULT_REJECTED",
    "SAFE_DIAGNOSTIC_FIELDS",
    "ValidationResult",
    "_check_forbidden_fields",
    "_check_id_namespace",
    "_check_required_mapping",
    "_edition_valid_for_date",
    "_finalize",
    "_has_allowed_prefix",
    "_has_error",
    "_join_path",
    "_optional_safe_id",
    "_safe_id",
    "_scope_id",
    "_validate_answer_claim",
    "_validate_citation",
    "build_fixture",
    "load_fixture_file",
    "validate_case",
    "validate_output",
]
