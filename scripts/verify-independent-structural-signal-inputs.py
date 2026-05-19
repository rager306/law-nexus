#!/usr/bin/env python3
"""Verify M029 independent one-signal descriptor inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/independent_structural_signal_inputs.json"
SCHEMA_VERSION = "independent-structural-signal-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_anchor_family_v1"
SELECTED_SIGNAL = "safe_anchor_family_bucket"
FORBIDDEN_REUSED_SIGNAL = "safe_source_order_neighborhood_bucket"
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
ANCHOR_FAMILY_VALUES = {"source_anchor_family_article", "source_anchor_family_paragraph", "source_anchor_family_unknown"}
M027_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
M028_BASELINE = {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0, "runtime_boundary_confirmed": 1.0}
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
    "forbidden_reused_signal",
    "forbidden_reused_signal_declared",
    "m027_baseline_locked",
    "m027_baseline_metrics",
    "m028_baseline_locked",
    "m028_baseline_metrics",
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
    "source_order_index",
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
SAFE_DESCRIPTOR_ID_RE = re.compile(r"^MAT-DESC[QC]-M027-[0-9]{3}$")
SAFE_CASE_RE = re.compile(r"^CASE-M027-MAT-[0-9]{3}$")
SAFE_QUERY_RE = re.compile(r"^QUERY-M027-MAT-[0-9]{3}$")
SAFE_CANDIDATE_ID_RE = re.compile(r"^DESC-CAND-M027-[0-9]{3}$")
SAFE_MATERIALIZED_REF_RE = re.compile(r"^MAT-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_ANCHOR_REF_RE = re.compile(r"^SRC-M027-[0-9]{3}-[A-Z0-9-]+$")
SAFE_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class IndependentSignalInputError(RuntimeError):
    """Raised when independent descriptor input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IndependentSignalInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise IndependentSignalInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise IndependentSignalInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IndependentSignalInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise IndependentSignalInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise IndependentSignalInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise IndependentSignalInputError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise IndependentSignalInputError("unsafe durable vocabulary")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping) or set(allowed) != ENHANCED_FIELDS:
        raise IndependentSignalInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise IndependentSignalInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise IndependentSignalInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise IndependentSignalInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    if normalized[SELECTED_SIGNAL] != ANCHOR_FAMILY_VALUES:
        raise IndependentSignalInputError("selected signal enum mismatch")
    return normalized


def validate_descriptors(descriptors: Any, tokens: Any, allowed: Mapping[str, set[str]], input_id: str) -> str:
    if not isinstance(descriptors, Mapping) or set(descriptors) != ENHANCED_FIELDS:
        raise IndependentSignalInputError(f"descriptor field mismatch: {input_id}")
    expected_tokens: list[str] = []
    for field in BASE_FIELDS:
        if field == FORBIDDEN_REUSED_SIGNAL:
            raise IndependentSignalInputError("forbidden reused signal present")
    for field in ENHANCED_FIELDS:
        value = descriptors.get(field)
        if not isinstance(value, str) or value not in allowed[field]:
            raise IndependentSignalInputError(f"descriptor enum not allowed: {input_id}: {field}")
        token = f"{field}:{value}"
        if not SAFE_TOKEN_RE.fullmatch(token):
            raise IndependentSignalInputError(f"unsafe descriptor token: {input_id}: {field}")
        expected_tokens.append(token)
    if not isinstance(tokens, list):
        raise IndependentSignalInputError(f"descriptor token mismatch: {input_id}")
    token_text = "\n".join(str(token) for token in tokens)
    if FORBIDDEN_REUSED_SIGNAL in token_text:
        raise IndependentSignalInputError("forbidden reused signal present")
    if sorted(tokens) != sorted(expected_tokens):
        raise IndependentSignalInputError(f"descriptor token mismatch: {input_id}")
    return str(descriptors[SELECTED_SIGNAL])


def expected_anchor_family(source_anchor_ref: str) -> str:
    if source_anchor_ref.endswith("-ARTICLE"):
        return "source_anchor_family_article"
    if source_anchor_ref.endswith("-PARAGRAPH"):
        return "source_anchor_family_paragraph"
    return "source_anchor_family_unknown"


def validate_common(item: Mapping[str, Any], allowed: Mapping[str, set[str]], refs: set[str], anchors: set[str]) -> None:
    if set(item) - (ALLOWED_QUERY_FIELDS | ALLOWED_CANDIDATE_FIELDS):
        raise IndependentSignalInputError("unexpected descriptor field")
    input_id = str(item.get("descriptor_input_id"))
    if not SAFE_DESCRIPTOR_ID_RE.fullmatch(input_id):
        raise IndependentSignalInputError(f"unsafe descriptor id: {input_id}")
    case_id = str(item.get("case_id"))
    if not SAFE_CASE_RE.fullmatch(case_id):
        raise IndependentSignalInputError(f"unsafe case id: {case_id}")
    query_id = str(item.get("query_id"))
    if not SAFE_QUERY_RE.fullmatch(query_id):
        raise IndependentSignalInputError(f"unsafe query id: {query_id}")
    ref = str(item.get("materialized_candidate_ref"))
    if not SAFE_MATERIALIZED_REF_RE.fullmatch(ref):
        raise IndependentSignalInputError(f"unsafe materialized ref: {ref}")
    refs.add(ref)
    source_anchor_ref = str(item.get("source_anchor_ref"))
    if not SAFE_ANCHOR_REF_RE.fullmatch(source_anchor_ref):
        raise IndependentSignalInputError(f"unsafe source anchor ref: {source_anchor_ref}")
    anchors.add(source_anchor_ref)
    source_hash = str(item.get("source_anchor_sha256"))
    if not SAFE_HASH_RE.fullmatch(source_hash):
        raise IndependentSignalInputError(f"unsafe source anchor hash: {input_id}")
    if item.get("representation_kind") != REPRESENTATION_KIND:
        raise IndependentSignalInputError(f"representation mismatch: {input_id}")
    if item.get("selected_signal") != SELECTED_SIGNAL:
        raise IndependentSignalInputError(f"selected signal mismatch: {input_id}")
    value = validate_descriptors(item.get("descriptors"), item.get("descriptor_tokens"), allowed, input_id)
    if item.get("selected_signal_value") != value:
        raise IndependentSignalInputError(f"selected signal value mismatch: {input_id}")
    if value != expected_anchor_family(source_anchor_ref):
        raise IndependentSignalInputError(f"anchor family derivation mismatch: {input_id}")
    if item.get("non_authoritative") is not True:
        raise IndependentSignalInputError(f"non-authoritative marker missing: {input_id}")


def validate_items(manifest: Mapping[str, Any], allowed: Mapping[str, set[str]]) -> tuple[set[str], set[str]]:
    refs: set[str] = set()
    anchors: set[str] = set()
    query_items = manifest.get("query_descriptors")
    candidate_items = manifest.get("candidate_descriptors")
    if not isinstance(query_items, list) or not isinstance(candidate_items, list):
        raise IndependentSignalInputError("descriptor arrays missing")
    if len(query_items) != manifest.get("query_descriptor_count") or len(candidate_items) != manifest.get("candidate_descriptor_count"):
        raise IndependentSignalInputError("descriptor count mismatch")
    for item in query_items:
        if not isinstance(item, Mapping) or set(item) - ALLOWED_QUERY_FIELDS:
            raise IndependentSignalInputError("unexpected query descriptor shape")
        validate_common(item, allowed, refs, anchors)
    for item in candidate_items:
        if not isinstance(item, Mapping) or set(item) - ALLOWED_CANDIDATE_FIELDS:
            raise IndependentSignalInputError("unexpected candidate descriptor shape")
        candidate_id = str(item.get("candidate_id"))
        if not SAFE_CANDIDATE_ID_RE.fullmatch(candidate_id):
            raise IndependentSignalInputError(f"unsafe candidate id: {candidate_id}")
        records = item.get("source_record_ids")
        if not isinstance(records, list) or not records or not all(isinstance(record, str) for record in records):
            raise IndependentSignalInputError("source record ids missing")
        validate_common(item, allowed, refs, anchors)
    return refs, anchors


def verify_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    if set(manifest) != ALLOWED_ROOT_FIELDS:
        raise IndependentSignalInputError("manifest root field mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise IndependentSignalInputError("schema or representation mismatch")
    if manifest.get("milestone_id") != "M029-yfyh51" or manifest.get("slice_id") != "S02":
        raise IndependentSignalInputError("milestone/slice mismatch")
    if manifest.get("selected_signal") != SELECTED_SIGNAL:
        raise IndependentSignalInputError("selected signal mismatch")
    if manifest.get("forbidden_reused_signal") != FORBIDDEN_REUSED_SIGNAL or manifest.get("forbidden_reused_signal_declared") is not True:
        raise IndependentSignalInputError("forbidden reused signal marker mismatch")
    if manifest.get("single_signal_change_only") is not True or manifest.get("added_descriptor_fields") != [SELECTED_SIGNAL]:
        raise IndependentSignalInputError("single signal change mismatch")
    if set(manifest.get("base_derivation_fields", [])) != BASE_FIELDS:
        raise IndependentSignalInputError("base derivation field mismatch")
    if set(manifest.get("enhanced_derivation_fields", [])) != ENHANCED_FIELDS:
        raise IndependentSignalInputError("enhanced derivation field mismatch")
    if manifest.get("m027_baseline_locked") is not True or manifest.get("m027_baseline_metrics") != M027_BASELINE:
        raise IndependentSignalInputError("M027 baseline mismatch")
    if manifest.get("m028_baseline_locked") is not True or manifest.get("m028_baseline_metrics") != M028_BASELINE:
        raise IndependentSignalInputError("M028 baseline mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or set(redaction) != REQUIRED_REDACTION or not all(redaction.values()):
        raise IndependentSignalInputError("redaction flags mismatch")
    if manifest.get("r035_non_validation_declared") is not True or manifest.get("r038_review_required") is not True or manifest.get("non_authoritative") is not True:
        raise IndependentSignalInputError("lifecycle boundary marker missing")
    summary = manifest.get("signal_derivation_summary")
    if not isinstance(summary, Mapping):
        raise IndependentSignalInputError("signal derivation summary missing")
    if summary.get("allowed_inputs") != ["source_anchor_ref", "source_anchor_sha256", "materialized_candidate_ref"]:
        raise IndependentSignalInputError("allowed derivation inputs mismatch")
    if summary.get("source_order_index_used") is not False or summary.get("forbidden_reused_signal_used") is not False:
        raise IndependentSignalInputError("forbidden derivation input used")
    if summary.get("raw_text_used") is not False or summary.get("labels_used") is not False:
        raise IndependentSignalInputError("unsafe derivation input used")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    refs, anchors = validate_items(manifest, allowed)
    base_artifact = repo_path(str(manifest.get("base_descriptor_inputs_artifact")))
    if manifest.get("base_descriptor_inputs_sha256") != sha256_path(base_artifact):
        raise IndependentSignalInputError("base descriptor source hash mismatch")
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "forbidden_reused_signal": FORBIDDEN_REUSED_SIGNAL,
        "query_descriptor_count": manifest["query_descriptor_count"],
        "candidate_descriptor_count": manifest["candidate_descriptor_count"],
        "materialized_ref_count": len(refs),
        "source_anchor_ref_count": len(anchors),
        "r035_non_validation_declared": True,
        "r038_review_required": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(verify_manifest(args.manifest), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
