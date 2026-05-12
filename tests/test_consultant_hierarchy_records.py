from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from parser_records import load_jsonl_records, parse_parser_record  # noqa: E402

SCRIPT_PATH = ROOT / "scripts" / "build-consultant-hierarchy-records.py"
JSONL_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.jsonl"
JSON_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.json"
REPORT_PATH = ROOT / "prd" / "parser" / "consultant_hierarchy_records.md"
SOURCE_PATH = ROOT / "law-source" / "consultant" / "44-FZ-2026.xml"
CONTEXT_FALSE_POSITIVE_FIXTURE = ROOT / "tests" / "fixtures" / "consultant_wordml_context_false_positive.xml"


def load_builder_module():
    spec = importlib.util.spec_from_file_location("build_consultant_hierarchy_records", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generated_hierarchy_jsonl_records_are_valid_and_contextual():
    records, diagnostics = load_jsonl_records(JSONL_PATH)
    assert diagnostics == []
    assert records

    payloads = [record.model_dump(mode="json") for record in records]
    counts = Counter(payload["level"] for payload in payloads)
    assert counts == {
        "document": 1,
        "chapter": 8,
        "section": 9,
        "article": 94,
        "part": 793,
        "clause": 997,
        "subclause": 283,
    }

    first_by_level = {}
    for payload in payloads:
        first_by_level.setdefault(payload["level"], payload)
    assert payloads[0]["id"] == "HIER-CONS-DOCUMENT"
    assert payloads[0]["parent_id"] is None
    assert first_by_level["chapter"]["parent_id"] == "HIER-CONS-DOCUMENT"
    assert first_by_level["article"]["parent_id"] == first_by_level["chapter"]["id"]
    assert first_by_level["part"]["parent_id"] == first_by_level["article"]["id"]
    assert first_by_level["clause"]["parent_id"] == first_by_level["part"]["id"]

    source_hash = hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
    assert {payload["source_sha256"] for payload in payloads} == {source_hash}
    assert all(payload["source_path"] == "law-source/consultant/44-FZ-2026.xml" for payload in payloads)
    assert all(payload["non_authoritative"] is True for payload in payloads)
    assert all("legal correctness" in " ".join(payload["non_claims"]) for payload in payloads)


def test_generator_build_is_deterministic_against_artifacts():
    module = load_builder_module()
    result = module.build()
    assert result.jsonl == JSONL_PATH.read_text(encoding="utf-8")
    assert result.summary_json == JSON_PATH.read_text(encoding="utf-8")
    assert result.report_md == REPORT_PATH.read_text(encoding="utf-8")
    assert result.diagnostics["namespace_detected"] == "http://schemas.microsoft.com/office/word/2003/wordml"
    assert result.diagnostics["paragraph_count"] == 3601
    assert result.diagnostics["skipped_empty_paragraphs"] == 439
    assert result.diagnostics["validation_error_count"] == 0


def test_cli_check_reports_fresh_artifacts_and_observability():
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--check"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["status"] == "pass"
    assert payload["phase"] == "consultant_wordml_hierarchy_build"
    assert payload["artifact_freshness"] == {
        "prd/parser/consultant_hierarchy_records.json": True,
        "prd/parser/consultant_hierarchy_records.jsonl": True,
        "prd/parser/consultant_hierarchy_records.md": True,
    }
    assert payload["source"]["inventory_hash_matches"] is True
    assert payload["malformed_xml"] is None
    assert payload["emitted_counts_by_level"]["article"] == 94


def test_marker_entity_decoding_and_boundary_resets_on_inline_fixture():
    module = load_builder_module()
    paragraphs = [
        module.Paragraph(index=1, text="Федеральный закон", style="5"),
        module.Paragraph(index=2, text="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ", style="2"),
        module.Paragraph(index=3, text=module.normalize_text("&#167; 1. Планирование"), style="2"),
        module.Paragraph(index=4, text="Статья 1. Предмет", style="2"),
        module.Paragraph(index=5, text="1. Часть первая", style="0"),
        module.Paragraph(index=6, text="1) пункт", style="0"),
        module.Paragraph(index=7, text="а) подпункт", style="0"),
        module.Paragraph(index=8, text="Статья 2. Новая статья", style="2"),
        module.Paragraph(index=9, text="1) пункт без новой части", style="0"),
    ]
    records, diagnostics = module.hierarchy_records(paragraphs, "a" * 64)
    payloads = [parse_parser_record(record).model_dump(mode="json") for record in records]
    by_title = {payload["title"]: payload for payload in payloads}

    assert diagnostics["validation_error_count"] == 0
    assert diagnostics["structural_error_count"] == 0
    assert by_title["§ 1. Планирование"]["level"] == "section"
    assert by_title["§ 1. Планирование"]["parent_id"] == by_title["Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ"]["id"]
    assert by_title["Статья 1. Предмет"]["parent_id"] == by_title["§ 1. Планирование"]["id"]
    assert by_title["Статья 2. Новая статья"]["parent_id"] == by_title["§ 1. Планирование"]["id"]
    assert by_title["1) пункт без новой части"]["parent_id"] == by_title["Статья 2. Новая статья"]["id"]


def test_context_false_positive_fixture_rejects_markers_outside_article_context():
    module = load_builder_module()
    paragraphs, stream_diagnostics = module.stream_wordml_paragraphs(CONTEXT_FALSE_POSITIVE_FIXTURE)

    records, diagnostics = module.hierarchy_records(paragraphs, "d" * 64)
    payloads = [parse_parser_record(record).model_dump(mode="json") for record in records]
    titles = {payload["title"] for payload in payloads}
    rejected = diagnostics["rejected_context_markers"]

    assert stream_diagnostics["malformed_xml"] is None
    assert diagnostics["skipped_marker_counts"] == {
        "clause_outside_article": 1,
        "part_outside_article": 2,
        "subclause_outside_article": 1,
    }
    assert diagnostics["rejected_context_marker_count"] == 4
    assert diagnostics["structural_error_count"] == 3
    assert [payload["level"] for payload in payloads] == ["document", "chapter", "article", "part", "clause", "subclause"]
    assert all("Context-free" not in title and "Chapter-level" not in title for title in titles)
    assert all(item["rule_id"] == "hierarchical_parsing_required" for item in rejected)
    assert {item["reason"] for item in rejected} == {
        "clause_outside_article",
        "part_outside_article",
        "subclause_outside_article",
    }
    assert all(item["source_excerpt"] and len(item["source_excerpt_sha256"]) == 64 for item in rejected)

def write_wordml(path: Path, paragraphs: list[str]) -> None:
    body = "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body>{body}</w:body></w:wordDocument>',
        encoding="utf-8",
    )


def configure_temp_builder(module, monkeypatch, tmp_path: Path, source_texts: list[str] | None, inventory_sha256: str | None = None):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SOURCE_PATH", Path("fixture.xml"))
    monkeypatch.setattr(module, "INVENTORY_PATH", Path("inventory.json"))
    monkeypatch.setattr(module, "JSONL_PATH", Path("out.jsonl"))
    monkeypatch.setattr(module, "JSON_PATH", Path("out.json"))
    monkeypatch.setattr(module, "REPORT_PATH", Path("out.md"))
    source_path = tmp_path / "fixture.xml"
    if source_texts is not None:
        write_wordml(source_path, source_texts)
    sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path.exists() else "0" * 64
    inventory = {"fixtures": [{"path": "fixture.xml", "sha256": inventory_sha256 or sha256}]}
    (tmp_path / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
    return source_path


def test_cli_fail_closed_for_missing_source_fixture(monkeypatch, tmp_path, capsys):
    module = load_builder_module()
    configure_temp_builder(module, monkeypatch, tmp_path, source_texts=None)

    assert module.main(["--check"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["fatal_error_count"] == 1
    assert payload["fatal_errors"][0]["kind"] == "missing_source"
    assert payload["source"]["inventory_hash_matches"] is False
    assert payload["non_authoritative"] is True


def test_cli_fail_closed_for_sha_mismatch(monkeypatch, tmp_path, capsys):
    module = load_builder_module()
    configure_temp_builder(module, monkeypatch, tmp_path, ["Федеральный закон", "Статья 1. Предмет"], inventory_sha256="b" * 64)

    assert module.main(["--check"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["source"]["inventory_hash_matches"] is False
    assert payload["fatal_error_count"] == 0
    assert payload["malformed_xml"] is None


def test_cli_fail_closed_for_malformed_xml(monkeypatch, tmp_path, capsys):
    module = load_builder_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SOURCE_PATH", Path("fixture.xml"))
    monkeypatch.setattr(module, "INVENTORY_PATH", Path("inventory.json"))
    monkeypatch.setattr(module, "JSONL_PATH", Path("out.jsonl"))
    monkeypatch.setattr(module, "JSON_PATH", Path("out.json"))
    monkeypatch.setattr(module, "REPORT_PATH", Path("out.md"))
    source_path = tmp_path / "fixture.xml"
    source_path.write_text("<w:wordDocument><w:body><w:p>", encoding="utf-8")
    sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    (tmp_path / "inventory.json").write_text(json.dumps({"fixtures": [{"path": "fixture.xml", "sha256": sha256}]}), encoding="utf-8")

    assert module.main(["--check"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["malformed_xml"] is not None
    assert payload["emitted_counts_by_level"] == {}
    assert payload["diagnostics_bounded"] is True


def test_hierarchy_diagnostics_for_missing_article_heading_and_context_break():
    module = load_builder_module()
    paragraphs = [
        module.Paragraph(index=1, text="Федеральный закон", style="5"),
        module.Paragraph(index=2, text="Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ", style="2"),
        module.Paragraph(index=3, text="1. Часть без статьи", style="0"),
        module.Paragraph(index=4, text="1) пункт без статьи", style="0"),
    ]

    records, diagnostics = module.hierarchy_records(paragraphs, "c" * 64)
    assert [record["level"] for record in records] == ["document", "chapter"]
    assert diagnostics["skipped_marker_counts"] == {"clause_outside_article": 1, "part_outside_article": 1}
    assert diagnostics["structural_error_count"] == 3
    assert diagnostics["structural_errors"][0]["kind"] == "missing_article_heading"
    assert {error["kind"] for error in diagnostics["structural_errors"][1:]} == {"context_break"}


def test_cli_fail_closed_for_missing_article_heading(monkeypatch, tmp_path, capsys):
    module = load_builder_module()
    configure_temp_builder(module, monkeypatch, tmp_path, ["Федеральный закон", "Глава 1. Общие", "1. Часть без статьи"])

    assert module.main(["--check"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["structural_error_count"] >= 1
    assert payload["structural_errors"][0]["kind"] == "missing_article_heading"
    assert payload["validation_error_count"] == 0
