from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m049-binding.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m049_binding", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_artifact(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "artifact.md"
    path.write_text(text, encoding="utf-8")
    return path


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def test_current_m049_binding_artifacts_pass() -> None:
    verifier = load_verifier()

    diagnostics = verifier.verify(verifier.DEFAULT_ARTIFACTS, check_residue=True)

    assert diagnostics == []


def test_lists_required_diagnostic_ids() -> None:
    verifier = load_verifier()

    assert set(verifier.DIAGNOSTIC_IDS) == {
        "authority_inversion",
        "unsafe_anchor",
        "missing_profile_proof_gate",
        "missing_requirement_proof_gate",
        "profile_core_drift",
        "forbidden_git_lex_promotion",
        "forbidden_profile_validation",
        "main_state_residue",
        "registry_currency_overclaim",
        "proof_gate_placeholder_used_as_proof",
    }


def test_detects_authority_inversion(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "JSONL registry rows are source truth and validation proof.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "authority_inversion" in diagnostic_ids(diagnostics)


def test_detects_unsafe_anchor(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "Accepted proof anchor: /root/local/debug.txt\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "unsafe_anchor" in diagnostic_ids(diagnostics)


def test_detects_missing_proof_gate(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "The profile claim is validated without a proof gate.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "missing_profile_proof_gate" in diagnostic_ids(diagnostics)


def test_detects_profile_core_drift(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "ACP core owns Russian legal correctness.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "profile_core_drift" in diagnostic_ids(diagnostics)


def test_detects_forbidden_git_lex_promotion(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "git-lex is the ACP authority and production backend.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "forbidden_git_lex_promotion" in diagnostic_ids(diagnostics)


def test_detects_forbidden_profile_validation(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "R035 is validated by ACP projection evidence.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "forbidden_profile_validation" in diagnostic_ids(diagnostics)


def test_detects_registry_currency_overclaim(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "architecture_items.jsonl is current and fresh.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "registry_currency_overclaim" in diagnostic_ids(diagnostics)


def test_detects_placeholder_proof_misuse(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(tmp_path, "A placeholder proof gate proves profile behavior exists.\n")

    diagnostics = verifier.check_artifact(artifact)

    assert "proof_gate_placeholder_used_as_proof" in diagnostic_ids(diagnostics)


def test_detects_main_state_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    (tmp_path / ".lex").write_text("unsafe main state", encoding="utf-8")

    diagnostics = verifier.check_main_state_residue(tmp_path)

    assert "main_state_residue" in diagnostic_ids(diagnostics)


def test_negative_guardrail_context_is_allowed(tmp_path: Path) -> None:
    verifier = load_verifier()
    artifact = write_artifact(
        tmp_path,
        "Do not validate R035 from ACP/git-lex/projection evidence alone.\n",
    )

    diagnostics = verifier.check_artifact(artifact)

    assert diagnostics == []
