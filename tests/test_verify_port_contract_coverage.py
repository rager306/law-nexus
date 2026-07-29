"""Tests for crate-qualified InMemory port-contract coverage inventory (M148)."""

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


def test_declared_covered_set_is_crate_qualified() -> None:
    module = load_module()
    assert module.COVERED_INMEMORY_ADAPTERS == {
        "ln-storage::InMemoryVectorStore",
        "ln-storage::InMemoryGraphStore",
        "ln-citation::InMemoryCitationSource",
        "ln-promote::InMemoryPromotionStore",
        "ln-query::InMemoryQueryState",
        "ln-publish::InMemoryPublicationLedger",
        "ln-decode::InMemoryDiagnosticSink",
        "ln-observe::InMemoryWorkState",
        "ln-observe::InMemoryDiagnosticSink",
        "ln-diagnostic::InMemoryDiagnosticSink",
        "ln-inventory::InMemoryInventoryStore",
        "ln-inventory::InMemoryVisibilityView",
    }
    assert module.SCHEMA_VERSION == "law-nexus/port-contract-coverage/v2"


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
    assert payload["schema_version"] == "law-nexus/port-contract-coverage/v2"
    assert payload["lifecycle"] == "[bounded]"
    assert payload["identity_model"] == "crate-qualified"
    covered = {item["identity"] for item in payload["covered"]}
    assert covered == {
        "ln-storage::InMemoryVectorStore",
        "ln-storage::InMemoryGraphStore",
        "ln-citation::InMemoryCitationSource",
        "ln-promote::InMemoryPromotionStore",
        "ln-query::InMemoryQueryState",
        "ln-publish::InMemoryPublicationLedger",
        "ln-decode::InMemoryDiagnosticSink",
        "ln-observe::InMemoryWorkState",
        "ln-observe::InMemoryDiagnosticSink",
        "ln-diagnostic::InMemoryDiagnosticSink",
        "ln-inventory::InMemoryInventoryStore",
        "ln-inventory::InMemoryVisibilityView",
    }
    assert payload["covered_count"] == 12
    assert payload["uncovered_count"] > 0
    assert payload["status"] == "debt"
    uncovered = {item["identity"] for item in payload["uncovered"]}
    assert "ln-inventory::InMemoryInventoryStore" not in uncovered
    assert "ln-gate::InMemoryCandidateStore" in uncovered
    assert "ln-query::InMemoryQueryState" not in uncovered
    assert "ln-publish::InMemoryPublicationLedger" not in uncovered
    assert "ln-decode::InMemoryDiagnosticSink" not in uncovered
    assert "ln-observe::InMemoryWorkState" not in uncovered
    assert "ln-diagnostic::InMemoryDiagnosticSink" not in uncovered


def test_same_named_adapters_in_different_crates_are_distinct() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    identities = {item["identity"] for item in payload["covered"] + payload["uncovered"]}
    diagnostic_sinks = {
        "ln-decode::InMemoryDiagnosticSink",
        "ln-diagnostic::InMemoryDiagnosticSink",
        "ln-observe::InMemoryDiagnosticSink",
    }
    assert diagnostic_sinks <= identities
    assert payload["discovered_count"] == 22
    assert payload["uncovered_count"] == 10
    covered_ids = {item["identity"] for item in payload["covered"]}
    assert diagnostic_sinks <= covered_ids
    assert "ln-inventory::InMemoryInventoryStore" in covered_ids
    assert "ln-inventory::InMemoryVisibilityView" in covered_ids


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


def test_discover_inmemory_adapters_uses_crate_qualified_keys() -> None:
    module = load_module()
    found = module.discover_inmemory_adapters()
    assert "ln-storage::InMemoryVectorStore" in found
    assert "ln-citation::InMemoryCitationSource" in found
    assert "ln-promote::InMemoryPromotionStore" in found
    assert "ln-query::InMemoryQueryState" in found
    assert "ln-publish::InMemoryPublicationLedger" in found
    assert "ln-decode::InMemoryDiagnosticSink" in found
    assert "ln-observe::InMemoryWorkState" in found
    assert "ln-diagnostic::InMemoryDiagnosticSink" in found
    assert found["ln-decode::InMemoryDiagnosticSink"]["crate"] == "ln-decode"
    assert found["ln-observe::InMemoryDiagnosticSink"]["adapter"] == "InMemoryDiagnosticSink"
