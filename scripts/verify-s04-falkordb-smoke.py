#!/usr/bin/env python3
"""Verify S04 FalkorDB/FalkorDBLite capability smoke artifacts.

This verifier is intentionally conservative. S04 runtime artifacts must list every
required capability and must preserve ownership/diagnostic fields even before
runtime probes have executed. Schema-only mode allows scaffold statuses; runtime
results mode requires every capability to be terminally classified with diagnostics
for blocked or failed probes.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MARKDOWN = ROOT / ".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.md"
DEFAULT_JSON = ROOT / ".gsd/milestones/M001/slices/S04/S04-FALKORDB-CAPABILITY-SMOKE.json"

SCHEMA_VERSION = "s04-falkordb-capability-smoke/v1"


class VerificationMode(StrEnum):
    SCHEMA_ONLY = "schema-only"
    RUNTIME_RESULTS = "runtime-results"


class CheckFailure(Exception):
    """Raised when an artifact cannot be read or parsed."""


@dataclass(frozen=True)
class CapabilitySpec:
    capability_id: str
    title: str
    runtime_owner: str


CAPABILITIES: tuple[CapabilitySpec, ...] = (
    CapabilitySpec("docker-daemon", "Docker daemon availability", "S04"),
    CapabilitySpec("docker-falkordb-image", "FalkorDB Docker image availability", "S04"),
    CapabilitySpec("falkordb-basic-graph", "FalkorDB basic graph query", "S04"),
    CapabilitySpec("falkordb-udf-load-execute", "FalkorDB UDF load/list/execute/flush", "S04"),
    CapabilitySpec("falkordb-procedure-list", "FalkorDB procedure discovery", "S04"),
    CapabilitySpec("falkordb-fulltext-node", "FalkorDB node full-text index/query", "S04"),
    CapabilitySpec("falkordb-vector-node", "FalkorDB node vector index/query", "S04"),
    CapabilitySpec("falkordb-vector-distance", "FalkorDB vector distance functions", "S04"),
    CapabilitySpec("falkordb-algo-pagerank", "FalkorDB PageRank algorithm output shape", "S04"),
    CapabilitySpec("falkordb-algo-wcc", "FalkorDB WCC algorithm output shape", "S04"),
    CapabilitySpec("falkordb-algo-bfs", "FalkorDB BFS algorithm output shape", "S04"),
    CapabilitySpec("falkordb-algo-betweenness", "FalkorDB betweenness algorithm output shape", "S04"),
    CapabilitySpec("falkordb-algo-label-propagation", "FalkorDB label propagation algorithm output shape", "S04"),
    CapabilitySpec("falkordb-algo-sp-paths", "FalkorDB single-pair shortest paths output shape", "S04"),
    CapabilitySpec("falkordb-algo-ss-paths", "FalkorDB single-source shortest paths output shape", "S04"),
    CapabilitySpec("falkordblite-import", "FalkorDBLite import/bootstrap", "S04"),
    CapabilitySpec("falkordblite-basic-graph", "FalkorDBLite basic graph query", "S04"),
    CapabilitySpec("falkordblite-udf", "FalkorDBLite UDF behavior", "S04"),
    CapabilitySpec("falkordblite-vector-fulltext", "FalkorDBLite vector/full-text behavior", "S04"),
    CapabilitySpec("embedding-env", "Embedding package/cache environment", "S04"),
    CapabilitySpec("embedding-cpu-tiny", "Bounded CPU embedding smoke", "S04"),
)

REQUIRED_CAPABILITY_IDS = tuple(spec.capability_id for spec in CAPABILITIES)

SCHEMA_SCAFFOLD_STATUSES = frozenset({"not-run", "smoke-needed"})
TERMINAL_RUNTIME_STATUSES = frozenset(
    {
        "confirmed-runtime",
        "blocked-environment",
        "failed-runtime",
        "bounded-not-product-proven",
    }
)
ALLOWED_RUNTIME_STATUSES = SCHEMA_SCAFFOLD_STATUSES | TERMINAL_RUNTIME_STATUSES

ALLOWED_EVIDENCE_CLASSES = frozenset(
    {
        "confirmed",
        "docs-backed/source-pending",
        "smoke-needed",
        "contradicted",
        "out-of-scope",
    }
)

REQUIRED_MARKDOWN_SECTIONS = (
    "# S04 FalkorDB Capability Smoke",
    "## Purpose",
    "## Capability Findings",
    "## Runtime Boundary",
    "## Command Summary",
    "## Environment Metadata",
    "## Cleanup Status",
    "## Failure Diagnostics",
    "## Verification",
)

REQUIRED_JSON_TOP_LEVEL_FIELDS = (
    "schema_version",
    "generated_at",
    "phase",
    "capabilities",
    "findings",
    "command_summary",
    "image_metadata",
    "package_metadata",
    "cleanup_status",
    "log_artifact_path",
)

REQUIRED_FINDING_FIELDS = (
    "capability_id",
    "status",
    "evidence_class",
    "phase",
    "timestamp",
    "owner",
    "resolution_path",
    "verification_criteria",
    "raw_log_reference",
    "diagnostics",
)

REQUIRED_DIAGNOSTIC_FIELDS = (
    "root_cause",
    "detail",
)

ArtifactMode = Literal["schema-only", "runtime-results"]


def read_text(path: Path, label: str) -> str:
    if not path.is_file():
        raise CheckFailure(f"{label} missing: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise CheckFailure(f"{label} empty: {path}")
    return text


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path, "JSON artifact")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"JSON artifact invalid JSON at {path}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise CheckFailure(f"JSON artifact root must be an object: {path}")
    return cast("dict[str, Any]", parsed)


def check_markdown_structure(text: str) -> list[str]:
    failures: list[str] = []
    for section in REQUIRED_MARKDOWN_SECTIONS:
        if section not in text:
            failures.append(f"markdown missing section: {section}")
    for capability_id in REQUIRED_CAPABILITY_IDS:
        if f"`{capability_id}`" not in text:
            failures.append(f"markdown missing capability ID: {capability_id}")
    if "M001 architecture-only" not in text:
        failures.append("markdown must preserve the M001 architecture-only boundary")
    return failures


def _as_non_empty_string(value: object, path: str) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return [f"{path} must be a non-empty string"]
    return []


def _validate_diagnostics(
    capability_id: str,
    diagnostics: object,
    status: str,
    mode: VerificationMode,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(diagnostics, dict):
        return [f"finding {capability_id} diagnostics must be an object"]
    diagnostics_map = cast("dict[str, object]", diagnostics)
    for field in REQUIRED_DIAGNOSTIC_FIELDS:
        failures.extend(
            _as_non_empty_string(
                diagnostics_map.get(field),
                f"finding {capability_id} diagnostics.{field}",
            )
        )
    if mode == VerificationMode.RUNTIME_RESULTS and status in {"blocked-environment", "failed-runtime"}:
        for field in ("root_cause", "detail"):
            if diagnostics_map.get(field) in {"not-run", "pending", "N/A"}:
                failures.append(
                    f"finding {capability_id} {status} diagnostics.{field} must name the concrete runtime cause"
                )
    return failures


def _validate_finding(
    finding: object,
    index: int,
    mode: VerificationMode,
) -> tuple[str | None, list[str]]:
    if not isinstance(finding, dict):
        return None, [f"findings[{index}] must be an object"]
    finding_map = cast("dict[str, object]", finding)
    raw_capability_id = finding_map.get("capability_id")
    capability_id = raw_capability_id if isinstance(raw_capability_id, str) else None
    label = capability_id or f"index {index}"

    failures: list[str] = []
    for field in REQUIRED_FINDING_FIELDS:
        if field not in finding_map:
            failures.append(f"finding {label} missing required field: {field}")
    if capability_id is None or not capability_id.strip():
        failures.append(f"finding {label} capability_id must be a non-empty string")
        return None, failures
    if capability_id not in REQUIRED_CAPABILITY_IDS:
        failures.append(f"finding {capability_id} has unknown capability ID")

    for field in ("phase", "timestamp", "owner", "resolution_path", "verification_criteria", "raw_log_reference"):
        failures.extend(_as_non_empty_string(finding_map.get(field), f"finding {capability_id} {field}"))

    raw_status = finding_map.get("status")
    if not isinstance(raw_status, str) or not raw_status.strip():
        failures.append(f"finding {capability_id} status must be a non-empty string")
        status = ""
    else:
        status = raw_status
        if status not in ALLOWED_RUNTIME_STATUSES:
            allowed = ", ".join(sorted(ALLOWED_RUNTIME_STATUSES))
            failures.append(f"finding {capability_id} invalid status {status!r}; allowed: {allowed}")
        if mode == VerificationMode.RUNTIME_RESULTS and status in SCHEMA_SCAFFOLD_STATUSES:
            terminal = ", ".join(sorted(TERMINAL_RUNTIME_STATUSES))
            failures.append(
                f"finding {capability_id} has non-terminal runtime status {status!r}; runtime mode requires one of: {terminal}"
            )

    raw_evidence_class = finding_map.get("evidence_class")
    if not isinstance(raw_evidence_class, str) or not raw_evidence_class.strip():
        failures.append(f"finding {capability_id} evidence_class must be a non-empty string")
    elif raw_evidence_class not in ALLOWED_EVIDENCE_CLASSES:
        allowed = ", ".join(sorted(ALLOWED_EVIDENCE_CLASSES))
        failures.append(
            f"finding {capability_id} invalid evidence_class {raw_evidence_class!r}; allowed: {allowed}"
        )

    failures.extend(
        _validate_diagnostics(
            capability_id,
            finding_map.get("diagnostics"),
            status,
            mode,
        )
    )
    return capability_id, failures


def check_json_structure(data: dict[str, Any], mode: VerificationMode) -> list[str]:
    failures: list[str] = []
    for field in REQUIRED_JSON_TOP_LEVEL_FIELDS:
        if field not in data:
            failures.append(f"JSON missing top-level field: {field}")
    if data.get("schema_version") != SCHEMA_VERSION:
        failures.append(
            f"JSON schema_version must be {SCHEMA_VERSION!r}, got {data.get('schema_version')!r}"
        )
    if mode == VerificationMode.RUNTIME_RESULTS and data.get("phase") != "runtime-results":
        failures.append("JSON phase must be 'runtime-results' in runtime-results mode")
    if mode == VerificationMode.SCHEMA_ONLY and data.get("phase") not in {"schema-only", "runtime-results"}:
        failures.append("JSON phase must be 'schema-only' or 'runtime-results' in schema-only mode")

    for field in ("generated_at", "cleanup_status", "log_artifact_path"):
        failures.extend(_as_non_empty_string(data.get(field), f"JSON {field}"))

    for field in ("command_summary", "image_metadata", "package_metadata"):
        if not isinstance(data.get(field), dict):
            failures.append(f"JSON {field} must be an object")

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        failures.append("JSON capabilities must be a list")
    else:
        capability_values = [item for item in capabilities if isinstance(item, str)]
        if len(capability_values) != len(capabilities):
            failures.append("JSON capabilities must contain only strings")
        missing_capabilities = sorted(set(REQUIRED_CAPABILITY_IDS) - set(capability_values))
        unknown_capabilities = sorted(set(capability_values) - set(REQUIRED_CAPABILITY_IDS))
        for capability_id in missing_capabilities:
            failures.append(f"JSON capabilities missing required capability ID: {capability_id}")
        for capability_id in unknown_capabilities:
            failures.append(f"JSON capabilities has unknown capability ID: {capability_id}")

    findings = data.get("findings")
    if not isinstance(findings, list):
        failures.append("JSON findings must be a list")
        return failures

    seen: set[str] = set()
    for index, finding in enumerate(findings):
        capability_id, finding_failures = _validate_finding(finding, index, mode)
        failures.extend(finding_failures)
        if capability_id is not None:
            if capability_id in seen:
                failures.append(f"JSON duplicate finding for capability ID: {capability_id}")
            seen.add(capability_id)

    missing_findings = sorted(set(REQUIRED_CAPABILITY_IDS) - seen)
    for capability_id in missing_findings:
        failures.append(f"JSON findings missing required capability ID: {capability_id}")
    return failures


def validate_artifacts(markdown_path: Path, json_path: Path, mode: VerificationMode) -> list[str]:
    failures: list[str] = []
    try:
        markdown_text = read_text(markdown_path, "markdown artifact")
    except CheckFailure as exc:
        failures.append(str(exc))
    else:
        failures.extend(check_markdown_structure(markdown_text))

    try:
        json_data = read_json(json_path)
    except CheckFailure as exc:
        failures.append(str(exc))
    else:
        failures.extend(check_json_structure(json_data, mode))
    return failures


def print_capability_summary() -> None:
    print("Required S04 capability IDs:")
    for spec in CAPABILITIES:
        print(f"- {spec.capability_id}: {spec.title} (owner: {spec.runtime_owner})")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--require-schema-only",
        action="store_true",
        help="Require complete scaffold artifacts; not-run/smoke-needed statuses are allowed.",
    )
    mode_group.add_argument(
        "--require-runtime-results",
        action="store_true",
        help="Require terminal runtime classifications for every capability.",
    )
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument(
        "--list-capabilities",
        action="store_true",
        help="Print the required capability ID list before verification.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_capabilities:
        print_capability_summary()

    mode = (
        VerificationMode.SCHEMA_ONLY
        if args.require_schema_only
        else VerificationMode.RUNTIME_RESULTS
    )
    failures = validate_artifacts(args.markdown, args.json, mode)
    if failures:
        print("S04 FalkorDB capability smoke verification failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("S04 FalkorDB capability smoke verification passed.")
    print(f"Mode: {mode.value}.")
    print(f"Markdown artifact: {args.markdown}")
    print(f"JSON artifact: {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
