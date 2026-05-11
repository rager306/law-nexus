from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/inventory-parser-fixtures.py"


def load_inventory_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("inventory_parser_fixtures", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_minimal_odt(path: Path, *, content_root: str = "content", meta_root: str = "meta") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", f"<{content_root}><p>body</p><p>tail</p></{content_root}>")
        archive.writestr("meta.xml", f"<{meta_root}><m /></{meta_root}>")


def write_expected_fixture_tree(root: Path) -> None:
    write_minimal_odt(root / "law-source/garant/44-fz.odt")
    write_minimal_odt(root / "law-source/garant/PP_60_27-01-2022.odt")
    xml_path = root / "law-source/consultant/Список документов (5).xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text("<wordDocument><doc /><rels /><tail /></wordDocument>", encoding="utf-8")


def test_build_inventory_records_expected_fixture_shapes(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_expected_fixture_tree(tmp_path)

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "pass"
    assert manifest["fixture_count"] == 3
    assert manifest["duplicate_check"]["duplicate_absent"] is True
    assert manifest["non_authoritative"] is True
    assert "law-source/consultant/Список документов (5).xml" in manifest["canonical_paths"]
    odt = manifest["fixtures"][0]
    assert odt["odt_shape"]["zip_valid"] is True
    assert odt["odt_shape"]["required_members_present"] is True
    assert odt["odt_shape"]["content_xml"]["direct_child_count"] == 2
    xml_fixture = manifest["fixtures"][2]
    assert xml_fixture["xml_shape"]["well_formed"] is True
    assert xml_fixture["xml_shape"]["direct_child_count"] == 3


def test_build_inventory_fails_when_removed_duplicate_reappears(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_expected_fixture_tree(tmp_path)
    duplicate = tmp_path / "law-source/Список документов (5).xml"
    duplicate.write_text("<wordDocument />", encoding="utf-8")

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "fail"
    assert manifest["duplicate_check"]["duplicate_absent"] is False


def test_check_outputs_detects_stale_artifacts(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_expected_fixture_tree(tmp_path)
    manifest = module.build_inventory(tmp_path)
    module.write_outputs(tmp_path, manifest)
    (tmp_path / module.JSON_OUTPUT).write_text("{}\n", encoding="utf-8")

    errors = module.check_outputs(tmp_path, manifest)

    assert any("source_fixture_inventory.json" in error for error in errors)


def test_repository_outputs_are_current_and_report_non_claims() -> None:
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
    assert summary["duplicate_absent"] is True
    assert summary["non_authoritative"] is True
    markdown = (ROOT / "prd/parser/source_fixture_inventory.md").read_text(encoding="utf-8")
    assert "This inventory does not claim parser completeness." in markdown
    assert "This inventory does not claim legal correctness" in markdown
    assert "Consultant WordML XML is classified only as a relation fixture" in markdown
