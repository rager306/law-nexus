from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/evaluate-parser-golden-cases.py"

REQUIRED_CASE_CLASSES = {
    "evidence-present",
    "no-answer",
    "candidate-only",
    "unresolved-reference",
    "non-authoritative",
}
REQUIRED_BLOCKED_CLAIMS = {
    "parser completeness",
    "retrieval quality",
    "legal-answer correctness",
    "citation-safe retrieval readiness",
    "product ETL readiness",
    "FalkorDB loading/runtime readiness",
    "Consultant WordML legal authority",
    "relation correctness",
    "product graph truth",
}


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


def copy_parser_artifacts(tmp_path: Path) -> Path:
    """Copy only bounded tracked parser artifacts used by the evaluator."""

    parser_dir = tmp_path / "prd" / "parser"
    parser_dir.mkdir(parents=True)
    for filename in [
        "golden_cases.json",
        "odt_document_records.jsonl",
        "odt_source_block_records.jsonl",
        "consultant_relation_candidates.jsonl",
        "parser_staging_graph.json",
    ]:
        shutil.copy2(ROOT / "prd" / "parser" / filename, parser_dir / filename)
    return parser_dir


def run_cli_for_parser_dir(parser_dir: Path) -> subprocess.CompletedProcess[str]:
    return run_cli(
        "--check",
        "--parser-dir",
        str(parser_dir),
        "--golden-cases",
        str(parser_dir / "golden_cases.json"),
    )


def load_json_artifact(parser_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((parser_dir / filename).read_text(encoding="utf-8"))


def write_json_artifact(parser_dir: Path, filename: str, payload: dict[str, Any]) -> None:
    (parser_dir / filename).write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def load_jsonl_artifact(parser_dir: Path, filename: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (parser_dir / filename).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl_artifact(parser_dir: Path, filename: str, rows: list[dict[str, Any]]) -> None:
    (parser_dir / filename).write_text(
        "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )


def assert_error_diagnostic(
    report: dict[str, Any],
    *,
    case_id: str | None,
    rule: str,
    artifact_suffix: str,
    case_class: str | None = None,
) -> dict[str, Any]:
    matches = [
        diagnostic
        for diagnostic in report["diagnostics"]
        if diagnostic["case_id"] == case_id
        and diagnostic["rule"] == rule
        and diagnostic["severity"] == "error"
        and diagnostic["artifact_path"].endswith(artifact_suffix)
        and (case_class is None or diagnostic["case_class"] == case_class)
    ]
    assert matches, report
    return matches[0]


def test_evaluator_cli_passes_tracked_golden_cases() -> None:
    result = run_cli("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    report = parse_stdout_json(result)
    assert report["schema_version"] == "legalgraph-parser-golden-evaluator/v1"
    assert report["generated_by"] == "scripts/evaluate-parser-golden-cases.py"
    assert report["status"] == "pass"
    assert report["non_authoritative"] is True
    assert report["case_count"] == 5
    assert report["evaluated_case_count"] == 5
    assert set(report["case_class_counts"]) == REQUIRED_CASE_CLASSES
    assert report["error_count"] == 0
    assert report["severity_counts"]["error"] == 0
    assert set(report["blocked_claims"]) == REQUIRED_BLOCKED_CLAIMS


def test_evaluator_stdout_has_compact_path_qualified_diagnostics() -> None:
    result = run_cli("--check")
    report = parse_stdout_json(result)

    assert report["diagnostics"]
    assert {diagnostic["rule"] for diagnostic in report["diagnostics"]} >= {
        "intentionally_absent_target",
        "unresolved_references_preserved",
        "claims_blocked",
    }
    for diagnostic in report["diagnostics"]:
        assert set(diagnostic) >= {
            "case_id",
            "case_class",
            "rule",
            "artifact_path",
            "expected_state",
            "actual_state",
            "message",
            "severity",
            "non_authoritative",
        }
        assert diagnostic["case_class"] in REQUIRED_CASE_CLASSES
        assert diagnostic["artifact_path"].startswith("prd/parser/")
        assert diagnostic["non_authoritative"] is True


def test_evaluator_stdout_preserves_non_authoritative_redaction_boundary() -> None:
    result = run_cli("--check")
    serialized = result.stdout.lower()

    for forbidden in [
        "article 1",
        "статья",
        "provides legal advice",
        "claims legal correctness",
        "legal answer is correct",
        "product-ready",
        "production-ready",
        "product retrieval is ready",
        "citation-safe retrieval is ready",
        "relation is correct",
        "falkordb runtime proof",
    ]:
        assert forbidden not in serialized


def test_fails_when_required_evidence_source_block_is_missing(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    rows = [row for row in load_jsonl_artifact(parser_dir, "odt_source_block_records.jsonl") if row["id"] != "BLOCK-44-FZ-000"]
    write_jsonl_artifact(parser_dir, "odt_source_block_records.jsonl", rows)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-001",
        case_class="evidence-present",
        rule="required_evidence_missing",
        artifact_suffix="odt_source_block_records.jsonl",
    )
    assert diagnostic["record_id"] == "BLOCK-44-FZ-000"
    assert diagnostic["expected_state"] == "evidence-present"
    assert diagnostic["actual_state"] == "missing"


def test_fails_when_required_evidence_source_block_hash_drifts(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    rows = load_jsonl_artifact(parser_dir, "odt_source_block_records.jsonl")
    target = next(row for row in rows if row["id"] == "BLOCK-44-FZ-000")
    target["source_sha256"] = "0" * 64
    write_jsonl_artifact(parser_dir, "odt_source_block_records.jsonl", rows)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-001",
        case_class="evidence-present",
        rule="evidence_anchor_hash_mismatch",
        artifact_suffix="odt_source_block_records.jsonl",
    )
    assert diagnostic["record_id"] == "BLOCK-44-FZ-000"
    assert diagnostic["expected_state"] == "source_sha256-matches-anchor"
    assert diagnostic["actual_state"] == "source_sha256-mismatch"


def test_fails_when_evidence_case_has_empty_anchors(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    golden = load_json_artifact(parser_dir, "golden_cases.json")
    case = next(item for item in golden["cases"] if item["case_id"] == "GT-001")
    case["anchors"] = []
    write_json_artifact(parser_dir, "golden_cases.json", golden)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-001",
        case_class="evidence-present",
        rule="evidence_anchor_missing",
        artifact_suffix="odt_source_block_records.jsonl",
    )
    assert diagnostic["expected_state"] == "bounded-anchor-present"
    assert diagnostic["actual_state"] == "missing"


def test_fails_when_no_answer_target_is_fabricated_in_records(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    rows = load_jsonl_artifact(parser_dir, "odt_document_records.jsonl")
    fabricated = dict(rows[0])
    fabricated["id"] = "DOC-ABSENT-GOLDEN-NO-ANSWER"
    fabricated["title"] = "Synthetic no-answer drift record"
    rows.append(fabricated)
    write_jsonl_artifact(parser_dir, "odt_document_records.jsonl", rows)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-002",
        case_class="no-answer",
        rule="no_answer_target_matched",
        artifact_suffix="consultant_relation_candidates.jsonl",
    )
    assert diagnostic["record_id"] == "DOC-ABSENT-GOLDEN-NO-ANSWER"
    assert diagnostic["expected_state"] == "no-answer"
    assert diagnostic["actual_state"] == "matched"


def test_fails_when_no_answer_case_gains_anchor(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    golden = load_json_artifact(parser_dir, "golden_cases.json")
    case = next(item for item in golden["cases"] if item["case_id"] == "GT-002")
    case["anchors"] = [
        {
            "artifact_path": "prd/parser/odt_document_records.jsonl",
            "record_id": "DOC-44-FZ",
            "record_kind": "document",
        }
    ]
    write_json_artifact(parser_dir, "golden_cases.json", golden)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-002",
        case_class="no-answer",
        rule="no_answer_target_matched",
        artifact_suffix="consultant_relation_candidates.jsonl",
    )
    assert diagnostic["expected_state"] == "no-answer"
    assert diagnostic["actual_state"] == "matched"


def test_fails_when_candidate_relation_is_promoted(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    rows = load_jsonl_artifact(parser_dir, "consultant_relation_candidates.jsonl")
    rows[0]["status"] = "needs-review"
    write_jsonl_artifact(parser_dir, "consultant_relation_candidates.jsonl", rows)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-003",
        case_class="candidate-only",
        rule="candidate_relation_not_candidate",
        artifact_suffix="consultant_relation_candidates.jsonl",
    )
    assert diagnostic["record_id"] == "REL-CONS-0001"
    assert diagnostic["expected_state"] == "candidate-only"
    assert diagnostic["actual_state"] == "needs-review"


def test_fails_when_candidate_keyed_staging_edge_is_missing(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    staging_graph = load_json_artifact(parser_dir, "parser_staging_graph.json")
    staging_graph["keyed_relation_edges"] = []
    write_json_artifact(parser_dir, "parser_staging_graph.json", staging_graph)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-003",
        case_class="candidate-only",
        rule="candidate_staging_edge_missing",
        artifact_suffix="parser_staging_graph.json",
    )
    assert diagnostic["record_id"] == "REL-CONS-0001"
    assert diagnostic["expected_state"] == "keyed-candidate-edge"
    assert diagnostic["actual_state"] == "missing"


def test_fails_when_unresolved_reference_boundary_drifts_empty(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    staging_graph = load_json_artifact(parser_dir, "parser_staging_graph.json")
    staging_graph["unresolved_reference_ids"] = []
    write_json_artifact(parser_dir, "parser_staging_graph.json", staging_graph)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-004",
        case_class="unresolved-reference",
        rule="unresolved_reference_missing",
        artifact_suffix="parser_staging_graph.json",
    )
    assert diagnostic["expected_state"] == "unresolved-reference"
    assert diagnostic["actual_state"] == "missing"


def test_fails_when_unresolved_reference_boundary_adds_resolved_odt_id(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    staging_graph = load_json_artifact(parser_dir, "parser_staging_graph.json")
    staging_graph["unresolved_reference_ids"] = ["DOC-44-FZ"]
    write_json_artifact(parser_dir, "parser_staging_graph.json", staging_graph)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-004",
        case_class="unresolved-reference",
        rule="unresolved_reference_unexpected",
        artifact_suffix="parser_staging_graph.json",
    )
    assert diagnostic["record_id"] == "DOC-44-FZ"
    assert diagnostic["expected_state"] == "only-golden-unresolved-reference-ids"
    assert diagnostic["actual_state"] == "unexpected"


def test_fails_when_required_blocked_claim_is_missing(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    golden = load_json_artifact(parser_dir, "golden_cases.json")
    golden["blocked_claims"] = [claim for claim in golden["blocked_claims"] if claim != "retrieval quality"]
    write_json_artifact(parser_dir, "golden_cases.json", golden)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-005",
        case_class="non-authoritative",
        rule="blocked_claim_missing",
        artifact_suffix="golden_cases.json",
    )
    assert diagnostic["record_id"] == "blocked-claims"
    assert diagnostic["expected_state"] == "blocked-claim-present"
    assert diagnostic["actual_state"] == "missing"
    assert "retrieval quality" in diagnostic["message"]


def test_fails_closed_for_invalid_jsonl_without_traceback(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    with (parser_dir / "odt_source_block_records.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id=None,
        rule="json_invalid",
        artifact_suffix="odt_source_block_records.jsonl",
    )
    assert diagnostic["expected_state"] == "valid-parser-record"
    assert diagnostic["actual_state"] == "invalid-parser-record"


def test_fails_closed_for_invalid_golden_json_without_traceback(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    (parser_dir / "golden_cases.json").write_text("{not-json}\n", encoding="utf-8")

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id=None,
        rule="json_invalid",
        artifact_suffix="golden_cases.json",
    )
    assert diagnostic["expected_state"] == "valid-json-object"
    assert diagnostic["actual_state"] == "invalid-json"


def test_fails_closed_for_unsupported_case_class(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    golden = load_json_artifact(parser_dir, "golden_cases.json")
    golden["cases"][0]["case_class"] = "unsupported-boundary"
    write_json_artifact(parser_dir, "golden_cases.json", golden)

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id="GT-001",
        case_class="unsupported-boundary",
        rule="unsupported_case_class",
        artifact_suffix="golden_cases.json",
    )
    assert diagnostic["expected_state"] == "supported-case-class"
    assert diagnostic["actual_state"] == "unsupported-boundary"


def test_fails_closed_for_missing_source_artifact(tmp_path: Path) -> None:
    parser_dir = copy_parser_artifacts(tmp_path)
    (parser_dir / "parser_staging_graph.json").unlink()

    result = run_cli_for_parser_dir(parser_dir)

    assert result.returncode != 0
    report = parse_stdout_json(result)
    diagnostic = assert_error_diagnostic(
        report,
        case_id=None,
        rule="missing_source_artifact",
        artifact_suffix="parser_staging_graph.json",
    )
    assert diagnostic["expected_state"] == "readable-json-object"
    assert diagnostic["actual_state"] == "missing"
