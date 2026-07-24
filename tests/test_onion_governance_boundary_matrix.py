from __future__ import annotations

from pathlib import Path

MATRIX = Path("prd/architecture/onion-governance-boundary-matrix.md")


def read_matrix() -> str:
    return MATRIX.read_text(encoding="utf-8")


def test_governance_boundary_matrix_has_required_sections() -> None:
    text = read_matrix()

    required_sections = [
        "## Source-truth hierarchy",
        "## Boundary matrix",
        "## Lifecycle tag discipline",
        "## Durable proof-anchor rules",
        "## Non-claim guardrails",
        "## S19 handoff",
    ]
    for section in required_sections:
        assert section in text


def test_governance_boundary_matrix_preserves_lifecycle_tags() -> None:
    text = read_matrix()

    for tag in ["[validated]", "[bounded]", "[smoke]", "[proposed]", "[deferred]"]:
        assert tag in text

    assert (
        "Do not smooth `[bounded]`, `[smoke]`, `[proposed]`, or `[deferred]` into `[validated]`"
        in text
    )


def test_governance_boundary_matrix_blocks_projection_overclaims() -> None:
    text = read_matrix()

    required_boundaries = [
        "ACP/git-lex/RDF/SPARQL/JSON-LD projections",
        "Requirement validation from ACP/git-lex/RDF/SPARQL/JSON-LD projections alone.",
        "Architecture registry/verifier/remediation outputs",
        "Non-authoritative projections/recovery surfaces",
        "Generated Cypher policy (`S16`)",
        "Local embedding adapter (`S17`)",
    ]
    for boundary in required_boundaries:
        assert boundary in text


def test_governance_boundary_matrix_keeps_durable_proof_anchor_exclusions() -> None:
    text = read_matrix()

    forbidden_anchor_phrases = [
        "`.gsd/exec/*` stdout/stderr paths as standalone proof",
        "Absolute local paths.",
        "Secrets, credentials, provider payloads, raw vectors, or unnecessary raw legal text.",
        "Ignored build/cache artifacts.",
    ]
    for phrase in forbidden_anchor_phrases:
        assert phrase in text


def test_governance_boundary_matrix_keeps_legalgraph_non_claims() -> None:
    text = read_matrix()

    non_claims = [
        "Legal correctness or authoritative legal advice.",
        "Parser completeness for Russian legal sources.",
        "Retrieval quality or answer faithfulness.",
        "Production FalkorDB readiness.",
        "Neo4j-to-FalkorDB feature equivalence.",
        "OpenCypher completeness.",
        "Generated Cypher correctness or runtime safety.",
        "Local embedding model availability or embedding quality.",
        "Managed GigaChat/GigaChat API support in embedding paths.",
    ]
    for non_claim in non_claims:
        assert non_claim in text
