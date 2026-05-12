from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROOF_JSON_PATH = ROOT / "prd" / "parser" / "consultant_parser_proof.json"
PROOF_MD_PATH = ROOT / "prd" / "parser" / "consultant_parser_proof.md"
INVENTORY_PATH = ROOT / "prd" / "parser" / "consultant_prior_art_inventory.json"
HIERARCHY_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl"
COMPARISON_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_prior_art_comparison.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_proof() -> dict:
    return json.loads(PROOF_JSON_PATH.read_text(encoding="utf-8"))


def test_proof_package_records_current_input_freshness():
    proof = load_proof()
    by_path = {entry["path"]: entry for entry in proof["input_artifacts"]}

    for path in [INVENTORY_PATH, HIERARCHY_PATH, COMPARISON_PATH]:
        relative = path.relative_to(ROOT).as_posix()
        assert relative in by_path
        assert by_path[relative]["exists"] is True
        assert by_path[relative]["size_bytes"] == path.stat().st_size
        assert by_path[relative]["sha256"] == sha256(path)

    assert proof["artifact_freshness"] == {
        "rule": "tests/test_consultant_parser_proof.py recomputes input sha256/size and fails if proof input_artifacts drift.",
        "stale_artifact_count": 0,
        "stale_artifacts": [],
        "status": "fresh-at-generation",
    }


def test_proof_exposes_consultant_fixture_inventory_and_hierarchy_counts():
    proof = load_proof()

    assert proof["package_scope"] == "Consultant 44-FZ tracer proof package only"
    assert proof["source_kind"] == "consultant-wordml-xml"
    assert proof["document_id"] == "DOC-CONS-44-FZ"

    inventory = proof["fixture_inventory"]
    assert inventory["asset_count"] == 28
    assert inventory["classification_counts"] == {"adapt": 13, "defer": 13, "keep": 1, "reject": 1}
    assert inventory["missing_assets"] == []
    assert inventory["hash_mismatches"] == []
    assert inventory["consultant_fixture_assets"][0]["source_path"] == "law-source/consultant/44-FZ-2026.xml"
    assert inventory["consultant_fixture_assets"][0]["classification"] == "keep"

    hierarchy = proof["hierarchy_artifacts"]
    assert hierarchy["record_count"] == 2185
    assert hierarchy["counts_by_level"] == {
        "article": 94,
        "chapter": 8,
        "clause": 997,
        "document": 1,
        "part": 793,
        "section": 9,
        "subclause": 283,
    }
    assert hierarchy["duplicate_ids"] == []
    assert hierarchy["non_authoritative_false_count"] == 0
    assert hierarchy["source_paths"] == {"law-source/consultant/44-FZ-2026.xml": 2185}


def test_proof_preserves_comparison_verdicts_without_overclaiming():
    proof = load_proof()
    comparison = proof["prior_art_comparison"]

    assert comparison["overall_status"] == "needs-review"
    assert comparison["diagnostics_bounded"] is True
    assert comparison["blocked_check_count"] == 0
    assert comparison["fatal_error_count"] == 0
    assert comparison["needs_review_check_count"] == 1
    assert comparison["status_counts"] == {"accepted": 4, "needs-review": 1, "pass": 6}

    checks = {check["check_id"]: check for check in comparison["checks"]}
    assert checks["COUNT-CHAPTER"]["status"] == "pass"
    assert checks["COUNT-ARTICLE"]["status"] == "pass"
    assert checks["COUNT-PART"]["status"] == "accepted"
    assert checks["COUNT-CLAUSE"]["status"] == "accepted"
    assert checks["INVALIDITY-MARKER-SAMPLES"]["status"] == "needs-review"
    assert checks["INVALIDITY-MARKER-SAMPLES"]["rationale"] == (
        "Invalidity wording is compared as advisory marker evidence only; it does not determine amendment legal effect."
    )


def test_proof_states_deferred_garant_boundary_and_non_claims():
    proof = load_proof()
    non_claims = "\n".join(proof["non_claims"])

    assert "Garant ODT parsing" in proof["deferred_boundaries"]["garant"]
    assert "not a completion gate" in proof["deferred_boundaries"]["garant"]
    assert "multi-source parser readiness" in proof["deferred_boundaries"]["multi_source"]
    assert "FalkorDB/product ETL load readiness" in proof["deferred_boundaries"]["graph_loading"]
    assert "Does not claim legal correctness" in non_claims
    assert "Does not claim parser completeness" in non_claims
    assert "Does not wire Garant ODT parsing" in non_claims


def test_markdown_report_is_self_contained_for_cold_reader():
    report = PROOF_MD_PATH.read_text(encoding="utf-8")

    assert "# Consultant Parser Proof Package" in report
    assert "## Commands" in report
    assert ".venv/bin/python3 -m pytest tests/test_consultant_parser_proof.py" in report
    assert "## Input Artifacts and Freshness" in report
    assert "Freshness status: **fresh-at-generation**; stale artifact count: **0**" in report
    assert "Total records: **2185**" in report
    assert "Overall status: **needs-review**" in report
    assert "INVALIDITY-MARKER-SAMPLES" in report
    assert "Garant is deferred separately" in report
    assert "Does not claim product ETL, FalkorDB load readiness, or multi-source parser readiness." in report
