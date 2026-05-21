from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export-acp-recovery-view.py"
OUTPUT = ROOT / "prd/architecture/acp/derived/recovery-view.json"


def run_exporter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXPORTER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_acp_recovery_export_is_current() -> None:
    result = run_exporter("--check")

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["message"] == "output file is current"
    assert payload["output"] == "prd/architecture/acp/derived/recovery-view.json"


def test_acp_recovery_view_shape_is_source_linked() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))

    assert payload["kind"] == "acp_recovery_view"
    assert payload["boundary"] == "Derived recovery view only; ACP source records remain authoritative."
    assert payload["validation"] == {"diagnostic_count": 0, "record_count": 5, "status": "ok"}
    assert {record["id"] for record in payload["records"]} == {
        "APR-0001",
        "AP-0001",
        "DC-0001",
        "PG-0001",
        "AHF-0001",
    }
    assert all(record["path"].startswith("prd/architecture/acp/fixtures/minimal-chain/") for record in payload["records"])
    assert any(edge == {"source": "DC-0001", "target": "PG-0001", "relationship": "requiresProof"} for edge in payload["edges"])
    assert any(action["blocked_by"] == "PG-0001" for action in payload["blocked_actions"])
    assert any("S02 validator/exporter" in action for action in payload["allowed_next_actions"])


def test_acp_recovery_export_detects_stale_output(tmp_path: Path) -> None:
    stale = tmp_path / "recovery-view.json"
    stale.write_text("{}\n", encoding="utf-8")

    result = run_exporter("--output", str(stale), "--check")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["message"] == "output file is stale"
