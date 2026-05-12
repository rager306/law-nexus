#!/usr/bin/env python3
# ruff: noqa: E402
"""Evaluate parser golden cases against tracked parser artifacts.

The evaluator is deterministic and local-only: it reads bounded artifacts under
``prd/parser`` and never rescans raw legal sources, calls FalkorDB, invokes an
LLM, or claims parser/retrieval/legal-answer readiness.
"""

from __future__ import annotations

import argparse
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

SCHEMA_VERSION = "legalgraph-parser-golden-evaluator/v1"
GENERATED_BY = "scripts/evaluate-parser-golden-cases.py"
GOLDEN_CASES_SCHEMA_VERSION = "legalgraph-parser-golden-cases/v1"
DEFAULT_PARSER_DIR = ROOT / "prd/parser"
REQUIRED_CASE_CLASSES = {
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
}
SOURCE_ARTIFACT_FILENAMES = {
    "documents": "odt_document_records.jsonl",
    "source_blocks": "odt_source_block_records.jsonl",
    "relations": "consultant_relation_candidates.jsonl",
    "staging_graph": "parser_staging_graph.json",
}


def display_path(path: Path) -> str:
    """Return a stable repository-relative path when possible."""

    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def diagnostic(
    *,
    case_id: str | None,
    case_class: str | None,
    severity: str,
    rule: str,
    artifact_path: str,
    expected_state: str | None,
    actual_state: str | None,
    message: str,
    record_id: str | None = None,
    record_kind: str | None = None,
    source_path: str | None = None,
    non_authoritative: bool = True,
    **extra: Any,
) -> dict[str, Any]:
    """Create the compact path-qualified diagnostic contract for stdout."""

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


def sort_diagnostics(diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def severity_counts(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    """Return deterministic severity counts with explicit zeroes."""

    counts = {"error": 0, "warning": 0, "info": 0}
    for item in diagnostics:
        severity = str(item.get("severity") or "")
        if severity in counts:
            counts[severity] += 1
    return counts


def load_json_object(path: Path, *, artifact_label: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load a JSON object with fail-closed diagnostics."""

    if not path.exists():
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path),
                expected_state="readable-json-object",
                actual_state="missing",
                message=f"Required {artifact_label} artifact is missing.",
            )
        ]
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="json_invalid",
                artifact_path=display_path(path),
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
                artifact_path=display_path(path),
                expected_state="object",
                actual_state=type(loaded).__name__,
                message=f"{artifact_label} artifact must decode to a JSON object.",
            )
        ]
    return loaded, []


def convert_loader_diagnostics(
    loader_diagnostics: list[dict[str, Any]], *, artifact_path: Path
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
                artifact_path=str(item.get("file") or display_path(artifact_path)),
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


def load_records(path: Path) -> tuple[list[Any], list[dict[str, Any]]]:
    """Load one parser JSONL artifact using the shared parser record contracts."""

    if not path.exists():
        return [], [
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="missing_source_artifact",
                artifact_path=display_path(path),
                expected_state="readable-jsonl-parser-records",
                actual_state="missing",
                message="Required parser JSONL artifact is missing.",
            )
        ]
    records, loader_diagnostics = load_jsonl_records(path)
    return records, convert_loader_diagnostics(loader_diagnostics, artifact_path=path)


def load_source_artifacts(parser_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load all bounded parser artifacts consumed by the evaluator."""

    diagnostics: list[dict[str, Any]] = []
    documents_raw, document_diagnostics = load_records(parser_dir / SOURCE_ARTIFACT_FILENAMES["documents"])
    source_blocks_raw, source_block_diagnostics = load_records(parser_dir / SOURCE_ARTIFACT_FILENAMES["source_blocks"])
    relations_raw, relation_diagnostics = load_records(parser_dir / SOURCE_ARTIFACT_FILENAMES["relations"])
    diagnostics.extend(document_diagnostics)
    diagnostics.extend(source_block_diagnostics)
    diagnostics.extend(relation_diagnostics)

    staging_graph, staging_diagnostics = load_json_object(
        parser_dir / SOURCE_ARTIFACT_FILENAMES["staging_graph"], artifact_label="parser staging graph"
    )
    diagnostics.extend(staging_diagnostics)

    documents = [record for record in documents_raw if isinstance(record, DocumentRecord)]
    source_blocks = [record for record in source_blocks_raw if isinstance(record, SourceBlockRecord)]
    relations = [record for record in relations_raw if isinstance(record, RelationCandidateRecord)]
    record_ids = {record.id for record in [*documents, *source_blocks, *relations]}
    return {
        "documents": documents,
        "source_blocks": source_blocks,
        "relations": relations,
        "staging_graph": staging_graph,
        "record_ids": record_ids,
    }, diagnostics


def load_golden_cases(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load and minimally validate the golden-case report artifact."""

    report, diagnostics = load_json_object(path, artifact_label="golden cases")
    if diagnostics:
        return report, diagnostics
    if report.get("schema_version") != GOLDEN_CASES_SCHEMA_VERSION:
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=None,
                severity="error",
                rule="unsupported_golden_cases_schema",
                artifact_path=display_path(path),
                expected_state=GOLDEN_CASES_SCHEMA_VERSION,
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
                artifact_path=display_path(path),
                expected_state="cases-list",
                actual_state=type(cases).__name__,
                message="golden_cases.json must contain a cases array.",
            )
        )
    return report, diagnostics


def require_case_mapping(
    golden_report: dict[str, Any], *, golden_path: Path
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
                    artifact_path=display_path(golden_path),
                    expected_state="case-object",
                    actual_state=type(case).__name__,
                    message="Each golden case must be a JSON object.",
                )
            )
            continue
        case_id = str(case.get("case_id") or "") or None
        case_class = str(case.get("case_class") or "") or None
        if case_class not in REQUIRED_CASE_CLASSES:
            diagnostics.append(
                diagnostic(
                    case_id=case_id,
                    case_class=case_class,
                    severity="error",
                    rule="unsupported_case_class",
                    artifact_path=display_path(golden_path),
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
                    artifact_path=display_path(golden_path),
                    expected_state="one-case-per-required-class",
                    actual_state="duplicate",
                    message="Golden cases must contain at most one case for each required class.",
                )
            )
            continue
        cases_by_class[case_class] = case

    for required in sorted(REQUIRED_CASE_CLASSES - set(cases_by_class)):
        diagnostics.append(
            diagnostic(
                case_id=None,
                case_class=required,
                severity="error",
                rule="required_case_class_missing",
                artifact_path=display_path(golden_path),
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


def case_expected_state(case: dict[str, Any]) -> str | None:
    """Return the case expected answer_state if present."""

    expected = case.get("expected")
    value = expected.get("answer_state") if isinstance(expected, dict) else None
    return str(value) if value is not None else None


def evaluate_evidence_present(
    case: dict[str, Any], *, source_blocks: list[SourceBlockRecord], source_blocks_path: Path
) -> list[dict[str, Any]]:
    """Verify all required evidence record ids remain present."""

    diagnostics: list[dict[str, Any]] = []
    ids = {record.id for record in source_blocks}
    for record_id in expected_list(case, "required_record_ids"):
        if record_id not in ids:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="evidence-present",
                    severity="error",
                    rule="required_evidence_missing",
                    artifact_path=display_path(source_blocks_path),
                    record_id=record_id,
                    record_kind="source_block",
                    expected_state="evidence-present",
                    actual_state="missing",
                    message="Required evidence source-block id is absent from parser records.",
                )
            )
    return diagnostics


def evaluate_no_answer(
    case: dict[str, Any], *, source_artifacts: dict[str, Any], parser_dir: Path
) -> list[dict[str, Any]]:
    """Verify the intentionally absent target remains absent and anchor-free."""

    diagnostics: list[dict[str, Any]] = []
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    target_id = str(expected.get("missing_target_id") or "")
    inspected_paths = expected.get("inspected_artifact_paths")
    artifact_path = inspected_paths[-1] if isinstance(inspected_paths, list) and inspected_paths else display_path(parser_dir)
    anchors = case.get("anchors")
    actual_state = "no-answer" if target_id and target_id not in source_artifacts["record_ids"] and anchors == [] else "matched"
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
    case: dict[str, Any], *, relations: list[RelationCandidateRecord], staging_graph: dict[str, Any], relations_path: Path, staging_path: Path
) -> list[dict[str, Any]]:
    """Verify relation records remain candidate-only and keyed in staging."""

    diagnostics: list[dict[str, Any]] = []
    by_id = {record.id: record for record in relations}
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    required_status = str(expected.get("required_relation_status") or "candidate")
    edge_key = str(expected.get("required_staging_edge_key") or "")
    keyed_edges = staging_graph.get("keyed_relation_edges")
    keyed_edge_set = set(str(edge) for edge in keyed_edges) if isinstance(keyed_edges, list) else set()
    for record_id in expected_list(case, "required_record_ids"):
        record = by_id.get(record_id)
        if record is None:
            diagnostics.append(
                diagnostic(
                    case_id=str(case.get("case_id")),
                    case_class="candidate-only",
                    severity="error",
                    rule="candidate_relation_missing",
                    artifact_path=display_path(relations_path),
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
                    artifact_path=display_path(relations_path),
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
                artifact_path=display_path(staging_path),
                record_id=edge_key or None,
                record_kind="relation_candidate",
                expected_state="keyed-candidate-edge",
                actual_state="missing",
                message="Required candidate relation key is absent from parser staging graph.",
            )
        )
    return diagnostics


def evaluate_unresolved_reference(
    case: dict[str, Any], *, staging_graph: dict[str, Any], staging_path: Path
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
                artifact_path=display_path(staging_path),
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
                artifact_path=display_path(staging_path),
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
                artifact_path=display_path(staging_path),
                expected_state="unresolved-reference",
                actual_state="unresolved-reference",
                message="Golden unresolved reference ids match parser staging graph unresolved ids.",
            )
        )
    return diagnostics


def evaluate_non_authoritative(
    case: dict[str, Any], *, golden_report: dict[str, Any], source_artifacts: dict[str, Any], golden_path: Path
) -> list[dict[str, Any]]:
    """Verify blocked claims and non-claim fragments remain present."""

    diagnostics: list[dict[str, Any]] = []
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    required_claims = set(str(item) for item in expected.get("blocked_claims", []) if isinstance(item, str))
    actual_claims = set(str(item) for item in golden_report.get("blocked_claims", []) if isinstance(item, str))
    missing_claims = required_claims - actual_claims
    non_claims: list[str] = []
    for record in [*source_artifacts["documents"], *source_artifacts["source_blocks"], *source_artifacts["relations"]]:
        non_claims.extend(record.non_claims)
    staging_non_claims = source_artifacts["staging_graph"].get("non_claims")
    if isinstance(staging_non_claims, list):
        non_claims.extend(str(item) for item in staging_non_claims if isinstance(item, str))
    for golden_case in golden_report.get("cases", []):
        if isinstance(golden_case, dict) and isinstance(golden_case.get("non_claims"), list):
            non_claims.extend(str(item) for item in golden_case["non_claims"] if isinstance(item, str))
    non_claim_text = "\n".join([*non_claims, *actual_claims]).casefold()
    for claim in sorted(missing_claims):
        diagnostics.append(
            diagnostic(
                case_id=str(case.get("case_id")),
                case_class="non-authoritative",
                severity="error",
                rule="blocked_claim_missing",
                artifact_path=display_path(golden_path),
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
                    artifact_path=display_path(golden_path),
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
                artifact_path=display_path(golden_path),
                record_id="blocked-claims",
                record_kind="result",
                expected_state="non-authoritative-boundary",
                actual_state="non-authoritative-boundary",
                message="Golden cases preserve parser/retrieval/legal-answer blocked-claim labels.",
            )
        )
    return diagnostics


def evaluate_cases(golden_report: dict[str, Any], golden_path: Path, parser_dir: Path) -> dict[str, Any]:
    """Evaluate the golden cases and return the stdout JSON contract."""

    source_artifacts, diagnostics = load_source_artifacts(parser_dir)
    cases_by_class, case_mapping_diagnostics = require_case_mapping(golden_report, golden_path=golden_path)
    diagnostics.extend(case_mapping_diagnostics)

    source_blocks_path = parser_dir / SOURCE_ARTIFACT_FILENAMES["source_blocks"]
    relations_path = parser_dir / SOURCE_ARTIFACT_FILENAMES["relations"]
    staging_path = parser_dir / SOURCE_ARTIFACT_FILENAMES["staging_graph"]

    if "evidence-present" in cases_by_class:
        diagnostics.extend(
            evaluate_evidence_present(
                cases_by_class["evidence-present"],
                source_blocks=source_artifacts["source_blocks"],
                source_blocks_path=source_blocks_path,
            )
        )
    if "no-answer" in cases_by_class:
        diagnostics.extend(evaluate_no_answer(cases_by_class["no-answer"], source_artifacts=source_artifacts, parser_dir=parser_dir))
    if "candidate-only" in cases_by_class:
        diagnostics.extend(
            evaluate_candidate_only(
                cases_by_class["candidate-only"],
                relations=source_artifacts["relations"],
                staging_graph=source_artifacts["staging_graph"],
                relations_path=relations_path,
                staging_path=staging_path,
            )
        )
    if "unresolved-reference" in cases_by_class:
        diagnostics.extend(
            evaluate_unresolved_reference(
                cases_by_class["unresolved-reference"],
                staging_graph=source_artifacts["staging_graph"],
                staging_path=staging_path,
            )
        )
    if "non-authoritative" in cases_by_class:
        diagnostics.extend(
            evaluate_non_authoritative(
                cases_by_class["non-authoritative"],
                golden_report=golden_report,
                source_artifacts=source_artifacts,
                golden_path=golden_path,
            )
        )

    counts = severity_counts(diagnostics)
    sorted_diagnostics = sort_diagnostics(diagnostics)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "status": "fail" if counts["error"] else "pass",
        "non_authoritative": golden_report.get("non_authoritative") is True,
        "blocked_claims": sorted(str(item) for item in golden_report.get("blocked_claims", []) if isinstance(item, str)),
        "case_count": len(golden_report.get("cases", [])) if isinstance(golden_report.get("cases"), list) else 0,
        "evaluated_case_count": len(cases_by_class),
        "case_class_counts": {case_class: 1 for case_class in sorted(cases_by_class)},
        "severity_counts": counts,
        "error_count": counts["error"],
        "warning_count": counts["warning"],
        "info_count": counts["info"],
        "diagnostics": sorted_diagnostics,
    }


def build_result(*, golden_cases_path: Path, parser_dir: Path) -> dict[str, Any]:
    """Build the evaluator result for CLI and tests."""

    golden_report, diagnostics = load_golden_cases(golden_cases_path)
    if diagnostics:
        counts = severity_counts(diagnostics)
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_by": GENERATED_BY,
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
            "diagnostics": sort_diagnostics(diagnostics),
        }
    return evaluate_cases(golden_report, golden_cases_path, parser_dir)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the evaluator CLI."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True, help="Evaluate tracked golden cases and exit non-zero on errors.")
    parser.add_argument(
        "--parser-dir",
        type=Path,
        default=DEFAULT_PARSER_DIR,
        help="Directory containing parser artifacts; defaults to prd/parser.",
    )
    parser.add_argument(
        "--golden-cases",
        type=Path,
        default=None,
        help="Path to golden_cases.json; defaults to <parser-dir>/golden_cases.json.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    parser_dir = args.parser_dir
    golden_cases_path = args.golden_cases or parser_dir / "golden_cases.json"
    result = build_result(golden_cases_path=golden_cases_path, parser_dir=parser_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
