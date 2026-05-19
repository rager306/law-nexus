#!/usr/bin/env python3
"""Verify M026 held-out safe semantic descriptor input manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json"
SCHEMA_VERSION = "held-out-semantic-descriptor-inputs/v1"
REPRESENTATION_KIND = "safe_semantic_descriptor_v1"
ALLOWED_ROOT_FIELDS = {
    "allowed_descriptor_fields",
    "candidate_descriptor_count",
    "candidate_descriptors",
    "contract",
    "contract_sha256",
    "held_out_case_independence_required",
    "m022_acceptance_case_reuse_forbidden",
    "m025_design_case_reuse_forbidden",
    "milestone_id",
    "non_authoritative",
    "non_claim_boundary",
    "query_descriptor_count",
    "query_descriptors",
    "redaction",
    "representation_kind",
    "schema_version",
    "slice_id",
}
ALLOWED_QUERY_FIELDS = {
    "case_id",
    "descriptor_input_id",
    "descriptor_tokens",
    "descriptors",
    "non_authoritative",
    "query_hash_ref",
    "query_id",
    "representation_kind",
}
ALLOWED_CANDIDATE_FIELDS = {
    "candidate_id",
    "case_id",
    "descriptor_input_id",
    "descriptor_tokens",
    "descriptors",
    "non_authoritative",
    "query_id",
    "representation_kind",
    "source_hash_ref",
    "source_record_ids",
}
QUERY_DESCRIPTOR_FIELDS = {
    "actor_role",
    "ambiguity_handling",
    "citation_granularity",
    "document_scope",
    "obligation_type",
    "procurement_phase",
    "query_intent",
    "safety_boundary",
    "temporal_status",
    "topic_class",
}
CANDIDATE_DESCRIPTOR_FIELDS = {
    "actor_role",
    "ambiguity_handling",
    "candidate_role",
    "citation_binding_status",
    "citation_granularity",
    "document_scope",
    "obligation_type",
    "procurement_phase",
    "safety_boundary",
    "temporal_status",
    "topic_class",
}
FORBIDDEN_FIELD_NAMES = {
    "raw_legal_text",
    "raw_text",
    "source_excerpt",
    "source_excerpts",
    "query_text",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_response_body",
    "secret",
    "secrets",
    "vector",
    "vectors",
    "embedding",
    "embedding_vector",
    "runtime_row",
    "falkordb_row",
    "generated_answer_prose",
    "generated_query",
    "generated_cypher",
    "legal_advice",
    "llm_reasoning",
    "expected_label",
    "expected_rank",
    "rank",
    "expected_candidate_ids",
    "expected_rejected_candidate_ids",
    "expected_diagnostic_codes",
    "selection_reason",
    "expected_result",
}
FORBIDDEN_STRING_FRAGMENTS = (
    "Федеральный закон",
    "Статья ",
    "raw_legal_text",
    "source_excerpt",
    "provider_payload",
    "embedding_vector",
    "expected_label",
    "expected_candidate_ids",
    "Bearer ",
    "BEGIN PRIVATE KEY",
    "api_key",
    ".gsd/exec",
    "/root/",
    "/tmp/",
)
FORBIDDEN_ID_PREFIXES = ("CASE-M022-", "QUERY-M022-", "CAND-M022-", "DESCQ-M025-", "DESCC-M025-")
SAFE_TOKEN_RE = re.compile(r"^[a-z_]+:[a-z0-9_]+$")
SAFE_ENUM_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SAFE_M026_ID_RE = re.compile(r"^(CASE|QUERY|CAND)-M026-[A-Z0-9-]+$")
SAFE_DESCRIPTOR_ID_RE = re.compile(r"^HO-DESC[QC]-M026-[A-Z0-9-]+$")
SAFE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class HeldOutDescriptorInputError(RuntimeError):
    """Raised when held-out descriptor input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HeldOutDescriptorInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise HeldOutDescriptorInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise HeldOutDescriptorInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise HeldOutDescriptorInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise HeldOutDescriptorInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise HeldOutDescriptorInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise HeldOutDescriptorInputError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise HeldOutDescriptorInputError("unsafe durable vocabulary")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping):
        raise HeldOutDescriptorInputError("allowed_descriptor_fields must be object")
    expected = QUERY_DESCRIPTOR_FIELDS | CANDIDATE_DESCRIPTOR_FIELDS
    if set(allowed) != expected:
        raise HeldOutDescriptorInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise HeldOutDescriptorInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise HeldOutDescriptorInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise HeldOutDescriptorInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    return normalized


def validate_descriptors(descriptors: Any, fields: set[str], allowed: Mapping[str, set[str]], input_id: str) -> None:
    if not isinstance(descriptors, Mapping):
        raise HeldOutDescriptorInputError(f"descriptors missing: {input_id}")
    if set(descriptors) != fields:
        raise HeldOutDescriptorInputError(f"descriptor field mismatch: {input_id}")
    for field, value in descriptors.items():
        if not isinstance(value, str):
            raise HeldOutDescriptorInputError(f"descriptor value must be string: {input_id}: {field}")
        if not SAFE_ENUM_RE.fullmatch(value):
            raise HeldOutDescriptorInputError(f"unsafe descriptor enum grammar: {input_id}: {field}")
        if value not in allowed[field]:
            raise HeldOutDescriptorInputError(f"descriptor enum not allowed: {input_id}: {field}")


def validate_tokens(tokens: Any, descriptors: Mapping[str, Any], input_id: str) -> None:
    if not isinstance(tokens, list) or not tokens:
        raise HeldOutDescriptorInputError(f"descriptor tokens missing: {input_id}")
    expected = {f"{field}:{value}" for field, value in descriptors.items()}
    observed: set[str] = set()
    for token in tokens:
        if not isinstance(token, str) or not SAFE_TOKEN_RE.fullmatch(token):
            raise HeldOutDescriptorInputError(f"unsafe descriptor token grammar: {input_id}")
        field, value = token.split(":", 1)
        if descriptors.get(field) != value:
            raise HeldOutDescriptorInputError(f"descriptor token mismatch: {input_id}")
        observed.add(token)
    if observed != expected:
        raise HeldOutDescriptorInputError(f"descriptor token coverage mismatch: {input_id}")


def assert_no_forbidden_id_reuse(*ids: str) -> None:
    for identifier in ids:
        for prefix in FORBIDDEN_ID_PREFIXES:
            if identifier.startswith(prefix):
                raise HeldOutDescriptorInputError(f"forbidden acceptance id reuse: {identifier}")


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    unexpected = set(manifest) - ALLOWED_ROOT_FIELDS
    if unexpected:
        raise HeldOutDescriptorInputError(f"unexpected root fields: {sorted(unexpected)}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise HeldOutDescriptorInputError("schema_version mismatch")
    if manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise HeldOutDescriptorInputError("representation_kind mismatch")
    if manifest.get("milestone_id") != "M026-1uqmzc" or manifest.get("slice_id") != "S02":
        raise HeldOutDescriptorInputError("milestone or slice marker mismatch")
    for marker in ("held_out_case_independence_required", "m025_design_case_reuse_forbidden", "m022_acceptance_case_reuse_forbidden"):
        if manifest.get(marker) is not True:
            raise HeldOutDescriptorInputError(f"independence marker missing: {marker}")
    if not isinstance(manifest.get("contract"), str):
        raise HeldOutDescriptorInputError("missing contract path")
    if sha256_path(repo_path(manifest["contract"])) != manifest.get("contract_sha256"):
        raise HeldOutDescriptorInputError("sha256 mismatch: contract")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    query_descriptors = manifest.get("query_descriptors")
    candidate_descriptors = manifest.get("candidate_descriptors")
    if not isinstance(query_descriptors, list) or not isinstance(candidate_descriptors, list):
        raise HeldOutDescriptorInputError("descriptor inputs must be lists")
    if manifest.get("query_descriptor_count") != len(query_descriptors) or manifest.get("candidate_descriptor_count") != len(candidate_descriptors):
        raise HeldOutDescriptorInputError("descriptor count mismatch")
    if len(query_descriptors) < 3 or len(candidate_descriptors) < len(query_descriptors):
        raise HeldOutDescriptorInputError("held-out descriptor coverage mismatch")
    seen_ids: set[str] = set()
    query_case_ids: set[str] = set()
    query_ids: set[str] = set()
    for item in query_descriptors:
        if not isinstance(item, Mapping):
            raise HeldOutDescriptorInputError("query descriptor must be object")
        unexpected_query_fields = set(item) - ALLOWED_QUERY_FIELDS
        if unexpected_query_fields:
            raise HeldOutDescriptorInputError(f"unexpected query fields: {sorted(unexpected_query_fields)}")
        case_id = str(item.get("case_id"))
        query_id = str(item.get("query_id"))
        descriptor_id = str(item.get("descriptor_input_id"))
        assert_no_forbidden_id_reuse(case_id, query_id, descriptor_id)
        if not SAFE_M026_ID_RE.fullmatch(case_id) or not SAFE_M026_ID_RE.fullmatch(query_id):
            raise HeldOutDescriptorInputError(f"unsafe M026 query id: {descriptor_id}")
        if not SAFE_DESCRIPTOR_ID_RE.fullmatch(descriptor_id):
            raise HeldOutDescriptorInputError(f"unsafe descriptor id: {descriptor_id}")
        if item.get("representation_kind") != REPRESENTATION_KIND or item.get("non_authoritative") is not True:
            raise HeldOutDescriptorInputError(f"query descriptor boundary mismatch: {descriptor_id}")
        if not isinstance(item.get("query_hash_ref"), str) or not SAFE_HASH_RE.fullmatch(item["query_hash_ref"]):
            raise HeldOutDescriptorInputError(f"query hash missing: {descriptor_id}")
        if descriptor_id in seen_ids:
            raise HeldOutDescriptorInputError(f"duplicate descriptor id: {descriptor_id}")
        seen_ids.add(descriptor_id)
        query_case_ids.add(case_id)
        query_ids.add(query_id)
        descriptors = item.get("descriptors")
        if not isinstance(descriptors, Mapping):
            raise HeldOutDescriptorInputError(f"descriptors missing: {descriptor_id}")
        validate_descriptors(descriptors, QUERY_DESCRIPTOR_FIELDS, allowed, descriptor_id)
        validate_tokens(item.get("descriptor_tokens"), descriptors, descriptor_id)
    candidate_case_ids: set[str] = set()
    for item in candidate_descriptors:
        if not isinstance(item, Mapping):
            raise HeldOutDescriptorInputError("candidate descriptor must be object")
        unexpected_candidate_fields = set(item) - ALLOWED_CANDIDATE_FIELDS
        if unexpected_candidate_fields:
            raise HeldOutDescriptorInputError(f"unexpected candidate fields: {sorted(unexpected_candidate_fields)}")
        case_id = str(item.get("case_id"))
        query_id = str(item.get("query_id"))
        candidate_id = str(item.get("candidate_id"))
        descriptor_id = str(item.get("descriptor_input_id"))
        assert_no_forbidden_id_reuse(case_id, query_id, candidate_id, descriptor_id)
        if not SAFE_M026_ID_RE.fullmatch(case_id) or not SAFE_M026_ID_RE.fullmatch(query_id) or not SAFE_M026_ID_RE.fullmatch(candidate_id):
            raise HeldOutDescriptorInputError(f"unsafe M026 candidate id: {descriptor_id}")
        if not SAFE_DESCRIPTOR_ID_RE.fullmatch(descriptor_id):
            raise HeldOutDescriptorInputError(f"unsafe descriptor id: {descriptor_id}")
        if case_id not in query_case_ids or query_id not in query_ids:
            raise HeldOutDescriptorInputError(f"candidate without query coverage: {descriptor_id}")
        if item.get("representation_kind") != REPRESENTATION_KIND or item.get("non_authoritative") is not True:
            raise HeldOutDescriptorInputError(f"candidate descriptor boundary mismatch: {descriptor_id}")
        source_record_ids = item.get("source_record_ids")
        if not isinstance(source_record_ids, list) or not source_record_ids:
            raise HeldOutDescriptorInputError(f"source record ids missing: {descriptor_id}")
        for source_id in source_record_ids:
            if not isinstance(source_id, str) or not re.fullmatch(r"^HELDOUT-SRC-M026-[A-Z0-9-]+$", source_id):
                raise HeldOutDescriptorInputError(f"unsafe source record id: {descriptor_id}")
        if not isinstance(item.get("source_hash_ref"), str) or not SAFE_HASH_RE.fullmatch(item["source_hash_ref"]):
            raise HeldOutDescriptorInputError(f"source hash missing: {descriptor_id}")
        if descriptor_id in seen_ids:
            raise HeldOutDescriptorInputError(f"duplicate descriptor id: {descriptor_id}")
        seen_ids.add(descriptor_id)
        candidate_case_ids.add(case_id)
        descriptors = item.get("descriptors")
        if not isinstance(descriptors, Mapping):
            raise HeldOutDescriptorInputError(f"descriptors missing: {descriptor_id}")
        validate_descriptors(descriptors, CANDIDATE_DESCRIPTOR_FIELDS, allowed, descriptor_id)
        validate_tokens(item.get("descriptor_tokens"), descriptors, descriptor_id)
    if candidate_case_ids != query_case_ids:
        raise HeldOutDescriptorInputError("case coverage mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping):
        raise HeldOutDescriptorInputError("redaction flags missing")
    required_redaction = {
        "source_text_excluded",
        "query_text_excluded",
        "raw_vectors_excluded",
        "external_payloads_excluded",
        "generated_answer_prose_excluded",
        "generated_query_excluded",
        "expected_answer_fields_excluded_from_descriptor_inputs",
        "absolute_paths_excluded",
        "gsd_exec_paths_excluded",
    }
    if set(redaction) != required_redaction or any(value is not True for value in redaction.values()):
        raise HeldOutDescriptorInputError("redaction flags mismatch")
    boundary = manifest.get("non_claim_boundary")
    if not isinstance(boundary, str) or "does not prove semantic retrieval quality" not in boundary or "validate R035" not in boundary:
        raise HeldOutDescriptorInputError("non-claim boundary missing")
    return {
        "schema_version": "held-out-semantic-descriptor-inputs-verification/v1",
        "status": "ok",
        "representation_kind": REPRESENTATION_KIND,
        "query_descriptor_count": len(query_descriptors),
        "candidate_descriptor_count": len(candidate_descriptors),
        "held_out_case_independence_required": True,
        "diagnostic_codes": ["held_out_semantic_descriptors_verified"],
        "non_authoritative": True,
        "non_claim_boundary": "Held-out safe descriptor inputs only; does not prove semantic retrieval quality or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_manifest(args.manifest)
    except HeldOutDescriptorInputError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
