from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "prd" / "retrieval" / "representative_retrieval_corpus_contract.md"

REQUIRED_SECTIONS = [
    "# Representative Retrieval Corpus Contract",
    "## Source artifacts",
    "## Manifest artifact and builder paths",
    "## Manifest schema",
    "## Coverage classes",
    "## Query-label shape",
    "## Candidate/reference shape",
    "## Provenance",
    "## Redaction",
    "## Forbidden payloads",
    "## Diagnostics",
    "## Explicit limits",
    "## S03 handoff",
    "## Non-claims",
    "## Verification hook",
]

REQUIRED_SOURCE_ARTIFACTS = [
    "prd/retrieval/local_retrieval_quality_benchmark_contract.md",
    "prd/retrieval/retrieval_output_validator_contract.md",
    "prd/retrieval/offline_citation_retrieval_contract.md",
    "prd/retrieval/real_artifact_evidence_mapping.md",
    "prd/retrieval/fixtures/offline_citation_retrieval_cases.json",
    "prd/retrieval/fixtures/real_artifact_retrieval_cases.json",
    "prd/parser/consultant_hierarchy_records.json",
    "prd/parser/consultant_hierarchy_records.jsonl",
    "prd/parser/parser_staging_graph.json",
]

EXPECTED_T02_PATHS = [
    "prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json",
    "prd/retrieval/representative_retrieval_corpus_manifest.md",
    "scripts/build_representative_retrieval_corpus_manifest.py",
    "tests/test_representative_retrieval_corpus_manifest.py",
]

REQUIRED_SCHEMA_FIELDS = [
    "schema_version",
    "corpus_id",
    "created_by",
    "source_artifacts",
    "coverage_classes",
    "query_labels",
    "candidate_references",
    "s03_handoff",
    "diagnostics",
    "non_claims",
]

REQUIRED_COVERAGE_CLASSES = [
    "source_family_consultant_wordml",
    "source_family_garant_odt_metadata",
    "legal_unit_path_coverage",
    "positive_retrieval",
    "distractor_retrieval",
    "scoped_no_answer",
    "ambiguous_rejection",
    "unsafe_rejection",
    "edition_path_mismatch",
    "environment_runtime_handoff_boundary",
]

REQUIRED_QUERY_FIELDS = [
    "query_label_id",
    "coverage_class_ids",
    "query_kind",
    "query_label_sha256",
    "scope_id",
    "as_of_date",
    "expected_relevant_reference_ids",
    "expected_result",
    "source_case_ids",
    "redaction",
]

REQUIRED_REFERENCE_FIELDS = [
    "reference_id",
    "source_family",
    "source_artifact",
    "source_sha256",
    "source_record_ids",
    "evidence_path_ids",
    "excerpt_sha256",
    "reference_role",
    "provenance",
    "redaction",
]

REQUIRED_REDACTION_FIELDS = [
    "raw_legal_text_persisted",
    "raw_query_text_persisted",
    "raw_prompt_persisted",
    "raw_vector_persisted",
    "provider_payload_persisted",
    "raw_falkordb_row_persisted",
    "generated_legal_advice_persisted",
    "absolute_path_persisted",
]

REQUIRED_DIAGNOSTIC_CODES = [
    "missing_source_artifact",
    "manifest_schema_mismatch",
    "unsafe_payload_field",
    "coverage_class_missing",
    "source_family_missing",
    "query_label_mismatch",
    "candidate_reference_mismatch",
    "edition_path_mismatch",
    "managed_api_forbidden",
    "raw_vector_forbidden",
    "raw_falkordb_row_forbidden",
    "gate_overclaim_forbidden",
]

REQUIRED_NON_CLAIMS = [
    "does not prove product retrieval quality",
    "does not prove parser completeness",
    "does not prove legal-answer correctness",
    "does not prove legal interpretation authority",
    "does not prove production FalkorDB runtime behavior",
    "does not prove production graph schema readiness",
    "does not prove local embedding quality",
    "does not compute runtime benchmark metrics",
    "does not allow managed GigaChat API fallback",
    "does not allow managed embedding API fallback",
    "does not persist raw legal text, raw query prompts, vectors, provider payloads, raw FalkorDB rows, or generated legal advice",
    "does not close GATE-G011",
    "does not close GATE-G008",
    "does not make LLM output legal authority",
    "does not make proof-local IDs production IDs",
]

FORBIDDEN_OVERCLAIM_PHRASES = [
    "GATE-G011 is closed",
    "closes GATE-G011",
    "production retrieval quality is proven",
    "proves product retrieval quality",
    "proves parser completeness",
    "legal advice:",
    "managed API fallback is allowed",
    "managed embedding API fallback is allowed",
]

FORBIDDEN_PERSISTENCE_PHRASES = [
    "raw legal text may be persisted",
    "raw query prompts may be persisted",
    "raw vectors may be persisted",
    "provider payloads may be persisted",
    "raw FalkorDB rows may be persisted",
]

FORBIDDEN_PATH_TOKENS = [
    "/root/",
    ".gsd/exec",
    ".planning/",
    ".audits/",
]


def contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    start = text.index(heading)
    next_heading = text.find("\n## ", start + len(heading))
    return text[start:] if next_heading == -1 else text[start:next_heading]


def test_contract_file_exists_and_has_frontmatter() -> None:
    assert CONTRACT_PATH.exists(), f"missing contract: {CONTRACT_PATH.relative_to(ROOT)}"
    text = contract_text()

    assert text.startswith("---\n")
    assert "title: \"Representative Retrieval Corpus Contract\"" in text
    assert "owner: \"M016/S02\"" in text
    assert "gate: \"GATE-G011\"" in text
    assert "contract_version: \"representative-retrieval-corpus/v1\"" in text
    assert "non_authoritative: true" in text


def test_required_sections_are_present_in_order() -> None:
    text = contract_text()
    positions = [text.find(heading) for heading in REQUIRED_SECTIONS]

    assert all(position >= 0 for position in positions)
    assert positions == sorted(positions)


def test_source_artifacts_are_tracked_repository_relative_inputs() -> None:
    text = contract_text()
    source_artifacts = section(text, "## Source artifacts")

    for artifact in REQUIRED_SOURCE_ARTIFACTS:
        assert f"`{artifact}`" in source_artifacts
        assert (ROOT / artifact).exists(), f"missing source artifact: {artifact}"
    assert "tracked repository-relative source artifacts" in source_artifacts
    assert "must not read `.gsd/`, `.planning/`, `.audits/`, untracked local corpora" in source_artifacts
    assert "must not fetch external data" in source_artifacts
    assert "managed GigaChat/GigaChat API" in source_artifacts
    assert "managed embedding API" in source_artifacts
    assert "raw FalkorDB rows" in source_artifacts


def test_contract_names_exact_t02_manifest_builder_and_check_paths() -> None:
    text = contract_text()
    paths = section(text, "## Manifest artifact and builder paths")

    for path in EXPECTED_T02_PATHS:
        assert f"`{path}`" in paths
    assert "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check" in paths
    assert "compact safe JSON" in paths
    assert "safe field paths and repository-relative artifact paths" in paths


def test_manifest_schema_version_id_prefixes_and_root_fields_are_declared() -> None:
    text = contract_text()
    intro = section(text, "# Representative Retrieval Corpus Contract")
    schema = section(text, "## Manifest schema")

    assert "representative-retrieval-corpus/v1" in intro
    for prefix in ["CORPUS-M016-*", "QRL-M016-*", "RC-M016-*", "COV-M016-*"]:
        assert f"`{prefix}`" in intro or prefix in schema
    for field in REQUIRED_SCHEMA_FIELDS:
        assert f"`{field}`" in schema
    assert "Must be exactly `representative-retrieval-corpus/v1`" in schema
    assert "stable sorted arrays by ID" in schema
    assert "at 10x corpus size" in schema
    assert "rather than raw payloads" in schema


def test_required_coverage_classes_make_manifest_representative_but_bounded() -> None:
    text = contract_text()
    coverage = section(text, "## Coverage classes")

    for coverage_class in REQUIRED_COVERAGE_CLASSES:
        assert f"`{coverage_class}`" in coverage
    assert "more representative than M015 seed fixtures" in coverage
    assert "bounded to tracked artifacts" in coverage
    assert "safe diagnostic" in coverage
    assert "must not be filled from raw ODT text" in coverage
    assert "must fail closed rather than choose arbitrarily" in coverage


def test_query_label_shape_is_hash_based_and_prompt_safe() -> None:
    text = contract_text()
    query_shape = section(text, "## Query-label shape")

    for field in REQUIRED_QUERY_FIELDS:
        assert f"`{field}`" in query_shape
    for query_kind in [
        "positive_retrieval",
        "distractor_retrieval",
        "scoped_no_answer",
        "ambiguous_rejection",
        "unsafe_rejection",
        "edition_path_mismatch",
        "environment_runtime_handoff_boundary",
    ]:
        assert f"`{query_kind}`" in query_shape
    assert "never raw query text" in query_shape
    assert "raw query labels and prompts must not be persisted" in query_shape
    assert "must not include raw legal text" in query_shape
    assert "provider payloads" in query_shape
    assert "raw FalkorDB rows" in query_shape


def test_candidate_reference_shape_is_source_backed_and_redacted() -> None:
    text = contract_text()
    candidate_shape = section(text, "## Candidate/reference shape")

    for field in REQUIRED_REFERENCE_FIELDS:
        assert f"`{field}`" in candidate_shape
    for role in ["relevant", "distractor", "no_answer_boundary", "ambiguous", "unsafe", "edition_mismatch", "environment_boundary"]:
        assert f"`{role}`" in candidate_shape
    assert "consultant_wordml" in candidate_shape
    assert "garant_odt_metadata" in candidate_shape
    assert "never the excerpt text" in candidate_shape
    assert "not product search results" in candidate_shape
    assert "or evidence that parser coverage is complete" in candidate_shape


def test_provenance_redaction_and_forbidden_payloads_exclude_raw_material() -> None:
    text = contract_text()
    provenance = section(text, "## Provenance")
    redaction = section(text, "## Redaction")
    forbidden = section(text, "## Forbidden payloads")

    for safe_item in ["source contract path", "source fixture path", "source artifact SHA-256", "parser hierarchy record ID", "evidence path IDs"]:
        assert safe_item in provenance
    for field in REQUIRED_REDACTION_FIELDS:
        assert f"`{field}`" in redaction
        assert "`false`" in redaction
    for blocked in [
        "raw legal text",
        "raw query text",
        "raw query prompts",
        "managed GigaChat or GigaChat API",
        "managed embedding API",
        "credentials",
        "raw embedding arrays",
        "raw FalkorDB rows",
        "generated legal advice",
        "absolute paths",
        "product-facing retrieval quality claims",
    ]:
        assert blocked in forbidden


def test_diagnostics_are_categorical_safe_and_agent_inspectable() -> None:
    text = contract_text()
    diagnostics = section(text, "## Diagnostics")

    assert "deterministic, categorical, compact, and safe" in diagnostics
    for field in ["code", "severity", "field_path", "artifact_path", "corpus_id", "query_label_id", "reference_id", "coverage_class_id", "source_case_id"]:
        assert f"`{field}`" in diagnostics
    for code in REQUIRED_DIAGNOSTIC_CODES:
        assert f"`{code}`" in diagnostics
    assert "Diagnostics must not include raw legal text" in diagnostics
    assert "absolute paths" in diagnostics
    assert "`.gsd/exec` references" in diagnostics


def test_explicit_limits_exclude_managed_api_fallback_and_runtime_claims() -> None:
    text = contract_text()
    limits = section(text, "## Explicit limits")

    assert "not a runtime benchmark" in limits
    assert "does not run embeddings" in limits
    assert "does not call FalkorDB" in limits
    assert "does not parse raw ODT/WordML documents" in limits
    assert "does not close any readiness gate" in limits
    assert "Local/open-weight runtime benchmarking belongs to S03" in limits
    assert "Managed GigaChat" in limits
    assert "managed embedding API fallback" in limits
    assert "must not silently fall back to a managed API" in limits


def test_s03_handoff_fields_are_actionable_and_keep_gate_open() -> None:
    text = contract_text()
    handoff = section(text, "## S03 handoff")

    for field in [
        "manifest_path",
        "builder_check_command",
        "schema_version",
        "corpus_id",
        "allowed_runtime_model_boundary",
        "managed_api_allowed",
        "managed_embedding_api_fallback_allowed",
        "raw_payload_persistence_allowed",
        "gate_g011_status",
        "quality_claim_scope",
    ]:
        assert f"`{field}`" in handoff
    assert "`prd/retrieval/fixtures/representative_retrieval_corpus_manifest.json`" in handoff
    assert "`uv run python scripts/build_representative_retrieval_corpus_manifest.py --check`" in handoff
    assert "Local/open-weight only" in handoff
    assert "Must be `false`" in handoff
    assert "Must state `open`" in handoff
    assert "not product retrieval quality" in handoff


def test_non_claims_keep_gate_g011_open_and_avoid_legal_authority() -> None:
    text = contract_text()
    non_claims = section(text, "## Non-claims")

    for non_claim in REQUIRED_NON_CLAIMS:
        assert non_claim in non_claims
    assert "`GATE-G011` remains open until later validation explicitly confirms full gate criteria" in non_claims


def test_contract_rejects_overclaims_and_forbidden_persistence_language() -> None:
    text = contract_text()

    for phrase in FORBIDDEN_OVERCLAIM_PHRASES + FORBIDDEN_PERSISTENCE_PHRASES:
        assert phrase not in text
    for token in FORBIDDEN_PATH_TOKENS:
        if token in {".gsd/exec", ".planning/", ".audits/"}:
            assert f"`{token}`" in text
            assert f"{token} outputs" not in text
            assert f"{token} references" in text or f"must not read `.gsd/`, `.planning/`, `.audits/`" in text
        else:
            assert token not in text


def test_verification_hook_names_this_contract_test_only() -> None:
    text = contract_text()
    verification = section(text, "## Verification hook")

    assert "uv run pytest tests/test_representative_retrieval_corpus_contract.py -q" in verification
    assert "uv run python scripts/build_representative_retrieval_corpus_manifest.py --check" in verification
