from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/build-acp-canonical-integration.py"
ITEMS_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration.items.jsonl"
EDGES_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration.edges.jsonl"
REPORT_OUTPUT = ROOT / "prd/architecture/acp/derived/canonical-integration-report.json"
GRAPH_REPORT_JSON = ROOT / "prd/architecture/acp/derived/canonical-integration-graph-report.json"
GRAPH_REPORT_MD = ROOT / "prd/architecture/acp/derived/canonical-integration-graph-report.md"
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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )


def load_schema_test_module():
    spec = importlib.util.spec_from_file_location("architecture_registry_schema_tests", SCHEMA_TESTS)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def temp_output_args(tmp_path: Path) -> list[str]:
    return [
        "--items-output",
        str(tmp_path / "items.jsonl"),
        "--edges-output",
        str(tmp_path / "edges.jsonl"),
        "--report-output",
        str(tmp_path / "report.json"),
        "--graph-report-json",
        str(tmp_path / "graph.json"),
        "--graph-report-md",
        str(tmp_path / "graph.md"),
    ]


def run_with_temp_outputs(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_builder(*args, *temp_output_args(tmp_path))


def test_acp_canonical_integration_enabled_outputs_are_current() -> None:
    result = run_builder("--include-acp", "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["mode"] == "enabled"
    assert payload["owner"] == "opt-in architecture-build composition"
    assert payload["diagnostic_count"] == 0
    assert payload["record_counts"] == {
        "canonical_item_count": 58,
        "canonical_edge_count": 91,
        "acp_item_count": 5,
        "acp_edge_count": 7,
        "integration_item_count": 63,
        "integration_edge_count": 98,
    }
    assert payload["graph_summary"]["nodes"] == 63
    assert payload["graph_summary"]["edges"] == 98
    assert payload["graph_summary"]["mode"] == "custom"


def test_acp_canonical_integration_disabled_mode_omits_acp_rows(tmp_path: Path) -> None:
    write_result = run_with_temp_outputs(tmp_path)
    check_result = run_with_temp_outputs(tmp_path, "--check")

    assert write_result.returncode == 0, write_result.stdout + write_result.stderr
    assert check_result.returncode == 0, check_result.stdout + check_result.stderr
    payload = json.loads(check_result.stdout)
    assert payload["mode"] == "disabled"
    assert payload["record_counts"]["acp_item_count"] == 0
    assert payload["record_counts"]["acp_edge_count"] == 0
    assert payload["record_counts"]["integration_item_count"] == 58
    assert payload["record_counts"]["integration_edge_count"] == 91


def test_acp_canonical_integration_records_validate_against_schema() -> None:
    schema_tests = load_schema_test_module()
    schema = schema_tests.load_schema()
    records = [*schema_tests.load_jsonl(ITEMS_OUTPUT), *schema_tests.load_jsonl(EDGES_OUTPUT)]

    errors = schema_tests.validate_schema_records(records, schema)

    assert not errors, schema_tests.format_errors(errors)


def test_acp_canonical_integration_report_is_safe() -> None:
    report_text = REPORT_OUTPUT.read_text(encoding="utf-8")
    report = json.loads(report_text)

    assert report["status"] == "ok"
    assert report["mode"] == "enabled"
    assert report["graph_summary"]["report_json"] == "prd/architecture/acp/derived/canonical-integration-graph-report.json"
    assert report["graph_summary"]["report_md"] == "prd/architecture/acp/derived/canonical-integration-graph-report.md"
    assert "/root/" not in report_text
    assert ".gsd/exec" not in report_text
    assert "sk-" not in report_text


def test_acp_canonical_integration_graph_outputs_exist() -> None:
    assert GRAPH_REPORT_JSON.exists()
    assert GRAPH_REPORT_MD.exists()
    graph_report = json.loads(GRAPH_REPORT_JSON.read_text(encoding="utf-8"))
    assert graph_report["counts"] == {"nodes": 63, "edges": 98}


def test_acp_canonical_integration_detects_stale_outputs(tmp_path: Path) -> None:
    for name in ("items.jsonl", "edges.jsonl", "report.json", "graph.json", "graph.md"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")

    result = run_builder("--include-acp", *temp_output_args(tmp_path), "--check")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "stale-output" for diagnostic in payload["diagnostics"])


def test_acp_canonical_integration_rejects_duplicate_ids(tmp_path: Path) -> None:
    duplicate_items = tmp_path / "acp-items.jsonl"
    duplicate_edges = tmp_path / "acp-edges.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["id"] = load_jsonl(CANONICAL_ITEMS)[0]["id"]
    write_jsonl(duplicate_items, acp_records)
    duplicate_edges.write_text(ACP_EDGES.read_text(encoding="utf-8"), encoding="utf-8")

    result = run_with_temp_outputs(tmp_path, "--include-acp", "--acp-items", str(duplicate_items), "--acp-edges", str(duplicate_edges))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "duplicate-id" for diagnostic in payload["diagnostics"])


def test_acp_canonical_integration_rejects_broken_endpoint(tmp_path: Path) -> None:
    broken_edges = tmp_path / "acp-edges.jsonl"
    edge_records = load_jsonl(ACP_EDGES)
    edge_records[0]["to"] = "ACP-MISSING"
    write_jsonl(broken_edges, edge_records)

    result = run_with_temp_outputs(tmp_path, "--include-acp", "--acp-edges", str(broken_edges))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "edge-endpoint" for diagnostic in payload["diagnostics"])


def test_acp_canonical_integration_rejects_missing_non_claim(tmp_path: Path) -> None:
    invalid_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    acp_records[0]["non_claims"] = [claim for claim in acp_records[0]["non_claims"] if claim != "Does not validate R035."]
    write_jsonl(invalid_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--include-acp", "--acp-items", str(invalid_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "acp-non-claims" for diagnostic in payload["diagnostics"])


def test_acp_canonical_integration_rejects_missing_authority_requirement(tmp_path: Path) -> None:
    invalid_items = tmp_path / "acp-items.jsonl"
    acp_records = load_jsonl(ACP_ITEMS)
    for record in acp_records:
        if record["type"] == "decision_candidate":
            record["authority_required"] = False
    write_jsonl(invalid_items, acp_records)

    result = run_with_temp_outputs(tmp_path, "--include-acp", "--acp-items", str(invalid_items))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert any(diagnostic["rule"] == "authority-required" for diagnostic in payload["diagnostics"])


def test_acp_canonical_integration_refuses_canonical_output_paths() -> None:
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_builder("--include-acp", "--items-output", str(CANONICAL_ITEMS), "--edges-output", str(EDGES_OUTPUT))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "refusing to write canonical architecture registry file" in payload["message"]
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges
