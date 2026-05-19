#!/usr/bin/env python3
"""Build M030 descriptors with one safe source-record cardinality signal."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json"
BASE_VERIFIER = ROOT / "scripts/verify-materialized-descriptor-inputs.py"
OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/fixtures/source_record_cardinality_signal_inputs.json"
SCHEMA_VERSION = "source-record-cardinality-signal-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_source_record_cardinality_v1"
SELECTED_SIGNAL = "safe_source_record_cardinality_bucket"
FORBIDDEN_PRIOR_SIGNALS = ("safe_source_order_neighborhood_bucket", "safe_anchor_family_bucket")
BASE_DERIVATION_FIELDS = (
    "candidate_kind",
    "structural_unit_kind",
    "citation_granularity",
    "content_role",
    "temporal_status",
    "materialization_method",
    "source_order_index_bucket",
)
ENHANCED_DERIVATION_FIELDS = (*BASE_DERIVATION_FIELDS, SELECTED_SIGNAL)
CARDINALITY_VALUES = [
    "source_record_cardinality_single",
    "source_record_cardinality_multiple",
    "source_record_cardinality_unknown",
]
M027_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
M028_BASELINE = {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0, "runtime_boundary_confirmed": 1.0}
M029_BASELINE = {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}


class SourceRecordCardinalityBuildError(RuntimeError):
    """Raised when source-record-cardinality descriptors cannot be built safely."""


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SourceRecordCardinalityBuildError("JSON root must be object")
    return payload


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SourceRecordCardinalityBuildError(f"module load failed: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_base_inputs(path: Path) -> dict[str, Any]:
    verifier = load_module(BASE_VERIFIER, "m030_base_descriptor_verifier")
    return verifier.verify_manifest(path)


def cardinality_bucket(record_ids: Sequence[Any] | None) -> str:
    if record_ids is None:
        return "source_record_cardinality_unknown"
    count = len(record_ids)
    if count == 1:
        return "source_record_cardinality_single"
    if count > 1:
        return "source_record_cardinality_multiple"
    return "source_record_cardinality_unknown"


def descriptor_tokens(descriptors: Mapping[str, str]) -> list[str]:
    return [f"{field}:{descriptors[field]}" for field in ENHANCED_DERIVATION_FIELDS]


def source_record_index(candidate_items: Sequence[Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for item in candidate_items:
        if not isinstance(item, Mapping):
            continue
        ref = str(item.get("materialized_candidate_ref"))
        records = item.get("source_record_ids")
        if not isinstance(records, list) or not records or not all(isinstance(record, str) for record in records):
            raise SourceRecordCardinalityBuildError(f"source_record_ids missing: {ref}")
        index[ref] = list(records)
    if not index:
        raise SourceRecordCardinalityBuildError("source record index empty")
    return index


def enhance_item(item: Mapping[str, Any], records_by_ref: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    base_descriptors = item.get("descriptors")
    if not isinstance(base_descriptors, Mapping):
        raise SourceRecordCardinalityBuildError("base descriptors missing")
    descriptors = {str(key): str(value) for key, value in base_descriptors.items()}
    if set(descriptors) != set(BASE_DERIVATION_FIELDS):
        raise SourceRecordCardinalityBuildError("base descriptor field mismatch")
    serialized_tokens = "\n".join(str(token) for token in item.get("descriptor_tokens", []))
    if any(signal in descriptors or signal in serialized_tokens for signal in FORBIDDEN_PRIOR_SIGNALS):
        raise SourceRecordCardinalityBuildError("forbidden prior signal present")
    materialized_ref = str(item.get("materialized_candidate_ref"))
    records = records_by_ref.get(materialized_ref)
    bucket = cardinality_bucket(records)
    descriptors[SELECTED_SIGNAL] = bucket
    enhanced = dict(item)
    enhanced["representation_kind"] = REPRESENTATION_KIND
    enhanced["descriptors"] = descriptors
    enhanced["descriptor_tokens"] = descriptor_tokens(descriptors)
    enhanced["selected_signal"] = SELECTED_SIGNAL
    enhanced["selected_signal_value"] = bucket
    enhanced["source_record_cardinality"] = len(records) if records is not None else 0
    enhanced.pop("source_order_index", None)
    return enhanced


def build_inputs(base_inputs_path: Path = BASE_INPUTS) -> dict[str, Any]:
    base_summary = verify_base_inputs(base_inputs_path)
    base_inputs = load_json(base_inputs_path)
    query_items = base_inputs.get("query_descriptors")
    candidate_items = base_inputs.get("candidate_descriptors")
    if not isinstance(query_items, list) or not isinstance(candidate_items, list):
        raise SourceRecordCardinalityBuildError("descriptor arrays missing")
    records_by_ref = source_record_index(candidate_items)
    query_descriptors = [enhance_item(item, records_by_ref) for item in query_items if isinstance(item, Mapping)]
    candidate_descriptors = [enhance_item(item, records_by_ref) for item in candidate_items if isinstance(item, Mapping)]
    allowed_descriptor_fields = dict(base_inputs.get("allowed_descriptor_fields", {}))
    allowed_descriptor_fields[SELECTED_SIGNAL] = CARDINALITY_VALUES
    distribution = Counter(item["selected_signal_value"] for item in query_descriptors + candidate_descriptors)
    cardinality_counts = sorted({item["source_record_cardinality"] for item in query_descriptors + candidate_descriptors})
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M030-hwfnq0",
        "slice_id": "S02",
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "forbidden_prior_signals": list(FORBIDDEN_PRIOR_SIGNALS),
        "forbidden_prior_signals_declared": True,
        "single_signal_change_only": True,
        "m027_baseline_locked": True,
        "m028_baseline_locked": True,
        "m029_baseline_locked": True,
        "m027_baseline_metrics": M027_BASELINE,
        "m028_baseline_metrics": M028_BASELINE,
        "m029_baseline_metrics": M029_BASELINE,
        "base_descriptor_inputs_artifact": repo_ref(base_inputs_path),
        "base_descriptor_inputs_sha256": sha256_path(base_inputs_path),
        "base_descriptor_verification_summary": base_summary,
        "base_derivation_fields": list(BASE_DERIVATION_FIELDS),
        "enhanced_derivation_fields": list(ENHANCED_DERIVATION_FIELDS),
        "added_descriptor_fields": [SELECTED_SIGNAL],
        "allowed_descriptor_fields": allowed_descriptor_fields,
        "signal_derivation_summary": {
            "allowed_inputs": ["materialized_candidate_ref", "source_record_ids", "source_anchor_sha256"],
            "forbidden_inputs": ["source_order_index", *FORBIDDEN_PRIOR_SIGNALS, "source_anchor_ref_suffix_family"],
            "raw_text_used": False,
            "labels_used": False,
            "source_order_index_used": False,
            "prior_signals_used": False,
            "source_anchor_ref_suffix_family_used": False,
            "query_cardinality_via_materialized_candidate_ref": True,
            "selected_signal_values": sorted(distribution),
            "source_record_cardinality_counts": cardinality_counts,
            "constant_signal_risk": len(distribution) == 1,
        },
        "cardinality_distribution": dict(sorted(distribution.items())),
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
            "expected_answer_fields_excluded_from_descriptor_inputs": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "r035_non_validation_declared": True,
        "r038_review_required": True,
        "non_authoritative": True,
        "non_claim_boundary": "Source-record-cardinality one-signal descriptor input only; does not validate R035 or prove retrieval quality.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-inputs", type=Path, default=BASE_INPUTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_inputs(args.base_inputs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "schema_version": SCHEMA_VERSION,
                "representation_kind": REPRESENTATION_KIND,
                "selected_signal": SELECTED_SIGNAL,
                "forbidden_prior_signals": list(FORBIDDEN_PRIOR_SIGNALS),
                "query_descriptor_count": manifest["query_descriptor_count"],
                "candidate_descriptor_count": manifest["candidate_descriptor_count"],
                "cardinality_distribution": manifest["cardinality_distribution"],
                "constant_signal_risk": manifest["signal_derivation_summary"]["constant_signal_risk"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
