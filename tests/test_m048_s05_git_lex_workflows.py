from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/run-m048-s05-git-lex-workflows.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m048_s05_git_lex_workflows", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_harness_main(module: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, dict[str, Any]]:
    monkeypatch.setattr(module.sys, "argv", [str(HARNESS_PATH), *args])
    exit_code = module.main()
    captured = capsys.readouterr()
    return exit_code, json.loads(captured.out)


def workflow_by_id(result: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    workflows = {workflow["id"]: workflow for workflow in result["workflows"]}
    assert workflow_id in workflows, f"Missing workflow {workflow_id!r}; got {sorted(workflows)}"
    return workflows[workflow_id]


def test_current_blocked_runtime_state_exits_successfully_and_preserves_json_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", tmp_path / ".lex")

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["harness"] == "m048-s05-git-lex-workflows"
    assert result["status"] in {"blocked", "pass"}
    assert result["fatal_failures"] == []
    assert result["workflow_ids"] == module.WORKFLOW_IDS
    assert set(result["workflow_statuses"]) == set(module.WORKFLOW_IDS)
    assert result["mutation_guard"] == {
        "checked": True,
        "main_lex_before": False,
        "main_lex_after": False,
        "safe": True,
    }
    assert result["main_repo_lex_exists"] is False


def test_absent_git_lex_blocks_runtime_adoption_but_s04_mechanics_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", tmp_path / ".lex")

    def missing_probe(command: list[str], cwd: Path) -> dict[str, Any]:  # noqa: ARG001
        return {
            "command": command,
            "exit_code": None,
            "stdout_preview": "",
            "stderr_preview": "missing executable",
            "duration_ms": 1,
            "timed_out": False,
        }

    s04 = module.load_s04_harness()
    monkeypatch.setattr(s04, "run_probe", missing_probe)
    monkeypatch.setattr(module, "load_s04_harness", lambda: s04)

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["status"] == "blocked"
    assert result["workflow_statuses"]["runtime_acquisition_and_adoption"] == "blocked"
    assert result["workflow_statuses"]["typed_source_record_validation"] == "pass"
    assert result["workflow_statuses"]["extraction_projection_query_recovery"] == "pass"
    assert result["workflow_statuses"]["lifecycle_proof_gate_profile_boundary"] == "pass"
    runtime = workflow_by_id(result, "runtime_acquisition_and_adoption")
    assert runtime["blocked_or_deferred_reason"] == (
        "git-lex executable unavailable; runtime acquisition and adoption are deferred while deterministic ACP mechanics remain inspectable"
    )
    assert result["adoption_recommendation"] == "defer_runtime_adoption_keep_deterministic_acp_mechanics_only"
    assert "claim_full_acp_runtime_adoption_from_fixture_only_evidence" in result["blocked_actions"]


def test_no_full_adoption_recommendation_even_when_runtime_probe_succeeds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", tmp_path / ".lex")

    def successful_probe(command: list[str], cwd: Path) -> dict[str, Any]:  # noqa: ARG001
        return {
            "command": command,
            "exit_code": 0,
            "stdout_preview": "usage: git lex",
            "stderr_preview": "",
            "duration_ms": 1,
            "timed_out": False,
        }

    s04 = module.load_s04_harness()
    monkeypatch.setattr(s04, "run_probe", successful_probe)
    monkeypatch.setattr(module, "load_s04_harness", lambda: s04)

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["status"] == "pass"
    assert result["workflow_statuses"]["runtime_acquisition_and_adoption"] == "pass"
    assert result["adoption_recommendation"] == "partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption"
    assert result["adoption_recommendation"] != "full_adoption"
    assert result["adoption_recommendation"].startswith("partial_adoption_")
    assert "does_not_claim_full_acp_git_lex_adoption" in result["non_claims"]


def test_main_repo_dot_lex_presence_fails_closed_without_creating_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    lex_path = tmp_path / ".lex"
    lex_path.mkdir()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", lex_path)

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 1
    assert result["status"] == "fail"
    assert result["main_repo_lex_exists"] is True
    assert "main repository .lex exists before S05 workflow diagnostics" in result["fatal_failures"]
    assert "main repository .lex exists after S05 workflow diagnostics" in result["fatal_failures"]
    assert result["workflow_statuses"]["main_repo_mutation_guard"] == "fail"


def test_requirement_boundary_keeps_r035_r037_r038_unvalidated_and_non_claimed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", tmp_path / ".lex")

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["requirement_boundary"] == {
        "R035": "not_validated_by_s05_git_lex_workflow_diagnostics",
        "R037": "not_validated_by_s05_git_lex_workflow_diagnostics",
        "R038": "not_validated_by_s05_git_lex_workflow_diagnostics",
    }
    assert "does_not_validate_R035" in result["non_claims"]
    assert "does_not_validate_R037" in result["non_claims"]
    assert "does_not_validate_R038" in result["non_claims"]
    assert "validate_R035_R037_R038_from_git_lex_projection_diagnostics" in result["blocked_actions"]


def test_source_projection_boundary_blocks_derived_projection_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = load_harness()
    monkeypatch.setattr(module, "MAIN_REPO_LEX_DIR", tmp_path / ".lex")

    exit_code, result = run_harness_main(module, monkeypatch, capsys, "--check")

    assert exit_code == 0
    assert result["source_projection_boundary"] == {
        "source_truth": "tracked S04 fixture source records and evidence anchors",
        "derived_projection": "temporary deterministic non-authoritative diagnostic projection",
        "projection_may_validate_requirements": False,
        "projection_may_override_source_records": False,
    }
    assert "does_not_promote_derived_projections_to_source_truth" in result["non_claims"]
    assert "treat_derived_projection_as_source_truth" in result["blocked_actions"]


def test_malformed_contract_validation_rejects_missing_workflow_and_requirement_overclaim() -> None:
    module = load_harness()
    contract = {
        "workflow_statuses": {"runtime_acquisition_and_adoption": "blocked"},
        "source_projection_boundary": {
            "projection_may_validate_requirements": False,
            "projection_may_override_source_records": False,
        },
        "requirement_boundary": {
            "R035": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R037": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R038": "not_validated_by_s05_git_lex_workflow_diagnostics",
        },
        "non_claims": ["does_not_claim_full_acp_git_lex_adoption"],
        "blocked_actions": ["treat_derived_projection_as_source_truth"],
        "main_repo_lex_exists": False,
        "fatal_failures": [],
    }

    with pytest.raises(module.ContractError, match="missing workflow diagnostics"):
        module.validate_contract(contract)

    contract["workflow_statuses"] = {workflow_id: "pass" for workflow_id in module.WORKFLOW_IDS}
    contract["requirement_boundary"]["R035"] = "validated"
    with pytest.raises(module.ContractError, match="R035 must remain not validated"):
        module.validate_contract(contract)


def test_projection_overclaim_and_source_override_are_malformed_contracts() -> None:
    module = load_harness()
    contract = {
        "workflow_statuses": {workflow_id: "pass" for workflow_id in module.WORKFLOW_IDS},
        "source_projection_boundary": {
            "projection_may_validate_requirements": True,
            "projection_may_override_source_records": False,
        },
        "requirement_boundary": {
            "R035": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R037": "not_validated_by_s05_git_lex_workflow_diagnostics",
            "R038": "not_validated_by_s05_git_lex_workflow_diagnostics",
        },
        "non_claims": ["does_not_claim_full_acp_git_lex_adoption"],
        "blocked_actions": ["treat_derived_projection_as_source_truth"],
        "main_repo_lex_exists": False,
        "fatal_failures": [],
    }

    with pytest.raises(module.ContractError, match="derived projection must not validate requirements"):
        module.validate_contract(contract)

    contract["source_projection_boundary"]["projection_may_validate_requirements"] = False
    contract["source_projection_boundary"]["projection_may_override_source_records"] = True
    with pytest.raises(module.ContractError, match="derived projection must not override source records"):
        module.validate_contract(contract)
