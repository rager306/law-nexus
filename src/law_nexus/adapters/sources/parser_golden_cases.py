"""Shared helpers for parser golden-case builder/evaluator scripts.

These helpers are deterministic support utilities only. They do not read raw legal
sources and do not claim parser completeness, retrieval quality, legal-answer
correctness, or FalkorDB readiness.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, cast

from law_nexus.adapters.sources.parser_records import (
    DocumentRecord,
    RelationCandidateRecord,
    SourceBlockRecord,
    load_jsonl_records,
)


def display_path(path: Path, *, root: Path) -> str:
    """Return a stable repository-relative path when possible."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
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
    expected_state: str | None = None,
    actual_state: str | None = None,
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create a compact path-qualified diagnostic payload."""

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


def load_json_object(
    path: Path, *, root: Path
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Load a JSON object and report bounded diagnostics instead of raising."""

    if not path.exists():
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path, root=root),
                expected_state="readable-source-artifact",
                actual_state="missing",
                message="Required tracked parser golden-case source artifact is missing.",
            )
        ]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="invalid_json",
                artifact_path=display_path(path, root=root),
                expected_state="valid-json-object",
                actual_state="invalid-json",
                message=str(exc),
            )
        ]
    if not isinstance(loaded, dict):
        return None, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="invalid_json_shape",
                artifact_path=display_path(path, root=root),
                expected_state="json-object",
                actual_state=type(loaded).__name__,
                message="Expected a JSON object.",
            )
        ]
    return loaded, []


def load_jsonl_if_exists(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load parser JSONL records if the path exists; missing is reported elsewhere."""

    if not path.exists():
        return [], []
    return load_jsonl_records(path)


def diagnostic_sort_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    """Return a stable diagnostic sort key."""

    return (
        str(item.get("severity") or ""),
        str(item.get("case_id") or ""),
        str(item.get("rule") or ""),
        str(item.get("artifact_path") or ""),
    )


def sort_diagnostics(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return diagnostics in deterministic order."""

    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        items,
        key=lambda item: (
            severity_order.get(str(item.get("severity")), 99),
            str(item.get("case_id") or ""),
            str(item.get("rule") or ""),
            str(item.get("artifact_path") or ""),
        ),
    )


def severity_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    """Count diagnostics by severity in stable key order."""

    counts: dict[str, int] = {}
    for item in items:
        severity = str(item.get("severity") or "unknown")
        counts[severity] = counts.get(severity, 0) + 1
    return dict(sorted(counts.items()))


def source_artifact_inventory_core(
    source_artifact_paths: list[Path], *, root: Path
) -> list[dict[str, Any]]:
    """Return deterministic source artifact paths and file hashes."""

    inventory: list[dict[str, Any]] = []
    for path in source_artifact_paths:
        item: dict[str, Any] = {
            "path": display_path(path, root=root),
            "exists": path.exists(),
        }
        if path.exists():
            item["sha256"] = sha256_file(path)
        inventory.append(item)
    return inventory


def make_anchor_core(record: Any, artifact_path: Path, *, root: Path) -> dict[str, Any]:
    """Project one parser record into a bounded source anchor."""

    anchor: dict[str, Any] = {
        "artifact_path": display_path(artifact_path, root=root),
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


def build_cases(
    sources: dict[str, Any],
    *,
    contract_path: Path,
    document_records_path: Path,
    source_block_records_path: Path,
    relation_candidates_path: Path,
    staging_graph_path: Path,
    required_case_classes: Sequence[str],
    blocked_claims: Sequence[str],
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build all required golden cases from loaded tracked parser artifacts."""

    diagnostics: list[dict[str, Any]] = []
    documents: list[DocumentRecord] = sorted(sources["documents"], key=lambda record: record.id)
    source_blocks: list[SourceBlockRecord] = sorted(
        sources["source_blocks"],
        key=lambda record: (record.document_id, record.order_index, record.id),
    )
    relation_candidates: list[RelationCandidateRecord] = sorted(
        sources["relation_candidates"], key=lambda record: record.id
    )
    staging_graph: dict[str, Any] = sources["staging_graph"]
    cases: list[dict[str, Any]] = []

    preferred_block = next(
        (record for record in source_blocks if record.id == "BLOCK-44-FZ-000"), None
    )
    if preferred_block is None:
        preferred_block = next(
            (record for record in source_blocks if record.document_id == "DOC-44-FZ"), None
        )
    if preferred_block is None and source_blocks:
        preferred_block = source_blocks[0]
    if preferred_block is None:
        diagnostics.append(
            diagnostic(
                case_id="GT-001",
                case_class="evidence-present",
                severity="error",
                rule="missing_evidence",
                artifact_path=display_path(source_block_records_path, root=root),
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
                "source_artifacts": [display_path(source_block_records_path, root=root)],
                "anchors": [
                    make_anchor_core(preferred_block, source_block_records_path, root=root)
                ],
                "expected": {
                    "answer_state": "evidence-present",
                    "matched": True,
                    "required_record_ids": [preferred_block.id],
                    "forbidden_claims": blocked_claims[:3],
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
                display_path(document_records_path, root=root),
                display_path(source_block_records_path, root=root),
                display_path(relation_candidates_path, root=root),
            ],
            "anchors": [],
            "expected": {
                "answer_state": "no-answer",
                "matched": False,
                "missing_target_id": absent_target,
                "inspected_artifact_paths": [
                    display_path(document_records_path, root=root),
                    display_path(source_block_records_path, root=root),
                    display_path(relation_candidates_path, root=root),
                ],
                "expected_match_count": 0,
                "forbidden_claims": blocked_claims[:3],
            },
            "diagnostics": [
                diagnostic(
                    case_id="GT-002",
                    case_class="no-answer",
                    severity="info",
                    rule="intentionally_absent_target",
                    artifact_path=display_path(source_block_records_path, root=root),
                    record_id=absent_target,
                    record_kind="result",
                    expected_state="no-answer",
                    actual_state="no-answer"
                    if absent_target not in known_ids
                    else "target-present",
                    message="Golden no-answer target is intentionally absent from tracked parser artifacts.",
                )
            ],
            "non_authoritative": True,
            "non_claims": [
                "No-answer behavior does not prove recall, parser completeness, or product retrieval quality."
            ],
        }
    )
    if absent_target in known_ids:
        diagnostics.append(
            diagnostic(
                case_id="GT-002",
                case_class="no-answer",
                severity="error",
                rule="absent_target_present",
                artifact_path=display_path(source_block_records_path, root=root),
                record_id=absent_target,
                record_kind="result",
                expected_state="no-answer",
                actual_state="target-present",
                message="The intentionally absent no-answer target unexpectedly exists.",
            )
        )

    relation = next(
        (record for record in relation_candidates if record.id == "REL-CONS-0001"), None
    )
    if relation is None:
        diagnostics.append(
            diagnostic(
                case_id="GT-003",
                case_class="candidate-only",
                severity="error",
                rule="missing_candidate",
                artifact_path=display_path(relation_candidates_path, root=root),
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
                artifact_path=display_path(relation_candidates_path, root=root),
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
                "source_artifacts": [
                    display_path(relation_candidates_path, root=root),
                    display_path(staging_graph_path, root=root),
                ],
                "anchors": [make_anchor_core(relation, relation_candidates_path, root=root)],
                "expected": {
                    "answer_state": "candidate-only",
                    "matched": True,
                    "required_record_ids": [relation.id],
                    "required_relation_status": "candidate",
                    "required_staging_edge_key": relation.id,
                    "forbidden_claims": [
                        "relation correctness",
                        "Consultant WordML legal authority",
                        "product graph truth",
                    ],
                },
                "diagnostics": [],
                "non_authoritative": True,
                "non_claims": list(relation.non_claims),
            }
        )

    unresolved_ids = sorted(
        str(value)
        for value in staging_graph.get("unresolved_reference_ids", [])
        if isinstance(value, str)
    )
    if not unresolved_ids:
        diagnostics.append(
            diagnostic(
                case_id="GT-004",
                case_class="unresolved-reference",
                severity="error",
                rule="unresolved_reference_missing",
                artifact_path=display_path(staging_graph_path, root=root),
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
                            artifact_path=display_path(staging_graph_path, root=root),
                            record_id=item.get("record_id"),
                            record_kind="unresolved_reference",
                            source_path=item.get("source_path"),
                            expected_state="unresolved-reference",
                            actual_state="unresolved-reference",
                            message=str(
                                item.get("message") or "Unresolved reference remains explicit."
                            ),
                            field=item.get("field"),
                        )
                    )
        cases.append(
            {
                "case_id": "GT-004",
                "case_class": "unresolved-reference",
                "description": "Staging unresolved references stay explicit and are not rewritten to ODT ids.",
                "source_artifacts": [display_path(staging_graph_path, root=root)],
                "anchors": [
                    {
                        "artifact_path": display_path(staging_graph_path, root=root),
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
        | {
            claim
            for claim in staging_graph.get("non_claims", [])
            if isinstance(claim, str) and claim.strip()
        }
    )
    if not non_claims:
        diagnostics.append(
            diagnostic(
                case_id="GT-005",
                case_class="non-authoritative",
                severity="error",
                rule="missing_non_claims",
                artifact_path=display_path(contract_path, root=root),
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
                    display_path(contract_path, root=root),
                    display_path(document_records_path, root=root),
                    display_path(source_block_records_path, root=root),
                    display_path(relation_candidates_path, root=root),
                    display_path(staging_graph_path, root=root),
                ],
                "anchors": [
                    {
                        "artifact_path": display_path(contract_path, root=root),
                        "record_id": "golden-test-contract",
                        "record_kind": "result",
                        "source_path": None,
                        "source_sha256": sha256_file(contract_path)
                        if contract_path.exists()
                        else None,
                        "non_authoritative": True,
                    }
                ],
                "expected": {
                    "answer_state": "non-authoritative-boundary",
                    "matched": True,
                    "blocked_claims": blocked_claims,
                    "required_non_claim_fragments": blocked_claims[:3],
                },
                "diagnostics": [
                    diagnostic(
                        case_id="GT-005",
                        case_class="non-authoritative",
                        severity="info",
                        rule="claims_blocked",
                        artifact_path=display_path(contract_path, root=root),
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
    for case_class in required_case_classes:
        if case_class not in case_classes:
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=case_class,
                    severity="error",
                    rule="required_case_class_missing",
                    artifact_path=display_path(contract_path, root=root),
                    expected_state=case_class,
                    actual_state="missing",
                    message=f"Required golden case class {case_class!r} was not generated.",
                )
            )
    return cases, diagnostics


# Evaluator core helpers migrated from scripts/evaluate-parser-golden-cases.py.
def sort_evaluation_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort diagnostics deterministically by severity context and path."""

    severity_order = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        diagnostics,
        key=lambda item: (
            severity_order.get(str(item.get("severity")), 9),
            str(item.get("case_id") or ""),
            str(item.get("case_class") or ""),
            str(item.get("artifact_path") or ""),
            str(item.get("rule") or ""),
            str(item.get("record_id") or ""),
        ),
    )


def evaluation_severity_counts(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    """Return deterministic severity counts with explicit zeroes."""

    counts = {"error": 0, "warning": 0, "info": 0}
    for item in diagnostics:
        severity = str(item.get("severity") or "")
        if severity in counts:
            counts[severity] += 1
    return counts


def evaluation_loader_diagnostics(
    loader_diagnostics: list[dict[str, Any]], *, artifact_path: Path, root: Path
) -> list[dict[str, Any]]:
    """Normalize parser-record loader diagnostics to evaluator diagnostics."""

    normalized: list[dict[str, Any]] = []
    for item in loader_diagnostics:
        normalized.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule=str(item.get("rule") or "validation_error"),
                artifact_path=str(item.get("file") or display_path(artifact_path, root=root)),
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


def load_evaluation_source_artifacts(
    parser_dir: Path,
    *,
    source_artifact_filenames: dict[str, str],
    root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load all bounded parser artifacts consumed by the evaluator."""

    diagnostics: list[dict[str, Any]] = []
    documents_raw, document_diagnostics = load_jsonl_records(
        parser_dir / source_artifact_filenames["documents"]
    )
    source_blocks_raw, source_block_diagnostics = load_jsonl_records(
        parser_dir / source_artifact_filenames["source_blocks"]
    )
    relations_raw, relation_diagnostics = load_jsonl_records(
        parser_dir / source_artifact_filenames["relations"]
    )
    diagnostics.extend(
        evaluation_loader_diagnostics(
            document_diagnostics,
            artifact_path=parser_dir / source_artifact_filenames["documents"],
            root=root,
        )
    )
    diagnostics.extend(
        evaluation_loader_diagnostics(
            source_block_diagnostics,
            artifact_path=parser_dir / source_artifact_filenames["source_blocks"],
            root=root,
        )
    )
    diagnostics.extend(
        evaluation_loader_diagnostics(
            relation_diagnostics,
            artifact_path=parser_dir / source_artifact_filenames["relations"],
            root=root,
        )
    )

    staging_graph_path = parser_dir / source_artifact_filenames["staging_graph"]
    if not staging_graph_path.exists():
        staging_graph = {}
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(staging_graph_path, root=root),
                expected_state="readable-json-object",
                actual_state="missing",
                message="Required parser staging graph artifact is missing.",
            )
        )
    else:
        staging_graph_loaded, staging_diagnostics = load_json_object(staging_graph_path, root=root)
        staging_graph = staging_graph_loaded or {}
        diagnostics.extend(staging_diagnostics)

    documents = [record for record in documents_raw if isinstance(record, DocumentRecord)]
    source_blocks = [
        record for record in source_blocks_raw if isinstance(record, SourceBlockRecord)
    ]
    relations = [record for record in relations_raw if isinstance(record, RelationCandidateRecord)]
    record_ids = {record.id for record in [*documents, *source_blocks, *relations]}
    return {
        "documents": documents,
        "source_blocks": source_blocks,
        "relations": relations,
        "staging_graph": staging_graph,
        "record_ids": record_ids,
    }, diagnostics


def load_golden_cases_report(
    path: Path, *, golden_cases_schema_version: str, root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load and minimally validate the golden-case report artifact."""

    diagnostics: list[dict[str, Any]] = []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="json_invalid",
                artifact_path=display_path(path, root=root),
                expected_state="valid-json-object",
                actual_state="invalid-json",
                message=exc.msg,
            )
        ]
    if not isinstance(loaded, dict):
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="json_type",
                artifact_path=display_path(path, root=root),
                expected_state="object",
                actual_state=type(loaded).__name__,
                message="golden_cases.json must decode to a JSON object.",
            )
        ]
    report = loaded
    if report.get("schema_version") != golden_cases_schema_version:
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="unsupported_golden_cases_schema",
                artifact_path=display_path(path, root=root),
                expected_state=golden_cases_schema_version,
                actual_state=str(report.get("schema_version")),
                message="golden_cases.json schema_version is unsupported.",
            )
        )
    cases = report.get("cases")
    if not isinstance(cases, list):
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="golden_cases_shape_invalid",
                artifact_path=display_path(path, root=root),
                expected_state="cases-list",
                actual_state=type(cases).__name__,
                message="golden_cases.json must contain a cases array.",
            )
        )
    return report, diagnostics


def require_case_mapping(
    golden_report: dict[str, Any], *, golden_path: Path, required_case_classes: set[str], root: Path
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Return cases keyed by class, failing closed for duplicates or unsupported classes."""

    diagnostics: list[dict[str, Any]] = []
    cases_by_class: dict[str, dict[str, Any]] = {}
    raw_cases = golden_report.get("cases")
    cases = raw_cases if isinstance(raw_cases, list) else []
    for case in cases:
        if not isinstance(case, dict):
            diagnostics.append(
                diagnostic(
                    case_id=None,
                    case_class=None,
                    severity="error",
                    rule="golden_case_type_invalid",
                    artifact_path=display_path(golden_path, root=root),
                    expected_state="case-object",
                    actual_state=type(case).__name__,
                    message="Each golden case must be a JSON object.",
                )
            )
            continue
        case_id = str(case.get("case_id") or "") or None
        case_class = str(case.get("case_class") or "") or None
        if case_class not in required_case_classes:
            diagnostics.append(
                diagnostic(
                    case_id=case_id,
                    case_class=case_class,
                    severity="error",
                    rule="unsupported_case_class",
                    artifact_path=display_path(golden_path, root=root),
                    expected_state="supported-case-class",
                    actual_state=case_class,
                    message="Unsupported golden-case class fails closed.",
                )
            )
            continue
        if case_class in cases_by_class:
            diagnostics.append(
                diagnostic(
                    case_id=case_id,
                    case_class=case_class,
                    severity="error",
                    rule="duplicate_case_class",
                    artifact_path=display_path(golden_path, root=root),
                    expected_state="one-case-per-required-class",
                    actual_state="duplicate",
                    message="Golden cases must contain at most one case for each required class.",
                )
            )
            continue
        case_class_key = str(case_class)
        cases_by_class[case_class_key] = case

    for required in sorted(required_case_classes - set(cases_by_class)):
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=required,
                severity="error",
                rule="required_case_class_missing",
                artifact_path=display_path(golden_path, root=root),
                expected_state="present",
                actual_state="missing",
                message="Required golden-case class is missing or invalid.",
            )
        )
    return cases_by_class, diagnostics


def expected_list(case: dict[str, Any], key: str) -> list[str]:
    """Return a string list from a case expected payload."""

    expected = case.get("expected")
    value = expected.get(key) if isinstance(expected, dict) else None
    return [str(item) for item in value] if isinstance(value, list) else []


def evaluate_evidence_present(
    case: dict[str, Any],
    *,
    source_blocks: list[SourceBlockRecord],
    source_blocks_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Verify all required evidence record ids and bounded anchors remain present."""

    diagnostics: list[dict[str, Any]] = []
    by_id = {record.id: record for record in source_blocks}
    raw_anchors = case.get("anchors")
    anchors = raw_anchors if isinstance(raw_anchors, list) else []
    if not anchors:
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="evidence-present",
                severity="error",
                rule="evidence_anchor_missing",
                artifact_path=display_path(source_blocks_path, root=root),
                record_kind="source_block",
                expected_state="bounded-anchor-present",
                actual_state="missing",
                message="Evidence-present cases must keep at least one bounded source-block anchor.",
            )
        )
    anchors_by_record_id: dict[str, list[dict[str, Any]]] = {}
    for anchor in anchors:
        if isinstance(anchor, dict):
            anchors_by_record_id.setdefault(str(anchor.get("record_id") or ""), []).append(anchor)
    for record_id in expected_list(case, "required_record_ids"):
        record = by_id.get(record_id)
        if record is None:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="evidence-present",
                    severity="error",
                    rule="required_evidence_missing",
                    artifact_path=display_path(source_blocks_path, root=root),
                    record_id=record_id,
                    record_kind="source_block",
                    expected_state="evidence-present",
                    actual_state="missing",
                    message="Required evidence source-block id is absent from parser records.",
                )
            )
            continue
        record_anchors = anchors_by_record_id.get(record_id, [])
        if not record_anchors:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="evidence-present",
                    severity="error",
                    rule="evidence_anchor_missing",
                    artifact_path=display_path(source_blocks_path, root=root),
                    record_id=record_id,
                    record_kind="source_block",
                    expected_state="bounded-anchor-present",
                    actual_state="missing",
                    message="Required evidence source-block id has no matching golden anchor.",
                )
            )
            continue
        for anchor in record_anchors:
            expected_source_sha = str(anchor.get("source_sha256") or "")
            expected_excerpt_sha = str(anchor.get("excerpt_sha256") or "")
            if expected_source_sha and expected_source_sha != record.source_sha256:
                diagnostics.append(
                    diagnostic(
                        case_id=str(case.get("case_id")),
                        case_class="evidence-present",
                        severity="error",
                        rule="evidence_anchor_hash_mismatch",
                        artifact_path=display_path(source_blocks_path, root=root),
                        record_id=record_id,
                        record_kind="source_block",
                        source_path=record.source_path,
                        expected_state="source_sha256-matches-anchor",
                        actual_state="source_sha256-mismatch",
                        message="Evidence source_sha256 drifted from the golden anchor.",
                    )
                )
            if expected_excerpt_sha and expected_excerpt_sha != record.excerpt_sha256:
                diagnostics.append(
                    diagnostic(
                        case_id=str(case.get("case_id")),
                        case_class="evidence-present",
                        severity="error",
                        rule="evidence_anchor_hash_mismatch",
                        artifact_path=display_path(source_blocks_path, root=root),
                        record_id=record_id,
                        record_kind="source_block",
                        source_path=record.source_path,
                        expected_state="excerpt_sha256-matches-anchor",
                        actual_state="excerpt_sha256-mismatch",
                        message="Evidence excerpt_sha256 drifted from the golden anchor.",
                    )
                )
    return diagnostics


def evaluate_no_answer(
    case: dict[str, Any], *, source_artifacts: dict[str, Any], parser_dir: Path, root: Path
) -> list[dict[str, Any]]:
    """Verify the intentionally absent target remains absent and anchor-free."""

    diagnostics: list[dict[str, Any]] = []
    expected_value = case.get("expected")
    expected = cast(dict[str, Any], expected_value) if isinstance(expected_value, dict) else {}
    target_id = str(expected.get("missing_target_id") or "")
    inspected_paths = expected.get("inspected_artifact_paths")
    artifact_path = (
        inspected_paths[-1]
        if isinstance(inspected_paths, list) and inspected_paths
        else display_path(parser_dir, root=root)
    )
    anchors = case.get("anchors")
    actual_state = (
        "no-answer"
        if target_id and target_id not in source_artifacts["record_ids"] and anchors == []
        else "matched"
    )
    if actual_state != "no-answer":
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="no-answer",
                severity="error",
                rule="no_answer_target_matched",
                artifact_path=str(artifact_path),
                record_id=target_id or None,
                record_kind="result",
                expected_state="no-answer",
                actual_state=actual_state,
                message="Golden no-answer target must remain absent from parser records and have no anchors.",
            )
        )
    else:
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="no-answer",
                severity="info",
                rule="intentionally_absent_target",
                artifact_path=str(artifact_path),
                record_id=target_id,
                record_kind="result",
                expected_state="no-answer",
                actual_state="no-answer",
                message="Golden no-answer target is intentionally absent from tracked parser artifacts.",
            )
        )
    return diagnostics


def evaluate_candidate_only(
    case: dict[str, Any],
    *,
    relations: list[RelationCandidateRecord],
    staging_graph: dict[str, Any],
    relations_path: Path,
    staging_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Verify relation records remain candidate-only and keyed in staging."""

    diagnostics: list[dict[str, Any]] = []
    by_id = {record.id: record for record in relations}
    expected_value = case.get("expected")
    expected = cast(dict[str, Any], expected_value) if isinstance(expected_value, dict) else {}
    required_status = str(expected.get("required_relation_status") or "candidate")
    edge_key = str(expected.get("required_staging_edge_key") or "")
    keyed_edges = staging_graph.get("keyed_relation_edges")
    keyed_edge_set = (
        set(str(edge) for edge in keyed_edges) if isinstance(keyed_edges, list) else set()
    )
    for record_id in expected_list(case, "required_record_ids"):
        record = by_id.get(record_id)
        if record is None:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="candidate-only",
                    severity="error",
                    rule="candidate_relation_missing",
                    artifact_path=display_path(relations_path, root=root),
                    record_id=record_id,
                    record_kind="relation_candidate",
                    expected_state="candidate-only",
                    actual_state="missing",
                    message="Required candidate-only relation record is absent.",
                )
            )
        elif record.status != required_status:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="candidate-only",
                    severity="error",
                    rule="candidate_relation_not_candidate",
                    artifact_path=display_path(relations_path, root=root),
                    record_id=record_id,
                    record_kind="relation_candidate",
                    source_path=record.source_path,
                    expected_state="candidate-only",
                    actual_state=record.status,
                    message="Relation record must remain status:candidate, not a promoted relation claim.",
                )
            )
    if edge_key not in keyed_edge_set:
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="candidate-only",
                severity="error",
                rule="candidate_staging_edge_missing",
                artifact_path=display_path(staging_path, root=root),
                record_id=edge_key or None,
                record_kind="relation_candidate",
                expected_state="keyed-candidate-edge",
                actual_state="missing",
                message="Required candidate relation key is absent from parser staging graph.",
            )
        )
    return diagnostics


def evaluate_unresolved_reference(
    case: dict[str, Any], *, staging_graph: dict[str, Any], staging_path: Path, root: Path
) -> list[dict[str, Any]]:
    """Verify unresolved reference ids exactly match the staging graph ids."""

    diagnostics: list[dict[str, Any]] = []
    expected_ids = set(expected_list(case, "required_reference_ids"))
    raw_actual = staging_graph.get("unresolved_reference_ids")
    actual_ids = set(str(item) for item in raw_actual) if isinstance(raw_actual, list) else set()
    missing = expected_ids - actual_ids
    unexpected = actual_ids - expected_ids
    for record_id in sorted(missing):
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="unresolved-reference",
                severity="error",
                rule="unresolved_reference_missing",
                artifact_path=display_path(staging_path, root=root),
                record_id=record_id,
                record_kind="unresolved_reference",
                expected_state="unresolved-reference",
                actual_state="missing",
                message="Expected unresolved reference id is absent from parser staging graph.",
            )
        )
    for record_id in sorted(unexpected):
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="unresolved-reference",
                severity="error",
                rule="unresolved_reference_unexpected",
                artifact_path=display_path(staging_path, root=root),
                record_id=record_id,
                record_kind="unresolved_reference",
                expected_state="only-golden-unresolved-reference-ids",
                actual_state="unexpected",
                message="Parser staging graph contains an unresolved reference id outside the golden contract.",
            )
        )
    if not missing and not unexpected:
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="unresolved-reference",
                severity="warning",
                rule="unresolved_references_preserved",
                artifact_path=display_path(staging_path, root=root),
                expected_state="unresolved-reference",
                actual_state="unresolved-reference",
                message="Golden unresolved reference ids match parser staging graph unresolved ids.",
            )
        )
    return diagnostics


def evaluate_non_authoritative(
    case: dict[str, Any],
    *,
    golden_report: dict[str, Any],
    source_artifacts: dict[str, Any],
    golden_path: Path,
    root: Path,
) -> list[dict[str, Any]]:
    """Verify blocked claims and non-claim fragments remain present."""

    diagnostics: list[dict[str, Any]] = []
    expected_value = case.get("expected")
    expected = cast(dict[str, Any], expected_value) if isinstance(expected_value, dict) else {}
    required_claims = set(
        str(item) for item in expected.get("blocked_claims", []) if isinstance(item, str)
    )
    actual_claims = set(
        str(item) for item in golden_report.get("blocked_claims", []) if isinstance(item, str)
    )
    missing_claims = required_claims - actual_claims
    non_claims: list[str] = []
    for record in [
        *source_artifacts["documents"],
        *source_artifacts["source_blocks"],
        *source_artifacts["relations"],
    ]:
        non_claims.extend(record.non_claims)
    staging_non_claims = source_artifacts["staging_graph"].get("non_claims")
    if isinstance(staging_non_claims, list):
        non_claims.extend(str(item) for item in staging_non_claims if isinstance(item, str))
    for golden_case in golden_report.get("cases", []):
        if isinstance(golden_case, dict) and isinstance(golden_case.get("non_claims"), list):
            non_claims.extend(
                str(item) for item in golden_case["non_claims"] if isinstance(item, str)
            )
    non_claim_text = "\n".join([*non_claims, *actual_claims]).casefold()
    for claim in sorted(missing_claims):
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="non-authoritative",
                severity="error",
                rule="blocked_claim_missing",
                artifact_path=display_path(golden_path, root=root),
                record_id="blocked-claims",
                record_kind="result",
                expected_state="blocked-claim-present",
                actual_state="missing",
                message=f"Required blocked-claim label is absent: {claim}",
            )
        )
    for fragment in expected_list(case, "required_non_claim_fragments"):
        if fragment.casefold() not in non_claim_text:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="non-authoritative",
                    severity="error",
                    rule="non_claim_fragment_missing",
                    artifact_path=display_path(golden_path, root=root),
                    record_id="non-claims",
                    record_kind="result",
                    expected_state="non-claim-fragment-present",
                    actual_state="missing",
                    message=f"Required non-claim fragment is absent: {fragment}",
                )
            )
    if not missing_claims:
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="non-authoritative",
                severity="info",
                rule="claims_blocked",
                artifact_path=display_path(golden_path, root=root),
                record_id="blocked-claims",
                record_kind="result",
                expected_state="non-authoritative-boundary",
                actual_state="non-authoritative-boundary",
                message="Golden cases preserve parser/retrieval/legal-answer blocked-claim labels.",
            )
        )
    return diagnostics


def evaluate_cases(
    golden_report: dict[str, Any],
    golden_path: Path,
    parser_dir: Path,
    *,
    source_artifact_filenames: dict[str, str],
    required_case_classes: set[str],
    golden_cases_schema_version: str,
    schema_version: str,
    generated_by: str,
    root: Path,
) -> dict[str, Any]:
    """Evaluate the golden cases and return the stdout JSON contract."""

    source_artifacts, diagnostics = load_evaluation_source_artifacts(
        parser_dir, source_artifact_filenames=source_artifact_filenames, root=root
    )
    cases_by_class, case_mapping_diagnostics = require_case_mapping(
        golden_report,
        golden_path=golden_path,
        required_case_classes=required_case_classes,
        root=root,
    )
    diagnostics.extend(case_mapping_diagnostics)

    source_blocks_path = parser_dir / source_artifact_filenames["source_blocks"]
    relations_path = parser_dir / source_artifact_filenames["relations"]
    staging_path = parser_dir / source_artifact_filenames["staging_graph"]

    if "evidence-present" in cases_by_class:
        diagnostics.extend(
            evaluate_evidence_present(
                cases_by_class["evidence-present"],
                source_blocks=source_artifacts["source_blocks"],
                source_blocks_path=source_blocks_path,
                root=root,
            )
        )
    if "no-answer" in cases_by_class:
        diagnostics.extend(
            evaluate_no_answer(
                cases_by_class["no-answer"],
                source_artifacts=source_artifacts,
                parser_dir=parser_dir,
                root=root,
            )
        )
    if "candidate-only" in cases_by_class:
        diagnostics.extend(
            evaluate_candidate_only(
                cases_by_class["candidate-only"],
                relations=source_artifacts["relations"],
                staging_graph=source_artifacts["staging_graph"],
                relations_path=relations_path,
                staging_path=staging_path,
                root=root,
            )
        )
    if "unresolved-reference" in cases_by_class:
        diagnostics.extend(
            evaluate_unresolved_reference(
                cases_by_class["unresolved-reference"],
                staging_graph=source_artifacts["staging_graph"],
                staging_path=staging_path,
                root=root,
            )
        )
    if "non-authoritative" in cases_by_class:
        diagnostics.extend(
            evaluate_non_authoritative(
                cases_by_class["non-authoritative"],
                golden_report=golden_report,
                source_artifacts=source_artifacts,
                golden_path=golden_path,
                root=root,
            )
        )

    counts = evaluation_severity_counts(diagnostics)
    sorted_diagnostics = sort_evaluation_diagnostics(diagnostics)
    return {
        "schema_version": schema_version,
        "generated_by": generated_by,
        "status": "fail" if counts["error"] else "pass",
        "non_authoritative": golden_report.get("non_authoritative") is True,
        "blocked_claims": sorted(
            str(item) for item in golden_report.get("blocked_claims", []) if isinstance(item, str)
        ),
        "case_count": len(golden_report.get("cases", []))
        if isinstance(golden_report.get("cases"), list)
        else 0,
        "evaluated_case_count": len(cases_by_class),
        "case_class_counts": {case_class: 1 for case_class in sorted(cases_by_class)},
        "severity_counts": counts,
        "error_count": counts["error"],
        "warning_count": counts["warning"],
        "info_count": counts["info"],
        "diagnostics": sorted_diagnostics,
    }


def build_evaluation_result(
    *,
    golden_cases_path: Path,
    parser_dir: Path,
    source_artifact_filenames: dict[str, str],
    required_case_classes: set[str],
    golden_cases_schema_version: str,
    schema_version: str,
    generated_by: str,
    root: Path,
) -> dict[str, Any]:
    """Build the evaluator result for CLI and tests."""

    golden_report, diagnostics = load_golden_cases_report(
        golden_cases_path, golden_cases_schema_version=golden_cases_schema_version, root=root
    )
    if diagnostics:
        counts = evaluation_severity_counts(diagnostics)
        return {
            "schema_version": schema_version,
            "generated_by": generated_by,
            "status": "fail",
            "non_authoritative": False,
            "blocked_claims": [],
            "case_count": 0,
            "evaluated_case_count": 0,
            "case_class_counts": {},
            "severity_counts": counts,
            "error_count": counts["error"],
            "warning_count": counts["warning"],
            "info_count": counts["info"],
            "diagnostics": sort_evaluation_diagnostics(diagnostics),
        }
    return evaluate_cases(
        golden_report,
        golden_cases_path,
        parser_dir,
        source_artifact_filenames=source_artifact_filenames,
        required_case_classes=required_case_classes,
        golden_cases_schema_version=golden_cases_schema_version,
        schema_version=schema_version,
        generated_by=generated_by,
        root=root,
    )
