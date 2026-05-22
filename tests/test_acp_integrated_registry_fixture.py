from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-acp-integrated-registry-fixture.py"
ITEMS_OUTPUT = ROOT / "prd/architecture/acp/derived/integrated-registry.items.jsonl"
EDGES_OUTPUT = ROOT / "prd/architecture/acp/derived/integrated-registry.edges.jsonl"
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
ACP_ITEMS = ROOT / "prd/architecture/acp/derived/canonical-projection.items.jsonl"
ACP_EDGES = ROOT / "prd/architecture/acp/derived/canonical-projection.edges.jsonl"
SCHEMA_TESTS = ROOT / "tests/test_architecture_registry_schema.py"


def run_builder(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def load_schema_test_module():
    spec = importlib.util.spec_from_file_location("architecture_registry_schema_tests", SCHEMA_TESTS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_acp_integrated_registry_fixture_is_current() -> None:
    result = run_builder("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["item_count"] == 63
    assert payload["edge_count"] == 98
    assert payload["acp_item_count"] == 5
    assert payload["acp_edge_count"] == 7
    assert payload["diagnostic_count"] == 0
    assert "Custom integrated fixture only" in payload["boundary"]


def test_acp_integrated_registry_fixture_validates_against_schema() -> None:
    schema_tests = load_schema_test_module()
    schema = schema_tests.load_schema()
    records = [*schema_tests.load_jsonl(ITEMS_OUTPUT), *schema_tests.load_jsonl(EDGES_OUTPUT)]

    errors = schema_tests.validate_schema_records(records, schema)

    assert not errors, schema_tests.format_errors(errors)


def test_acp_integrated_registry_fixture_contains_expected_acp_records() -> None:
    items = load_jsonl(ITEMS_OUTPUT)
    edges = load_jsonl(EDGES_OUTPUT)
    acp_items = {item["id"]: item for item in items if item["id"].startswith("ACP-")}
    acp_edges = {edge["id"]: edge for edge in edges if edge["id"].startswith("ACP-EDGE-")}

    assert set(acp_items) == {"ACP-AHF-0001", "ACP-AP-0001", "ACP-APR-0001", "ACP-DC-0001", "ACP-PG-0001"}
    assert len(acp_edges) == 7
    assert acp_items["ACP-DC-0001"]["type"] == "decision_candidate"
    assert acp_items["ACP-DC-0001"]["authority_required"] is True
    for item in acp_items.values():
        assert "Does not validate R035." in item["non_claims"]
        assert "Does not validate R037." in item["non_claims"]
        assert "Does not validate R038." in item["non_claims"]


def test_acp_integrated_registry_fixture_detects_stale_outputs(tmp_path: Path) -> None:
    stale_items = tmp_path / "items.jsonl"
    stale_edges = tmp_path / "edges.jsonl"
    stale_items.write_text("{}\n", encoding="utf-8")
    stale_edges.write_text("{}\n", encoding="utf-8")

    result = run_builder("--items-output", str(stale_items), "--edges-output", str(stale_edges), "--check")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "stale-output" for diagnostic in payload["diagnostics"])


def test_acp_integrated_registry_fixture_rejects_duplicate_ids(tmp_path: Path) -> None:
    duplicate_items = tmp_path / "acp-items.jsonl"
    duplicate_edges = tmp_path / "acp-edges.jsonl"
    duplicate_items.write_text(ACP_ITEMS.read_text(encoding="utf-8"), encoding="utf-8")
    duplicate_edges.write_text(ACP_EDGES.read_text(encoding="utf-8"), encoding="utf-8")

    first_canonical = load_jsonl(CANONICAL_ITEMS)[0]
    acp_records = load_jsonl(duplicate_items)
    acp_records[0]["id"] = first_canonical["id"]
    duplicate_items.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in acp_records),
        encoding="utf-8",
    )

    result = run_builder("--acp-items", str(duplicate_items), "--acp-edges", str(duplicate_edges), "--items-output", str(tmp_path / "items.jsonl"), "--edges-output", str(tmp_path / "edges.jsonl"))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "duplicate-id" for diagnostic in payload["diagnostics"])


def test_acp_integrated_registry_fixture_rejects_broken_endpoint(tmp_path: Path) -> None:
    broken_edges = tmp_path / "acp-edges.jsonl"
    broken_edges.write_text(ACP_EDGES.read_text(encoding="utf-8"), encoding="utf-8")
    edge_records = load_jsonl(broken_edges)
    edge_records[0]["to"] = "ACP-MISSING"
    broken_edges.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in edge_records),
        encoding="utf-8",
    )

    result = run_builder("--acp-edges", str(broken_edges), "--items-output", str(tmp_path / "items.jsonl"), "--edges-output", str(tmp_path / "edges.jsonl"))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "edge-endpoint" for diagnostic in payload["diagnostics"])


def test_acp_integrated_registry_fixture_refuses_canonical_output_paths() -> None:
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_builder("--items-output", str(CANONICAL_ITEMS))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "refusing to write canonical architecture registry file" in payload["message"]
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges
