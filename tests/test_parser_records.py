from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/parser_records.py"
VALID_SHA = "a" * 64


def load_parser_records_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("parser_records", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def document_payload() -> dict[str, object]:
    return {
        "record_kind": "document",
        "schema_version": "legalgraph-parser-record/v1",
        "id": "DOC-44-FZ",
        "source_kind": "garant-odt",
        "source_path": "law-source/garant/44-fz.odt",
        "source_sha256": VALID_SHA,
        "title": "44-FZ bounded fixture",
        "non_authoritative": True,
        "non_claims": ["Contract shape only; not legal correctness."],
    }


def source_block_payload() -> dict[str, object]:
    return {
        "record_kind": "source_block",
        "schema_version": "legalgraph-parser-record/v1",
        "id": "BLOCK-44-FZ-0001",
        "document_id": "DOC-44-FZ",
        "source_kind": "garant-odt",
        "source_path": "law-source/garant/44-fz.odt",
        "source_sha256": VALID_SHA,
        "source_member": "content.xml",
        "order_index": 0,
        "location": {"selector": "/office:document-content/office:body", "label": "body"},
        "excerpt": "Bounded excerpt, not a legal answer.",
        "excerpt_sha256": "b" * 64,
        "non_authoritative": True,
        "non_claims": ["Source block shape only; not parser completeness."],
    }


def relation_payload() -> dict[str, object]:
    return {
        "record_kind": "relation_candidate",
        "schema_version": "legalgraph-parser-record/v1",
        "id": "REL-CONS-0001",
        "source_kind": "consultant-wordml-xml",
        "source_path": "law-source/consultant/Список документов (5).xml",
        "source_sha256": VALID_SHA,
        "source_member": None,
        "source_block_id": "BLOCK-CONS-0001",
        "subject_ref": "DOC-44-FZ",
        "object_ref": "DOC-PP-60",
        "relation_type": "mentions",
        "status": "candidate",
        "evidence_excerpt": "Bounded relation-candidate excerpt only.",
        "evidence_sha256": "c" * 64,
        "non_authoritative": True,
        "non_claims": ["Relation candidate only; not authoritative."],
    }


def test_models_accept_one_valid_record_per_kind() -> None:
    module = load_parser_records_module()

    document = module.DocumentRecord.model_validate(document_payload())
    block = module.SourceBlockRecord.model_validate(source_block_payload())
    relation = module.RelationCandidateRecord.model_validate(relation_payload())

    assert document.id == "DOC-44-FZ"
    assert block.order_index == 0
    assert relation.status == "candidate"
    assert document.non_authoritative is True
    assert block.non_claims
    assert relation.non_claims


@pytest.mark.parametrize(
    ("payload_factory", "expected_kind"),
    [
        (document_payload, "document"),
        (source_block_payload, "source_block"),
        (relation_payload, "relation_candidate"),
    ],
)
def test_parser_record_adapter_discriminates_record_kinds(payload_factory, expected_kind: str) -> None:
    module = load_parser_records_module()

    record = module.parse_parser_record(payload_factory())

    assert record.record_kind == expected_kind


@pytest.mark.parametrize(
    ("mutator", "expected_fragment"),
    [
        (lambda payload: payload.update({"source_path": "/tmp/44-fz.odt"}), "source_path"),
        (lambda payload: payload.update({"source_path": "../law-source/garant/44-fz.odt"}), "source_path"),
        (lambda payload: payload.pop("source_sha256"), "source_sha256"),
        (lambda payload: payload.update({"id": "BAD-44-FZ"}), "DOC-"),
        (lambda payload: payload.update({"source_sha256": "A" * 64}), "sha256"),
        (lambda payload: payload.update({"non_authoritative": False}), "non_authoritative"),
    ],
)
def test_document_validation_rejects_malformed_provenance_and_claims(mutator, expected_fragment: str) -> None:
    module = load_parser_records_module()
    payload = document_payload()
    mutator(payload)

    with pytest.raises(ValidationError) as exc_info:
        module.DocumentRecord.model_validate(payload)

    assert expected_fragment in str(exc_info.value)


def test_source_block_requires_odt_content_xml_member_and_non_negative_order() -> None:
    module = load_parser_records_module()
    valid = source_block_payload()
    assert module.SourceBlockRecord.model_validate(valid).order_index == 0

    wrong_member = source_block_payload()
    wrong_member["source_member"] = "styles.xml"
    with pytest.raises(ValidationError) as wrong_member_error:
        module.SourceBlockRecord.model_validate(wrong_member)
    assert "content.xml" in str(wrong_member_error.value)

    negative_order = source_block_payload()
    negative_order["order_index"] = -1
    with pytest.raises(ValidationError) as negative_order_error:
        module.SourceBlockRecord.model_validate(negative_order)
    assert "order_index" in str(negative_order_error.value)


def test_relation_candidate_rejects_authoritative_or_product_ready_statuses() -> None:
    module = load_parser_records_module()
    payload = relation_payload()
    payload["status"] = "authoritative"

    with pytest.raises(ValidationError) as exc_info:
        module.RelationCandidateRecord.model_validate(payload)

    assert "candidate" in str(exc_info.value)
    assert "authoritative" in str(exc_info.value)


def test_wrong_record_kind_and_excerpt_boundaries_are_rejected() -> None:
    module = load_parser_records_module()
    wrong_kind = document_payload()
    wrong_kind["record_kind"] = "authority"
    with pytest.raises(ValidationError):
        module.parse_parser_record(wrong_kind)

    oversized = source_block_payload()
    oversized["excerpt"] = "x" * (module.MAX_EXCERPT_CHARS + 1)
    with pytest.raises(ValidationError) as exc_info:
        module.SourceBlockRecord.model_validate(oversized)
    assert "excerpt" in str(exc_info.value)


def test_jsonl_validation_diagnostics_include_file_line_record_and_field(tmp_path: Path) -> None:
    module = load_parser_records_module()
    jsonl = tmp_path / "records.jsonl"
    jsonl.write_text(
        "{not json}\n"
        + module.dumps_jsonl_record({**document_payload(), "id": "BAD-44-FZ"})
        + "\n",
        encoding="utf-8",
    )

    records, diagnostics = module.load_jsonl_records(jsonl)

    assert records == []
    assert len(diagnostics) == 2
    malformed, invalid = diagnostics
    assert malformed["file"] == str(jsonl)
    assert malformed["line"] == 1
    assert malformed["rule"] == "json_invalid"
    assert invalid["file"] == str(jsonl)
    assert invalid["line"] == 2
    assert invalid["record_id"] == "BAD-44-FZ"
    assert invalid["record_kind"] == "document"
    assert invalid["field"] == "id"
    assert invalid["source_path"] == "law-source/garant/44-fz.odt"
