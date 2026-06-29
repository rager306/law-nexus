"""Shared helpers for parser golden-case builder/evaluator scripts.

These helpers are deterministic support utilities only. They do not read raw legal
sources and do not claim parser completeness, retrieval quality, legal-answer
correctness, or FalkorDB readiness.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from law_nexus.adapters.sources.parser_records import load_jsonl_records


def display_path(path: Path, *, root: Path) -> str:
    """Return a stable repository-relative path when possible."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest for an artifact file."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def diagnostic(
    *,
    case_id: str | None,
    case_class: str | None,
    severity: str,
    rule: str,
    artifact_path: str,
    message: str,
    expected_state: str | None = None,
    actual_state: str | None = None,
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create a compact path-qualified diagnostic payload."""

    payload: dict[str, Any] = {
        "case_id": case_id,
        "case_class": case_class,
        "severity": severity,
        "rule": rule,
        "artifact_path": artifact_path,
        "record_id": record_id,
        "record_kind": record_kind,
        "source_path": source_path,
        "expected_state": expected_state,
        "actual_state": actual_state,
        "message": message,
        "non_authoritative": non_authoritative,
    }
    payload.update(extra)
    return payload


def load_json_object(path: Path, *, root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load a JSON object and report bounded diagnostics instead of raising."""

    if not path.exists():
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path, root=root),
                expected_state="readable-source-artifact",
                actual_state="missing",
                message="Required tracked parser golden-case source artifact is missing.",
            )
        ]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="invalid_json",
                artifact_path=display_path(path, root=root),
                expected_state="valid-json-object",
                actual_state="invalid-json",
                message=str(exc),
            )
        ]
    if not isinstance(loaded, dict):
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="invalid_json_shape",
                artifact_path=display_path(path, root=root),
                expected_state="json-object",
                actual_state=type(loaded).__name__,
                message="Expected a JSON object.",
            )
        ]
    return loaded, []


def load_jsonl_if_exists(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load parser JSONL records if the path exists; missing is reported elsewhere."""

    if not path.exists():
        return [], []
    return load_jsonl_records(path)


def diagnostic_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return a stable diagnostic sort key."""

    return (
        str(item.get("severity") or ""),
        str(item.get("case_id") or ""),
        str(item.get("rule") or ""),
        str(item.get("artifact_path") or ""),
    )


def sort_diagnostics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return diagnostics in deterministic order."""

    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        items,
        key=lambda item: (
            severity_order.get(str(item.get("severity")), 99),
            str(item.get("case_id") or ""),
            str(item.get("rule") or ""),
            str(item.get("artifact_path") or ""),
        ),
    )


def severity_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Count diagnostics by severity in stable key order."""

    counts: dict[str, int] = {}
    for item in items:
        severity = str(item.get("severity") or "unknown")
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))
