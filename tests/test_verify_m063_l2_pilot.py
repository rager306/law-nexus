from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/verify-m063-l2-pilot.py"


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("verify_m063_l2_pilot", HARNESS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_workspace_provision_creates_disposable_dir() -> None:
    harness = load_harness()

    workspace, disposable = harness.create_workspace()

    try:
        assert disposable is True
        assert workspace.exists()
        assert workspace.parent == Path("/tmp")
        assert workspace.name.startswith("m063-l2-")
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)


def test_residue_check_passes_when_main_clean(tmp_path: Path) -> None:
    harness = load_harness()
    root = tmp_path / "repo"
    root.mkdir()

    residue = harness.assert_no_main_residue(root)

    assert residue == {".lex": False, "Squad": False, "Raw": False, ".artifacts": False}


def test_residue_check_fails_on_main_state(tmp_path: Path) -> None:
    harness = load_harness()
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".lex").mkdir()

    with pytest.raises(harness.ResidueViolation) as exc_info:
        harness.assert_no_main_residue(root)

    assert exc_info.value.residue[".lex"] is True


def test_jsonl_record_shape() -> None:
    harness = load_harness()

    record = harness.make_record(
        phase="setup",
        step="shape-check",
        command="internal",
        exit_code=0,
        classification="pass",
        workspace="/tmp/m063-l2-shape",
    )

    assert harness.REQUIRED_RECORD_FIELDS.issubset(record.keys())
    assert harness.record_shape_valid(record)
    assert record["milestone_id"] == "M063-qp7ial"


def test_classification_vocabulary_includes_required() -> None:
    harness = load_harness()

    assert {
        "pass",
        "pass-with-shape-violation",
        "fail-closed",
        "blocked",
        "residue-violation",
        "pilot-aborted",
    }.issubset(harness.CLASSIFICATION_VOCABULARY)


def test_state_location_enforcement(tmp_path: Path) -> None:
    harness = load_harness()
    root = tmp_path / "repo"
    root.mkdir()
    workspace = Path("/tmp") / "m063-l2-state-location-test"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir()

    try:
        layers = harness.enforce_state_locations(workspace, root=root)

        assert layers["disposable"] == str(workspace.resolve())
        assert layers["persistent"].endswith(
            "prd/architecture/acp/runtime/M063-qp7ial"
        )
        assert layers["forbidden_main"] == str(root.resolve())
        assert not (root / ".lex").exists()
        assert not (root / "Squad").exists()
        assert not (root / "Raw").exists()
        assert not (root / ".artifacts").exists()
    finally:
        if workspace.exists():
            shutil.rmtree(workspace)


@pytest.mark.parametrize(
    "mode",
    [
        "state-corruption",
        "network-failure",
        "hook-failure",
        "validation-overflow",
        "workspace-retention-overrun",
        "main-repo-residue",
        "acp-native-only-overclaim",
        "user-abort",
    ],
)
def test_8_failure_modes_classified(mode: str, tmp_path: Path) -> None:
    harness = load_harness()

    context = harness.sample_context_for_failure_mode(mode, tmp_path)

    try:
        assert harness.detect_failure_mode(mode, context)
        assert mode in harness.RECOVERY_POLICIES
        assert harness.RECOVERY_POLICIES[mode].classification in harness.CLASSIFICATION_VOCABULARY
    finally:
        if mode == "workspace-retention-overrun" and context.workspace and context.workspace.exists():
            shutil.rmtree(context.workspace)


def test_milestone_id_default_is_M063_qp7ial() -> None:
    harness = load_harness()

    args = harness.parse_args([])

    assert harness.DEFAULT_MILESTONE_ID == "M063-qp7ial"
    assert args.milestone_id == "M063-qp7ial"
