---
milestone: M025-50be7n
slice: S04
status: pre-decision-review
verdict: REQUEST_CHANGES
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M025 Self-Confirming Risk Review

## Verdict

```text
REQUEST_CHANGES
```

The pre-S04 reviewer found that S03 is useful bounded evidence, but `safe_semantic_descriptor_v1` is not ready for `accept` because the perfect metrics are partly self-confirming.

## Summary

S03 did not directly inject `expected_label`, `expected_rank`, `expected_candidate_ids`, or expected candidate lists into the scorer. The normal scoring path encodes descriptor token strings, ranks by observed similarity, and compares expected fixture answers only after scoring.

However, the descriptor design is partly self-confirming because several enum values were derived from fixture outcome semantics and query-specific policy. The key distractor improvement appears strongly tied to a descriptor that states the desired granularity preference.

## Findings

### Medium — distractor improvement depends on expected ordering semantics

The positive-with-distractor win is associated with the query descriptor:

```text
query_intent:prefer_granular_marker_over_broad_unit
```

The relevant candidate carries source-block-marker descriptors, while the distractor carries broader article/evidence-span descriptors. That is plausible as a structural preference, but it is also close to the expected ordering rule for the one distractor case.

Risk:

```text
The primary metric improved from 0.0 to 1.0, but the descriptor may encode the fixture-specific preference that makes the metric pass.
```

### Medium — some enum values encode outcome-like semantics

Reviewer flagged enum names such as:

```text
ambiguous_candidates_expected
no_answer_expected
unsupported_scope_expected
```

These are not literal expected candidate IDs or ranks, but they encode expected outcome semantics and weaken the evidence that descriptors are neutral retrieval features.

Recommended neutral replacements:

```text
ambiguous_candidates_expected -> ambiguity_resolution_required
unsupported_scope_expected -> scope_outside_supported_corpus
no_answer_expected -> scoped_absence_check_required
```

### Medium — tests are strong for safety but weak for self-confirming risk

Current tests reject obvious forbidden fields and unsafe payloads, but they do not prove that descriptor generation avoids expected answer fields or selection reasons.

Required before any `accept` decision:

```text
- descriptor derivation test: fail if generation reads expected_label, rank, expected_candidate_ids, expected_rejected_candidate_ids, or expected_diagnostic_codes;
- distractor perturbation test: prove descriptor strings do not change when expected IDs are changed unless structural candidate fields change;
- ablation report: recompute positive-with-distractor without or neutralizing prefer_granular_marker_over_broad_unit.
```

### Low — perfect metrics apply only to selected-positive ranking

The metrics are bounded to positive selected retrieval cases. They do not prove rejection behavior, unsupported scope behavior, legal-answer correctness, or product retrieval quality.

## Positive evidence

The reviewer also confirmed:

- no direct expected label/rank/candidate-list scoring injection was found;
- scorer uses descriptor-token embeddings in the normal path;
- expected fixture answers are used after scoring for metric comparison;
- CLI blocks injected runtime/scores as acceptance proof unless test-only mode is enabled;
- test-only injected mode cannot write the proof artifact;
- R035 non-validation boundary is explicit.

## Recommended S04 disposition

```text
revise
```

Not `accept`: the primary metric improvement is too dependent on descriptor enums that mirror fixture intent/outcome semantics.

Not `reject`: there is no direct raw expected-answer scoring injection, and the descriptor approach remains plausibly useful bounded evidence.

Not `blocked`: no raw text/vector/provider leakage or verifier bypass was found.

## Recommended next-cycle constraint

Keep runtime/model/fixture/metrics unchanged. Change only descriptor derivation rules so query intent and candidate descriptors are produced from pre-registered non-answer structural fields, not from expected labels, ranks, expected candidate lists, expected rejected candidate lists, expected diagnostic lists, or selection reasons that encode desired ordering.

## Non-claims

This review does not claim:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- parser completeness;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness.
