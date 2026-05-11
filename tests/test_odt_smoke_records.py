from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/build-odt-smoke-records.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_odt_smoke_records", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_odt_smoke_records"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_odt(path: Path, content_xml: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        if content_xml is not None:
            zf.writestr("content.xml", content_xml)


def minimal_content_xml(body: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0">
  <office:body>{body}</office:body>
</office:document-content>
'''


def test_real_fixtures_build_s02_valid_bounded_records_with_raw_order() -> None:
    module = load_module()

    result = module.build_smoke_records(ROOT)

    assert result.report["status"] == "pass"
    assert [record["id"] for record in result.document_records] == ["DOC-44-FZ", "DOC-PP-60"]
    assert result.report["document_count"] == 2
    assert result.report["source_block_count"] == len(result.source_block_records)
    assert result.report["downstream_boundary"].startswith("S03 emits bounded smoke parser records only")
    assert result.markdown.count("parser completeness") >= 1
    assert "First emitted hash" in result.markdown
    assert 0 < result.report["source_block_count"] <= module.MAX_BLOCKS_PER_DOCUMENT * 2
    for document in result.report["documents"]:
        assert document["emitted_block_count"] <= module.MAX_BLOCKS_PER_DOCUMENT
        assert document["raw_block_count"] >= document["emitted_block_count"]
        assert document["first_emitted_excerpt_sha256"]
        assert document["last_emitted_excerpt_sha256"]
    for record in [*result.document_records, *result.source_block_records]:
        assert record["non_authoritative"] is True
        assert record["non_claims"]
        assert set(record) <= module.ALLOWED_FIELDS_BY_KIND[record["record_kind"]]
    by_doc: dict[str, list[dict[str, object]]] = {}
    for block in result.source_block_records:
        by_doc.setdefault(str(block["document_id"]), []).append(block)
        assert block["source_member"] == "content.xml"
        assert len(str(block["excerpt"])) <= 500
        assert str(block["location"]["selector"]).startswith("content.xml#block[")
    for blocks in by_doc.values():
        indexes = [int(block["order_index"]) for block in blocks]
        assert indexes == sorted(indexes)


def test_check_prints_compact_report_and_detects_stale_outputs(tmp_path: Path) -> None:
    module = load_module()
    generated = module.build_smoke_records(ROOT)
    out_dir = tmp_path / "prd/parser"
    module.write_outputs(generated, out_dir)

    ok = run_cli("--check", "--output-dir", str(out_dir))
    assert ok.returncode == 0, ok.stderr
    report = json.loads(ok.stdout)
    assert report["status"] == "pass"
    assert report["artifact_freshness"]["status"] == "pass"

    (out_dir / "odt_document_records.jsonl").write_text("stale\n", encoding="utf-8")
    stale = run_cli("--check", "--output-dir", str(out_dir))
    assert stale.returncode == 1
    stale_report = json.loads(stale.stdout)
    assert stale_report["status"] == "fail"
    assert stale_report["diagnostics"][0]["rule"] == "stale-artifact"
    assert stale_report["diagnostics"][0]["path"].endswith("odt_document_records.jsonl")


def test_tracked_artifacts_and_readme_expose_t02_boundaries() -> None:
    module = load_module()
    artifact_paths = [
        ROOT / "prd/parser/odt_document_records.jsonl",
        ROOT / "prd/parser/odt_source_block_records.jsonl",
        ROOT / "prd/parser/odt_smoke_records.json",
        ROOT / "prd/parser/odt_smoke_records.md",
    ]
    for path in artifact_paths:
        assert path.exists(), path
        assert path.read_text(encoding="utf-8")

    report = json.loads((ROOT / "prd/parser/odt_smoke_records.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["generated_by"] == "scripts/build-odt-smoke-records.py"
    assert report["max_blocks_per_document"] == module.MAX_BLOCKS_PER_DOCUMENT
    assert report["document_count"] == 2
    assert report["source_block_count"] <= module.MAX_BLOCKS_PER_DOCUMENT * 2
    for document in report["documents"]:
        assert document["source_sha256"]
        assert document["table_count"] >= 0
        assert document["first_emitted_excerpt_sha256"]
        assert document["last_emitted_excerpt_sha256"]

    docs = "\n".join(
        [
            (ROOT / "prd/parser/README.md").read_text(encoding="utf-8"),
            (ROOT / "prd/parser/odt_smoke_records.md").read_text(encoding="utf-8"),
        ]
    )
    for phrase in [
        "R031",
        "parser completeness",
        "legal correctness",
        "product ETL",
        "FalkorDB readiness",
        "non-authoritative",
        "content.xml",
        "citation-safe retrieval",
    ]:
        assert phrase in docs


def test_fixture_failure_diagnostics_cover_missing_path_invalid_zip_missing_member_and_bad_xml(tmp_path: Path) -> None:
    module = load_module()
    missing = module.load_fixture("DOC-MISSING", "missing.odt", "0" * 64, tmp_path)
    assert missing.status == "missing-canonical-path"
    assert missing.diagnostics[0]["source_path"] == "missing.odt"

    invalid = tmp_path / "bad.odt"
    invalid.write_text("not a zip", encoding="utf-8")
    invalid_result = module.load_fixture("DOC-BAD", "bad.odt", "0" * 64, tmp_path)
    assert invalid_result.status == "invalid-zip"
    assert invalid_result.diagnostics[0]["rule"] == "invalid-zip"

    no_content = tmp_path / "missing-content.odt"
    write_odt(no_content, None)
    no_content_result = module.load_fixture("DOC-NO-CONTENT", "missing-content.odt", "0" * 64, tmp_path)
    assert no_content_result.status == "missing-content-xml"
    assert no_content_result.diagnostics[0]["rule"] == "missing-content-xml"

    bad_xml = tmp_path / "bad-xml.odt"
    write_odt(bad_xml, "<broken>")
    bad_xml_result = module.load_fixture("DOC-BAD-XML", "bad-xml.odt", "0" * 64, tmp_path)
    assert bad_xml_result.status == "xml-parse-error"
    assert bad_xml_result.diagnostics[0]["rule"] == "xml-parse-error"


def test_title_excerpt_limits_and_raw_vs_emitted_order(tmp_path: Path) -> None:
    module = load_module()
    long_heading = "З" * 300
    long_para = "П" * 800
    path = tmp_path / "sample.odt"
    write_odt(
        path,
        minimal_content_xml(
            f'''
            <text:h text:outline-level="1">{long_heading}</text:h>
            <text:p>first emitted</text:p>
            <text:p></text:p>
            <text:p>{long_para}</text:p>
            '''
        ),
    )

    result = module.load_fixture("DOC-SAMPLE", "sample.odt", module.sha256_file(path), tmp_path)

    assert result.status == "pass"
    assert result.document_record is not None
    assert len(result.document_record["title"]) == 240
    assert result.raw_block_count == 4
    assert result.emitted_block_count == 3
    assert [block["order_index"] for block in result.source_block_records] == [0, 1, 3]
    assert all(len(block["excerpt"]) <= 500 for block in result.source_block_records)
