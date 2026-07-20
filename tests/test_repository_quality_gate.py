from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRE_COMMIT = ROOT / ".pre-commit-config.yaml"
WORKFLOW = ROOT / ".github/workflows/repository-quality.yml"
OLD_WORKFLOW = ROOT / ".github/workflows/compliance-gate.yml"
VERIFIER = ROOT / "scripts/verify-adr-conformance.py"
INVENTORY = ROOT / "prd/migration/decommission/repository-quality-gate.json"
FORBIDDEN = ("git-lex", "git lex", "d098", "acp checkpoint", ".lex/")


def load_verifier():
    spec = importlib.util.spec_from_file_location("neutral_adr_verifier", VERIFIER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_active_gate_files_have_neutral_terminology() -> None:
    for path in (PRE_COMMIT, WORKFLOW, VERIFIER):
        text = path.read_text(encoding="utf-8").lower()
        for marker in FORBIDDEN:
            assert marker not in text, f"{path}: active gate contains {marker!r}"


def test_pre_commit_commands_are_expected_and_non_mutating() -> None:
    payload = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    hooks = payload["repos"][0]["hooks"]
    by_id = {hook["id"]: hook for hook in hooks}
    assert set(by_id) == {
        "ruff-check-python",
        "ruff-format-python",
        "python-onion-dependencies",
        "architecture-claim-conformance",
    }
    commands = "\n".join(hook["entry"] for hook in hooks)
    assert "git-lex" not in commands
    assert ".lex" not in commands
    assert by_id["python-onion-dependencies"]["always_run"] is True
    assert by_id["architecture-claim-conformance"]["always_run"] is True


def test_ci_workflow_replaces_old_compliance_name_and_keeps_required_checks() -> None:
    assert WORKFLOW.exists()
    assert not OLD_WORKFLOW.exists()
    text = WORKFLOW.read_text(encoding="utf-8")
    for command in (
        "uv run ruff check src/",
        "uv run ruff format --check src/",
        "uv run lint-imports",
        "uv run basedpyright src/",
        "uv run ty check src/",
        "uv run pyrefly check src/",
        "uv run python scripts/verify-adr-conformance.py",
    ):
        assert command in text


def test_verifier_default_paths_do_not_depend_on_archived_semantic_state() -> None:
    module = load_verifier()
    relative = [path.relative_to(ROOT).as_posix() for path in module.default_claim_paths()]
    assert relative
    assert not any(path.startswith(".lex/") for path in relative)
    assert not any(path.startswith("prd/architecture/acp/") for path in relative)
    assert all("git-lex-kit" not in path for path in relative)


def test_gate_inventory_matches_active_paths_and_boundary() -> None:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert payload["status"] == "active"
    assert payload["local_config"] == ".pre-commit-config.yaml"
    assert payload["ci_workflow"] == ".github/workflows/repository-quality.yml"
    assert payload["product_logic_in_python_harness_allowed"] is False
    assert len(payload["checks"]) == 4
