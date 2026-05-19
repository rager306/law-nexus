from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/verify-graph-filtered-retrieval-integration.py"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/graph_filtered_retrieval_integration_proof.json"

REQUIRED_PHASES = {
    "s04_fixture_verification",
    "s05_baseline_verification",
    "graph_runtime",
    "graph_materialization",
    "ontology_temporal_filter",
    "citation_preservation",
    "baseline_comparison",
    "negative_routes",
    "cleanup",
    "overclaim_safety",
}

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
    "MATCH (",
    "CREATE (",
}


def load_module(name: str = "s06_integration") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_checked_in_proof_shape_and_routes_are_passing() -> None:
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    serialized = json.dumps(proof, ensure_ascii=False, sort_keys=True)

    assert proof["schema_version"] == "graph-filtered-retrieval-integration-proof/v1"
    assert set(proof["phases"]) == REQUIRED_PHASES
    assert all(phase["status"] == "passed" for phase in proof["phases"].values())
    assert proof["container_runtime"]["cleanup_status"] == "deleted"
    assert proof["materialized_counts"]["candidate_count"] == 5
    assert proof["baseline_metrics"]["threshold_passed"] is True
    assert {route["route"] for route in proof["routes"]} == {
        "positive_evidence_span_filter",
        "positive_source_block_filter",
        "stale_temporal_filter",
        "ambiguous_candidate_filter",
        "unsupported_scope_filter",
        "scoped_no_answer_filter",
    }
    assert all(route["status"] == "passed" for route in proof["routes"])
    for snippet in FORBIDDEN_SNIPPETS:
        assert snippet not in serialized


def test_candidate_projection_preserves_safe_ids_and_temporal_status() -> None:
    module = load_module("s06_candidates")
    fixture = load_fixture()

    candidates = module.all_candidates(fixture)

    assert len(candidates) == 5
    by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    assert by_id["CAND-M021-S04-EV-ARTICLE-0001"]["temporal_status"] == "current"
    assert by_id["CAND-M021-S04-STALE-WRONG-EDITION-001"]["temporal_status"] == "stale"
    assert by_id["CAND-M021-S04-EV-ARTICLE-0001"]["evidence_span_id"] == "EV-M014-HIER-CONS-ARTICLE-0001"
    assert by_id["CAND-M021-S04-EV-ARTICLE-0001"]["source_block_id"] == "SB-M014-HIER-CONS-ARTICLE-0001"
    assert by_id["CAND-M021-S04-EV-ARTICLE-0001"]["citation_key"] == "CIT-M014-HIER-CONS-ARTICLE-0001"


def test_expected_ids_from_fixture_match_routes() -> None:
    module = load_module("s06_expected_ids")
    fixture = load_fixture()

    assert module.expected_ids(fixture, "positive_evidence_span") == ["CAND-M021-S04-EV-ARTICLE-0001"]
    assert module.expected_ids(fixture, "positive_source_block_marker") == ["CAND-M021-S04-SB-ARTICLE-0001-MARKER"]
    assert module.expected_ids(fixture, "stale_temporal_negative") == []
    assert module.expected_ids(fixture, "stale_temporal_negative", "expected_rejected_candidate_ids") == ["CAND-M021-S04-STALE-WRONG-EDITION-001"]


def test_citation_preservation_contains_positive_bindings() -> None:
    module = load_module("s06_citation")
    fixture = load_fixture()

    result = module.citation_preservation([], fixture)

    assert result["status"] == "passed"
    assert result["diagnostic_codes"] == ["citation_binding_preserved"]
    assert {row["candidate_id"] for row in result["preserved_bindings"]} == {
        "CAND-M021-S04-EV-ARTICLE-0001",
        "CAND-M021-S04-SB-ARTICLE-0001-MARKER",
    }
    assert all(row["evidence_span_id"] for row in result["preserved_bindings"])
    assert all(row["source_block_id"] for row in result["preserved_bindings"])
    assert all(row["citation_key"] for row in result["preserved_bindings"])


def test_cli_blocks_when_container_disabled() -> None:
    result = subprocess.run(
        ["uv", "run", "python", str(CLI), "--container", "never", "--no-write", "--timeout", "120"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["phases"]["graph_runtime"]["status"] == "blocked"
    assert "graph_runtime_blocked" in payload["diagnostic_codes"]
    assert payload["container_runtime"]["status"] == "skipped_by_flag"


def test_safety_rejects_unsafe_field_and_fragment() -> None:
    module = load_module("s06_safety")
    payload = module.base_report()
    payload["raw_text"] = "blocked"

    try:
        module.assert_safe_payload(payload)
    except module.IntegrationError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected IntegrationError")

    payload = module.base_report()
    payload["note"] = "provider_payload"
    try:
        module.assert_safe_payload(payload)
    except module.IntegrationError as exc:
        assert "unsafe output fragment" in str(exc)
    else:
        raise AssertionError("expected IntegrationError")
