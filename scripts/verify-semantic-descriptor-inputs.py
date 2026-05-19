#!/usr/bin/env python3
"""Verify M025 safe semantic descriptor input manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json"
SCHEMA_VERSION = "semantic-descriptor-inputs/v1"
REPRESENTATION_KIND = "safe_semantic_descriptor_v1"
ALLOWED_ROOT_FIELDS = {
    "allowed_descriptor_fields",
    "candidate_descriptor_count",
    "candidate_descriptors",
    "contract",
    "contract_sha256",
    "milestone_id",
    "non_authoritative",
    "non_claim_boundary",
    "query_descriptor_count",
    "query_descriptors",
    "redaction",
    "representation_kind",
    "schema_version",
    "slice_id",
    "source_fixture",
    "source_fixture_sha256",
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
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class DescriptorInputError(RuntimeError):
    """Raised when descriptor input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DescriptorInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise DescriptorInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise DescriptorInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise DescriptorInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise DescriptorInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise DescriptorInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise DescriptorInputError(f"unsafe payload fragment: {fragment}")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping):
        raise DescriptorInputError("allowed_descriptor_fields must be object")
    expected = QUERY_DESCRIPTOR_FIELDS | CANDIDATE_DESCRIPTOR_FIELDS
    if set(allowed) != expected:
        raise DescriptorInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise DescriptorInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise DescriptorInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise DescriptorInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    return normalized


def validate_descriptors(descriptors: Any, fields: set[str], allowed: Mapping[str, set[str]], input_id: str) -> None:
    if not isinstance(descriptors, Mapping):
        raise DescriptorInputError(f"descriptors missing: {input_id}")
    if set(descriptors) != fields:
        raise DescriptorInputError(f"descriptor field mismatch: {input_id}")
    for field, value in descriptors.items():
        if not isinstance(value, str):
            raise DescriptorInputError(f"descriptor value must be string: {input_id}: {field}")
        if not SAFE_ENUM_RE.fullmatch(value):
            raise DescriptorInputError(f"unsafe descriptor enum grammar: {input_id}: {field}")
        if value not in allowed[field]:
            raise DescriptorInputError(f"descriptor enum not allowed: {input_id}: {field}")


def validate_tokens(tokens: Any, descriptors: Mapping[str, Any], input_id: str) -> None:
    if not isinstance(tokens, list) or not tokens:
        raise DescriptorInputError(f"descriptor tokens missing: {input_id}")
    expected = {f"{field}:{value}" for field, value in descriptors.items()}
    observed: set[str] = set()
    for token in tokens:
        if not isinstance(token, str) or not SAFE_TOKEN_RE.fullmatch(token):
            raise DescriptorInputError(f"unsafe descriptor token grammar: {input_id}")
        field, value = token.split(":", 1)
        if descriptors.get(field) != value:
            raise DescriptorInputError(f"descriptor token mismatch: {input_id}")
        observed.add(token)
    if observed != expected:
        raise DescriptorInputError(f"descriptor token coverage mismatch: {input_id}")


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    unexpected = set(manifest) - ALLOWED_ROOT_FIELDS
    if unexpected:
        raise DescriptorInputError(f"unexpected root fields: {sorted(unexpected)}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise DescriptorInputError("schema_version mismatch")
    if manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise DescriptorInputError("representation_kind mismatch")
    for field in ("source_fixture", "contract"):
        if not isinstance(manifest.get(field), str):
            raise DescriptorInputError(f"missing path field: {field}")
        repo_path(manifest[field])
    for path_field, hash_field in (("source_fixture", "source_fixture_sha256"), ("contract", "contract_sha256")):
        if sha256_path(repo_path(manifest[path_field])) != manifest.get(hash_field):
            raise DescriptorInputError(f"sha256 mismatch: {path_field}")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    query_descriptors = manifest.get("query_descriptors")
    candidate_descriptors = manifest.get("candidate_descriptors")
    if not isinstance(query_descriptors, list) or not isinstance(candidate_descriptors, list):
        raise DescriptorInputError("descriptor inputs must be lists")
    if manifest.get("query_descriptor_count") != len(query_descriptors) or manifest.get("candidate_descriptor_count") != len(candidate_descriptors):
        raise DescriptorInputError("descriptor count mismatch")
    if len(query_descriptors) != 10 or len(candidate_descriptors) != 10:
        raise DescriptorInputError("representative descriptor coverage mismatch")
    seen_ids: set[str] = set()
    query_case_ids: set[str] = set()
    for item in query_descriptors:
        if not isinstance(item, Mapping):
            raise DescriptorInputError("query descriptor must be object")
        unexpected_query = set(item) - ALLOWED_QUERY_FIELDS
        if unexpected_query:
            raise DescriptorInputError(f"unexpected query descriptor fields: {sorted(unexpected_query)}")
        input_id = str(item.get("descriptor_input_id", ""))
        if not input_id.startswith("DESCQ-M025-") or input_id in seen_ids:
            raise DescriptorInputError(f"bad descriptor input id: {input_id}")
        seen_ids.add(input_id)
        query_case_ids.add(str(item.get("case_id")))
        if item.get("representation_kind") != REPRESENTATION_KIND:
            raise DescriptorInputError(f"bad query representation kind: {input_id}")
        query_hash = item.get("query_hash_ref")
        if not isinstance(query_hash, str) or len(query_hash) != 64 or not re.fullmatch(r"[a-f0-9]{64}", query_hash):
            raise DescriptorInputError(f"bad query hash ref: {input_id}")
        validate_descriptors(item.get("descriptors"), QUERY_DESCRIPTOR_FIELDS, allowed, input_id)
        validate_tokens(item.get("descriptor_tokens"), item["descriptors"], input_id)
    candidate_case_ids: set[str] = set()
    for item in candidate_descriptors:
        if not isinstance(item, Mapping):
            raise DescriptorInputError("candidate descriptor must be object")
        unexpected_candidate = set(item) - ALLOWED_CANDIDATE_FIELDS
        if unexpected_candidate:
            raise DescriptorInputError(f"unexpected candidate descriptor fields: {sorted(unexpected_candidate)}")
        input_id = str(item.get("descriptor_input_id", ""))
        if not input_id.startswith("DESCC-M025-") or input_id in seen_ids:
            raise DescriptorInputError(f"bad descriptor input id: {input_id}")
        seen_ids.add(input_id)
        candidate_case_ids.add(str(item.get("case_id")))
        if item.get("representation_kind") != REPRESENTATION_KIND:
            raise DescriptorInputError(f"bad candidate representation kind: {input_id}")
        if not isinstance(item.get("candidate_id"), str) or not item["candidate_id"]:
            raise DescriptorInputError(f"missing candidate id: {input_id}")
        if not isinstance(item.get("source_record_ids"), list):
            raise DescriptorInputError(f"bad source_record_ids: {input_id}")
        validate_descriptors(item.get("descriptors"), CANDIDATE_DESCRIPTOR_FIELDS, allowed, input_id)
        validate_tokens(item.get("descriptor_tokens"), item["descriptors"], input_id)
    if not candidate_case_ids.issubset(query_case_ids):
        raise DescriptorInputError("candidate/query descriptor coverage mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or not all(value is True for value in redaction.values()):
        raise DescriptorInputError("redaction flags must all be true")
    return {
        "status": "ok",
        "schema_version": "semantic-descriptor-inputs-verification/v1",
        "representation_kind": REPRESENTATION_KIND,
        "query_descriptor_count": len(query_descriptors),
        "candidate_descriptor_count": len(candidate_descriptors),
        "diagnostic_codes": ["semantic_descriptors_verified"],
        "non_authoritative": True,
        "non_claim_boundary": "Safe descriptor inputs only; does not prove semantic retrieval quality or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_manifest(args.manifest)
    except DescriptorInputError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
