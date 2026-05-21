from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "prd/architecture/acp/fixtures/minimal-chain"
VALIDATOR = ROOT / "scripts/verify-acp-records.py"


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_acp_fixture_chain_validates() -> None:
    result = run_validator()

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["record_count"] == 5
    assert payload["diagnostic_count"] == 0
    assert set(payload["records"]) == {"APR-0001", "AP-0001", "DC-0001", "PG-0001", "AHF-0001"}
    assert "fixture mechanics only" in payload["boundary"]


def test_acp_validator_rejects_unsafe_fixture(tmp_path: Path) -> None:
    unsafe_dir = tmp_path / "fixtures"
    shutil.copytree(FIXTURE_DIR, unsafe_dir)
    target = unsafe_dir / "APR-0001.md"
    text = target.read_text(encoding="utf-8")
    text = text.replace("claims_r035_validated: false", "claims_r035_validated: true")
    target.write_text(text, encoding="utf-8")

    result = run_validator("--fixture-dir", str(unsafe_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["diagnostic_count"] >= 1
    assert any(
        diagnostic["rule"] == "safety-false" and diagnostic["field"] == "safety.claims_r035_validated"
        for diagnostic in payload["diagnostics"]
    )


def test_acp_validator_rejects_missing_relationship(tmp_path: Path) -> None:
    invalid_dir = tmp_path / "fixtures"
    shutil.copytree(FIXTURE_DIR, invalid_dir)
    (invalid_dir / "PG-0001.md").unlink()

    result = run_validator("--fixture-dir", str(invalid_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    rules = {diagnostic["rule"] for diagnostic in payload["diagnostics"]}
    assert "required-kind" in rules or "record-ref-exists" in rules
