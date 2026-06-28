"""Shared bounded CLI runtime helpers for script wrappers.

These helpers are intentionally small and stdlib-only. They support stable CLI
proof surfaces without owning argparse, live runtime orchestration, legal logic,
or product validation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

CLI_RUNTIME_NON_CLAIMS: tuple[str, ...] = (
    "Does not validate legal correctness.",
    "Does not prove parser completeness.",
    "Does not prove retrieval quality.",
    "Does not prove production runtime readiness.",
    "Does not prove external service availability.",
)

JsonObjectValidator = Callable[[dict[str, Any]], None]
PathDisplay = Callable[[Path], str]


class CliRuntimeError(RuntimeError):
    """Bounded CLI helper failure with a stable code and failure class."""

    def __init__(self, code: str, message: str, *, failure_class: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.failure_class = failure_class


def repo_relative_path(path: Path, *, root: Path, outside_project: str = "<outside-project>") -> str:
    """Return a repo-relative POSIX path or an outside-project sentinel."""

    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return outside_project


def sha256_bytes(payload: bytes) -> str:
    """Return a SHA-256 hex digest for raw bytes."""

    return hashlib.sha256(payload).hexdigest()


def sha256_text(payload: str) -> str:
    """Return a SHA-256 hex digest for UTF-8 text."""

    return sha256_bytes(payload.encode("utf-8"))


def sha256_path(path: Path) -> str:
    """Return a SHA-256 hex digest for a file's bytes."""

    return sha256_bytes(path.read_bytes())


def stable_json_text(payload: Mapping[str, Any]) -> str:
    """Return deterministic UTF-8 JSON text for CLI reports."""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_json_object(path: Path, *, path_display: PathDisplay | None = None) -> dict[str, Any]:
    """Load a JSON object from a file with bounded failure diagnostics."""

    display = path_display(path) if path_display is not None else path.as_posix()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliRuntimeError(
            "E_JSON_FILE_MISSING",
            f"missing JSON source artifact: {display}",
            failure_class="missing_source_artifact",
        ) from exc
    except json.JSONDecodeError as exc:
        raise CliRuntimeError(
            "E_JSON_DECODE_FAILED",
            f"invalid JSON source artifact: {display}: {exc.msg}",
            failure_class="invalid_source_artifact",
        ) from exc
    if not isinstance(payload, dict):
        raise CliRuntimeError(
            "E_JSON_OBJECT_EXPECTED",
            f"JSON source artifact must be an object: {display}",
            failure_class="invalid_source_artifact",
        )
    return payload


def write_json_report(
    path: Path,
    payload: Mapping[str, Any],
    *,
    validator: JsonObjectValidator | None = None,
) -> None:
    """Validate and write a stable JSON report."""

    report = dict(payload)
    if validator is not None:
        validator(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json_text(report), encoding="utf-8")


__all__ = [
    "CLI_RUNTIME_NON_CLAIMS",
    "CliRuntimeError",
    "JsonObjectValidator",
    "load_json_object",
    "repo_relative_path",
    "sha256_bytes",
    "sha256_path",
    "sha256_text",
    "stable_json_text",
    "write_json_report",
]
