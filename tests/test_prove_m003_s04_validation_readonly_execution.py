from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m003-s04-validation-readonly-execution.py"
PROOF_SCRIPT_PATH = ROOT / "scripts/prove-m003-s04-validation-readonly-execution.py"


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_verifier() -> ModuleType:
    return load_module("verify_m003_s04_validation_readonly_execution", SCRIPT_PATH)


def load_proof() -> ModuleType:
    return load_module("prove_m003_s04_validation_readonly_execution", PROOF_SCRIPT_PATH)


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
            "attempted": True,
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


def s03_payload(*, status: str = "confirmed-runtime", accepted: bool = True, text: str | None = None) -> dict[str, object]:
    candidate: dict[str, object] = {
        "accepted": accepted,
        "categories": [],
        "has_comment": False,
        "has_markdown_fence": False,
        "has_multi_statement": False,
        "has_prose_prefix": False,
        "has_prose_suffix": False,
        "has_think_tag": False,
        "raw_provider_body_persisted": False,
        "root_cause": "none" if status == "confirmed-runtime" else "provider-malformed-response",
        "sha256_12": "abc123def456" if accepted else None,
        "starts_with": "MATCH" if accepted else None,
        "status": status,
        "text_length": len(text or ""),
        "trimmed_length": len((text or "").strip()),
    }
    if text is not None:
        candidate["normalized_text"] = text
    return {
        "schema_version": "m003-s03-reasoning-safe-candidate/v2",
        "status": status,
        "root_cause": "none" if status == "confirmed-runtime" else "provider-malformed-response",
        "phase": "candidate-classification" if status == "confirmed-runtime" else "provider-response",
        "provider_attempts": 1,
        "candidate": candidate,
    }


def write_s03(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "S03-REASONING-SAFE-CANDIDATE.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_proof_skips_current_failed_runtime_s03_without_validation_or_execution(tmp_path: Path) -> None:
    proof = load_proof()
    s03_path = write_s03(tmp_path, s03_payload(status="failed-runtime", accepted=False))

    artifact = proof.build_artifact(s03_path, proof.DEFAULT_SCHEMA_CONTRACT)

    assert artifact["status"] == "skipped"
    assert artifact["root_cause"] == "candidate-unavailable"
    assert artifact["s03_source"]["status"] == "failed-runtime"
    assert artifact["s03_source"]["candidate_accepted"] is False
    assert artifact["validation"]["attempted"] is False
    assert artifact["validation"]["accepted"] is False
    assert artifact["execution"]["attempted"] is False


def test_proof_rejects_clean_s03_candidate_that_fails_m002_validation(tmp_path: Path) -> None:
    proof = load_proof()
    s03_path = write_s03(tmp_path, s03_payload(text="CREATE (:Article {id: $id}) RETURN 1 LIMIT 1"))

    artifact = proof.build_artifact(s03_path, proof.DEFAULT_SCHEMA_CONTRACT)

    assert artifact["status"] == "validation-rejected"
    assert artifact["root_cause"] == "validation-rejected"
    assert artifact["validation"]["attempted"] is True
    assert artifact["validation"]["accepted"] is False
    assert artifact["validation"]["rejection_codes"] == ["E_WRITE_OPERATION"]
    assert artifact["execution"]["attempted"] is False


class FakeGraph:
    def __init__(self, result: object | None = None) -> None:
        self.calls: list[tuple[str, dict[str, object], int]] = []
        self.result = result if result is not None else [["article:44fz:1", "evidence:44fz:art1:span1", "sourceblock:garant:44fz:1"]]

    def ro_query(self, query: str, params: dict[str, object], timeout: int) -> object:
        self.calls.append((query, params, timeout))
        return self.result


def accepted_report(query: str) -> Any:
    proof = load_proof()
    contract = proof.load_schema_contract(proof.DEFAULT_SCHEMA_CONTRACT)
    report = proof.validate_candidate(query, contract, query_case="unit")
    assert report.accepted is True
    return report


def accepted_query() -> str:
    return """MATCH (span:EvidenceSpan)-[:SUPPORTS]->(article:Article)-[:SUPPORTED_BY]->(block:SourceBlock),
                     (span)-[:IN_BLOCK]->(block)
              WHERE article.id = $article_id
              RETURN article.id, span.id, block.id, block.source_id, span.start_offset, span.end_offset
              LIMIT 5"""


def test_execute_validated_calls_only_ro_query_with_timeout_and_safe_params() -> None:
    proof = load_proof()
    query = accepted_query()
    report = accepted_report(query)
    graph = FakeGraph()

    summary = proof.execute_validated(report, {"article_id": "article:44fz:1"}, graph)

    assert graph.calls == [(report.normalized_query, {"article_id": "article:44fz:1"}, 1000)]
    assert summary["attempted"] is True
    assert summary["status"] == "confirmed-runtime"
    assert summary["method"] == "Graph.ro_query"
    assert summary["timeout_ms"] == 1000
    assert summary["row_shape_summary"] == {
        "row_count_category": "non-empty",
        "column_categories": ["Article.id", "EvidenceSpan.id", "SourceBlock.id"],
        "column_type_categories": ["identifier", "identifier", "identifier"],
        "raw_rows_persisted": False,
    }
    assert summary["synthetic_identifier_categories"] == ["article_id", "evidence_span_id", "source_block_id"]
    assert summary["parameter_summary"] == {
        "article_id": {"type_category": "string", "value_category": "synthetic-article-id"}
    }


def test_execute_validated_rejects_unaccepted_validation_report_without_graph_call() -> None:
    proof = load_proof()
    contract = proof.load_schema_contract(proof.DEFAULT_SCHEMA_CONTRACT)
    report = proof.validate_candidate("CREATE (:Article {id: $id}) RETURN 1 LIMIT 1", contract, query_case="unit")
    graph = FakeGraph()

    with pytest.raises(proof.ExecutionContractError, match="validation report must be accepted"):
        proof.execute_validated(report, {"id": "article:44fz:1"}, graph)

    assert graph.calls == []


def test_execute_validated_rejects_unsafe_parameter_categories_without_graph_call() -> None:
    proof = load_proof()
    graph = FakeGraph()

    with pytest.raises(proof.ExecutionContractError, match="unsafe parameter"):
        proof.execute_validated(accepted_report(accepted_query()), {"article_id": "raw legal text value"}, graph)

    assert graph.calls == []


def test_proof_executes_evidence_return_candidate_with_injected_synthetic_graph(tmp_path: Path) -> None:
    proof = load_proof()
    s03_path = write_s03(tmp_path, s03_payload(text=accepted_query()))
    graph = FakeGraph()

    artifact = proof.build_artifact(
        s03_path,
        proof.DEFAULT_SCHEMA_CONTRACT,
        graph_factory=lambda: graph,
        setup_synthetic_graph=lambda _graph: None,
        cleanup_synthetic_graph=lambda _graph: None,
    )

    assert artifact["status"] == "confirmed-runtime"
    assert artifact["root_cause"] == "none"
    assert artifact["phase"] == "execution"
    assert artifact["validation"]["attempted"] is True
    assert artifact["validation"]["accepted"] is True
    assert artifact["validation"]["query_shape_category"] == "evidence-return-readonly"
    assert artifact["validation"]["safe_parameter_categories"] == {"article_id": "identifier"}
    assert artifact["execution"]["attempted"] is True
    assert artifact["execution"]["status"] == "confirmed-runtime"
    assert graph.calls == [(graph.calls[0][0], {"article_id": "article:44fz:1"}, 1000)]
    assert "normalized_query" not in artifact["validation"]


def test_proof_cli_writes_verifiable_artifact_for_failed_runtime_skip(tmp_path: Path) -> None:
    s03_path = write_s03(tmp_path, s03_payload(status="failed-runtime", accepted=False))
    artifact_dir = tmp_path / "artifacts"

    completed = subprocess.run(
        [sys.executable, str(PROOF_SCRIPT_PATH), "--s03-artifact", str(s03_path), "--artifact-dir", str(artifact_dir)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["status"] == "skipped"
    artifact_path = artifact_dir / "S04-VALIDATION-READONLY-EXECUTION.json"
    markdown_path = artifact_dir / "S04-VALIDATION-READONLY-EXECUTION.md"
    assert artifact_path.exists()
    assert markdown_path.exists()
    assert "Raw rows persisted: `False`" in markdown_path.read_text(encoding="utf-8")
    verifier = load_verifier()
    assert verifier.verify_artifact(artifact_path)["status"] == "skipped"


def test_accepts_blocked_environment_before_execution_attempt(verifier: ModuleType, tmp_path: Path) -> None:
    payload = base_artifact()
    payload.update({"status": "blocked-environment", "root_cause": "blocked-environment", "phase": "execution"})
    payload["execution"] = {
        "attempted": False,
        "status": "blocked-environment",
        "method": None,
        "timeout_ms": None,
        "graph_kind": "synthetic-legalgraph",
        "graph_name_category": "not-run",
        "row_shape_summary": {
            "row_count_category": "not-run",
            "column_categories": [],
            "column_type_categories": [],
            "raw_rows_persisted": False,
        },
        "synthetic_identifier_categories": [],
        "parameter_summary": {},
        "diagnostics": {"root_cause": "blocked-environment", "error_category": "ModuleNotFoundError"},
    }

    result = verifier.verify_artifact(write_artifact(tmp_path, payload))

    assert result["verdict"] == "pass"
    assert result["status"] == "blocked-environment"
    assert result["execution_attempted"] is False


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
        "attempted": False,
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
        "attempted": True,
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


def test_rejects_confirmed_runtime_without_execution(verifier: ModuleType, tmp_path: Path) -> None:
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

    with pytest.raises(verifier.VerificationError, match="confirmed-runtime requires attempted execution"):
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
        "attempted": True,
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
