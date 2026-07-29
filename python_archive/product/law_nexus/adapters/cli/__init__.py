"""CLI adapter utilities for stable script wrappers."""

from __future__ import annotations

from law_nexus.adapters.cli.runtime import (
    CLI_RUNTIME_NON_CLAIMS,
    CliRuntimeError,
    JsonObjectValidator,
    load_json_object,
    repo_relative_path,
    sha256_bytes,
    sha256_path,
    sha256_text,
    stable_json_text,
    write_json_report,
)

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
