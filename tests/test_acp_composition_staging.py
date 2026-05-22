from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-acp-composition-staging.py"
ITEMS_OUTPUT = ROOT / "prd/architecture/acp/derived/composed-registry.items.jsonl"
EDGES_OUTPUT = ROOT / "prd/architecture/acp/derived/composed-registry.edges.jsonl"
REPORT_OUTPUT = ROOT / "prd/architecture/acp/derived/composition-report.json"
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


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def run_with_temp_outputs(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_builder(
        *args,
        "--items-output",
        str(tmp_path / "items.jsonl"),
        "--edges-output",
        str(tmp_path / "edges.jsonl"),
        "--report-output",
        str(tmp_path / "report.json"),
    )


def test_acp_composition_staging_outputs_are_current() -> None:
    result = run_builder("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["owner"] == "ACP composition staging"
    assert payload["diagnostic_count"] == 0
    assert payload["record_counts"] == {
        "canonical_item_count": 58,
        "canonical_edge_count": 91,
        "acp_item_count": 5,
        "acp_edge_count": 7,
        "composed_item_count": 63,
        "composed_edge_count": 98,
    }
    assert "custom-only" in payload["boundary"]


def test_acp_composition_staging_records_validate_against_schema() -> None:
    schema_tests = load_schema_test_module()
    schema = schema_tests.load_schema()
    records = [*schema_tests.load_jsonl(ITEMS_OUTPUT), *schema_tests.load_jsonl(EDGES_OUTPUT)]

    errors = schema_tests.validate_schema_records(records, schema)

    assert not errors, schema_tests.format_errors(errors)


def test_acp_composition_staging_report_is_current_and_safe() -> None:
    report = json.loads(REPORT_OUTPUT.read_text(encoding="utf-8"))

    assert report["status"] == "ok"
    assert report["owner"] == "ACP composition staging"
    assert report["diagnostic_count"] == 0
    assert report["outputs"]["items"] == "prd/architecture/acp/derived/composed-registry.items.jsonl"
    assert report["outputs"]["edges"] == "prd/architecture/acp/derived/composed-registry.edges.jsonl"
    assert "/root/" not in REPORT_OUTPUT.read_text(encoding="utf-8")
    assert ".gsd/exec" not in REPORT_OUTPUT.read_text(encoding="utf-8")


def test_acp_composition_staging_rejects_duplicate_ids(tmp_path: Path) -> None:
    duplicate_items = tmp_path / "acp-items.jsonl"
    duplicate_edges = tmp_path / "acp-edges.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["id"] = load_jsonl(CANONICAL_ITEMS)[0]["id"]
    write_jsonl(duplicate_items, acp_records)
    duplicate_edges.write_text(ACP_EDGES.read_text(encoding="utf-8"), encoding="utf-8")

    result = run_with_temp_outputs(tmp_path, "--acp-items", str(duplicate_items), "--acp-edges", str(duplicate_edges))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "duplicate-id" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_rejects_broken_endpoint(tmp_path: Path) -> None:
    broken_edges = tmp_path / "acp-edges.jsonl"
    edge_records = load_jsonl(ACP_EDGES)
    edge_records[0]["to"] = "ACP-MISSING"
    write_jsonl(broken_edges, edge_records)

    result = run_with_temp_outputs(tmp_path, "--acp-edges", str(broken_edges))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "edge-endpoint" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_rejects_unsafe_source_anchor(tmp_path: Path) -> None:
    unsafe_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["source_anchors"][0]["path"] = "/tmp/not-allowed"
    write_jsonl(unsafe_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--acp-items", str(unsafe_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "source-anchor-path" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_rejects_untracked_acp_source_anchor(tmp_path: Path) -> None:
    untracked = tmp_path / "not-tracked.md"
    untracked.write_text("not tracked", encoding="utf-8")
    unsafe_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["source_anchors"][0]["path"] = str(untracked.relative_to(ROOT)) if untracked.is_relative_to(ROOT) else "tmp/not-tracked.md"
    write_jsonl(unsafe_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--acp-items", str(unsafe_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "source-anchor-tracked" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_rejects_missing_non_claim(tmp_path: Path) -> None:
    invalid_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["non_claims"] = [claim for claim in acp_records[0]["non_claims"] if claim != "Does not validate R035."]
    write_jsonl(invalid_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--acp-items", str(invalid_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "acp-non-claims" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_rejects_missing_authority_requirement(tmp_path: Path) -> None:
    invalid_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    for record in acp_records:
        if record["type"] == "decision_candidate":
            record["authority_required"] = False
    write_jsonl(invalid_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--acp-items", str(invalid_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "authority-required" for diagnostic in payload["diagnostics"])


def test_acp_composition_staging_detects_stale_outputs(tmp_path: Path) -> None:
    stale_items = tmp_path / "items.jsonl"
    stale_edges = tmp_path / "edges.jsonl"
    stale_report = tmp_path / "report.json"
    stale_items.write_text("{}\n", encoding="utf-8")
    stale_edges.write_text("{}\n", encoding="utf-8")
    stale_report.write_text("{}\n", encoding="utf-8")

    result = run_builder(
        "--items-output",
        str(stale_items),
        "--edges-output",
        str(stale_edges),
        "--report-output",
        str(stale_report),
        "--check",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert sum(1 for diagnostic in payload["diagnostics"] if diagnostic["rule"] == "stale-output") == 3


def test_acp_composition_staging_refuses_canonical_output_paths() -> None:
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_builder("--items-output", str(CANONICAL_ITEMS), "--edges-output", str(EDGES_OUTPUT))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "refusing to write canonical architecture registry file" in payload["message"]
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges
