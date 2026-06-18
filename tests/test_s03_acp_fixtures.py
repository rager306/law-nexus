"""S03 ACP-kit true-negative/positive fixture regression test (M064-4aierx/S03/T01).

Asserts the committed S03 ACP-kit fixtures carry the locked frontmatter invariants
so the T02 git-lex validate true-negative/positive proof stays clean
(SHAPE-CONTRACT.md section 7, D087):

  - all 3 fixtures exist and each carries 'acp.' typed frontmatter,
  - the EvidenceAnchor POSITIVE fixture (example-evidence-anchor.md) has a
    'sourceArtifact' key,
  - the EvidenceAnchor NEGATIVE fixture (example-evidence-anchor-missing-source-artifact.md)
    does NOT have a 'sourceArtifact' key (trips sh:minCount 1),
  - the ProofGate NEGATIVE fixture verdict (example-proof-gate-invalid-verdict.md)
    is outside the 6-element VerdictValue enum (trips sh:in),
  - NONE of the 3 fixtures contains 'nonAuthoritative' (D087 invariant: under the
    adaptive-overlay validate path a nonAuthoritative string 'true' emits a
    spurious xsd:boolean datatype violation because detection reads the static
    v0.1.0 shapes while enforcement reads static+adaptive v0.2.0),
  - no fixture contains a repository-root absolute path literal (self-guard
    against the verify-m056 line-policy unsafe_anchor scanner),
  - any line matching R035/R037/R038 + (validated|validates|validation
    evidence|proof for) also carries a ' not ' marker (mirrors the verify-m056
    forbidden_profile_validation policy).

These fixtures are committed content and self-describing. This test does NOT run
git-lex validate and does NOT claim runtime, source-truth, or profile proof.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EA_DIR = REPO_ROOT / "git-lex-kit-acp" / "content" / "ACP" / "EvidenceAnchor"
PG_DIR = REPO_ROOT / "git-lex-kit-acp" / "content" / "ACP" / "ProofGate"

EA_POSITIVE = EA_DIR / "example-evidence-anchor.md"
EA_NEGATIVE = EA_DIR / "example-evidence-anchor-missing-source-artifact.md"
PG_NEGATIVE = PG_DIR / "example-proof-gate-invalid-verdict.md"

ALL_FIXTURES = (EA_POSITIVE, EA_NEGATIVE, PG_NEGATIVE)

# VerdictValue enum from git-lex-kit-acp/ontology/acp/acp.ttl (D085):
# acp:VerdictValue owl:oneOf (...). The ProofGate true-negative verdict must be
# OUTSIDE this set so the generated sh:in constraint rejects it.
VERDICT_VALUE_ENUM = (
    "pass",
    "fail",
    "needs-attention",
    "needs-remediation",
    "blocked",
    "not-applicable",
)

# The guardrail sentence every ACP-kit example must carry. The verify-m056
# check_text_policies scanner rglobs every kit file, so a line carrying
# R035/R037/R038 plus a validation/proof claim must also carry a ' not ' marker.
GUARDRAIL_SENTENCE = "This example is synthetic ACP-kit shape evidence only"


def _read(path: Path) -> str:
    assert path.exists(), f"fixture missing: {path}"
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> str:
    """Return the YAML frontmatter region between the '---' fences."""
    assert text.startswith("---\n"), f"missing opening frontmatter fence: {text[:40]!r}"
    end = text.find("\n---\n", 4)
    assert end != -1, "missing closing frontmatter fence"
    return text[4:end]


@pytest.fixture(scope="module")
def ea_positive_text() -> str:
    return _read(EA_POSITIVE)


@pytest.fixture(scope="module")
def ea_negative_text() -> str:
    return _read(EA_NEGATIVE)


@pytest.fixture(scope="module")
def pg_negative_text() -> str:
    return _read(PG_NEGATIVE)


# (a) all 3 fixtures exist and each has 'acp.' frontmatter.
@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=lambda p: p.name)
def test_all_fixtures_exist_and_have_acp_frontmatter(fixture: Path) -> None:
    fm = _frontmatter(_read(fixture))
    assert "acp." in fm, f"fixture {fixture.name} lacks acp. typed frontmatter"


# (b) EA-positive has a 'sourceArtifact' key, EA-negative does NOT.
def test_ea_positive_has_source_artifact(ea_positive_text: str) -> None:
    fm = _frontmatter(ea_positive_text)
    assert "acp.EvidenceAnchor.sourceArtifact:" in fm


def test_ea_positive_has_identifier(ea_positive_text: str) -> None:
    fm = _frontmatter(ea_positive_text)
    assert "acp.EvidenceAnchor.identifier:" in fm


def test_ea_negative_lacks_source_artifact(ea_negative_text: str) -> None:
    fm = _frontmatter(ea_negative_text)
    assert "acp.EvidenceAnchor.sourceArtifact:" not in fm


def test_ea_negative_has_identifier(ea_negative_text: str) -> None:
    fm = _frontmatter(ea_negative_text)
    assert "acp.EvidenceAnchor.identifier:" in fm


# (c) PG-negative verdict is not in the 6-element VerdictValue enum.
def test_pg_negative_verdict_outside_enum(pg_negative_text: str) -> None:
    fm = _frontmatter(pg_negative_text)
    m = re.search(r'acp\.ProofGate\.verdict:\s*"?([^"\n]+)"?', fm)
    assert m, "acp.ProofGate.verdict frontmatter key missing"
    verdict = m.group(1).strip()
    assert verdict not in VERDICT_VALUE_ENUM, (
        f"verdict {verdict!r} must be outside the 6-element VerdictValue enum"
    )


# (d) NONE of the 3 fixtures contains 'nonAuthoritative' (D087 invariant).
@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=lambda p: p.name)
def test_no_nonauthoritative(fixture: Path) -> None:
    text = _read(fixture)
    assert "nonAuthoritative" not in text, (
        f"fixture {fixture.name} must not contain nonAuthoritative (D087: it "
        "would emit a spurious xsd:boolean violation under the adaptive-overlay path)"
    )


# (e) no fixture contains a repository-root absolute path literal.
@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=lambda p: p.name)
def test_no_root_anchor_literal(fixture: Path) -> None:
    text = _read(fixture)
    assert "/root/" not in text, f"fixture {fixture.name} contains forbidden /root/ literal"


# Guardrail sentence wording is mandatory (verify-m056 rglobs every new file).
@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=lambda p: p.name)
def test_guardrail_sentence_present(fixture: Path) -> None:
    text = _read(fixture)
    assert GUARDRAIL_SENTENCE in text, f"fixture {fixture.name} missing guardrail sentence"


# (f) any line carrying R035/R037/R038 + a validation/proof claim also carries ' not '.
@pytest.mark.parametrize("fixture", ALL_FIXTURES, ids=lambda p: p.name)
def test_r035_37_38_lines_carry_negative_marker(fixture: Path) -> None:
    text = _read(fixture)
    for line in text.splitlines():
        if re.search(r"R0?(35|37|38)", line) and re.search(
            r"validated|validates|validation evidence|proof for", line, flags=re.IGNORECASE
        ):
            assert " not " in line, (
                f"fixture {fixture.name}: line carrying an R035/R037/R038 "
                f"validation/proof claim lacks a ' not ' marker: {line!r}"
            )
