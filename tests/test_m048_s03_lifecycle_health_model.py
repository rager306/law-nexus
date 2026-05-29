from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "prd/architecture/acp/M048-S03-LIFECYCLE-HEALTH-MODEL.md"


RECORD_FAMILIES = [
    "ArchitecturePromptRecord",
    "ArchitectureProposal",
    "DecisionCandidate",
    "ArchitectureDecision",
    "ProofGate",
    "ArchitectureHealthFinding",
    "DerivedProjectionReference",
    "ProfileConstraint",
    "BlockedAction",
]

CORE_HEALTH_CATEGORIES = [
    "stale_summary",
    "sparse_evidence",
    "blocked_adoption",
    "unsafe_anchor",
    "derived_authority_overclaim",
    "profile_boundary_risk",
]

REQUIREMENT_IDS = ["R035", "R037", "R038"]


def read_model() -> str:
    assert MODEL.exists(), f"Missing lifecycle health model: {MODEL.relative_to(ROOT)}"
    text = MODEL.read_text(encoding="utf-8")
    assert text.strip(), f"Lifecycle health model is empty: {MODEL.relative_to(ROOT)}"
    return text


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold())


def assert_terms(text: str, terms: list[str]) -> None:
    missing = [term for term in terms if term.casefold() not in text.casefold()]
    assert not missing, f"Missing required lifecycle-health terms: {missing}"


def assert_patterns(text: str, patterns: list[str]) -> None:
    missing = [pattern for pattern in patterns if not re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)]
    assert not missing, f"Missing required lifecycle-health patterns: {missing}"


def section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match, f"Missing section: {heading}"
    return match.group(1)


def table_subsection(text: str, heading: str) -> str:
    pattern = rf"^### {re.escape(heading)}\s*$([\s\S]*?)(?=^### |^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    assert match, f"Missing lifecycle table subsection: {heading}"
    return match.group(1)


def test_model_declares_required_record_families_and_lifecycle_tables() -> None:
    text = read_model()
    scope = section(text, "Scope")
    lifecycle = section(text, "Lifecycle State Tables")

    assert_terms(scope, RECORD_FAMILIES)
    assert_terms(lifecycle, RECORD_FAMILIES)

    for family in RECORD_FAMILIES:
        family_table = table_subsection(lifecycle, family)
        assert_terms(family_table, ["| State | Meaning | Allowed next states | Blocking conditions |"])
        assert_patterns(family_table, [rf"Core rule:.*{re.escape(family)[:18]}|Core rule:"])

    assert_patterns(
        lifecycle,
        [
            r"DecisionCandidate[\s\S]*requires_authority[\s\S]*requires_proof[\s\S]*accepted",
            r"ArchitectureDecision[\s\S]*accepted[\s\S]*active[\s\S]*requires_proof[\s\S]*verified",
            r"ProofGate[\s\S]*defined[\s\S]*pending_evidence[\s\S]*running[\s\S]*satisfied",
            r"ArchitectureHealthFinding[\s\S]*open[\s\S]*triaged[\s\S]*blocked[\s\S]*resolved",
            r"BlockedAction[\s\S]*active[\s\S]*unblock_pending[\s\S]*unblocked",
        ],
    )


def test_model_preserves_health_categories_actions_and_s01_seed_mapping() -> None:
    text = read_model()
    categories = section(text, "Health Finding Categories")
    mapping = section(text, "S01 Health Seed Mapping")

    assert_terms(categories, CORE_HEALTH_CATEGORIES)
    assert_terms(categories, ["Default severity", "Typical surfaces", "Blocks"])
    assert_terms(mapping, ["Blocked actions", "Allowed next actions"])

    expected_findings = [f"HF-M048-S01-{number:03d}" for number in range(1, 14)]
    assert_terms(mapping, expected_findings)

    assert_patterns(
        mapping,
        [
            r"HF-M048-S01-011[\s\S]*critical[\s\S]*blocked_adoption[\s\S]*git-lex[\s\S]*\.lex",
            r"HF-M048-S01-012[\s\S]*critical[\s\S]*derived_authority_overclaim[\s\S]*R035[\s\S]*R037[\s\S]*R038",
            r"HF-M048-S01-013[\s\S]*high[\s\S]*unsafe_anchor[\s\S]*\.gsd/exec[\s\S]*absolute paths",
        ],
    )


def test_authority_proof_and_non_authority_boundaries_are_explicit() -> None:
    text = read_model()
    authority = section(text, "Authority and Non-Authority Rules")
    lifecycle = section(text, "Lifecycle State Tables")
    transitions = section(text, "Transition Rules")
    assertions = section(text, "Document Assertions for T02")

    assert_patterns(
        authority + lifecycle + transitions + assertions,
        [
            r"DecisionCandidate.*non-authoritative.*unless.*ArchitectureDecision.*accepted authority",
            r"ArchitecturePromptRecord.*provenance.*not authority|ArchitecturePromptRecord.*provenance/context, not authority or proof",
            r"external AI output.*non-authoritative",
            r"accepted doctrine and proof satisfaction are separate states",
            r"accepted.*decision.*may not validate.*until.*ProofGate.*satisfied",
            r"ProofGate.*definition.*never.*proof|ProofGate.*definitions do not satisfy proof gates",
            r"verified.*proof gates.*satisfied by durable evidence|durable evidence.*required evidence class",
        ],
    )


def test_derived_projections_stale_project_state_and_unsafe_anchors_are_blocked() -> None:
    text = read_model()
    non_claims = section(text, "Required Non-Claims")
    authority = section(text, "Authority and Non-Authority Rules")
    core_matrix = section(text, "Generic ACP Core Action Matrix")
    assertions = section(text, "Document Assertions for T02")

    derived_projection = table_subsection(section(text, "Lifecycle State Tables"), "DerivedProjectionReference")

    assert_patterns(
        non_claims + authority + derived_projection + core_matrix + assertions,
        [
            r"derived JSONL.*RDF.*SHACL.*SPARQL.*recovery.*dashboard.*report.*project-state.*non-authoritative",
            r"stale `?prd/project-state/\*`? files.*not current M048 authority|does not refresh stale `?prd/project-state/\*`? files",
            r"DerivedProjectionReference[\s\S]*authority_status: non_authoritative",
            r"derived projections.*diagnostics and recovery views only",
            r"\.gsd/exec/\*.*absolute local paths.*ignored paths.*raw provider payloads.*raw vectors.*secrets.*unnecessary raw legal text",
            r"external URLs? as the only proof",
            r"unsafe anchors.*blocked durable proof anchors|blocked durable proof anchors[\s\S]*unsafe",
        ],
    )


def test_git_lex_main_repo_adoption_remains_blocked_until_isolated_proof() -> None:
    text = read_model()
    transitions = section(text, "Transition Rules")
    profile_matrix = section(text, "law-nexus Profile Action Matrix")
    checklist = section(text, "S04 Isolated Git-Lex Mechanic Checklist")
    assertions = section(text, "Document Assertions for T02")

    assert_patterns(
        transitions + profile_matrix + checklist + assertions,
        [
            r"Main-repo `?git lex init`?.*`?\.lex`? state creation remain blocked.*S04 isolated proof.*adoption decision",
            r"Use git-lex in main repo[\s\S]*Not yet[\s\S]*Blind `?git lex init`? or `?\.lex`? creation[\s\S]*S04 isolated proof plus later explicit adoption decision",
            r"Run git-lex proof only outside main-repo adoption state; do not create main-repo `?\.lex`? state",
            r"git lex init.*\.lex.*blocked until isolated proof and explicit adoption decision|\.lex.*blocked until isolated proof and explicit adoption decision",
        ],
    )


def test_reusable_acp_core_excludes_law_nexus_profile_constraints() -> None:
    text = read_model()
    boundary = section(text, "Reusable Core versus Profile Boundary")
    lifecycle = section(text, "Lifecycle State Tables")
    transition_rules = section(text, "Transition Rules")
    assertions = section(text, "Document Assertions for T02")

    assert_terms(
        boundary + transition_rules + assertions,
        [
            "law-nexus",
            "Russian legal evidence",
            "FalkorDB",
            "parser",
            "LLM",
            "GSD",
            "R035",
            "R037",
            "R038",
            "ProfileConstraint",
        ],
    )
    assert_patterns(
        boundary + lifecycle + transition_rules + assertions,
        [
            r"generic core must express the block as generic categories and action semantics",
            r"must not pollute the generic core taxonomy",
            r"it belongs in `ProfileConstraint` or a profile adapter, not in the reusable ACP core",
            r"remain profile constraints",
        ],
    )


def test_r035_r037_r038_are_not_validated_by_acp_or_projection_evidence_alone() -> None:
    text = read_model()
    lowered = normalized(text)
    non_claims = section(text, "Required Non-Claims")
    profile_matrix = section(text, "law-nexus Profile Action Matrix")
    checklist = section(text, "S04 Isolated Git-Lex Mechanic Checklist")
    assertions = section(text, "Document Assertions for T02")
    negative_tests = section(text, "Negative Tests")

    assert_terms(non_claims + profile_matrix + checklist + assertions + negative_tests, REQUIREMENT_IDS)
    assert "this contract does not validate `r035`, `r037`, or `r038`" in lowered
    assert_patterns(
        profile_matrix + checklist + assertions + negative_tests,
        [
            r"R035[\s\S]*Marking `?R035`? validated from ACP research, projections, docs, prompt records, or git-lex mechanics alone",
            r"R037[\s\S]*Marking `?R037`? validated from graph-context staging, dashboard output, or source-record existence",
            r"R038[\s\S]*Treating internal review packs, LLM review, or ACP summaries as independent review satisfaction",
            r"R035`, `R037`, and `R038` cannot be marked validated by fixture or projection proof",
            r"R035`, `R037`, or `R038` is marked validated from ACP docs, fixture proof, git-lex mechanics, or projections alone",
        ],
    )


def test_negative_tests_cover_boundary_regressions() -> None:
    text = read_model()
    negative_tests = section(text, "Negative Tests")

    expected_cases = [f"NEG-S03-{number:03d}" for number in range(1, 15)]
    assert_terms(negative_tests, expected_cases)
    assert_patterns(
        negative_tests,
        [
            r"DecisionCandidate.*accepted `?ArchitectureDecision`?[\s\S]*Reject or flag `?derived_authority_overclaim`?",
            r"ArchitecturePromptRecord.*external AI output.*used as proof[\s\S]*Reject or flag non-authoritative provenance misuse",
            r"ProofGate.*definition.*marked `?satisfied`? with no evidence anchor[\s\S]*pending_evidence",
            r"derived JSONL/RDF/recovery/project-state projection.*only source for an authoritative claim[\s\S]*derived_authority_overclaim",
            r"Stale `?prd/project-state/\*`? data.*current M048[\s\S]*stale_summary",
            r"\.gsd/exec/\*.*durable proof[\s\S]*unsafe_anchor",
            r"git lex init.*\.lex.*main repository[\s\S]*blocked_adoption",
            r"R035.*R037.*R038.*ACP docs, fixture proof, git-lex mechanics, or projections alone[\s\S]*profile_boundary_risk[\s\S]*derived_authority_overclaim",
            r"Russian legal evidence, FalkorDB, parser, LLM, or GSD-specific rule.*generic ACP core[\s\S]*profile_boundary_risk",
            r"fresh derived projection changes its `?authority_status`? to authoritative[\s\S]*derived_authority_overclaim",
            r"proof-gate waiver.*parser, legal, FalkorDB, runtime, or independent-review proof[\s\S]*profile_boundary_risk",
        ],
    )
