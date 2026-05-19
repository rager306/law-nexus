#!/usr/bin/env python3
"""Build M025 safe semantic descriptor inputs from non-answer structural fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
DEFAULT_CONTRACT = ROOT / "prd/research/ontology_architecture_requirements/44-local-semantic-scoring-iteration-contract.md"
DEFAULT_OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json"
SCHEMA_VERSION = "semantic-descriptor-inputs/v1"
REPRESENTATION_KIND = "safe_semantic_descriptor_v1"
FORBIDDEN_DERIVATION_FIELDS = {
    "expected_label",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "selection_reason",
}
ALLOWED_QUERY_SOURCE_FIELDS = {
    "case_class",
    "case_id",
    "non_authoritative",
    "query",
    "source_artifact_refs",
    "source_record_ids",
}
ALLOWED_QUERY_OBJECT_FIELDS = {
    "as_of_date",
    "expected_result",
    "query_id",
    "query_kind",
    "query_text_sha256",
    "scope_id",
}
ALLOWED_CANDIDATE_SOURCE_FIELDS = {
    "act_edition_id",
    "candidate_id",
    "citation_key",
    "evidence_span_id",
    "source_artifact",
    "source_block_id",
    "source_case_id",
    "source_record_ids",
}
QUERY_KIND_POLICY = {
    "evidence_span_lookup": {
        "query_intent": "locate_evidence_span",
        "document_scope": "evidence_span",
        "obligation_type": "retrieval_selection",
        "temporal_status": "not_applicable",
        "citation_granularity": "article_or_evidence_span",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "source_block_marker_lookup": {
        "query_intent": "locate_source_block_marker",
        "document_scope": "source_block",
        "obligation_type": "retrieval_selection",
        "temporal_status": "not_applicable",
        "citation_granularity": "source_block_marker",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "distractor_retrieval": {
        "query_intent": "resolve_granularity_conflict",
        "document_scope": "source_block",
        "obligation_type": "retrieval_selection",
        "temporal_status": "not_applicable",
        "citation_granularity": "source_block_marker",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "temporal_scoped_lookup": {
        "query_intent": "apply_temporal_scope",
        "document_scope": "act_edition",
        "obligation_type": "temporal_filtering",
        "temporal_status": "as_of_date_required",
        "citation_granularity": "document_unit",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "ambiguous_clause_lookup": {
        "query_intent": "detect_ambiguous_candidates",
        "document_scope": "clause_set",
        "obligation_type": "ambiguity_resolution",
        "temporal_status": "not_applicable",
        "citation_granularity": "document_unit",
        "ambiguity_handling": "ambiguity_resolution_required",
        "safety_boundary": "not_applicable",
    },
    "unsupported_scope_lookup": {
        "query_intent": "reject_unsupported_scope",
        "document_scope": "unsupported_scope",
        "obligation_type": "scope_rejection",
        "temporal_status": "not_applicable",
        "citation_granularity": "document_unit",
        "ambiguity_handling": "scope_outside_supported_corpus",
        "safety_boundary": "not_applicable",
    },
    "scoped_no_answer": {
        "query_intent": "detect_scoped_absence",
        "document_scope": "scope_absence",
        "obligation_type": "scope_rejection",
        "temporal_status": "not_applicable",
        "citation_granularity": "document_unit",
        "ambiguity_handling": "scoped_absence_check_required",
        "safety_boundary": "not_applicable",
    },
    "citation_binding_check": {
        "query_intent": "preserve_citation_binding",
        "document_scope": "citation_binding",
        "obligation_type": "citation_preservation",
        "temporal_status": "not_applicable",
        "citation_granularity": "complete_citation_binding",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "edition_mismatch_lookup": {
        "query_intent": "reject_edition_mismatch",
        "document_scope": "act_edition",
        "obligation_type": "temporal_filtering",
        "temporal_status": "edition_consistency_required",
        "citation_granularity": "act_edition",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "not_applicable",
    },
    "unsafe_boundary_check": {
        "query_intent": "reject_unsafe_payload_boundary",
        "document_scope": "safety_boundary",
        "obligation_type": "safety_rejection",
        "temporal_status": "not_applicable",
        "citation_granularity": "safety_boundary",
        "ambiguity_handling": "not_applicable",
        "safety_boundary": "unsafe_payload_boundary",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def portable_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return f"external-test-fixture:{path.name}"


def ensure_no_forbidden_fields(value: Any) -> None:
    if isinstance(value, Mapping):
        forbidden = set(value) & FORBIDDEN_DERIVATION_FIELDS
        if forbidden:
            raise ValueError(f"forbidden derivation fields present: {sorted(forbidden)}")
        for child in value.values():
            ensure_no_forbidden_fields(child)
    elif isinstance(value, list):
        for child in value:
            ensure_no_forbidden_fields(child)


def filtered_query_case(case: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {key: case[key] for key in ALLOWED_QUERY_SOURCE_FIELDS if key in case}
    query = allowed.get("query")
    if not isinstance(query, Mapping):
        raise ValueError("query object missing")
    allowed["query"] = {key: query[key] for key in ALLOWED_QUERY_OBJECT_FIELDS if key in query}
    return allowed


def filtered_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {key: candidate[key] for key in ALLOWED_CANDIDATE_SOURCE_FIELDS if key in candidate}


def query_policy(query_kind: str) -> dict[str, str]:
    try:
        return dict(QUERY_KIND_POLICY[query_kind])
    except KeyError as exc:
        raise ValueError(f"unsupported query_kind: {query_kind}") from exc


def candidate_granularity(candidate: Mapping[str, Any]) -> str:
    candidate_id = str(candidate.get("candidate_id", ""))
    if "MARKER" in candidate_id or "SB-" in candidate_id:
        return "source_block_marker"
    if "CLAUSE" in candidate_id:
        return "clause"
    if "EDITION" in candidate_id:
        return "act_edition"
    if "UNSAFE" in candidate_id:
        return "safety_boundary"
    if "ARTICLE" in candidate_id or str(candidate.get("evidence_span_id", "")).startswith("EV-"):
        return "article_or_evidence_span"
    return "document_unit"


def candidate_document_scope(candidate: Mapping[str, Any]) -> str:
    granularity = candidate_granularity(candidate)
    if granularity == "source_block_marker":
        return "source_block"
    if granularity == "clause":
        return "clause_set"
    if granularity == "act_edition":
        return "act_edition"
    if granularity == "safety_boundary":
        return "safety_boundary"
    if granularity == "article_or_evidence_span":
        return "article_or_evidence_span"
    return "evidence_span"


def temporal_status(candidate: Mapping[str, Any]) -> str:
    edition = str(candidate.get("act_edition_id", ""))
    if "M013" in edition or "1900" in edition:
        return "stale_or_mismatched_edition"
    if "M014" in edition or "2026" in edition:
        return "current_edition"
    return "not_applicable"


def citation_binding(candidate: Mapping[str, Any]) -> str:
    required = ("citation_key", "evidence_span_id", "source_block_id", "act_edition_id")
    if all(candidate.get(field) for field in required):
        return "complete_citation_binding"
    return "incomplete_citation_binding"


def descriptor_tokens(descriptors: Mapping[str, str]) -> list[str]:
    return [f"{field}:{value}" for field, value in sorted(descriptors.items())]


def build_manifest(fixture_path: Path = DEFAULT_FIXTURE, contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    fixture = load_json(fixture_path)
    ensure_no_forbidden_fields({"allowed_fixture_root": {key: fixture[key] for key in fixture if key != "cases"}})
    cases = fixture.get("cases")
    if not isinstance(cases, list):
        raise ValueError("fixture cases missing")
    query_descriptors: list[dict[str, Any]] = []
    candidate_descriptors: list[dict[str, Any]] = []
    for index, raw_case in enumerate(cases, start=1):
        if not isinstance(raw_case, Mapping):
            raise ValueError("case must be object")
        case = filtered_query_case(raw_case)
        ensure_no_forbidden_fields(case)
        query = case["query"]
        policy = query_policy(str(query["query_kind"]))
        qdesc = {
            "topic_class": "procurement_contracting",
            "actor_role": "retrieval_system",
            "procurement_phase": "general_44fz_retrieval",
            **policy,
        }
        query_descriptors.append(
            {
                "descriptor_input_id": f"DESCQ-M025-{index:03d}",
                "case_id": case["case_id"],
                "query_id": query["query_id"],
                "query_hash_ref": query["query_text_sha256"],
                "representation_kind": REPRESENTATION_KIND,
                "descriptors": qdesc,
                "descriptor_tokens": descriptor_tokens(qdesc),
                "non_authoritative": True,
            }
        )
        raw_candidates = raw_case.get("candidates", [])
        if not isinstance(raw_candidates, list):
            raise ValueError("candidate list malformed")
        for candidate_index, raw_candidate in enumerate(raw_candidates, start=1):
            if not isinstance(raw_candidate, Mapping):
                raise ValueError("candidate must be object")
            candidate = filtered_candidate(raw_candidate)
            ensure_no_forbidden_fields(candidate)
            cdesc = {
                "topic_class": "procurement_contracting",
                "obligation_type": policy["obligation_type"],
                "actor_role": "retrieval_system",
                "document_scope": candidate_document_scope(candidate),
                "temporal_status": temporal_status(candidate),
                "citation_granularity": candidate_granularity(candidate),
                "procurement_phase": "general_44fz_retrieval",
                "candidate_role": "candidate_document_unit",
                "ambiguity_handling": policy["ambiguity_handling"],
                "safety_boundary": policy["safety_boundary"],
                "citation_binding_status": citation_binding(candidate),
            }
            candidate_descriptors.append(
                {
                    "descriptor_input_id": f"DESCC-M025-{index:03d}-{candidate_index:02d}",
                    "case_id": case["case_id"],
                    "query_id": query["query_id"],
                    "candidate_id": candidate["candidate_id"],
                    "source_record_ids": candidate.get("source_record_ids", []),
                    "representation_kind": REPRESENTATION_KIND,
                    "descriptors": cdesc,
                    "descriptor_tokens": descriptor_tokens(cdesc),
                    "non_authoritative": True,
                }
            )
    allowed_descriptor_fields: dict[str, list[str]] = {}
    for item in query_descriptors + candidate_descriptors:
        for field, value in item["descriptors"].items():
            allowed_descriptor_fields.setdefault(field, [])
            if value not in allowed_descriptor_fields[field]:
                allowed_descriptor_fields[field].append(value)
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M025-50be7n",
        "slice_id": "S05",
        "representation_kind": REPRESENTATION_KIND,
        "contract": portable_path(contract_path),
        "contract_sha256": sha256_path(contract_path),
        "source_fixture": portable_path(fixture_path),
        "source_fixture_sha256": sha256_path(fixture_path),
        "allowed_descriptor_fields": {field: sorted(values) for field, values in sorted(allowed_descriptor_fields.items())},
        "query_descriptor_count": len(query_descriptors),
        "candidate_descriptor_count": len(candidate_descriptors),
        "query_descriptors": query_descriptors,
        "candidate_descriptors": candidate_descriptors,
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "generated_answer_prose_excluded": True,
            "generated_query_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
            "answer_fields_excluded_from_scoring_inputs": True,
            "answer_labels_excluded": True,
            "answer_ranks_excluded": True,
        },
        "non_authoritative": True,
        "non_claim_boundary": "Safe descriptor inputs only; no scoring result, no retrieval-quality validation, and no R035 validation.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_manifest(args.fixture, args.contract)
    if not args.no_write:
        args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "schema_version": manifest["schema_version"],
                "representation_kind": manifest["representation_kind"],
                "query_descriptor_count": manifest["query_descriptor_count"],
                "candidate_descriptor_count": manifest["candidate_descriptor_count"],
                "diagnostic_codes": ["semantic_descriptor_inputs_built"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
