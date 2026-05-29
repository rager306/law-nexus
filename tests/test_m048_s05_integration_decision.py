from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "prd/architecture/acp/M048-S05-GIT-LEX-INTEGRATION-DECISION.md"

REQUIRED_SECTIONS = [
    "## Status",
    "## Decision",
    "## What is adopted",
    "## Evidence considered",
    "## Accepted interpretation",
    "## Allowed next actions",
    "## Blocked actions",
    "## Non-claims",
    "## Source and projection boundary",
    "## Revisit trigger",
    "## Closeout verdict",
    "## Failure Modes",
    "## Load Profile",
    "## Negative Tests",
    "## Observability Impact",
]


def decision_text() -> str:
    assert DECISION_PATH.exists(), f"Missing decision document: {DECISION_PATH.relative_to(ROOT)}"
    return DECISION_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required decision section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_decision_exists_and_has_required_sections() -> None:
    text = decision_text()

    assert text.startswith("# M048 S05 git-lex Integration Decision")
    for heading in REQUIRED_SECTIONS:
        assert heading in text
    assert "prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md" in text
    assert "prd/architecture/acp/M048-S05-GIT-LEX-WORKFLOW-REPORT.md" in text
    assert "scripts/run-m048-s05-git-lex-workflows.py" in text
    assert "prd/architecture/acp/M045-RDF-PROJECTION-DECISION.md" in text
    assert "prd/architecture/acp/M046-RDF-PROJECTION-HARDENING-DECISION.md" in text


def test_decision_explicitly_classifies_full_partial_and_deferred_adoption() -> None:
    text = decision_text()
    decision = section(text, "Decision")
    closeout = section(text, "Closeout verdict")

    assert "Full adoption" in decision
    assert "rejected for S05" in decision
    assert "Partial adoption" in decision
    assert "deterministic ACP mechanics" in decision
    assert "Deferred adoption" in decision
    assert "runtime git-lex acquisition" in decision
    assert "defer_runtime_adoption_keep_deterministic_acp_mechanics_only" in decision
    assert "partial_adoption_requires_separate_runtime_git_lex_proof_before_full_adoption" in decision
    assert "no main-repository git-lex initialization" in closeout


def test_decision_rejects_full_runtime_adoption_overclaims() -> None:
    text = decision_text()
    lowered = text.casefold()

    forbidden_claims = [
        "full adoption: accepted",
        "full adoption is accepted",
        "full acp git-lex runtime adoption is approved",
        "git-lex is adopted.",
        "it is safe to initialize in the main repository",
    ]
    for claim in forbidden_claims:
        assert claim not in lowered

    assert "full adoption" in lowered
    assert "rejected for s05" in lowered
    assert "does not permit full acp git-lex runtime adoption" in lowered
    assert "runtime adoption stays `blocked` or `deferred`" in lowered


def test_decision_blocks_main_repo_git_lex_init_and_dot_lex_mutation() -> None:
    text = decision_text()
    blocked = section(text, "Blocked actions")
    revisit = section(text, "Revisit trigger")

    assert "running `git lex init` in the main `law-nexus` repository" in blocked
    assert "creating or mutating main-repository `.lex` state" in blocked
    assert "Main repository filesystem state" in section(text, "Failure Modes")
    assert "where `.lex` state may be created" in revisit
    assert "keep main-repository git-lex initialization blocked" in revisit


def test_decision_preserves_source_projection_boundary_and_non_authority() -> None:
    text = decision_text()
    boundary = section(text, "Source and projection boundary")

    assert "Source truth | Tracked S04 fixture source records and evidence anchors." in boundary
    assert "Derived projection | Temporary deterministic non-authoritative diagnostic projection." in boundary
    assert "Projection may validate requirements | `false`" in boundary
    assert "Projection may override source records | `false`" in boundary
    assert "Proof-gate definition equals proof satisfaction | `false`" in boundary
    assert "not source truth" in boundary
    assert "not product runtime proof" in boundary
    assert "not legal truth" in boundary


def test_decision_keeps_r035_r037_r038_unvalidated() -> None:
    text = decision_text()
    lowered = text.casefold()

    for requirement_id in ["R035", "R037", "R038"]:
        assert f"`{requirement_id}` validation" in text
        assert requirement_id in section(text, "Blocked actions")
        assert f"{requirement_id.lower()} is validated" not in lowered
        assert f"{requirement_id.lower()} has been validated" not in lowered
        assert f"validates {requirement_id.lower()}" not in lowered
        assert f"validated {requirement_id.lower()}" not in lowered

    assert "They do not prove" in section(text, "Accepted interpretation")
    assert "requirement validation" in section(text, "Accepted interpretation")


def test_decision_keeps_reusable_acp_core_separate_from_law_nexus_profile() -> None:
    text = decision_text()
    adopted = section(text, "What is adopted")
    blocked = section(text, "Blocked actions")
    non_claims = section(text, "Non-claims")
    revisit = section(text, "Revisit trigger")

    assert "reusable ACP core / law-nexus profile separation" in adopted
    assert "Russian legal evidence" in adopted
    assert "FalkorDB" in adopted
    assert "profile constraints must not be promoted into reusable ACP core" in adopted
    assert "moving law-nexus profile constraints into reusable ACP core" in blocked
    assert "reusable ACP core includes law-nexus-specific" in non_claims
    assert "separation between reusable ACP core and law-nexus profile constraints" in revisit


def test_decision_includes_failure_modes_load_profile_negative_tests_and_observability() -> None:
    text = decision_text()

    failure_modes = section(text, "Failure Modes")
    assert "Local git-lex executable probes" in failure_modes
    assert "S04 proof report and harness evidence" in failure_modes
    assert "S05 workflow JSON contract" in failure_modes
    assert "Human-readable decision drift" in failure_modes
    assert "Network acquisition is deliberately not a dependency of S05" in failure_modes

    load_profile = section(text, "Load Profile")
    assert "S05 has no production runtime load dimension." in load_profile
    assert "At 10x the expected diagnostic size" in load_profile
    assert "No pool sizing, rate limiting, pagination, caching" in load_profile

    negative_tests = section(text, "Negative Tests")
    assert "tests/test_m048_s05_integration_decision.py" in negative_tests
    assert "rejects full runtime adoption overclaims" in negative_tests
    assert "source/projection boundary enforcement" in negative_tests
    assert "requirement-boundary enforcement" in negative_tests

    observability = section(text, "Observability Impact")
    assert "stable human-readable adoption boundary" in observability
    assert "S05 JSON workflow diagnostics" in observability
