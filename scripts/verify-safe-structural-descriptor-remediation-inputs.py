#!/usr/bin/env python3
"""Verify M028 one-signal safe structural descriptor remediation inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json"
SCHEMA_VERSION = "safe-structural-descriptor-remediation-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_neighborhood_v1"
SELECTED_SIGNAL = "safe_source_order_neighborhood_bucket"
BASE_FIELDS = {
    "candidate_kind",
    "structural_unit_kind",
    "citation_granularity",
    "content_role",
    "temporal_status",
    "materialization_method",
    "source_order_index_bucket",
}
ENHANCED_FIELDS = BASE_FIELDS | {SELECTED_SIGNAL}
NEIGHBOR_VALUES = {
    "source_order_neighbor_first",
    "source_order_neighbor_after_source_block",
    "source_order_neighbor_between_evidence_spans",
    "source_order_neighbor_before_late_gap",
    "source_order_neighbor_late",
}
M027_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0, "score_count": 36}
ALLOWED_ROOT_FIELDS = {
    "added_descriptor_fields",
    "allowed_descriptor_fields",
    "base_derivation_fields",
    "base_descriptor_inputs_artifact",
    "base_descriptor_inputs_sha256",
    "base_descriptor_verification_summary",
    "candidate_descriptor_count",
    "candidate_descriptors",
    "enhanced_derivation_fields",
    "m027_baseline_locked",
    "m027_baseline_metrics",
    "materialization_artifact",
    "materialization_sha256",
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
    "selected_signal",
    "signal_derivation_summary",
    "single_signal_change_only",
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
    "selected_signal",
    "selected_signal_value",
    "source_anchor_ref",
    "source_anchor_sha256",
    "source_order_index",
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
    "selected_signal",
    "selected_signal_value",
    "source_anchor_ref",
    "source_anchor_sha256",
    "source_order_index",
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


class SafeStructuralDescriptorInputError(RuntimeError):
    """Raised when safe structural descriptor remediation input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SafeStructuralDescriptorInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SafeStructuralDescriptorInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise SafeStructuralDescriptorInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SafeStructuralDescriptorInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise SafeStructuralDescriptorInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise SafeStructuralDescriptorInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise SafeStructuralDescriptorInputError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise SafeStructuralDescriptorInputError("unsafe durable vocabulary")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping) or set(allowed) != ENHANCED_FIELDS:
        raise SafeStructuralDescriptorInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise SafeStructuralDescriptorInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise SafeStructuralDescriptorInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise SafeStructuralDescriptorInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    if normalized[SELECTED_SIGNAL] != NEIGHBOR_VALUES:
        raise SafeStructuralDescriptorInputError("selected signal enum mismatch")
    return normalized


def validate_descriptors(descriptors: Any, tokens: Any, allowed: Mapping[str, set[str]], input_id: str) -> str:
    if not isinstance(descriptors, Mapping) or set(descriptors) != ENHANCED_FIELDS:
        raise SafeStructuralDescriptorInputError(f"descriptor field mismatch: {input_id}")
    expected_tokens: list[str] = []
    for field in sorted(ENHANCED_FIELDS):
        value = descriptors.get(field)
        if not isinstance(value, str) or value not in allowed[field]:
            raise SafeStructuralDescriptorInputError(f"descriptor enum not allowed: {input_id}: {field}")
        token = f"{field}:{value}"
        if not SAFE_TOKEN_RE.fullmatch(token):
            raise SafeStructuralDescriptorInputError(f"unsafe descriptor token: {input_id}: {field}")
        expected_tokens.append(token)
    if not isinstance(tokens, list) or sorted(tokens) != expected_tokens:
        raise SafeStructuralDescriptorInputError(f"descriptor token mismatch: {input_id}")
    return str(descriptors[SELECTED_SIGNAL])


def validate_common(item: Mapping[str, Any], allowed: Mapping[str, set[str]], refs: set[str], anchors: set[str]) -> None:
    input_id = str(item.get("descriptor_input_id"))
    if not SAFE_DESCRIPTOR_ID_RE.fullmatch(input_id):
        raise SafeStructuralDescriptorInputError(f"unsafe descriptor id: {input_id}")
    if not isinstance(item.get("case_id"), str) or not SAFE_CASE_RE.fullmatch(item["case_id"]):
        raise SafeStructuralDescriptorInputError(f"unsafe case id: {input_id}")
    if not isinstance(item.get("query_id"), str) or not SAFE_QUERY_RE.fullmatch(item["query_id"]):
        raise SafeStructuralDescriptorInputError(f"unsafe query id: {input_id}")
    if item.get("representation_kind") != REPRESENTATION_KIND:
        raise SafeStructuralDescriptorInputError(f"representation mismatch: {input_id}")
    if item.get("selected_signal") != SELECTED_SIGNAL:
        raise SafeStructuralDescriptorInputError(f"selected signal mismatch: {input_id}")
    materialized_ref = item.get("materialized_candidate_ref")
    anchor_ref = item.get("source_anchor_ref")
    if not isinstance(materialized_ref, str) or not SAFE_MATERIALIZED_REF_RE.fullmatch(materialized_ref):
        raise SafeStructuralDescriptorInputError(f"unsafe materialized ref: {input_id}")
    if not isinstance(anchor_ref, str) or not SAFE_ANCHOR_REF_RE.fullmatch(anchor_ref):
        raise SafeStructuralDescriptorInputError(f"unsafe source anchor ref: {input_id}")
    if materialized_ref in refs and anchor_ref in anchors:
        raise SafeStructuralDescriptorInputError(f"duplicate descriptor source ref: {input_id}")
    refs.add(materialized_ref)
    anchors.add(anchor_ref)
    if not isinstance(item.get("source_anchor_sha256"), str) or not SAFE_HASH_RE.fullmatch(item["source_anchor_sha256"]):
        raise SafeStructuralDescriptorInputError(f"source anchor hash mismatch: {input_id}")
    if not isinstance(item.get("source_order_index"), int) or item["source_order_index"] <= 0:
        raise SafeStructuralDescriptorInputError(f"source order index mismatch: {input_id}")
    if item.get("non_authoritative") is not True:
        raise SafeStructuralDescriptorInputError(f"non-authoritative marker missing: {input_id}")
    signal_value = validate_descriptors(item.get("descriptors"), item.get("descriptor_tokens"), allowed, input_id)
    if item.get("selected_signal_value") != signal_value:
        raise SafeStructuralDescriptorInputError(f"selected signal value mismatch: {input_id}")


def validate_query(item: Any, allowed: Mapping[str, set[str]], refs: set[str], anchors: set[str]) -> None:
    if not isinstance(item, Mapping) or set(item) != ALLOWED_QUERY_FIELDS:
        raise SafeStructuralDescriptorInputError("query descriptor field mismatch")
    validate_common(item, allowed, refs, anchors)
    if not isinstance(item.get("query_hash_ref"), str) or not SAFE_HASH_RE.fullmatch(item["query_hash_ref"]):
        raise SafeStructuralDescriptorInputError("query hash ref mismatch")


def validate_candidate(item: Any, allowed: Mapping[str, set[str]], refs: set[str], anchors: set[str]) -> None:
    if not isinstance(item, Mapping) or set(item) != ALLOWED_CANDIDATE_FIELDS:
        raise SafeStructuralDescriptorInputError("candidate descriptor field mismatch")
    validate_common(item, allowed, refs, anchors)
    if not isinstance(item.get("candidate_id"), str) or not SAFE_CANDIDATE_ID_RE.fullmatch(item["candidate_id"]):
        raise SafeStructuralDescriptorInputError("candidate id mismatch")
    if item.get("source_record_ids") != [item.get("materialized_candidate_ref")]:
        raise SafeStructuralDescriptorInputError("source record id mismatch")


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    unexpected = set(manifest) - ALLOWED_ROOT_FIELDS
    if unexpected:
        raise SafeStructuralDescriptorInputError(f"unexpected root fields: {sorted(unexpected)}")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise SafeStructuralDescriptorInputError("schema or representation mismatch")
    if manifest.get("milestone_id") != "M028-yejcai" or manifest.get("slice_id") != "S02":
        raise SafeStructuralDescriptorInputError("milestone or slice marker mismatch")
    if manifest.get("selected_signal") != SELECTED_SIGNAL or manifest.get("added_descriptor_fields") != [SELECTED_SIGNAL]:
        raise SafeStructuralDescriptorInputError("selected signal mismatch")
    if manifest.get("single_signal_change_only") is not True or manifest.get("m027_baseline_locked") is not True:
        raise SafeStructuralDescriptorInputError("single-signal or baseline marker missing")
    if manifest.get("m027_baseline_metrics") != M027_BASELINE:
        raise SafeStructuralDescriptorInputError("M027 baseline mismatch")
    if set(manifest.get("base_derivation_fields", [])) != BASE_FIELDS or set(manifest.get("enhanced_derivation_fields", [])) != ENHANCED_FIELDS:
        raise SafeStructuralDescriptorInputError("derivation field mismatch")
    if sha256_path(repo_path(str(manifest.get("base_descriptor_inputs_artifact")))) != manifest.get("base_descriptor_inputs_sha256"):
        raise SafeStructuralDescriptorInputError("base descriptor source hash mismatch")
    if sha256_path(repo_path(str(manifest.get("materialization_artifact")))) != manifest.get("materialization_sha256"):
        raise SafeStructuralDescriptorInputError("materialization source hash mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or set(redaction) != REQUIRED_REDACTION or any(value is not True for value in redaction.values()):
        raise SafeStructuralDescriptorInputError("redaction flags mismatch")
    if manifest.get("r035_non_validation_declared") is not True or manifest.get("r038_review_required") is not True:
        raise SafeStructuralDescriptorInputError("lifecycle boundary marker missing")
    summary = manifest.get("signal_derivation_summary")
    if not isinstance(summary, Mapping) or summary.get("raw_text_used") is not False or summary.get("labels_used") is not False:
        raise SafeStructuralDescriptorInputError("signal derivation summary mismatch")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    queries = manifest.get("query_descriptors")
    candidates = manifest.get("candidate_descriptors")
    if not isinstance(queries, list) or not isinstance(candidates, list):
        raise SafeStructuralDescriptorInputError("descriptor arrays missing")
    if manifest.get("query_descriptor_count") != len(queries) or manifest.get("candidate_descriptor_count") != len(candidates):
        raise SafeStructuralDescriptorInputError("descriptor count mismatch")
    query_refs: set[str] = set()
    query_anchors: set[str] = set()
    candidate_refs: set[str] = set()
    candidate_anchors: set[str] = set()
    for item in queries:
        validate_query(item, allowed, query_refs, query_anchors)
    for item in candidates:
        validate_candidate(item, allowed, candidate_refs, candidate_anchors)
    if query_refs != candidate_refs or query_anchors != candidate_anchors:
        raise SafeStructuralDescriptorInputError("query/candidate materialized refs mismatch")
    boundary = manifest.get("non_claim_boundary")
    if not isinstance(boundary, str) or "does not validate R035" not in boundary:
        raise SafeStructuralDescriptorInputError("non-claim boundary missing")
    return {
        "schema_version": "safe-structural-descriptor-remediation-inputs-verification/v1",
        "status": "ok",
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "single_signal_change_only": True,
        "query_descriptor_count": len(queries),
        "candidate_descriptor_count": len(candidates),
        "non_authoritative": True,
        "non_claim_boundary": "One-signal descriptor remediation verification only; does not validate R035.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = verify_manifest(args.manifest)
    except SafeStructuralDescriptorInputError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, ensure_ascii=False, sort_keys=True))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
