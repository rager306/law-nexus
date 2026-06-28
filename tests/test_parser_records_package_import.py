from __future__ import annotations

from law_nexus.adapters.sources import parser_records


def test_package_parser_records_exports_core_contract() -> None:
    assert parser_records.SCHEMA_VERSION == "legalgraph-parser-record/v1"
    assert parser_records.MAX_DIAGNOSTICS_PER_FILE == 100
    assert parser_records.ParserRecord is not None
    assert parser_records.parse_parser_record is not None
    assert parser_records.load_jsonl_records is not None


def test_package_parser_records_preserves_non_claim_defaults() -> None:
    record = parser_records.parse_parser_record(
        {
            "schema_version": parser_records.SCHEMA_VERSION,
            "record_kind": "document",
            "id": "DOC-1",
            "source_kind": "consultant-wordml-xml",
            "source_path": "law-source/consultant/example.xml",
            "source_sha256": "a" * 64,
            "non_authoritative": True,
            "non_claims": ["shape-only"],
            "title": "Example",
        }
    )

    assert record.non_authoritative is True
    assert record.non_claims == ["shape-only"]
