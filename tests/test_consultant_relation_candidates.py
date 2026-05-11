from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/build-consultant-relation-candidates.py"
CONSULTANT_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
  <w:body>
    <w:p>
      <w:hlink w:dest="{dest}">
        <w:r><w:t>{text}</w:t></w:r>
      </w:hlink>
    </w:p>
  </w:body>
</w:wordDocument>
'''


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def parse_stdout_json(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def write_inventory(root: Path, source_path: str, sha256: str) -> None:
    inventory = {
        "fixtures": [
            {
                "canonical": True,
                "path": source_path,
                "sha256": sha256,
                "source_kind": "consultant-wordml-xml",
            }
        ]
    }
    target = root / "prd/parser/source_fixture_inventory.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(inventory, ensure_ascii=False), encoding="utf-8")


def write_xml_fixture(root: Path, relative_path: str, xml: str) -> Path:
    target = root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(xml, encoding="utf-8")
    return target


def load_module():
    spec = importlib.util.spec_from_file_location("build_consultant_relation_candidates", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_consultant_relation_candidates"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_real_fixture_happy_path_builds_one_s02_valid_candidate() -> None:
    module = load_module()

    result = module.build_relation_candidates(ROOT)

    assert result.report["status"] == "pass"
    assert result.report["candidate_count"] == 1
    assert result.diagnostics == []
    assert len(result.records) == 1

    record = result.records[0]
    assert record["record_kind"] == "relation_candidate"
    assert record["id"] == "REL-CONS-0001"
    assert record["source_kind"] == "consultant-wordml-xml"
    assert record["source_path"] == "law-source/consultant/Список документов (5).xml"
    assert record["source_sha256"] == "0694587f4a907faf2e4cbaccb27b166e34a8380e9afc17642769b5ac54d5ede3"
    assert record["source_member"] is None
    assert record["source_block_id"] == "BLOCK-CONSULTANT-XML-0001"
    assert record["subject_ref"] == "consultant-list:law-source/consultant/Список документов (5).xml"
    assert record["object_ref"] == "consultant:LAW:179581@11.05.2026"
    assert record["relation_type"] == "consultant-list-entry"
    assert record["status"] == "candidate"
    assert record["non_authoritative"] is True
    assert "КонсультантПлюс: Новости для специалиста по закупкам" in record["evidence_excerpt"]
    assert len(record["evidence_excerpt"]) <= module.MAX_EXCERPT_CHARS
    assert record["evidence_sha256"] == module.sha256_text(record["evidence_excerpt"])

    non_claims = "\n".join(record["non_claims"])
    for phrase in [
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB loading/runtime readiness",
        "Consultant WordML legal authority",
        "relation correctness",
    ]:
        assert phrase in non_claims


def test_real_fixture_happy_path_preserves_consultant_url_identity_in_report() -> None:
    module = load_module()

    result = module.build_relation_candidates(ROOT)

    candidate = result.report["candidates"][0]
    assert candidate == {
        "id": "REL-CONS-0001",
        "source_block_id": "BLOCK-CONSULTANT-XML-0001",
        "status": "candidate",
        "selector": "wordml:hlink[1]",
        "object_ref": "consultant:LAW:179581@11.05.2026",
        "base": "LAW",
        "n": "179581",
        "date": "11.05.2026",
        "demo": "2",
    }


def test_write_then_check_generates_three_deterministic_artifacts(tmp_path: Path) -> None:
    module = load_module()
    result = module.build_relation_candidates(ROOT)
    output_dir = tmp_path / "parser"

    module.write_outputs(result, output_dir)

    expected = module.output_contents(result)
    assert sorted(expected) == [
        "consultant_relation_candidates.json",
        "consultant_relation_candidates.jsonl",
        "consultant_relation_candidates.md",
    ]
    for name, content in expected.items():
        assert (output_dir / name).read_text(encoding="utf-8") == content
    assert "current fixture yields one candidate only" in expected["consultant_relation_candidates.md"]
    for phrase in [
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB loading/runtime readiness",
        "Consultant WordML legal authority",
        "relation correctness",
    ]:
        assert phrase in expected["consultant_relation_candidates.md"]

    check = run_cli("--check", "--output-dir", str(output_dir))
    assert check.returncode == 0, check.stdout + check.stderr
    summary = parse_stdout_json(check)
    assert summary["status"] == "pass"
    assert summary["candidate_count"] == 1
    assert summary["artifact_freshness"]["status"] == "pass"  # type: ignore[index]


def test_check_reports_missing_and_stale_artifacts(tmp_path: Path) -> None:
    module = load_module()
    output_dir = tmp_path / "parser"
    module.write_outputs(module.build_relation_candidates(ROOT), output_dir)

    (output_dir / "consultant_relation_candidates.jsonl").write_text("stale\n", encoding="utf-8")
    (output_dir / "consultant_relation_candidates.md").unlink()

    result = run_cli("--check", "--output-dir", str(output_dir))

    assert result.returncode == 1
    summary = parse_stdout_json(result)
    assert summary["status"] == "fail"
    freshness = summary["artifact_freshness"]
    assert freshness["status"] == "stale"  # type: ignore[index]
    stale_paths = set(freshness["stale_paths"])  # type: ignore[index]
    assert any(path.endswith("consultant_relation_candidates.jsonl") for path in stale_paths)
    assert any(path.endswith("consultant_relation_candidates.md") for path in stale_paths)
    diagnostics = summary["diagnostics"]
    assert all(diagnostic["rule"] == "stale-artifact" for diagnostic in diagnostics)  # type: ignore[index]


def test_tracked_artifacts_validate_and_markdown_repeats_non_claims() -> None:
    module = load_module()
    artifact_paths = [
        ROOT / "prd/parser/consultant_relation_candidates.jsonl",
        ROOT / "prd/parser/consultant_relation_candidates.json",
        ROOT / "prd/parser/consultant_relation_candidates.md",
    ]
    for path in artifact_paths:
        assert path.exists(), path
        assert path.read_text(encoding="utf-8")

    generated = module.build_relation_candidates(ROOT)
    expected_contents = module.output_contents(generated)
    for name, expected in expected_contents.items():
        assert (ROOT / "prd/parser" / name).read_text(encoding="utf-8") == expected

    report = json.loads((ROOT / "prd/parser/consultant_relation_candidates.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["candidate_count"] == 1
    assert report["non_authoritative"] is True

    docs = "\n".join(
        [
            (ROOT / "prd/parser/README.md").read_text(encoding="utf-8"),
            (ROOT / "prd/parser/consultant_relation_candidates.md").read_text(encoding="utf-8"),
        ]
    )
    for phrase in [
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB loading/runtime readiness",
        "Consultant WordML",
        "non-authoritative",
        "relation correctness",
    ]:
        assert phrase in docs


def test_fixture_diagnostics_cover_missing_sha_mismatch_malformed_xml_and_no_hyperlinks(tmp_path: Path) -> None:
    module = load_module()
    missing_records, missing_rows, missing_diags, missing_sha = module.extract_relation_candidates(
        tmp_path, "missing.xml", "0" * 64
    )
    assert missing_records == []
    assert missing_rows == []
    assert missing_sha is None
    assert missing_diags[0]["rule"] == "missing-canonical-path"

    fixture_path = write_xml_fixture(
        tmp_path,
        "fixture.xml",
        CONSULTANT_XML.format(dest="https://example.test/?base=LAW&amp;n=1&amp;date=01.01.2024", text="link"),
    )
    mismatch = module.extract_relation_candidates(tmp_path, "fixture.xml", "0" * 64)
    assert mismatch[2][0]["rule"] == "fixture-mismatch"
    assert mismatch[2][0]["actual_sha256"] == module.sha256_file(fixture_path)

    bad_path = write_xml_fixture(tmp_path, "bad.xml", "<broken>")
    bad = module.extract_relation_candidates(tmp_path, "bad.xml", module.sha256_file(bad_path))
    assert bad[2][0]["rule"] == "xml-parse-error"

    no_links_path = write_xml_fixture(
        tmp_path,
        "no-links.xml",
        '<?xml version="1.0"?><w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p>No links</w:p></w:body></w:wordDocument>',
    )
    no_links = module.extract_relation_candidates(tmp_path, "no-links.xml", module.sha256_file(no_links_path))
    assert no_links[0] == []
    assert no_links[2][0]["rule"] == "no-hyperlinks"


def test_incomplete_consultant_identity_is_retained_as_needs_review_and_bounded(tmp_path: Path) -> None:
    module = load_module()
    long_text = "А" * (module.MAX_EXCERPT_CHARS + 100)
    fixture_path = write_xml_fixture(
        tmp_path,
        "fixture.xml",
        CONSULTANT_XML.format(dest="https://example.test/?base=LAW&amp;n=179581", text=long_text),
    )

    records, rows, diagnostics, _ = module.extract_relation_candidates(
        tmp_path, "fixture.xml", module.sha256_file(fixture_path)
    )

    assert diagnostics == []
    assert len(records) == 1
    assert records[0]["status"] == "needs-review"
    assert records[0]["object_ref"] == "consultant:incomplete:0001"
    assert len(records[0]["evidence_excerpt"]) <= module.MAX_EXCERPT_CHARS
    assert records[0]["evidence_sha256"] == module.sha256_text(records[0]["evidence_excerpt"])
    assert rows[0]["date"] is None


def test_build_uses_temporary_inventory_variants_for_manifest_diagnostics(tmp_path: Path) -> None:
    module = load_module()
    write_inventory(tmp_path, "fixture.xml", "0" * 64)

    result = module.build_relation_candidates(tmp_path)

    assert result.report["status"] == "fail"
    assert result.report["candidate_count"] == 0
    assert result.diagnostics[0]["source_path"] == "fixture.xml"
    assert result.diagnostics[0]["rule"] == "missing-canonical-path"

    fixture_path = write_xml_fixture(
        tmp_path,
        "fixture.xml",
        CONSULTANT_XML.format(dest="https://example.test/?base=LAW&amp;n=1&amp;date=01.01.2024", text="link"),
    )
    write_inventory(tmp_path, "fixture.xml", module.sha256_file(fixture_path))
    ok = module.build_relation_candidates(tmp_path)
    assert ok.report["status"] == "pass"
    assert ok.report["candidate_count"] == 1
