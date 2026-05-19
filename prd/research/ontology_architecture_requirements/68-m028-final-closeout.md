---
milestone: M028-yejcai
slice: S04
status: final-closeout
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M028 Final Closeout

## Final decision

```text
accept_bounded
```

M028 closes as bounded remediation evidence: one safe source-order neighborhood signal improved the controlled materialized descriptor scoring metrics relative to the immutable M027 baseline.

M028 does not validate R035.

## What M028 tested

M028 tested exactly one representation change:

```text
selected_signal: safe_source_order_neighborhood_bucket
```

The proof chain was:

```text
M027 materialized descriptor inputs
-> add one safe source-order neighborhood signal
-> local USER-bge-m3 descriptor scoring
-> compare to immutable M027 baseline
-> independent bounded review
```

## Accepted evidence

### S01 — Contract

S01 locked the M027 baseline and selected exactly one signal.

```text
m027_baseline_locked: true
single_signal_change_only: true
selected_signal: safe_source_order_neighborhood_bucket
```

### S02 — Enhanced descriptor bridge

S02 produced verified enhanced descriptor inputs:

```text
schema_version: safe-structural-descriptor-remediation-inputs/v1
representation_kind: safe_materialized_descriptor_with_neighborhood_v1
query_descriptor_count: 6
candidate_descriptor_count: 6
```

The added signal was derived from safe materialized source-order metadata only.

### S03 — Enhanced scoring

S03 scored the enhanced descriptors locally:

```text
schema_version: safe-structural-descriptor-remediation-scoring-proof/v1
scoring_mode: local_user_bge_m3_safe_structural_descriptor_similarity_v1
score_count: 36
outcome_classification: improvement
```

Runtime boundary:

```text
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

Metrics:

```text
mrr: 0.916667
recall_at_1: 0.833333
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

Deltas vs M027:

```text
delta_vs_m027_mrr: 0.236112
delta_vs_m027_recall_at_1: 0.333333
delta_vs_m027_recall_at_3: 0.166667
delta_vs_m027_runtime_boundary_confirmed: 0.0
```

### S04 — Independent review

Review verdict:

```text
PASS_BOUNDED
```

Final review conclusion:

```text
one-signal contract followed
runtime boundary passed
label separation passed
bounded metrics improved
self-confirming risk remains material
R035 validation rejected
```

## Self-confirming-risk disposition

The improvement is accepted as bounded representation evidence only. It may be partly self-confirming because source-order neighborhood buckets can align with the same six-candidate materialized sequence used by the post-scoring labels.

This risk does not invalidate the artifact-control proof, but it blocks product retrieval-quality and R035 validation claims.

## Requirement outcomes

### R035

```text
status: active
validation: not validated by M028
```

M028 advances R035 with bounded evidence that one safe structural signal can improve controlled descriptor scoring, but R035 remains unvalidated because the proof is still a small controlled fixture and not a broad architecture/product validation.

### R038

```text
status: active
validation: standing independent proof-review gate remains required
```

M028 confirms the R038 gate: independent review separated bounded metric improvement from overclaiming retrieval quality.

## Final non-claims

M028 does not prove:

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

## Recommended next work

Next work should not promote M028 to production readiness. It should choose one of these bounded paths:

```text
held-out materialized source-order generalization
second independent safe structural signal in a new one-signal cycle
larger controlled materialization set before another scoring acceptance
```

All future cycles must preserve:

```text
one representation change per cycle
post-scoring-only labels
local/open-weight runtime only
no raw legal text in durable artifacts
no raw vector persistence
independent review before acceptance
```

## Final verification status

```text
S02 enhanced descriptor verifier passed
S03 scoring verifier completed
S02/S03 focused tests passed
ruff passed
architecture verifier passed
GSD sync drift passed
S04 review markers passed
S04 closeout markers passed
```

## Final disposition

```text
M028 may close as bounded improvement evidence.
R035 remains active and not validated.
R038 remains active as standing review gate.
```
