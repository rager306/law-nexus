from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m003-s04-validation-readonly-execution.py"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m003_s04_validation_readonly_execution", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def verifier() -> ModuleType:
    return load_verifier()


def base_artifact() -> dict[str, object]:
    return {
        "schema_version": "m003-s04-validation-readonly-execution/v1",
        "status": "confirmed-runtime",
        "root_cause": "none",
        "phase": "execution",
        "s03_source": {
            "schema_version": "m003-s03-reasoning-safe-candidate/v2",
            "status": "confirmed-runtime",
            "root_cause": "none",
            "phase": "candidate-classification",
            "provider_attempts": 1,
            "candidate_accepted": True,
        },
        "validation": {
            "accepted": True,
            "schema_version": "m002-legalgraph-cypher-safety-contract/v1",
            "rejection_codes": [],
            "required_evidence_returns": ["Article.id", "EvidenceSpan.id", "SourceBlock.id"],
        },
        "execution": {
            "attempted": True,
            "status": "confirmed-runtime",
            "method": "Graph.ro_query",
            "timeout_ms": 1000,
            "graph_kind": "synthetic-legalgraph",
            "row_shape_summary": {
                "row_count_category": "non-empty",
                "column_categories": ["Article.id", "EvidenceSpan.id", "SourceBlock.id"],
                "raw_rows_persisted": False,
            },
            "synthetic_identifier_categories": ["article_id", "evidence_span_id", "source_block_id"],
        },
        "redaction": {
            "raw_provider_body_persisted": False,
            "credential_persisted": False,
            "auth_header_persisted": False,
            "prompt_text_persisted": False,
            "raw_reasoning_text_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_graph_rows_persisted": False,
            "secret_like_values_persisted": False,
        },
        "boundaries": {
            "proves": [
                "S03 accepted candidate was gated through deterministic M002 validation",
                "validator-accepted Cypher executed read-only against synthetic LegalGraph-shaped data",
            ],
            "does_not_prove": [
                "provider generation quality",
                "Legal KnowQL product behavior",
                "legal-answer correctness",
                "ODT parsing",
                "retrieval quality",
                "production graph schema fitness",
                "live legal graph execution",
            ],
        },
    }


def write_artifact(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "S04-VALIDATION-READONLY-EXECUTION.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def test_accepts_current_s03_style_no_candidate_skip(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    payload.update({"status": "skipped", "root_cause": "candidate-unavailable", "phase": "s03-handoff"})
    payload["s03_source"] = {
        "schema_version": "m003-s03-reasoning-safe-candidate/v2",
        "status": "blocked-credential",
        "root_cause": "minimax-credential-missing",
        "phase": "credential-check",
        "provider_attempts": 0,
        "candidate_accepted": False,
    }
    payload["validation"] = {
        "accepted": False,
        "schema_version": "m002-legalgraph-cypher-safety-contract/v1",
        "rejection_codes": ["E_CANDIDATE_UNAVAILABLE"],
        "required_evidence_returns": [],
    }
    payload["execution"] = {
        "attempted": False,
        "status": "not-attempted",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "row_shape_summary": {"row_count_category": "not-run", "column_categories": [], "raw_rows_persisted": False},
        "synthetic_identifier_categories": [],
    }

    result = verifier.verify_artifact(write_artifact(tmp_path, payload))

    assert result["verdict"] == "pass"
    assert result["status"] == "skipped"
    assert result["root_cause"] == "candidate-unavailable"
    assert result["validation_accepted"] is False
    assert result["execution_attempted"] is False


def test_accepts_validation_rejection_without_execution(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    payload.update({"status": "validation-rejected", "root_cause": "validation-rejected", "phase": "validation"})
    payload["validation"] = {
        "accepted": False,
        "schema_version": "m002-legalgraph-cypher-safety-contract/v1",
        "rejection_codes": ["E_WRITE_OPERATION"],
        "required_evidence_returns": ["Article.id", "EvidenceSpan.id", "SourceBlock.id"],
    }
    payload["execution"] = {
        "attempted": False,
        "status": "not-attempted",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "row_shape_summary": {"row_count_category": "not-run", "column_categories": [], "raw_rows_persisted": False},
        "synthetic_identifier_categories": [],
    }

    result = verifier.verify_artifact(write_artifact(tmp_path, payload))

    assert result["verdict"] == "pass"
    assert result["status"] == "validation-rejected"
    assert result["root_cause"] == "validation-rejected"
    assert result["validation_accepted"] is False
    assert result["execution_attempted"] is False


def test_rejects_accepted_validation_without_execution(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    payload["execution"] = {
        "attempted": False,
        "status": "not-attempted",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "row_shape_summary": {"row_count_category": "not-run", "column_categories": [], "raw_rows_persisted": False},
        "synthetic_identifier_categories": [],
    }

    with pytest.raises(verifier.VerificationError, match="accepted validation requires execution.attempted=true"):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"method": "Graph.query"}, "execution.method must be Graph.ro_query"),
        ({"timeout_ms": 5000}, "execution.timeout_ms must be 1000"),
        ({"graph_kind": "live-legalgraph"}, "execution.graph_kind must be synthetic-legalgraph"),
    ],
)
def test_requires_readonly_ro_query_execution_contract(
    verifier: ModuleType, tmp_path: Path, patch: dict[str, object], message: str
) -> None:
    payload = base_artifact()
    execution = copy.deepcopy(payload["execution"])
    assert isinstance(execution, dict)
    execution.update(patch)
    payload["execution"] = execution

    with pytest.raises(verifier.VerificationError, match=message):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


def test_rejects_execution_attempt_without_validation_acceptance(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    payload.update({"status": "validation-rejected", "root_cause": "validation-rejected", "phase": "validation"})
    payload["validation"] = {
        "accepted": False,
        "schema_version": "m002-legalgraph-cypher-safety-contract/v1",
        "rejection_codes": ["E_WRITE_OPERATION"],
        "required_evidence_returns": ["Article.id"],
    }

    with pytest.raises(verifier.VerificationError, match="execution cannot be attempted unless validation.accepted is true"):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


def test_rejects_missing_validation_fields(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    validation = copy.deepcopy(payload["validation"])
    assert isinstance(validation, dict)
    validation.pop("schema_version")
    payload["validation"] = validation

    with pytest.raises(verifier.VerificationError, match="validation.schema_version is required"):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


@pytest.mark.parametrize(
    "term",
    [
        "raw_provider_body_value",
        "request_prompt",
        "reasoning_text_value",
        "raw_legal_text_value",
        "falkordb_rows_value",
        "Authorization: Bearer sk-secret-token",
    ],
)
def test_rejects_forbidden_raw_content_terms(verifier: ModuleType, tmp_path: Path, term: str) -> None:
    payload = base_artifact()
    payload["diagnostics"] = {"unsafe_value": term}

    with pytest.raises(verifier.VerificationError, match="redaction violation"):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


def test_rejects_boundary_overclaims(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    boundaries = copy.deepcopy(payload["boundaries"])
    assert isinstance(boundaries, dict)
    proves = boundaries["proves"]
    assert isinstance(proves, list)
    proves.append("Legal KnowQL product behavior is validated for production use")
    payload["boundaries"] = boundaries

    with pytest.raises(verifier.VerificationError, match="boundary overclaim"):
        verifier.verify_artifact(write_artifact(tmp_path, payload))


def test_cli_reports_categorical_failure_first_error(tmp_path: Path) -> None:
    artifact = tmp_path / "broken.json"
    artifact.write_text("{not-json", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--artifact", str(artifact)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    output = json.loads(completed.stdout)
    assert output["verdict"] == "fail"
    assert output["status"] == "contract-invalid"
    assert output["root_cause"] == "malformed-json"
    assert output["validation_accepted"] is None
    assert output["execution_attempted"] is None
    assert output["first_error"]
