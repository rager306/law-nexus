---
milestone: M029-yfyh51
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Independent Structural Signal Contract

M029 tests a second one-signal cycle with an independent safe structural signal. The purpose is to determine whether M028's improvement was specific to source-order neighborhood or whether a different safe structural signal can also provide bounded scoring evidence.

M029 does not validate R035.

## Selected representation change

M029 selects exactly one signal:

```text
selected_signal: safe_anchor_family_bucket
```

No other descriptor representation change is allowed in M029.

## Explicitly forbidden reused signal

M029 must not use the M028 selected signal as a descriptor field or scoring input:

```text
forbidden_reused_signal: safe_source_order_neighborhood_bucket
```

The M028 signal may be mentioned only in review/contract prose as a forbidden prior signal. It must not appear in M029 descriptor manifests, descriptor tokens, scoring inputs, or scoring proof scores.

## Signal definition

`safe_anchor_family_bucket` is a bounded enum derived from the safe source anchor reference family, not from source order neighborhood.

Allowed values:

```text
source_anchor_family_article
source_anchor_family_paragraph
source_anchor_family_unknown
```

Allowed derivation inputs:

```text
source_anchor_ref
source_anchor_sha256
materialized_candidate_ref
```

Forbidden derivation inputs for M029:

```text
source_order_index
safe_source_order_neighborhood_bucket
expected labels
expected candidate IDs
ranks
raw legal text
generated answer prose
generated queries
raw vectors
managed API payloads
absolute paths
```

## Baselines

M027 baseline:

```text
m027_mrr: 0.680555
m027_recall_at_1: 0.5
m027_recall_at_3: 0.833333
m027_runtime_boundary_confirmed: 1.0
```

M028 accepted bounded result:

```text
m028_mrr: 0.916667
m028_recall_at_1: 0.833333
m028_recall_at_3: 1.0
m028_runtime_boundary_confirmed: 1.0
m028_outcome_classification: improvement
```

M029 must compare against both baselines.

## Required output schema

S02 independent descriptor output must use:

```text
schema_version: independent-structural-signal-inputs/v1
representation_kind: safe_materialized_descriptor_with_anchor_family_v1
milestone_id: M029-yfyh51
```

Required root markers:

```text
selected_signal_field_required: true
forbidden_reused_signal_declared: true
single_signal_change_only: true
m027_baseline_locked: true
m028_baseline_locked: true
r035_non_validation_declared: true
r038_review_required: true
```

## Scoring requirement

S03 must score independent-signal descriptors with the same local runtime boundary:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

Labels must remain post-scoring-only:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
```

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

M029 final review may choose one of:

```text
accept_bounded
revise
reject
blocked
```

Acceptance requires independent review and must remain bounded to this one signal.

## Expected interpretation

Possible outcomes:

```text
improvement_vs_m027_and_near_m028: independent structure may be useful
neutral_vs_m027: independent signal is likely redundant
regression_vs_m027: independent signal harms this fixture
below_m028: M028 source-order signal remains stronger for this fixture
```

No outcome validates R035.

## Non-claims

M029 does not prove:

```text
R035 validation
product retrieval quality
parser completeness
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
safe_anchor_family_bucket derived from safe anchor refs only
safe_source_order_neighborhood_bucket absent from descriptor/scoring inputs
source_order_index absent from M029 derivation summary and descriptor records
no raw text or labels are used
source hashes are recorded
```
