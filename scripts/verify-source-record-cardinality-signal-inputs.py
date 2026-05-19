#!/usr/bin/env python3
"""Verify M030 source-record-cardinality one-signal descriptor inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "prd/research/ontology_architecture_requirements/fixtures/source_record_cardinality_signal_inputs.json"
SCHEMA_VERSION = "source-record-cardinality-signal-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_source_record_cardinality_v1"
SELECTED_SIGNAL = "safe_source_record_cardinality_bucket"
FORBIDDEN_PRIOR_SIGNALS = {"safe_source_order_neighborhood_bucket", "safe_anchor_family_bucket"}
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
CARDINALITY_VALUES = {"source_record_cardinality_single", "source_record_cardinality_multiple", "source_record_cardinality_unknown"}
M027_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
M028_BASELINE = {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0, "runtime_boundary_confirmed": 1.0}
M029_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
ALLOWED_ROOT_FIELDS = {
    "added_descriptor_fields",
    "allowed_descriptor_fields",
    "base_derivation_fields",
    "base_descriptor_inputs_artifact",
    "base_descriptor_inputs_sha256",
    "base_descriptor_verification_summary",
    "candidate_descriptor_count",
    "candidate_descriptors",
    "cardinality_distribution",
    "enhanced_derivation_fields",
    "forbidden_prior_signals",
    "forbidden_prior_signals_declared",
    "m027_baseline_locked",
    "m027_baseline_metrics",
    "m028_baseline_locked",
    "m028_baseline_metrics",
    "m029_baseline_locked",
    "m029_baseline_metrics",
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
    "source_record_cardinality",
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
    "source_record_cardinality",
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
} | FORBIDDEN_PRIOR_SIGNALS
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
SAFE_SOURCE_RECORD_RE = re.compile(r"^MAT-M027-[0-9]{3}-[A-Z0-9-]+$")
ABSOLUTE_PATH_RE = re.compile(r"(^|[\s:=])(?:/[A-Za-z0-9_.-]+|[A-Za-z]:\\)")


class SourceRecordCardinalityInputError(RuntimeError):
    """Raised when source-record-cardinality input verification fails."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceRecordCardinalityInputError(f"malformed JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SourceRecordCardinalityInputError("manifest root must be object")
    return payload


def repo_path(path_value: str) -> Path:
    if path_value.startswith("/") or path_value.startswith(".gsd/exec"):
        raise SourceRecordCardinalityInputError(f"unsafe path: {path_value}")
    path = ROOT / path_value
    try:
        path.resolve().relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SourceRecordCardinalityInputError(f"path outside repository: {path_value}") from exc
    return path


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def assert_safe_payload(payload: Mapping[str, Any]) -> None:
    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_FIELD_NAMES:
                    raise SourceRecordCardinalityInputError(f"unsafe field name: {key}")
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str) and ABSOLUTE_PATH_RE.search(value):
            raise SourceRecordCardinalityInputError("unsafe absolute path fragment")

    walk(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for fragment in FORBIDDEN_STRING_FRAGMENTS:
        if fragment.lower() in serialized.lower():
            raise SourceRecordCardinalityInputError(f"unsafe payload fragment: {fragment}")
    if "provider_payloads_excluded" in serialized:
        raise SourceRecordCardinalityInputError("unsafe durable vocabulary")


def validate_allowed_enums(allowed: Any) -> dict[str, set[str]]:
    if not isinstance(allowed, Mapping) or set(allowed) != ENHANCED_FIELDS:
        raise SourceRecordCardinalityInputError("allowed descriptor field set mismatch")
    normalized: dict[str, set[str]] = {}
    for field, values in allowed.items():
        if not isinstance(values, list) or not values:
            raise SourceRecordCardinalityInputError(f"allowed enum values missing: {field}")
        enum_values: set[str] = set()
        for value in values:
            if not isinstance(value, str) or not SAFE_ENUM_RE.fullmatch(value):
                raise SourceRecordCardinalityInputError(f"unsafe enum value: {field}")
            enum_values.add(value)
        if len(enum_values) != len(values):
            raise SourceRecordCardinalityInputError(f"duplicate enum values: {field}")
        normalized[str(field)] = enum_values
    if normalized[SELECTED_SIGNAL] != CARDINALITY_VALUES:
        raise SourceRecordCardinalityInputError("selected signal enum mismatch")
    return normalized


def cardinality_bucket(count: int) -> str:
    if count == 1:
        return "source_record_cardinality_single"
    if count > 1:
        return "source_record_cardinality_multiple"
    return "source_record_cardinality_unknown"


def validate_descriptors(descriptors: Any, tokens: Any, allowed: Mapping[str, set[str]], input_id: str) -> str:
    if not isinstance(descriptors, Mapping) or set(descriptors) != ENHANCED_FIELDS:
        raise SourceRecordCardinalityInputError(f"descriptor field mismatch: {input_id}")
    expected_tokens: list[str] = []
    for field in ENHANCED_FIELDS:
        value = descriptors.get(field)
        if not isinstance(value, str) or value not in allowed[field]:
            raise SourceRecordCardinalityInputError(f"descriptor enum not allowed: {input_id}: {field}")
        token = f"{field}:{value}"
        if not SAFE_TOKEN_RE.fullmatch(token):
            raise SourceRecordCardinalityInputError(f"unsafe descriptor token: {input_id}: {field}")
        expected_tokens.append(token)
    if not isinstance(tokens, list):
        raise SourceRecordCardinalityInputError(f"descriptor token mismatch: {input_id}")
    token_text = "\n".join(str(token) for token in tokens)
    if any(signal in token_text for signal in FORBIDDEN_PRIOR_SIGNALS):
        raise SourceRecordCardinalityInputError("forbidden prior signal present")
    if sorted(tokens) != sorted(expected_tokens):
        raise SourceRecordCardinalityInputError(f"descriptor token mismatch: {input_id}")
    return str(descriptors[SELECTED_SIGNAL])


def validate_common(item: Mapping[str, Any], allowed: Mapping[str, set[str]], refs: set[str], anchors: set[str]) -> str:
    input_id = str(item.get("descriptor_input_id"))
    if not SAFE_DESCRIPTOR_ID_RE.fullmatch(input_id):
        raise SourceRecordCardinalityInputError(f"unsafe descriptor id: {input_id}")
    case_id = str(item.get("case_id"))
    if not SAFE_CASE_RE.fullmatch(case_id):
        raise SourceRecordCardinalityInputError(f"unsafe case id: {case_id}")
    query_id = str(item.get("query_id"))
    if not SAFE_QUERY_RE.fullmatch(query_id):
        raise SourceRecordCardinalityInputError(f"unsafe query id: {query_id}")
    ref = str(item.get("materialized_candidate_ref"))
    if not SAFE_MATERIALIZED_REF_RE.fullmatch(ref):
        raise SourceRecordCardinalityInputError(f"unsafe materialized ref: {ref}")
    refs.add(ref)
    source_anchor_ref = str(item.get("source_anchor_ref"))
    if not SAFE_ANCHOR_REF_RE.fullmatch(source_anchor_ref):
        raise SourceRecordCardinalityInputError(f"unsafe source anchor ref: {source_anchor_ref}")
    anchors.add(source_anchor_ref)
    source_hash = str(item.get("source_anchor_sha256"))
    if not SAFE_HASH_RE.fullmatch(source_hash):
        raise SourceRecordCardinalityInputError(f"unsafe source anchor hash: {input_id}")
    if item.get("representation_kind") != REPRESENTATION_KIND:
        raise SourceRecordCardinalityInputError(f"representation mismatch: {input_id}")
    if item.get("selected_signal") != SELECTED_SIGNAL:
        raise SourceRecordCardinalityInputError(f"selected signal mismatch: {input_id}")
    value = validate_descriptors(item.get("descriptors"), item.get("descriptor_tokens"), allowed, input_id)
    if item.get("selected_signal_value") != value:
        raise SourceRecordCardinalityInputError(f"selected signal value mismatch: {input_id}")
    cardinality = item.get("source_record_cardinality")
    if not isinstance(cardinality, int) or cardinality < 0:
        raise SourceRecordCardinalityInputError(f"source record cardinality missing: {input_id}")
    if value != cardinality_bucket(cardinality):
        raise SourceRecordCardinalityInputError(f"cardinality derivation mismatch: {input_id}")
    if item.get("non_authoritative") is not True:
        raise SourceRecordCardinalityInputError(f"non-authoritative marker missing: {input_id}")
    return ref


def candidate_cardinality_index(candidate_items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    index: dict[str, int] = {}
    for item in candidate_items:
        ref = str(item.get("materialized_candidate_ref"))
        records = item.get("source_record_ids")
        if not isinstance(records, list) or not records:
            raise SourceRecordCardinalityInputError(f"source record ids missing: {ref}")
        for record in records:
            if not isinstance(record, str) or not SAFE_SOURCE_RECORD_RE.fullmatch(record):
                raise SourceRecordCardinalityInputError(f"unsafe source record id: {ref}")
        cardinality = item.get("source_record_cardinality")
        if cardinality != len(records):
            raise SourceRecordCardinalityInputError(f"source record cardinality mismatch: {ref}")
        index[ref] = len(records)
    return index


def validate_items(manifest: Mapping[str, Any], allowed: Mapping[str, set[str]]) -> tuple[set[str], set[str], dict[str, int]]:
    refs: set[str] = set()
    anchors: set[str] = set()
    query_items = manifest.get("query_descriptors")
    candidate_items = manifest.get("candidate_descriptors")
    if not isinstance(query_items, list) or not isinstance(candidate_items, list):
        raise SourceRecordCardinalityInputError("descriptor arrays missing")
    if len(query_items) != manifest.get("query_descriptor_count") or len(candidate_items) != manifest.get("candidate_descriptor_count"):
        raise SourceRecordCardinalityInputError("descriptor count mismatch")
    for item in query_items:
        if not isinstance(item, Mapping) or set(item) - ALLOWED_QUERY_FIELDS:
            raise SourceRecordCardinalityInputError("unexpected query descriptor shape")
    typed_candidates: list[Mapping[str, Any]] = []
    for item in candidate_items:
        if not isinstance(item, Mapping) or set(item) - ALLOWED_CANDIDATE_FIELDS:
            raise SourceRecordCardinalityInputError("unexpected candidate descriptor shape")
        candidate_id = str(item.get("candidate_id"))
        if not SAFE_CANDIDATE_ID_RE.fullmatch(candidate_id):
            raise SourceRecordCardinalityInputError(f"unsafe candidate id: {candidate_id}")
        typed_candidates.append(item)
    cardinality_by_ref = candidate_cardinality_index(typed_candidates)
    for item in typed_candidates:
        validate_common(item, allowed, refs, anchors)
    for item in query_items:
        ref = validate_common(item, allowed, refs, anchors)
        if item.get("source_record_cardinality") != cardinality_by_ref.get(ref):
            raise SourceRecordCardinalityInputError(f"query cardinality derivation mismatch: {ref}")
    return refs, anchors, cardinality_by_ref


def verify_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest = load_json(path)
    assert_safe_payload(manifest)
    if set(manifest) != ALLOWED_ROOT_FIELDS:
        raise SourceRecordCardinalityInputError("manifest root field mismatch")
    if manifest.get("schema_version") != SCHEMA_VERSION or manifest.get("representation_kind") != REPRESENTATION_KIND:
        raise SourceRecordCardinalityInputError("schema or representation mismatch")
    if manifest.get("milestone_id") != "M030-hwfnq0" or manifest.get("slice_id") != "S02":
        raise SourceRecordCardinalityInputError("milestone/slice mismatch")
    if manifest.get("selected_signal") != SELECTED_SIGNAL:
        raise SourceRecordCardinalityInputError("selected signal mismatch")
    if set(manifest.get("forbidden_prior_signals", [])) != FORBIDDEN_PRIOR_SIGNALS or manifest.get("forbidden_prior_signals_declared") is not True:
        raise SourceRecordCardinalityInputError("forbidden prior signal marker mismatch")
    if manifest.get("single_signal_change_only") is not True or manifest.get("added_descriptor_fields") != [SELECTED_SIGNAL]:
        raise SourceRecordCardinalityInputError("single signal change mismatch")
    if set(manifest.get("base_derivation_fields", [])) != BASE_FIELDS:
        raise SourceRecordCardinalityInputError("base derivation field mismatch")
    if set(manifest.get("enhanced_derivation_fields", [])) != ENHANCED_FIELDS:
        raise SourceRecordCardinalityInputError("enhanced derivation field mismatch")
    if manifest.get("m027_baseline_locked") is not True or manifest.get("m027_baseline_metrics") != M027_BASELINE:
        raise SourceRecordCardinalityInputError("M027 baseline mismatch")
    if manifest.get("m028_baseline_locked") is not True or manifest.get("m028_baseline_metrics") != M028_BASELINE:
        raise SourceRecordCardinalityInputError("M028 baseline mismatch")
    if manifest.get("m029_baseline_locked") is not True or manifest.get("m029_baseline_metrics") != M029_BASELINE:
        raise SourceRecordCardinalityInputError("M029 baseline mismatch")
    redaction = manifest.get("redaction")
    if not isinstance(redaction, Mapping) or set(redaction) != REQUIRED_REDACTION or not all(redaction.values()):
        raise SourceRecordCardinalityInputError("redaction flags mismatch")
    if manifest.get("r035_non_validation_declared") is not True or manifest.get("r038_review_required") is not True or manifest.get("non_authoritative") is not True:
        raise SourceRecordCardinalityInputError("lifecycle boundary marker missing")
    summary = manifest.get("signal_derivation_summary")
    if not isinstance(summary, Mapping):
        raise SourceRecordCardinalityInputError("signal derivation summary missing")
    if summary.get("allowed_inputs") != ["materialized_candidate_ref", "source_record_ids", "source_anchor_sha256"]:
        raise SourceRecordCardinalityInputError("allowed derivation inputs mismatch")
    if summary.get("source_order_index_used") is not False or summary.get("prior_signals_used") is not False:
        raise SourceRecordCardinalityInputError("forbidden derivation input used")
    if summary.get("source_anchor_ref_suffix_family_used") is not False:
        raise SourceRecordCardinalityInputError("anchor-family derivation input used")
    if summary.get("raw_text_used") is not False or summary.get("labels_used") is not False:
        raise SourceRecordCardinalityInputError("unsafe derivation input used")
    allowed = validate_allowed_enums(manifest.get("allowed_descriptor_fields"))
    refs, anchors, cardinality_by_ref = validate_items(manifest, allowed)
    distribution = Counter(
        item["selected_signal_value"]
        for item in [*manifest["query_descriptors"], *manifest["candidate_descriptors"]]
        if isinstance(item, Mapping)
    )
    if manifest.get("cardinality_distribution") != dict(sorted(distribution.items())):
        raise SourceRecordCardinalityInputError("cardinality distribution mismatch")
    if summary.get("constant_signal_risk") is not (len(distribution) == 1):
        raise SourceRecordCardinalityInputError("constant signal risk mismatch")
    base_artifact = repo_path(str(manifest.get("base_descriptor_inputs_artifact")))
    if manifest.get("base_descriptor_inputs_sha256") != sha256_path(base_artifact):
        raise SourceRecordCardinalityInputError("base descriptor source hash mismatch")
    return {
        "status": "ok",
        "schema_version": SCHEMA_VERSION,
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "forbidden_prior_signals": sorted(FORBIDDEN_PRIOR_SIGNALS),
        "query_descriptor_count": manifest["query_descriptor_count"],
        "candidate_descriptor_count": manifest["candidate_descriptor_count"],
        "materialized_ref_count": len(refs),
        "source_anchor_ref_count": len(anchors),
        "source_record_ref_count": len(cardinality_by_ref),
        "cardinality_distribution": dict(sorted(distribution.items())),
        "constant_signal_risk": len(distribution) == 1,
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
