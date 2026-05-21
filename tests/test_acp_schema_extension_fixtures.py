from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/verify-acp-schema-extension-fixtures.py"
FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/schema-extension"
ITEMS = FIXTURE_DIR / "custom-items.jsonl"
EDGES = FIXTURE_DIR / "custom-edges.jsonl"
NOTES = FIXTURE_DIR / "schema-extension-notes.md"
CANONICAL_SCHEMA = ROOT / "prd/architecture/architecture.schema.json"
CANONICAL_ITEMS = ROOT / "prd/architecture/architecture_items.jsonl"
CANONICAL_EDGES = ROOT / "prd/architecture/architecture_edges.jsonl"


def run_checker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_acp_schema_extension_fixtures_validate() -> None:
    result = run_checker()

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["item_count"] == 5
    assert payload["edge_count"] == 7
    assert payload["diagnostic_count"] == 0
    assert payload["item_types"] == [
        "decision_candidate",
        "health_finding",
        "prompt_record",
        "proof_gate",
        "proposal",
    ]
    assert "canonical architecture registry files are unchanged" in payload["boundary"]


def test_acp_schema_extension_checker_rejects_broken_edge_endpoint(tmp_path: Path) -> None:
    items = tmp_path / "items.jsonl"
    edges = tmp_path / "edges.jsonl"
    notes = tmp_path / "notes.md"
    shutil.copyfile(ITEMS, items)
    shutil.copyfile(EDGES, edges)
    shutil.copyfile(NOTES, notes)

    edge_lines = edges.read_text(encoding="utf-8").splitlines()
    first = json.loads(edge_lines[0])
    first["target"] = "ACP-SCHEMA-MISSING"
    edge_lines[0] = json.dumps(first, ensure_ascii=False, sort_keys=True)
    edges.write_text("\n".join(edge_lines) + "\n", encoding="utf-8")

    result = run_checker("--items", str(items), "--edges", str(edges), "--notes", str(notes))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "edge-endpoint" for diagnostic in payload["diagnostics"])


def test_acp_schema_extension_checker_rejects_candidate_without_authority(tmp_path: Path) -> None:
    items = tmp_path / "items.jsonl"
    edges = tmp_path / "edges.jsonl"
    notes = tmp_path / "notes.md"
    shutil.copyfile(ITEMS, items)
    shutil.copyfile(EDGES, edges)
    shutil.copyfile(NOTES, notes)

    lines = []
    for raw in items.read_text(encoding="utf-8").splitlines():
        record = json.loads(raw)
        if record.get("type") == "decision_candidate":
            record["authority_required"] = False
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    items.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = run_checker("--items", str(items), "--edges", str(edges), "--notes", str(notes))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert any(diagnostic["rule"] == "authority-required" for diagnostic in payload["diagnostics"])


def test_acp_schema_extension_checker_does_not_mutate_canonical_registry() -> None:
    before_schema = CANONICAL_SCHEMA.read_text(encoding="utf-8")
    before_items = CANONICAL_ITEMS.read_text(encoding="utf-8")
    before_edges = CANONICAL_EDGES.read_text(encoding="utf-8")

    result = run_checker()

    assert result.returncode == 0, result.stdout + result.stderr
    assert CANONICAL_SCHEMA.read_text(encoding="utf-8") == before_schema
    assert CANONICAL_ITEMS.read_text(encoding="utf-8") == before_items
    assert CANONICAL_EDGES.read_text(encoding="utf-8") == before_edges
