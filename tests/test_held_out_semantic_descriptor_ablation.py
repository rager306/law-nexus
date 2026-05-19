from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-held-out-semantic-descriptor-ablation.py"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_ablation_proof.json"


def load_module(name: str = "held_out_ablation") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_proof() -> dict:
    return json.loads(PROOF.read_text(encoding="utf-8"))


def test_checked_in_ablation_proof_passes_boundaries() -> None:
    proof = load_proof()

    assert proof["schema_version"] == "held-out-semantic-descriptor-ablation-proof/v1"
    assert proof["status"] == "ok"
    assert proof["slice_id"] == "S04"
    assert proof["ablation_scope"] == "held_out_query_intent_only"
    assert proof["dependency_diagnosis"] == "held_out_success_survives_ablation"
    assert proof["current_metrics"] == proof["ablated_metrics"]
    assert proof["metric_deltas_after_ablation"]["mrr"] == 0.0
    assert proof["non_authoritative"] is True
    assert "does not prove product retrieval quality" in proof["non_claim_boundary"]


def test_changed_fields_are_query_intent_only() -> None:
    proof = load_proof()
    changed = proof["changed_fields"]

    assert len(changed) == 4
    assert {row["field"] for row in changed} == {"query_intent"}
    assert {row["to"] for row in changed} == {"locate_evidence_span"}
    assert all(row["descriptor_input_id"].startswith("HO-DESCQ-M026-") for row in changed)
    assert all(row["case_id"].startswith("CASE-M026-") for row in changed)


def test_fixed_invariants_are_recorded() -> None:
    proof = load_proof()
    invariants = proof["fixed_invariants"]

    assert invariants["ablation_changes_one_signal_at_a_time"] is True
    assert invariants["changed_signal"] == "query_intent"
    assert invariants["candidate_descriptors_fixed"] is True
    assert invariants["evaluation_labels_fixed"] is True
    assert invariants["metrics_policy_fixed"] is True
    assert invariants["temporary_manifest_persisted"] is False
    assert invariants["runtime_model_fixed"] == "deepvk/USER-bge-m3"
    assert invariants["expected_vector_dimension_fixed"] == 1024
    assert invariants["scoring_mode_fixed"] == "local_user_bge_m3_held_out_descriptor_similarity_v1"


def test_digests_and_redaction_are_present() -> None:
    proof = load_proof()

    assert len(proof["source_descriptor_manifest_sha256"]) == 64
    assert len(proof["source_scoring_proof_sha256"]) == 64
    assert len(proof["evaluation_labels_sha256"]) == 64
    assert len(proof["score_digest"]["current_scores_sha256"]) == 64
    assert len(proof["score_digest"]["ablated_scores_sha256"]) == 64
    assert proof["score_digest"]["current_scores_sha256"] != proof["score_digest"]["ablated_scores_sha256"]
    assert proof["redaction"]["external_payloads_excluded"] is True
    assert proof["redaction"]["raw_vectors_excluded"] is True


def test_cli_emits_compact_ok_json_no_write() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--no-write"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
        timeout=180,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["dependency_diagnosis"] == "held_out_success_survives_ablation"
    assert payload["metric_deltas_after_ablation"]["mrr"] == 0.0


def test_classifier_detects_dependency_when_metrics_drop() -> None:
    ablation = load_module("held_out_ablation_classifier")
    current = {"status": "completed", "metrics": {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0}}
    ablated = {"status": "completed", "metrics": {"mrr": 0.5, "recall_at_1": 0.0, "recall_at_3": 1.0}}

    assert ablation.classify(current, ablated) == "held_out_success_depends_on_descriptor_signal"


def test_classifier_detects_blocked_scoring() -> None:
    ablation = load_module("held_out_ablation_blocked")
    current = {"status": "completed", "metrics": {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0}}
    ablated = {"status": "blocked", "metrics": {"mrr": 0.0, "recall_at_1": 0.0, "recall_at_3": 0.0}}

    assert ablation.classify(current, ablated) == "held_out_scoring_blocked"
