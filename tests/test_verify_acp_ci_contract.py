from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts/verify-acp-ci-contract.py"


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_acp_ci_contract", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def diagnostic_ids(diagnostics: list[object]) -> set[str]:
    return {getattr(diagnostic, "diagnostic_id") for diagnostic in diagnostics}


def write_m058_fixture(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "M058-S03-CORRECTED-VALIDATION-SYNTHESIS.md"
    path.write_text(text, encoding="utf-8")
    return path


def valid_m058_text() -> str:
    return "\n".join(
        [
            "validate/query representation mismatch",
            "This artifact does not validate R035, R037, or R038.",
            "M058 root cause closed for the ACP-kit generated-shape gate.",
            "reject enforcement is proven for the 2 contracted true-negative probes.",
            "Stage 2 (D084, future milestone) is the install + single-repo adoption handoff.",
        ]
    )


def test_current_m058_synthesis_passes() -> None:
    verifier = load_verifier()

    diagnostics = verifier.check_m058_synthesis()

    assert diagnostics == []


def test_detects_missing_m058_guard_term(tmp_path: Path) -> None:
    verifier = load_verifier()
    path = write_m058_fixture(
        tmp_path,
        "validate/query representation mismatch\n"
        "Do not use `git-lex validate` as a hard ACP proof gate yet\n",
    )

    diagnostics = verifier.check_m058_synthesis(path)

    assert "missing_m058_guard_term" in diagnostic_ids(diagnostics)


def test_detects_forbidden_m058_overclaim(tmp_path: Path) -> None:
    verifier = load_verifier()
    path = write_m058_fixture(
        tmp_path,
        valid_m058_text() + "\ngit-lex validate is broken\n",
    )

    diagnostics = verifier.check_m058_synthesis(path)

    assert "forbidden_m058_overclaim" in diagnostic_ids(diagnostics)


def test_allows_explicitly_rejected_m058_overclaim_wording(tmp_path: Path) -> None:
    verifier = load_verifier()
    path = write_m058_fixture(
        tmp_path,
        valid_m058_text() + "\nAvoid this wording:\n`git-lex validate` is broken.\n",
    )

    diagnostics = verifier.check_m058_synthesis(path)

    assert diagnostics == []


def test_detects_main_state_residue(tmp_path: Path) -> None:
    verifier = load_verifier()
    (tmp_path / ".lex").write_text("unsafe main state", encoding="utf-8")

    diagnostics = verifier.check_main_state_residue(tmp_path)

    assert "main_state_residue" in diagnostic_ids(diagnostics)


def test_run_contract_can_be_unit_tested_without_subprocesses(monkeypatch) -> None:
    verifier = load_verifier()
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, cwd: Path = verifier.ROOT):
        commands.append(command)
        return None

    monkeypatch.setattr(verifier, "_run", fake_run)

    diagnostics = verifier.run_contract(run_tests=True, run_diff_check=True, check_residue=False)

    assert diagnostics == []
    assert ["uv", "run", "python", "scripts/verify-m049-binding.py"] in commands
    assert ["uv", "run", "python", "scripts/verify-m056-acp-kit.py"] in commands
    assert any(command[:3] == ["uv", "run", "pytest"] for command in commands)
    assert ["git", "diff", "--check"] in commands
