from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-safe-structural-descriptor-remediation-scoring.py"
INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json"
LABELS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_evaluation_labels.json"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/safe_structural_descriptor_remediation_scoring_proof.json"


def load_module(name: str = "safe_structural_descriptor_remediation_scoring") -> ModuleType:
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
    scorer = load_module(f"safe_structural_scoring_{text[:8].replace(' ', '_')}")
    try:
        fn(scorer)
    except scorer.SafeStructuralDescriptorScoringError as exc:
        assert text in str(exc)
    else:
        raise AssertionError("expected SafeStructuralDescriptorScoringError")


def test_checked_in_proof_has_expected_boundaries() -> None:
    proof = load_json(PROOF)

    assert proof["schema_version"] == "safe-structural-descriptor-remediation-scoring-proof/v1"
    assert proof["milestone_id"] == "M028-yejcai"
    assert proof["slice_id"] == "S03"
    assert proof["status"] == "completed"
    assert proof["scoring_mode"] == "local_user_bge_m3_safe_structural_descriptor_similarity_v1"
    assert proof["descriptor_inputs_artifact"] == "prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json"
    assert proof["outcome_classification"] == "improvement"
    assert proof["m027_baseline_metrics"] == {"mrr": 0.680555, "recall_at_1": 0.5, "recall_at_3": 0.833333, "runtime_boundary_confirmed": 1.0}
    assert proof["evaluation_label_boundary"]["post_scoring_only"] is True
    assert proof["evaluation_label_boundary"]["forbidden_as_descriptor_input"] is True
    assert proof["evaluation_label_boundary"]["loaded_after_score_generation"] is True
    assert proof["runtime_boundary"]["model_id"] == "deepvk/USER-bge-m3"
    assert proof["runtime_boundary"]["observed_vector_dimension"] == 1024
    assert proof["runtime_boundary"]["managed_api_used"] is False
    assert proof["runtime_boundary"]["network_used"] is False
    assert proof["score_count"] == 36
    assert proof["metrics"] == {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0, "runtime_boundary_confirmed": 1.0}
    assert proof["metric_deltas_vs_m027"]["delta_vs_m027_mrr"] == 0.236112
    assert proof["metric_deltas_vs_m027"]["delta_vs_m027_recall_at_1"] == 0.333333
    assert "Does not validate R035." in proof["non_claims"]


def test_scores_rank_all_candidates_per_case() -> None:
    proof = load_json(PROOF)
    scores_by_case: dict[str, list[dict[str, Any]]] = {}
    for row in proof["scores"]:
        scores_by_case.setdefault(row["case_id"], []).append(row)

    assert len(scores_by_case) == 6
    assert all(len(rows) == 6 for rows in scores_by_case.values())
    assert all(sorted(row["observed_rank"] for row in rows) == [1, 2, 3, 4, 5, 6] for rows in scores_by_case.values())


def test_evaluation_labels_are_post_scoring_only() -> None:
    labels = load_json(LABELS)

    assert labels["schema_version"] == "materialized-descriptor-evaluation-labels/v1"
    assert labels["post_scoring_only"] is True
    assert labels["forbidden_as_descriptor_input"] is True
    assert labels["label_count"] == 6
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
    scorer = load_module("safe_structural_scoring_metrics")
    proof = load_json(PROOF)
    labels = scorer.load_evaluation_labels()

    metrics = scorer.compute_metrics(proof["scores"], labels)

    assert metrics == {"mrr": 0.916667, "recall_at_1": 0.833333, "recall_at_3": 1.0}


def test_expected_fields_in_scores_are_rejected() -> None:
    proof = load_json(PROOF)
    proof["scores"][0]["expected_candidate_ids"] = [proof["scores"][0]["candidate_id"]]

    def run(scorer: ModuleType) -> None:
        scorer.compute_metrics(proof["scores"], scorer.load_evaluation_labels())

    expect_error(run, "expected_answer_leakage")


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


def test_runtime_boundary_blocks_managed_api(tmp_path: Path) -> None:
    scorer = load_module("safe_structural_scoring_runtime")
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


def test_runtime_boundary_blocks_network(tmp_path: Path) -> None:
    scorer = load_module("safe_structural_scoring_network")
    runtime = write_json(
        tmp_path,
        "runtime.json",
        {
            "runtime_status": "confirmed_runtime",
            "model_id": "deepvk/USER-bge-m3",
            "vector_dimension": 1024,
            "managed_api_used": False,
            "raw_vectors_persisted": False,
            "network_used": True,
        },
    )

    boundary = scorer.runtime_boundary(10, runtime)

    assert boundary["confirmed"] is False
    assert "network_forbidden" in boundary["diagnostic_codes"]


def test_labels_with_wrong_boundary_are_rejected(tmp_path: Path) -> None:
    labels = load_json(LABELS)
    labels["post_scoring_only"] = False
    path = write_json(tmp_path, "labels.json", labels)

    def run(scorer: ModuleType) -> None:
        scorer.load_evaluation_labels(path)

    expect_error(run, "evaluation label boundary missing")


def test_descriptor_input_with_expected_label_is_rejected() -> None:
    inputs = load_json(INPUTS)
    inputs["query_descriptors"][0]["expected_label"] = "blocked"

    def run(scorer: ModuleType) -> None:
        scorer.assert_safe_payload(inputs)

    expect_error(run, "unsafe field name")


def test_report_rejects_unsafe_string_fragment() -> None:
    def run(scorer: ModuleType) -> None:
        scorer.assert_safe_payload({"note": "Федеральный закон"})

    expect_error(run, "unsafe payload fragment")
