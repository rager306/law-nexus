#!/usr/bin/env python3
"""Run M026 held-out query-intent ablation proof."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json"
EVALUATION_LABELS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json"
SCORING_PROOF = ROOT / "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json"
REPORT = ROOT / "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_ablation_proof.json"
SCORING_SCRIPT = ROOT / "scripts/verify-held-out-semantic-descriptor-scoring.py"
INPUT_VERIFIER_SCRIPT = ROOT / "scripts/verify-held-out-semantic-descriptor-inputs.py"
SCHEMA_VERSION = "held-out-semantic-descriptor-ablation-proof/v1"
ABLATION_FIELD = "query_intent"
ABLATION_TO = "locate_evidence_span"
ALLOWED_DIAGNOSES = {
    "held_out_success_survives_ablation",
    "held_out_success_depends_on_descriptor_signal",
    "held_out_scoring_blocked",
    "held_out_metric_mismatch",
}


class HeldOutAblationError(RuntimeError):
    """Raised when held-out ablation proof cannot be produced."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HeldOutAblationError(f"input_missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise HeldOutAblationError(f"malformed JSON: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise HeldOutAblationError(f"JSON root must be object: {path}")
    return payload


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest_rows(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = json.dumps(list(rows), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise HeldOutAblationError(f"module load failed: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def update_query_intent_tokens(tokens: Sequence[str], value: str) -> list[str]:
    return [token if not token.startswith(f"{ABLATION_FIELD}:") else f"{ABLATION_FIELD}:{value}" for token in tokens]


def build_ablated_manifest(source: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    ablated = copy.deepcopy(dict(source))
    changed_fields: list[dict[str, str]] = []
    query_descriptors = ablated.get("query_descriptors")
    if not isinstance(query_descriptors, list):
        raise HeldOutAblationError("query descriptors missing")
    for item in query_descriptors:
        if not isinstance(item, dict):
            raise HeldOutAblationError("query descriptor must be object")
        descriptors = item.get("descriptors")
        if not isinstance(descriptors, dict):
            raise HeldOutAblationError("query descriptor values missing")
        original = descriptors.get(ABLATION_FIELD)
        if not isinstance(original, str):
            raise HeldOutAblationError("query_intent missing")
        if original == ABLATION_TO:
            continue
        descriptors[ABLATION_FIELD] = ABLATION_TO
        tokens = item.get("descriptor_tokens")
        if not isinstance(tokens, list):
            raise HeldOutAblationError("descriptor tokens missing")
        item["descriptor_tokens"] = update_query_intent_tokens(tokens, ABLATION_TO)
        changed_fields.append(
            {
                "descriptor_input_id": str(item.get("descriptor_input_id")),
                "case_id": str(item.get("case_id")),
                "field": ABLATION_FIELD,
                "from": original,
                "to": ABLATION_TO,
            }
        )
    if not changed_fields:
        raise HeldOutAblationError("ablation made no changes")
    return ablated, changed_fields


def run_scoring_with_manifest(scoring: ModuleType, manifest_path: Path, timeout_seconds: int) -> dict[str, Any]:
    previous = getattr(scoring, "DESCRIPTOR_INPUTS")
    try:
        setattr(scoring, "DESCRIPTOR_INPUTS", manifest_path)
        return scoring.build_report(None, None, timeout_seconds)
    finally:
        setattr(scoring, "DESCRIPTOR_INPUTS", previous)


def classify(current: Mapping[str, Any], ablated: Mapping[str, Any]) -> str:
    if ablated.get("status") != "completed":
        return "held_out_scoring_blocked"
    current_metrics = current.get("metrics")
    ablated_metrics = ablated.get("metrics")
    if not isinstance(current_metrics, Mapping) or not isinstance(ablated_metrics, Mapping):
        return "held_out_metric_mismatch"
    metric_names = ("mrr", "recall_at_1", "recall_at_3")
    if all(float(ablated_metrics.get(name, -1.0)) == float(current_metrics.get(name, -2.0)) for name in metric_names):
        return "held_out_success_survives_ablation"
    return "held_out_success_depends_on_descriptor_signal"


def build_report(timeout_seconds: int) -> dict[str, Any]:
    source = load_json(DESCRIPTOR_INPUTS)
    scoring_proof = load_json(SCORING_PROOF)
    scoring = load_module(SCORING_SCRIPT, "held_out_scoring_for_ablation")
    input_verifier = load_module(INPUT_VERIFIER_SCRIPT, "held_out_input_verifier_for_ablation")
    ablated_manifest, changed_fields = build_ablated_manifest(source)
    candidate_digest = digest_rows(source.get("candidate_descriptors", []))
    label_digest = sha256_path(EVALUATION_LABELS)
    with tempfile.TemporaryDirectory(prefix="m026-held-out-ablation-") as temp_dir:
        temp_path = Path(temp_dir) / "held_out_query_intent_ablation_manifest.json"
        write_json(temp_path, ablated_manifest)
        verification = input_verifier.verify_manifest(temp_path)
        ablated_report = run_scoring_with_manifest(scoring, temp_path, timeout_seconds)
    current_report = scoring.build_report(None, None, timeout_seconds)
    diagnosis = classify(current_report, ablated_report)
    if diagnosis not in ALLOWED_DIAGNOSES:
        raise HeldOutAblationError(f"invalid diagnosis: {diagnosis}")
    metric_deltas_after_ablation = {
        key: round(float(ablated_report["metrics"].get(key, 0.0)) - float(current_report["metrics"].get(key, 0.0)), 6)
        for key in current_report["metrics"]
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "milestone_id": "M026-1uqmzc",
        "slice_id": "S04",
        "status": "ok",
        "ablation_scope": "held_out_query_intent_only",
        "dependency_diagnosis": diagnosis,
        "source_descriptor_manifest": "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json",
        "source_descriptor_manifest_sha256": sha256_path(DESCRIPTOR_INPUTS),
        "source_scoring_proof": "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json",
        "source_scoring_proof_sha256": sha256_path(SCORING_PROOF),
        "evaluation_labels": "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json",
        "evaluation_labels_sha256": label_digest,
        "current_scoring_status": scoring_proof.get("status"),
        "current_metrics": current_report["metrics"],
        "ablated_metrics": ablated_report["metrics"],
        "metric_deltas_after_ablation": metric_deltas_after_ablation,
        "changed_fields": changed_fields,
        "fixed_invariants": {
            "ablation_changes_one_signal_at_a_time": True,
            "changed_signal": ABLATION_FIELD,
            "candidate_descriptors_fixed": candidate_digest == digest_rows(ablated_manifest.get("candidate_descriptors", [])),
            "evaluation_labels_fixed": label_digest == sha256_path(EVALUATION_LABELS),
            "metrics_policy_fixed": True,
            "runtime_model_fixed": scoring.MODEL_ID,
            "expected_vector_dimension_fixed": scoring.EXPECTED_VECTOR_DIMENSION,
            "scoring_mode_fixed": scoring.SCORING_MODE,
            "temporary_manifest_persisted": False,
        },
        "descriptor_verification_summary": verification,
        "score_digest": {
            "current_scores_sha256": digest_rows(current_report["scores"]),
            "ablated_scores_sha256": digest_rows(ablated_report["scores"]),
        },
        "redaction": {
            "source_text_excluded": True,
            "query_text_excluded": True,
            "raw_vectors_excluded": True,
            "external_payloads_excluded": True,
            "generated_answer_prose_excluded": True,
            "generated_query_excluded": True,
            "absolute_paths_excluded": True,
            "gsd_exec_paths_excluded": True,
        },
        "non_authoritative": True,
        "non_claim_boundary": "Held-out ablation proof only; does not prove product retrieval quality or validate R035.",
    }
    if report["fixed_invariants"]["candidate_descriptors_fixed"] is not True:
        raise HeldOutAblationError("candidate descriptors changed")
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args.timeout_seconds)
        if not args.no_write:
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except HeldOutAblationError as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc), "non_authoritative": True}, sort_keys=True))
        return 1
    print(
        json.dumps(
            {
                "status": report["status"],
                "dependency_diagnosis": report["dependency_diagnosis"],
                "current_metrics": report["current_metrics"],
                "ablated_metrics": report["ablated_metrics"],
                "metric_deltas_after_ablation": report["metric_deltas_after_ablation"],
                "changed_field_count": len(report["changed_fields"]),
                "non_authoritative": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
