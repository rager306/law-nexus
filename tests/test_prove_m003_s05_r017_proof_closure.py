from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/prove-m003-s05-r017-proof-closure.py"


def load_producer() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prove_m003_s05_r017_proof_closure", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def producer() -> ModuleType:
    return load_producer()


def s01_payload(*, status: str = "blocked-credential", root_cause: str = "minimax-credential-missing") -> dict[str, Any]:
    return {
        "schema_version": "m003-s01-minimax-live-baseline/v1",
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": 0 if status == "blocked-credential" else 1,
        "endpoint": {"preserves_v1": True, "effective_url": "https://api.minimax.io/v1/chat/completions"},
        "response_shape": {"status": status, "root_cause": root_cause, "content_kind": "not-run"},
        "safety": {
            "auth_header_persisted": False,
            "credential_persisted": False,
            "raw_body_persisted": False,
            "raw_falkordb_rows_persisted": False,
            "raw_legal_text_persisted": False,
            "request_body_persisted": False,
        },
    }


def s02_payload(*, status: str = "failed-runtime", root_cause: str = "provider-non-cypher-diagnostic") -> dict[str, Any]:
    return {
        "schema_version": "m003-s02-minimax-pyo3-endpoint/v2",
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": 1,
        "endpoint": {
            "endpoint_contract_valid": True,
            "preserves_v1": True,
            "normalization_status": "normalized",
            "effective_chat_completions_url": "https://api.minimax.io/v1/chat/completions",
        },
        "phases": {
            "build": {"status": "confirmed-runtime", "root_cause": "none"},
            "import": {"status": "confirmed-runtime", "root_cause": "none"},
            "resolver": {"status": "confirmed-runtime", "root_cause": "none"},
            "provider": {"status": status, "root_cause": root_cause, "raw_provider_body_persisted": False},
        },
        "safety": {
            "auth_headers_persisted": False,
            "credentials_persisted": False,
            "raw_falkordb_rows_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_prompt_persisted": False,
            "raw_provider_body_persisted": False,
            "think_content_persisted": False,
        },
    }


def s03_payload(*, status: str = "failed-runtime", root_cause: str = "provider-malformed-response", accepted: bool = False) -> dict[str, Any]:
    return {
        "schema_version": "m003-s03-reasoning-safe-candidate/v2",
        "status": status,
        "root_cause": root_cause,
        "provider_attempts": 1,
        "phase": "candidate-classification" if accepted else "provider-response",
        "candidate": {
            "accepted": accepted,
            "status": status,
            "root_cause": root_cause,
            "categories": [] if accepted else ["malformed-provider-shape"],
            "starts_with": "MATCH" if accepted else None,
            "sha256_12": "abc123def456" if accepted else None,
            "raw_provider_body_persisted": False,
            "text_length": 42 if accepted else 0,
            "trimmed_length": 42 if accepted else 0,
        },
        "safety": {
            "auth_header_persisted": False,
            "credential_persisted": False,
            "raw_graph_rows_persisted": False,
            "raw_legal_text_persisted": False,
            "raw_provider_body_persisted": False,
            "raw_reasoning_text_persisted": False,
            "request_text_persisted": False,
        },
    }


def s04_payload(
    *,
    status: str = "skipped",
    root_cause: str = "candidate-unavailable",
    validation_accepted: bool = False,
    execution_confirmed: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "m003-s04-validation-readonly-execution/v1",
        "status": status,
        "root_cause": root_cause,
        "phase": "execution" if execution_confirmed else "s03-handoff",
        "validation": {
            "attempted": validation_accepted,
            "accepted": validation_accepted,
            "schema_version": "m002-legalgraph-cypher-safety-contract/v1",
            "rejection_codes": [] if validation_accepted else ["E_CANDIDATE_UNAVAILABLE"],
            "required_evidence_returns": ["Article.id", "EvidenceSpan.id", "SourceBlock.id"] if validation_accepted else [],
            "query_shape_category": "evidence-return-readonly" if validation_accepted else "candidate-unavailable",
        },
        "execution": {
            "attempted": execution_confirmed,
            "status": "confirmed-runtime" if execution_confirmed else "not-attempted",
            "method": "Graph.ro_query" if execution_confirmed else None,
            "timeout_ms": 1000 if execution_confirmed else None,
            "graph_kind": "synthetic-legalgraph",
            "row_shape_summary": {"raw_rows_persisted": False, "row_count_category": "non-empty" if execution_confirmed else "not-run"},
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
    }


def write_upstreams(tmp_path: Path, payloads: dict[str, dict[str, Any]]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for slice_id, payload in payloads.items():
        path = tmp_path / f"{slice_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        paths[slice_id] = path
    return paths


def current_payloads() -> dict[str, dict[str, Any]]:
    return {
        "S01": s01_payload(),
        "S02": s02_payload(),
        "S03": s03_payload(),
        "S04": s04_payload(),
    }


def test_current_state_derives_conditioned_category_without_validating_r017(producer: ModuleType, tmp_path: Path) -> None:
    paths = write_upstreams(tmp_path, current_payloads())

    artifact = producer.build_proof_closure(paths)

    assert artifact["schema_version"] == "m003-s05-r017-proof-closure/v1"
    assert artifact["derived_recommendation_category"] == "pursue-pyo3-conditioned"
    assert artifact["r017_effect"] == {
        "status": "advanced-not-validated",
        "summary": "R017 is advanced by endpoint, provider-attempt, and safety evidence but remains active pending accepted candidate generation and read-only execution proof.",
    }
    assert artifact["requirements_advanced"] == ["R017"]
    assert artifact["requirements_validated"] == []
    assert artifact["upstream_artifacts"]["S03"]["candidate_accepted"] is False
    assert artifact["upstream_artifacts"]["S04"]["validation_accepted"] is False
    assert artifact["non_claims"] == producer.REQUIRED_NON_CLAIMS
    assert artifact["verification_summary"]["producer_status"] == "generated"


def test_synthetic_all_confirmed_state_derives_unconditioned_pyo3(producer: ModuleType, tmp_path: Path) -> None:
    payloads = current_payloads()
    payloads["S01"] = s01_payload(status="confirmed-runtime", root_cause="none")
    payloads["S02"] = s02_payload(status="confirmed-runtime", root_cause="none")
    payloads["S02"]["phases"]["provider"] = {"status": "confirmed-runtime", "root_cause": "none", "raw_provider_body_persisted": False}
    payloads["S03"] = s03_payload(status="confirmed-runtime", root_cause="none", accepted=True)
    payloads["S04"] = s04_payload(status="confirmed-runtime", root_cause="none", validation_accepted=True, execution_confirmed=True)
    paths = write_upstreams(tmp_path, payloads)

    artifact = producer.build_proof_closure(paths)

    assert artifact["derived_recommendation_category"] == "pursue-pyo3"
    assert artifact["r017_effect"]["status"] == "advanced-not-validated"
    assert artifact["requirements_validated"] == []


def test_rejects_missing_required_upstream_fields_without_outputs(producer: ModuleType, tmp_path: Path) -> None:
    payloads = current_payloads()
    del payloads["S02"]["provider_attempts"]
    paths = write_upstreams(tmp_path, payloads)

    with pytest.raises(producer.ProofClosureError, match="S02.provider_attempts is required"):
        producer.build_proof_closure(paths)


def test_rejects_wrong_schema_and_contradictory_execution(producer: ModuleType, tmp_path: Path) -> None:
    payloads = current_payloads()
    payloads["S03"]["schema_version"] = "wrong-schema/v1"
    payloads["S04"]["execution"]["attempted"] = True
    paths = write_upstreams(tmp_path, payloads)

    with pytest.raises(producer.ProofClosureError, match="S03.schema_version mismatch"):
        producer.build_proof_closure(paths)

    payloads["S03"]["schema_version"] = "m003-s03-reasoning-safe-candidate/v2"
    paths = write_upstreams(tmp_path, payloads)
    with pytest.raises(producer.ProofClosureError, match="S04 execution cannot be attempted unless validation.accepted is true"):
        producer.build_proof_closure(paths)


def test_rejects_missing_artifact_and_invalid_json(producer: ModuleType, tmp_path: Path) -> None:
    paths = write_upstreams(tmp_path, current_payloads())
    paths["S01"] = tmp_path / "missing.json"
    with pytest.raises(producer.ProofClosureError, match="missing artifact: S01"):
        producer.build_proof_closure(paths)

    bad = tmp_path / "bad.json"
    bad.write_text("{not-json", encoding="utf-8")
    paths = write_upstreams(tmp_path, current_payloads())
    paths["S02"] = bad
    with pytest.raises(producer.ProofClosureError, match="malformed JSON: S02"):
        producer.build_proof_closure(paths)


def test_rejects_secret_like_or_raw_claim_contamination(producer: ModuleType, tmp_path: Path) -> None:
    payloads = current_payloads()
    payloads["S01"]["diagnostics"] = {"unsafe": "Authorization: Bearer sk-secret-token"}
    paths = write_upstreams(tmp_path, payloads)

    with pytest.raises(producer.ProofClosureError, match="redaction violation"):
        producer.build_proof_closure(paths)

    payloads = current_payloads()
    payloads["S04"]["boundaries"] = {"proves": ["Legal KnowQL product behavior is proven for production"]}
    paths = write_upstreams(tmp_path, payloads)
    with pytest.raises(producer.ProofClosureError, match="forbidden overclaim"):
        producer.build_proof_closure(paths)


def test_cli_writes_json_and_markdown_with_redacted_categorical_content(tmp_path: Path) -> None:
    paths = write_upstreams(tmp_path, current_payloads())
    artifact_dir = tmp_path / "out"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--artifact-dir",
            str(artifact_dir),
            "--s01-artifact",
            str(paths["S01"]),
            "--s02-artifact",
            str(paths["S02"]),
            "--s03-artifact",
            str(paths["S03"]),
            "--s04-artifact",
            str(paths["S04"]),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["derived_recommendation_category"] == "pursue-pyo3-conditioned"
    json_path = artifact_dir / "S05-R017-PROOF-CLOSURE.json"
    md_path = artifact_dir / "S05-R017-PROOF-CLOSURE.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    markdown = md_path.read_text(encoding="utf-8")
    assert payload["derived_recommendation_category"] == "pursue-pyo3-conditioned"
    assert "R017 is advanced but not validated" in markdown
    assert "Legal KnowQL product behavior" in markdown
    forbidden_text = json_path.read_text(encoding="utf-8") + markdown
    assert "Authorization: Bearer" not in forbidden_text
    assert "raw provider body" not in forbidden_text.lower()
    assert "Legal KnowQL product behavior is proven" not in forbidden_text


def test_cli_does_not_overwrite_existing_outputs_when_upstream_is_malformed(tmp_path: Path) -> None:
    paths = write_upstreams(tmp_path, current_payloads())
    artifact_dir = tmp_path / "out"
    artifact_dir.mkdir()
    json_path = artifact_dir / "S05-R017-PROOF-CLOSURE.json"
    md_path = artifact_dir / "S05-R017-PROOF-CLOSURE.md"
    json_path.write_text("sentinel-json", encoding="utf-8")
    md_path.write_text("sentinel-md", encoding="utf-8")
    paths["S03"].write_text("{not-json", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--artifact-dir",
            str(artifact_dir),
            "--s01-artifact",
            str(paths["S01"]),
            "--s02-artifact",
            str(paths["S02"]),
            "--s03-artifact",
            str(paths["S03"]),
            "--s04-artifact",
            str(paths["S04"]),
        ],
        check=False,
        text=True,
        capture_output=True,
    )

    assert completed.returncode == 1
    assert "malformed JSON: S03" in completed.stderr
    assert json_path.read_text(encoding="utf-8") == "sentinel-json"
    assert md_path.read_text(encoding="utf-8") == "sentinel-md"
