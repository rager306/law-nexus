"""Tests for hostile shared-negative suite inventory (M152)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-hostile-negative-suite-coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_hostile_negative_suite_coverage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_report_lists_hostiles_with_and_without_shared_negatives() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "law-nexus/hostile-negative-suite-coverage/v1"
    assert payload["lifecycle"] == "[bounded]"
    assert payload["identity_model"] == "crate-qualified"
    assert payload["discovered_count"] == 14
    assert payload["with_shared_negative_count"] == 10
    assert payload["missing_shared_negative_count"] == 4
    assert payload["status"] == "debt"
    missing = {item["identity"] for item in payload["missing_shared_negative"]}
    covered = {item["identity"] for item in payload["with_shared_negative"]}
    assert "ln-publish::HostileDualWriterLedger" in covered
    assert "ln-relation::OpenRelationHostileRegistry" in covered
    assert "ln-admission::HostileVendorCapacity" in missing
    assert "ln-work::HostileMutatingEvidence" in missing
    assert "ln-citation::HostileMirrorRelabeler" in covered
    assert "ln-replay::HostileDuplicateEffectLedger" in covered


def test_strict_mode_fails_while_gaps_remain() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["missing_shared_negative_count"] > 0


def test_discover_finds_crate_qualified_hostile_identities() -> None:
    module = load_module()
    found = module.discover_hostile_adapters()
    assert "ln-gate::InPlaceMutatingHostileStore" in found
    assert "ln-publish::HostileDualWriterLedger" in found
    assert found["ln-citation::HostileMirrorRelabeler"]["crate"] == "ln-citation"
