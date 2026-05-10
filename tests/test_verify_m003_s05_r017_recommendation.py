from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m003-s05-r017-recommendation.py"
RECOMMENDATION_PATH = ROOT / "prd/08_m003_minimax_pyo3_functioning_proof.md"
CLOSURE_PATH = ROOT / ".gsd/milestones/M003/slices/S05/S05-R017-PROOF-CLOSURE.json"
UPSTREAM_PATHS = {
    "S01": ROOT / ".gsd/milestones/M003/slices/S01/S01-MINIMAX-LIVE-BASELINE.json",
    "S02": ROOT / ".gsd/milestones/M003/slices/S02/S02-MINIMAX-PYO3-ENDPOINT.json",
    "S03": ROOT / ".gsd/milestones/M003/slices/S03/S03-REASONING-SAFE-CANDIDATE.json",
    "S04": ROOT / ".gsd/milestones/M003/slices/S04/S04-VALIDATION-READONLY-EXECUTION.json",
}


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m003_s05_r017_recommendation", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def verifier() -> ModuleType:
    return load_verifier()


@pytest.fixture()
def recommendation_text() -> str:
    return RECOMMENDATION_PATH.read_text(encoding="utf-8")


@pytest.fixture()
def closure_payload() -> dict[str, object]:
    return json.loads(CLOSURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture()
def upstream_payloads() -> dict[str, dict[str, object]]:
    return {slice_id: json.loads(path.read_text(encoding="utf-8")) for slice_id, path in UPSTREAM_PATHS.items()}


def write_case(
    tmp_path: Path,
    text: str,
    closure: dict[str, object],
    upstream: dict[str, dict[str, object]],
) -> tuple[Path, Path, dict[str, Path]]:
    recommendation = tmp_path / "recommendation.md"
    closure_path = tmp_path / "closure.json"
    upstream_dir = tmp_path / "upstream"
    upstream_dir.mkdir()
    upstream_paths: dict[str, Path] = {}
    recommendation.write_text(text, encoding="utf-8")
    closure_path.write_text(json.dumps(closure, ensure_ascii=False, indent=2), encoding="utf-8")
    for slice_id, payload in upstream.items():
        path = upstream_dir / f"{slice_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        upstream_paths[slice_id] = path
    return recommendation, closure_path, upstream_paths


def errors_for(
    verifier: ModuleType,
    tmp_path: Path,
    text: str,
    closure: dict[str, object],
    upstream: dict[str, dict[str, object]],
) -> list[str]:
    recommendation, closure_path, upstream_paths = write_case(tmp_path, text, closure, upstream)
    return verifier.verify_recommendation(recommendation, closure_path, upstream_paths).errors


def make_all_confirmed(
    closure: dict[str, object],
    upstream: dict[str, dict[str, object]],
) -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    closure = copy.deepcopy(closure)
    upstream = copy.deepcopy(upstream)
    closure["derived_recommendation_category"] = "pursue-pyo3"
    closure["category_blockers"] = []
    assert isinstance(closure["r017_effect"], dict)
    closure["r017_effect"]["status"] = "advanced-not-validated"
    assert isinstance(closure["upstream_artifacts"], dict)
    closure_upstream = closure["upstream_artifacts"]
    assert isinstance(closure_upstream["S03"], dict)
    closure_upstream["S03"]["candidate_accepted"] = True
    closure_upstream["S03"]["candidate_status"] = "accepted"
    assert isinstance(closure_upstream["S04"], dict)
    closure_upstream["S04"]["validation_accepted"] = True
    closure_upstream["S04"]["validation_attempted"] = True
    closure_upstream["S04"]["execution_attempted"] = True
    closure_upstream["S04"]["execution_status"] = "confirmed-runtime"
    closure_upstream["S04"]["status"] = "confirmed-runtime"
    upstream["S03"]["candidate_accepted"] = True
    upstream["S03"]["candidate_status"] = "accepted"
    upstream["S03"]["status"] = "confirmed-runtime"
    upstream["S04"]["validation_accepted"] = True
    upstream["S04"]["validation_attempted"] = True
    upstream["S04"]["execution_attempted"] = True
    upstream["S04"]["execution_status"] = "confirmed-runtime"
    upstream["S04"]["status"] = "confirmed-runtime"
    return closure, upstream


def test_current_recommendation_matches_current_evidence(verifier: ModuleType) -> None:
    result = verifier.verify_recommendation(RECOMMENDATION_PATH, CLOSURE_PATH, UPSTREAM_PATHS)

    assert result.ok, result.errors


def test_derives_current_pyo3_category(verifier: ModuleType, closure_payload: dict[str, object], upstream_payloads: dict[str, dict[str, object]]) -> None:
    result = verifier.VerificationResult()

    assert verifier.derive_category(closure_payload, upstream_payloads, result) == "pursue-pyo3"
    assert result.ok


def test_derives_all_confirmed_upgrade_eligibility(verifier: ModuleType, closure_payload: dict[str, object], upstream_payloads: dict[str, dict[str, object]]) -> None:
    closure, upstream = make_all_confirmed(closure_payload, upstream_payloads)
    result = verifier.VerificationResult()

    assert verifier.derive_category(closure, upstream, result) == "pursue-pyo3"
    assert result.ok


@pytest.mark.parametrize("row", ["S01", "S02", "S03", "S04", "S05"])
def test_rejects_missing_evidence_rows(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
    row: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace(f"| {row} |", "| missing |", 1), closure_payload, upstream_payloads)

    assert any(f"missing {row} row" in error for error in errors)


def test_rejects_mismatched_recommendation_category(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
) -> None:
    text = recommendation_text.replace("`pursue-pyo3`", "`pursue-pyo3-conditioned`", 1)

    errors = errors_for(verifier, tmp_path, text, closure_payload, upstream_payloads)

    assert any("does not match independently derived category" in error for error in errors)


@pytest.mark.parametrize(
    "overclaim",
    [
        "Legal KnowQL product behavior is proven.",
        "legal-answer correctness is proven.",
        "provider generation quality is proven.",
        "ODT parsing is proven.",
        "retrieval quality is proven.",
        "production FalkorDB scale is proven.",
        "ship Legal KnowQL now.",
    ],
)
def test_rejects_forbidden_product_and_legal_answer_claims(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
    overclaim: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text + f"\n{overclaim}\n", closure_payload, upstream_payloads)

    assert any("forbidden overclaim" in error for error in errors)


@pytest.mark.parametrize(
    "raw_or_secret_like",
    [
        "Authorization: Bearer abcdefghijk",
        "api_key=minimax-example",
        "sk-testsecret123456789",
        "<think>hidden reasoning</think>",
        "raw_provider_body: {'choices': []}",
        "prompt: generate cypher for this legal question",
        "raw_reasoning: chain of thought",
        "raw_legal_text: Статья 1 example",
        "raw_graph_rows: [{'n': 1}]",
    ],
)
def test_rejects_raw_secret_and_think_contamination(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
    raw_or_secret_like: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text + f"\n{raw_or_secret_like}\n", closure_payload, upstream_payloads)

    assert any("forbidden" in error for error in errors)


def test_rejects_missing_r017_active_language(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace("R017 remains active", "R017 remains pending", 1), closure_payload, upstream_payloads)

    assert any("R017 remains active" in error for error in errors)


@pytest.mark.parametrize(
    "required_non_claim",
    [
        "legal-answer correctness",
        "ODT parsing",
        "retrieval quality",
        "Russian legal terminology quality",
        "production schema grounding",
        "production FalkorDB scale",
        "raw legal evidence quality",
    ],
)
def test_rejects_missing_explicit_non_claims(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
    required_non_claim: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace(required_non_claim, ""), closure_payload, upstream_payloads)

    assert any("missing explicit non-claims" in error for error in errors)


def test_fails_closed_on_invalid_closure_json(verifier: ModuleType, tmp_path: Path, recommendation_text: str, upstream_payloads: dict[str, dict[str, object]]) -> None:
    recommendation = tmp_path / "recommendation.md"
    closure = tmp_path / "closure.json"
    recommendation.write_text(recommendation_text, encoding="utf-8")
    closure.write_text("{not-json", encoding="utf-8")

    result = verifier.verify_recommendation(recommendation, closure, UPSTREAM_PATHS)

    assert not result.ok
    assert any("Closure invalid JSON" in error for error in result.errors)


def test_fails_closed_on_invalid_closure_schema(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
) -> None:
    closure = copy.deepcopy(closure_payload)
    closure["schema_version"] = "wrong"

    errors = errors_for(verifier, tmp_path, recommendation_text, closure, upstream_payloads)

    assert any("schema_version" in error for error in errors)


def test_rejects_missing_category_line(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    closure_payload: dict[str, object],
    upstream_payloads: dict[str, dict[str, object]],
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace("**Recommendation category:**", "**Recommendation:**", 1), closure_payload, upstream_payloads)

    assert any("missing canonical recommendation category line" in error for error in errors)


def test_route_regression_falls_back_to_rest_baseline(verifier: ModuleType, closure_payload: dict[str, object], upstream_payloads: dict[str, dict[str, object]]) -> None:
    closure = copy.deepcopy(closure_payload)
    upstream = copy.deepcopy(upstream_payloads)
    assert isinstance(closure["upstream_artifacts"], dict)
    assert isinstance(closure["upstream_artifacts"]["S02"], dict)
    closure["upstream_artifacts"]["S02"]["mechanics_confirmed"] = False
    upstream["S02"]["mechanics_confirmed"] = False
    result = verifier.VerificationResult()

    assert verifier.derive_category(closure, upstream, result) == "pursue-rest-baseline"
    assert result.ok


def test_safety_regression_defers(verifier: ModuleType, closure_payload: dict[str, object], upstream_payloads: dict[str, dict[str, object]]) -> None:
    closure = copy.deepcopy(closure_payload)
    upstream = copy.deepcopy(upstream_payloads)
    assert isinstance(closure["upstream_artifacts"], dict)
    assert isinstance(closure["upstream_artifacts"]["S03"], dict)
    closure["upstream_artifacts"]["S03"]["candidate_categories"] = ["unsafe-write-query"]
    upstream["S03"]["candidate_categories"] = ["unsafe-write-query"]
    result = verifier.VerificationResult()

    assert verifier.derive_category(closure, upstream, result) == "defer"
    assert result.ok
