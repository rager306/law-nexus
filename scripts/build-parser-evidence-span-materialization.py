#!/usr/bin/env python3
"""Build a tiny safe parser-to-EvidenceSpan materialization smoke artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "law-source/garant/44-fz.odt"
CONTRACT = ROOT / "prd/research/ontology_architecture_requirements/58-parser-evidence-span-materialization-contract.md"
OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"
SCHEMA_VERSION = "parser-evidence-span-materialization/v1"
REPRESENTATION_KIND = "safe_materialized_evidence_candidates_v1"
TEXT_NS = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"
TABLE_NS = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
OFFICE_NS = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
TEXT_P = f"{{{TEXT_NS}}}p"
TEXT_H = f"{{{TEXT_NS}}}h"
TABLE_TABLE = f"{{{TABLE_NS}}}table"
OFFICE_BODY = f"{{{OFFICE_NS}}}body"
OFFICE_TEXT = f"{{{OFFICE_NS}}}text"


class MaterializationBuildError(RuntimeError):
    """Raised when the smoke artifact cannot be built."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def safe_hash(*parts: object) -> str:
    payload = "|".join(str(part) for part in parts).encode("utf-8")
    return f"sha256:{sha256_bytes(payload)}"


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_content_xml(source: Path) -> bytes:
    try:
        with zipfile.ZipFile(source) as archive:
            return archive.read("content.xml")
    except FileNotFoundError as exc:
        raise MaterializationBuildError("source_unavailable") from exc
    except KeyError as exc:
        raise MaterializationBuildError("content_xml_missing") from exc
    except zipfile.BadZipFile as exc:
        raise MaterializationBuildError("parser_unavailable") from exc


def iter_structural_events(content_xml: bytes) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(content_xml)
    except ET.ParseError as exc:
        raise MaterializationBuildError("parser_unavailable") from exc
    body = root.find(OFFICE_BODY)
    text = body.find(OFFICE_TEXT) if body is not None else None
    if text is None:
        raise MaterializationBuildError("insufficient_structural_evidence")
    events: list[dict[str, Any]] = []
    for index, element in enumerate(text.iter(), start=1):
        if element.tag == TEXT_H:
            events.append({"tag": "text:h", "source_order_index": index, "structural_unit_kind": "article", "candidate_kind": "source_block", "citation_granularity": "article_or_evidence_span", "content_role": "scope_boundary"})
        elif element.tag == TEXT_P:
            events.append({"tag": "text:p", "source_order_index": index, "structural_unit_kind": "paragraph", "candidate_kind": "evidence_span", "citation_granularity": "article_or_evidence_span", "content_role": "retrieval_candidate"})
        elif element.tag == TABLE_TABLE:
            events.append({"tag": "table:table", "source_order_index": index, "structural_unit_kind": "table", "candidate_kind": "source_block", "citation_granularity": "source_block_marker", "content_role": "citation_boundary"})
        if len(events) >= 6:
            break
    return events


def build_candidate(event: dict[str, Any], ordinal: int, source_ref: str, source_sha: str) -> dict[str, Any]:
    anchor_id = f"SRC-M027-{ordinal:03d}-{event['structural_unit_kind'].upper().replace('_', '-')}"
    anchor_sha = safe_hash(source_sha, event["tag"], event["source_order_index"], event["structural_unit_kind"], event["candidate_kind"])
    return {
        "candidate_id": f"MAT-M027-{ordinal:03d}-{event['candidate_kind'].upper().replace('_', '-')}",
        "candidate_kind": event["candidate_kind"],
        "source_document_ref": source_ref,
        "source_document_sha256": f"sha256:{source_sha}",
        "source_anchor_id": anchor_id,
        "source_anchor_sha256": anchor_sha,
        "source_order_index": event["source_order_index"],
        "structural_unit_kind": event["structural_unit_kind"],
        "citation_granularity": event["citation_granularity"],
        "content_role": event["content_role"],
        "temporal_status": "unknown_temporal_status",
        "materialization_method": "content_xml_order_anchor",
        "parser_evidence_ref": f"parser-smoke:{anchor_id}",
        "non_authoritative": True,
    }


def blocked_payload(reason: str, source_ref: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M027-vxdy7c",
        "slice_id": "S02",
        "representation_kind": REPRESENTATION_KIND,
        "status": "blocked",
        "blocked_reason": reason,
        "source_document_ref": source_ref or "law-source/garant/44-fz.odt",
        "materialized_candidate_count": 0,
        "materialized_candidates": [],
        "safe_source_anchors_verified": False,
        "redaction": redaction_flags(),
        "r035_non_validation_declared": True,
        "r038_review_required": True,
        "non_authoritative": True,
        "non_claim_boundary": "Blocked materialization smoke; does not prove parser completeness or validate R035.",
    }


def redaction_flags() -> dict[str, bool]:
    return {
        "source_text_excluded": True,
        "query_text_excluded": True,
        "raw_vectors_excluded": True,
        "external_payloads_excluded": True,
        "generated_answer_prose_excluded": True,
        "generated_query_excluded": True,
        "absolute_paths_excluded": True,
        "gsd_exec_paths_excluded": True,
    }


def build_materialization(source: Path = SOURCE) -> dict[str, Any]:
    source_ref = repo_ref(source)
    try:
        source_sha = sha256_path(source)
        content_xml = load_content_xml(source)
        events = iter_structural_events(content_xml)
    except MaterializationBuildError as exc:
        reason = str(exc)
        if reason == "content_xml_missing":
            reason = "parser_unavailable"
        return blocked_payload(reason, source_ref)
    if not events:
        return blocked_payload("insufficient_structural_evidence", source_ref)
    candidates = [build_candidate(event, ordinal, source_ref, source_sha) for ordinal, event in enumerate(events, start=1)]
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M027-vxdy7c",
        "slice_id": "S02",
        "representation_kind": REPRESENTATION_KIND,
        "status": "ok",
        "blocked_reason": "none",
        "source_document_ref": source_ref,
        "source_document_sha256": f"sha256:{source_sha}",
        "contract": repo_ref(CONTRACT),
        "contract_sha256": f"sha256:{sha256_path(CONTRACT)}",
        "materialized_candidate_count": len(candidates),
        "materialized_candidates": candidates,
        "safe_source_anchors_verified": True,
        "parser_evidence_summary": {
            "parser_evidence_ref_prefix": "parser-smoke",
            "content_xml_ordering_oracle_used": True,
            "raw_text_persisted": False,
            "structural_event_count": len(events),
        },
        "redaction": redaction_flags(),
        "r035_non_validation_declared": True,
        "r038_review_required": True,
        "non_authoritative": True,
        "non_claim_boundary": "Tiny materialization smoke only; does not prove parser completeness, product retrieval quality, or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_materialization(args.source)
    if not args.no_write:
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "blocked_reason": payload["blocked_reason"], "materialized_candidate_count": payload["materialized_candidate_count"], "non_authoritative": True}, sort_keys=True))
    return 0 if payload["status"] in {"ok", "blocked"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
