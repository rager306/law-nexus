from __future__ import annotations

import json
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
