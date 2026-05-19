---
milestone: M030-hwfnq0
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# Source Record Cardinality Signal Contract

M030 tests a third one-signal cycle with a safe structural signal independent from both prior M028 and M029 tested signals.

M030 does not validate R035.

## Selected representation change

M030 selects exactly one signal:

```text
selected_signal: safe_source_record_cardinality_bucket
```

No other descriptor representation change is allowed in M030.

## Explicitly forbidden prior signals

M030 must not use either prior tested signal as an added descriptor field or scoring input:

```text
forbidden_prior_signal: safe_source_order_neighborhood_bucket
forbidden_prior_signal: safe_anchor_family_bucket
```

These prior signals may be mentioned only in contract/review prose as forbidden prior signals. They must not appear in M030 descriptor manifests, descriptor tokens, scoring inputs, or scoring proof scores except as root-level forbidden-signal metadata.

## Signal definition

`safe_source_record_cardinality_bucket` is a bounded enum derived from the cardinality of safe `source_record_ids` associated with a materialized candidate reference.

Allowed values:

```text
source_record_cardinality_single
source_record_cardinality_multiple
source_record_cardinality_unknown
```

Allowed derivation inputs:

```text
materialized_candidate_ref
source_record_ids
source_anchor_sha256
```

Forbidden derivation inputs for M030:

```text
source_order_index
safe_source_order_neighborhood_bucket
safe_anchor_family_bucket
source_anchor_ref suffix family
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

M027 materialized descriptor baseline:

```text
m027_mrr: 0.680555
m027_recall_at_1: 0.5
m027_recall_at_3: 0.833333
m027_runtime_boundary_confirmed: 1.0
```

M028 source-order-neighborhood result:

```text
m028_mrr: 0.916667
m028_recall_at_1: 0.833333
m028_recall_at_3: 1.0
m028_runtime_boundary_confirmed: 1.0
m028_outcome_classification: improvement
```

M029 anchor-family result:

```text
m029_mrr: 0.680555
m029_recall_at_1: 0.5
m029_recall_at_3: 0.833333
m029_runtime_boundary_confirmed: 1.0
m029_outcome_classification: neutral_vs_m027_below_m028
```

M030 must compare against all three.

## Expected schema

S02 descriptor output must use:

```text
schema_version: source-record-cardinality-signal-inputs/v1
representation_kind: safe_materialized_descriptor_with_source_record_cardinality_v1
milestone_id: M030-hwfnq0
```

Required root markers:

```text
selected_signal_field_required: true
forbidden_prior_signals_declared: true
single_signal_change_only: true
m027_baseline_locked: true
m028_baseline_locked: true
m029_baseline_locked: true
r035_non_validation_declared: true
r038_review_required: true
```

## Scoring requirement

S03 must score descriptors with the same local runtime boundary:

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
source_order_index
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
/root/
/tmp/
```

Durable redaction markers must use:

```text
external_payloads_excluded
```

They must not use unsafe alternate vocabulary for provider payload exclusion.

## Acceptance outcomes

M030 final review may choose one of:

```text
accept_bounded_as_improvement
accept_bounded_as_negative_comparison
reject_as_improvement_signal
revise
blocked
```

Acceptance requires independent review and remains bounded to this one signal.

## Expected interpretation

Possible outcomes:

```text
improvement_vs_m027: cardinality may carry useful structural signal
neutral_vs_m027: cardinality is likely redundant or constant for this fixture
regression_vs_m027: cardinality harms this fixture
below_m028: source-order neighborhood remains stronger than cardinality for this fixture
matches_m029: cardinality behaves similarly to anchor-family or base descriptors
```

No outcome validates R035.

## Non-claims

M030 does not prove:

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
safe_source_record_cardinality_bucket derived from safe source-record cardinality only
safe_source_order_neighborhood_bucket absent from descriptor/scoring inputs
safe_anchor_family_bucket absent from descriptor/scoring inputs
source_order_index absent from M030 descriptor records
source_anchor_ref suffix family not used for derivation
no raw text or labels are used
source hashes are recorded
```
