from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/extract-prd-architecture-items.py"
ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"
REQUIRED_ITEM_IDS = {
    "REQ-R001",
    "REQ-R009",
    "REQ-R010",
    "REQ-R017",
    "REQ-R022",
    "REQ-R028",
    "REQ-R029",
    "DEC-D031",
    "DEC-D032",
    "GATE-G005",
    "GATE-G008",
    "GATE-G011",
    "GATE-G015",
    "S07-FIXED-PRD-CONSISTENCY",
    "S04-FALKORDB-RUNTIME-BOUNDED",
    "S05-PARSER-ODT-BOUNDARY",
    "S05-OLD-PROJECT-PRIOR-ART",
    "S10-USER-BGE-M3-BASELINE",
    "S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED",
    "M001-ARCHITECTURE-ONLY-GUARDRAIL",
    "ASSUMP-PRD-SOURCE-TRUTH",
    "RISK-OVERCLAIM-RUNTIME",
    "CHECK-ARCHITECTURE-EXTRACTOR",
}


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_check_mode_matches_generated_outputs_and_required_ids() -> None:
    result = run_cli("--check")

    assert result.returncode == 0, result.stderr
    assert "architecture JSONL outputs are current" in result.stdout

    items = read_jsonl(ITEMS)
    edges = read_jsonl(EDGES)
    item_ids = [str(item["id"]) for item in items]
    edge_ids = [str(edge["id"]) for edge in edges]

    assert REQUIRED_ITEM_IDS <= set(item_ids)
    assert item_ids == sorted(item_ids)
    assert edge_ids == sorted(edge_ids)
    assert ITEMS.read_text(encoding="utf-8").endswith("\n")
    assert EDGES.read_text(encoding="utf-8").endswith("\n")


def test_generated_records_are_conservative_and_anchored() -> None:
    items = read_jsonl(ITEMS)
    edges = read_jsonl(EDGES)

    assert all(item["status"] != "validated" for item in items)

    by_id = {str(item["id"]): item for item in items}
    assert by_id["REQ-R001"]["status"] == "active"
    assert by_id["REQ-R001"]["proof_level"] == "source-anchor"
    assert by_id["GATE-G005"]["proof_level"] == "none"
    assert by_id["GATE-G008"]["proof_level"] == "none"
    assert by_id["S04-FALKORDB-RUNTIME-BOUNDED"]["status"] == "bounded-evidence"
    assert by_id["S10-GIGAEMBEDDINGS-CHALLENGER-BLOCKED"]["status"] == "blocked"
    assert by_id["M001-ARCHITECTURE-ONLY-GUARDRAIL"]["status"] == "out-of-scope"

    non_claim_text = "\n".join(
        claim for item in items for claim in item.get("non_claims", []) if isinstance(claim, str)
    )
    for phrase in [
        "No legal-answer correctness claim.",
        "No product Legal KnowQL behavior claim.",
        "No parser completeness claim.",
        "No product retrieval quality claim.",
        "No managed embedding API fallback claim.",
        "No production-scale FalkorDB claim.",
        "No LLM legal authority claim.",
    ]:
        assert phrase in non_claim_text

    for record in [*items, *edges]:
        for anchor in record["source_anchors"]:
            path = str(anchor["path"])
            assert not path.startswith("/")
            assert not path.startswith(".gsd/exec")
            assert (ROOT / path).exists(), f"{record['id']} anchor missing: {path}"


def test_check_mode_reports_stale_outputs_without_rewriting(tmp_path: Path) -> None:
    item_out = tmp_path / "architecture_items.jsonl"
    edge_out = tmp_path / "architecture_edges.jsonl"
    write_result = run_cli("--items", str(item_out), "--edges", str(edge_out))
    assert write_result.returncode == 0, write_result.stderr

    stale_bytes = item_out.read_text(encoding="utf-8") + "{}\n"
    item_out.write_text(stale_bytes, encoding="utf-8")

    result = run_cli("--items", str(item_out), "--edges", str(edge_out), "--check")

    assert result.returncode != 0
    assert "stale generated output" in result.stderr
    assert str(item_out) in result.stderr
    assert "python scripts/extract-prd-architecture-items.py" in result.stderr
    assert item_out.read_text(encoding="utf-8") == stale_bytes


def test_missing_or_malformed_s08_findings_fail_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing-S08-FINDINGS.json"
    missing_result = run_cli("--s08-findings", str(missing), "--items", str(tmp_path / "i.jsonl"), "--edges", str(tmp_path / "e.jsonl"))
    assert missing_result.returncode != 0
    assert "missing required source" in missing_result.stderr
    assert str(missing) in missing_result.stderr

    malformed = tmp_path / "S08-FINDINGS.json"
    malformed.write_text("{not-json", encoding="utf-8")
    malformed_result = run_cli("--s08-findings", str(malformed), "--items", str(tmp_path / "i2.jsonl"), "--edges", str(tmp_path / "e2.jsonl"))
    assert malformed_result.returncode != 0
    assert "malformed source JSON" in malformed_result.stderr
    assert str(malformed) in malformed_result.stderr
