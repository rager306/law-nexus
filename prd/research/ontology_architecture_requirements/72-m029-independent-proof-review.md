---
milestone: M029-yfyh51
slice: S04
status: independent-review
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# M029 Independent Proof Review

## Verdict

```text
PASS_BOUNDED_NEGATIVE_COMPARISON
```

M029 passes as bounded comparative evidence that the independent `safe_anchor_family_bucket` signal did not improve the controlled materialized descriptor scoring fixture relative to M027 and scored below M028.

M029 does not validate R035 and does not prove product retrieval quality.

## Reviewed evidence

```text
69-independent-structural-signal-contract.md
70-independent-structural-signal-inputs-proof.md
71-independent-structural-signal-scoring-proof.md
independent_structural_signal_scoring_proof.json
fixtures/independent_structural_signal_inputs.json
```

## Review questions

### Q1. Was there exactly one representation change?

Verdict: pass.

Evidence:

```text
selected_signal: safe_anchor_family_bucket
added_descriptor_fields: [safe_anchor_family_bucket]
single_signal_change_only: true
```

The M029 descriptor bridge adds one independent field to the M027 materialized descriptor representation.

### Q2. Was M028's source-order neighborhood signal excluded?

Verdict: pass.

Evidence:

```text
forbidden_reused_signal: safe_source_order_neighborhood_bucket
source_order_index_used: false
forbidden_reused_signal_used: false
```

Verifier and tests reject `safe_source_order_neighborhood_bucket` and `source_order_index` leakage in descriptor records and scoring inputs.

### Q3. Was the selected signal derived safely?

Verdict: pass for bounded artifact safety.

Allowed derivation inputs:

```text
source_anchor_ref
source_anchor_sha256
materialized_candidate_ref
```

Rejected derivation inputs:

```text
source_order_index
safe_source_order_neighborhood_bucket
raw legal text
expected labels
expected candidate IDs
ranks
generated answer prose
generated queries
raw vectors
managed API payloads
absolute paths
```

The builder derives `safe_anchor_family_bucket` from safe anchor-family metadata only.

### Q4. Did scoring preserve label separation and local runtime boundaries?

Verdict: pass.

Evidence:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

Scores are scalar similarities only; no raw vectors are persisted.

### Q5. Did the selected signal improve bounded metrics?

Verdict: no.

M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
```

M029 observed metrics:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
```

Deltas vs M027:

```text
delta_vs_m027_mrr: 0.0
delta_vs_m027_recall_at_1: 0.0
delta_vs_m027_recall_at_3: 0.0
```

Deltas vs M028:

```text
delta_vs_m028_mrr: -0.236112
delta_vs_m028_recall_at_1: -0.333333
delta_vs_m028_recall_at_3: -0.166667
```

Outcome classification:

```text
neutral_vs_m027_below_m028
```

Disposition:

```text
accept_bounded_as_negative_comparison
reject_as_improvement_signal
```

### Q6. What does this imply about M028 self-confirming risk?

Verdict: bounded diagnostic signal.

M029 does not prove M028 is generally valid. It does show that another independent safe structural signal, selected before scoring and evaluated under the same local runtime and label boundaries, did not reproduce M028's improvement.

This weakly supports the hypothesis that M028's improvement was signal-specific to source-order neighborhood in this fixture. It does not eliminate the M028 self-confirming risk because both cycles still use the same controlled six-candidate materialized fixture and post-scoring labels.

## Findings

### Finding 1 — one-signal contract was followed

Severity: positive evidence.

Disposition: accepted.

### Finding 2 — M028 source-order signal was excluded from descriptor records and scoring inputs

Severity: positive control evidence.

Disposition: accepted.

### Finding 3 — local runtime and label separation controls passed

Severity: positive evidence.

Disposition: accepted.

### Finding 4 — anchor-family signal did not improve over M027

Severity: negative comparison evidence.

Disposition: accept bounded negative comparison; reject as improvement signal.

### Finding 5 — anchor-family signal scored below M028

Severity: diagnostic evidence.

Disposition: M028 remains the stronger of these two tested signals for the controlled fixture, but this does not validate R035.

### Finding 6 — self-confirming risk remains material

Severity: limitation.

Disposition: does not block bounded negative-comparison closeout, but blocks product retrieval-quality and R035 validation claims.

### Finding 7 — R035 remains active and not validated

Severity: validation blocker.

Disposition: keep R035 active/not validated.

### Finding 8 — R038 remains active

Severity: process-validating.

Disposition: keep R038 as standing independent proof-review gate.

## Accepted claims

```text
M029 tested exactly one independent safe structural representation change.
M029 preserved raw-text, label, vector, managed API, path, and generated-output boundaries.
M029 used local USER-bge-m3 scoring with observed vector dimension 1024.
M029 produced neutral metrics relative to M027 and lower metrics than M028.
M029 provides bounded negative comparison evidence for safe_anchor_family_bucket in this fixture.
```

## Rejected claims

```text
safe_anchor_family_bucket is an improvement signal for this fixture.
R035 is validated.
Product retrieval quality is proven.
Parser completeness is proven.
Legal-answer correctness is proven.
Legal interpretation authority is established.
Production ETL readiness is proven.
Graph-vector or HNSW behavior is proven.
Hybrid retrieval quality is proven.
Pilot readiness is proven.
Managed embedding API authorization is established.
```

## Review conclusion

```text
final_review_verdict: PASS_BOUNDED_NEGATIVE_COMPARISON
recommended_final_decision: accept_bounded_as_negative_comparison
r035_status: active_not_validated
r038_status: active_standing_gate
```
