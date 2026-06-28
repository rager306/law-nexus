from __future__ import annotations

from pathlib import Path

REVIEW = Path("prd/architecture/acp-projection-helper-extraction-review.md")


def read_review() -> str:
    return REVIEW.read_text(encoding="utf-8")


def test_acp_projection_helper_review_has_required_sections() -> None:
    text = read_review()

    for section in [
        "## Purpose",
        "## Source-truth boundary",
        "## Candidate classification summary",
        "## Extraction rules for future work",
        "## Canonical registry mutation guardrails",
        "## GitNexus traceability notes",
        "## Decision",
        "## Non-claims",
    ]:
        assert section in text


def test_acp_projection_helper_review_classifies_candidates() -> None:
    text = read_review()

    for classification in ["extract-later", "keep-in-script", "defer"]:
        assert classification in text

    for candidate_group in [
        "Path display and repository-relative normalization helpers",
        "Canonical registry path guards",
        "ACP source-reference conversion helpers",
        "RDF string escaping and IRI helpers",
        "TTL block builders",
        "SHACL and SPARQL template builders",
        "Output writers and stale-check helpers",
        "CLI modes and argument parsing",
    ]:
        assert candidate_group in text


def test_acp_projection_helper_review_preserves_canonical_registry_write_guards() -> None:
    text = read_review()

    guarded_paths = [
        "prd/architecture/architecture_items.jsonl",
        "prd/architecture/architecture_edges.jsonl",
    ]
    for path in guarded_paths:
        assert path in text

    assert "must remain protected from projection-helper writes" in text
    assert "derived paths remain diagnostic/projection artifacts, not authoritative registry truth" in text


def test_acp_projection_helper_review_blocks_projection_overclaims() -> None:
    text = read_review()

    overclaim_guards = [
        "ACP/RDF/SPARQL/JSON-LD projection output validates requirements.",
        "Projection helper output proves legal correctness, parser completeness, retrieval quality, FalkorDB readiness, OpenCypher completeness, or LLM authority.",
        "Do not claim R035/R037/R038 validation from projection evidence alone.",
        "Do not promote law-nexus profile constraints into the external generic ACP/git-lex core.",
    ]
    for guard in overclaim_guards:
        assert guard in text


def test_acp_projection_helper_review_records_gitnexus_traceability() -> None:
    text = read_review()

    assert "Function:scripts/export-architecture-rdf-projection.py:ttl_prefixes" in text
    assert "Upstream impact for `ttl_prefixes` is LOW" in text
    assert "file-qualified GitNexus UIDs" in text


def test_acp_projection_helper_review_keeps_review_first_decision() -> None:
    text = read_review()

    assert "review-first, extract-later" in text
    assert "Immediate extraction is not justified in S19" in text
