from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export-acp-architecture-projection.py"
OUTPUT = ROOT / "prd/architecture/acp/derived/architecture-projection.preview.json"
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"


def run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXPORTER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


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
