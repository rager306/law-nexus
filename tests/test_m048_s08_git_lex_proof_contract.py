from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd/architecture/acp/M048-S08-GIT-LEX-PROOF-CONTRACT.md"

REQUIRED_SECTIONS = [
    "Status",
    "Inputs and Authority",
    "Scenario Matrix",
    "Workspace Constraints",
    "No-Main-Repo `.lex` Guard",
    "Accepted Diagnostic Artifacts",
    "Blocked-Runtime Semantics",
    "Required S09 Proof Steps",
    "Pass, Block, and Fail Rules",
    "Failure Modes",
    "Load Profile",
    "Negative Tests",
    "Observability Impact",
]

REQUIRED_SCENARIOS = [
    "source-record-lifecycle",
    "blocked-claim",
    "projection-boundary",
    "recovery-query",
    "git-semantics",
    "isolation-safety",
]

FAILURE_CATEGORIES = [
    "ImitativeArtifact",
    "BlockedCapability",
    "UnsupportedGitLexRuntime",
    "UnsafeMutation",
    "InsufficientEvidence",
]

RESULT_STATES = ["pass", "blocked", "fail", "not_applicable"]

FORBIDDEN_OVERCLAIMS = [
    "full runtime git-lex adoption is approved",
    "full acp git-lex runtime adoption is approved",
    "git-lex is adopted.",
    "runtime git-lex adoption is approved",
    "r035 is validated",
    "r037 is validated",
    "r038 is validated",
    "validates r035",
    "validates r037",
    "validates r038",
]


def contract_text() -> str:
    assert CONTRACT_PATH.exists(), f"Missing proof contract: {CONTRACT_PATH.relative_to(ROOT)}"
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required proof contract section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def table_rows(table_text: str) -> list[list[str]]:
    rows = []
    for line in table_text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
    return rows


def scenario_row(scenarios: str, scenario: str) -> list[str]:
    for row in table_rows(scenarios):
        if len(row) >= 5 and row[0] == f"`{scenario}`":
            return row
    raise AssertionError(f"Missing scenario row: {scenario}")


def test_contract_exists_and_has_required_sections() -> None:
    text = contract_text()

    assert text.startswith("# M048 S08 git-lex Proof Contract")
    for heading in REQUIRED_SECTIONS:
        body = section(text, heading)
        assert body.strip(), f"Section must not be empty: {heading}"

    authority = section(text, "Inputs and Authority")
    assert "M048-S08-GIT-LEX-CAPABILITY-MATRIX.md" in authority
    assert "No artifact is authoritative by shape alone." in authority
    assert "source category + lifecycle state + evidence anchor + proof gate or accepted decision" in authority


def test_scenario_matrix_covers_required_s09_proof_scenarios() -> None:
    text = contract_text()
    scenarios = section(text, "Scenario Matrix")

    expected_header = (
        "| Scenario | Priority | Required capability focus | Minimum passing evidence | "
        "Blocked/fail interpretation |"
    )
    assert expected_header in scenarios

    for scenario in REQUIRED_SCENARIOS:
        row = scenario_row(scenarios, scenario)
        assert row[1], f"Scenario priority must be populated: {scenario}"
        assert row[2], f"Required capability focus must be populated: {scenario}"
        assert row[3], f"Minimum passing evidence must be populated: {scenario}"
        assert row[4], f"Blocked/fail interpretation must be populated: {scenario}"
        assert any(category in row[4] for category in FAILURE_CATEGORIES) or scenario == "git-semantics", (
            f"Blocked/fail interpretation should name a failure category: {scenario}"
        )

    assert "Create a representative ACP source record" in scenarios
    assert "proof fail or runtime probe unavailable" in scenarios
    assert "recover canonical source records as authoritative" in scenarios
    assert "without relying on polished prose" in scenarios
    assert "ordinary git branch/diff/history/conflict/rebase" in scenarios
    assert "outside the main `law-nexus` checkout" in scenarios

    for category in FAILURE_CATEGORIES:
        assert category in text, f"Missing failure category in proof contract: {category}"


def test_pass_block_fail_rules_define_allowed_dispositions_without_binary_adoption() -> None:
    rules = section(contract_text(), "Pass, Block, and Fail Rules")

    for state in RESULT_STATES:
        assert f"`{state}`" in rules, f"Missing result state: {state}"

    assert "Capability may inform a later explicit adoption/implementation decision" in rules
    assert "Keep runtime adoption blocked/deferred" in rules
    assert "Fail closed" in rules
    assert "Do not cite as coverage" in rules
    assert "A single `fail` in `isolation-safety` or `projection-boundary` blocks runtime adoption" in rules
    assert "`yes`" not in rules.casefold()
    assert "`no`" not in rules.casefold()


def test_workspace_constraints_and_no_main_lex_guard_are_explicit() -> None:
    text = contract_text()
    workspace = section(text, "Workspace Constraints")
    guard = section(text, "No-Main-Repo `.lex` Guard")
    steps = section(text, "Required S09 Proof Steps")

    assert "Do not run `git lex init`" in workspace
    assert "create `.lex`" in workspace
    assert "isolated workspace" in workspace
    assert "No hidden acquisition" in workspace
    assert "Do not clone, install, download, durably build, or cache git-lex" in workspace
    assert "Rollback is mandatory" in workspace
    assert "`R035`/`R037`/`R038`" in workspace

    assert "`test ! -e .lex` before proof" in guard
    assert "blind `git lex init`" in guard
    assert "rollback/delete path" in guard
    assert "`test ! -e .lex` after proof" in guard
    assert "UnsafeMutation" in guard

    assert "Clean up isolated workspace" in steps
    assert "re-check main `.lex` absence" in steps


def test_diagnostic_artifacts_and_blocked_runtime_semantics_are_bounded() -> None:
    text = contract_text()
    diagnostics = section(text, "Accepted Diagnostic Artifacts")
    blocked = section(text, "Blocked-Runtime Semantics")
    observability = section(text, "Observability Impact")

    for artifact in [
        "tracked Markdown proof report",
        "tracked JSON or fixture projection",
        "pytest output or proof command result",
        "typed health finding",
        "transition history record",
    ]:
        assert artifact in diagnostics

    for rejected in [
        "polished prose without anchors",
        "manually edited derived projections",
        "`.gsd/exec/*` paths by themselves",
        "`.lex/*` state in the main checkout",
        "raw embeddings/vectors",
        "secrets",
    ]:
        assert rejected in diagnostics

    assert "not a test pass and not an adoption claim" in blocked
    assert "must not trigger unplanned clone/install/download/build behavior" in blocked
    assert "a later successful runtime probe is not enough for full adoption" in blocked
    assert "blocked" in blocked.casefold()

    for field in [
        "scenario id",
        "capability id or name",
        "result state",
        "failure category",
        "command/artifact anchor",
        "source/projection authority status",
        "workspace path class",
        "rollback status",
        "allowed next action",
    ]:
        assert field in observability


def test_no_main_repository_mutation_constraints_are_executable_contract_terms() -> None:
    text = contract_text()
    workspace = section(text, "Workspace Constraints")
    guard = section(text, "No-Main-Repo `.lex` Guard")
    steps = section(text, "Required S09 Proof Steps")
    failure_modes = section(text, "Failure Modes")

    for required in [
        "Main checkout is read-only for git-lex runtime state",
        "Do not run `git lex init`",
        "create `.lex`",
        "isolated workspace",
        "No hidden acquisition",
        "Rollback is mandatory",
    ]:
        assert required in workspace

    for required in [
        "`test ! -e .lex` before proof in main checkout",
        "No command equivalent to blind `git lex init` in main checkout",
        "Runtime/projection state created only in isolated workspace",
        "Isolated workspace rollback/delete path recorded",
        "`test ! -e .lex` after proof in main checkout",
    ]:
        assert required in guard

    assert "assert main `.lex` absence" in steps
    assert "Clean up isolated workspace and re-check main `.lex` absence" in steps
    assert "main checkout gains `.lex`" in failure_modes
    assert "fail closed" in failure_modes


def test_contract_preserves_runtime_adoption_and_requirement_boundaries() -> None:
    text = contract_text()
    lowered = text.casefold()

    for claim in FORBIDDEN_OVERCLAIMS:
        assert claim not in lowered, f"Forbidden overclaim present: {claim}"

    blocked = section(text, "Blocked-Runtime Semantics")
    assert "deterministic ACP-native checks may still pass" in blocked
    assert "ACP mechanics only" in blocked

    workspace = section(text, "Workspace Constraints")
    assert "Russian legal evidence" in workspace
    assert "FalkorDB behavior" in workspace
    assert "reusable ACP core proof" in workspace


def test_failure_modes_load_profile_and_negative_tests_are_populated() -> None:
    text = contract_text()

    failure_modes = section(text, "Failure Modes")
    for dependency in [
        "Tracked input matrix and prior ACP artifacts",
        "Filesystem and workspace isolation",
        "Subprocess runtime probes",
        "Git operations",
        "Source/projection validation",
        "Diagnostic persistence",
    ]:
        assert dependency in failure_modes

    assert "Record `UnsupportedGitLexRuntime`" in failure_modes
    assert "do not auto-install" in failure_modes
    assert "Network acquisition is deliberately excluded" in failure_modes

    load_profile = section(text, "Load Profile")
    assert "no production runtime load dimension" in load_profile
    assert "At 10x the expected scenario count" in load_profile
    assert "No rate limiting, pagination, caching" in load_profile
    assert "future S09 executable proof must define its own load profile" in load_profile

    negative_tests = section(text, "Negative Tests")
    assert "tests/test_m048_s08_git_lex_proof_contract.py" in negative_tests
    assert "rejects missing scenario rows" in negative_tests
    assert "no-main-repo `.lex` guard" in negative_tests
    assert "runtime adoption overclaims" in negative_tests
    assert "blocked-runtime semantics" in negative_tests
