#!/usr/bin/env python3
"""Verify M001/S08 final architecture report and findings artifacts.

This verifier intentionally fails closed. It keeps the human final report synced
with the machine-readable findings rows, verifies owner/resolution/verification
and roadmap metadata, and rejects M001 architecture overclaims that would turn
bounded smoke/parser/embedding evidence into product or legal-quality proof.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "prd/05_final_architecture_review.md"
DEFAULT_FINDINGS = ROOT / ".gsd/milestones/M001/slices/S08/S08-FINDINGS.json"
DEFAULT_SCHEMA = ROOT / ".gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json"

SCHEMA_VERSION = "s08-final-architecture-findings/v1"
REQUIRED_SOURCE_ARTIFACTS = (
    "s07_review_findings",
    "s04_falkordb_smoke",
    "s05_odt_parser_findings",
    "s09_local_embedding_evaluation",
    "s10_embedding_runtime_proof",
)
REQUIRED_GATE_IDS = ("G-005", "G-008", "G-011", "G-015")
REQUIRED_REQUIREMENTS = ("R001", "R009", "R010")
REQUIRED_REPORT_SECTIONS = (
    "# 5. Final Architecture Review",
    "## 1. Executive verdict",
    "## 2. Evidence inventory",
    "## 3. Findings matrix",
    "## 4. Roadmap corrections for M002-M007",
    "## 5. Machine-readable findings path and schema proposal",
    "## 6. Non-goals and overclaim guardrails",
    "## 7. Cold-reader action checklist",
)
REQUIRED_REPORT_TERMS = (
    "machine-readable",
    "owner",
    "resolution",
    "verification",
    "roadmap",
    "architecture-only",
    "local/open-weight",
)
REQUIRED_MACHINE_PATHS = (
    ".gsd/milestones/M001/slices/S08/S08-FINDINGS.json",
    ".gsd/milestones/M001/slices/S08/S08-FINDINGS.schema.json",
    "prd/findings/architecture-findings.v1.json",
    "prd/findings/architecture-findings.v1.schema.json",
)
REQUIRED_ROW_FIELDS = (
    "id",
    "title",
    "source",
    "claim_class",
    "status",
    "severity",
    "evidence",
    "impact",
    "recommendation",
    "owner",
    "resolution_path",
    "verification_criteria",
    "roadmap_effect",
    "requirement_links",
)
REQUIRED_EVIDENCE_FIELDS = ("artifact", "summary")

# Positive overclaim patterns only. Negative guardrails such as "No product ETL"
# must pass, while promotional wording fails with a precise diagnostic.
OVERCLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "product ETL promotion",
        re.compile(r"\bproduct\s+ETL\b[^\n.]{0,80}\b(ready|implemented|shipped|import(?:ed)?|production\s+import)", re.I),
    ),
    (
        "final ODT parser readiness",
        re.compile(r"\bfinal\s+ODT\s+parser\b[^\n.]{0,80}\b(ready|proven|complete|production|authoritative)", re.I),
    ),
    (
        "production retrieval quality proof",
        re.compile(r"\bproduction\s+retrieval\s+quality\b[^\n.]{0,80}\b(proven|confirmed|ready|validated)", re.I),
    ),
    (
        "direct GraphBLAS control-surface proof",
        re.compile(r"\bdirect\s+(?:LegalGraph\s+)?GraphBLAS\s+control[- ]surface\s+proof\b[^\n.]{0,80}\b(proven|confirmed|ready|validated)", re.I),
    ),
    (
        "managed embedding API promotion",
        re.compile(r"\bmanaged\s+embedding\s+API\b[^\n.]{0,80}\b(fallback|promoted|allowed|default|recommended)", re.I),
    ),
)


@dataclass
class VerificationResult:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, message: str) -> None:
        self.errors.append(message)


def read_text(path: Path, label: str, result: VerificationResult) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.add(f"{label} missing: {path}")
        return None
    if not text.strip():
        result.add(f"{label} empty: {path}")
        return None
    return text


def read_json(path: Path, label: str, result: VerificationResult) -> dict[str, Any] | None:
    text = read_text(path, label, result)
    if text is None:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        result.add(f"{label} invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None
    if not isinstance(parsed, dict):
        result.add(f"{label} root must be an object: {path}")
        return None
    return cast("dict[str, Any]", parsed)


def require_non_empty_string(value: object, result: VerificationResult, path: str) -> None:
    if not isinstance(value, str) or not value.strip():
        result.add(f"{path} must be a non-empty string")


def resolve_artifact_path(path_value: str, base: Path) -> Path:
    path_without_fragment = path_value.split("#", 1)[0]
    path = Path(path_without_fragment)
    if path.is_absolute():
        return path
    return base / path


def require_existing_path(value: object, result: VerificationResult, path: str, base: Path) -> None:
    if not isinstance(value, str) or not value.strip():
        result.add(f"{path} must be a non-empty path string")
        return
    candidate = resolve_artifact_path(value, base)
    if not candidate.exists():
        result.add(f"{path} path does not exist: {value}")


def schema_required_fields(schema: dict[str, Any]) -> tuple[str, ...]:
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return REQUIRED_ROW_FIELDS
    finding = defs.get("finding")
    if not isinstance(finding, dict):
        return REQUIRED_ROW_FIELDS
    required = finding.get("required")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        return REQUIRED_ROW_FIELDS
    return tuple(cast("list[str]", required))


def schema_enum(schema: dict[str, Any], field_name: str, fallback: set[str]) -> set[str]:
    defs = schema.get("$defs")
    if not isinstance(defs, dict):
        return fallback
    finding = defs.get("finding")
    if not isinstance(finding, dict):
        return fallback
    properties = finding.get("properties")
    if not isinstance(properties, dict):
        return fallback
    field_schema = properties.get(field_name)
    if not isinstance(field_schema, dict):
        return fallback
    enum = field_schema.get("enum")
    if not isinstance(enum, list) or not all(isinstance(item, str) for item in enum):
        return fallback
    return set(cast("list[str]", enum))


def validate_schema(schema: dict[str, Any], result: VerificationResult) -> None:
    required = schema.get("required")
    if not isinstance(required, list):
        result.add("schema missing top-level required list")
    else:
        for field_name in ("schema_version", "generated_at", "source_artifacts", "findings"):
            if field_name not in required:
                result.add(f"schema required list missing top-level field: {field_name}")
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        result.add("schema missing properties object")
        return
    schema_version = properties.get("schema_version")
    if not isinstance(schema_version, dict) or schema_version.get("const") != SCHEMA_VERSION:
        result.add(f"schema properties.schema_version.const must be {SCHEMA_VERSION!r}")
    row_required = set(schema_required_fields(schema))
    for field_name in REQUIRED_ROW_FIELDS:
        if field_name not in row_required:
            result.add(f"schema finding.required missing field: {field_name}")


def validate_top_level(payload: dict[str, Any], result: VerificationResult, base: Path) -> None:
    for field_name in ("schema_version", "generated_at", "source_artifacts", "findings"):
        if field_name not in payload:
            result.add(f"findings JSON missing top-level field: {field_name}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        result.add(f"findings JSON schema_version must be {SCHEMA_VERSION!r}, got {payload.get('schema_version')!r}")
    require_non_empty_string(payload.get("generated_at"), result, "findings JSON generated_at")

    source_artifacts = payload.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        result.add("findings JSON source_artifacts must be an object")
    else:
        for key in REQUIRED_SOURCE_ARTIFACTS:
            if key not in source_artifacts:
                result.add(f"source_artifacts missing required key: {key}")
            else:
                require_existing_path(source_artifacts.get(key), result, f"source_artifacts.{key}", base)

    if not isinstance(payload.get("findings"), list):
        result.add("findings JSON findings must be a list")


def validate_evidence_entry(
    row_id: str,
    evidence: object,
    index: int,
    result: VerificationResult,
    base: Path,
) -> None:
    if not isinstance(evidence, dict):
        result.add(f"finding {row_id} evidence[{index}] must be an object")
        return
    evidence_obj = cast("dict[str, object]", evidence)
    for field_name in REQUIRED_EVIDENCE_FIELDS:
        if field_name not in evidence_obj:
            result.add(f"finding {row_id} evidence[{index}] missing required field: {field_name}")
    require_existing_path(evidence_obj.get("artifact"), result, f"finding {row_id} evidence[{index}].artifact", base)
    require_non_empty_string(evidence_obj.get("summary"), result, f"finding {row_id} evidence[{index}].summary")
    if "status" in evidence_obj:
        require_non_empty_string(evidence_obj.get("status"), result, f"finding {row_id} evidence[{index}].status")


def validate_finding(
    row: object,
    index: int,
    result: VerificationResult,
    schema: dict[str, Any],
    base: Path,
) -> str | None:
    if not isinstance(row, dict):
        result.add(f"findings[{index}] must be an object")
        return None
    row_obj = cast("dict[str, object]", row)
    raw_id = row_obj.get("id")
    row_id = raw_id if isinstance(raw_id, str) and raw_id.strip() else f"index {index}"

    for field_name in schema_required_fields(schema):
        if field_name not in row_obj:
            result.add(f"finding {row_id} missing required field: {field_name}")

    if not isinstance(raw_id, str) or not raw_id.strip():
        result.add(f"finding index {index} id must be a non-empty string")
        return None

    for field_name in ("title", "impact", "recommendation", "owner", "resolution_path", "verification_criteria", "roadmap_effect"):
        require_non_empty_string(row_obj.get(field_name), result, f"finding {raw_id} {field_name}")

    for field_name in ("claim_class", "status", "severity"):
        require_non_empty_string(row_obj.get(field_name), result, f"finding {raw_id} {field_name}")

    claim_class = row_obj.get("claim_class")
    allowed_claim_classes = schema_enum(schema, "claim_class", set())
    if isinstance(claim_class, str) and allowed_claim_classes and claim_class not in allowed_claim_classes:
        result.add(f"finding {raw_id} invalid claim_class {claim_class!r}")

    status = row_obj.get("status")
    allowed_statuses = schema_enum(schema, "status", set())
    if isinstance(status, str) and allowed_statuses and status not in allowed_statuses:
        result.add(f"finding {raw_id} invalid status {status!r}")

    severity = row_obj.get("severity")
    allowed_severities = schema_enum(schema, "severity", set())
    if isinstance(severity, str) and allowed_severities and severity not in allowed_severities:
        result.add(f"finding {raw_id} invalid severity {severity!r}")

    sources = row_obj.get("source")
    if not isinstance(sources, list) or not sources:
        result.add(f"finding {raw_id} source must be a non-empty list")
    else:
        for source_index, source in enumerate(sources):
            require_existing_path(source, result, f"finding {raw_id} source[{source_index}]", base)

    evidence = row_obj.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        result.add(f"finding {raw_id} evidence must be a non-empty list")
    else:
        for evidence_index, entry in enumerate(evidence):
            validate_evidence_entry(raw_id, entry, evidence_index, result, base)

    requirement_links = row_obj.get("requirement_links")
    if not isinstance(requirement_links, list) or not requirement_links:
        result.add(f"finding {raw_id} requirement_links must be a non-empty list")
    else:
        seen_requirements = {item for item in requirement_links if isinstance(item, str)}
        for requirement in REQUIRED_REQUIREMENTS:
            if requirement not in seen_requirements:
                result.add(f"finding {raw_id} missing required requirement link: {requirement}")
        for item in requirement_links:
            if not isinstance(item, str) or not re.fullmatch(r"R[0-9]{3}", item):
                result.add(f"finding {raw_id} invalid requirement link: {item!r}")

    for optional_list_field in ("decision_links", "non_goals"):
        value = row_obj.get(optional_list_field)
        if value is None:
            continue
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            result.add(f"finding {raw_id} {optional_list_field} must contain only non-empty strings")

    return raw_id


def validate_findings(payload: dict[str, Any], schema: dict[str, Any], result: VerificationResult, base: Path) -> set[str]:
    validate_top_level(payload, result, base)
    rows = payload.get("findings")
    if not isinstance(rows, list):
        return set()
    seen: set[str] = set()
    for index, row in enumerate(rows):
        row_id = validate_finding(row, index, result, schema, base)
        if row_id is None:
            continue
        if row_id in seen:
            result.add(f"findings JSON duplicate finding ID: {row_id}")
        seen.add(row_id)
    for gate_id in REQUIRED_GATE_IDS:
        if gate_id not in seen:
            result.add(f"findings JSON missing required finding ID: {gate_id}")
    return seen


def is_negated_guardrail(report: str, match: re.Match[str]) -> bool:
    sentence_start = max(report.rfind(".", 0, match.start()), report.rfind("\n", 0, match.start())) + 1
    prefix = report[sentence_start : match.start()].strip().lower()
    sentence = report[sentence_start : report.find(".", match.end()) if report.find(".", match.end()) != -1 else len(report)]
    lowered_sentence = sentence.strip().lower()
    return (
        prefix.endswith("no")
        or prefix.endswith("not")
        or lowered_sentence.startswith("no ")
        or lowered_sentence.startswith("not ")
        or lowered_sentence.startswith("do not ")
        or lowered_sentence.startswith("does not ")
        or " is not " in lowered_sentence
        or " not allowed" in lowered_sentence
        or " no " in lowered_sentence[:40]
    )


def validate_report(report: str, row_ids: set[str], payload: dict[str, Any], result: VerificationResult) -> None:
    for section in REQUIRED_REPORT_SECTIONS:
        if section not in report:
            result.add(f"report missing section: {section}")
    for term in REQUIRED_REPORT_TERMS:
        if term not in report:
            result.add(f"report missing required term: {term}")
    for path in REQUIRED_MACHINE_PATHS:
        if path not in report:
            result.add(f"report missing machine-readable path proposal: {path}")
    for row_id in sorted(row_ids):
        if row_id not in report:
            result.add(f"report missing finding ID: {row_id}")
    for gate_id in REQUIRED_GATE_IDS:
        if gate_id not in report:
            result.add(f"report missing required gate ID: {gate_id}")

    rows = payload.get("findings")
    if isinstance(rows, list):
        observed_statuses = {
            row.get("status")
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("status"), str)
        }
        for status in sorted(cast("set[str]", observed_statuses)):
            if status not in report:
                result.add(f"report missing status reference: {status}")

    for label, pattern in OVERCLAIM_PATTERNS:
        for match in pattern.finditer(report):
            if is_negated_guardrail(report, match):
                continue
            snippet = " ".join(match.group(0).split())
            result.add(f"report contains overclaim marker ({label}): {snippet}")
            break


def verify(report: Path | str, findings: Path | str, schema: Path | str) -> VerificationResult:
    result = VerificationResult()
    report_path = Path(report)
    findings_path = Path(findings)
    schema_path = Path(schema)
    base = ROOT if findings_path.absolute().is_relative_to(ROOT) else findings_path.absolute().parent

    report_text = read_text(report_path, "report", result)
    findings_payload = read_json(findings_path, "findings JSON", result)
    schema_payload = read_json(schema_path, "schema JSON", result)
    if findings_payload is None or schema_payload is None:
        return result

    validate_schema(schema_payload, result)
    row_ids = validate_findings(findings_payload, schema_payload, result, base)
    if report_text is not None:
        validate_report(report_text, row_ids, findings_payload, result)
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="S08 final architecture review markdown path")
    parser.add_argument("--findings", type=Path, default=DEFAULT_FINDINGS, help="S08 machine-readable findings JSON path")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="S08 findings JSON schema path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify(args.report, args.findings, args.schema)
    if not result.ok:
        print("S08 final architecture report verification failed:", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("S08 final architecture report verification passed.")
    print(f"Report: {args.report}")
    print(f"Findings: {args.findings}")
    print(f"Schema: {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
