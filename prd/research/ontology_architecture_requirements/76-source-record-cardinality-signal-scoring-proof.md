---
milestone: M030-hwfnq0
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# Source Record Cardinality Signal Scoring Proof

S03 scored the M030 source-record-cardinality descriptor representation locally.

## Scored representation

```text
schema_version: source-record-cardinality-signal-scoring-proof/v1
representation_kind: safe_materialized_descriptor_with_source_record_cardinality_v1
selected_signal: safe_source_record_cardinality_bucket
forbidden_prior_signal: safe_source_order_neighborhood_bucket
forbidden_prior_signal: safe_anchor_family_bucket
scoring_mode: local_user_bge_m3_source_record_cardinality_similarity_v1
score_count: 36
status: completed
```

The M028 source-order neighborhood signal and M029 anchor-family signal remain forbidden as descriptor or scoring inputs.

## Constant-signal boundary

The S02 manifest recorded:

```text
source_record_cardinality_single: 12
constant_signal_risk: true
```

The selected signal is constant across this controlled fixture. S03 therefore treats the result as negative-control evidence unless incidental token interactions change ranking.

## Runtime boundary

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
runtime_boundary_confirmed: 1.0
```

Scoring used local/open-weight runtime only. No managed embedding API was used.

## Label boundary

Evaluation labels remained post-scoring-only:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
```

Expected candidate IDs are allowed only in the separate post-scoring label artifact and are rejected as descriptor/scoring inputs.

## Metrics

M030 source-record-cardinality result:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

Delta vs M027 baseline:

```text
delta_vs_m027_mrr: 0.0
delta_vs_m027_recall_at_1: 0.0
delta_vs_m027_recall_at_3: 0.0
delta_vs_m027_runtime_boundary_confirmed: 0.0
```

Delta vs M028 source-order-neighborhood result:

```text
delta_vs_m028_mrr: -0.236112
delta_vs_m028_recall_at_1: -0.333333
delta_vs_m028_recall_at_3: -0.166667
delta_vs_m028_runtime_boundary_confirmed: 0.0
```

Delta vs M029 anchor-family result:

```text
delta_vs_m029_mrr: 0.0
delta_vs_m029_recall_at_1: 0.0
delta_vs_m029_recall_at_3: 0.0
delta_vs_m029_runtime_boundary_confirmed: 0.0
```

Outcome classification:

```text
neutral_vs_m027_below_m028_matches_m029
```

## Interpretation

The constant `safe_source_record_cardinality_bucket` signal did not improve over the M027 materialized descriptor baseline. It matched M029's anchor-family result and scored below M028's source-order-neighborhood result.

This is useful negative-control evidence: adding a constant safe cardinality token does not reproduce M028's improvement.

This does not prove that M028 is generally valid. It only shows that, in this controlled six-candidate fixture, source-record cardinality does not add useful ranking signal beyond M027.

## Verification evidence

The following checks passed in the current session:

```text
scoring script: pass
focused regression tests: 17 passed
LSP diagnostics: no diagnostics for scoring script and tests
```

The focused tests verify:

```text
checked-in proof boundaries
36 scored rows
post-scoring-only labels
no labels in descriptor inputs
no reused M028 or M029 signal in descriptor records/tokens
metric recomputation from scores plus labels
expected-answer leakage rejection
injected runtime/scores rejection without test flag
test-only injection cannot write acceptance proof
managed API rejection
network rejection
raw vector persistence rejection
label boundary rejection
source_order_index rejection
prior signal rejection
unsafe string rejection
constant-signal proof markers
```

## Redaction and safe artifact boundaries

Durable artifacts preserve:

```text
source_text_excluded: true
query_text_excluded: true
raw_vectors_excluded: true
external_payloads_excluded: true
generated_answer_prose_excluded: true
generated_query_excluded: true
absolute_paths_excluded: true
```

## S04 handoff

S04 should independently review whether this constant-signal result should close as bounded negative-control evidence. The likely disposition is:

```text
accept_bounded_as_negative_control
reject_as_improvement_signal
```

S04 should preserve the R035 non-validation boundary and evaluate how this second neutral cycle affects confidence that M028's improvement is source-order-specific for the controlled fixture.

## Non-claims

S03 does not prove:

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

R035 remains active and not validated. R038 remains the active independent proof-review gate.
