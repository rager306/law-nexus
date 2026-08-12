"""Deterministic JSON report helpers for Review Case CLI.

Outer composition only. Does not normalize semantics, record dispositions,
promote authority, or create GSD work.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

CLI_REPORT_SCHEMA_VERSION = "review-case-cli-report/v1"
CLI_TOOL_ERROR_SCHEMA_VERSION = "review-case-cli-tool-error/v1"

_DEFAULT_NON_CLAIMS = (
    "Non-authoritative review projection",
    "Does not promote requirements, ADRs, roadmap, or lifecycle",
    "Does not create GSD milestones or product claims",
    "CLI success is not semantic acceptance or product readiness",
)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def render_success_report(*, operation: str, payload: object) -> str:
    body = {
        "schema_version": CLI_REPORT_SCHEMA_VERSION,
        "status": "ok",
        "authoritative": False,
        "authority_required": True,
        "operation": operation,
        "result": _jsonable(payload),
        "non_claims": list(_DEFAULT_NON_CLAIMS),
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def render_failure_report(
    *,
    operation: str,
    code: str,
    message: str,
    exit_class: str,
) -> str:
    body = {
        "schema_version": CLI_TOOL_ERROR_SCHEMA_VERSION
        if exit_class == "tool-error"
        else CLI_REPORT_SCHEMA_VERSION,
        "status": exit_class,
        "authoritative": False,
        "authority_required": True,
        "operation": operation,
        "error": {
            "code": code,
            "message": message,
        },
        "non_claims": list(_DEFAULT_NON_CLAIMS),
    }
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
