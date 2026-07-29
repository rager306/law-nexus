from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "prd" / "architecture" / "parser-source-cli-compatibility.md"


def _matrix_text() -> str:
    return MATRIX.read_text(encoding="utf-8")


def test_matrix_lists_existing_parser_source_scripts() -> None:
    text = _matrix_text()
    script_paths = sorted(set(re.findall(r"`(scripts/[^`]+\.py)(?: [^`]*)?`", text)))
    assert script_paths, "matrix must list parser/source script paths"

    missing = [path for path in script_paths if not (ROOT / path).is_file()]
    assert missing == []


def test_matrix_records_touched_wrapper_commands_and_package_seams() -> None:
    text = _matrix_text()

    required = [
        "scripts/inventory-parser-fixtures.py --check",
        "ParserInventoryUseCase",
        "FilesystemParserFixtureInventory",
        "scripts/build-consultant-hierarchy-records.py",
        "SourceHierarchyUseCase",
        "ConsultantHierarchyRecordBuilder",
        "make_consultant_hierarchy_use_case()",
        "src/law_nexus/adapters/parsers/consultant_wordml.py",
        "ConsultantWordMLParser",
    ]
    missing = [entry for entry in required if entry not in text]
    assert missing == []


def test_matrix_preserves_known_debt_and_non_claims() -> None:
    text = _matrix_text()

    required = [
        "artifact_freshness: false",
        "currently exits `1`",
        "tests/test_consultant_hierarchy_prior_art_comparison.py",
        "currently `3 failed, 2 passed`",
        "This matrix does not validate Russian legal correctness.",
        "This matrix does not validate Garant ODT parser completeness.",
        "This matrix does not validate FalkorDB import or graph runtime behavior.",
        "This matrix does not retire any script path.",
    ]
    missing = [entry for entry in required if entry not in text]
    assert missing == []


def test_matrix_classifies_parser_records_as_script_owned_contract_module() -> None:
    text = _matrix_text()

    assert "scripts/parser_records.py" in text
    assert "script-owned contract module" in text
    assert "package code must not import it" in text
