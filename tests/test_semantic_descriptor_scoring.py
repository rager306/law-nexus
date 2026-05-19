from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / "scripts/verify-semantic-descriptor-scoring.py"
PROOF = ROOT / "prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json"
FIXTURE = ROOT / "prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json"
DESCRIPTOR_INPUTS = ROOT / "prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json"
SCORING_MODE = "local_user_bge_m3_safe_descriptor_similarity_v1"


def load_module(name: str = "semantic_descriptor_scoring_verifier") -> ModuleType:
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


def runtime_file(tmp_path: Path, **overrides: Any) -> Path:
    payload = {
        "runtime_status": "confirmed_runtime",
        "model_id": "deepvk/USER-bge-m3",
        "observed_vector_dimension": 1024,
        "managed_api_used": False,
        "raw_vectors_persisted": False,
        "network_used": False,
    }
    payload.update(overrides)
    return write_json(tmp_path, "runtime.json", payload)


def perfect_scores(tmp_path: Path) -> Path:
    fixture = load_json(FIXTURE)
    scores: list[dict[str, Any]] = []
    for case in fixture["cases"]:
        candidates = case.get("candidates", [])
        if not candidates:
            continue
        expected = set(case.get("expected_candidate_ids", []))
        ordered = sorted(candidates, key=lambda candidate: 0 if candidate["candidate_id"] in expected else 1)
        for observed_rank, candidate in enumerate(ordered, start=1):
            scores.append(
                {
                    "case_id": case["case_id"],
                    "query_id": case["query"]["query_id"],
                    "candidate_id": candidate["candidate_id"],
                    "descriptor_input_ref": f"TEST-{candidate['candidate_id']}",
                    "scoring_mode": SCORING_MODE,
                    "observed_similarity_score": round(1.0 / observed_rank, 6),
                    "observed_rank": observed_rank,
                    "observation_status": "scored",
                    "diagnostic_codes": [],
                    "non_authoritative": True,
                }
            )
    return write_json(tmp_path, "scores.json", {"scores": scores})


def test_checked_in_proof_shape_and_positive_delta() -> None:
    proof = load_json(PROOF)

    assert proof["schema_version"] == "semantic-descriptor-scoring-proof/v1"
    assert proof["status"] == "completed"
    assert proof["scoring_mode"] == SCORING_MODE
    assert proof["runtime_boundary"]["confirmed"] is True
    assert proof["score_count"] == 10
    assert proof["metrics"]["mrr"] == 1.0
    assert proof["metrics"]["recall_at_1"] == 1.0
    assert proof["metrics"]["recall_at_3"] == 1.0
    assert proof["metrics"]["positive_with_distractor_relevant_first"] == 1.0
    assert proof["metric_deltas"]["delta_mrr"] == 0.125
    assert proof["metric_deltas"]["delta_recall_at_1"] == 0.25
    assert proof["metric_deltas"]["delta_positive_with_distractor_relevant_first"] == 1.0
    assert proof["threshold_failures"] == []
    assert proof["disposition_hint"] == "accept_candidate_pending_review"
    assert "baseline_delta_positive" in proof["diagnostic_codes"]


def test_build_report_with_injected_perfect_scores(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_perfect")

    report = verifier.build_report(runtime_file(tmp_path), perfect_scores(tmp_path), timeout_seconds=30, allow_injected_test_inputs=True)

    assert report["status"] == "completed"
    assert report["threshold_failures"] == []
    assert report["metric_deltas"]["delta_mrr"] == 0.125
    assert report["disposition_hint"] == "accept_candidate_pending_review"


def test_blocks_runtime_boundary_when_unconfirmed(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_runtime_blocked")

    report = verifier.build_report(runtime_file(tmp_path, runtime_status="blocked_environment"), perfect_scores(tmp_path), timeout_seconds=30, allow_injected_test_inputs=True)

    assert report["status"] == "blocked"
    assert report["disposition_hint"] == "blocked"
    assert "runtime_boundary_confirmed" in report["threshold_failures"]
    assert "runtime_blocked" in report["diagnostic_codes"]
    assert report["score_count"] == 0


def test_rejects_raw_vector_persistence_flag(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_raw_vectors")

    report = verifier.build_report(runtime_file(tmp_path, raw_vectors_persisted=True), perfect_scores(tmp_path), timeout_seconds=30, allow_injected_test_inputs=True)

    assert report["status"] == "blocked"
    assert "raw_vector_persistence_forbidden" in report["diagnostic_codes"]


def test_rejects_expected_answer_leakage_in_scores(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_expected_leak")
    scores = load_json(perfect_scores(tmp_path))
    scores["scores"][0]["expected_label"] = "relevant"
    scores_path = write_json(tmp_path, "scores_with_leak.json", scores)

    try:
        verifier.build_report(runtime_file(tmp_path), scores_path, timeout_seconds=30, allow_injected_test_inputs=True)
    except verifier.DescriptorScoringError as exc:
        assert "unsafe field name" in str(exc) or "expected_answer_leakage" in str(exc)
    else:
        raise AssertionError("expected DescriptorScoringError")


def test_rejects_wrong_scoring_mode(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_wrong_mode")
    scores = load_json(perfect_scores(tmp_path))
    scores["scores"][0]["scoring_mode"] = "fixture_expected_order"
    scores_path = write_json(tmp_path, "scores_wrong_mode.json", scores)

    try:
        verifier.build_report(runtime_file(tmp_path), scores_path, timeout_seconds=30, allow_injected_test_inputs=True)
    except verifier.DescriptorScoringError as exc:
        assert "scoring mode mismatch" in str(exc)
    else:
        raise AssertionError("expected DescriptorScoringError")


def test_rejects_missing_score(tmp_path: Path) -> None:
    verifier = load_module("descriptor_scoring_missing_score")
    scores = load_json(perfect_scores(tmp_path))
    scores["scores"][0].pop("observed_similarity_score")
    scores_path = write_json(tmp_path, "scores_missing_score.json", scores)

    try:
        verifier.build_report(runtime_file(tmp_path), scores_path, timeout_seconds=30, allow_injected_test_inputs=True)
    except verifier.DescriptorScoringError as exc:
        assert "observed score missing" in str(exc)
    else:
        raise AssertionError("expected DescriptorScoringError")


def test_rejects_unsafe_descriptor_manifest(tmp_path: Path, monkeypatch: Any) -> None:
    verifier = load_module("descriptor_scoring_unsafe_input")
    descriptor_inputs = load_json(DESCRIPTOR_INPUTS)
    descriptor_inputs["query_descriptors"][0]["raw_text"] = "blocked"
    bad_manifest = write_json(tmp_path, "descriptor_inputs_bad.json", descriptor_inputs)
    monkeypatch.setattr(verifier, "DESCRIPTOR_INPUTS", bad_manifest)

    try:
        verifier.build_report(runtime_file(tmp_path), perfect_scores(tmp_path), timeout_seconds=30, allow_injected_test_inputs=True)
    except verifier.DescriptorScoringError as exc:
        assert "unsafe field name" in str(exc)
    else:
        raise AssertionError("expected DescriptorScoringError")


def test_cli_rejects_injected_acceptance_inputs(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--runtime-json",
            str(runtime_file(tmp_path)),
            "--scores-json",
            str(perfect_scores(tmp_path)),
            "--no-write",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "injected runtime/scores JSON forbidden" in completed.stdout


def test_cli_test_only_injected_inputs_cannot_write_proof(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--runtime-json",
            str(runtime_file(tmp_path)),
            "--scores-json",
            str(perfect_scores(tmp_path)),
            "--allow-injected-test-inputs",
        ],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "test-only injected inputs cannot write acceptance proof" in completed.stdout
