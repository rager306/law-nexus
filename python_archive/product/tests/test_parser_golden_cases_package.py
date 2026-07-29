from __future__ import annotations

import json
from pathlib import Path

from law_nexus.adapters.sources.parser_golden_cases import (
    build_cases,
    build_evaluation_result,
    diagnostic,
    display_path,
    load_json_object,
    severity_counts,
    sha256_file,
    sort_diagnostics,
)
from law_nexus.adapters.sources.parser_records import load_jsonl_records

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_RECORDS_PATH = ROOT / "prd/parser/odt_document_records.jsonl"
SOURCE_BLOCK_RECORDS_PATH = ROOT / "prd/parser/odt_source_block_records.jsonl"
RELATION_CANDIDATES_PATH = ROOT / "prd/parser/consultant_relation_candidates.jsonl"
STAGING_GRAPH_PATH = ROOT / "prd/parser/parser_staging_graph.json"
GOLDEN_CASES_PATH = ROOT / "prd/parser/golden_cases.json"
REQUIRED_CASE_CLASSES = [
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
]
BLOCKED_CLAIMS = [
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness",
]


def test_display_path_prefers_repo_relative_path(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    nested = root / "prd" / "parser" / "golden_cases.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")

    assert display_path(nested, root=root) == "prd/parser/golden_cases.json"


def test_diagnostic_preserves_extra_fields_and_non_claim_default() -> None:
    item = diagnostic(
        case_id="CASE-1",
        case_class="evidence-present",
        severity="warning",
        rule="bounded",
        artifact_path="prd/parser/golden_cases.json",
        message="Bounded diagnostic.",
        field="source_id",
    )

    assert item["non_authoritative"] is True
    assert item["field"] == "source_id"
    assert item["expected_state"] is None
    assert item["actual_state"] is None


def test_load_json_object_reports_missing_and_invalid_shapes(tmp_path: Path) -> None:
    missing_payload, missing_diags = load_json_object(tmp_path / "missing.json", root=tmp_path)
    assert missing_payload is None
    assert missing_diags[0]["rule"] == "missing_source_artifact"

    list_path = tmp_path / "list.json"
    list_path.write_text("[]", encoding="utf-8")
    list_payload, list_diags = load_json_object(list_path, root=tmp_path)
    assert list_payload is None
    assert list_diags[0]["rule"] == "invalid_json_shape"

    object_path = tmp_path / "object.json"
    object_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    object_payload, object_diags = load_json_object(object_path, root=tmp_path)
    assert object_payload == {"ok": True}
    assert object_diags == []


def test_sha256_sort_and_severity_helpers_are_stable(tmp_path: Path) -> None:
    payload = tmp_path / "payload.txt"
    payload.write_text("abc", encoding="utf-8")
    assert (
        sha256_file(payload) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )

    diagnostics = [
        diagnostic(
            case_id="B",
            case_class=None,
            severity="info",
            rule="z",
            artifact_path="b",
            message="b",
        ),
        diagnostic(
            case_id="A",
            case_class=None,
            severity="error",
            rule="a",
            artifact_path="a",
            message="a",
        ),
    ]

    assert [item["case_id"] for item in sort_diagnostics(diagnostics)] == ["A", "B"]
    assert severity_counts(diagnostics) == {"error": 1, "info": 1}


def test_build_cases_core_uses_tracked_parser_artifacts_without_parser_completeness_claim() -> None:
    documents, document_diagnostics = load_jsonl_records(DOCUMENT_RECORDS_PATH)
    source_blocks, source_block_diagnostics = load_jsonl_records(SOURCE_BLOCK_RECORDS_PATH)
    relation_candidates, relation_diagnostics = load_jsonl_records(RELATION_CANDIDATES_PATH)
    assert document_diagnostics == []
    assert source_block_diagnostics == []
    assert relation_diagnostics == []

    cases, diagnostics = build_cases(
        {
            "documents": documents,
            "source_blocks": source_blocks,
            "relation_candidates": relation_candidates,
            "staging_graph": json.loads(STAGING_GRAPH_PATH.read_text(encoding="utf-8")),
        },
        contract_path=ROOT / "prd/parser/golden_test_contract.md",
        document_records_path=DOCUMENT_RECORDS_PATH,
        source_block_records_path=SOURCE_BLOCK_RECORDS_PATH,
        relation_candidates_path=RELATION_CANDIDATES_PATH,
        staging_graph_path=STAGING_GRAPH_PATH,
        required_case_classes=REQUIRED_CASE_CLASSES,
        blocked_claims=BLOCKED_CLAIMS,
        root=ROOT,
    )

    assert {case["case_class"] for case in cases} == set(REQUIRED_CASE_CLASSES)
    assert len(cases) == 5
    assert diagnostics == []
    assert all(case["non_authoritative"] is True for case in cases)
    assert any("parser completeness" in json.dumps(case) for case in cases)
    assert all("parser completeness validated" not in json.dumps(case) for case in cases)


def test_build_evaluation_result_core_preserves_warning_status_and_non_claims() -> None:
    result = build_evaluation_result(
        golden_cases_path=GOLDEN_CASES_PATH,
        parser_dir=ROOT / "prd/parser",
        source_artifact_filenames={
            "documents": "odt_document_records.jsonl",
            "source_blocks": "odt_source_block_records.jsonl",
            "relations": "consultant_relation_candidates.jsonl",
            "staging_graph": "parser_staging_graph.json",
        },
        required_case_classes=set(REQUIRED_CASE_CLASSES),
        golden_cases_schema_version="legalgraph-parser-golden-cases/v1",
        schema_version="legalgraph-parser-golden-evaluator/v1",
        generated_by="scripts/evaluate-parser-golden-cases.py",
        root=ROOT,
    )

    assert result["schema_version"] == "legalgraph-parser-golden-evaluator/v1"
    assert result["status"] == "pass"
    assert result["case_count"] == 5
    assert result["evaluated_case_count"] == 5
    assert result["error_count"] == 0
    assert result["warning_count"] >= 1
    assert "parser completeness" in result["blocked_claims"]
