#!/usr/bin/env python3
"""Build M028 enhanced descriptors with one safe structural neighborhood signal."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json"
MATERIALIZATION = ROOT / "prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json"
BASE_VERIFIER = ROOT / "scripts/verify-materialized-descriptor-inputs.py"
OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json"
SCHEMA_VERSION = "safe-structural-descriptor-remediation-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_neighborhood_v1"
SELECTED_SIGNAL = "safe_source_order_neighborhood_bucket"
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
NEIGHBOR_VALUES = [
    "source_order_neighbor_first",
    "source_order_neighbor_after_source_block",
    "source_order_neighbor_between_evidence_spans",
    "source_order_neighbor_before_late_gap",
    "source_order_neighbor_late",
]
M027_BASELINE = {
    "mrr": 0.680555,
    "recall_at_1": 0.5,
    "recall_at_3": 0.833333,
    "runtime_boundary_confirmed": 1.0,
    "score_count": 36,
}


class SafeStructuralDescriptorBuildError(RuntimeError):
    """Raised when enhanced descriptors cannot be built safely."""


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SafeStructuralDescriptorBuildError("JSON root must be object")
    return payload


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SafeStructuralDescriptorBuildError(f"module load failed: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_base_inputs(path: Path) -> dict[str, Any]:
    verifier = load_module(BASE_VERIFIER, "m028_base_descriptor_verifier")
    return verifier.verify_manifest(path)


def materialization_index(path: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(path)
    candidates = payload.get("materialized_candidates")
    if not isinstance(candidates, list) or not candidates:
        raise SafeStructuralDescriptorBuildError("materialized candidates missing")
    index: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise SafeStructuralDescriptorBuildError("materialized candidate must be object")
        candidate_id = str(candidate.get("candidate_id"))
        source_order_index = candidate.get("source_order_index")
        if not isinstance(source_order_index, int):
            raise SafeStructuralDescriptorBuildError(f"source_order_index missing: {candidate_id}")
        index[candidate_id] = {
            "candidate_kind": str(candidate.get("candidate_kind")),
            "source_order_index": source_order_index,
            "source_anchor_ref": str(candidate.get("source_anchor_id")),
            "source_anchor_sha256": str(candidate.get("source_anchor_sha256")),
        }
    return index


def neighborhood_bucket(candidate_id: str, ordered_ids: Sequence[str], materialized: Mapping[str, Mapping[str, Any]]) -> str:
    position = ordered_ids.index(candidate_id)
    candidate = materialized[candidate_id]
    previous_id = ordered_ids[position - 1] if position > 0 else None
    next_id = ordered_ids[position + 1] if position + 1 < len(ordered_ids) else None
    if previous_id is None:
        return "source_order_neighbor_first"
    previous_kind = materialized[previous_id]["candidate_kind"]
    current_index = int(candidate["source_order_index"])
    next_index = int(materialized[next_id]["source_order_index"]) if next_id is not None else None
    if previous_kind == "source_block":
        return "source_order_neighbor_after_source_block"
    if next_index is not None and next_index - current_index > 1:
        return "source_order_neighbor_before_late_gap"
    if next_id is None:
        return "source_order_neighbor_late"
    return "source_order_neighbor_between_evidence_spans"


def enhanced_tokens(descriptors: Mapping[str, str]) -> list[str]:
    return [f"{field}:{descriptors[field]}" for field in ENHANCED_DERIVATION_FIELDS]


def enhance_item(item: Mapping[str, Any], materialized: Mapping[str, Mapping[str, Any]], ordered_ids: Sequence[str]) -> dict[str, Any]:
    materialized_ref = str(item.get("materialized_candidate_ref"))
    if materialized_ref not in materialized:
        raise SafeStructuralDescriptorBuildError(f"unknown materialized ref: {materialized_ref}")
    base_descriptors = item.get("descriptors")
    if not isinstance(base_descriptors, Mapping):
        raise SafeStructuralDescriptorBuildError("base descriptors missing")
    descriptors = {str(key): str(value) for key, value in base_descriptors.items()}
    if tuple(descriptors.keys()) and set(descriptors) != set(BASE_DERIVATION_FIELDS):
        raise SafeStructuralDescriptorBuildError("base descriptor field mismatch")
    bucket = neighborhood_bucket(materialized_ref, ordered_ids, materialized)
    descriptors[SELECTED_SIGNAL] = bucket
    enhanced = dict(item)
    enhanced["representation_kind"] = REPRESENTATION_KIND
    enhanced["descriptors"] = descriptors
    enhanced["descriptor_tokens"] = enhanced_tokens(descriptors)
    enhanced["selected_signal"] = SELECTED_SIGNAL
    enhanced["selected_signal_value"] = bucket
    enhanced["source_order_index"] = materialized[materialized_ref]["source_order_index"]
    return enhanced


def build_inputs(base_inputs_path: Path = BASE_INPUTS, materialization_path: Path = MATERIALIZATION) -> dict[str, Any]:
    base_summary = verify_base_inputs(base_inputs_path)
    base_inputs = load_json(base_inputs_path)
    materialized = materialization_index(materialization_path)
    ordered_ids = [candidate_id for candidate_id, _ in sorted(materialized.items(), key=lambda item: int(item[1]["source_order_index"]))]
    query_items = base_inputs.get("query_descriptors")
    candidate_items = base_inputs.get("candidate_descriptors")
    if not isinstance(query_items, list) or not isinstance(candidate_items, list):
        raise SafeStructuralDescriptorBuildError("descriptor arrays missing")
    query_descriptors = [enhance_item(item, materialized, ordered_ids) for item in query_items if isinstance(item, Mapping)]
    candidate_descriptors = [enhance_item(item, materialized, ordered_ids) for item in candidate_items if isinstance(item, Mapping)]
    allowed_descriptor_fields = dict(base_inputs.get("allowed_descriptor_fields", {}))
    allowed_descriptor_fields[SELECTED_SIGNAL] = NEIGHBOR_VALUES
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M028-yejcai",
        "slice_id": "S02",
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "single_signal_change_only": True,
        "m027_baseline_locked": True,
        "m027_baseline_metrics": M027_BASELINE,
        "base_descriptor_inputs_artifact": repo_ref(base_inputs_path),
        "base_descriptor_inputs_sha256": sha256_path(base_inputs_path),
        "base_descriptor_verification_summary": base_summary,
        "materialization_artifact": repo_ref(materialization_path),
        "materialization_sha256": sha256_path(materialization_path),
        "base_derivation_fields": list(BASE_DERIVATION_FIELDS),
        "enhanced_derivation_fields": list(ENHANCED_DERIVATION_FIELDS),
        "added_descriptor_fields": [SELECTED_SIGNAL],
        "allowed_descriptor_fields": allowed_descriptor_fields,
        "signal_derivation_summary": {
            "allowed_inputs": ["materialized_candidate_ref", "source_order_index", "candidate_kind", "source_anchor_ref", "source_anchor_sha256"],
            "raw_text_used": False,
            "labels_used": False,
            "source_order_index_values": [int(materialized[candidate_id]["source_order_index"]) for candidate_id in ordered_ids],
            "selected_signal_values": sorted({item["selected_signal_value"] for item in query_descriptors}),
        },
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
        "non_claim_boundary": "One-signal descriptor remediation input only; does not validate R035 or prove retrieval quality.",
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-inputs", type=Path, default=BASE_INPUTS)
    parser.add_argument("--materialization", type=Path, default=MATERIALIZATION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_inputs(args.base_inputs, args.materialization)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "schema_version": SCHEMA_VERSION, "representation_kind": REPRESENTATION_KIND, "selected_signal": SELECTED_SIGNAL, "query_descriptor_count": manifest["query_descriptor_count"], "candidate_descriptor_count": manifest["candidate_descriptor_count"], "non_authoritative": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
