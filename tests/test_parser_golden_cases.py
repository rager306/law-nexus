from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/build-parser-golden-cases.py"
PARSER_DIR = ROOT / "prd/parser"

REQUIRED_CASE_CLASSES = {
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
}
ALLOWED_ANSWER_STATES = REQUIRED_CASE_CLASSES | {"non-authoritative-boundary"}
BLOCKED_CLAIM_FRAGMENTS = [
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


def load_module():
    spec = importlib.util.spec_from_file_location("build_parser_golden_cases", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_parser_golden_cases"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def case_by_class(report: dict[str, Any], case_class: str) -> dict[str, Any]:
    matches = [case for case in report["cases"] if case["case_class"] == case_class]
    assert len(matches) == 1
    return matches[0]


def patch_source_paths(module: Any, monkeypatch: pytest.MonkeyPatch, parser_dir: Path) -> None:
    contract = parser_dir / "golden_test_contract.md"
    documents = parser_dir / "odt_document_records.jsonl"
    source_blocks = parser_dir / "odt_source_block_records.jsonl"
    relations = parser_dir / "consultant_relation_candidates.jsonl"
    staging = parser_dir / "parser_staging_graph.json"
    monkeypatch.setattr(module, "CONTRACT_PATH", contract)
    monkeypatch.setattr(module, "DOCUMENT_RECORDS_PATH", documents)
    monkeypatch.setattr(module, "SOURCE_BLOCK_RECORDS_PATH", source_blocks)
    monkeypatch.setattr(module, "RELATION_CANDIDATES_PATH", relations)
    monkeypatch.setattr(module, "STAGING_GRAPH_PATH", staging)
    monkeypatch.setattr(module, "SOURCE_ARTIFACT_PATHS", [contract, documents, source_blocks, relations, staging])


def copy_source_fixtures(tmp_path: Path, module: Any, monkeypatch: pytest.MonkeyPatch) -> Path:
    parser_dir = tmp_path / "prd/parser"
    parser_dir.mkdir(parents=True)
    for name in [
        "golden_test_contract.md",
        "odt_document_records.jsonl",
        "odt_source_block_records.jsonl",
        "consultant_relation_candidates.jsonl",
        "parser_staging_graph.json",
    ]:
        (parser_dir / name).write_text((PARSER_DIR / name).read_text(encoding="utf-8"), encoding="utf-8")
    patch_source_paths(module, monkeypatch, parser_dir)
    return parser_dir


def diagnostics_by_rule(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for diagnostic in report["diagnostics"]:
        grouped.setdefault(diagnostic["rule"], []).append(diagnostic)
    return grouped


def test_real_tracked_check_succeeds_with_expected_counts_and_sources() -> None:
    result = run_cli("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    report = parse_stdout_json(result)
    assert report["status"] == "pass"
    assert report["artifact_freshness"]["status"] == "pass"
    assert report["artifact_freshness"]["stale_paths"] == []
    assert report["case_count"] == 5
    assert report["case_class_counts"] == {case_class: 1 for case_class in sorted(REQUIRED_CASE_CLASSES)}
    assert [artifact["path"] for artifact in report["source_artifacts"]] == [
        "prd/parser/golden_test_contract.md",
        "prd/parser/odt_document_records.jsonl",
        "prd/parser/odt_source_block_records.jsonl",
        "prd/parser/consultant_relation_candidates.jsonl",
        "prd/parser/parser_staging_graph.json",
    ]
    assert {diagnostic["rule"] for diagnostic in report["diagnostics"]} >= {
        "intentionally_absent_target",
        "unresolved_subject_ref",
        "unresolved_object_ref",
        "claims_blocked",
    }


def test_json_artifact_shape_is_closed_bounded_and_non_authoritative() -> None:
    report = read_json(PARSER_DIR / "golden_cases.json")

    assert report["schema_version"] == "legalgraph-parser-golden-cases/v1"
    assert report["generated_by"] == "scripts/build-parser-golden-cases.py"
    assert report["status"] == "pass"
    assert report["non_authoritative"] is True
    assert set(report["case_class_counts"]) == REQUIRED_CASE_CLASSES
    assert {case["case_class"] for case in report["cases"]} == REQUIRED_CASE_CLASSES
    assert set(report["blocked_claims"]) == set(BLOCKED_CLAIM_FRAGMENTS)

    for case in report["cases"]:
        assert set(case) >= {
            "case_id",
            "case_class",
            "description",
            "source_artifacts",
            "anchors",
            "expected",
            "diagnostics",
            "non_authoritative",
            "non_claims",
        }
        assert case["case_class"] in REQUIRED_CASE_CLASSES
        assert case["expected"]["answer_state"] in ALLOWED_ANSWER_STATES
        assert case["non_authoritative"] is True
        assert case["non_claims"]
        for source_artifact in case["source_artifacts"]:
            assert source_artifact.startswith("prd/parser/")
        for anchor in case["anchors"]:
            assert set(anchor) >= {"artifact_path", "record_id", "record_kind", "source_path", "source_sha256", "non_authoritative"}
            assert anchor["artifact_path"].startswith("prd/parser/")
            assert anchor["record_id"]
            assert anchor["non_authoritative"] is True
        for diagnostic in case["diagnostics"]:
            assert set(diagnostic) >= {
                "case_id",
                "case_class",
                "severity",
                "rule",
                "artifact_path",
                "record_id",
                "record_kind",
                "source_path",
                "expected_state",
                "actual_state",
                "message",
                "non_authoritative",
            }
            assert diagnostic["non_authoritative"] is True

    serialized = json.dumps(report, ensure_ascii=False).lower()
    for forbidden_affirmative in [
        "provides legal advice",
        "claims legal correctness",
        "product-ready",
        "production-ready",
        "relation is correct",
        "falkordb runtime proof",
    ]:
        assert forbidden_affirmative not in serialized


def test_candidate_only_and_unresolved_reference_cases_preserve_source_identities() -> None:
    report = read_json(PARSER_DIR / "golden_cases.json")
    candidate = case_by_class(report, "candidate-only")
    unresolved = case_by_class(report, "unresolved-reference")

    candidate_anchor = candidate["anchors"][0]
    assert candidate_anchor["record_id"] == "REL-CONS-0001"
    assert candidate_anchor["relation_status"] == "candidate"
    assert candidate_anchor["source_block_id"] == "BLOCK-CONSULTANT-XML-0001"
    assert candidate_anchor["subject_ref"] == "consultant-list:law-source/consultant/Список документов (5).xml"
    assert candidate_anchor["object_ref"] == "consultant:LAW:179581@11.05.2026"
    assert candidate["expected"]["required_relation_status"] == "candidate"
    assert candidate["expected"]["required_staging_edge_key"] == "REL-CONS-0001"
    assert {"relation correctness", "Consultant WordML legal authority"} <= set(candidate["expected"]["forbidden_claims"])

    staging_graph = read_json(PARSER_DIR / "parser_staging_graph.json")
    unresolved_ids = set(staging_graph["unresolved_reference_ids"])
    assert unresolved_ids == {
        "consultant-list:law-source/consultant/Список документов (5).xml",
        "consultant:LAW:179581@11.05.2026",
    }
    assert {anchor["record_id"] for anchor in unresolved["anchors"]} == unresolved_ids
    assert set(unresolved["expected"]["required_reference_ids"]) == unresolved_ids
    assert "DOC-44-FZ" not in unresolved["expected"]["required_reference_ids"]
    assert "DOC-PP-60" not in unresolved["expected"]["required_reference_ids"]


def test_check_reports_path_qualified_stale_artifacts(tmp_path: Path) -> None:
    module = load_module()
    output_dir = tmp_path / "parser"
    module.write_outputs(output_dir)

    ok = run_cli("--check", "--output-dir", str(output_dir))
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert parse_stdout_json(ok)["artifact_freshness"]["status"] == "pass"

    (output_dir / "golden_cases.md").write_text("stale\n", encoding="utf-8")
    stale = run_cli("--check", "--output-dir", str(output_dir))

    assert stale.returncode == 1
    report = parse_stdout_json(stale)
    assert report["status"] == "fail"
    assert report["artifact_freshness"]["status"] == "stale"
    assert any(path.endswith("golden_cases.md") for path in report["artifact_freshness"]["stale_paths"])
    stale_diagnostics = [diagnostic for diagnostic in report["diagnostics"] if diagnostic["rule"] == "stale-artifact"]
    assert stale_diagnostics
    assert all(diagnostic["severity"] == "error" for diagnostic in stale_diagnostics)
    assert any(diagnostic["artifact_path"].endswith("golden_cases.md") for diagnostic in stale_diagnostics)


def test_malformed_jsonl_becomes_path_line_rule_diagnostic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    parser_dir = copy_source_fixtures(tmp_path, module, monkeypatch)
    malformed = parser_dir / "consultant_relation_candidates.jsonl"
    malformed.write_text('{"record_kind":"relation_candidate"\n', encoding="utf-8")

    report = module.build_report()
    rules = diagnostics_by_rule(report)

    assert report["status"] == "fail"
    assert "json_invalid" in rules
    diagnostic = rules["json_invalid"][0]
    assert diagnostic["artifact_path"] == str(malformed)
    assert diagnostic["line"] == 1
    assert diagnostic["rule"] == "json_invalid"
    assert diagnostic["expected_state"] == "valid-parser-record"
    assert diagnostic["actual_state"] == "invalid-parser-record"
    assert diagnostic["non_authoritative"] is True
    assert "missing_candidate" in rules


def test_candidate_promotion_and_missing_unresolved_references_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    parser_dir = copy_source_fixtures(tmp_path, module, monkeypatch)

    relations = read_jsonl(parser_dir / "consultant_relation_candidates.jsonl")
    relations[0]["status"] = "rejected"
    write_jsonl(parser_dir / "consultant_relation_candidates.jsonl", relations)
    staging_graph = read_json(parser_dir / "parser_staging_graph.json")
    staging_graph["unresolved_reference_ids"] = []
    (parser_dir / "parser_staging_graph.json").write_text(json.dumps(staging_graph, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    report = module.build_report()
    rules = diagnostics_by_rule(report)

    assert report["status"] == "fail"
    candidate = rules["candidate_promoted"][0]
    assert candidate["record_id"] == "REL-CONS-0001"
    assert candidate["expected_state"] == "candidate-only"
    assert candidate["actual_state"] == "rejected"
    assert candidate["artifact_path"] == str(parser_dir / "consultant_relation_candidates.jsonl")
    missing_unresolved = rules["unresolved_reference_missing"][0]
    assert missing_unresolved["artifact_path"] == str(parser_dir / "parser_staging_graph.json")
    assert missing_unresolved["expected_state"] == "unresolved-reference"
    assert missing_unresolved["actual_state"] == "missing"
    assert {diagnostic["case_class"] for diagnostic in rules["required_case_class_missing"]} >= {
        "candidate-only",
        "unresolved-reference",
    }


def test_missing_evidence_source_blocks_fail_without_long_text_comparison(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    parser_dir = copy_source_fixtures(tmp_path, module, monkeypatch)
    (parser_dir / "odt_source_block_records.jsonl").write_text("", encoding="utf-8")

    report = module.build_report()
    rules = diagnostics_by_rule(report)

    assert report["status"] == "fail"
    assert rules["missing_evidence"][0]["case_id"] == "GT-001"
    assert rules["missing_evidence"][0]["artifact_path"] == str(parser_dir / "odt_source_block_records.jsonl")
    assert rules["required_case_class_missing"][0]["case_class"] == "evidence-present"
