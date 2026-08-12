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
ACTIVE_HOOK_IDS = {
    "ruff-check-python",
    "ruff-format-python",
    "cargo-fmt-rust",
    "cargo-check-rust",
    "cargo-clippy-rust",
    "crate-dependency-allowlist",
    "architecture-claim-conformance",
}
CI_PROCESS_SUITE = {
    "tests/test_harness_status_tracer.py",
    "tests/test_harness_subprocess_failure_modes.py",
    "tests/test_harness_no_forbidden_imports.py",
    "tests/test_harness_governor.py",
    "tests/test_harness_cli_entrypoints.py",
    "tests/test_harness_preflight.py",
    "tests/test_documentation_navigation.py",
    "tests/test_repository_quality_gate.py",
    "tests/test_verify_crate_dependency_allowlist.py",
    "tests/test_verify_port_contract_coverage.py",
    "tests/test_verify_hostile_negative_suite_coverage.py",
    "tests/test_verify_multi_adapter_port_coverage.py",
    "tests/test_verify_live_adapter_readiness.py",
    "tests/test_architecture_views.py",
    "tests/test_architecture_analysis_views.py",
    "tests/test_architecture_remediation_matrix.py",
    "tests/test_architecture_track_split.py",
    "tests/test_architecture_closure_roadmap.py",
    "tests/test_architecture_registry_schema.py",
    "tests/test_verify_adr_conformance.py",
    "tests/test_verify_repository_pre_commit_hook.py",
}
CI_INVENTORY_SCRIPTS = {
    "scripts/verify-port-contract-coverage.py",
    "scripts/verify-hostile-negative-suite-coverage.py",
    "scripts/verify-multi-adapter-port-coverage.py",
    "scripts/verify-live-adapter-readiness.py",
}
RUST_PATHS = r"^(Cargo\.(toml|lock)|crates/.*\.(rs|toml))$"


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
    assert set(by_id) == ACTIVE_HOOK_IDS
    commands = "\n".join(hook["entry"] for hook in hooks)
    assert "git-lex" not in commands
    assert ".lex" not in commands
    assert "lint-imports" not in commands
    assert "python-onion-dependencies" not in by_id
    assert by_id["cargo-fmt-rust"]["entry"] == "cargo fmt --all -- --check"
    assert by_id["cargo-check-rust"]["entry"] == "cargo check --workspace --offline"
    assert (
        by_id["cargo-clippy-rust"]["entry"]
        == "cargo clippy --workspace --offline --all-targets -- -D warnings"
    )
    rust_paths = by_id["cargo-fmt-rust"]["files"]
    assert rust_paths == by_id["cargo-check-rust"]["files"]
    assert rust_paths == by_id["cargo-clippy-rust"]["files"]
    assert rust_paths == RUST_PATHS
    assert "always_run" not in by_id["cargo-fmt-rust"]
    assert "always_run" not in by_id["cargo-check-rust"]
    assert "always_run" not in by_id["cargo-clippy-rust"]
    assert by_id["architecture-claim-conformance"]["always_run"] is True
    assert by_id["ruff-check-python"].get("exclude") == "^python_archive/"
    assert by_id["ruff-format-python"].get("exclude") == "^python_archive/"


def test_ci_workflow_replaces_old_compliance_name_and_keeps_required_checks() -> None:
    assert WORKFLOW.exists()
    assert not OLD_WORKFLOW.exists()
    text = WORKFLOW.read_text(encoding="utf-8")
    for command in (
        "uv run ruff check src/",
        "uv run ruff format --check src/",
        "uv run basedpyright src/",
        "uv run ty check src/",
        "uv run pyrefly check src/",
        "uv run python scripts/verify-adr-conformance.py",
        "uv run python scripts/verify-crate-dependency-allowlist.py",
        "cargo fetch --locked",
        "cargo fmt --all -- --check",
        "cargo check --workspace --offline",
        "cargo clippy --workspace --offline --all-targets -- -D warnings",
        "cargo build --workspace --offline",
        "cargo test --workspace --offline",
        *sorted(CI_PROCESS_SUITE),
        *sorted(CI_INVENTORY_SCRIPTS),
    ):
        assert command in text
    assert "uv run lint-imports" not in text
    assert "verify-m112-adr-sync.py" not in text
    assert "python-onion-dependencies" not in text
    assert text.index("cargo fetch --locked") < text.index("cargo check --workspace --offline")
    assert "rust-harness-quality:" in text
    assert "dtolnay/rust-toolchain@stable" in text
    assert "clippy" in text
    assert "Process inventory scripts (report-only)" in text


def test_verifier_default_paths_do_not_depend_on_archived_semantic_state() -> None:
    module = load_verifier()
    relative = [path.relative_to(ROOT).as_posix() for path in module.default_claim_paths()]
    assert relative
    assert not any(path.startswith(".lex/") for path in relative)
    assert not any(path.startswith("prd/architecture/acp/") for path in relative)
    assert not any(path.startswith("python_archive/") for path in relative)
    assert all("git-lex-kit" not in path for path in relative)


def test_gate_inventory_matches_active_paths_and_boundary() -> None:
    payload = json.loads(INVENTORY.read_text(encoding="utf-8"))
    assert payload["status"] == "active"
    assert payload["local_config"] == ".pre-commit-config.yaml"
    assert payload["ci_workflow"] == ".github/workflows/repository-quality.yml"
    assert payload["product_logic_in_python_harness_allowed"] is False
    assert len(payload["checks"]) == 7
    by_id = {check["id"]: check for check in payload["checks"]}
    assert set(by_id) == ACTIVE_HOOK_IDS
    assert by_id["cargo-fmt-rust"]["command"] == "cargo fmt --all -- --check"
    assert by_id["cargo-check-rust"]["command"] == "cargo check --workspace --offline"
    assert (
        by_id["cargo-clippy-rust"]["command"]
        == "cargo clippy --workspace --offline --all-targets -- -D warnings"
    )
    assert "python-onion-dependencies" not in by_id
    assert all("lint-imports" not in check["command"] for check in payload["checks"])
    assert set(payload["ci_process_suite"]) == CI_PROCESS_SUITE
    assert set(payload["ci_inventory_scripts"]) == CI_INVENTORY_SCRIPTS
    future = payload["future_additions"]
    assert "cargo clippy" not in future
    assert "cargo test pre-commit gating" in future
    assert any("optional inventory --strict" in item for item in future)
    assert not any(
        "optional port-contract-coverage --strict CI policy decision (InMemory inventory already 22/22"
        in item
        for item in future
    )
    assert "cargo test --workspace --offline" in WORKFLOW.read_text(encoding="utf-8")
