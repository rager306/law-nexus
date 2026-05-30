from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "build/acp/m048-s09/git_lex_capability_results.json"
REPORT_PATH = ROOT / "prd/architecture/acp/M048-S09-GIT-LEX-FUNCTIONAL-FIT-REPORT.md"
DIAGNOSTICS_PATH = ROOT / "prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md"

REQUIRED_SCENARIOS = {
    "source-record-lifecycle": "ACP-S09-C01",
    "blocked-claim": "ACP-S09-C02",
    "projection-boundary": "ACP-S09-C03",
    "recovery-query": "ACP-S09-C04",
    "git-semantics": "ACP-S09-C05",
    "isolation-safety": "ACP-S09-C06",
}

ALLOWED_RESULT_STATES = {"pass", "blocked", "fail", "not_applicable"}
ALLOWED_FAILURE_CATEGORIES = {
    None,
    "ImitativeArtifact",
    "BlockedCapability",
    "UnsupportedGitLexRuntime",
    "UnsafeMutation",
    "InsufficientEvidence",
}

FORBIDDEN_ADOPTION_CLAIMS = [
    "full runtime git-lex adoption is approved",
    "full acp git-lex runtime adoption is approved",
    "git-lex is adopted.",
    "runtime git-lex adoption is approved",
    "adoption readiness is proven",
    "adoption readiness was proven",
    "safe to initialize in the main repository",
]


def load_results() -> dict:
    assert RESULTS_PATH.exists(), f"Missing S09 results JSON: {RESULTS_PATH.relative_to(ROOT)}"
    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def report_text() -> str:
    assert REPORT_PATH.exists(), f"Missing S09 functional-fit report: {REPORT_PATH.relative_to(ROOT)}"
    return REPORT_PATH.read_text(encoding="utf-8")


def diagnostics_text() -> str:
    assert DIAGNOSTICS_PATH.exists(), f"Missing S09 runtime diagnostics: {DIAGNOSTICS_PATH.relative_to(ROOT)}"
    return DIAGNOSTICS_PATH.read_text(encoding="utf-8")


def rows_by_scenario(results: dict) -> dict[str, dict]:
    rows = results.get("results")
    assert isinstance(rows, list) and rows, "S09 results must contain per-capability rows"
    return {row["scenario_id"]: row for row in rows}


def test_results_cover_required_capabilities_once_with_allowed_statuses() -> None:
    results = load_results()
    rows = rows_by_scenario(results)

    assert set(rows) == set(REQUIRED_SCENARIOS)
    assert results["scenario_ids"] == list(REQUIRED_SCENARIOS)

    for scenario, capability_id in REQUIRED_SCENARIOS.items():
        row = rows[scenario]
        assert row["capability_id"] == capability_id
        assert row["result_state"] in ALLOWED_RESULT_STATES
        assert row.get("failure_category") in ALLOWED_FAILURE_CATEGORIES
        assert row["evidence_anchor"], f"Missing evidence anchor for {scenario}"
        assert row["source_projection_authority_status"], f"Missing authority status for {scenario}"
        assert row["workspace_path_class"] == "temporary_disposable_workspace"
        assert row["rollback_status"] == "deleted_by_TemporaryDirectory"
        assert row["allowed_next_action"], f"Missing allowed next action for {scenario}"


def test_blocked_runtime_diagnostics_are_preserved_without_treating_block_as_pass() -> None:
    results = load_results()
    rows = rows_by_scenario(results)
    runtime = results["runtime"]

    assert results["status"] == "blocked"
    assert runtime["runtime_status"] == "blocked"
    assert runtime["blocker_class"] == "UnsupportedGitLexRuntime"
    assert runtime["tool_versions"]["git_lex_runtime"] == "unavailable"
    assert "no clone/install/download/durable build/git-lex-init" in runtime["safe_acquisition_policy"]

    commands = {" ".join(command["command"]): command for command in runtime["commands"]}
    assert "git lex --help" in commands
    assert "git-lex --help" in commands
    assert commands["git lex --help"]["exit_code"] != 0
    assert commands["git-lex --help"]["exit_code"] is None

    git_semantics = rows["git-semantics"]
    assert git_semantics["result_state"] == "blocked"
    assert git_semantics["failure_category"] == "UnsupportedGitLexRuntime"
    assert "no record-aware git-lex value was proven" in git_semantics["value_beyond_acp_native_git"]

    blocked_claim = rows["blocked-claim"]
    assert blocked_claim["failure_category"] == "UnsupportedGitLexRuntime"
    assert "not a pass and not adoption evidence" in blocked_claim["notes"]


def test_no_main_repo_lex_mutation_guard_is_machine_readable_and_reported() -> None:
    results = load_results()
    report = report_text()
    diagnostics = diagnostics_text()

    guard = results["main_repo_mutation_guard"]
    runtime_guard = results["runtime"]["mutation_guard"]

    for mutation_guard in [guard, runtime_guard]:
        assert mutation_guard["checked"] is True
        assert mutation_guard["main_lex_before"] is False
        assert mutation_guard["main_lex_after"] is False
        assert mutation_guard["safe"] is True

    isolation = rows_by_scenario(results)["isolation-safety"]
    assert isolation["result_state"] == "pass"
    assert isolation["diagnostics"]["mutation_guard"]["safe"] is True
    assert isolation["evidence_anchor"] == "prd/architecture/acp/M048-S09-GIT-LEX-RUNTIME-DIAGNOSTICS.md"

    assert "Main-repo mutation guard safe: `True`" in report
    assert "Main checkout .lex absence checked before and after" in report
    assert "`.lex` absent before proof | `True`" in diagnostics
    assert "`.lex` absent after proof | `True`" in diagnostics
    assert "Guard safe | `True`" in diagnostics


def test_reports_do_not_overclaim_adoption_or_requirement_validation() -> None:
    combined = "\n".join(
        [
            json.dumps(load_results(), ensure_ascii=False),
            report_text(),
            diagnostics_text(),
        ]
    ).casefold()

    for claim in FORBIDDEN_ADOPTION_CLAIMS:
        assert claim not in combined, f"Forbidden adoption overclaim present: {claim}"

    for requirement_id in ["r035", "r037", "r038"]:
        forbidden_requirement_claims = [
            f"{requirement_id} is validated",
            f"{requirement_id} has been validated",
            f"validates {requirement_id}",
            f"validated {requirement_id}",
        ]
        for claim in forbidden_requirement_claims:
            assert claim not in combined, f"Forbidden requirement overclaim present: {claim}"

    assert "do not adopt runtime git-lex from s09 evidence" in combined
    assert "not adoption evidence" in combined
    assert "not_applicable_no_git_lex_projection" in combined


def test_no_full_adoption_claim_when_any_critical_capability_is_not_passing() -> None:
    results = load_results()
    rows = rows_by_scenario(results)
    critical_states = {scenario: row["result_state"] for scenario, row in rows.items()}

    assert critical_states["git-semantics"] == "blocked"
    assert any(state != "pass" for state in critical_states.values())

    conclusion = results["adoption_conclusion"].casefold()
    assert conclusion.startswith("do not adopt runtime git-lex from s09 evidence")
    assert "keep acp-native records plus ordinary git" in conclusion
    assert "explicit acquisition/runtime proof" in conclusion

    value_assessment = report_text().casefold()
    assert "s09 did not prove runtime git-lex adoption" in value_assessment
    assert "ordinary git provides branch, diff, history, and conflict mechanics" in value_assessment
