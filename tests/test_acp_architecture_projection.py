from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export-acp-architecture-projection.py"
OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.preview.json"
CANONICAL_PROJECTION_ITEMS = ROOT / "prd/architecture/acp/derived/canonical-projection.items.jsonl"
CANONICAL_PROJECTION_EDGES = ROOT / "prd/architecture/acp/derived/canonical-projection.edges.jsonl"
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
SCHEMA_TESTS = ROOT / "tests/test_architecture_registry_schema.py"


def run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXPORTER), *args],
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


def test_acp_architecture_projection_is_current() -> None:
    result = run_exporter("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "message": "output file is current",
        "output": "prd/architecture/acp/derived/architecture-projection.preview.json",
        "status": "ok",
    }


def test_acp_architecture_projection_shape_and_boundary() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))

    assert payload["kind"] == "acp_architecture_projection_preview"
    assert payload["boundary"] == "Preview only; canonical architecture registry files are unchanged."
    assert payload["source"] == "prd/architecture/acp/derived/recovery-view.json"
    assert payload["non_mappable"] == []
    assert len(payload["items"]) == 5
    assert len(payload["edges"]) == 7
    assert payload["canonical_registry_files"] == [
        "prd/architecture/architecture_items.jsonl",
        "prd/architecture/architecture_edges.jsonl",
    ]


def test_acp_architecture_projection_items_preserve_non_claims() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    items = {item["source_record_id"]: item for item in payload["items"]}

    assert items["APR-0001"]["suggested_type"] == "evidence"
    assert items["AP-0001"]["suggested_type"] == "viewpoint"
    assert items["DC-0001"]["suggested_type"] == "decision"
    assert items["PG-0001"]["suggested_type"] == "proof_gate"
    assert items["AHF-0001"]["suggested_type"] == "risk"
    for item in items.values():
        assert item["preview_id"].startswith("ACP-PREVIEW-")
        assert item["suggested_layer"] == "architecture-governance"
        assert "Does not validate R035." in item["non_claims"]
        assert "Does not prove FalkorDB ingestion or runtime loading." in item["non_claims"]
        assert item["source_anchors"]


def test_acp_architecture_projection_edges_and_blocked_mutations() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    edges = {(edge["source_preview_id"], edge["target_preview_id"], edge["suggested_edge_type"]) for edge in payload["edges"]}

    assert ("ACP-PREVIEW-DC-0001", "ACP-PREVIEW-PG-0001", "checked_by") in edges
    assert ("ACP-PREVIEW-AHF-0001", "ACP-PREVIEW-DC-0001", "blocks") in edges
    assert "write prd/architecture/architecture_items.jsonl" in payload["blocked_canonical_mutations"]
    assert "write prd/architecture/architecture_edges.jsonl" in payload["blocked_canonical_mutations"]


def test_acp_architecture_projection_detects_stale_output(tmp_path: Path) -> None:
    stale = tmp_path / "projection.json"
    stale.write_text("{}\n", encoding="utf-8")

    result = run_exporter("--output", str(stale), "--check")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["message"] == "output file is stale"


def test_acp_architecture_projection_refuses_canonical_registry_write() -> None:
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_exporter("--output", str(CANONICAL_ITEMS))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "refusing to write canonical architecture registry file" in payload["message"]
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges


def test_acp_canonical_projection_jsonl_is_current() -> None:
    result = run_exporter("--canonical-jsonl", "--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "edges_message": "output file is current",
        "edges_output": "prd/architecture/acp/derived/canonical-projection.edges.jsonl",
        "items_message": "output file is current",
        "items_output": "prd/architecture/acp/derived/canonical-projection.items.jsonl",
        "status": "ok",
    }


def test_acp_canonical_projection_jsonl_shape_and_schema() -> None:
    schema_tests = load_schema_test_module()
    schema = schema_tests.load_schema()
    items = list(schema_tests.load_jsonl(CANONICAL_PROJECTION_ITEMS))
    edges = list(schema_tests.load_jsonl(CANONICAL_PROJECTION_EDGES))

    assert len(items) == 5
    assert len(edges) == 7
    assert {item.record["type"] for item in items} == {
        "decision_candidate",
        "health_finding",
        "prompt_record",
        "proof_gate",
        "proposal",
    }
    assert {edge.record["type"] for edge in edges} >= {
        "produced_proposal",
        "origin_prompt_record",
        "suggested_decision",
        "origin_proposal",
        "requires_proof",
        "blocks",
        "affects",
    }

    errors = schema_tests.validate_schema_records([*items, *edges], schema)

    assert not errors, schema_tests.format_errors(errors)


def test_acp_canonical_projection_preserves_boundaries() -> None:
    items = load_jsonl(CANONICAL_PROJECTION_ITEMS)
    edges = load_jsonl(CANONICAL_PROJECTION_EDGES)
    item_by_id = {item["id"]: item for item in items}

    assert "ACP-APR-0001" in item_by_id
    assert item_by_id["ACP-APR-0001"]["type"] == "prompt_record"
    assert item_by_id["ACP-APR-0001"]["capture_mode"] == "summarized-with-quotes"
    assert item_by_id["ACP-APR-0001"]["redaction_status"] == "checked"
    assert item_by_id["ACP-DC-0001"]["type"] == "decision_candidate"
    assert item_by_id["ACP-DC-0001"]["authority_required"] is True
    assert item_by_id["ACP-AHF-0001"]["type"] == "health_finding"
    assert item_by_id["ACP-AHF-0001"]["blocked_actions"]
    for item in items:
        assert item["record_kind"] == "item"
        assert item["id"].startswith("ACP-")
        assert item["generated_draft"] is True
        assert "Does not validate R035." in item["non_claims"]
        assert "Does not prove FalkorDB ingestion or runtime loading." in item["non_claims"]
    for edge in edges:
        assert edge["record_kind"] == "edge"
        assert edge["id"].startswith("ACP-EDGE-")
        assert edge["from"].startswith("ACP-")
        assert edge["to"].startswith("ACP-")


def test_acp_canonical_projection_detects_stale_outputs(tmp_path: Path) -> None:
    stale_items = tmp_path / "items.jsonl"
    stale_edges = tmp_path / "edges.jsonl"
    stale_items.write_text("{}\n", encoding="utf-8")
    stale_edges.write_text("{}\n", encoding="utf-8")

    result = run_exporter(
        "--canonical-jsonl",
        "--items-output",
        str(stale_items),
        "--edges-output",
        str(stale_edges),
        "--check",
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["items_message"] == "output file is stale"
    assert payload["edges_message"] == "output file is stale"


def test_acp_canonical_projection_refuses_canonical_registry_write() -> None:
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_exporter("--canonical-jsonl", "--items-output", str(CANONICAL_ITEMS))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert "refusing to write canonical architecture registry file" in payload["message"]
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges
