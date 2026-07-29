"""Tests for multi-adapter real-port shared-suite inventory (M155)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-multi-adapter-port-coverage.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_multi_adapter_port_coverage", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_report_lists_real_multi_adapter_ports_with_shared_suites() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "law-nexus/multi-adapter-port-coverage/v1"
    assert payload["lifecycle"] == "[bounded]"
    assert payload["identity_model"] == "crate-qualified"
    assert payload["multi_adapter_port_count"] >= 3
    assert payload["missing_shared_suite_count"] == 0
    assert payload["status"] == "ok"
    covered = {item["identity"] for item in payload["with_shared_suite"]}
    assert "ln-decode::WordMLStreamingDecoder" in covered
    assert "ln-decode::ConsultantWordMlBlockDecoder" in covered
    assert "ln-decode::GarantOdtBlockDecoder" in covered
    assert "ln-storage::TeiEmbeddingAdapter" in covered


def test_strict_mode_passes_when_no_real_multi_adapter_gaps() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["missing_shared_suite_count"] == 0
    assert payload["status"] == "ok"


def test_is_real_adapter_heuristic() -> None:
    module = load_module()
    assert module.is_real_adapter("WordMLStreamingDecoder") is True
    assert module.is_real_adapter("TeiEmbeddingAdapter") is True
    assert module.is_real_adapter("ConsultantWordMlBlockDecoder") is True
    assert module.is_real_adapter("InMemoryVectorStore") is False
    assert module.is_real_adapter("HostileVendorCapacity") is False
    assert module.is_real_adapter("HonestSyntheticDecoder") is False
    assert module.is_real_adapter("StubEmbedding") is False
    assert module.is_real_adapter("MaliciousSyntheticDecoder") is False
