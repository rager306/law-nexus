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
from typing import Any

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


def load_json_object(path: Path, *, root: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
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


def source_artifact_inventory_core(source_artifact_paths: list[Path], *, root: Path) -> list[dict[str, Any]]:
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
                "anchors": [make_anchor_core(preferred_block, source_block_records_path, root=root)],
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
                artifact_path=display_path(source_block_records_path, root=root),
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
                "source_artifacts": [display_path(relation_candidates_path, root=root), display_path(staging_graph_path, root=root)],
                "anchors": [make_anchor_core(relation, relation_candidates_path, root=root)],
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
                            message=str(item.get("message") or "Unresolved reference remains explicit."),
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
        | {claim for claim in staging_graph.get("non_claims", []) if isinstance(claim, str) and claim.strip()}
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
                        "source_sha256": sha256_file(contract_path) if contract_path.exists() else None,
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
