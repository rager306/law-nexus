---
milestone: M030-hwfnq0
slice: S04
status: independent-review
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# M030 Independent Proof Review

## Verdict

```text
PASS_BOUNDED_NEGATIVE_CONTROL
```

M030 passes as bounded negative-control evidence that adding the constant `safe_source_record_cardinality_bucket` signal did not improve the controlled materialized descriptor scoring fixture relative to M027, matched M029, and scored below M028.

M030 does not validate R035 and does not prove product retrieval quality.

## Reviewed evidence

```text
74-source-record-cardinality-signal-contract.md
75-source-record-cardinality-signal-inputs-proof.md
76-source-record-cardinality-signal-scoring-proof.md
source_record_cardinality_signal_scoring_proof.json
fixtures/source_record_cardinality_signal_inputs.json
```

## Review questions

### Q1. Was there exactly one representation change?

Verdict: pass.

Evidence:

```text
selected_signal: safe_source_record_cardinality_bucket
added_descriptor_fields: [safe_source_record_cardinality_bucket]
single_signal_change_only: true
```

M030 adds one field to the M027 materialized descriptor representation.

### Q2. Were prior M028 and M029 signals excluded?

Verdict: pass.

Evidence:

```text
forbidden_prior_signal: safe_source_order_neighborhood_bucket
forbidden_prior_signal: safe_anchor_family_bucket
source_order_index_used: false
prior_signals_used: false
```

Verifier and tests reject prior signal leakage and source-order leakage in descriptor records and scoring inputs.

### Q3. Was the selected signal derived safely?

Verdict: pass for bounded artifact safety.

Allowed derivation inputs:

```text
materialized_candidate_ref
source_record_ids
source_anchor_sha256
```

Rejected derivation inputs:

```text
source_order_index
safe_source_order_neighborhood_bucket
safe_anchor_family_bucket
source_anchor_ref suffix family
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

The builder derives query cardinality through matching `materialized_candidate_ref` to candidate `source_record_ids` metadata.

### Q4. Was constant-signal risk handled honestly?

Verdict: pass.

Evidence:

```text
source_record_cardinality_single: 12
constant_signal_risk: true
```

M030 did not hide that the selected signal is constant across the 6 query and 6 candidate descriptors. This supports negative-control interpretation rather than improvement interpretation.

### Q5. Did scoring preserve label separation and local runtime boundaries?

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

### Q6. Did the selected signal improve bounded metrics?

Verdict: no.

M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
```

M030 observed metrics:

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

Deltas vs M029:

```text
delta_vs_m029_mrr: 0.0
delta_vs_m029_recall_at_1: 0.0
delta_vs_m029_recall_at_3: 0.0
```

Outcome classification:

```text
neutral_vs_m027_below_m028_matches_m029
```

Disposition:

```text
accept_bounded_as_negative_control
reject_as_improvement_signal
```

### Q7. What does this imply about M028 self-confirming risk?

Verdict: bounded diagnostic signal.

M030 does not prove M028 is generally valid. It does show that another safe one-signal change, this time a constant cardinality token, did not reproduce M028's improvement.

Together with M029, this strengthens the bounded diagnosis that M028's gain was not caused by adding any arbitrary safe structural token. It does not eliminate M028 self-confirming risk because all three cycles still use the same controlled six-candidate materialized fixture and post-scoring labels.

## Findings

### Finding 1 — one-signal contract was followed

Severity: positive evidence.

Disposition: accepted.

### Finding 2 — prior M028/M029 signals were excluded from descriptor records and scoring inputs

Severity: positive control evidence.

Disposition: accepted.

### Finding 3 — local runtime and label separation controls passed

Severity: positive evidence.

Disposition: accepted.

### Finding 4 — cardinality signal was constant

Severity: expected limitation.

Disposition: accepted as negative-control setup, not as improvement setup.

### Finding 5 — cardinality signal did not improve over M027 and matched M029

Severity: negative-control evidence.

Disposition: accept bounded negative control; reject as improvement signal.

### Finding 6 — cardinality signal scored below M028

Severity: diagnostic evidence.

Disposition: M028 remains the stronger of these tested signals for the controlled fixture, but this does not validate R035.

### Finding 7 — self-confirming risk remains material

Severity: limitation.

Disposition: does not block bounded negative-control closeout, but blocks product retrieval-quality and R035 validation claims.

### Finding 8 — R035 remains active and not validated

Severity: validation blocker.

Disposition: keep R035 active/not validated.

### Finding 9 — R038 remains active

Severity: process-validating.

Disposition: keep R038 as standing independent proof-review gate.

## Accepted claims

```text
M030 tested exactly one safe source-record-cardinality representation change.
M030 preserved raw-text, label, vector, managed API, path, and generated-output boundaries.
M030 used local USER-bge-m3 scoring with observed vector dimension 1024.
M030 produced neutral metrics relative to M027 and M029 and lower metrics than M028.
M030 provides bounded negative-control evidence for a constant safe cardinality signal in this fixture.
```

## Rejected claims

```text
safe_source_record_cardinality_bucket is an improvement signal for this fixture.
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
final_review_verdict: PASS_BOUNDED_NEGATIVE_CONTROL
recommended_final_decision: accept_bounded_as_negative_control
r035_status: active_not_validated
r038_status: active_standing_gate
```
