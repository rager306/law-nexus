from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd/architecture/acp/M048-S06-FINAL-INTEGRATION-VERIFICATION.md"

REQUIRED_SECTIONS = [
    "## Verdict",
    "## Scope",
    "## Command Matrix",
    "## Evidence Consumed",
    "## Accepted Interpretation",
    "## Source and Projection Boundary",
    "## Mutation Guard",
    "## Requirement Boundary",
    "## Allowed Actions",
    "## Blocked Actions",
    "## Non-Claims",
    "## Future Law-Nexus Binding Handoff",
    "## Failure Modes",
    "## Load Profile",
    "## Negative Tests",
    "## Observability Impact",
    "## Closeout Criteria",
]

CANONICAL_COMMANDS = [
    "uv run python scripts/verify-architecture-graph.py",
    "uv run python scripts/verify-acp-records.py",
    "uv run python scripts/export-acp-recovery-view.py --check",
    "uv run python scripts/export-acp-architecture-projection.py --check",
    "uv run python scripts/export-architecture-rdf-projection.py --check",
    "uv run python scripts/export-architecture-rdf-projection.py --diff",
    "uv run python scripts/run-m048-s04-git-lex-proof.py --check",
    "uv run python scripts/run-m048-s05-git-lex-workflows.py --check",
]

FORBIDDEN_BOUNDARY_DRIFT_CLAIMS = [
    "projection is source truth",
    "projections are source truth",
    "projection may validate requirements | `true`",
    "projection may override source records | `true`",
    "rdf projection is authoritative",
    "jsonl projection is authoritative",
    "full runtime git-lex adoption is accepted",
    "full acp git-lex runtime adoption is approved",
    "git-lex is adopted.",
    "it is safe to initialize in the main repository",
    "r035 is validated",
    "r037 is validated",
    "r038 is validated",
    "validates r035",
    "validates r037",
    "validates r038",
]


def report_text() -> str:
    assert REPORT_PATH.exists(), f"Missing S06 report: {REPORT_PATH.relative_to(ROOT)}"
    return REPORT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required report section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_report_exists_and_has_required_reader_oriented_sections() -> None:
    text = report_text()

    assert text.startswith("# M048 S06 Final Integration Verification")
    for heading in REQUIRED_SECTIONS:
        assert heading in text

    assert "S06 is a final integration and closeout report" in section(text, "Scope")
    assert "future law-nexus architecture binding handoff" in section(text, "Scope")
    assert "this report is the main human-readable s06 diagnostic surface" in section(
        text, "Observability Impact"
    ).casefold()


def test_report_references_every_canonical_s06_command() -> None:
    text = report_text()
    command_matrix = section(text, "Command Matrix")

    for command in CANONICAL_COMMANDS:
        assert f"`{command}`" in command_matrix

    assert "`test ! -e .lex`" in command_matrix
    assert "architecture verifier reports `status=ok`" in command_matrix
    assert "ACP records verify" in command_matrix
    assert "recovery view is current" in command_matrix
    assert "ACP architecture projection is current" in command_matrix
    assert "RDF projection is current and non-authoritative" in command_matrix
    assert "no unexpected RDF projection drift" in command_matrix
    assert "`fatal_failures=[]`" in command_matrix
    assert "mutation guard safe; main `.lex` absent" in command_matrix


def test_report_preserves_projection_non_authority_and_rejects_source_promotion() -> None:
    text = report_text()
    boundary = section(text, "Source and Projection Boundary")
    blocked = section(text, "Blocked Actions")
    non_claims = section(text, "Non-Claims")
    lowered = text.casefold()

    assert "Derived outputs are useful inspection surfaces only" in boundary
    assert "These derived projections are **non-authoritative**" in boundary
    assert "override source records" in boundary
    assert "validate requirements by themselves" in boundary
    assert "become accepted architecture doctrine by freshness alone" in boundary
    assert "the remedy is to repair the source/projection pipeline" in boundary
    assert "treat RDF, JSONL, recovery, project-state, dashboard, or git-lex diagnostics as source truth" in blocked
    assert "RDF, SHACL, SPARQL, Turtle, JSONL, dashboards, recovery outputs, project-state summaries, or git-lex projections are authoritative source truth" in non_claims

    for claim in FORBIDDEN_BOUNDARY_DRIFT_CLAIMS:
        assert claim not in lowered


def test_report_keeps_r035_r037_r038_not_validated_by_s06_evidence() -> None:
    text = report_text()
    requirement_boundary = section(text, "Requirement Boundary")
    blocked = section(text, "Blocked Actions")
    non_claims = section(text, "Non-Claims")
    handoff = section(text, "Future Law-Nexus Binding Handoff")

    for requirement_id in ["R035", "R037", "R038"]:
        assert f"| `{requirement_id}` | not validated by S06 ACP/git-lex/projection evidence |" in requirement_boundary
        assert requirement_id in blocked
        assert requirement_id in non_claims
        assert requirement_id in handoff

    assert "S06 does not prove ontology correctness" in requirement_boundary
    assert "FalkorDB ingestion" in requirement_boundary
    assert "generated-Cypher safety" in requirement_boundary
    assert "production readiness" in requirement_boundary


def test_report_blocks_main_repo_git_lex_init_and_dot_lex_mutation() -> None:
    text = report_text()
    mutation_guard = section(text, "Mutation Guard")
    blocked = section(text, "Blocked Actions")
    non_claims = section(text, "Non-Claims")

    assert "do not run `git lex init`" in mutation_guard
    assert "do not create `.lex`" in mutation_guard
    assert "do not mutate existing repository state through git-lex" in mutation_guard
    assert "Main `.lex` before verification | absent" in mutation_guard
    assert "Main `.lex` after verification | absent" in mutation_guard
    assert "Runtime git-lex adoption | deferred" in mutation_guard
    assert "A pre-existing or newly created main-repository `.lex` path is a closeout failure" in mutation_guard
    assert "claim `.lex` is safe in the main repository" in blocked
    assert "main-repository `.lex` state exists or should exist" in non_claims


def test_report_documents_deferred_runtime_adoption_recommendation() -> None:
    text = report_text()
    verdict = section(text, "Verdict")
    accepted = section(text, "Accepted Interpretation")
    evidence = section(text, "Evidence Consumed")
    handoff = section(text, "Future Law-Nexus Binding Handoff")

    assert "not as full runtime git-lex adoption" in verdict
    assert "runtime git-lex adoption deferred" in verdict
    assert "Runtime git-lex adoption" in accepted
    assert "deferred until a future proof-gated milestone" in accepted
    assert "defer runtime git-lex adoption and keep deterministic ACP mechanics only" in evidence
    assert "defer_runtime_adoption_keep_deterministic_acp_mechanics_only" in text
    assert "Keep runtime git-lex adoption behind a new proof gate" in handoff


def test_report_includes_future_handoff_failure_modes_load_profile_negative_tests_and_observability() -> None:
    text = report_text()

    handoff = section(text, "Future Law-Nexus Binding Handoff")
    assert "Treat M048 as a foundation for ACP governance mechanics" in handoff
    assert "Bind architecture only from authoritative source records" in handoff
    assert "Keep all projections non-authoritative" in handoff
    assert "executable provenance, acquisition policy, build/install behavior" in handoff

    failure_modes = section(text, "Failure Modes")
    assert "Local filesystem for tracked reports and scripts" in failure_modes
    assert "Architecture/ACP verifier subprocesses" in failure_modes
    assert "RDF/JSONL/recovery/projection exporters" in failure_modes
    assert "S04 isolated proof harness" in failure_modes
    assert "S05 workflow harness" in failure_modes
    assert "Local git-lex probes" in failure_modes
    assert "Main repository mutation boundary" in failure_modes
    assert "Human-readable report drift" in failure_modes
    assert "Network acquisition is not a dependency of S06" in failure_modes

    load_profile = section(text, "Load Profile")
    assert "S06 has no production runtime load dimension." in load_profile
    assert "At 10x the current diagnostic input size" in load_profile
    assert "local subprocess time and filesystem parsing" in load_profile
    assert "not runtime pool sizing, rate limiting, pagination, caching" in load_profile

    negative_tests = section(text, "Negative Tests")
    assert "tests/test_m048_s04_git_lex_isolated_proof.py" in negative_tests
    assert "tests/test_m048_s05_git_lex_workflows.py" in negative_tests
    assert "tests/test_m048_s05_workflow_report.py" in negative_tests
    assert "tests/test_m048_s05_integration_decision.py" in negative_tests
    assert "permits `git lex init`" in negative_tests
    assert "claims full runtime adoption" in negative_tests
    assert "validates `R035`/`R037`/`R038`" in negative_tests

    observability = section(text, "Observability Impact")
    assert "human-readable S06 diagnostic surface" in observability
    assert "where to inspect verifier/projection status" in observability
    assert "how to interpret S04/S05 blocked-versus-failed runtime status" in observability
    assert "which projections are non-authoritative" in observability


def test_closeout_criteria_lock_authority_mutation_requirement_and_deferred_boundaries() -> None:
    text = report_text()
    criteria = section(text, "Closeout Criteria")

    assert "canonical architecture/ACP/projection/RDF/S04/S05 checks pass" in criteria
    assert "the main repository has no `.lex` state" in criteria
    assert "source/projection non-authority is explicit" in criteria
    assert "runtime git-lex adoption remains deferred" in criteria
    assert "`R035`, `R037`, and `R038` remain not validated by S06" in criteria
    assert "reusable ACP core and law-nexus profile constraints remain separate" in criteria
