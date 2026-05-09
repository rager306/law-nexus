from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERIFIER_PATH = ROOT / "scripts/verify-s10-embedding-runtime-proof.py"
USER_MODEL_ID = "deepvk/USER-bge-m3"
GIGA_MODEL_ID = "ai-sage/Giga-Embeddings-instruct"


def load_verifier() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_s10_embedding_runtime_proof", VERIFIER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_log(root: Path, name: str) -> str:
    path = root / ".gsd/milestones/M001/slices/S10/logs" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")
    return path.relative_to(root).as_posix()


def blocked_model(root: Path, model_id: str, dimension: int) -> dict[str, Any]:
    is_giga = model_id == GIGA_MODEL_ID
    return {
        "id": model_id,
        "role": "quality-challenger" if is_giga else "practical-baseline",
        "status": "not-safe-to-run" if is_giga else "blocked-environment",
        "verdict": "not-safe-challenger" if is_giga else "blocked-baseline",
        "vector_dimension": dimension,
        "max_token_limit": 4096 if is_giga else 8192,
        "package_status": "blocked-environment",
        "cache_status": "absent",
        "download_status": "disabled",
        "runtime_status": "not-safe-to-run" if is_giga else "blocked-environment",
        "encode_duration_ms": None,
        "observed_vector_dimension": None,
        "resource_metadata": {"cpu_count": 2, "memory_mib": 4096},
        "retrieval_metrics": None,
        "blocked_root_cause": "safety-gate-no-gpu" if is_giga else "embedding-packages-missing",
        "next_proof_step": "Install optional deps and populate cache.",
        "raw_log_paths": [write_log(root, f"{model_id.replace('/', '__')}.log")],
        "instruction_handling": {
            "query_instruction_applied": is_giga,
            "document_instruction_applied": False,
        },
        "safety_gate": {
            "status": "not-safe-to-run" if is_giga else "confirmed-runtime",
            "reasons": ["no GPU/flash-attn gate"] if is_giga else [],
        },
    }


def proven_user_model(root: Path) -> dict[str, Any]:
    model = blocked_model(root, USER_MODEL_ID, 1024)
    model.update(
        {
            "status": "confirmed-runtime",
            "verdict": "proven-baseline",
            "package_status": "available",
            "cache_status": "available",
            "download_status": "allowed-not-needed",
            "runtime_status": "confirmed-runtime",
            "encode_duration_ms": 123.4,
            "observed_vector_dimension": 1024,
            "retrieval_metrics": {"recall_at_1": 1.0, "mrr": 1.0},
            "blocked_root_cause": None,
            "next_proof_step": "Use S05 EvidenceSpan fixture for broader eval.",
        }
    )
    return model


def vector_proof(root: Path, dimension: int, *, confirmed: bool = False) -> dict[str, Any]:
    return {
        "dimension": dimension,
        "model_id": USER_MODEL_ID if dimension == 1024 else GIGA_MODEL_ID,
        "status": "confirmed-runtime" if confirmed else "blocked-environment",
        "index_created": confirmed,
        "query_executed": confirmed,
        "duration_ms": 55.0 if confirmed else None,
        "blocked_root_cause": None if confirmed else "falkordb-client-runtime-missing",
        "next_proof_step": "Start FalkorDB and install client." if not confirmed else "Expand batch test.",
        "raw_log_paths": [write_log(root, f"vector-{dimension}.log")],
    }


def valid_payload(root: Path) -> dict[str, Any]:
    return {
        "schema_version": "s10-embedding-runtime-proof/v1",
        "generated_at": "2026-05-09T00:00:00Z",
        "policy": {
            "managed_embedding_apis": "excluded",
            "local_open_weight_only": True,
            "downloads": "disabled",
        },
        "environment": {
            "python": "3.13.12",
            "platform": "linux",
            "cpu_count": 2,
            "memory_mib": 4096,
            "package_status": "blocked-environment",
            "cache_status": "absent",
            "raw_log_paths": [write_log(root, "environment.log")],
        },
        "models": [
            blocked_model(root, USER_MODEL_ID, 1024),
            blocked_model(root, GIGA_MODEL_ID, 2048),
        ],
        "vector_proofs": [
            vector_proof(root, 1024),
            vector_proof(root, 2048),
        ],
        "fixture_policy": {
            "source": "synthetic-and-s05-evidence-span-ids",
            "raw_legal_text_logged": False,
            "raw_vectors_logged": False,
            "production_legal_quality_claim": "not-proven",
        },
        "confidence_loop": {
            "question": "Ты на 100% уверен в этой стратегии?",
            "answer": "No. Runtime proof is blocked by environment in this fixture.",
            "holes_found": ["models are blocked"],
            "fixes_or_next_proofs": ["install dependencies"],
            "closed": False,
        },
        "raw_log_paths": [write_log(root, "summary.log")],
    }


def write_payload(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "proof.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def verify(payload: dict[str, Any], tmp_path: Path, mode: Any | None = None) -> Any:
    verifier = load_verifier()
    path = write_payload(tmp_path, payload)
    selected_mode = verifier.VerificationMode.ALLOW_BLOCKED if mode is None else mode
    return verifier.verify_artifact(path, selected_mode)


def test_accepts_terminal_blocked_scaffold(tmp_path: Path) -> None:
    result = verify(valid_payload(tmp_path), tmp_path)

    assert result.ok is True


def test_cli_accepts_terminal_blocked_scaffold(tmp_path: Path) -> None:
    path = write_payload(tmp_path, valid_payload(tmp_path))

    result = subprocess.run(
        [sys.executable, str(VERIFIER_PATH), "--artifact", str(path), "--allow-blocked"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "allow-blocked" in result.stdout


def test_rejects_managed_api_policy(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["policy"]["managed_embedding_apis"] = "allowed"

    result = verify(payload, tmp_path)

    assert result.ok is False
    assert any("managed_embedding_apis" in error for error in result.errors)


def test_rejects_forbidden_credential_literal(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    path = write_payload(tmp_path, payload)
    forbidden = "GIGACHAT" + "_AUTH_DATA"
    path.write_text(path.read_text(encoding="utf-8") + forbidden, encoding="utf-8")
    verifier = load_verifier()

    result = verifier.verify_artifact(path, verifier.VerificationMode.ALLOW_BLOCKED)

    assert result.ok is False
    assert any("forbidden" in error for error in result.errors)


def test_rejects_proven_verdict_without_confirmed_runtime(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["models"][0]["verdict"] = "proven-baseline"

    result = verify(payload, tmp_path)

    assert result.ok is False
    assert any("requires confirmed-runtime" in error for error in result.errors)


def test_rejects_confirmed_runtime_without_metrics_or_dimension(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["models"][0].update(
        {
            "status": "confirmed-runtime",
            "runtime_status": "confirmed-runtime",
            "verdict": "proven-baseline",
            "encode_duration_ms": None,
            "observed_vector_dimension": 768,
            "retrieval_metrics": None,
            "blocked_root_cause": None,
        }
    )

    result = verify(payload, tmp_path)

    assert result.ok is False
    assert any("encode_duration_ms" in error for error in result.errors)
    assert any("observed_vector_dimension" in error for error in result.errors)
    assert any("retrieval_metrics" in error for error in result.errors)


def test_require_user_proof_demands_user_model_and_1024_vector(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    verifier = load_verifier()

    blocked_result = verify(payload, tmp_path, verifier.VerificationMode.REQUIRE_USER_PROOF)

    payload["models"][0] = proven_user_model(tmp_path)
    payload["vector_proofs"][0] = vector_proof(tmp_path, 1024, confirmed=True)
    proven_result = verify(payload, tmp_path, verifier.VerificationMode.REQUIRE_USER_PROOF)

    assert any("USER-bge-m3 confirmed-runtime" in error for error in blocked_result.errors)
    assert any("1024-dim vector proof" in error for error in blocked_result.errors)
    assert proven_result.ok is True


def test_giga_blocked_mode_requires_terminal_safety_gate(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    verifier = load_verifier()
    payload["models"][1]["safety_gate"] = {"status": "unknown", "reasons": []}

    result = verify(payload, tmp_path, verifier.VerificationMode.ALLOW_GIGA_BLOCKED_WITH_GATE)

    assert result.ok is False
    assert any("safety_gate" in error for error in result.errors)


def test_rejects_vector_confirmed_without_index_and_query(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["vector_proofs"][0].update(
        {
            "status": "confirmed-runtime",
            "index_created": False,
            "query_executed": False,
            "blocked_root_cause": None,
        }
    )

    result = verify(payload, tmp_path)

    assert result.ok is False
    assert any("index_created=true" in error for error in result.errors)
    assert any("query_executed=true" in error for error in result.errors)


def test_rejects_raw_legal_text_or_vector_logging_claim(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["fixture_policy"]["raw_legal_text_logged"] = True
    payload["fixture_policy"]["raw_vectors_logged"] = True

    result = verify(payload, tmp_path)

    assert result.ok is False
    assert any("raw_legal_text_logged" in error for error in result.errors)
    assert any("raw_vectors_logged" in error for error in result.errors)


def test_require_final_demands_closed_confidence_loop(tmp_path: Path) -> None:
    payload = valid_payload(tmp_path)
    payload["models"][0] = proven_user_model(tmp_path)
    payload["vector_proofs"][0] = vector_proof(tmp_path, 1024, confirmed=True)
    verifier = load_verifier()

    open_result = verify(deepcopy(payload), tmp_path, verifier.VerificationMode.REQUIRE_FINAL)

    payload["confidence_loop"]["closed"] = True
    closed_result = verify(payload, tmp_path, verifier.VerificationMode.REQUIRE_FINAL)

    assert any("confidence_loop.closed=true" in error for error in open_result.errors)
    assert closed_result.ok is True
