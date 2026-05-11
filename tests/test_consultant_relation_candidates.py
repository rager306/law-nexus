from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/build-consultant-relation-candidates.py"


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
