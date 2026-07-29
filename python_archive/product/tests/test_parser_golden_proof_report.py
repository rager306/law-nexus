from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER_DIR = ROOT / "prd" / "parser"
REPORT_PATH = PARSER_DIR / "golden_test_proof_report.md"
GOLDEN_CASES_PATH = PARSER_DIR / "golden_cases.json"

REQUIRED_COMMANDS = [
    "uv run python scripts/build-parser-golden-cases.py --check",
    "uv run python scripts/evaluate-parser-golden-cases.py --check",
]
REQUIRED_CASE_CLASSES = {
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
}
REQUIRED_SOURCE_PATHS = {
    "prd/parser/golden_test_contract.md",
    "prd/parser/golden_cases.json",
    "prd/parser/golden_cases.md",
    "prd/parser/odt_document_records.jsonl",
    "prd/parser/odt_source_block_records.jsonl",
    "prd/parser/consultant_relation_candidates.jsonl",
    "prd/parser/parser_staging_graph.json",
    "scripts/build-parser-golden-cases.py",
    "scripts/evaluate-parser-golden-cases.py",
}
REQUIRED_BLOCKED_CLAIMS = {
    "Consultant WordML legal authority",
    "FalkorDB loading/runtime readiness",
    "citation-safe retrieval readiness",
    "legal-answer correctness",
    "parser completeness",
    "product ETL readiness",
    "product graph truth",
    "relation correctness",
    "retrieval quality",
}
FORBIDDEN_READINESS_UPGRADES = [
    "proves parser completeness",
    "validates parser completeness",
    "proves product retrieval quality",
    "validates product retrieval quality",
    "proves citation-safe retrieval readiness",
    "validates citation-safe retrieval readiness",
    "proves legal-answer correctness",
    "validates legal-answer correctness",
    "proves relation correctness",
    "validates relation correctness",
    "proves FalkorDB loading/runtime readiness",
    "validates FalkorDB loading/runtime readiness",
    "proves product graph truth",
    "validates product graph truth",
    "product retrieval is ready",
    "citation-safe retrieval is ready",
    "parser is complete",
    "legal answers are correct",
    "relations are correct",
    "FalkorDB runtime is ready",
    "product graph is true",
]
FORBIDDEN_RAW_OR_SECRET_SURFACES = [
    "BEGIN PRIVATE KEY",
    "api_key",
    "password=",
    "http://",
    "https://",
]


def read_report() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def read_golden_cases() -> dict[str, object]:
    return json.loads(GOLDEN_CASES_PATH.read_text(encoding="utf-8"))


def test_report_exists_and_uses_only_tracked_parser_artifact_sources() -> None:
    report = read_report()

    for path in REQUIRED_SOURCE_PATHS:
        assert path in report

    assert ".gsd/" not in report
    assert ".planning/" not in report
    assert ".audits/" not in report


def test_report_records_command_evidence_and_current_public_counts() -> None:
    report = read_report()

    for command in REQUIRED_COMMANDS:
        assert command in report

    for required_fragment in [
        "Status | Case count | Evaluated | Errors | Warnings | Info | Non-authoritative",
        "| build golden cases | `pass` | 5 | n/a | n/a | n/a | n/a | `true` |",
        "| evaluate golden cases | `pass` | 5 | 5 | 0 | 1 | 2 | `true` |",
        "Evaluator severity counts are `error: 0`, `warning: 1`, and `info: 2`.",
        "legalgraph-parser-golden-evaluator/v1",
    ]:
        assert required_fragment in report


def test_report_covers_required_case_classes_and_named_boundary_cases() -> None:
    report = read_report()
    golden_cases = read_golden_cases()

    assert golden_cases["case_count"] == 5
    assert set(golden_cases["case_class_counts"]) == REQUIRED_CASE_CLASSES
    assert "five evaluated cases" in report

    for case_class in REQUIRED_CASE_CLASSES:
        assert f"`{case_class}`" in report

    for required_fragment in [
        "`GT-003` keeps `REL-CONS-0001` as candidate-only / needs-review",
        "`GT-004` keeps unresolved Consultant references path-qualified",
        "consultant-list:law-source/consultant/Список документов (5).xml",
        "consultant:LAW:179581@11.05.2026",
    ]:
        assert required_fragment in report


def test_report_lists_all_blocked_claims_and_non_claim_boundary() -> None:
    report = read_report()
    golden_cases = read_golden_cases()

    assert set(golden_cases["blocked_claims"]) == {claim for claim in REQUIRED_BLOCKED_CLAIMS}
    for claim in REQUIRED_BLOCKED_CLAIMS:
        assert f"`{claim}`" in report

    for required_non_claim in [
        "It does not prove parser completeness",
        "product retrieval quality",
        "citation-safe retrieval readiness",
        "legal-answer correctness",
        "relation correctness",
        "FalkorDB loading/runtime readiness",
        "Consultant WordML legal authority",
        "product ETL readiness",
        "product graph truth",
    ]:
        assert required_non_claim in report


def test_report_points_to_path_qualified_diagnostics_without_dumping_raw_surfaces() -> None:
    report = read_report()

    for required_fragment in [
        "status",
        "case_count",
        "evaluated_case_count",
        "severity_counts",
        "blocked_claims",
        "non_authoritative",
        "path-qualified diagnostics",
        "prd/parser/odt_source_block_records.jsonl",
        "prd/parser/consultant_relation_candidates.jsonl",
        "prd/parser/parser_staging_graph.json",
    ]:
        assert required_fragment in report

    for forbidden in FORBIDDEN_RAW_OR_SECRET_SURFACES:
        assert forbidden not in report


def test_report_does_not_use_forbidden_readiness_upgrade_phrasing() -> None:
    report = read_report().casefold()

    for forbidden in FORBIDDEN_READINESS_UPGRADES:
        assert forbidden.casefold() not in report
