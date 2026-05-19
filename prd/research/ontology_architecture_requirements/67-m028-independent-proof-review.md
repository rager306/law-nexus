---
milestone: M028-yejcai
slice: S04
status: independent-review
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M028 Independent Proof Review

## Verdict

```text
PASS_BOUNDED
```

M028 passes as bounded evidence that adding exactly one safe structural signal, `safe_source_order_neighborhood_bucket`, improves the controlled materialized descriptor scoring fixture relative to M027.

M028 does not validate R035 and does not prove product retrieval quality.

## Reviewed evidence

```text
64-safe-structural-descriptor-remediation-contract.md
65-safe-structural-descriptor-remediation-inputs-proof.md
66-safe-structural-descriptor-remediation-scoring-proof.md
safe_structural_descriptor_remediation_inputs.json
safe_structural_descriptor_remediation_scoring_proof.json
```

## Review questions

### Q1. Was there exactly one representation change?

Verdict: pass.

Evidence:

```text
selected_signal: safe_source_order_neighborhood_bucket
added_descriptor_fields: [safe_source_order_neighborhood_bucket]
single_signal_change_only: true
```

The original M027 descriptor fields remain unchanged. S02/S03 add only the selected source-order neighborhood signal.

### Q2. Was the selected signal derived safely?

Verdict: pass for bounded artifact safety.

Allowed derivation inputs:

```text
materialized_candidate_ref
source_order_index
candidate_kind
source_anchor_ref
source_anchor_sha256
```

Rejected derivation inputs:

```text
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

The builder uses safe materialized source-order metadata and does not inspect raw source text.

### Q3. Did scoring preserve label separation and local runtime boundaries?

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

### Q4. Did the selected signal improve the bounded metrics?

Verdict: pass for bounded fixture delta.

M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
```

M028 observed metrics:

```text
mrr: 0.916667
recall_at_1: 0.833333
recall_at_3: 1.0
```

Deltas:

```text
delta_vs_m027_mrr: 0.236112
delta_vs_m027_recall_at_1: 0.333333
delta_vs_m027_recall_at_3: 0.166667
```

Outcome classification:

```text
improvement
```

### Q5. Is there self-confirming risk?

Verdict: material risk, bounded acceptable.

Risk:

```text
source-order neighborhood buckets may align strongly with the small controlled label set because labels identify the same materialized candidate IDs from the same six-candidate sequence.
```

Mitigations:

```text
signal was selected before scoring in S01
exactly one signal was added
labels remained post-scoring-only
M027 baseline was immutable
all candidates were ranked for each query
negative/positive deltas were recorded without threshold promotion
```

Residual limitation:

```text
The improvement may not generalize beyond this controlled materialized descriptor fixture.
```

Disposition:

```text
accept_bounded, not retrieval-quality acceptance
```

## Findings

### Finding 1 — one-signal contract was followed

Severity: positive evidence.

Disposition: accepted.

### Finding 2 — local runtime and label separation controls passed

Severity: positive evidence.

Disposition: accepted.

### Finding 3 — scoring improved vs M027 baseline

Severity: positive bounded evidence.

Disposition: accepted as controlled representation evidence only.

### Finding 4 — self-confirming risk remains material

Severity: limitation.

Disposition: does not block bounded acceptance, but blocks R035 validation and product retrieval-quality claims.

### Finding 5 — R035 remains active and not validated

Severity: validation blocker.

Disposition: keep R035 active/not validated.

### Finding 6 — R038 remains active

Severity: process-validating.

Disposition: keep R038 as standing independent review gate.

## Accepted claims

```text
M028 tested exactly one safe structural representation change.
M028 preserved raw-text, label, vector, managed API, path, and generated-output boundaries.
M028 improved controlled materialized descriptor scoring metrics over M027 baseline.
M028 provides bounded evidence that safe source-order neighborhood structure can help this fixture.
```

## Rejected claims

```text
R035 is validated.
Product retrieval quality is proven.
Parser completeness is proven.
Legal-answer correctness is proven.
Legal interpretation authority is established.
Production ETL readiness is proven.
Graph-vector or HNSW behavior is proven.
Pilot readiness is proven.
Managed embedding API authorization is proven.
```

## Final recommendation

```text
final_decision: accept_bounded
r035_status: active_not_validated
r038_status: active_standing_gate
next_cycle: test generalization or a second independent safe signal only in a new milestone
```
