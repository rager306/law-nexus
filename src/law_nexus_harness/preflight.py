"""Repository preflight checks for early auto-mode trajectory failures.

This module is ADR-0007 repository control-plane logic only. It exposes a
non-mutating report envelope; concrete checks are added in thin follow-up slices.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

PREFLIGHT_SCHEMA_VERSION = "law-nexus-preflight-report/v1"

PreflightStatus = Literal["ok", "failure"]
CheckStatus = Literal["pass", "fail", "warn"]
Severity = Literal["ok", "warn", "error"]


@dataclass(frozen=True)
class PreflightCheck:
    """Bounded diagnostics for one repository preflight check."""

    check_id: str
    phase: str
    status: CheckStatus
    severity: Severity
    command: tuple[str, ...]
    duration_ms: int
    exit_code: int | None
    stdout_tail: str
    stderr_tail: str
    observed: str
    remediation: str


@dataclass(frozen=True)
class PreflightReport:
    """Stable preflight report for auto-mode and human operators."""

    schema_version: str
    status: PreflightStatus
    root: str
    checks: tuple[PreflightCheck, ...]
    error_count: int
    warn_count: int
    pass_count: int

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checks"] = [asdict(item) for item in self.checks]
        for item in payload["checks"]:
            item["command"] = list(item["command"])
        return payload

    def to_json(self) -> str:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )


def run_preflight(root: Path) -> PreflightReport:
    """Return the non-mutating preflight report skeleton.

    Follow-up slices add concrete formatter, GSD, GitNexus, and docs checks.
    The skeleton intentionally performs no product/runtime inspection.
    """

    resolved_root = root.resolve()
    checks: tuple[PreflightCheck, ...] = ()
    error_count = sum(1 for item in checks if item.severity == "error")
    warn_count = sum(1 for item in checks if item.severity == "warn")
    pass_count = sum(1 for item in checks if item.severity == "ok")
    return PreflightReport(
        schema_version=PREFLIGHT_SCHEMA_VERSION,
        status="failure" if error_count else "ok",
        root=str(resolved_root),
        checks=checks,
        error_count=error_count,
        warn_count=warn_count,
        pass_count=pass_count,
    )
