---
milestone: M023-9rfkrs
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# Observed Retrieval Proof Remediation Contract

M023 exists to remediate the proof-quality gap found after M022: representative metrics must not be accepted when they are computed only from fixture-encoded expectations. Future retrieval-quality evidence must distinguish expected fixture data, provenance data, observed retrieval outputs, runtime boundary checks, and independent proof review.

## Triggering evidence

The M022 independent proof review is the source of this remediation contract:

```text
prd/research/ontology_architecture_requirements/33-m022-independent-proof-review.md
```

High finding from that review:

```text
metrics are fixture-derived, not observed retrieval-derived
```

M022 proved a useful but narrower result:

```text
fixture-derived deterministic metrics passed, and the approved local runtime boundary was separately confirmed.
```

M022 did not prove:

```text
per-case model retrieval/ranking over the representative corpus.
```

## Purpose

M023 must answer this narrower question:

```text
Can LegalGraph produce a safe observed-output proof where candidate rankings and diagnostics are emitted as observed artifacts, then compared against expected EvidenceSpan fixture answers, without storing raw legal text, raw query text, raw vectors, provider payloads, or generated answer prose?
```

## Required separation of evidence classes

M023 artifacts must keep these evidence classes separate:

| Evidence class | Meaning | Must not substitute for |
| --- | --- | --- |
| Expected fixture | Safe expected candidate IDs, rejected IDs, labels, diagnostics, and case classes. | Observed retrieval output. |
| Query provenance | Safe registry proving a query hash/template relation without raw query text. | Raw query text or generated query prose. |
| Source provenance | Safe validation that source/candidate IDs exist in declared source artifacts where feasible. | Mere source-file path/hash existence. |
| Runtime boundary | Local/open-weight model availability, vector dimension, and no managed API/raw-vector/network flags. | Per-case ranking success. |
| Observed output | Ranked candidate IDs and emitted diagnostics produced by the retrieval path. | Expected fixture ranks/labels. |
| Metrics comparison | Metrics computed by comparing observed outputs to expected fixture fields. | Fixture-derived metrics alone. |
| Independent proof review | External read-only review of tests, mocks, hardcodes, bare artifacts, and overclaim risk. | Implementation-authored success reports. |

## Safe query provenance requirement

Raw query text remains excluded. Instead, S02 must provide a tracked query provenance registry with safe fields such as:

- `query_id`;
- `query_kind`;
- `query_text_sha256`;
- `redacted_template_id`;
- `controlled_terms` using safe IDs or bounded vocabulary only;
- `normalization_profile`;
- `hash_algorithm`;
- `expected_case_id`;
- `source_artifact_refs`.

The verifier must reject:

- unregistered query hashes;
- duplicate query IDs;
- malformed hashes;
- registry entries with raw query text;
- generated query/Cypher text;
- external provider payloads;
- `.gsd/exec` paths as durable registry anchors.

## Source provenance requirement

S02 must strengthen provenance beyond source path and SHA-256 existence. Where the referenced fixture format is parseable, the verifier must confirm that candidate references are present in the declared source artifact.

Minimum checks:

- every `source_artifact` is tracked and repo-relative;
- every declared artifact hash matches;
- every candidate `source_case_id` is checked against the source artifact when that artifact has case IDs;
- every candidate `source_record_id` is checked against the source artifact when that artifact has record IDs;
- every citation-bearing ID that can be mapped from the source artifact is checked;
- unverifiable source formats must be reported with an explicit bounded diagnostic, not silently accepted as fully proven.

Required failure examples:

- source file exists and hash matches but `source_case_id` is bogus;
- `source_record_ids` are bogus;
- candidate citation IDs drift from source artifact values where source artifact exposes them.

## Observed retrieval output requirement

S03 must produce or consume an observed-output artifact that is distinct from the expected fixture. It must include safe observed fields only:

- `case_id`;
- `query_id`;
- `observed_ranked_candidate_ids`;
- `observed_diagnostic_codes`;
- `retrieval_mode`;
- `runtime_boundary_ref`;
- `candidate_source_ref`;
- `observation_status`;
- redaction flags;
- non-claims.

The observed-output artifact must not include:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors or embedding arrays;
- external provider payloads;
- generated answer prose;
- generated query/Cypher text;
- secrets;
- absolute paths;
- temporary paths;
- `.gsd/exec` durable anchors;
- raw FalkorDB rows.

## Metrics comparison requirement

S03 metrics must be computed by comparing observed outputs against expected fixture fields.

Blocked conditions:

- metrics computed directly from expected fixture ranks/labels without observed output;
- observed ranked candidates missing for selected cases;
- observed diagnostics missing for negative/boundary cases;
- observed output copied mechanically from expected fixture fields without a declared retrieval mode and provenance boundary;
- runtime boundary confirmed but no observed-output artifact exists;
- injected runtime JSON used as acceptance proof rather than unit-test support.

Allowed unit-test support:

- injected runtime JSON for fast negative/edge tests;
- synthetic observed-output copies only when the test name and assertion prove the evaluator rejects or accepts a specific controlled condition.

Acceptance proof must include a real observed-output artifact and a final verifier run without relying solely on injected runtime JSON.

## Runtime boundary

Allowed runtime boundary remains:

```text
deepvk/USER-bge-m3
local_open_weight
observed_vector_dimension: 1024
```

Managed embedding APIs, GigaChat/GigaEmbeddings fallback, hosted LLMs, remote vector services, and network downloads remain excluded. Raw vectors must not be persisted.

Runtime confirmation is necessary but insufficient. It proves only environment/model boundary, not retrieval quality.

## Diagnostic taxonomy

M023 verifiers should use these diagnostics where applicable:

- `query_registry_verified`
- `query_hash_unregistered`
- `source_provenance_verified`
- `source_case_missing`
- `source_record_missing`
- `citation_binding_missing`
- `observed_output_present`
- `observed_output_missing`
- `observed_output_self_confirming`
- `runtime_confirmed`
- `runtime_blocked`
- `managed_api_forbidden`
- `raw_vector_persistence_forbidden`
- `metric_comparison_verified`
- `metric_mismatch`
- `overclaim_rejected`
- `independent_review_passed`
- `independent_review_findings_open`

## Independent proof-review gate

R038 requires an independent review before closeout. S04 must run at least one subagent review with no code edits. The reviewer must inspect:

- whether tests are non-vacuous;
- whether mocks replace the proof;
- whether observed outputs are actually distinct from expected fixture data;
- whether source/query provenance is independently auditable;
- whether reports overstate evidence;
- whether high/medium findings are remediated or explicitly deferred.

Milestone closeout must include a tracked proof-review report. High findings should block closeout unless the milestone explicitly scopes them as non-goals and records follow-up requirements.

## Requirement lifecycle boundary

M023 can advance R038 and can advance R035 with stronger proof-quality controls. It must not validate R035 unless all remaining R035 proof gates are closed, including parser-to-EvidenceSpan materialization, product retrieval quality, legal-answer correctness, graph-vector/HNSW or hybrid retrieval behavior, production FalkorDB behavior, pilot readiness, and registry extractor/regenerated registry outputs.

## Non-claims

M023 does not claim by contract:

- R035 validation;
- R037 validation;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- bulk-loader production readiness;
- pilot or 1000-document readiness;
- managed embedding API authorization.

## S01 acceptance criteria

This contract is accepted only if a marker verification confirms:

- it cites the M022 independent review;
- it states metrics must be observed-output-derived;
- it separates expected fixture, provenance, runtime boundary, observed output, metrics comparison, and independent review;
- it requires safe query provenance;
- it requires source provenance checks beyond path/hash;
- it requires an independent proof-review gate;
- it preserves R035 non-validation and all non-claims.
