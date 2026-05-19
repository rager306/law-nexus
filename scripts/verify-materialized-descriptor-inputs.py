#!/usr/bin/env python3
"""Verify M027 materialized-derived safe descriptor inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json"
SCHEMA_VERSION = "materialized-descriptor-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_v1"
DERIVATION_FIELDS = {
    "candidate_kind",
    "structural_unit_kind",
    "citation_granularity",
    "content_role",
    "temporal_status",
    "materialization_method",
    "source_order_index_bucket",
}
ALLOWED_ROOT_FIELDS = {
    "allowed_descriptor_fields",
    "candidate_descriptor_count",
    "candidate_descriptors",
    "derivation_fields",
    "materialization_source",
    "materialization_source_sha256",
    "materialization_verification_summary",
    "milestone_id",
    "non_authoritative",
    "non_claim_boundary",
    "query_descriptor_count",
    "query_descriptors",
    "r035_non_validation_declared",
    "r038_review_required",
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
    "materialized_candidate_ref",
    "non_authoritative",
    "query_hash_ref",
    "query_id",
    "representation_kind",
    "source_anchor_ref",
    "source_anchor_sha256",
}
ALLOWED_CANDIDATE_FIELDS = {
    "candidate_id",
    "case_id",
    "descriptor_input_id",
    "descriptor_tokens",
    "descriptors",
    "materialized_candidate_ref",
    "non_authoritative",
    "query_id",
    "representation_kind",
    "source_anchor_ref",
    "source_anchor_sha256",
    "source_record_ids",
}
REQUIRED_REDACTION = {
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
SAFE_TOKEN_RE = re.compile(r"^[a-z_]+:[a-z0-9_]+$")
SAFE_ENUM_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SAFE_CASE_RE = re.compile(r"^CASE-M027-MAT-[0-9]{3}$")
SAFE_QUERY_RE = re.compile(r"^QUERY-M027-MAT-[0-9]{3}$")
SAFE_DESCRIPTOR_ID_RE = re.compile(r"^MAT-DESC[QC]-M027-[0-9]{3}$")
SAFE_CANDIDATE_ID_RE = re.compile(r"^DESC-CAND-M027-[0-9]{3}$")
SAFE_MATERIALIZED_REF_RE = re.compile(r"^MAT-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_ANCHOR_REF_RE = re.compile(r"^SRC-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class MaterializedDescriptorInputError(RuntimeError):
    """Raised when materialized descriptor input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaterializedDescriptorInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise MaterializedDescriptorInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise MaterializedDescriptorInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise MaterializedDescriptorInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise MaterializedDescriptorInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise MaterializedDescriptorInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise MaterializedDescriptorInputError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise MaterializedDescriptorInputError("unsafe durable vocabulary")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping) or set(allowed) != DERIVATION_FIELDS:
        raise MaterializedDescriptorInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise MaterializedDescriptorInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise MaterializedDescriptorInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise MaterializedDescriptorInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    return normalized


def validate_descriptors(descriptors: Any, tokens: Any, allowed: Mapping[str, set[str]], input_id: str) -> None:
    if not isinstance(descriptors, Mapping) or set(descriptors) != DERIVATION_FIELDS:
        raise MaterializedDescriptorInputError(f"descriptor field mismatch: {input_id}")
    expected_tokens: list[str] = []
    for field in sorted(DERIVATION_FIELDS):
        value = descriptors.get(field)
        if not isinstance(value, str) or value not in allowed[field]:
            raise MaterializedDescriptorInputError(f"descriptor enum not allowed: {input_id}: {field}")
        token = f"{field}:{value}"
        if not SAFE_TOKEN_RE.fullmatch(token):
            raise MaterializedDescriptorInputError(f"unsafe descriptor token: {input_id}: {field}")
        expected_tokens.append(token)
    if not isinstance(tokens, list) or sorted(tokens) != expected_tokens:
        raise MaterializedDescriptorInputError(f"descriptor token mismatch: {input_id}")


def validate_common_descriptor(item: Mapping[str, Any], allowed: Mapping[str, set[str]], materialized_refs: set[str], anchor_refs: set[str]) -> None:
    input_id = str(item.get("descriptor_input_id"))
    if not SAFE_DESCRIPTOR_ID_RE.fullmatch(input_id):
        raise MaterializedDescriptorInputError(f"unsafe descriptor id: {input_id}")
    if not isinstance(item.get("case_id"), str) or not SAFE_CASE_RE.fullmatch(item["case_id"]):
        raise MaterializedDescriptorInputError(f"unsafe case id: {input_id}")
    if not isinstance(item.get("query_id"), str) or not SAFE_QUERY_RE.fullmatch(item["query_id"]):
        raise MaterializedDescriptorInputError(f"unsafe query id: {input_id}")
    if item.get("representation_kind") != REPRESENTATION_KIND:
        raise MaterializedDescriptorInputError(f"representation mismatch: {input_id}")
    materialized_ref = item.get("materialized_candidate_ref")
    anchor_ref = item.get("source_anchor_ref")
    if not isinstance(materialized_ref, str) or not SAFE_MATERIALIZED_REF_RE.fullmatch(materialized_ref):
        raise MaterializedDescriptorInputError(f"unsafe materialized ref: {input_id}")
    if not isinstance(anchor_ref, str) or not SAFE_ANCHOR_REF_RE.fullmatch(anchor_ref):
        raise MaterializedDescriptorInputError(f"unsafe source anchor ref: {input_id}")
    if materialized_ref in materialized_refs and anchor_ref in anchor_refs:
        raise MaterializedDescriptorInputError(f"duplicate descriptor source ref: {input_id}")
    materialized_refs.add(materialized_ref)
    anchor_refs.add(anchor_ref)
    if not isinstance(item.get("source_anchor_sha256"), str) or not SAFE_HASH_RE.fullmatch(item["source_anchor_sha256"]):
        raise MaterializedDescriptorInputError(f"source anchor hash mismatch: {input_id}")
    if item.get("non_authoritative") is not True:
        raise MaterializedDescriptorInputError(f"non-authoritative marker missing: {input_id}")
    validate_descriptors(item.get("descriptors"), item.get("descriptor_tokens"), allowed, input_id)


def validate_query(item: Any, allowed: Mapping[str, set[str]], materialized_refs: set[str], anchor_refs: set[str]) -> None:
    if not isinstance(item, Mapping) or set(item) != ALLOWED_QUERY_FIELDS:
        raise MaterializedDescriptorInputError("query descriptor field mismatch")
    validate_common_descriptor(item, allowed, materialized_refs, anchor_refs)
    if not isinstance(item.get("query_hash_ref"), str) or not SAFE_HASH_RE.fullmatch(item["query_hash_ref"]):
        raise MaterializedDescriptorInputError("query hash ref mismatch")


def validate_candidate(item: Any, allowed: Mapping[str, set[str]], materialized_refs: set[str], anchor_refs: set[str]) -> None:
    if not isinstance(item, Mapping) or set(item) != ALLOWED_CANDIDATE_FIELDS:
        raise MaterializedDescriptorInputError("candidate descriptor field mismatch")
    validate_common_descriptor(item, allowed, materialized_refs, anchor_refs)
    if not isinstance(item.get("candidate_id"), str) or not SAFE_CANDIDATE_ID_RE.fullmatch(item["candidate_id"]):
        raise MaterializedDescriptorInputError("candidate id mismatch")
    source_record_ids = item.get("source_record_ids")
    if not isinstance(source_record_ids, list) or source_record_ids != [item.get("materialized_candidate_ref")]:
        raise MaterializedDescriptorInputError("source record id mismatch")


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    unexpected = set(manifest) - ALLOWED_ROOT_FIELDS
    if unexpected:
        raise MaterializedDescriptorInputError(f"unexpected root fields: {sorted(unexpected)}")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise MaterializedDescriptorInputError("schema or representation mismatch")
    if manifest.get("milestone_id") != "M027-vxdy7c" or manifest.get("slice_id") != "S03":
        raise MaterializedDescriptorInputError("milestone or slice marker mismatch")
    if set(manifest.get("derivation_fields", [])) != DERIVATION_FIELDS:
        raise MaterializedDescriptorInputError("derivation field mismatch")
    source = manifest.get("materialization_source")
    if not isinstance(source, str) or sha256_path(repo_path(source)) != manifest.get("materialization_source_sha256"):
        raise MaterializedDescriptorInputError("materialization source hash mismatch")
    summary = manifest.get("materialization_verification_summary")
    if not isinstance(summary, Mapping) or summary.get("status") != "ok" or summary.get("artifact_status") != "ok":
        raise MaterializedDescriptorInputError("materialization verification summary mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or set(redaction) != REQUIRED_REDACTION or any(value is not True for value in redaction.values()):
        raise MaterializedDescriptorInputError("redaction flags mismatch")
    if manifest.get("r035_non_validation_declared") is not True or manifest.get("r038_review_required") is not True:
        raise MaterializedDescriptorInputError("lifecycle boundary marker missing")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    queries = manifest.get("query_descriptors")
    candidates = manifest.get("candidate_descriptors")
    if not isinstance(queries, list) or not isinstance(candidates, list):
        raise MaterializedDescriptorInputError("descriptor arrays missing")
    if manifest.get("query_descriptor_count") != len(queries) or manifest.get("candidate_descriptor_count") != len(candidates):
        raise MaterializedDescriptorInputError("descriptor count mismatch")
    query_refs: set[str] = set()
    query_anchors: set[str] = set()
    candidate_refs: set[str] = set()
    candidate_anchors: set[str] = set()
    for item in queries:
        validate_query(item, allowed, query_refs, query_anchors)
    for item in candidates:
        validate_candidate(item, allowed, candidate_refs, candidate_anchors)
    if query_refs != candidate_refs or query_anchors != candidate_anchors:
        raise MaterializedDescriptorInputError("query/candidate materialized refs mismatch")
    boundary = manifest.get("non_claim_boundary")
    if not isinstance(boundary, str) or "does not validate R035" not in boundary:
        raise MaterializedDescriptorInputError("non-claim boundary missing")
    return {
        "schema_version": "materialized-descriptor-inputs-verification/v1",
        "status": "ok",
        "representation_kind": REPRESENTATION_KIND,
        "query_descriptor_count": len(queries),
        "candidate_descriptor_count": len(candidates),
        "derivation_fields_verified": sorted(DERIVATION_FIELDS),
        "source_materialization_verified": True,
        "non_authoritative": True,
        "non_claim_boundary": "Descriptor input verification only; does not validate R035 or prove retrieval quality.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_manifest(args.manifest)
    except MaterializedDescriptorInputError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
