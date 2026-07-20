"""Stable structured result for repository-owned Rust subprocesses."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

SCHEMA_VERSION = "law-nexus-harness-run/v1"

RunStatus = Literal["ok", "failure"]
RunPhase = Literal["subprocess_complete", "timeout", "binary_missing", "startup_error"]
FailureClass = Literal["timeout", "binary_missing", "nonzero_exit", "startup_oserror"]


@dataclass(frozen=True)
class RustRunResult:
    """Bounded diagnostics from one process-level Rust invocation."""

    command: tuple[str, ...]
    binary_path: str
    phase: RunPhase
    duration_ms: int
    exit_code: int | None
    timed_out: bool
    stdout_bytes: int
    stderr_bytes: int
    stdout_tail: str
    stderr_tail: str
    stdout_truncated: bool
    stderr_truncated: bool
    failure_class: FailureClass | None
    status: RunStatus
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        """Return the stable JSON-compatible result mapping."""

        payload = asdict(self)
        payload["command"] = list(self.command)
        return payload

    def to_json(self) -> str:
        """Return deterministic JSON with a trailing newline."""

        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )
