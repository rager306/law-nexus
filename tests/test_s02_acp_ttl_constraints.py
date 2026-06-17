"""S02 acp.ttl constraint-set regression test (M064-4aierx/S02/T02).

Asserts the locked SHAPE-CONTRACT.md (D085 Design B) target snapshot for
git-lex-kit-acp/ontology/acp/acp.ttl:

  - exactly 22 rdfs:domain declarations (3 baseline + 19 added),
  - exactly 2 owl:Restriction blocks,
  - exactly 2 owl:minCardinality declarations,
  - owl:versionInfo bumped to "0.2.0" (no "0.1.0" remains),
  - both minCount restriction targets present (verdict on ProofGate,
    sourceArtifact on EvidenceAnchor),
  - key domain assignments present (verdict -> ProofGate+ValidationClaim;
    sourceArtifact -> EvidenceAnchor; nonAuthoritative -> the 8 record classes),
  - no /root/ anchor literals (self-guard against the F3 line-policy trap),
  - all M056 REQUIRED_ONTOLOGY_TERMS still present (no term dropped).

The ontology itself remains derived / non-authoritative (R046); this test does
not validate R035/R037/R038 and does not claim runtime or source-truth proof.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Mirror of scripts/verify-m056-acp-kit.py REQUIRED_ONTOLOGY_TERMS. Kept inline
# so this regression test is self-contained and pins the v0.2.0 term set.
REQUIRED_ONTOLOGY_TERMS = (
    "acp:SourceRecord",
    "acp:Requirement",
    "acp:Decision",
    "acp:EvidenceAnchor",
    "acp:ProofGate",
    "acp:HealthFinding",
    "acp:Projection",
    "acp:LifecycleState",
    "acp:AuthorityClass",
    "acp:ValidationClaim",
    "acp:ProfileConstraint",
    "acp:RuntimeAdapter",
    "acp:hasEvidenceAnchor",
    "acp:requiresProofGate",
    "acp:satisfiesProofGate",
    "acp:blocksClaim",
    "acp:validatesRequirement",
    "acp:doesNotValidateRequirement",
    "acp:derivedFrom",
    "acp:hasLifecycleState",
    "acp:hasAuthorityClass",
    "acp:constrainedByProfile",
    "acp:implementedByAdapter",
    "acp:identifier",
    "acp:sourcePath",
    "acp:selector",
    "acp:nonAuthoritative",
    "acp:blockedRequirementValidation",
    "acp:proofLevel",
    "acp:verdict",
    "acp:sourceArtifact",
    "acp:allowedNextAction",
    "acp:blockedAction",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ACP_TTL = REPO_ROOT / "git-lex-kit-acp" / "ontology" / "acp" / "acp.ttl"

# The 8 record classes that must be enumerated in acp:nonAuthoritative's domain
# (D3: flat ACP hierarchy mandates enumeration, no superclass expansion).
NON_AUTHORITATIVE_DOMAIN_CLASSES = (
    "acp:SourceRecord",
    "acp:Requirement",
    "acp:Decision",
    "acp:EvidenceAnchor",
    "acp:ProofGate",
    "acp:ValidationClaim",
    "acp:HealthFinding",
    "acp:Projection",
)


@pytest.fixture(scope="module")
def acp_text() -> str:
    assert ACP_TTL.exists(), f"acp.ttl missing at {ACP_TTL}"
    return ACP_TTL.read_text(encoding="utf-8")


def _statement_block(text: str, subject: str) -> str:
    """Return the Turtle statement block for ``subject`` (e.g. 'acp:verdict').

    A block runs from ``acp:<subject> a owl:...`` up to the next top-level subject
    (``acp:`` / ``<https`` at column 0) or end of file. Indented predicate lines
    are not matched, so only true statement boundaries delimit the block.
    """
    needle = f"{subject} a owl:"
    start = text.find(needle)
    assert start != -1, f"statement block for {subject} not found in acp.ttl"
    tail = text[start:]
    m = re.search(r"\n(?:acp:|<https|# ====)", tail)
    end = m.start() if m else len(tail)
    return tail[:end]


def test_domain_count_is_twenty_two(acp_text: str) -> None:
    # 3 baseline (blocksClaim/validatesRequirement/doesNotValidateRequirement)
    # + 19 added (10 datatype + 9 object) = 22 total.
    assert acp_text.count("rdfs:domain") == 22


def test_restriction_count_is_two(acp_text: str) -> None:
    assert acp_text.count("owl:Restriction") == 2


def test_min_cardinality_count_is_two(acp_text: str) -> None:
    assert acp_text.count("owl:minCardinality") == 2


def test_version_bumped_to_0_2_0(acp_text: str) -> None:
    assert 'owl:versionInfo "0.2.0"' in acp_text
    assert 'owl:versionInfo "0.1.0"' not in acp_text


def test_both_restriction_targets_present(acp_text: str) -> None:
    assert "owl:onProperty acp:verdict" in acp_text
    assert "owl:onProperty acp:sourceArtifact" in acp_text


def test_no_root_anchor_literals(acp_text: str) -> None:
    # F3 self-guard: the verify-m056 line-policy scanner forbids /root/ anchors.
    assert "/root/" not in acp_text


@pytest.mark.parametrize("term", REQUIRED_ONTOLOGY_TERMS)
def test_required_ontology_terms_present(acp_text: str, term: str) -> None:
    assert term in acp_text, f"required ontology term missing from acp.ttl: {term}"


def test_verdict_domain_is_proofgate_and_validationclaim(acp_text: str) -> None:
    block = _statement_block(acp_text, "acp:verdict")
    assert "rdfs:domain" in block
    assert "acp:ProofGate" in block
    assert "acp:ValidationClaim" in block


def test_source_artifact_domain_includes_evidenceanchor(acp_text: str) -> None:
    block = _statement_block(acp_text, "acp:sourceArtifact")
    assert "rdfs:domain" in block
    assert "acp:EvidenceAnchor" in block


def test_non_authoritative_domain_is_eight_record_classes(acp_text: str) -> None:
    block = _statement_block(acp_text, "acp:nonAuthoritative")
    assert "rdfs:domain" in block
    # exactly the 8 contracted classes appear on the nonAuthoritative property,
    # nothing more, nothing less (guards against D3 enumeration drift).
    found = re.findall(r"acp:[A-Za-z]+", block)
    domain_classes = {c for c in found if c != "acp:nonAuthoritative"}
    assert domain_classes == set(NON_AUTHORITATIVE_DOMAIN_CLASSES)
