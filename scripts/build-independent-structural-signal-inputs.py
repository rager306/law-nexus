#!/usr/bin/env python3
"""Build M029 descriptors with one independent safe anchor-family signal."""

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
BASE_VERIFIER = ROOT / "scripts/verify-materialized-descriptor-inputs.py"
OUTPUT = ROOT / "prd/research/ontology_architecture_requirements/fixtures/independent_structural_signal_inputs.json"
SCHEMA_VERSION = "independent-structural-signal-inputs/v1"
REPRESENTATION_KIND = "safe_materialized_descriptor_with_anchor_family_v1"
SELECTED_SIGNAL = "safe_anchor_family_bucket"
FORBIDDEN_REUSED_SIGNAL = "safe_source_order_neighborhood_bucket"
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
ANCHOR_FAMILY_VALUES = [
    "source_anchor_family_article",
    "source_anchor_family_paragraph",
    "source_anchor_family_unknown",
]
M027_BASELINE = {
    "mrr": 0.680555,
    "recall_at_1": 0.5,
    "recall_at_3": 0.833333,
    "runtime_boundary_confirmed": 1.0,
}
M028_BASELINE = {
    "mrr": 0.916667,
    "recall_at_1": 0.833333,
    "recall_at_3": 1.0,
    "runtime_boundary_confirmed": 1.0,
}


class IndependentSignalBuildError(RuntimeError):
    """Raised when independent descriptors cannot be built safely."""


def sha256_path(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def repo_ref(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise IndependentSignalBuildError("JSON root must be object")
    return payload


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise IndependentSignalBuildError(f"module load failed: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_base_inputs(path: Path) -> dict[str, Any]:
    verifier = load_module(BASE_VERIFIER, "m029_base_descriptor_verifier")
    return verifier.verify_manifest(path)


def anchor_family(source_anchor_ref: str) -> str:
    if source_anchor_ref.endswith("-ARTICLE"):
        return "source_anchor_family_article"
    if source_anchor_ref.endswith("-PARAGRAPH"):
        return "source_anchor_family_paragraph"
    return "source_anchor_family_unknown"


def descriptor_tokens(descriptors: Mapping[str, str]) -> list[str]:
    return [f"{field}:{descriptors[field]}" for field in ENHANCED_DERIVATION_FIELDS]


def enhance_item(item: Mapping[str, Any]) -> dict[str, Any]:
    base_descriptors = item.get("descriptors")
    if not isinstance(base_descriptors, Mapping):
        raise IndependentSignalBuildError("base descriptors missing")
    descriptors = {str(key): str(value) for key, value in base_descriptors.items()}
    if set(descriptors) != set(BASE_DERIVATION_FIELDS):
        raise IndependentSignalBuildError("base descriptor field mismatch")
    if FORBIDDEN_REUSED_SIGNAL in descriptors or FORBIDDEN_REUSED_SIGNAL in item.get("descriptor_tokens", []):
        raise IndependentSignalBuildError("forbidden reused signal present")
    source_anchor_ref = str(item.get("source_anchor_ref"))
    bucket = anchor_family(source_anchor_ref)
    descriptors[SELECTED_SIGNAL] = bucket
    enhanced = dict(item)
    enhanced["representation_kind"] = REPRESENTATION_KIND
    enhanced["descriptors"] = descriptors
    enhanced["descriptor_tokens"] = descriptor_tokens(descriptors)
    enhanced["selected_signal"] = SELECTED_SIGNAL
    enhanced["selected_signal_value"] = bucket
    # Do not copy or create source_order_index. M029 must stay independent from M028 source-order signal.
    enhanced.pop("source_order_index", None)
    return enhanced


def build_inputs(base_inputs_path: Path = BASE_INPUTS) -> dict[str, Any]:
    base_summary = verify_base_inputs(base_inputs_path)
    base_inputs = load_json(base_inputs_path)
    query_items = base_inputs.get("query_descriptors")
    candidate_items = base_inputs.get("candidate_descriptors")
    if not isinstance(query_items, list) or not isinstance(candidate_items, list):
        raise IndependentSignalBuildError("descriptor arrays missing")
    query_descriptors = [enhance_item(item) for item in query_items if isinstance(item, Mapping)]
    candidate_descriptors = [enhance_item(item) for item in candidate_items if isinstance(item, Mapping)]
    allowed_descriptor_fields = dict(base_inputs.get("allowed_descriptor_fields", {}))
    allowed_descriptor_fields[SELECTED_SIGNAL] = ANCHOR_FAMILY_VALUES
    return {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M029-yfyh51",
        "slice_id": "S02",
        "representation_kind": REPRESENTATION_KIND,
        "selected_signal": SELECTED_SIGNAL,
        "forbidden_reused_signal": FORBIDDEN_REUSED_SIGNAL,
        "forbidden_reused_signal_declared": True,
        "single_signal_change_only": True,
        "m027_baseline_locked": True,
        "m028_baseline_locked": True,
        "m027_baseline_metrics": M027_BASELINE,
        "m028_baseline_metrics": M028_BASELINE,
        "base_descriptor_inputs_artifact": repo_ref(base_inputs_path),
        "base_descriptor_inputs_sha256": sha256_path(base_inputs_path),
        "base_descriptor_verification_summary": base_summary,
        "base_derivation_fields": list(BASE_DERIVATION_FIELDS),
        "enhanced_derivation_fields": list(ENHANCED_DERIVATION_FIELDS),
        "added_descriptor_fields": [SELECTED_SIGNAL],
        "allowed_descriptor_fields": allowed_descriptor_fields,
        "signal_derivation_summary": {
            "allowed_inputs": ["source_anchor_ref", "source_anchor_sha256", "materialized_candidate_ref"],
            "forbidden_inputs": ["source_order_index", FORBIDDEN_REUSED_SIGNAL],
            "raw_text_used": False,
            "labels_used": False,
            "source_order_index_used": False,
            "forbidden_reused_signal_used": False,
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
        "non_claim_boundary": "Independent one-signal descriptor input only; does not validate R035 or prove retrieval quality.",
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
                "forbidden_reused_signal": FORBIDDEN_REUSED_SIGNAL,
                "query_descriptor_count": manifest["query_descriptor_count"],
                "candidate_descriptor_count": manifest["candidate_descriptor_count"],
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
