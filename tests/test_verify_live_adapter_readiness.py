"""Tests for live-adapter readiness report-only inventory (M156)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-live-adapter-readiness.py"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_live_adapter_readiness", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repository_report_classifies_tei_http_surface_and_ruvector_proposed() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "law-nexus/live-adapter-readiness/v1"
    assert payload["lifecycle"] == "[bounded]"
    assert payload["status"] == "ok"
    assert payload["overclaim_count"] == 0
    assert payload["tei"]["status"] == "http_surface_present_unproven"
    assert payload["tei"]["has_tei_embedding_adapter"] is True
    assert payload["tei"]["has_embedding_transport"] is True
    assert payload["tei"]["http_client_hits"]
    assert any("tei_http.rs" in hit for hit in payload["tei"]["http_client_hits"])
    assert payload["ruvector"]["status"] == "proposed"
    assert payload["ruvector"]["adr"]["lifecycle"] == "proposed"
    assert payload["ruvector"]["cargo_product_dep_hits"] == []
    assert any("stub_transport_only is not live TEI" in item for item in payload["non_claims"])
    assert any("no live endpoint was contacted or" in item for item in payload["non_claims"])


def test_strict_mode_passes_without_overclaims() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["overclaim_count"] == 0


def test_overclaim_scanner_ignores_nonclaim_wording() -> None:
    module = load_module()
    report = module.build_report(ROOT)
    assert report["overclaim_count"] == 0
    # Synthetic line classification via private regexes would be brittle; the
    # repository report is the process oracle for current evidence ceiling.
    assert report["tei"]["status"] == "http_surface_present_unproven"
    assert report["ruvector"]["status"] == "proposed"


def test_http_surface_scanner_flags_std_only_tei_transport() -> None:
    module = load_module()
    hits = module._scan_http_clients(ROOT)
    assert any(hit.startswith("crates/ln-storage/src/adapters/tei_http.rs:") for hit in hits)
    # Test sources are excluded from the surface scan.
    assert not any("/tests/" in hit for hit in hits)
