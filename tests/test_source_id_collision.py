from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from law_nexus.adapters.parsers.consultant_wordml import (
    ConsultantWordMLParser,
    _derive_source_id,
)

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_JSON = ROOT / "prd/parser/source_fixture_inventory.json"

_WORDML_NS = "http://schemas.microsoft.com/office/word/2003/wordml"
_OFFICE_NS = "urn:schemas-microsoft-com:office:office"


def _write_minimal_consultant_xml(path: Path, title: str, body_marker: str = "DEFAULT_BODY") -> None:
    """Write a minimal valid Consultant WordML XML with the given ``<o:Title>``.

    ``body_marker`` is embedded in ``<w:body>`` to make the file content
    distinguishable from other test fixtures that share the same title.
    Two files with the same title and different ``body_marker`` have different
    SHA-256 hashes and therefore different source_id entropy suffixes.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<w:wordDocument xmlns:w="{_WORDML_NS}" xmlns:o="{_OFFICE_NS}">'
        f'<o:DocumentProperties>'
        f'<o:Title>{title}</o:Title>'
        f'<o:Company>Версия 4025.00.30</o:Company>'
        f'</o:DocumentProperties>'
        f'<w:body><w:p>{body_marker}</w:p></w:body>'
        f'</w:wordDocument>'
    )
    path.write_text(xml, encoding="utf-8")


def test_synthetic_collision_two_files_same_act_number(tmp_path: Path) -> None:
    """Two files with the same act number must produce different source_ids.

    Without file-hash entropy, ``_derive_source_id("44-ФЗ", "a.xml", hash)``
    and ``_derive_source_id("44-ФЗ", "b.xml", hash)`` could collide; with
    entropy they are guaranteed distinct.
    """

    a = tmp_path / "first.xml"
    b = tmp_path / "second.xml"
    _write_minimal_consultant_xml(a, "Федеральный закон от 05.04.2013 N 44-ФЗ", body_marker="FIRST_BODY")
    _write_minimal_consultant_xml(b, "Федеральный закон от 05.04.2013 N 44-ФЗ", body_marker="SECOND_BODY")

    parser = ConsultantWordMLParser(source_root=str(tmp_path))
    doc_a, _ = parser.parse(str(a))
    doc_b, _ = parser.parse(str(b))
    assert doc_a.source_id != doc_b.source_id, (
        f"source_id collision: {doc_a.source_id} == {doc_b.source_id}"
    )
    assert doc_a.source_id.startswith("consultant:44-ФЗ-")
    assert doc_b.source_id.startswith("consultant:44-ФЗ-")


def test_synthetic_collision_same_file_parsed_twice_is_deterministic(tmp_path: Path) -> None:
    """Parsing the same file twice must produce the same source_id (idempotent)."""
    a = tmp_path / "same.xml"
    _write_minimal_consultant_xml(a, "Федеральный закон от 05.04.2013 N 44-ФЗ")

    parser = ConsultantWordMLParser(source_root=str(tmp_path))
    doc_1, _ = parser.parse(str(a))
    doc_2, _ = parser.parse(str(a))
    assert doc_1.source_id == doc_2.source_id


def test_derive_source_id_format_includes_hash_entropy() -> None:
    """The format is consultant:{head}-{8hex} for any input combination."""
    sid = _derive_source_id("44-ФЗ", "foo.xml", "a" * 64)
    assert sid == "consultant:44-ФЗ-aaaaaaaa"
    sid_no_act = _derive_source_id(None, "my-fixture.xml", "0123456789abcdef" * 4)
    assert sid_no_act == "consultant:my-fixture-01234567"
    assert all(c in "0123456789abcdef" for c in sid_no_act.rsplit("-", 1)[-1])


def test_derive_source_id_falls_back_to_filename_stem_when_no_act_number() -> None:
    sid = _derive_source_id(None, "Акт без номера.xml", "f" * 64)
    assert sid == "consultant:Акт без номера-ffffffff"


def test_real_corpus_source_ids_are_unique_within_content_groups() -> None:
    """Across the real corpus, source_id collisions are bounded to byte-identical duplicates.

    The S01 fixture inventory records internal_duplicate_pairs for two
    byte-identical file groups. They are expected to share source_id (same
    content -> same SHA -> same entropy). No other collisions are tolerated.
    """

    inventory = json.loads(INVENTORY_JSON.read_text(encoding="utf-8"))
    by_id: dict[str, list[str]] = {}
    for fixture in inventory["fixtures"]:
        if fixture.get("source_kind") != "consultant-wordml-xml":
            continue
        path = fixture["path"]
        if not (ROOT / path).is_file():
            continue
        parser = ConsultantWordMLParser()
        try:
            document, _ = parser.parse(path)
        except Exception:
            continue
        by_id.setdefault(document.source_id, []).append(path)

    duplicates = {sid: sorted(paths) for sid, paths in by_id.items() if len(paths) > 1}
    # Every duplicate group must correspond to a S01 internal_duplicate_pair
    # (byte-identical content). Group sizes are 2 each in the current corpus.
    expected_duplicate_paths = {
        tuple(sorted(group))
        for group in inventory.get("duplicate_check", {}).get("internal_duplicate_pairs", [])
    }
    actual_duplicate_paths = {tuple(sorted(paths)) for paths in duplicates.values()}
    assert actual_duplicate_paths <= expected_duplicate_paths, (
        f"unexpected new source_id collisions: {duplicates}"
    )


def test_source_id_uniqueness_jsonl_is_current() -> None:
    """``prd/parser/source_id_uniqueness.json`` is a checked-in artifact; verify it is current."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "scripts/build-source-id-uniqueness.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["status"] == "pass"
    assert summary["total_fixtures"] >= 39
