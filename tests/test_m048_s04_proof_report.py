from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "prd/architecture/acp/M048-S04-GIT-LEX-ISOLATED-PROOF.md"


def report_text() -> str:
    assert REPORT.exists(), f"Missing S04 proof report: {REPORT.relative_to(ROOT)}"
    return REPORT.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert marker in text, f"Missing required report section: {heading}"
    start = text.index(marker) + len(marker)
    next_heading = text.find("\n## ", start)
    if next_heading == -1:
        return text[start:]
    return text[start:next_heading]


def test_report_contains_required_s04_decision_sections() -> None:
    text = report_text()

    required_sections = [
        "Verdict",
        "Proof Scope",
        "Harness Result Summary",
        "Acquisition and Build Status",
        "Typed-Record Coverage",
        "Validation Status",
        "Extraction and Projection Status",
        "Query and Recovery Status",
        "Lifecycle and Proof-Gate Status",
        "Profile-Boundary Status",
        "Blocked and Allowed Action Visibility",
        "Main-Repo Mutation Guard Result",
        "S05 Integration Decision Inputs",
        "Failure Modes",
        "Load Profile",
        "Negative Tests",
        "Observability Impact",
    ]
    for heading in required_sections:
        assert section(text, heading).strip(), f"Section must not be empty: {heading}"

    verdict = section(text, "Verdict").casefold()
    assert "partially proven" in verdict
    assert "runtime git-lex mechanics are **blocked**" in verdict
    assert "not as evidence that git-lex is adopted" in verdict


def test_report_preserves_non_authoritative_projection_language() -> None:
    text = report_text()
    projection = section(text, "Extraction and Projection Status")
    decision_inputs = section(text, "S05 Integration Decision Inputs")

    assert "authority status is **non-authoritative**" in projection
    assert "must not serve as source truth" in projection
    assert "must not" in projection and "validate requirements" in projection
    assert "Derived projections must remain non-authoritative" in decision_inputs


def test_report_does_not_claim_r035_r037_r038_validation() -> None:
    text = report_text()
    lowered = text.casefold()

    for requirement in ["r035", "r037", "r038"]:
        assert f"{requirement} is validated" not in lowered
        assert f"{requirement} has been validated" not in lowered
        assert f"validates {requirement}" not in lowered
        assert f"validated {requirement}" not in lowered
        assert f"{requirement} validated" not in lowered

    non_claim_sections = "\n".join(
        [
            section(text, "Proof Scope"),
            section(text, "Validation Status"),
            section(text, "S05 Integration Decision Inputs"),
        ]
    ).casefold()
    assert "does not validate" in non_claim_sections
    assert "provides no validation evidence" in non_claim_sections


def test_report_does_not_claim_main_repo_lex_adoption() -> None:
    text = report_text()
    lowered = text.casefold()

    forbidden_adoption_claims = [
        "git-lex is adopted.",
        ".lex is adopted.",
        "main-repo .lex is adopted.",
        "main repository .lex is adopted.",
        "adopted .lex state",
        "adoption readiness is proven",
        "adoption readiness was proven",
        "it is safe to initialize in the main repository",
    ]
    for claim in forbidden_adoption_claims:
        assert claim not in lowered

    guard = section(text, "Main-Repo Mutation Guard Result")
    blocked = section(text, "Blocked and Allowed Action Visibility")
    assert "Main `.lex` after harness | absent" in guard
    assert "not an adoption claim" in guard
    assert "blocked path is initializing" in blocked
