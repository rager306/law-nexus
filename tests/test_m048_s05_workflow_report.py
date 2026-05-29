from __future__ import annotations

from pathlib import Path

REPORT_PATH = Path(__file__).resolve().parents[1] / "prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md"

REQUIRED_SECTIONS = [
    "## Verdict",
    "## Scope",
    "## Workflow Matrix",
    "## Evidence Consumed",
    "## Accepted Interpretation",
    "## Allowed Actions",
    "## Blocked Actions",
    "## Non-Claims",
    "## Source and Projection Boundary",
    "## Mutation Guard",
    "## Requirement Boundary",
    "## S06 Handoff",
    "## Failure Modes",
    "## Load Profile",
    "## Negative Tests",
    "## Observability Impact",
]


def report_text() -> str:
    return REPORT_PATH.read_text(encoding="utf-8")


def test_report_exists_and_has_required_reader_oriented_sections() -> None:
    text = report_text()

    assert text.startswith("# M048 S05 git-lex Workflow Report")
    for section in REQUIRED_SECTIONS:
        assert section in text
    assert "uv run python scripts/run-m048-s05-git-lex-workflows.py --check" in text
    assert "prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md" in text
    assert "prd/architecture/acp/M041-INTEGRATION-DECISION.md" in text
    assert "prd/architecture/acp/M043-CANONICAL-INTEGRATION-DECISION.md" in text


def test_report_bounds_runtime_adoption_claims() -> None:
    text = report_text()

    assert "deferred runtime adoption with safe deterministic ACP mechanics" in text
    assert "runtime git-lex acquisition and adoption are **blocked/deferred**" in text
    assert "Neither recommendation is full ACP git-lex runtime adoption." in text
    assert "defer_runtime_adoption_keep_deterministic_acp_mechanics_only" in text
    assert "partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption" in text
    assert "full ACP git-lex adoption" in text
    assert "no existing `git lex` subcommand or `git-lex` executable" in text


def test_report_preserves_deterministic_acp_mechanics_as_usable_but_bounded() -> None:
    text = report_text()

    assert "typed source-record validation" in text
    assert "extraction/projection/query recovery" in text
    assert "lifecycle/proof-gate/profile-boundary diagnostics" in text
    assert "deterministic ACP mechanics remain usable" in text
    assert "not enough to claim runtime git-lex adoption" in text


def test_report_blocks_main_repo_dot_lex_mutation() -> None:
    text = report_text()

    assert "running `git lex init` in the main `law-nexus` repository" in text
    assert "creating or mutating main-repository `.lex` state" in text
    assert "Main `.lex` before harness | absent" in text
    assert "Main `.lex` after harness | absent" in text
    assert "If main `.lex` exists before or after the run, the workflow must fail closed." in text


def test_report_keeps_projection_non_authoritative_and_source_bounded() -> None:
    text = report_text()

    assert "Source truth | Tracked S04 fixture source records and evidence anchors." in text
    assert "Derived projection | Temporary deterministic non-authoritative diagnostic projection." in text
    assert "Projection may validate requirements | `false`" in text
    assert "Projection may override source records | `false`" in text
    assert "treating a derived projection as source truth" in text
    assert "derived projections can be promoted to source truth" in text


def test_report_keeps_r035_r037_r038_unvalidated() -> None:
    text = report_text()

    for requirement_id in ["R035", "R037", "R038"]:
        assert f"| `{requirement_id}` | `not_validated_by_s05_git_lex_workflow_diagnostics` |" in text
        assert f"requirement validation for `{requirement_id}`" in text
    assert "S05 is workflow diagnostics for ACP git-lex integration safety" in text
    assert "not evidence for parser completeness" in text


def test_report_includes_failure_modes_load_profile_and_negative_test_evidence() -> None:
    text = report_text()

    assert "Local git-lex executable probes" in text
    assert "S04 harness dynamic import" in text
    assert "Main repository filesystem guard" in text
    assert "Report drift" in text
    assert "S05 has no production runtime load profile." in text
    assert "At 10x the expected diagnostic input size" in text
    assert "test_absent_git_lex_blocks_runtime_adoption_but_s04_mechanics_pass" in text
    assert "test_no_full_adoption_recommendation_even_when_runtime_probe_succeeds" in text
    assert "test_main_repo_dot_lex_presence_fails_closed_without_creating_state" in text
    assert "test_requirement_boundary_keeps_r035_r037_r038_unvalidated_and_non_claimed" in text
    assert "test_source_projection_boundary_blocks_derived_projection_promotion" in text


def test_report_s06_handoff_requires_future_runtime_proof_gate() -> None:
    text = report_text()

    assert "Treat runtime git-lex adoption as blocked/deferred" in text
    assert "Preserve the main-repo `.lex` mutation guard as a hard fail-closed condition." in text
    assert "Keep `R035`, `R037`, and `R038` out of scope for S05 evidence." in text
    assert "require a new proof gate" in text
    assert "runtime executable availability, acquisition policy, repository mutation policy, rollback, and source/projection authority" in text
