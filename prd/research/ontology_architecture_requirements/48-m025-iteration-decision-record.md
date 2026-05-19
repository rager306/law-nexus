---
milestone: M025-50be7n
slice: S04
status: decision
verdict: revise
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M025 Iteration Decision Record

## Decision

```text
revise
```

`safe_semantic_descriptor_v1` is not accepted as-is. It is also not rejected or blocked. The S03 evidence is useful and positive, but the pre-S04 review found enough self-confirming descriptor risk to require a controlled revision cycle before acceptance.

## Inputs

S01 iteration contract:

```text
prd/research/ontology_architecture_requirements/44-local-semantic-scoring-iteration-contract.md
```

S02 descriptor input proof:

```text
prd/research/ontology_architecture_requirements/45-semantic-descriptor-inputs-proof.md
```

S03 descriptor scoring proof:

```text
prd/research/ontology_architecture_requirements/46-semantic-descriptor-scoring-proof.md
```

Pre-S04 self-confirming risk review:

```text
prd/research/ontology_architecture_requirements/47-m025-self-confirming-risk-review.md
```

## Observed S03 metrics

M025 descriptor scoring produced positive deltas against M024:

```text
mrr: 1.0
delta_mrr: 0.125

recall_at_1: 1.0
delta_recall_at_1: 0.25

recall_at_3: 1.0
delta_recall_at_3: 0.0

positive_with_distractor_relevant_first: 1.0
delta_positive_with_distractor_relevant_first: 1.0

runtime_boundary_confirmed: 1.0
delta_runtime_boundary_confirmed: 0.0
```

S03 disposition hint:

```text
accept_candidate_pending_review
```

## Why not accept

The reviewer found `REQUEST_CHANGES`. The positive metrics are partly self-confirming because descriptor choices encode fixture-specific outcome semantics.

Main concern:

```text
query_intent:prefer_granular_marker_over_broad_unit
```

This descriptor explains the exact positive-with-distractor win. It is plausible as a structural retrieval preference, but it is also close to the expected ordering rule for the only distractor case.

Additional concern:

```text
ambiguous_candidates_expected
no_answer_expected
unsupported_scope_expected
```

These enum values are outcome-like. They are not expected IDs or ranks, but they weaken the evidence that the descriptor schema is neutral.

## Why not reject

The reviewer did not find direct expected-label, expected-rank, expected-candidate-list, raw text, raw vector, provider payload, or injected acceptance proof leakage in the scoring path. The descriptor approach remains plausible bounded evidence and improved all target metrics.

## Why not blocked

No runtime, safety, or verifier blocker was found. Scoring is possible under the local USER-bge-m3 boundary, and safety checks pass.

## Required revision

S05 must keep unchanged:

```text
runtime/model: deepvk/USER-bge-m3
fixture: representative M022 corpus
metrics: MRR, recall@1, recall@3, positive-with-distractor-first
threshold policy: M025 S01 contract
```

S05 may change exactly one thing:

```text
descriptor derivation rules
```

The revised descriptor derivation must be pre-registered and derived from non-answer structural fields only.

Forbidden derivation inputs:

```text
expected_label
rank
expected_candidate_ids
expected_rejected_candidate_ids
expected_diagnostic_codes
selection_reason
```

Required neutral enum replacements:

```text
ambiguous_candidates_expected -> ambiguity_resolution_required
unsupported_scope_expected -> scope_outside_supported_corpus
no_answer_expected -> scoped_absence_check_required
```

Required remediation proofs:

1. Descriptor derivation test: fail if generation reads expected answer fields or `selection_reason`.
2. Distractor perturbation test: changing expected IDs must not change descriptors unless structural candidate fields change.
3. Ablation report: recompute or simulate the positive-with-distractor case with `prefer_granular_marker_over_broad_unit` removed or neutralized, then record whether the metric depends on that enum.

## S05 acceptance bar

S05 may restore `accept_candidate_pending_review` only if:

- descriptor verifier passes;
- descriptor scoring still improves over M024 or clearly explains any regression;
- outcome-like enums are removed or neutralized;
- derivation tests prove no expected-answer fields or selection reasons are read;
- ablation/perturbation evidence is recorded;
- S05 proof does not validate R035;
- S06 independent review does not request changes.

## Requirement disposition

### R035

```text
active / not validated
```

M025/S03 advanced R035 with bounded local descriptor scoring evidence, but S04 classifies the first descriptor iteration as `revise`, not `accept`. No R035 validation claim is made.

### R038

```text
active / applied
```

R038 is applied because pre-decision review changed the milestone direction. It remains active for S06 final independent review and future proof-heavy milestones.

## Non-claims

This decision does not claim:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness.

## Next action

Proceed to S05: Descriptor derivation remediation.
