---
milestone: M021-qk4lze
slice: S04
status: contract
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# EvidenceSpan Golden Retrieval Contract

This contract defines the M021/S04 golden retrieval fixture used by later local/open-weight retrieval metrics. It is a fixture construction contract only. It does not run embeddings, rank candidates, query FalkorDB, or answer legal questions.

## Purpose

Create a tracked, citation-safe set of EvidenceSpan/SourceBlock retrieval cases that S05 and S06 can evaluate deterministically. The fixture must preserve expected candidate IDs and failure taxonomy without storing raw legal text, raw vectors, managed-provider payloads, generated legal-answer prose, or temporary runtime paths.

## Output artifact

```text
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
```

Required top-level fields:

- `schema_version`: `evidence-span-golden-retrieval-cases/v1`
- `fixture_artifact`: repo-relative path to the fixture
- `generated_by`: `M021/S04`
- `milestone_id`: `M021-qk4lze`
- `slice_id`: `S04`
- `non_authoritative`: `true`
- `source_artifacts`: tracked repo-relative source artifacts with sha256 hashes
- `required_case_classes`: required case-class names
- `allowed_expected_results`: allowed expected result values
- `diagnostic_taxonomy`: deterministic diagnostic codes
- `cases`: golden cases
- `non_claims`: explicit proof boundaries

## Source anchors

The fixture may reference these existing tracked artifacts as source evidence:

```text
prd/retrieval/fixtures/offline_citation_retrieval_cases.json
prd/retrieval/fixtures/local_retrieval_quality_benchmark.json
prd/retrieval/fixtures/real_artifact_retrieval_cases.json
prd/parser/consultant_hierarchy_records.json
prd/parser/parser_staging_graph.json
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json
```

The fixture must not reference `.gsd/exec`, absolute paths, temporary paths, raw source extracts, provider payloads, or raw vectors.

## Required case classes

The fixture must contain at least one case for each class:

| Case class | Intent | Expected result |
| --- | --- | --- |
| `positive_evidence_span` | A query whose expected relevant candidate is a known EvidenceSpan/SourceBlock-backed retrieval candidate. | `selected` |
| `positive_source_block_marker` | A query whose expected relevant candidate is marker/source-block-level evidence rather than exact record lookup. | `selected` |
| `stale_temporal_negative` | A query scoped to a date/edition where an otherwise plausible candidate is stale or wrong-edition. | `rejected` |
| `ambiguous_candidate_set` | A query where multiple plausible candidates must be surfaced as ambiguous rather than silently selected. | `ambiguous` |
| `unsupported_scope` | A query whose requested scope is outside the verified fixture/source boundary. | `unsupported` |
| `scoped_no_answer` | A scoped query where no candidate should be returned. | `no_answer` |

## Case shape

Each case must include:

- `case_id`: deterministic `CASE-M021-S04-*`
- `case_class`: one required class
- `non_authoritative`: `true`
- `query`:
  - `query_id`: deterministic `QUERY-M021-S04-*`
  - `query_kind`: one of the allowed fixture query kinds
  - `query_text_sha256`: hash of external query text, not query text itself
  - `scope_id`
  - `as_of_date`
  - `expected_result`
- `expected_candidate_ids`: relevant candidate IDs expected for positive/ambiguous cases
- `expected_rejected_candidate_ids`: stale/unsafe/rejected candidate IDs where applicable
- `expected_diagnostic_codes`: deterministic diagnostic codes expected for non-positive cases
- `source_artifact_refs`: repo-relative artifact paths backing the case
- `source_record_ids`: proof-local source IDs, if applicable
- `citation_requirements`:
  - `requires_evidence_span_id`
  - `requires_source_block_id`
  - `requires_citation_key`
  - `requires_act_edition_id`
- `candidates`: zero or more candidate descriptors

Candidate descriptors must use safe IDs only:

- `candidate_id`
- `source_artifact`
- `source_case_id`
- `source_record_ids`
- `evidence_span_id`
- `source_block_id`
- `citation_key`
- `act_edition_id`
- `expected_label`: `relevant`, `stale`, `ambiguous`, `unsupported`, `no_answer`, or `unsafe`
- `selection_reason`

## Diagnostic taxonomy

Allowed diagnostic codes:

- `stale_temporal_candidate`
- `ambiguous_candidate_set`
- `unsupported_scope`
- `scoped_no_answer`
- `unsafe_payload_rejected`
- `missing_evidence_span`
- `missing_source_block`
- `source_anchor_missing`
- `invalid_expected_candidate_reference`
- `unsafe_fixture_payload`

## Redaction and safety rules

The fixture and durable proof artifacts must not contain:

- raw legal text or source excerpts;
- raw vectors or embedding arrays;
- managed provider payloads or provider response bodies;
- generated legal-answer prose;
- secrets or tokens;
- absolute paths;
- temporary paths;
- `.gsd/exec` paths;
- runtime FalkorDB rows.

Source hashes and query hashes are allowed. Proof-local IDs such as `EV-*`, `SB-*`, `CIT-*`, and `HIER-*` are allowed when they are sourced from tracked fixture artifacts.

## Non-claims

The S04 fixture does not claim:

- product retrieval quality;
- local embedding quality;
- graph-filtered retrieval quality;
- production FalkorDB readiness;
- parser completeness;
- legal-answer correctness;
- final legal hierarchy correctness;
- graph-vector/HNSW behavior;
- pilot or 1000-document readiness;
- R035 validation.

## Verification

S04 must provide a verifier that fails closed when:

- a required case class is missing;
- an unsupported case class or expected result appears;
- IDs are duplicated or do not use deterministic prefixes;
- a source artifact path is missing or has a wrong sha256;
- an expected candidate ID does not exist in the case candidates;
- a non-positive case lacks expected diagnostics;
- forbidden fields or unsafe fragments appear anywhere in the fixture;
- non-claims are missing.
