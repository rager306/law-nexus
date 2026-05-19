---
milestone: M025-50be7n
slice: S05
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Semantic Descriptor Derivation Remediation Proof

S05 remediated the self-confirming descriptor risk identified in S04. The remediation keeps the M025 runtime, model, fixture, metrics, and threshold policy unchanged while changing only descriptor derivation rules.

## Remediation decision source

S04 decision:

```text
prd/research/ontology_architecture_requirements/48-m025-iteration-decision-record.md
```

S04 required:

- replace outcome-like enum values with neutral structural terms;
- prove descriptor derivation does not read expected answer fields or `selection_reason`;
- prove expected-field perturbations do not alter descriptors;
- run a distractor ablation/neutralization proof;
- rerun descriptor scoring with the same local runtime and metrics.

## Artifacts

Builder:

```text
scripts/build-semantic-descriptor-inputs.py
```

Remediated descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json
```

Derivation tests:

```text
tests/test_semantic_descriptor_derivation.py
```

Derivation remediation proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_derivation_remediation_proof.json
```

Distractor ablation proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_distractor_ablation_proof.json
```

Scoring proof JSON:

```text
prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json
```

## Neutralized descriptor derivation

Removed outcome-like enum values:

```text
ambiguous_candidates_expected
unsupported_scope_expected
no_answer_expected
prefer_granular_marker_over_broad_unit
```

Replacement neutral values:

```text
ambiguity_resolution_required
scope_outside_supported_corpus
scoped_absence_check_required
resolve_granularity_conflict
```

Builder source restrictions:

```text
forbidden_derivation_fields:
  - expected_candidate_ids
  - expected_diagnostic_codes
  - expected_label
  - expected_rejected_candidate_ids
  - rank
  - selection_reason
```

## Derivation independence proof

Evidence:

```text
gsd_exec[fca2e9a3-42ab-4ed2-ac54-4872e8206b59]
```

Proof result:

```text
descriptor_projection_stable: true
structural_change_detected: true
```

Projection digest remained stable when expected-answer fields and `selection_reason` were perturbed:

```text
original_projection_sha256: 58effac41a32f3cb421f92548fd5493b327418d3c52f47d110e8e6e71e864a40
perturbed_projection_sha256: 58effac41a32f3cb421f92548fd5493b327418d3c52f47d110e8e6e71e864a40
```

Structural control changed when a structural candidate field changed:

```text
changed_field: cases[2].candidates[0].candidate_id
structural_change_detected: true
```

## Distractor ablation proof

Evidence:

```text
gsd_exec[642e7011-41e9-4af1-bcb9-a737fdd1e2ba]
```

Ablation changed only the positive-with-distractor query descriptor:

```text
query_intent: resolve_granularity_conflict
query_intent: locate_source_block_marker
```

Result:

```text
dependency_diagnosis: distractor_success_survives_query_intent_ablation
current_distractor_top_candidate: CAND-M022-003-RELEVANT-MARKER
ablated_distractor_top_candidate: CAND-M022-003-RELEVANT-MARKER
positive_with_distractor_relevant_first_delta: 0.0
```

This means the remediated positive-with-distractor success does not depend on the previously suspicious `query_intent` descriptor value.

## Final remediated scoring

Evidence:

```text
gsd_exec[d936f08c-13ac-4dae-baa8-e27bd3af9c7f]
```

The final S05 verification chain rebuilt descriptors, verified descriptor inputs, reran local descriptor scoring, ran focused tests, ran ruff, ran the architecture verifier, and checked GSD sync drift.

Final local descriptor scoring metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
positive_with_distractor_relevant_first: 1.0
runtime_boundary_confirmed: 1.0
```

Deltas against the M024 safe-token baseline:

```text
delta_mrr: 0.125
delta_recall_at_1: 0.25
delta_recall_at_3: 0.0
delta_positive_with_distractor_relevant_first: 1.0
delta_runtime_boundary_confirmed: 0.0
```

Focused test result:

```text
34 passed
```

Architecture verifier:

```text
status: ok
failure_count: 0
```

GSD sync drift check:

```text
status: OK
failed: 0
```

## Acceptance boundary

S05 supports this bounded conclusion:

> The remediated `safe_semantic_descriptor_v1` descriptor representation improved the M024 safe-token semantic scoring metrics on the bounded fixture while no longer depending on direct expected-answer fields, `selection_reason`, the prior outcome-like enum names, or the specific suspicious positive-with-distractor query-intent value.

S05 does not support these claims:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.

R035 remains active and not validated. R038 remains active as the standing independent proof-review gate. S06 must independently review this S05 evidence before any M025 acceptance decision is closed.
