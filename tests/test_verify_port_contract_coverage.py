"""Tests for InMemory port-contract coverage inventory (M146)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-port-contract-coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_port_contract_coverage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_declared_covered_set_matches_current_testkit_surface() -> None:
    module = load_module()
    assert module.COVERED_INMEMORY_ADAPTERS == {
        "InMemoryVectorStore",
        "InMemoryGraphStore",
        "InMemoryCitationSource",
        "InMemoryPromotionStore",
        "InMemoryQueryState",
    }


def test_repository_report_lists_covered_and_uncovered() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "law-nexus/port-contract-coverage/v1"
    assert payload["lifecycle"] == "[bounded]"
    covered = {item["adapter"] for item in payload["covered"]}
    assert covered == {
        "InMemoryVectorStore",
        "InMemoryGraphStore",
        "InMemoryCitationSource",
        "InMemoryPromotionStore",
        "InMemoryQueryState",
    }
    assert payload["covered_count"] == 5
    assert payload["uncovered_count"] > 0
    assert payload["status"] == "debt"
    uncovered = {item["adapter"] for item in payload["uncovered"]}
    assert "InMemoryInventoryStore" in uncovered
    assert "InMemoryQueryState" not in uncovered


def test_strict_mode_fails_while_debt_remains() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["uncovered_count"] > 0


def test_discover_inmemory_adapters_finds_storage_and_citation() -> None:
    module = load_module()
    found = module.discover_inmemory_adapters()
    assert "InMemoryVectorStore" in found
    assert "InMemoryCitationSource" in found
    assert "InMemoryPromotionStore" in found
    assert "InMemoryQueryState" in found
