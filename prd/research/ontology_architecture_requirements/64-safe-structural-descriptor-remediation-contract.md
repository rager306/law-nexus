---
milestone: M028-yejcai
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Safe Structural Descriptor Remediation Contract

M028 tests exactly one safe representation change after M027 showed that materialized-derived structural descriptors were too coarse for retrieval-quality acceptance.

The milestone is a bounded remediation cycle. It does not validate R035.

## Immutable M027 baseline

Source proof:

```text
prd/research/ontology_architecture_requirements/materialized_descriptor_scoring_proof.json
```

Baseline scoring mode:

```text
local_user_bge_m3_materialized_descriptor_similarity_v1
```

Baseline metrics:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
score_count: 36
```

Runtime boundary:

```text
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

These baseline values are immutable for M028 delta calculations.

## Selected representation change

M028 selects exactly one signal:

```text
selected_signal: safe_source_order_neighborhood_bucket
```

No other descriptor representation change is allowed in M028.

## Signal definition

`safe_source_order_neighborhood_bucket` is a bounded enum derived from already-safe materialized source order indexes. It represents local structural neighborhood position without reading or persisting source text.

Allowed values:

```text
source_order_neighbor_first
source_order_neighbor_after_source_block
source_order_neighbor_between_evidence_spans
source_order_neighbor_before_late_gap
source_order_neighbor_late
```

Allowed derivation inputs:

```text
materialized_candidate_ref
source_order_index
candidate_kind
source_anchor_ref
source_anchor_sha256
```

The derivation may compare the current candidate order index to adjacent materialized candidate order indexes. It must not inspect raw legal text.

## Unchanged descriptor fields

All existing M027 materialized descriptor fields stay unchanged:

```text
candidate_kind
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
source_order_index_bucket
```

M028 adds only:

```text
safe_source_order_neighborhood_bucket
```

## Required output schema

S02 enhanced descriptor output must use:

```text
schema_version: safe-structural-descriptor-remediation-inputs/v1
representation_kind: safe_materialized_descriptor_with_neighborhood_v1
milestone_id: M028-yejcai
```

Required root markers:

```text
selected_signal_field_required: true
single_signal_change_only: true
m027_baseline_locked: true
r035_non_validation_declared: true
r038_review_required: true
```

## Scoring requirement

S03 must score enhanced descriptors with the same local runtime boundary:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

S03 must compare enhanced metrics against the immutable M027 baseline.

## Evaluation labels

Labels must remain post-scoring-only:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
```

Labels may not be read by the descriptor builder or score generator.

## Forbidden fields

Descriptor inputs, scoring inputs, and durable proof artifacts must reject:

```text
raw_legal_text
raw_text
source_excerpt
source_excerpts
query_text
prompt
user_prompt
provider_payload
provider_response_body
secret
secrets
vector
vectors
embedding
embedding_vector
runtime_row
falkordb_row
generated_answer_prose
generated_query
generated_cypher
legal_advice
llm_reasoning
expected_label
expected_rank
rank
expected_candidate_ids
expected_rejected_candidate_ids
expected_diagnostic_codes
selection_reason
expected_result
```

## Forbidden fragments

Durable artifacts must reject:

```text
Федеральный закон
Статья 
raw_legal_text
source_excerpt
provider_payload
embedding_vector
expected_label
expected_candidate_ids
Bearer 
BEGIN PRIVATE KEY
api_key
.gsd/exec
/root/
/tmp/
```

Durable redaction markers must use:

```text
external_payloads_excluded
```

They must not use unsafe alternate vocabulary for provider payload exclusion.

## Acceptance outcomes

M028 final review may choose one of:

```text
accept_bounded
revise
reject
blocked
```

Acceptance requires independent review and must remain bounded to this one signal.

## Non-claims

M028 does not prove:

```text
R035 validation
parser completeness
product retrieval quality
legal-answer correctness
legal interpretation authority
production ETL readiness
graph-vector or HNSW behavior
hybrid retrieval quality
pilot readiness
managed embedding API authorization
```

## Requirement boundaries

```text
R035: active, not validated by this contract
R038: active, standing independent proof-review gate
```

## S02 handoff

S02 must implement a builder and verifier that prove:

```text
only selected_signal changed
safe_source_order_neighborhood_bucket derived from safe source order structure
no raw text or labels are used
source materialization and descriptor input hashes are recorded
```
