from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "prd/architecture/acp/M048-S07-VALIDATION-REMEDIATION.md"

REQUIRED_SECTIONS = [
    "Verdict",
    "Remediation Scope",
    "Requirement Coverage Matrix",
    "R035/R037/R038 Non-Goal Reconciliation",
    "R043 Coverage and Runtime Caveat",
    "S04/S05 Metadata Caveat Resolution",
    "Source/Projection and Mutation Boundary",
    "Future Law-Nexus Binding Handoff",
    "Validation Round 1 Evidence",
    "Failure Modes",
    "Load Profile",
    "Negative Tests",
    "Observability Impact",
    "Closeout Criteria",
]

REQUIREMENT_IDS = ["R035", "R037", "R038", "R043", "R046", "R047", "R048"]

FORBIDDEN_OVERCLAIMS = [
    "git-lex is adopted.",
    "full runtime git-lex adoption is approved",
    "full acp git-lex runtime adoption is approved",
    "r035 is validated",
    "r037 is validated",
    "r038 is validated",
]

FORBIDDEN_COMPLETED_BINDING_CLAIMS = [
    "future law-nexus binding is complete",
    "future law-nexus binding is completed",
    "law-nexus binding is complete in m048",
    "m048 completes law-nexus binding",
    "m048 delivered law-nexus binding",
]


def report_text() -> str:
    assert REPORT_PATH.exists(), f"Missing S07 remediation report: {REPORT_PATH.relative_to(ROOT)}"
    return REPORT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required report section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def assert_s07_report_contract(text: str) -> None:
    assert text.startswith("# M048 S07 Validation Remediation"), "Report title drifted"

    for heading in REQUIRED_SECTIONS:
        body = section(text, heading)
        assert body.strip(), f"Section must not be empty: {heading}"

    lowered = text.casefold()
    for claim in FORBIDDEN_OVERCLAIMS + FORBIDDEN_COMPLETED_BINDING_CLAIMS:
        assert claim not in lowered, f"Forbidden overclaim present: {claim}"

    coverage_matrix = section(text, "Requirement Coverage Matrix")
    for requirement_id in REQUIREMENT_IDS:
        assert f"`{requirement_id}`" in coverage_matrix, f"Coverage matrix missing {requirement_id}"

    non_goals = section(text, "R035/R037/R038 Non-Goal Reconciliation")
    non_goals_lowered = non_goals.casefold()
    for requirement_id in ["R035", "R037", "R038"]:
        assert f"`{requirement_id}`" in non_goals, f"Non-goal reconciliation missing {requirement_id}"
    assert "must remain explicit non-goals" in non_goals
    assert "m048 preserves the proof boundary for `r035`, `r037`, and `r038`; it does not validate them" in non_goals_lowered
    assert "s04-s06 do not prove ontology architecture correctness" in non_goals_lowered
    assert "s04-s06 do not perform falkordb csv loading" in non_goals_lowered
    assert "does not itself replace a review gate" in non_goals_lowered

    r043 = section(text, "R043 Coverage and Runtime Caveat")
    r043_lowered = r043.casefold()
    assert "bounded partial coverage" in r043_lowered
    assert "deterministic fixture mechanics" in r043_lowered
    assert "typed source records" in r043_lowered
    assert "validation" in r043_lowered
    assert "projection/recovery" in r043_lowered
    assert "mutation guard" in r043_lowered
    assert "runtime git-lex acquisition/adoption remains blocked/deferred" in lowered
    assert "fatal_failures=[]" in r043

    caveat = section(text, "S04/S05 Metadata Caveat Resolution")
    caveat_lowered = caveat.casefold()
    assert "runtime layer" in caveat_lowered
    assert "deterministic acp layer" in caveat_lowered
    assert "blocked for runtime git-lex adoption" in caveat_lowered
    assert "pass bounded deterministic acp mechanics and mutation-safety checks" in caveat_lowered

    boundary = section(text, "Source/Projection and Mutation Boundary")
    boundary_lowered = boundary.casefold()
    assert "derived outputs remain non-authoritative diagnostics" in boundary_lowered
    assert "derived projections cannot override source records" in boundary_lowered
    assert "validate requirements by themselves" in boundary_lowered
    assert "do not run `git lex init` in the main `law-nexus` checkout" in boundary_lowered
    assert "do not create or mutate main-repository `.lex` state" in boundary_lowered

    handoff = section(text, "Future Law-Nexus Binding Handoff")
    handoff_lowered = handoff.casefold()
    assert "explicitly future work" in handoff_lowered
    assert "future binding milestone" in handoff_lowered
    assert "keep runtime git-lex adoption behind a new proof gate" in handoff_lowered
    assert "treat any future projection claim that a requirement is validated as a hypothesis" in handoff_lowered

    evidence = section(text, "Validation Round 1 Evidence")
    assert "uv run python scripts/run-m048-s04-git-lex-proof.py --check" in evidence
    assert "uv run python scripts/run-m048-s05-git-lex-workflows.py --check" in evidence
    assert "test ! -e .lex" in evidence
    assert "prd/architecture/acp/M048-S07-VALIDATION-REMEDIATION.md" in evidence


def test_report_exists_and_has_required_non_empty_sections() -> None:
    assert_s07_report_contract(report_text())


def test_coverage_matrix_reconciles_all_required_m048_requirements() -> None:
    text = report_text()
    coverage_matrix = section(text, "Requirement Coverage Matrix")

    expected_rows = {
        "R035": "must not claim `R035` validation",
        "R037": "must not use ACP/git-lex diagnostics as ingestion proof",
        "R038": "not a claim created by S04-S06",
        "R043": "Runtime git-lex acquisition/adoption remains blocked/deferred",
        "R046": "non-authoritative projection status",
        "R047": "no-main-`.lex` expectations",
        "R048": "Full law-nexus binding remains future work",
    }
    for requirement_id, expected_boundary in expected_rows.items():
        assert f"| `{requirement_id}` |" in coverage_matrix
        assert expected_boundary in coverage_matrix


def test_report_explicitly_keeps_r035_r037_r038_not_validated_by_acp_git_lex_or_projection_evidence() -> None:
    text = report_text()
    lowered = text.casefold()

    for requirement_id in ["r035", "r037", "r038"]:
        assert f"{requirement_id} is validated" not in lowered
        assert f"{requirement_id} has been validated" not in lowered
        assert f"validates {requirement_id}" not in lowered
        assert f"validated {requirement_id}" not in lowered

    assert "m048 may cite source/projection/proof-boundary guardrails, but it must not claim `r035` validation" in lowered
    assert "m048 does not load falkordb data and must not use acp/git-lex diagnostics as ingestion proof" in lowered
    assert "not newly validated by this report" in lowered
    assert "s04/s05 validate r035/r037/r038" in lowered
    assert "unacceptable wording" in lowered


def test_report_bounds_r043_blocked_runtime_semantics_without_turning_blocked_into_failed() -> None:
    text = report_text()
    r043 = section(text, "R043 Coverage and Runtime Caveat")
    caveat = section(text, "S04/S05 Metadata Caveat Resolution")

    assert "`R043` receives bounded partial coverage from S04-S06" in r043
    assert "runtime git-lex adoption deferred" in r043.casefold()
    assert "`blocked` means the local `git lex` / `git-lex` runtime surface was unavailable" in r043
    assert "It does not mean deterministic ACP mechanics failed when `fatal_failures=[]`, deterministic checks pass, and the mutation guard is safe." in r043
    assert "S04/S05 are blocked for runtime git-lex adoption but pass bounded deterministic ACP mechanics and mutation-safety checks." in caveat


def test_report_keeps_future_law_nexus_binding_as_future_work_only() -> None:
    text = report_text()
    handoff = section(text, "Future Law-Nexus Binding Handoff")
    lowered = text.casefold()

    assert "Future law-nexus architecture binding is explicitly future work." in handoff
    assert "A future binding milestone should start with these expectations" in handoff
    assert "Use M048 as ACP governance foundation evidence, not as product/runtime/legal proof." in handoff
    assert "Keep runtime git-lex adoption behind a new proof gate" in handoff
    for claim in FORBIDDEN_COMPLETED_BINDING_CLAIMS:
        assert claim not in lowered


def test_negative_contract_detects_missing_required_section() -> None:
    text = report_text().replace("## Future Law-Nexus Binding Handoff\n", "## Future Binding Handoff\n")

    with pytest.raises(AssertionError, match="Missing required report section: Future Law-Nexus Binding Handoff"):
        assert_s07_report_contract(text)


def test_negative_contract_detects_missing_requirement_id() -> None:
    text = report_text().replace("`R047`", "`R047-MISSING`")

    with pytest.raises(AssertionError, match="Coverage matrix missing R047"):
        assert_s07_report_contract(text)


def test_negative_contract_detects_forbidden_adoption_and_validation_claims() -> None:
    text = report_text() + "\n\nForbidden drift: git-lex is adopted. R035 is validated.\n"

    with pytest.raises(AssertionError, match="Forbidden overclaim present"):
        assert_s07_report_contract(text)


def test_negative_contract_detects_hidden_runtime_caveat() -> None:
    text = report_text().replace("`fatal_failures=[]`", "`fatal_failures omitted`")

    with pytest.raises(AssertionError, match="fatal_failures"):
        assert_s07_report_contract(text)


def test_negative_contract_detects_completed_future_binding_language() -> None:
    text = report_text() + "\n\nForbidden drift: future law-nexus binding is complete.\n"

    with pytest.raises(AssertionError, match="Forbidden overclaim present"):
        assert_s07_report_contract(text)
