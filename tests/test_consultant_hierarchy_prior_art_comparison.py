from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parser_records import ConsultantHierarchyRecord, load_jsonl_records  # noqa: E402

SCRIPT_PATH = ROOT / "scripts" / "compare-consultant-hierarchy-prior-art.py"
JSON_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_prior_art_comparison.json"
REPORT_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_prior_art_comparison.md"
EXPECTATIONS_PATH = ROOT / "prd" / "parser" / "consultant_prior_art_expectations.json"
HIERARCHY_JSONL_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl"


def load_comparison_module():
    spec = importlib.util.spec_from_file_location("compare_consultant_hierarchy_prior_art", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def hierarchy_records() -> list[ConsultantHierarchyRecord]:
    records, diagnostics = load_jsonl_records(HIERARCHY_JSONL_PATH)
    assert diagnostics == []
    return [record for record in records if isinstance(record, ConsultantHierarchyRecord)]


def test_generated_comparison_classifies_pass_accepted_and_needs_review_with_anchors():
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))

    assert payload["phase"] == "consultant_hierarchy_prior_art_comparison"
    assert payload["non_authoritative"] is True
    assert payload["fatal_error_count"] == 0
    assert payload["overall_status"] == "needs-review"
    assert payload["blocked_check_count"] == 0
    assert payload["needs_review_check_count"] == 1
    assert payload["classification_counts"] == {"accepted": 4, "needs-review": 1, "pass": 6}

    checks = {check["check_id"]: check for check in payload["checks"]}
    assert checks["COUNT-CHAPTER"]["status"] == "pass"
    assert checks["COUNT-ARTICLE"]["status"] == "pass"
    assert checks["COUNT-PART"]["status"] == "accepted"
    assert checks["COUNT-CLAUSE"]["status"] == "accepted"
    assert checks["COUNT-SUBCLAUSE"]["status"] == "accepted"
    assert checks["COUNT-SECTION"]["status"] == "accepted"
    assert checks["ORDER-CHAPTER-ARTICLE-COUNTS"]["status"] == "pass"
    assert checks["ORDER-FIRST-LAST-ARTICLES"]["status"] == "pass"
    assert checks["STRUCT-PARENTS-AND-ORDER"]["status"] == "pass"
    assert checks["INPUT-VALIDATION"]["status"] == "pass"

    invalidity = checks["INVALIDITY-MARKER-SAMPLES"]
    assert invalidity["status"] == "needs-review"
    assert invalidity["rule_ids"] == ["SEM-009"]
    assert invalidity["expected"] == {"article": 11, "part": 41, "clause": 17, "subclause": 1}
    assert invalidity["observed"] == {"article": 10, "part": 40, "clause": 19, "subclause": 1}
    assert invalidity["evidence_anchors"]
    assert {"record_id", "source_sha256", "excerpt_sha256", "excerpt"} <= set(invalidity["evidence_anchors"][0])

    report = REPORT_PATH.read_text(encoding="utf-8")
    assert "non-authoritative" in report
    assert "COUNT-PART" in report
    assert "INVALIDITY-MARKER-SAMPLES" in report


def test_cli_check_reports_fresh_artifacts_without_blocking_on_needs_review():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["status"] == "pass"
    assert payload["overall_status"] == "needs-review"
    assert payload["artifact_freshness"] == {
        "prd/parser/consultant_hierarchy_prior_art_comparison.json": True,
        "prd/parser/consultant_hierarchy_prior_art_comparison.md": True,
    }
    assert payload["fatal_error_count"] == 0
    assert payload["blocked_check_count"] == 0


def test_generator_build_is_deterministic_against_artifacts():
    module = load_comparison_module()
    result = module.build()

    assert result.summary_json == JSON_PATH.read_text(encoding="utf-8")
    assert result.report_md == REPORT_PATH.read_text(encoding="utf-8")
    assert result.diagnostics["observed"]["counts_by_level"] == {
        "article": 94,
        "chapter": 8,
        "clause": 997,
        "document": 1,
        "part": 793,
        "section": 9,
        "subclause": 283,
    }
    assert result.diagnostics["observed"]["chapter_article_counts"] == {
        "1": 15,
        "2": 8,
        "3": 47,
        "4": 2,
        "5": 6,
        "6": 3,
        "7": 10,
        "8": 3,
    }


def test_compare_blocks_major_structure_parent_breakage():
    module = load_comparison_module()
    expectations = json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))
    records = hierarchy_records()
    first_article_index = next(index for index, record in enumerate(records) if record.level == "article")
    records[first_article_index] = records[first_article_index].model_copy(update={"parent_id": "HIER-CONS-MISSING-PARENT"})

    payload = module.compare(expectations, records, [])
    checks = {check["check_id"]: check for check in payload["checks"]}

    assert payload["overall_status"] == "blocked"
    assert checks["STRUCT-PARENTS-AND-ORDER"]["status"] == "blocked"
    assert checks["STRUCT-PARENTS-AND-ORDER"]["observed"]["missing_parent_count"] == 1
    assert checks["STRUCT-PARENTS-AND-ORDER"]["evidence_anchors"][0]["record_id"].startswith("HIER-CONS-ARTICLE")


def test_compare_blocks_malformed_input_diagnostics():
    module = load_comparison_module()
    expectations = json.loads(EXPECTATIONS_PATH.read_text(encoding="utf-8"))

    payload = module.compare(expectations, hierarchy_records(), [{"rule": "json_invalid", "record_id": None}])
    checks = {check["check_id"]: check for check in payload["checks"]}

    assert payload["overall_status"] == "blocked"
    assert checks["INPUT-VALIDATION"]["status"] == "blocked"
    assert checks["INPUT-VALIDATION"]["observed"]["parse_diagnostic_count"] == 1
