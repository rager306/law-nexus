from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-held-out-semantic-descriptor-scoring.py"
INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json"
LABELS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_evaluation_labels.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/held_out_semantic_descriptor_scoring_proof.json"


def load_module(name: str = "held_out_descriptor_scoring") -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, VERIFIER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def expect_error(fn: Any, text: str) -> None:
    scorer = load_module(f"held_out_scoring_{text[:8].replace(' ', '_')}")
    try:
        fn(scorer)
    except scorer.HeldOutDescriptorScoringError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected HeldOutDescriptorScoringError")


def test_checked_in_proof_has_expected_boundaries() -> None:
    proof = load_json(PROOF)

    assert proof["schema_version"] == "held-out-semantic-descriptor-scoring-proof/v1"
    assert proof["status"] == "completed"
    assert proof["scoring_mode"] == "local_user_bge_m3_held_out_descriptor_similarity_v1"
    assert proof["evaluation_label_boundary"]["post_scoring_only"] is True
    assert proof["evaluation_label_boundary"]["forbidden_as_descriptor_input"] is True
    assert proof["runtime_boundary"]["model_id"] == "deepvk/USER-bge-m3"
    assert proof["runtime_boundary"]["observed_vector_dimension"] == 1024
    assert proof["runtime_boundary"]["managed_api_used"] is False
    assert proof["metrics"]["mrr"] == 1.0
    assert proof["metric_deltas_vs_m024"]["delta_vs_m024_mrr"] == 0.125
    assert proof["metric_deltas_vs_m025"]["delta_vs_m025_mrr"] == 0.0
    assert "Does not validate R035." in proof["non_claims"]


def test_cli_rejects_injected_runtime_without_test_flag(tmp_path: Path) -> None:
    runtime = write_json(
        tmp_path,
        "runtime.json",
        {
            "runtime_status": "confirmed_runtime",
            "model_id": "deepvk/USER-bge-m3",
            "vector_dimension": 1024,
            "managed_api_used": False,
            "raw_vectors_persisted": False,
            "network_used": False,
        },
    )
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), "--runtime-json", str(runtime), "--no-write"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert "injected runtime/scores JSON forbidden" in payload["diagnostic"]


def test_test_only_injection_cannot_write(tmp_path: Path) -> None:
    runtime = write_json(
        tmp_path,
        "runtime.json",
        {
            "runtime_status": "confirmed_runtime",
            "model_id": "deepvk/USER-bge-m3",
            "vector_dimension": 1024,
            "managed_api_used": False,
            "raw_vectors_persisted": False,
            "network_used": False,
        },
    )
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), "--runtime-json", str(runtime), "--allow-injected-test-inputs"],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert "test-only injected inputs cannot write" in payload["diagnostic"]


def test_evaluation_labels_are_post_scoring_only() -> None:
    labels = load_json(LABELS)

    assert labels["schema_version"] == "held-out-semantic-descriptor-evaluation-labels/v1"
    assert labels["post_scoring_only"] is True
    assert labels["forbidden_as_descriptor_input"] is True
    assert labels["label_count"] == 5
    assert all(row["metric_scope"] == "post_scoring_only" for row in labels["labels"])


def test_descriptor_inputs_do_not_contain_evaluation_labels() -> None:
    inputs = load_json(INPUTS)
    serialized = json.dumps(inputs, ensure_ascii=False, sort_keys=True)

    for forbidden in (
        "expected_candidate_ids",
        "expected_rejected_candidate_ids",
        "expected_label",
        "expected_result",
        "selection_reason",
        '"rank"',
    ):
        assert forbidden not in serialized


def test_metric_computation_uses_labels_after_scores() -> None:
    scorer = load_module("held_out_scoring_metrics")
    proof = load_json(PROOF)
    labels = scorer.load_evaluation_labels()

    metrics = scorer.compute_metrics(proof["scores"], labels)

    assert metrics == {"mrr": 1.0, "recall_at_1": 1.0, "recall_at_3": 1.0}


def test_expected_fields_in_scores_are_rejected() -> None:
    proof = load_json(PROOF)
    proof["scores"][0]["expected_candidate_ids"] = [proof["scores"][0]["candidate_id"]]

    def run(scorer: ModuleType) -> None:
        scorer.compute_metrics(proof["scores"], scorer.load_evaluation_labels())

    expect_error(run, "expected_answer_leakage")


def test_runtime_boundary_blocks_managed_api(tmp_path: Path) -> None:
    scorer = load_module("held_out_scoring_runtime")
    runtime = write_json(
        tmp_path,
        "runtime.json",
        {
            "runtime_status": "confirmed_runtime",
            "model_id": "deepvk/USER-bge-m3",
            "vector_dimension": 1024,
            "managed_api_used": True,
            "raw_vectors_persisted": False,
            "network_used": False,
        },
    )

    boundary = scorer.runtime_boundary(10, runtime)

    assert boundary["confirmed"] is False
    assert "managed_api_forbidden" in boundary["diagnostic_codes"]


def test_labels_with_wrong_boundary_are_rejected(tmp_path: Path) -> None:
    labels = load_json(LABELS)
    labels["post_scoring_only"] = False
    path = write_json(tmp_path, "labels.json", labels)

    def run(scorer: ModuleType) -> None:
        scorer.load_evaluation_labels(path)

    expect_error(run, "evaluation label boundary missing")
