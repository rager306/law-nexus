#!/usr/bin/env python3
"""Validate minimal Architecture Control Plane fixture records.

This verifier is intentionally small and deterministic. It validates the first
ACP fixture chain under ``prd/architecture/acp/fixtures/minimal-chain`` without
claiming product, parser, legal, FalkorDB, retrieval, or review readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/minimal-chain"
REQUIRED_RECORD_KINDS = {
    "architecture_prompt_record",
    "architecture_proposal",
    "decision_candidate",
    "proof_gate",
    "architecture_health_finding",
}
REQUIRED_SAFETY_FALSE_FIELDS = {
    "contains_secrets",
    "contains_provider_payloads",
    "contains_raw_vectors",
    "contains_unnecessary_raw_legal_text",
    "contains_local_absolute_paths",
    "claims_product_readiness",
    "claims_parser_completeness",
    "claims_falkordb_ingestion",
    "claims_legal_correctness",
    "claims_r035_validated",
    "claims_r037_validated",
    "claims_r038_validated",
}
FORBIDDEN_MARKERS = (
    "GIGACHAT" + "_AUTH_DATA",
    "MINIMAX" + "_API_KEY=",
    "OPENAI" + "_API_KEY=",
    "sk-",
    "R035 is validated",
    "R037 is validated",
    "R038 is validated",
    "validates parser completeness",
    "validates FalkorDB ingestion",
    "proves legal correctness",
    "graph-context staging is FalkorDB ingestion",
    "MiniMax is authoritative",
    "external AI dialogue is authority",
    "visualization validates architecture",
    "/root/",
    ".gsd/exec",
)


@dataclass(frozen=True)
class Diagnostic:
    rule: str
    message: str
    path: Path
    record_id: str = "<none>"
    field: str = "<none>"

    def to_json(self) -> dict[str, str]:
        return {
            "rule": self.rule,
            "message": self.message,
            "path": display_path(self.path),
            "record_id": self.record_id,
            "field": self.field,
        }


@dataclass(frozen=True)
class AcpRecord:
    path: Path
    frontmatter: dict[str, Any]
    body: str

    @property
    def record_id(self) -> str:
        value = self.frontmatter.get("id")
        return value if isinstance(value, str) and value else "<missing-id>"

    @property
    def record_kind(self) -> str:
        value = self.frontmatter.get("record_kind")
        return value if isinstance(value, str) and value else "<missing-record-kind>"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "true":
        return True
    if value == "false":
        return False
    if value == "[]":
        return []
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def parse_frontmatter_block(block: str) -> dict[str, Any]:
    """Parse the restricted YAML subset used by ACP fixtures."""
    root: dict[str, Any] = {}
    current_key: str | None = None
    current_list: list[Any] | None = None
    current_dict: dict[str, Any] | None = None

    for raw_line in block.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        if indent == 0:
            current_dict = None
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            current_key = key
            if value == "":
                root[key] = []
                current_list = root[key]
            else:
                root[key] = parse_scalar(value)
                current_list = None
            continue

        if current_key is None:
            continue

        if line.startswith("- "):
            if current_list is None:
                root[current_key] = []
                current_list = root[current_key]
            item = line[2:].strip()
            if item.endswith(":"):
                current_dict = {item[:-1].strip(): {}}
                current_list.append(current_dict)
            elif ":" in item:
                key, value = item.split(":", 1)
                current_dict = {key.strip(): parse_scalar(value)}
                current_list.append(current_dict)
            else:
                current_dict = None
                current_list.append(parse_scalar(item))
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = parse_scalar(value)
            if current_dict is not None:
                current_dict[key] = value
            elif isinstance(root.get(current_key), dict):
                root[current_key][key] = value
            else:
                if not isinstance(root.get(current_key), dict):
                    root[current_key] = {}
                root[current_key][key] = value

    return root


def parse_record(path: Path) -> AcpRecord:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing opening frontmatter marker")
    try:
        _, block, body = text.split("---", 2)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter marker") from exc
    return AcpRecord(path=path, frontmatter=parse_frontmatter_block(block), body=body.strip())


def load_records(fixture_dir: Path) -> tuple[list[AcpRecord], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    records: list[AcpRecord] = []
    for path in sorted(fixture_dir.glob("*.md")):
        try:
            records.append(parse_record(path))
        except ValueError as exc:
            diagnostics.append(Diagnostic("parse-frontmatter", str(exc), path))
    return records, diagnostics


def is_repo_relative_path(value: str) -> bool:
    if not value or value.startswith("/") or "\x00" in value:
        return False
    parts = Path(value).parts
    if ".." in parts:
        return False
    if value.startswith(".gsd/e") and value.startswith(".gsd/exec"):
        return False
    return True


def source_path_exists(value: str) -> bool:
    return (ROOT / value).exists()


def validate_base(record: AcpRecord) -> list[Diagnostic]:
    data = record.frontmatter
    diagnostics: list[Diagnostic] = []
    for field in ("id", "record_kind", "title", "status", "source_refs", "safety"):
        if field not in data:
            diagnostics.append(Diagnostic("required", "missing required field", record.path, record.record_id, field))

    if not re.fullmatch(r"(APR|AP|DC|PG|AHF)-[0-9]{4}", str(data.get("id", ""))):
        diagnostics.append(Diagnostic("record-id", "invalid ACP record id", record.path, record.record_id, "id"))

    if data.get("record_kind") not in REQUIRED_RECORD_KINDS:
        diagnostics.append(
            Diagnostic("record-kind", "unexpected ACP record kind", record.path, record.record_id, "record_kind")
        )

    source_refs = data.get("source_refs")
    if not isinstance(source_refs, list) or not source_refs:
        diagnostics.append(Diagnostic("source-ref", "source_refs must be a non-empty list", record.path, record.record_id, "source_refs"))
    else:
        for index, ref in enumerate(source_refs):
            if not isinstance(ref, dict):
                diagnostics.append(Diagnostic("source-ref", "source ref must be an object", record.path, record.record_id, f"source_refs[{index}]"))
                continue
            ref_path = ref.get("path")
            if not isinstance(ref_path, str) or not is_repo_relative_path(ref_path):
                diagnostics.append(Diagnostic("source-ref-path", "source ref path must be safe and repo-relative", record.path, record.record_id, f"source_refs[{index}].path"))
            elif not source_path_exists(ref_path):
                diagnostics.append(Diagnostic("source-ref-exists", "source ref path does not exist", record.path, record.record_id, f"source_refs[{index}].path"))
            if not isinstance(ref.get("role"), str) or not ref["role"]:
                diagnostics.append(Diagnostic("source-ref-role", "source ref role is required", record.path, record.record_id, f"source_refs[{index}].role"))

    safety = data.get("safety")
    if not isinstance(safety, dict):
        diagnostics.append(Diagnostic("safety", "safety must be an object", record.path, record.record_id, "safety"))
    else:
        for field in sorted(REQUIRED_SAFETY_FALSE_FIELDS):
            if safety.get(field) is not False:
                diagnostics.append(Diagnostic("safety-false", "safety field must be false", record.path, record.record_id, f"safety.{field}"))

    text = record.path.read_text(encoding="utf-8")
    for marker in FORBIDDEN_MARKERS:
        if marker in text:
            diagnostics.append(Diagnostic("forbidden-marker", f"forbidden marker found: {marker}", record.path, record.record_id))

    return diagnostics


def validate_kind_specific(record: AcpRecord, ids: set[str]) -> list[Diagnostic]:
    data = record.frontmatter
    kind = record.record_kind
    diagnostics: list[Diagnostic] = []

    def require_str(field: str) -> None:
        if not isinstance(data.get(field), str) or not data[field]:
            diagnostics.append(Diagnostic("required-string", "field must be a non-empty string", record.path, record.record_id, field))

    def require_ref(field: str, pattern: str) -> None:
        value = data.get(field)
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            diagnostics.append(Diagnostic("record-ref", "field must reference expected record id", record.path, record.record_id, field))
        elif value not in ids:
            diagnostics.append(Diagnostic("record-ref-exists", "referenced record id is missing", record.path, record.record_id, field))

    if kind == "architecture_prompt_record":
        for field in ("capture_mode", "redaction_status", "user_intent", "response_snapshot", "outcome"):
            require_str(field)
        if data.get("capture_mode") not in {"verbatim", "redacted-verbatim", "summarized-with-quotes", "metadata-only"}:
            diagnostics.append(Diagnostic("capture-mode", "unsupported capture mode", record.path, record.record_id, "capture_mode"))
        if data.get("redaction_status") not in {"checked", "redacted", "not-required"}:
            diagnostics.append(Diagnostic("redaction-status", "unsupported redaction status", record.path, record.record_id, "redaction_status"))
        require_ref("produced_proposal", r"AP-[0-9]{4}")
    elif kind == "architecture_proposal":
        require_ref("origin_prompt_record", r"APR-[0-9]{4}")
        for field in ("scope", "validation_plan"):
            require_str(field)
        candidates = data.get("decision_candidates")
        if not isinstance(candidates, list) or not candidates:
            diagnostics.append(Diagnostic("decision-candidates", "decision_candidates must be non-empty", record.path, record.record_id, "decision_candidates"))
        else:
            for candidate in candidates:
                if candidate not in ids:
                    diagnostics.append(Diagnostic("record-ref-exists", f"missing decision candidate {candidate}", record.path, record.record_id, "decision_candidates"))
    elif kind == "decision_candidate":
        require_ref("origin_proposal", r"AP-[0-9]{4}")
        require_ref("requires_proof_gate", r"PG-[0-9]{4}")
        if data.get("authority_required") is not True:
            diagnostics.append(Diagnostic("authority-required", "decision candidate must require authority", record.path, record.record_id, "authority_required"))
        for field in ("significance", "alternatives"):
            if not isinstance(data.get(field), list) or not data[field]:
                diagnostics.append(Diagnostic("required-list", "field must be a non-empty list", record.path, record.record_id, field))
        if data.get("status") not in {"candidate", "proposed", "rejected", "deferred"}:
            diagnostics.append(Diagnostic("candidate-status", "decision candidate has invalid status", record.path, record.record_id, "status"))
    elif kind == "proof_gate":
        for field in ("claim", "required_evidence_class", "failure_mode"):
            require_str(field)
        if not isinstance(data.get("blocks"), list) or not data["blocks"]:
            diagnostics.append(Diagnostic("blocks", "proof gate blocks must be non-empty", record.path, record.record_id, "blocks"))
    elif kind == "architecture_health_finding":
        for field in ("severity", "category", "finding", "recommended_fix"):
            require_str(field)
        if data.get("severity") not in {"info", "warning", "blocking"}:
            diagnostics.append(Diagnostic("severity", "invalid severity", record.path, record.record_id, "severity"))
        for field in ("affected_records", "blocked_actions"):
            if not isinstance(data.get(field), list) or not data[field]:
                diagnostics.append(Diagnostic("required-list", "field must be a non-empty list", record.path, record.record_id, field))
        for affected in data.get("affected_records", []):
            if affected not in ids:
                diagnostics.append(Diagnostic("record-ref-exists", f"missing affected record {affected}", record.path, record.record_id, "affected_records"))

    return diagnostics


def validate_records(records: list[AcpRecord]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    ids = {record.record_id for record in records}
    kinds = {record.record_kind for record in records}

    for required_kind in sorted(REQUIRED_RECORD_KINDS):
        if required_kind not in kinds:
            diagnostics.append(Diagnostic("required-kind", f"missing required record kind {required_kind}", DEFAULT_FIXTURE_DIR))

    seen: set[str] = set()
    for record in records:
        if record.record_id in seen:
            diagnostics.append(Diagnostic("duplicate-id", "duplicate ACP record id", record.path, record.record_id, "id"))
        seen.add(record.record_id)
        diagnostics.extend(validate_base(record))

    for record in records:
        diagnostics.extend(validate_kind_specific(record, ids))

    return diagnostics


def run(fixture_dir: Path) -> dict[str, Any]:
    records, diagnostics = load_records(fixture_dir)
    diagnostics.extend(validate_records(records))
    return {
        "status": "ok" if not diagnostics else "failed",
        "record_count": len(records),
        "records": [record.record_id for record in records],
        "diagnostic_count": len(diagnostics),
        "diagnostics": [diagnostic.to_json() for diagnostic in diagnostics],
        "boundary": "ACP validation proves fixture mechanics only; source evidence remains authoritative.",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=DEFAULT_FIXTURE_DIR,
        help="Directory containing ACP Markdown fixture records.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = run(args.fixture_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
