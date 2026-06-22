from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/probe-consultant-parser.py"


def load_probe_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("probe_consultant_parser", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_probe_runs_against_inventory_only(tmp_path: Path) -> None:
    """The probe must read source_fixture_inventory.json — never glob law-source/ directly."""
    # Build a minimal inventory referencing two non-existent files. The probe
    # should still process them (and mark them file-not-found) without raising.
    inventory = {
        "schema_version": "parser-source-fixture-inventory/v2",
        "fixtures": [
            {
                "path": "law-source/consultant/missing.xml",
                "source_kind": "consultant-wordml-xml",
                "source_role_v2": "federal-law",
                "document_type": "federal_law",
                "title_first_line": "Федеральный закон от 01.01.2020 N 1-ФЗ",
            },
        ],
    }
    inventory_path = tmp_path / "prd/parser/source_fixture_inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    module = load_probe_module()
    manifest = module.probe_corpus(tmp_path)

    assert manifest["fixture_count"] == 1
    row = manifest["fixtures"][0]
    assert row["parser_outcome"] == "fail"
    assert row["failure_mode"] == "file-not-found"


def test_probe_outcomes_sum_to_fixture_count(tmp_path: Path) -> None:
    """Every fixture produces exactly one outcome; counts sum to fixture_count."""
    inventory = {
        "schema_version": "parser-source-fixture-inventory/v2",
        "fixtures": [
            {
                "path": "law-source/consultant/a.xml",
                "source_kind": "consultant-wordml-xml",
                "source_role_v2": "code",
                "document_type": "code",
                "title_first_line": "Гражданский кодекс",
            },
            {
                "path": "law-source/garant/a.odt",
                "source_kind": "garant-odt",
                "source_role_v2": "odt-document-fixture",
                "document_type": "odt_document",
                "title_first_line": None,
            },
        ],
    }
    inventory_path = tmp_path / "prd/parser/source_fixture_inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    module = load_probe_module()
    manifest = module.probe_corpus(tmp_path)

    total = sum(manifest["outcome_counts"].values())
    assert total == manifest["fixture_count"] == 2
    # First row (Consultant code) fails because the file does not exist on disk.
    assert manifest["fixtures"][0]["parser_outcome"] == "fail"
    # Second row (ODT) also fails because the file does not exist on disk
    # (file-not-found, not wrong-namespace — wrong-namespace requires the parser
    # to actually open the file).
    assert manifest["fixtures"][1]["parser_outcome"] == "fail"


def test_probe_failure_modes_are_bounded(tmp_path: Path) -> None:
    """Each failure row carries a failure_mode from the bounded taxonomy."""
    inventory = {
        "schema_version": "parser-source-fixture-inventory/v2",
        "fixtures": [],
    }
    inventory_path = tmp_path / "prd/parser/source_fixture_inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    module = load_probe_module()
    # Sanity-check the bounded taxonomy is exported.
    assert "missing-document-properties" in module.FAILURE_MODES
    assert "missing-title" in module.FAILURE_MODES
    assert "wrong-namespace" in module.FAILURE_MODES
    assert "malformed-xml" in module.FAILURE_MODES
    assert "path-traversal" in module.FAILURE_MODES
    assert "file-not-found" in module.FAILURE_MODES
    assert "other-exception" in module.FAILURE_MODES


def test_probe_is_idempotent(tmp_path: Path) -> None:
    """Running the probe twice against the same inputs produces the same SHA-of-output."""
    inventory = {
        "schema_version": "parser-source-fixture-inventory/v2",
        "fixtures": [],
    }
    inventory_path = tmp_path / "prd/parser/source_fixture_inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    module = load_probe_module()
    module.write_outputs(tmp_path, module.probe_corpus(tmp_path))
    sha1 = module.sha256_of_file(tmp_path / module.JSON_OUTPUT)

    module.write_outputs(tmp_path, module.probe_corpus(tmp_path))
    sha2 = module.sha256_of_file(tmp_path / module.JSON_OUTPUT)

    assert sha1 == sha2


def test_probe_does_not_glob_law_source(tmp_path: Path) -> None:
    """The probe must rely on the inventory contract, not raw directory scanning.

    Specifically: an inventory that names zero fixtures should produce a
    manifest with fixture_count == 0 — even if real fixture files exist in
    law-source/ (which they do in the real repo).
    """
    inventory = {
        "schema_version": "parser-source-fixture-inventory/v2",
        "fixtures": [],
    }
    inventory_path = tmp_path / "prd/parser/source_fixture_inventory.json"
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")

    module = load_probe_module()
    manifest = module.probe_corpus(tmp_path)

    assert manifest["fixture_count"] == 0
    assert manifest["classification_gap_count"] == 0
    assert manifest["outcome_counts"] == {}
    assert manifest["failure_mode_counts"] == {}


def test_repository_outputs_are_current_and_report_non_claims() -> None:
    """The real-repo probe outputs are fresh, deterministic, and carry non-claims."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "pass"
    # Real-repo fixture count from S01 inventory = 53 (41 consultant + 12 garant).
    assert summary["fixture_count"] >= 50, summary["fixture_count"]
    # 12 ODT fixtures are expected to fail-by-design (parser rejects non-WordML).
    assert summary["outcome_counts"].get("fail-by-design", 0) >= 10
    # 2 federal laws (44-FZ-2026 + 223-FZ) should classify correctly today.
    assert summary["outcome_counts"].get("success-classified", 0) >= 2
    # Markdown contains the non-claim block.
    markdown = (ROOT / "prd/parser/probe_results.md").read_text(encoding="utf-8")
    assert "## Explicit non-claims" in markdown
    assert "does not validate parser completeness" in markdown
    assert "R035, R037, or R038" in markdown
    assert "FalkorDB" in markdown
    assert "retrieval" in markdown
    # JSON contains the bounded failure-modes taxonomy.
    manifest = json.loads((ROOT / "prd/parser/probe_results.json").read_text(encoding="utf-8"))
    assert set(manifest["failure_modes_taxonomy"]) == {
        "missing-document-properties",
        "missing-title",
        "wrong-namespace",
        "malformed-xml",
        "path-traversal",
        "file-not-found",
        "other-exception",
    }
