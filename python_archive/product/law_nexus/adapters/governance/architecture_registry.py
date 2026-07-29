"""Shared helpers for derived architecture registry tooling.

These helpers support local CLI/projection scripts. They do not make ACP,
RDF, JSONL, or graph projections authoritative source truth.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class JsonlDiagnostic:
    """Deterministic diagnostic for JSONL architecture registry loading."""

    rule: str
    message: str
    path: Path
    line_number: int = 0
    field: str = "<none>"


@dataclass(frozen=True)
class JsonlRecord:
    """JSONL object with its source line number."""

    line_number: int
    record: dict[str, Any]


def display_repo_path(path: Path, *, root: Path) -> str:
    """Return a stable repository-relative display path when possible."""

    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def normalize_repo_path(path: Path, *, root: Path) -> Path:
    """Resolve relative CLI paths against the repository root without requiring existence."""

    return path if path.is_absolute() else root / path


def is_same_resolved_path(path: Path, candidates: set[Path], *, root: Path) -> bool:
    """Return true when a path resolves to one of the candidate paths."""

    resolved = normalize_repo_path(path, root=root).resolve()
    return resolved in {candidate.resolve() for candidate in candidates}


def is_safe_repo_relative_path(value: str) -> bool:
    """Check whether a string is safe to store as a portable repo-relative path."""

    if not value or value.startswith("/") or "\x00" in value:
        return False
    parts = Path(value).parts
    return ".." not in parts and not value.startswith(".gsd/exec")


def load_located_jsonl_objects(path: Path) -> tuple[list[JsonlRecord], list[JsonlDiagnostic]]:
    """Load JSON object records from a JSONL file with source line numbers."""

    records: list[JsonlRecord] = []
    diagnostics: list[JsonlDiagnostic] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return records, [JsonlDiagnostic("read-jsonl", str(exc), path)]

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except JSONDecodeError as exc:
            diagnostics.append(
                JsonlDiagnostic(
                    "malformed-jsonl",
                    exc.msg,
                    path,
                    line_number=line_number,
                    field=str(line_number),
                )
            )
            continue
        if not isinstance(record, dict):
            diagnostics.append(
                JsonlDiagnostic(
                    "jsonl-object",
                    "expected each JSONL record to be an object",
                    path,
                    line_number=line_number,
                    field=str(line_number),
                )
            )
            continue
        records.append(JsonlRecord(line_number=line_number, record=record))
    return records, diagnostics


def load_jsonl_objects(path: Path) -> tuple[list[dict[str, Any]], list[JsonlDiagnostic]]:
    """Load JSON object records from a JSONL file with bounded diagnostics."""

    records, diagnostics = load_located_jsonl_objects(path)
    return [located.record for located in records], diagnostics
