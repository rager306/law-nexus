"""Tests for workspace crate-dependency allowlist checker (ADR-0015 follow-on)."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify-crate-dependency-allowlist.py"
ALLOWLIST = ROOT / "prd" / "architecture" / "crate-dependency-allowlist.json"


def load_module():
    spec = importlib.util.spec_from_file_location("verify_crate_dependency_allowlist", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_allowlist_file_matches_current_workspace_edges() -> None:
    module = load_module()
    allowlist = module.load_allowlist(ALLOWLIST)
    observed = module.workspace_path_edges(ROOT)
    assert observed == allowlist["_allowed_set"]
    assert len(observed) == 26


def test_current_repository_passes_cli() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["finding_count"] == 0
    assert payload["observed_edge_count"] == 26


def test_undeclared_edge_is_reported() -> None:
    module = load_module()
    allowlist = module.load_allowlist(ALLOWLIST)
    observed = set(allowlist["_allowed_set"])
    observed.add(("ln-decode", "ln-product-cli"))
    findings = module.evaluate_edges(observed, allowlist)
    codes = {f["code"] for f in findings}
    assert "UNDECLARED_WORKSPACE_EDGE" in codes
    assert any("ln-decode -> ln-product-cli" in f["message"] for f in findings)


def test_missing_declared_edge_is_reported() -> None:
    module = load_module()
    allowlist = module.load_allowlist(ALLOWLIST)
    observed = set(allowlist["_allowed_set"])
    observed.remove(("ln-query", "ln-storage"))
    findings = module.evaluate_edges(observed, allowlist)
    assert any(f["code"] == "MISSING_DECLARED_EDGE" for f in findings)


def test_capability_depending_on_hc_runner_is_forbidden() -> None:
    module = load_module()
    allowlist = module.load_allowlist(ALLOWLIST)
    observed = set(allowlist["_allowed_set"])
    observed.add(("ln-decode", "ln-hc05-runner"))
    findings = module.evaluate_edges(observed, allowlist)
    assert any(f["code"] == "CAPABILITY_DEPENDS_ON_HC_RUNNER" for f in findings)


def test_capability_depending_on_product_cli_is_forbidden() -> None:
    module = load_module()
    allowlist = module.load_allowlist(ALLOWLIST)
    observed = set(allowlist["_allowed_set"])
    observed.add(("ln-storage", "ln-product-cli"))
    findings = module.evaluate_edges(observed, allowlist)
    assert any(f["code"] == "CAPABILITY_DEPENDS_ON_PRODUCT_CLI" for f in findings)
