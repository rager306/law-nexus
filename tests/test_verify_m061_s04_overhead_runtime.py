from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Sequence

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/verify-m061-s04-overlay-runtime.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m061_s04_overlay_runtime", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_create_workspace_uses_tmp_s061_prefix() -> None:
    harness = load_harness()

    workspace, disposable = harness.create_workspace()

    try:
        assert disposable is True
        assert str(workspace).startswith("/tmp/s061-s04-")
        assert workspace.exists()
    finally:
        if workspace.exists():
            import shutil

            shutil.rmtree(workspace)


def test_create_workspace_rejects_non_tmp_path(tmp_path: Path) -> None:
    harness = load_harness()

    with pytest.raises(ValueError, match="/tmp/s061-s04"):
        harness.create_workspace(tmp_path / "not-disposable")


def test_residue_check_reports_main_state(tmp_path: Path) -> None:
    harness = load_harness()

    clean = harness.check_main_residue(tmp_path)
    assert clean == {".lex": False, "Squad": False, "Raw": False, ".artifacts": False}

    (tmp_path / ".lex").mkdir()
    assert harness.check_main_residue(tmp_path)[".lex"] is True
    with pytest.raises(RuntimeError, match="main checkout residue"):
        harness.assert_no_main_residue(tmp_path)


def test_run_checked_command_uses_stub_and_preserves_residue(tmp_path: Path) -> None:
    harness = load_harness()
    commands: list[list[str]] = []

    def fake_runner(
        command: Sequence[str], cwd: Path, env: dict[str, str]
    ) -> harness.CommandResult:
        commands.append(list(command))
        assert str(harness.GIT_LEX_BIN_DIR) in env["PATH"]
        return harness.CommandResult(list(command), str(cwd), 0, "[]", "")

    result, pre, post = harness.run_checked_command(
        ["git-lex", "list", "--json"], tmp_path, runner=fake_runner, root=tmp_path
    )

    assert commands == [["git-lex", "list", "--json"]]
    assert result.exit_code == 0
    assert pre == {".lex": False, "Squad": False, "Raw": False, ".artifacts": False}
    assert post == pre


def test_jsonl_record_shape(tmp_path: Path) -> None:
    harness = load_harness()
    result = harness.CommandResult(["git-lex", "validate"], str(tmp_path), 0, "all pass", "")
    record = harness.make_record(
        phase="positive",
        step="validate",
        result=result,
        workspace=tmp_path,
        classification="pass",
        pre_residue={".lex": False, "Squad": False, "Raw": False, ".artifacts": False},
        post_residue={".lex": False, "Squad": False, "Raw": False, ".artifacts": False},
        details={"row_count": 1},
    )
    output = tmp_path / "diagnostics.jsonl"

    harness.write_jsonl([record], output)
    parsed = json.loads(output.read_text(encoding="utf-8"))

    assert parsed["phase"] == "positive"
    assert parsed["step"] == "validate"
    assert parsed["command"] == "git-lex validate"
    assert parsed["exit_code"] == 0
    assert parsed["workspace"] == str(tmp_path)
    assert parsed["classification"] == "pass"
    assert parsed["pre_residue"] == parsed["post_residue"]
    assert parsed["details"] == {"row_count": 1}


def test_runtime_inputs_are_generated_style_and_negative_ready(tmp_path: Path) -> None:
    harness = load_harness()

    written = harness.write_runtime_inputs(tmp_path)

    relative_paths = {path.relative_to(tmp_path).as_posix() for path in written}
    assert "ACP/ProofGate/example-profile-proof-gate.md" in relative_paths
    assert "LawNexus/LegalDocument/example-legal-document.md" in relative_paths
    assert "shapes/composed-profile.ttl" in relative_paths

    shape = (tmp_path / "shapes/composed-profile.ttl").read_text(encoding="utf-8")
    assert "@prefix acp:" in shape
    assert "@prefix lawNexus:" in shape
    assert "acp:ValidationClaimShape a sh:NodeShape ;\n  sh:targetClass acp:ValidationClaim ;" in shape
    assert "sh:path acp:verdict" in shape
    assert "sh:path acp:sourceArtifact" in shape
    assert "sh:path lawNexus:observedAt" in shape
    assert "sh:path lawNexus:synthetic" in shape
    assert "sh:path lawNexus:proofStatus" in shape


def test_negative_fixture_replacements_are_localized(tmp_path: Path) -> None:
    harness = load_harness()
    case = harness.NEGATIVE_CASES[0]

    harness.install_negative_fixture(tmp_path, case)

    negative = tmp_path / "ACP/ValidationClaim/negative-invalid-verdict.md"
    assert negative.exists()
    text = negative.read_text(encoding="utf-8")
    assert "acp.ValidationClaim.verdict: bogus" in text
    assert "acp.ValidationClaim.nonAuthoritative: true" in text
