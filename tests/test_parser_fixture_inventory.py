from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/inventory-parser-fixtures.py"

_OFFICE_NS = "urn:schemas-microsoft-com:office:office"
_WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"


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


def write_consultant_xml(path: Path, *, title: str) -> None:
    """Write a minimal Consultant WordML XML with the given <o:Title> text."""
    path.parent.mkdir(parents=True, exist_ok=True)
    xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:wordDocument xmlns:w="{_WORDML_NS}" xmlns:o="{_OFFICE_NS}">'
        f'<o:DocumentProperties>'
        f'<o:Title>{title}</o:Title>'
        f'<o:Company>Версия 4025.00.30</o:Company>'
        f'</o:DocumentProperties>'
        f'<w:body/>'
        f'</w:wordDocument>'
    )
    path.write_text(xml, encoding="utf-8")


def test_build_inventory_discovers_all_fixtures(tmp_path: Path) -> None:
    """Discovery: every *.xml under consultant/ + every *.odt under garant/ is found."""
    module = load_inventory_module()
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt", content_root="fz44")
    write_minimal_odt(tmp_path / "law-source/garant/PP_60_27-01-2022.odt", content_root="pp60")
    write_consultant_xml(tmp_path / "law-source/consultant/Список документов (5).xml", title="Список документов (5)")
    write_consultant_xml(tmp_path / "law-source/consultant/44-FZ-2026.xml", title="Федеральный закон от 05.04.2013 N 44-ФЗ")

    manifest = module.build_inventory(tmp_path)

    paths = {fixture["path"] for fixture in manifest["fixtures"]}
    assert paths == {
        "law-source/garant/44-fz.odt",
        "law-source/garant/PP_60_27-01-2022.odt",
        "law-source/consultant/Список документов (5).xml",
        "law-source/consultant/44-FZ-2026.xml",
    }
    assert manifest["fixture_count"] == 4
    assert manifest["status"] == "pass"
    assert manifest["duplicate_check"]["duplicate_absent"] is True
    assert manifest["non_authoritative"] is True
    assert manifest["schema_version"] == "parser-source-fixture-inventory/v2"
    assert "law-source/consultant/Список документов (5).xml" in manifest["canonical_paths"]
    assert "law-source/consultant/44-FZ-2026.xml" in manifest["canonical_paths"]
    hygiene = manifest["fixture_hygiene"]
    assert hygiene["pp_filename_mismatch"]["canonical_path"] == "law-source/garant/PP_60_27-01-2022.odt"
    assert hygiene["pp_filename_mismatch"]["stated_path"] == "law-source/garant/PP_60_27-02-2022.odt"
    assert hygiene["pp_filename_mismatch"]["mismatch_visible"] is True
    assert hygiene["pp_filename_mismatch"]["stated_exists"] is False
    assert hygiene["unexpected_duplicate_paths"] == []
    assert hygiene["internal_duplicate_pairs"] == []
    odt = next(f for f in manifest["fixtures"] if f["path"].endswith(".odt"))
    assert odt["odt_shape"]["zip_valid"] is True
    assert odt["odt_shape"]["required_members_present"] is True
    assert odt["document_type"] == "odt_document"
    relation = next(f for f in manifest["fixtures"] if f["path"] == "law-source/consultant/Список документов (5).xml")
    assert relation["source_role"] == "document-list-prior-art"
    assert relation["document_type"] == "document_list"
    assert relation["xml_shape"]["well_formed"] is True
    full_act = next(f for f in manifest["fixtures"] if f["path"] == "law-source/consultant/44-FZ-2026.xml")
    assert full_act["source_role"] == "full-normative-act"
    assert full_act["document_type"] == "federal_law"
    assert full_act["xml_shape"]["well_formed"] is True
    assert full_act["xml_shape"]["root_local_name"] == "wordDocument"
    assert full_act["title_first_line"].startswith("Федеральный закон")


def test_build_inventory_classifies_first_line_title_patterns(tmp_path: Path) -> None:
    """Pattern matchers map observed first-line titles to the v2 taxonomy."""
    module = load_inventory_module()
    cases = [
        ("law-source/consultant/federal-law.xml", "Федеральный закон от 05.04.2013 N 44-ФЗ", "federal_law"),
        ("law-source/consultant/code.xml", "Бюджетный кодекс Российской Федерации", "code"),
        ("law-source/consultant/code-amendment.xml", "Обзор изменений Гражданского кодекса Российской Федерации", "code_amendment_overview"),
        ("law-source/consultant/court-practice.xml", "Обзор судебной практики Верховного Суда Российской Федерации", "court_practice_review"),
        ("law-source/consultant/fas-review.xml", "Обзор недостатков и нарушений, выявленных Федеральным казначейством", "fas_review"),
        ("law-source/consultant/gov-resolution.xml", "Постановление Правительства РФ от 29.12.2021 N 2571", "government_resolution"),
        ("law-source/consultant/ks-postanovlenie.xml", "Постановление Конституционного Суда РФ от 18.03.2021 N 7-П", "constitutional_court_ruling"),
        ("law-source/consultant/ks-opredelenie.xml", "Определение Конституционного Суда РФ от 30.10.2025 N 2837-О", "constitutional_court_ruling"),
        ("law-source/consultant/vs-postanovlenie.xml", "Постановление Верховного Суда РФ от 09.10.2025 N 38-АД25-9-К", "supreme_court_ruling"),
        ("law-source/consultant/vs-opredelenie.xml", "Определение Верховного Суда РФ от 05.12.2025 N 310-ЭС21-2741", "supreme_court_ruling"),
        ("law-source/consultant/lower-court.xml", "Постановление Девятого кассационного суда общей юрисдикции", "lower_court_ruling"),
        ("law-source/consultant/fas-order.xml", "Приказ ФАС России от 25.05.2012 N 339", "antimonopoly_decision"),
        ("law-source/consultant/fas-decision.xml", "Решение ФАС России от 06.11.2025 по делу N 28_06_105-4409_20", "antimonopoly_decision"),
        ("law-source/consultant/doc-list.xml", "Список документов (5)", "document_list"),
        ("law-source/consultant/list-related.xml", "List-44-FZ-connected documents", "list_related"),
    ]
    for path, title, _expected in cases:
        write_consultant_xml(tmp_path / path, title=title)
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")

    manifest = module.build_inventory(tmp_path)

    fixtures_by_path = {f["path"]: f for f in manifest["fixtures"]}
    for path, _title, expected in cases:
        actual = fixtures_by_path[path]["document_type"]
        assert actual == expected, f"{path}: expected={expected} actual={actual}"


def test_build_inventory_surfaces_internal_duplicate_pairs(tmp_path: Path) -> None:
    """Two tracked fixtures with the same SHA-256 are reported, not failed."""
    module = load_inventory_module()
    # Two files with byte-identical content (regardless of filename) -> same SHA-256.
    identical_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:wordDocument xmlns:w="{_WORDML_NS}" xmlns:o="{_OFFICE_NS}">'
        f'<o:DocumentProperties><o:Title>Идентичные байты</o:Title></o:DocumentProperties>'
        f'</w:wordDocument>'
    )
    for path in ("law-source/consultant/orig.xml", "law-source/consultant/dup.xml"):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(identical_xml, encoding="utf-8")
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "pass"
    pairs = manifest["fixture_hygiene"]["internal_duplicate_pairs"]
    assert len(pairs) == 1
    pair = pairs[0]
    assert sorted([pair[0], pair[1]]) == sorted([
        "law-source/consultant/orig.xml",
        "law-source/consultant/dup.xml",
    ])


def test_build_inventory_falls_through_to_other_document(tmp_path: Path) -> None:
    """A Consultant XML whose title matches no pattern gets other_document."""
    module = load_inventory_module()
    write_consultant_xml(tmp_path / "law-source/consultant/unknown.xml", title="Какой-то неизвестный тип документа 2025")
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "pass"
    fixture = next(f for f in manifest["fixtures"] if f["path"].endswith("unknown.xml"))
    assert fixture["document_type"] == "other_document"


def test_build_inventory_fails_when_removed_duplicate_reappears(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")
    write_minimal_odt(tmp_path / "law-source/garant/PP_60_27-01-2022.odt")
    write_consultant_xml(tmp_path / "law-source/consultant/Список документов (5).xml", title="Список документов (5)")
    write_consultant_xml(tmp_path / "law-source/consultant/44-FZ-2026.xml", title="Федеральный закон от 05.04.2013 N 44-ФЗ")
    duplicate = tmp_path / "law-source/Список документов (5).xml"
    duplicate.write_text("<wordDocument />", encoding="utf-8")

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "fail"
    assert manifest["duplicate_check"]["duplicate_absent"] is False
    assert manifest["fixture_hygiene"]["removed_duplicate_status"]["absent"] is False
    assert "law-source/Список документов (5).xml" in manifest["fixture_hygiene"]["unexpected_duplicate_paths"]


def test_build_inventory_fails_when_stated_pp_mismatch_path_reappears(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")
    write_minimal_odt(tmp_path / "law-source/garant/PP_60_27-01-2022.odt")
    write_minimal_odt(tmp_path / "law-source/garant/PP_60_27-02-2022.odt")
    write_consultant_xml(tmp_path / "law-source/consultant/Список документов (5).xml", title="Список документов (5)")
    write_consultant_xml(tmp_path / "law-source/consultant/44-FZ-2026.xml", title="Федеральный закон от 05.04.2013 N 44-ФЗ")

    manifest = module.build_inventory(tmp_path)

    assert manifest["status"] == "fail"
    mismatch = manifest["fixture_hygiene"]["pp_filename_mismatch"]
    assert mismatch["observed_path"] == "law-source/garant/PP_60_27-01-2022.odt"
    assert mismatch["stated_path"] == "law-source/garant/PP_60_27-02-2022.odt"
    assert mismatch["stated_exists"] is True
    assert "law-source/garant/PP_60_27-02-2022.odt" in manifest["fixture_hygiene"]["unexpected_duplicate_paths"]


def test_check_outputs_detects_stale_artifacts(tmp_path: Path) -> None:
    module = load_inventory_module()
    write_minimal_odt(tmp_path / "law-source/garant/44-fz.odt")
    write_minimal_odt(tmp_path / "law-source/garant/PP_60_27-01-2022.odt")
    write_consultant_xml(tmp_path / "law-source/consultant/Список документов (5).xml", title="Список документов (5)")
    write_consultant_xml(tmp_path / "law-source/consultant/44-FZ-2026.xml", title="Федеральный закон от 05.04.2013 N 44-ФЗ")
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
    # v2 contract: discovery-based fixture_count >= 50 (current real corpus is 53).
    assert summary["fixture_count"] >= 50, summary["fixture_count"]
    # internal_duplicate_pairs field is always present (may be empty).
    assert isinstance(summary["internal_duplicate_pairs"], list)
    markdown = (ROOT / "prd/parser/source_fixture_inventory.md").read_text(encoding="utf-8")
    assert "This inventory does not claim parser completeness." in markdown
    assert "This inventory does not claim legal correctness" in markdown
    assert "Consultant document-list WordML XML is classified only as a relation fixture" in markdown
    assert "Consultant full-act WordML XML is the M009 primary source fixture" in markdown
    assert "Garant ODT work is lower-priority/deferred from M009" in markdown
    assert "law-source/consultant/44-FZ-2026.xml" in markdown
    assert "full-normative-act" in markdown
    assert "## Fixture hygiene" in markdown
    assert "PP_60_27-02-2022.odt" in markdown
    assert "PP_60_27-01-2022.odt" in markdown
    # M072 v2 additions: schema, document-type taxonomy, role coverage.
    assert "parser-source-fixture-inventory/v2" in markdown
    assert "Document-type taxonomy (v2)" in markdown
    assert "Role coverage by document_type" in markdown
    # M072 non-claim: classification is NOT a parser assertion.
    assert "NOT a parser assertion" in markdown
    readme = (ROOT / "prd/parser/README.md").read_text(encoding="utf-8")
    assert "uv run python scripts/inventory-parser-fixtures.py --check" in readme
    assert "law-source/consultant/Список документов (5).xml" in readme
    assert "law-source/Список документов (5).xml" in readme
    assert "does not claim parser completeness" in readme
    assert "legal correctness" in readme
    assert "Consultant Plus WordML as the primary source contract" in readme
    assert "Garant ODT work is lower-priority/deferred from M009" in readme
    assert "multi-source parser readiness" in readme
    # M072 README additions
    assert "Source discovery and document-type taxonomy (M072)" in readme
    assert "parser-source-fixture-inventory/v2" in readme
