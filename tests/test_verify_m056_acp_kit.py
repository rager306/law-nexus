from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-m056-acp-kit.py"
KIT_ROOT = ROOT / "git-lex-kit-acp"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_m056_acp_kit", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def copy_kit(tmp_path: Path) -> Path:
    target = tmp_path / "git-lex-kit-acp"
    shutil.copytree(KIT_ROOT, target)
    return target


def test_current_acp_kit_scaffold_passes() -> None:
    verifier = load_verifier()

    diagnostics = verifier.verify(verifier.DEFAULT_KIT_ROOT, check_residue=True)

    assert diagnostics == []


def test_lists_expected_diagnostic_ids() -> None:
    verifier = load_verifier()

    assert set(verifier.DIAGNOSTIC_IDS) == {
        "missing_scaffold_file",
        "invalid_kit_config",
        "forbidden_kit_config",
        "missing_ontology_term",
        "missing_guidance_term",
        "missing_example_guardrail",
        "forbidden_kit_path",
        "unsafe_anchor",
        "source_truth_overclaim",
        "runtime_adoption_overclaim",
        "forbidden_profile_validation",
        "main_state_residue",
    }


def test_detects_missing_scaffold_file(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    (kit_root / "content/AGENTS.md").unlink()

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "missing_scaffold_file" in diagnostic_ids(diagnostics)


def test_detects_invalid_kit_config(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    kit_yml = kit_root / "kit.yml"
    kit_yml.write_text("name: acp\nfolder base: ACP\nfolder ontology: acp.ttl\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "invalid_kit_config" in diagnostic_ids(diagnostics)


def test_detects_forbidden_kit_config(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    kit_yml = kit_root / "kit.yml"
    kit_yml.write_text(kit_yml.read_text(encoding="utf-8") + "\nadaptive: true\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "forbidden_kit_config" in diagnostic_ids(diagnostics)


def test_detects_missing_ontology_term(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    ontology = kit_root / "ontology/acp/acp.ttl"
    ontology.write_text(ontology.read_text(encoding="utf-8").replace("acp:RuntimeAdapter", "acp:RuntimeBoundary"), encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "missing_ontology_term" in diagnostic_ids(diagnostics)


def test_detects_missing_guidance_term(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text("# AGENTS.md\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "missing_guidance_term" in diagnostic_ids(diagnostics)


def test_detects_missing_example_guardrail(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    example = kit_root / "content/ACP/Decision/example-decision.md"
    example.write_text("# Example without guardrails\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "missing_example_guardrail" in diagnostic_ids(diagnostics)


def test_detects_forbidden_kit_path(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    forbidden = kit_root / "content/Raw"
    forbidden.mkdir(parents=True)

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "forbidden_kit_path" in diagnostic_ids(diagnostics)


def test_detects_unsafe_anchor(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text(guidance.read_text(encoding="utf-8") + "\nAccepted proof anchor: /root/local/debug.txt\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "unsafe_anchor" in diagnostic_ids(diagnostics)


def test_detects_source_truth_overclaim(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text(guidance.read_text(encoding="utf-8") + "\nACP-kit is the ACP source truth.\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "source_truth_overclaim" in diagnostic_ids(diagnostics)


def test_detects_runtime_adoption_overclaim(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text(guidance.read_text(encoding="utf-8") + "\nACP-kit approves runtime adoption and production use.\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "runtime_adoption_overclaim" in diagnostic_ids(diagnostics)


def test_detects_forbidden_profile_validation(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text(guidance.read_text(encoding="utf-8") + "\nR035 is validated by ACP-kit projection shape.\n", encoding="utf-8")

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert "forbidden_profile_validation" in diagnostic_ids(diagnostics)


def test_detects_main_state_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    (tmp_path / ".lex").write_text("unsafe main state", encoding="utf-8")

    diagnostics = verifier.check_main_state_residue(tmp_path)

    assert "main_state_residue" in diagnostic_ids(diagnostics)


def test_negative_guardrail_context_is_allowed(tmp_path: Path) -> None:
    verifier = load_verifier()
    kit_root = copy_kit(tmp_path)
    guidance = kit_root / "content/AGENTS.md"
    guidance.write_text(
        guidance.read_text(encoding="utf-8")
        + "\nDo not validate R035 from ACP-kit or projection evidence alone.\n",
        encoding="utf-8",
    )

    diagnostics = verifier.verify(kit_root, check_residue=False)

    assert diagnostics == []
