#!/usr/bin/env python3
"""Verify M024 safe semantic retrieval input manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_retrieval_safe_inputs.json"
SCHEMA_VERSION = "semantic-retrieval-safe-inputs/v1"
ALLOWED_ROOT_FIELDS = {
    "allowed_representation_kinds",
    "candidate_input_count",
    "candidate_inputs",
    "contract",
    "milestone_id",
    "non_authoritative",
    "non_claims",
    "query_input_count",
    "query_inputs",
    "query_registry",
    "query_registry_sha256",
    "redaction",
    "schema_version",
    "slice_id",
    "source_fixture",
    "source_fixture_sha256",
    "source_provenance_manifest",
    "source_provenance_manifest_sha256",
}
ALLOWED_QUERY_FIELDS = {
    "as_of_date",
    "case_class",
    "case_id",
    "non_authoritative",
    "query_hash",
    "query_id",
    "query_kind",
    "query_provenance_ref",
    "representation_kind",
    "representation_tokens",
    "scope_id",
    "semantic_input_id",
}
ALLOWED_CANDIDATE_FIELDS = {
    "act_edition_id",
    "as_of_date",
    "candidate_id",
    "candidate_source_ref",
    "case_class",
    "case_id",
    "citation_key",
    "evidence_span_id",
    "non_authoritative",
    "query_id",
    "query_kind",
    "representation_kind",
    "representation_tokens",
    "scope_id",
    "semantic_input_id",
    "source_block_id",
    "source_provenance_ref",
    "source_record_ids",
}
ALLOWED_REPRESENTATION_KINDS = {"safe_query_token_bag_v1", "safe_candidate_token_bag_v1"}
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
ALLOWED_TOKEN_PREFIXES = {
    "as_of",
    "candidate",
    "case_class",
    "citation",
    "edition",
    "evidence_span",
    "query_hash",
    "query_kind",
    "scope",
    "source_block",
    "source_record",
}
SAFE_TOKEN_RE = re.compile(r"^[a-z_]+:[A-Za-z0-9_.-]+$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class SemanticInputError(RuntimeError):
    """Raised when safe semantic input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SemanticInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SemanticInputError("manifest root must be object")
    return payload


def resolve_repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise SemanticInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SemanticInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise SemanticInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            if ABSOLUTE_PATH_RE.search(value):
                raise SemanticInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise SemanticInputError(f"unsafe payload fragment: {fragment}")


def validate_tokens(tokens: Any, input_id: str) -> None:
    if not isinstance(tokens, list) or not tokens:
        raise SemanticInputError(f"representation tokens missing: {input_id}")
    for token in tokens:
        if not isinstance(token, str) or not token:
            raise SemanticInputError(f"invalid representation token: {input_id}")
        if not SAFE_TOKEN_RE.fullmatch(token):
            raise SemanticInputError(f"unsafe token grammar: {input_id}")
        prefix, _value = token.split(":", 1)
        if prefix not in ALLOWED_TOKEN_PREFIXES:
            raise SemanticInputError(f"unsafe token prefix: {input_id}: {prefix}")
        lowered = token.lower()
        for fragment in FORBIDDEN_STRING_FRAGMENTS:
            if fragment.lower() in lowered:
                raise SemanticInputError(f"unsafe token fragment: {input_id}: {fragment}")


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    if set(manifest) - ALLOWED_ROOT_FIELDS:
        raise SemanticInputError(f"unexpected root fields: {sorted(set(manifest) - ALLOWED_ROOT_FIELDS)}")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise SemanticInputError("schema_version mismatch")
    for field in ("source_fixture", "query_registry", "source_provenance_manifest", "contract"):
        if not isinstance(manifest.get(field), str):
            raise SemanticInputError(f"missing path field: {field}")
        resolve_repo_path(manifest[field])
    for path_field, hash_field in (
        ("source_fixture", "source_fixture_sha256"),
        ("query_registry", "query_registry_sha256"),
        ("source_provenance_manifest", "source_provenance_manifest_sha256"),
    ):
        if sha256_path(resolve_repo_path(manifest[path_field])) != manifest.get(hash_field):
            raise SemanticInputError(f"sha256 mismatch: {path_field}")
    if set(manifest.get("allowed_representation_kinds", [])) != ALLOWED_REPRESENTATION_KINDS:
        raise SemanticInputError("allowed representation kinds mismatch")
    query_inputs = manifest.get("query_inputs")
    candidate_inputs = manifest.get("candidate_inputs")
    if not isinstance(query_inputs, list) or not isinstance(candidate_inputs, list):
        raise SemanticInputError("inputs must be lists")
    if manifest.get("query_input_count") != len(query_inputs) or manifest.get("candidate_input_count") != len(candidate_inputs):
        raise SemanticInputError("input count mismatch")
    if len(query_inputs) != 10 or len(candidate_inputs) != 10:
        raise SemanticInputError("representative input coverage mismatch")
    seen_ids: set[str] = set()
    query_case_ids: set[str] = set()
    for item in query_inputs:
        if not isinstance(item, Mapping):
            raise SemanticInputError("query input must be object")
        if set(item) - ALLOWED_QUERY_FIELDS:
            raise SemanticInputError(f"unexpected query fields: {sorted(set(item) - ALLOWED_QUERY_FIELDS)}")
        input_id = str(item.get("semantic_input_id", ""))
        if not input_id.startswith("SEMQ-M024-") or input_id in seen_ids:
            raise SemanticInputError(f"bad semantic input id: {input_id}")
        seen_ids.add(input_id)
        query_case_ids.add(str(item.get("case_id")))
        if item.get("representation_kind") != "safe_query_token_bag_v1":
            raise SemanticInputError(f"bad query representation kind: {input_id}")
        validate_tokens(item.get("representation_tokens"), input_id)
        if not isinstance(item.get("query_hash"), str) or len(item["query_hash"]) != 64:
            raise SemanticInputError(f"bad query hash: {input_id}")
    candidate_case_ids: set[str] = set()
    for item in candidate_inputs:
        if not isinstance(item, Mapping):
            raise SemanticInputError("candidate input must be object")
        if set(item) - ALLOWED_CANDIDATE_FIELDS:
            raise SemanticInputError(f"unexpected candidate fields: {sorted(set(item) - ALLOWED_CANDIDATE_FIELDS)}")
        input_id = str(item.get("semantic_input_id", ""))
        if not input_id.startswith("SEMC-M024-") or input_id in seen_ids:
            raise SemanticInputError(f"bad semantic input id: {input_id}")
        seen_ids.add(input_id)
        candidate_case_ids.add(str(item.get("case_id")))
        if item.get("representation_kind") != "safe_candidate_token_bag_v1":
            raise SemanticInputError(f"bad candidate representation kind: {input_id}")
        validate_tokens(item.get("representation_tokens"), input_id)
        for field in ("candidate_id", "evidence_span_id", "source_block_id", "citation_key", "act_edition_id"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise SemanticInputError(f"missing candidate field: {input_id}: {field}")
    if not candidate_case_ids.issubset(query_case_ids):
        raise SemanticInputError("candidate/query coverage mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or not all(value is True for value in redaction.values()):
        raise SemanticInputError("redaction flags must all be true")
    return {
        "status": "ok",
        "schema_version": "semantic-retrieval-safe-inputs-verification/v1",
        "query_input_count": len(query_inputs),
        "candidate_input_count": len(candidate_inputs),
        "diagnostic_codes": ["semantic_inputs_verified"],
        "non_authoritative": True,
        "non_claim_boundary": "Safe semantic inputs only; does not prove semantic retrieval quality or validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_manifest(args.manifest)
    except SemanticInputError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
