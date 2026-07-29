from __future__ import annotations

from pathlib import Path

CLOSURE = Path("prd/architecture/onion-gitnexus-traceability-closure.md")


def read_closure() -> str:
    return CLOSURE.read_text(encoding="utf-8")


def test_traceability_closure_has_required_sections() -> None:
    text = read_closure()

    for section in [
        "## Purpose",
        "## Closure scope",
        "## Representative GitNexus addressability matrix",
        "## Slice-to-traceability closure",
        "## GitNexus operational rules",
        "## Required validators after M076",
        "## Milestone validation handoff",
        "## Non-claims",
        "## Result",
    ]:
        assert section in text


def test_traceability_closure_pins_representative_gitnexus_uids() -> None:
    text = read_closure()

    for uid in [
        "Class:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase",
        "Class:src/law_nexus/application/representative_corpus_manifest.py:RepresentativeCorpusManifestBuilder",
        "Class:src/law_nexus/adapters/embeddings/local_sentence_transformer.py:LocalSentenceTransformerEmbedder",
        "Class:src/law_nexus/application/generated_cypher_policy.py:GeneratedCypherPolicy",
        "Class:src/law_nexus/ports/graph_store.py:GraphStore",
        "Function:src/law_nexus/adapters/cli/runtime.py:write_json_report",
        "Function:tests/test_script_retirement_candidates_review.py:test_script_retirement_review_blocks_premature_deletion",
        "Function:scripts/verify-falkordb-csv-ingest-proof.py:main",
        "Function:scripts/build_representative_retrieval_corpus_manifest.py:main",
        "Function:scripts/acp_git_lex_backend.py:normalize_wrapper_record",
    ]:
        assert uid in text


def test_traceability_closure_pins_slice_dependencies() -> None:
    text = read_closure()

    for dependency in [
        "S05 parser source CLI compatibility",
        "S12 representative corpus manifest",
        "S17 local embedding adapter",
        "S21 script retirement review",
    ]:
        assert dependency in text


def test_traceability_closure_records_gitnexus_operational_caveats() -> None:
    text = read_closure()

    for caveat in [
        "Use repo name `law-nexus`",
        "gitnexus analyze --force --name law-nexus",
        "file-qualified UIDs",
        "Large legal source files may be skipped",
        "GitNexus addressability is navigation and traceability evidence",
    ]:
        assert caveat in text


def test_traceability_closure_keeps_required_validators_and_non_claims() -> None:
    text = read_closure()

    for validator in [
        "uv run pytest tests/test_parser_source_cli_compatibility.py -q",
        "uv run pytest tests/test_representative_corpus_manifest_use_case.py -q",
        "uv run pytest tests/test_local_embedding_adapter.py -q",
        "uv run pytest tests/test_generated_cypher_policy.py -q",
        "uv run pytest tests/test_cli_runtime_utilities.py -q",
        "uv run pytest tests/test_script_retirement_candidates_review.py -q",
        "uv run pytest tests/test_onion_gitnexus_traceability_closure.py -q",
    ]:
        assert validator in text

    for non_claim in [
        "Full CLI completeness across all 140 top-level scripts.",
        "Safe script deletion.",
        "Legal correctness or authoritative legal advice.",
        "Consultant/Garant parser completeness.",
        "Retrieval answer faithfulness or quality.",
        "Embedding model availability or quality.",
        "Generated Cypher query correctness.",
        "Production FalkorDB readiness.",
        "ACP/git-lex/RDF/SPARQL/JSON-LD projection authority.",
    ]:
        assert non_claim in text
