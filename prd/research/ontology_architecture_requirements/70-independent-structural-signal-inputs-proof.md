---
milestone: M029-yfyh51
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# Independent Structural Signal Inputs Proof

S02 builds and verifies M029 descriptor inputs with exactly one independent safe structural signal.

## Selected signal

```text
selected_signal: safe_anchor_family_bucket
```

The selected signal is derived only from safe anchor metadata.

Allowed derivation inputs:

```text
source_anchor_ref
source_anchor_sha256
materialized_candidate_ref
```

## Forbidden reused signal

M029 explicitly forbids the M028 source-order signal as a descriptor or scoring input:

```text
forbidden_reused_signal: safe_source_order_neighborhood_bucket
```

The verifier rejects descriptor records that add this field or token. M029 does not derive from `source_order_index`.

## Produced artifact

```text
artifact: prd/research/ontology_architecture_requirements/fixtures/independent_structural_signal_inputs.json
schema_version: independent-structural-signal-inputs/v1
representation_kind: safe_materialized_descriptor_with_anchor_family_v1
query_descriptor_count: 6
candidate_descriptor_count: 6
```

## Builder and verifier

```text
builder: scripts/build-independent-structural-signal-inputs.py
verifier: scripts/verify-independent-structural-signal-inputs.py
tests: tests/test_independent_structural_signal_inputs.py
```

The builder consumes the M027 materialized descriptor manifest and emits M029 descriptors with one added field:

```text
added_descriptor_fields:
  - safe_anchor_family_bucket
```

The verifier enforces:

```text
single_signal_change_only: true
forbidden_reused_signal_declared: true
m027_baseline_locked: true
m028_baseline_locked: true
r035_non_validation_declared: true
r038_review_required: true
```

## Baselines preserved

M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

M028 bounded result:

```text
mrr: 0.916667
recall_at_1: 0.833333
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

## Verification evidence

The following checks passed in the current session:

```text
builder run: pass
verifier run: pass
focused regression tests: 16 passed
LSP diagnostics: no diagnostics for builder, verifier, and tests
```

The regression tests include fail-closed cases for:

```text
reused M028 signal
source_order_index leakage
expected candidate leakage
raw text fragment leakage
invalid selected-signal enum
descriptor token mismatch
anchor-family derivation mismatch
base source hash mismatch
false redaction marker
missing lifecycle marker
M027 baseline mutation
M028 baseline mutation
```

## Redaction and runtime boundaries

Durable artifacts preserve:

```text
source_text_excluded: true
query_text_excluded: true
raw_vectors_excluded: true
external_payloads_excluded: true
generated_answer_prose_excluded: true
generated_query_excluded: true
expected_answer_fields_excluded_from_descriptor_inputs: true
absolute_paths_excluded: true
```

No managed embedding API, raw vector persistence, legal-answer generation, generated query, or raw legal text is part of S02.

## S03 handoff

S03 should score `safe_materialized_descriptor_with_anchor_family_v1` locally with:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
```

S03 must compare M029 metrics against both M027 and M028, while preserving post-scoring-only labels.

## Non-claims

S02 does not prove:

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
