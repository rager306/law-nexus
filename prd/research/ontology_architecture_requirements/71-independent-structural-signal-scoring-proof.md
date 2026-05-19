---
milestone: M029-yfyh51
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# Independent Structural Signal Scoring Proof

S03 scored the M029 independent anchor-family descriptor representation locally.

## Scored representation

```text
schema_version: independent-structural-signal-scoring-proof/v1
representation_kind: safe_materialized_descriptor_with_anchor_family_v1
selected_signal: safe_anchor_family_bucket
forbidden_reused_signal: safe_source_order_neighborhood_bucket
scoring_mode: local_user_bge_m3_independent_anchor_family_similarity_v1
score_count: 36
status: completed
```

The M028 source-order neighborhood signal remains forbidden as a descriptor or scoring input.

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

M029 independent anchor-family result:

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

Outcome classification:

```text
neutral_vs_m027_below_m028
```

## Interpretation

The independent `safe_anchor_family_bucket` signal did not improve over the M027 materialized descriptor baseline. It also scored below the M028 `safe_source_order_neighborhood_bucket` result.

This is useful comparative evidence: M028's improvement is not reproduced by this independent safe anchor-family signal alone.

This does not prove that M028 is generally valid. It only shows that, in this controlled six-candidate fixture, anchor-family structure did not add useful ranking signal beyond M027.

## Verification evidence

The following checks passed in the current session:

```text
scoring script: pass
focused regression tests: 16 passed
LSP diagnostics: no diagnostics for scoring script and tests
```

The focused tests verify:

```text
checked-in proof boundaries
36 scored rows
post-scoring-only labels
no labels in descriptor inputs
no reused M028 signal in descriptor records/tokens
metric recomputation from scores plus labels
expected-answer leakage rejection
injected runtime/scores rejection without test flag
test-only injection cannot write acceptance proof
managed API rejection
network rejection
raw vector persistence rejection
label boundary rejection
source_order_index rejection
reused M028 signal rejection
unsafe string rejection
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

S04 should independently review whether this neutral/below-M028 outcome changes the M029 decision. The likely bounded interpretation is that `safe_anchor_family_bucket` is weaker than M028's source-order neighborhood signal for this fixture, and therefore should not be accepted as a replacement improvement signal.

S04 must still consider whether this result increases or decreases self-confirming-risk concerns around M028.

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
