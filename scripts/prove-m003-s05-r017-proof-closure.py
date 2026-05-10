#!/usr/bin/env python3
"""Produce the M003/S05 R017 proof-closure projection.

This script reads the verifier-backed S01-S04 JSON artifacts, derives the R017
recommendation category, and writes a machine-readable JSON plus cold-reader
Markdown projection. It is intentionally local-file-only and fail-closed: malformed
upstream artifacts prevent output writes rather than partially updating closure
files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, NoReturn, cast

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "m003-s05-r017-proof-closure/v1"
DEFAULT_ARTIFACT_DIR = ROOT / ".gsd/milestones/M003/slices/S05"
DEFAULT_UPSTREAMS = {
    "S01": ROOT / ".gsd/milestones/M003/slices/S01/S01-MINIMAX-LIVE-BASELINE.json",
    "S02": ROOT / ".gsd/milestones/M003/slices/S02/S02-MINIMAX-PYO3-ENDPOINT.json",
    "S03": ROOT / ".gsd/milestones/M003/slices/S03/S03-REASONING-SAFE-CANDIDATE.json",
    "S04": ROOT / ".gsd/milestones/M003/slices/S04/S04-VALIDATION-READONLY-EXECUTION.json",
}
JSON_OUTPUT_NAME = "S05-R017-PROOF-CLOSURE.json"
MARKDOWN_OUTPUT_NAME = "S05-R017-PROOF-CLOSURE.md"

EXPECTED_SCHEMAS = {
    "S01": "m003-s01-minimax-live-baseline/v1",
    "S02": "m003-s02-minimax-pyo3-endpoint/v2",
    "S03": "m003-s03-reasoning-safe-candidate/v2",
    "S04": "m003-s04-validation-readonly-execution/v1",
}

REQUIRED_NON_CLAIMS = [
    "provider generation quality",
    "Legal KnowQL product behavior",
    "legal-answer correctness",
    "Legal KnowQL parser or product pipeline behavior",
    "product ETL/import behavior",
    "production graph schema fitness",
    "ODT parsing",
    "retrieval quality",
    "live legal graph execution beyond the S04 synthetic read-only boundary",
]

FALSE_REDACTION_FIELDS = {
    "auth_header_persisted",
    "auth_headers_persisted",
    "credential_persisted",
    "credentials_persisted",
    "prompt_text_persisted",
    "raw_body_persisted",
    "raw_falkordb_rows_persisted",
    "raw_graph_rows_persisted",
    "raw_legal_text_persisted",
    "raw_provider_body_persisted",
    "raw_reasoning_text_persisted",
    "raw_rows_persisted",
    "request_body_persisted",
    "request_text_persisted",
    "secret_like_values_persisted",
    "think_content_persisted",
}
FORBIDDEN_FIELD_PARTS = {
    "authorization",
    "auth_header_value",
    "credential_value",
    "provider_body_value",
    "raw_response",
    "request_prompt",
    "raw_reasoning_value",
    "reasoning_text_value",
    "raw_legal_text_value",
    "legal_text_value",
    "falkordb_rows_value",
    "raw_falkordb_value",
    "graph_rows_value",
    "secret_value",
}
FORBIDDEN_TEXT_PATTERNS = (
    re.compile(r"(?i)Authorization\s*:\s*Bearer\s+[^\s,;}]+"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;}]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)<\s*/?\s*think\s*>"),
)
FORBIDDEN_OVERCLAIM_PATTERNS = (
    re.compile(r"(?i)provider generation quality\s+(is\s+)?(validated|proven|confirmed)"),
    re.compile(r"(?i)Legal KnowQL product behavior\s+(is\s+)?(validated|proven|confirmed|implemented|production[- ]ready)"),
    re.compile(r"(?i)legal-answer correctness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)ODT parsing.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)retrieval quality.*(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)production graph schema fitness\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
    re.compile(r"(?i)live legal graph execution\s+(is\s+)?(validated|proven|confirmed|production[- ]ready)"),
)

RecommendationCategory = Literal["pursue-pyo3-conditioned", "pursue-pyo3", "defer"]


class ProofClosureError(ValueError):
    """Raised when upstream proof artifacts cannot support a safe S05 closure."""


def fail(message: str) -> NoReturn:
    raise ProofClosureError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{path} must be an object")
    return cast("dict[str, Any]", value)


def require_bool(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        fail(f"{path} must be boolean")
    return value


def require_str(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        fail(f"{path} must be a non-empty string")
    return value


def require_int(value: Any, path: str) -> int:
    if not isinstance(value, int) or value < 0:
        fail(f"{path} must be a non-negative integer")
    return value


def require_field(mapping: dict[str, Any], key: str, path: str) -> Any:
    if key not in mapping:
        fail(f"{path}.{key} is required")
    return mapping[key]


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing artifact: {label} at {path}")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"malformed JSON: {label} at line {exc.lineno} column {exc.colno}: {exc.msg}")
    return require_dict(parsed, label)


def assert_no_forbidden_text(text: str, *, path: str) -> None:
    for pattern in FORBIDDEN_TEXT_PATTERNS:
        if pattern.search(text):
            fail(f"redaction violation in {path}: matched {pattern.pattern}")
    for pattern in FORBIDDEN_OVERCLAIM_PATTERNS:
        if pattern.search(text):
            fail(f"forbidden overclaim in {path}: matched {pattern.pattern}")


def assert_redacted(value: Any, *, path: str = "payload") -> None:
    if isinstance(value, dict):
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            if normalized in FALSE_REDACTION_FIELDS:
                require(item is False, f"{path}.{key} must be false")
            elif any(part in normalized for part in FORBIDDEN_FIELD_PARTS):
                fail(f"redaction violation: unsafe field persisted at {path}.{key}")
            elif normalized == "prompt" or normalized.endswith("_prompt"):
                fail(f"redaction violation: prompt field persisted at {path}.{key}")
            assert_redacted(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            assert_redacted(item, path=f"{path}[{index}]")
    elif isinstance(value, str):
        assert_no_forbidden_text(value, path=path)


def validate_common(label: str, payload: dict[str, Any]) -> tuple[str, str, int]:
    require(payload.get("schema_version") == EXPECTED_SCHEMAS[label], f"{label}.schema_version mismatch")
    status = require_str(require_field(payload, "status", label), f"{label}.status")
    root_cause = require_str(require_field(payload, "root_cause", label), f"{label}.root_cause")
    provider_attempts = require_int(require_field(payload, "provider_attempts", label), f"{label}.provider_attempts")
    return status, root_cause, provider_attempts


def validate_s01(payload: dict[str, Any]) -> dict[str, Any]:
    status, root_cause, provider_attempts = validate_common("S01", payload)
    endpoint = require_dict(payload.get("endpoint"), "S01.endpoint")
    response_shape = require_dict(payload.get("response_shape"), "S01.response_shape")
    require_bool(endpoint.get("preserves_v1"), "S01.endpoint.preserves_v1")
    return {
        "schema_version": payload["schema_version"],
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": provider_attempts,
        "endpoint_preserves_v1": endpoint["preserves_v1"],
        "response_status": response_shape.get("status"),
        "response_root_cause": response_shape.get("root_cause"),
    }


def validate_s02(payload: dict[str, Any]) -> dict[str, Any]:
    status, root_cause, provider_attempts = validate_common("S02", payload)
    endpoint = require_dict(payload.get("endpoint"), "S02.endpoint")
    phases = require_dict(payload.get("phases"), "S02.phases")
    build = require_dict(phases.get("build"), "S02.phases.build")
    import_phase = require_dict(phases.get("import"), "S02.phases.import")
    resolver = require_dict(phases.get("resolver"), "S02.phases.resolver")
    provider = require_dict(phases.get("provider"), "S02.phases.provider")
    require_bool(endpoint.get("endpoint_contract_valid"), "S02.endpoint.endpoint_contract_valid")
    require_bool(endpoint.get("preserves_v1"), "S02.endpoint.preserves_v1")
    mechanics_confirmed = all(
        phase.get("status") == "confirmed-runtime" for phase in (build, import_phase, resolver)
    ) and endpoint.get("endpoint_contract_valid") is True and endpoint.get("preserves_v1") is True
    return {
        "schema_version": payload["schema_version"],
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": provider_attempts,
        "endpoint_contract_valid": endpoint["endpoint_contract_valid"],
        "endpoint_preserves_v1": endpoint["preserves_v1"],
        "mechanics_confirmed": mechanics_confirmed,
        "phase_statuses": {
            "build": build.get("status"),
            "import": import_phase.get("status"),
            "resolver": resolver.get("status"),
            "provider": provider.get("status"),
        },
        "provider_root_cause": provider.get("root_cause"),
    }


def validate_s03(payload: dict[str, Any]) -> dict[str, Any]:
    status, root_cause, provider_attempts = validate_common("S03", payload)
    candidate = require_dict(payload.get("candidate"), "S03.candidate")
    accepted = require_bool(candidate.get("accepted"), "S03.candidate.accepted")
    if accepted:
        require(status == "confirmed-runtime", "S03 accepted candidate requires S03.status confirmed-runtime")
        require(candidate.get("starts_with") in {"MATCH", "CALL"}, "S03 accepted candidate must start with MATCH or CALL")
        require(isinstance(candidate.get("sha256_12"), str) and candidate["sha256_12"], "S03 accepted candidate requires sha256_12")
    return {
        "schema_version": payload["schema_version"],
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": provider_attempts,
        "candidate_accepted": accepted,
        "candidate_status": candidate.get("status"),
        "candidate_root_cause": candidate.get("root_cause"),
        "candidate_categories": list(candidate.get("categories", [])) if isinstance(candidate.get("categories"), list) else [],
        "candidate_starts_with": candidate.get("starts_with"),
        "candidate_sha256_12": candidate.get("sha256_12"),
    }


def validate_s04(payload: dict[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == EXPECTED_SCHEMAS["S04"], "S04.schema_version mismatch")
    status = require_str(payload.get("status"), "S04.status")
    root_cause = require_str(payload.get("root_cause"), "S04.root_cause")
    validation = require_dict(payload.get("validation"), "S04.validation")
    execution = require_dict(payload.get("execution"), "S04.execution")
    validation_attempted = require_bool(validation.get("attempted"), "S04.validation.attempted")
    validation_accepted = require_bool(validation.get("accepted"), "S04.validation.accepted")
    execution_attempted = require_bool(execution.get("attempted"), "S04.execution.attempted")
    execution_status = require_str(execution.get("status"), "S04.execution.status")
    if validation_accepted:
        require(validation_attempted, "S04 validation cannot be accepted unless attempted")
    if execution_attempted:
        require(validation_accepted, "S04 execution cannot be attempted unless validation.accepted is true")
        require(execution_status == "confirmed-runtime", "S04 attempted execution must be confirmed-runtime")
        require(execution.get("method") == "Graph.ro_query", "S04 execution method must be Graph.ro_query")
        require(execution.get("timeout_ms") == 1000, "S04 execution timeout must be 1000")
    else:
        require(execution_status in {"not-attempted", "blocked-environment"}, "S04 unattempted execution status must be not-attempted or blocked-environment")
    return {
        "schema_version": payload["schema_version"],
        "status": status,
        "root_cause": root_cause,
        "validation_attempted": validation_attempted,
        "validation_accepted": validation_accepted,
        "validation_rejection_codes": list(validation.get("rejection_codes", [])) if isinstance(validation.get("rejection_codes"), list) else [],
        "validation_query_shape_category": validation.get("query_shape_category"),
        "execution_attempted": execution_attempted,
        "execution_status": execution_status,
        "execution_method": execution.get("method"),
        "execution_graph_kind": execution.get("graph_kind"),
    }


def summarize_upstreams(paths: dict[str, Path]) -> dict[str, dict[str, Any]]:
    missing = sorted(set(EXPECTED_SCHEMAS) - set(paths))
    require(not missing, "missing upstream path labels: " + ", ".join(missing))
    raw_payloads = {label: load_json(paths[label], label) for label in sorted(EXPECTED_SCHEMAS)}
    for label, payload in raw_payloads.items():
        assert_redacted(payload, path=label)
    return {
        "S01": {"path": str(paths["S01"]), **validate_s01(raw_payloads["S01"])},
        "S02": {"path": str(paths["S02"]), **validate_s02(raw_payloads["S02"])},
        "S03": {"path": str(paths["S03"]), **validate_s03(raw_payloads["S03"])},
        "S04": {"path": str(paths["S04"]), **validate_s04(raw_payloads["S04"])},
    }


def derive_recommendation_category(upstreams: dict[str, dict[str, Any]]) -> RecommendationCategory:
    s01 = upstreams["S01"]
    s02 = upstreams["S02"]
    s03 = upstreams["S03"]
    s04 = upstreams["S04"]
    all_confirmed = (
        s01["status"] == "confirmed-runtime"
        and s02["status"] == "confirmed-runtime"
        and s02["mechanics_confirmed"] is True
        and s03["status"] == "confirmed-runtime"
        and s03["candidate_accepted"] is True
        and s04["validation_accepted"] is True
        and s04["execution_attempted"] is True
        and s04["execution_status"] == "confirmed-runtime"
    )
    if all_confirmed:
        return "pursue-pyo3"
    if s02["provider_attempts"] > 0 and s02["mechanics_confirmed"] is True:
        return "pursue-pyo3-conditioned"
    return "defer"


def category_blockers(upstreams: dict[str, dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if upstreams["S03"]["candidate_accepted"] is not True:
        blockers.append("S03 has no accepted candidate")
    if upstreams["S04"]["validation_accepted"] is not True:
        blockers.append("S04 has no accepted validation")
    if upstreams["S04"]["execution_attempted"] is not True:
        blockers.append("S04 has no read-only execution attempt")
    if upstreams["S04"]["execution_status"] != "confirmed-runtime":
        blockers.append(f"S04 execution status is {upstreams['S04']['execution_status']}")
    return blockers


def r017_effect_for(category: RecommendationCategory) -> dict[str, str]:
    if category == "pursue-pyo3":
        return {
            "status": "ready-for-requirement-validation-review",
            "summary": "R017 has all S05 prerequisite proof signals for a future validation review, but this artifact does not itself validate the requirement.",
        }
    if category == "pursue-pyo3-conditioned":
        return {
            "status": "advanced-not-validated",
            "summary": "R017 is advanced by endpoint, provider-attempt, and safety evidence but remains active pending accepted candidate generation and read-only execution proof.",
        }
    return {
        "status": "not-advanced",
        "summary": "R017 lacks the minimum PyO3/provider mechanics needed for a positive recommendation category.",
    }


def build_proof_closure(paths: dict[str, Path]) -> dict[str, Any]:
    upstreams = summarize_upstreams(paths)
    category = derive_recommendation_category(upstreams)
    artifact: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "upstream_artifacts": upstreams,
        "derived_recommendation_category": category,
        "category_blockers": category_blockers(upstreams),
        "r017_effect": r017_effect_for(category),
        "requirements_advanced": ["R017"] if category in {"pursue-pyo3", "pursue-pyo3-conditioned"} else [],
        "requirements_validated": [],
        "verification_summary": {
            "producer_status": "generated",
            "upstream_artifacts_checked": sorted(upstreams),
            "verifier_status": "pending",
            "verifier_command": "uv run python scripts/verify-m003-s05-r017-recommendation.py",
        },
        "non_claims": REQUIRED_NON_CLAIMS,
        "redaction": {
            "raw_provider_bodies_persisted": False,
            "prompts_persisted": False,
            "raw_reasoning_persisted": False,
            "raw_generated_candidate_text_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_graph_rows_persisted": False,
            "credentials_or_auth_headers_persisted": False,
            "secret_like_values_persisted": False,
        },
    }
    assert_redacted(artifact)
    return artifact


def render_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# M003/S05 R017 proof closure",
        "",
        f"Schema version: `{artifact['schema_version']}`",
        f"Generated at: `{artifact['generated_at']}`",
        f"Derived recommendation category: `{artifact['derived_recommendation_category']}`",
        "",
        "## R017 effect",
        "",
        "R017 is advanced but not validated by this closure artifact.",
        f"- Status: `{artifact['r017_effect']['status']}`",
        f"- Summary: {artifact['r017_effect']['summary']}",
        "- Requirements advanced: `" + ", ".join(artifact["requirements_advanced"]) + "`" if artifact["requirements_advanced"] else "- Requirements advanced: none",
        "- Requirements validated: none",
        "",
        "## Upstream evidence summary",
        "",
        "| Slice | Status | Root cause | Provider attempts | Key closure fields | Path |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    upstreams = artifact["upstream_artifacts"]
    for label in ("S01", "S02", "S03", "S04"):
        item = upstreams[label]
        if label == "S03":
            key_fields = f"candidate_accepted=`{item['candidate_accepted']}`; candidate_status=`{item['candidate_status']}`"
            attempts = item["provider_attempts"]
        elif label == "S04":
            key_fields = f"validation_accepted=`{item['validation_accepted']}`; execution_status=`{item['execution_status']}`; execution_attempted=`{item['execution_attempted']}`"
            attempts = "n/a"
        elif label == "S02":
            key_fields = f"mechanics_confirmed=`{item['mechanics_confirmed']}`; endpoint_preserves_v1=`{item['endpoint_preserves_v1']}`"
            attempts = item["provider_attempts"]
        else:
            key_fields = f"endpoint_preserves_v1=`{item['endpoint_preserves_v1']}`; response_status=`{item['response_status']}`"
            attempts = item["provider_attempts"]
        lines.append(f"| {label} | `{item['status']}` | `{item['root_cause']}` | {attempts} | {key_fields} | `{item['path']}` |")
    lines.extend(
        [
            "",
            "## Category blockers",
            "",
        ]
    )
    blockers = artifact["category_blockers"]
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- None for the derived category.")
    lines.extend(
        [
            "",
            "## Verification summary",
            "",
            f"- Producer status: `{artifact['verification_summary']['producer_status']}`",
            f"- Verifier status: `{artifact['verification_summary']['verifier_status']}`",
            f"- Verifier command: `{artifact['verification_summary']['verifier_command']}`",
            "",
            "## Explicit non-claims",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in artifact["non_claims"])
    lines.extend(
        [
            "",
            "## Redaction boundary",
            "",
            "This closure persists only categorical summaries, booleans, counts, hashes, schema/status/root-cause fields, and artifact paths.",
            "It does not persist provider response bodies, prompts, raw reasoning, rejected candidate text, raw legal text, FalkorDB rows, credentials, authorization headers, or secret-like values.",
            "",
        ]
    )
    markdown = "\n".join(lines)
    assert_no_forbidden_text(markdown, path="markdown")
    return markdown


def write_outputs(artifact: dict[str, Any], artifact_dir: Path) -> tuple[Path, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifact_dir / JSON_OUTPUT_NAME
    markdown_path = artifact_dir / MARKDOWN_OUTPUT_NAME
    json_text = json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    markdown_text = render_markdown(artifact)
    assert_no_forbidden_text(json_text, path=str(json_path))
    assert_no_forbidden_text(markdown_text, path=str(markdown_path))
    json_path.write_text(json_text, encoding="utf-8")
    markdown_path.write_text(markdown_text, encoding="utf-8")
    return json_path, markdown_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    parser.add_argument("--s01-artifact", type=Path, default=DEFAULT_UPSTREAMS["S01"])
    parser.add_argument("--s02-artifact", type=Path, default=DEFAULT_UPSTREAMS["S02"])
    parser.add_argument("--s03-artifact", type=Path, default=DEFAULT_UPSTREAMS["S03"])
    parser.add_argument("--s04-artifact", type=Path, default=DEFAULT_UPSTREAMS["S04"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    paths = {
        "S01": args.s01_artifact,
        "S02": args.s02_artifact,
        "S03": args.s03_artifact,
        "S04": args.s04_artifact,
    }
    try:
        artifact = build_proof_closure(paths)
        json_path, markdown_path = write_outputs(artifact, args.artifact_dir)
    except ProofClosureError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "generated",
                "schema_version": artifact["schema_version"],
                "derived_recommendation_category": artifact["derived_recommendation_category"],
                "json_path": str(json_path),
                "markdown_path": str(markdown_path),
                "requirements_advanced": artifact["requirements_advanced"],
                "requirements_validated": artifact["requirements_validated"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
