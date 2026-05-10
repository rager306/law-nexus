from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m002-s04-recommendation.py"
RECOMMENDATION_PATH = ROOT / "prd/07_m002_text_to_cypher_recommendation.md"
PROOF_PATH = ROOT / ".gsd/milestones/M002/slices/S04/S04-MINIMAX-PYO3-PROOF.json"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m002_s04_recommendation", SCRIPT_PATH)
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
def proof_payload() -> dict[str, object]:
    return json.loads(PROOF_PATH.read_text(encoding="utf-8"))


def write_case(tmp_path: Path, text: str, proof: dict[str, object]) -> tuple[Path, Path]:
    recommendation = tmp_path / "recommendation.md"
    proof_path = tmp_path / "proof.json"
    recommendation.write_text(text, encoding="utf-8")
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    return recommendation, proof_path


def errors_for(verifier: ModuleType, tmp_path: Path, text: str, proof: dict[str, object]) -> list[str]:
    recommendation, proof_path = write_case(tmp_path, text, proof)
    return verifier.verify_recommendation(recommendation, proof_path).errors


def test_current_recommendation_matches_blocked_credential_proof(verifier: ModuleType) -> None:
    result = verifier.verify_recommendation(RECOMMENDATION_PATH, PROOF_PATH)

    assert result.ok, result.errors


@pytest.mark.parametrize(
    "term",
    [
        "MiniMax-M2.7-highspeed",
        "https://api.minimax.io/v1",
        "ServiceTargetResolver",
        "PyO3",
        "REST baseline",
        "Graph.ro_query",
        "EvidenceSpan",
        "SourceBlock",
        "LLM non-authoritative",
        "R017",
        "R011",
        "validator-only",
        "defer",
    ],
)
def test_rejects_missing_required_terms(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
    term: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace(term, ""), proof_payload)

    assert any("missing required terms" in error for error in errors)


@pytest.mark.parametrize("row", ["S01", "S02", "S03", "S04"])
def test_rejects_missing_evidence_table_rows(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
    row: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace(f"| {row} |", "| missing |", 1), proof_payload)

    assert any(f"missing {row} row" in error for error in errors)


@pytest.mark.parametrize(
    "secret_like",
    [
        "Authorization: Bearer abcdefghijk",
        "Bearer abcdefghijk",
        "api_key=minimax-example",
        "sk-testsecret123456789",
        "-----BEGIN PRIVATE KEY-----",
    ],
)
def test_rejects_secret_like_strings(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
    secret_like: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text + f"\n{secret_like}\n", proof_payload)

    assert any("forbidden secret-like content" in error for error in errors)


@pytest.mark.parametrize(
    "overclaim",
    [
        "Legal KnowQL product behavior is proven.",
        "provider generation quality is proven.",
        "legal-answer correctness is proven.",
        "TextToCypherClient can route MiniMax.",
        "ship Legal KnowQL now.",
    ],
)
def test_rejects_product_and_legal_overclaims(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
    overclaim: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text + f"\n{overclaim}\n", proof_payload)

    assert any("forbidden overclaim" in error for error in errors)


def test_rejects_recommendation_category_inconsistent_with_blocked_credentials(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
) -> None:
    text = recommendation_text.replace("`pursue-pyo3-conditioned`", "`pursue-pyo3`", 1)

    errors = errors_for(verifier, tmp_path, text, proof_payload)

    assert any("does not match proof-derived category" in error for error in errors)


@pytest.mark.parametrize(
    "boundary",
    [
        "R017 is advanced but not fully validated",
        "R011 remains a supported guardrail",
        "does not implement",
        "LegalGraph Nexus product pipeline",
        "product ETL/import",
        "production graph schema",
        "Legal KnowQL parser",
        "legal-answer correctness",
    ],
)
def test_rejects_missing_r017_r011_boundary_language(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
    boundary: str,
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace(boundary, ""), proof_payload)

    assert any("R011" in error or "R017" in error for error in errors)


def test_rejects_rest_baseline_without_validation_boundary(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
    proof_payload: dict[str, object],
) -> None:
    errors = errors_for(verifier, tmp_path, recommendation_text.replace("shares the exact same validation boundary", "shares the exact same runtime", 1), proof_payload)

    assert any("same validation boundary" in error for error in errors)


def test_fails_closed_on_malformed_proof_json(
    verifier: ModuleType,
    tmp_path: Path,
    recommendation_text: str,
) -> None:
    recommendation = tmp_path / "recommendation.md"
    proof = tmp_path / "proof.json"
    recommendation.write_text(recommendation_text, encoding="utf-8")
    proof.write_text("{not-json", encoding="utf-8")

    result = verifier.verify_recommendation(recommendation, proof)

    assert not result.ok
    assert any("invalid JSON" in error for error in result.errors)


def test_derives_validator_only_when_provider_blocked_and_execution_not_confirmed(
    verifier: ModuleType,
    proof_payload: dict[str, object],
) -> None:
    proof = copy.deepcopy(proof_payload)
    assert isinstance(proof["execution"], dict)
    proof["execution"]["status"] = "skipped"

    result = verifier.VerificationResult()

    assert verifier.expected_category(proof, result) == "validator-only"
    assert result.ok


def test_derives_defer_for_failed_runtime(verifier: ModuleType, proof_payload: dict[str, object]) -> None:
    proof = copy.deepcopy(proof_payload)
    proof["status"] = "failed-runtime"
    assert isinstance(proof["execution"], dict)
    proof["execution"]["status"] = "failed-runtime"

    result = verifier.VerificationResult()

    assert verifier.expected_category(proof, result) == "defer"
    assert result.ok
