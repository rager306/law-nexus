#!/usr/bin/env python3
# ruff: noqa: E402
"""Build deterministic golden-case artifacts from tracked parser outputs.

This generator consumes only tracked ``prd/parser`` artifacts. It creates
bounded, non-authoritative golden-case fixtures for later parser/retrieval
evaluators and never rescans raw legal sources or claims parser completeness,
retrieval quality, legal-answer correctness, citation-safe retrieval readiness,
or FalkorDB runtime readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.parser_records import (  # noqa: E402
    DocumentRecord,
    RelationCandidateRecord,
    SourceBlockRecord,
    load_jsonl_records,
)

DEFAULT_OUTPUT_DIR = ROOT / "prd/parser"
CONTRACT_PATH = ROOT / "prd/parser/golden_test_contract.md"
DOCUMENT_RECORDS_PATH = ROOT / "prd/parser/odt_document_records.jsonl"
SOURCE_BLOCK_RECORDS_PATH = ROOT / "prd/parser/odt_source_block_records.jsonl"
RELATION_CANDIDATES_PATH = ROOT / "prd/parser/consultant_relation_candidates.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
REPORT_JSON = "golden_cases.json"
REPORT_MD = "golden_cases.md"
SCHEMA_VERSION = "legalgraph-parser-golden-cases/v1"
GENERATED_BY = "scripts/build-parser-golden-cases.py"
BLOCKED_CLAIMS = [
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness",
    "citation-safe retrieval readiness",
    "product ETL readiness",
    "FalkorDB loading/runtime readiness",
    "Consultant WordML legal authority",
    "relation correctness",
    "product graph truth",
]
REQUIRED_CASE_CLASSES = [
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
]
SOURCE_ARTIFACT_PATHS = [
    CONTRACT_PATH,
    DOCUMENT_RECORDS_PATH,
    SOURCE_BLOCK_RECORDS_PATH,
    RELATION_CANDIDATES_PATH,
    STAGING_GRAPH_PATH,
]


def display_path(path: Path) -> str:
    """Return a stable repository-relative path when possible."""

    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
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
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    expected_state: str | None = None,
    actual_state: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create a compact S01-contract diagnostic for agents and tests."""

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


def load_source_artifacts() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load the bounded tracked parser artifacts and return diagnostics."""

    diagnostics: list[dict[str, Any]] = []
    for path in SOURCE_ARTIFACT_PATHS:
        if not path.exists():
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="missing_source_artifact",
                    artifact_path=display_path(path),
                    message="Required tracked golden-case source artifact is missing.",
                    expected_state="readable-source-artifact",
                    actual_state="missing",
                )
            )

    documents_raw, document_diagnostics = load_jsonl_if_exists(DOCUMENT_RECORDS_PATH)
    source_blocks_raw, source_block_diagnostics = load_jsonl_if_exists(SOURCE_BLOCK_RECORDS_PATH)
    relation_candidates_raw, relation_diagnostics = load_jsonl_if_exists(RELATION_CANDIDATES_PATH)
    diagnostics.extend(convert_loader_diagnostics(document_diagnostics, None, None))
    diagnostics.extend(convert_loader_diagnostics(source_block_diagnostics, None, None))
    diagnostics.extend(convert_loader_diagnostics(relation_diagnostics, None, None))

    staging_graph: dict[str, Any] = {}
    if STAGING_GRAPH_PATH.exists():
        try:
            loaded = json.loads(STAGING_GRAPH_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                staging_graph = loaded
            else:
                diagnostics.append(
                    diagnostic(
                        case_id=None,
                        case_class=None,
                        severity="error",
                        rule="json_type",
                        artifact_path=display_path(STAGING_GRAPH_PATH),
                        message="Parser staging graph artifact must decode to a JSON object.",
                        expected_state="object",
                        actual_state=type(loaded).__name__,
                    )
                )
        except json.JSONDecodeError as exc:
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="json_invalid",
                    artifact_path=display_path(STAGING_GRAPH_PATH),
                    message=exc.msg,
                    expected_state="valid-json",
                    actual_state="invalid-json",
                )
            )

    documents = [record for record in documents_raw if isinstance(record, DocumentRecord)]
    source_blocks = [record for record in source_blocks_raw if isinstance(record, SourceBlockRecord)]
    relation_candidates = [record for record in relation_candidates_raw if isinstance(record, RelationCandidateRecord)]
    return {
        "documents": documents,
        "source_blocks": source_blocks,
        "relation_candidates": relation_candidates,
        "staging_graph": staging_graph,
    }, diagnostics


def load_jsonl_if_exists(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load parser JSONL records if the path exists; missing is reported elsewhere."""

    if not path.exists():
        return [], []
    return load_jsonl_records(path)


def convert_loader_diagnostics(
    loader_diagnostics: list[dict[str, Any]], case_id: str | None, case_class: str | None
) -> list[dict[str, Any]]:
    """Normalize parser-record loader diagnostics to the golden-case shape."""

    normalized: list[dict[str, Any]] = []
    for item in loader_diagnostics:
        normalized.append(
            diagnostic(
                case_id=case_id,
                case_class=case_class,
                severity="error",
                rule=str(item.get("rule") or "validation_error"),
                artifact_path=str(item.get("file") or item.get("artifact_path") or "<unknown>"),
                record_id=item.get("record_id"),
                record_kind=item.get("record_kind"),
                source_path=item.get("source_path"),
                expected_state="valid-parser-record",
                actual_state="invalid-parser-record",
                message=str(item.get("message") or "Parser record validation failed."),
                field=item.get("field"),
                line=item.get("line"),
            )
        )
    return normalized


def source_artifact_inventory() -> list[dict[str, Any]]:
    """Return deterministic source artifact paths and file hashes."""

    inventory: list[dict[str, Any]] = []
    for path in SOURCE_ARTIFACT_PATHS:
        item: dict[str, Any] = {
            "path": display_path(path),
            "exists": path.exists(),
        }
        if path.exists():
            item["sha256"] = sha256_file(path)
        inventory.append(item)
    return inventory


def make_anchor(record: Any, artifact_path: Path) -> dict[str, Any]:
    """Project one parser record into a bounded source anchor."""

    anchor: dict[str, Any] = {
        "artifact_path": display_path(artifact_path),
        "record_id": record.id,
        "record_kind": record.record_kind,
        "source_path": record.source_path,
        "source_sha256": record.source_sha256,
        "non_authoritative": record.non_authoritative,
    }
    if isinstance(record, SourceBlockRecord):
        anchor.update(
            {
                "document_id": record.document_id,
                "source_member": record.source_member,
                "location": record.location.model_dump(),
                "excerpt_sha256": record.excerpt_sha256,
            }
        )
    if isinstance(record, RelationCandidateRecord):
        anchor.update(
            {
                "source_block_id": record.source_block_id,
                "subject_ref": record.subject_ref,
                "object_ref": record.object_ref,
                "relation_type": record.relation_type,
                "relation_status": record.status,
                "evidence_sha256": record.evidence_sha256,
            }
        )
    return anchor


def build_cases(sources: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build all required golden cases from loaded tracked parser artifacts."""

    diagnostics: list[dict[str, Any]] = []
    documents: list[DocumentRecord] = sorted(sources["documents"], key=lambda record: record.id)
    source_blocks: list[SourceBlockRecord] = sorted(sources["source_blocks"], key=lambda record: (record.document_id, record.order_index, record.id))
    relation_candidates: list[RelationCandidateRecord] = sorted(sources["relation_candidates"], key=lambda record: record.id)
    staging_graph: dict[str, Any] = sources["staging_graph"]
    cases: list[dict[str, Any]] = []

    preferred_block = next((record for record in source_blocks if record.id == "BLOCK-44-FZ-000"), None)
    if preferred_block is None:
        preferred_block = next((record for record in source_blocks if record.document_id == "DOC-44-FZ"), None)
    if preferred_block is None and source_blocks:
        preferred_block = source_blocks[0]
    if preferred_block is None:
        diagnostics.append(
            diagnostic(
                case_id="GT-001",
                case_class="evidence-present",
                severity="error",
                rule="missing_evidence",
                artifact_path=display_path(SOURCE_BLOCK_RECORDS_PATH),
                message="No source-block record is available for an evidence-present golden case.",
                expected_state="evidence-present",
                actual_state="missing",
            )
        )
    else:
        cases.append(
            {
                "case_id": "GT-001",
                "case_class": "evidence-present",
                "description": "Bounded evidence exists for a tracked Garant ODT source block.",
                "source_artifacts": [display_path(SOURCE_BLOCK_RECORDS_PATH)],
                "anchors": [make_anchor(preferred_block, SOURCE_BLOCK_RECORDS_PATH)],
                "expected": {
                    "answer_state": "evidence-present",
                    "matched": True,
                    "required_record_ids": [preferred_block.id],
                    "forbidden_claims": BLOCKED_CLAIMS[:3],
                },
                "diagnostics": [],
                "non_authoritative": True,
                "non_claims": list(preferred_block.non_claims),
            }
        )

    absent_target = "DOC-ABSENT-GOLDEN-NO-ANSWER"
    known_ids = {record.id for record in [*documents, *source_blocks, *relation_candidates]}
    cases.append(
        {
            "case_id": "GT-002",
            "case_class": "no-answer",
            "description": "An intentionally absent target id must remain no-answer without fabricated evidence.",
            "source_artifacts": [
                display_path(DOCUMENT_RECORDS_PATH),
                display_path(SOURCE_BLOCK_RECORDS_PATH),
                display_path(RELATION_CANDIDATES_PATH),
            ],
            "anchors": [],
            "expected": {
                "answer_state": "no-answer",
                "matched": False,
                "missing_target_id": absent_target,
                "inspected_artifact_paths": [
                    display_path(DOCUMENT_RECORDS_PATH),
                    display_path(SOURCE_BLOCK_RECORDS_PATH),
                    display_path(RELATION_CANDIDATES_PATH),
                ],
                "expected_match_count": 0,
                "forbidden_claims": BLOCKED_CLAIMS[:3],
            },
            "diagnostics": [
                diagnostic(
                    case_id="GT-002",
                    case_class="no-answer",
                    severity="info",
                    rule="intentionally_absent_target",
                    artifact_path=display_path(SOURCE_BLOCK_RECORDS_PATH),
                    record_id=absent_target,
                    record_kind="result",
                    expected_state="no-answer",
                    actual_state="no-answer" if absent_target not in known_ids else "target-present",
                    message="Golden no-answer target is intentionally absent from tracked parser artifacts.",
                )
            ],
            "non_authoritative": True,
            "non_claims": ["No-answer behavior does not prove recall, parser completeness, or product retrieval quality."],
        }
    )
    if absent_target in known_ids:
        diagnostics.append(
            diagnostic(
                case_id="GT-002",
                case_class="no-answer",
                severity="error",
                rule="absent_target_present",
                artifact_path=display_path(SOURCE_BLOCK_RECORDS_PATH),
                record_id=absent_target,
                record_kind="result",
                expected_state="no-answer",
                actual_state="target-present",
                message="The intentionally absent no-answer target unexpectedly exists.",
            )
        )

    relation = next((record for record in relation_candidates if record.id == "REL-CONS-0001"), None)
    if relation is None:
        diagnostics.append(
            diagnostic(
                case_id="GT-003",
                case_class="candidate-only",
                severity="error",
                rule="missing_candidate",
                artifact_path=display_path(RELATION_CANDIDATES_PATH),
                record_id="REL-CONS-0001",
                record_kind="relation_candidate",
                expected_state="candidate-only",
                actual_state="missing",
                message="Required candidate-only relation REL-CONS-0001 is absent.",
            )
        )
    elif relation.status != "candidate":
        diagnostics.append(
            diagnostic(
                case_id="GT-003",
                case_class="candidate-only",
                severity="error",
                rule="candidate_promoted",
                artifact_path=display_path(RELATION_CANDIDATES_PATH),
                record_id=relation.id,
                record_kind="relation_candidate",
                source_path=relation.source_path,
                expected_state="candidate-only",
                actual_state=relation.status,
                message="REL-CONS-0001 must remain status:candidate for this golden fixture.",
            )
        )
    else:
        cases.append(
            {
                "case_id": "GT-003",
                "case_class": "candidate-only",
                "description": "Consultant relation candidate remains visible only as status:candidate.",
                "source_artifacts": [display_path(RELATION_CANDIDATES_PATH), display_path(STAGING_GRAPH_PATH)],
                "anchors": [make_anchor(relation, RELATION_CANDIDATES_PATH)],
                "expected": {
                    "answer_state": "candidate-only",
                    "matched": True,
                    "required_record_ids": [relation.id],
                    "required_relation_status": "candidate",
                    "required_staging_edge_key": relation.id,
                    "forbidden_claims": ["relation correctness", "Consultant WordML legal authority", "product graph truth"],
                },
                "diagnostics": [],
                "non_authoritative": True,
                "non_claims": list(relation.non_claims),
            }
        )

    unresolved_ids = sorted(str(value) for value in staging_graph.get("unresolved_reference_ids", []) if isinstance(value, str))
    if not unresolved_ids:
        diagnostics.append(
            diagnostic(
                case_id="GT-004",
                case_class="unresolved-reference",
                severity="error",
                rule="unresolved_reference_missing",
                artifact_path=display_path(STAGING_GRAPH_PATH),
                record_kind="unresolved_reference",
                expected_state="unresolved-reference",
                actual_state="missing",
                message="Parser staging graph has no unresolved_reference_ids for the unresolved-reference golden case.",
            )
        )
    else:
        unresolved_diagnostics = []
        staging_diagnostics = staging_graph.get("diagnostics", [])
        if isinstance(staging_diagnostics, list):
            for item in staging_diagnostics:
                if not isinstance(item, dict):
                    continue
                if item.get("rule") in {"unresolved_subject_ref", "unresolved_object_ref"}:
                    unresolved_diagnostics.append(
                        diagnostic(
                            case_id="GT-004",
                            case_class="unresolved-reference",
                            severity=str(item.get("severity") or "warning"),
                            rule=str(item.get("rule") or "unresolved_reference"),
                            artifact_path=display_path(STAGING_GRAPH_PATH),
                            record_id=item.get("record_id"),
                            record_kind="unresolved_reference",
                            source_path=item.get("source_path"),
                            expected_state="unresolved-reference",
                            actual_state="unresolved-reference",
                            message=str(item.get("message") or "Unresolved reference remains explicit."),
                            field=item.get("field"),
                        )
                    )
        cases.append(
            {
                "case_id": "GT-004",
                "case_class": "unresolved-reference",
                "description": "Staging unresolved references stay explicit and are not rewritten to ODT ids.",
                "source_artifacts": [display_path(STAGING_GRAPH_PATH)],
                "anchors": [
                    {
                        "artifact_path": display_path(STAGING_GRAPH_PATH),
                        "record_id": unresolved_id,
                        "record_kind": "unresolved_reference",
                        "source_path": None,
                        "source_sha256": None,
                        "non_authoritative": True,
                    }
                    for unresolved_id in unresolved_ids
                ],
                "expected": {
                    "answer_state": "unresolved-reference",
                    "matched": True,
                    "required_reference_ids": unresolved_ids,
                    "forbidden_claims": [
                        "endpoint resolution",
                        "FalkorDB loading/runtime readiness",
                        "citation-safe retrieval readiness",
                    ],
                },
                "diagnostics": unresolved_diagnostics,
                "non_authoritative": True,
                "non_claims": list(staging_graph.get("non_claims") or []),
            }
        )

    non_claims = sorted(
        {
            claim
            for record in [*documents, *source_blocks, *relation_candidates]
            for claim in record.non_claims
            if isinstance(claim, str) and claim.strip()
        }
        | {claim for claim in staging_graph.get("non_claims", []) if isinstance(claim, str) and claim.strip()}
    )
    if not non_claims:
        diagnostics.append(
            diagnostic(
                case_id="GT-005",
                case_class="non-authoritative",
                severity="error",
                rule="missing_non_claims",
                artifact_path=display_path(CONTRACT_PATH),
                record_kind="result",
                expected_state="non-authoritative-boundary",
                actual_state="missing",
                message="No non_claims were found in current parser/staging artifacts.",
            )
        )
    else:
        cases.append(
            {
                "case_id": "GT-005",
                "case_class": "non-authoritative",
                "description": "Parser/staging non-claim metadata blocks legal-answer and retrieval-quality claims.",
                "source_artifacts": [
                    display_path(CONTRACT_PATH),
                    display_path(DOCUMENT_RECORDS_PATH),
                    display_path(SOURCE_BLOCK_RECORDS_PATH),
                    display_path(RELATION_CANDIDATES_PATH),
                    display_path(STAGING_GRAPH_PATH),
                ],
                "anchors": [
                    {
                        "artifact_path": display_path(CONTRACT_PATH),
                        "record_id": "golden-test-contract",
                        "record_kind": "result",
                        "source_path": None,
                        "source_sha256": sha256_file(CONTRACT_PATH) if CONTRACT_PATH.exists() else None,
                        "non_authoritative": True,
                    }
                ],
                "expected": {
                    "answer_state": "non-authoritative-boundary",
                    "matched": True,
                    "blocked_claims": BLOCKED_CLAIMS,
                    "required_non_claim_fragments": BLOCKED_CLAIMS[:3],
                },
                "diagnostics": [
                    diagnostic(
                        case_id="GT-005",
                        case_class="non-authoritative",
                        severity="info",
                        rule="claims_blocked",
                        artifact_path=display_path(CONTRACT_PATH),
                        record_id="blocked-claims",
                        record_kind="result",
                        expected_state="non-authoritative-boundary",
                        actual_state="non-authoritative-boundary",
                        message="Golden cases preserve parser/retrieval/legal-answer blocked-claim labels.",
                    )
                ],
                "non_authoritative": True,
                "non_claims": non_claims,
            }
        )

    case_classes = {case["case_class"] for case in cases}
    for case_class in REQUIRED_CASE_CLASSES:
        if case_class not in case_classes:
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=case_class,
                    severity="error",
                    rule="required_case_class_missing",
                    artifact_path=display_path(CONTRACT_PATH),
                    expected_state=case_class,
                    actual_state="missing",
                    message=f"Required golden case class {case_class!r} was not generated.",
                )
            )
    return cases, diagnostics


def build_report(*, artifact_freshness: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create deterministic machine-readable golden-case artifact content."""

    sources, load_diagnostics = load_source_artifacts()
    cases, case_diagnostics = build_cases(sources)
    embedded_case_diagnostics = [
        item
        for case in cases
        for item in case.get("diagnostics", [])
        if isinstance(item, dict)
    ]
    all_case_diagnostics = [*load_diagnostics, *case_diagnostics, *embedded_case_diagnostics]
    case_class_counts = {case_class: 0 for case_class in REQUIRED_CASE_CLASSES}
    for case in cases:
        case_class_counts[case["case_class"]] = case_class_counts.get(case["case_class"], 0) + 1
    freshness = artifact_freshness or {"status": "not-checked", "stale_paths": [], "diagnostics": []}
    freshness_diagnostics = list(freshness.get("diagnostics") or [])
    diagnostics = [*all_case_diagnostics, *freshness_diagnostics]
    error_count = sum(1 for item in diagnostics if item.get("severity") == "error")
    status = "pass" if error_count == 0 else "fail"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "status": status,
        "artifact_freshness": freshness,
        "non_authoritative": True,
        "blocked_claims": BLOCKED_CLAIMS,
        "source_artifacts": source_artifact_inventory(),
        "case_count": len(cases),
        "case_class_counts": dict(sorted(case_class_counts.items())),
        "cases": sorted(cases, key=lambda case: case["case_id"]),
        "diagnostic_count": len(diagnostics),
        "error_count": error_count,
        "warning_count": sum(1 for item in diagnostics if item.get("severity") == "warning"),
        "info_count": sum(1 for item in diagnostics if item.get("severity") == "info"),
        "diagnostics": sorted(diagnostics, key=diagnostic_sort_key),
    }


def diagnostic_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """Stable diagnostic sort key."""

    return (
        str(item.get("severity") or ""),
        str(item.get("artifact_path") or ""),
        str(item.get("case_id") or ""),
        str(item.get("rule") or ""),
        str(item.get("record_id") or ""),
    )


def render_markdown(report: dict[str, Any]) -> str:
    """Render bounded human-readable golden-case inventory."""

    lines = [
        "# Parser Golden Cases",
        "",
        f"- Status: `{report['status']}`",
        f"- Schema: `{report['schema_version']}`",
        f"- Generated by: `{report['generated_by']}`",
        "- Non-authoritative: true.",
        f"- Case count: {report['case_count']}",
        f"- Artifact freshness: `{report['artifact_freshness']['status']}`",
        "",
        "## Case inventory",
        "",
        "| Case ID | Class | Expected state | Matched | Anchor IDs |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        expected = case["expected"]
        anchor_ids = ", ".join(str(anchor.get("record_id")) for anchor in case.get("anchors", [])) or "none"
        lines.append(
            f"| `{case['case_id']}` | `{case['case_class']}` | `{expected.get('answer_state')}` | `{expected.get('matched')}` | {anchor_ids} |"
        )

    lines.extend(["", "## Source artifacts", "", "| Artifact | Exists | SHA-256 |", "| --- | --- | --- |"])
    for artifact in report["source_artifacts"]:
        lines.append(f"| `{artifact['path']}` | `{artifact['exists']}` | `{artifact.get('sha256', '')}` |")

    lines.extend(["", "## Source anchors", ""])
    for case in report["cases"]:
        lines.extend([f"### {case['case_id']} — {case['case_class']}", ""])
        anchors = case.get("anchors", [])
        if not anchors:
            lines.append("- No source anchor: this case intentionally expects no answer.")
        else:
            for anchor in anchors:
                details = [
                    f"artifact `{anchor.get('artifact_path')}`",
                    f"record `{anchor.get('record_id')}`",
                    f"kind `{anchor.get('record_kind')}`",
                ]
                if anchor.get("source_path"):
                    details.append(f"source `{anchor.get('source_path')}`")
                if anchor.get("source_sha256"):
                    details.append(f"source hash `{anchor.get('source_sha256')}`")
                if anchor.get("excerpt_sha256"):
                    details.append(f"excerpt hash `{anchor.get('excerpt_sha256')}`")
                if anchor.get("evidence_sha256"):
                    details.append(f"evidence hash `{anchor.get('evidence_sha256')}`")
                lines.append("- " + "; ".join(details) + ".")
        lines.append("")

    lines.extend(
        [
            "## Blocked claims and non-claim boundaries",
            "",
            "A golden-case pass under this artifact must not be described as proof of:",
            "",
        ]
    )
    lines.extend(f"- {claim}" for claim in report["blocked_claims"])
    lines.extend(
        [
            "",
            "These fixtures are bounded parser/retrieval evidence inputs only. They do not provide legal advice, authoritative legal interpretation, product retrieval quality proof, citation-safe retrieval readiness, production graph truth, or FalkorDB runtime proof.",
            "",
            "## Diagnostics",
            "",
            f"- Errors: {report['error_count']}",
            f"- Warnings: {report['warning_count']}",
            f"- Info: {report['info_count']}",
            "",
            "| Severity | Case | Rule | Artifact | Record | Message |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if report["diagnostics"]:
        for item in report["diagnostics"][:40]:
            message = str(item.get("message") or "").replace("|", "\\|")
            lines.append(
                f"| `{item.get('severity')}` | `{item.get('case_id')}` | `{item.get('rule')}` | `{item.get('artifact_path')}` | `{item.get('record_id')}` | {message} |"
            )
        if len(report["diagnostics"]) > 40:
            lines.append(
                f"| `info` | `report` | `bounded-report` | `prd/parser/golden_cases.md` | `None` | {len(report['diagnostics']) - 40} additional diagnostics omitted from Markdown. |"
            )
    else:
        lines.append("| `info` | `report` | `none` | `prd/parser/golden_cases.json` | `None` | No diagnostics. |")
    lines.append("")
    return "\n".join(lines)


def output_contents() -> dict[str, str]:
    """Return deterministic artifact bytes keyed by output filename."""

    report = build_report()
    return {
        REPORT_JSON: json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        REPORT_MD: render_markdown(report),
    }


def write_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Write deterministic golden-case artifacts and return a CLI report."""

    output_dir.mkdir(parents=True, exist_ok=True)
    expected = output_contents()
    for name, content in expected.items():
        (output_dir / name).write_text(content, encoding="utf-8")
    return build_report()


def check_outputs(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Byte-compare expected golden-case artifacts and return compact status."""

    expected = output_contents()
    stale_paths: list[str] = []
    freshness_diagnostics: list[dict[str, Any]] = []
    for name, content in expected.items():
        path = output_dir / name
        stable_path = display_path(path)
        if not path.exists():
            stale_paths.append(stable_path)
            freshness_diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="stale-artifact",
                    artifact_path=stable_path,
                    message="Expected parser golden-case artifact is missing.",
                    expected_state="fresh-artifact",
                    actual_state="missing",
                )
            )
            continue
        if path.read_text(encoding="utf-8") != content:
            stale_paths.append(stable_path)
            freshness_diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="stale-artifact",
                    artifact_path=stable_path,
                    message="Expected parser golden-case artifact bytes are stale.",
                    expected_state="fresh-artifact",
                    actual_state="stale",
                )
            )
    freshness = {
        "status": "pass" if not freshness_diagnostics else "stale",
        "stale_paths": stale_paths,
        "diagnostics": freshness_diagnostics,
    }
    return build_report(artifact_freshness=freshness)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="Write deterministic parser golden-case artifacts.")
    mode.add_argument("--check", action="store_true", help="Check parser golden-case artifact freshness and print compact JSON.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Artifact directory, default prd/parser.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    report = write_outputs(args.output_dir) if args.write else check_outputs(args.output_dir)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
