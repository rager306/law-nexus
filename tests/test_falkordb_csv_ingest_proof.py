from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "verify-falkordb-csv-ingest-proof.py"

FORBIDDEN_SNIPPETS = {
    "Федеральный закон",
    "Статья",
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
}


def load_module(name: str = "csv_ingest_proof") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Args:
    container = "auto"
    container_image = "falkordb/falkordb:edge"


def test_fixture_counts_match_contract() -> None:
    module = load_module("csv_ingest_counts")

    counts = module.expected_counts()

    assert counts == {
        "expected_source_node_rows": 4,
        "expected_source_relationship_rows": 3,
        "expected_node_count": 4,
        "expected_relationship_count": 3,
        "expected_current_nodes": 3,
        "expected_inactive_nodes": 1,
    }


def test_base_report_is_safe_and_keeps_non_claims() -> None:
    module = load_module("csv_ingest_safe_report")

    report = module.base_report(Args(), "load_csv_passed", [])
    report["graph_counts"] = {
        "node_count": 4,
        "relationship_count": 3,
        "current_nodes": 3,
        "inactive_nodes": 1,
    }
    report["idempotency"] = {
        "mode": "MERGE rerun",
        "status": "passed",
        "duplicate_nodes_created": 0,
        "duplicate_relationships_created": 0,
    }

    module.assert_safe_payload(report)
    serialized = json.dumps(report, ensure_ascii=False)
    for forbidden in FORBIDDEN_SNIPPETS:
        assert forbidden not in serialized
    assert report["schema_version"] == "falkordb-csv-ingest-proof/v1"
    assert report["requirement"] == "R037"
    assert report["related_requirement"] == "R035"
    assert report["loader"]["mechanism"] == "LOAD CSV"
    assert any("Does not validate R035" in claim for claim in report["non_claims"])
    assert any("retrieval quality" in claim for claim in report["non_claims"])


def test_compare_counts_reports_mismatches() -> None:
    module = load_module("csv_ingest_mismatch")

    report: dict[str, Any] = module.base_report(Args(), "load_csv_passed", [])
    report["graph_counts"] = {
        "node_count": 4,
        "relationship_count": 2,
        "current_nodes": 3,
        "inactive_nodes": 1,
    }

    assert module.compare_counts(report) == ["LOAD_CSV_COUNTS_MISMATCH"]


def test_compare_counts_accepts_expected_counts() -> None:
    module = load_module("csv_ingest_expected")

    report: dict[str, Any] = module.base_report(Args(), "load_csv_passed", [])
    report["graph_counts"] = {
        "node_count": 4,
        "relationship_count": 3,
        "current_nodes": 3,
        "inactive_nodes": 1,
    }

    assert module.compare_counts(report) == []
