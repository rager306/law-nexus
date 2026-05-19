---
milestone: M030-hwfnq0
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
---

# Source Record Cardinality Signal Inputs Proof

S02 builds and verifies M030 descriptor inputs with exactly one safe source-record-cardinality signal.

## Selected signal

```text
selected_signal: safe_source_record_cardinality_bucket
```

Allowed derivation inputs:

```text
materialized_candidate_ref
source_record_ids
source_anchor_sha256
```

For query descriptors, cardinality is resolved through the matching safe `materialized_candidate_ref` and candidate `source_record_ids` metadata.

## Forbidden prior signals

M030 explicitly forbids prior M028 and M029 signals as descriptor or scoring inputs:

```text
forbidden_prior_signal: safe_source_order_neighborhood_bucket
forbidden_prior_signal: safe_anchor_family_bucket
```

The verifier rejects these prior signals in descriptor records and descriptor tokens. M030 also rejects `source_order_index` leakage.

## Produced artifact

```text
artifact: prd/research/ontology_architecture_requirements/fixtures/source_record_cardinality_signal_inputs.json
schema_version: source-record-cardinality-signal-inputs/v1
representation_kind: safe_materialized_descriptor_with_source_record_cardinality_v1
query_descriptor_count: 6
candidate_descriptor_count: 6
```

## Builder and verifier

```text
builder: scripts/build-source-record-cardinality-signal-inputs.py
verifier: scripts/verify-source-record-cardinality-signal-inputs.py
tests: tests/test_source_record_cardinality_signal_inputs.py
```

The builder consumes the M027 materialized descriptor manifest and emits M030 descriptors with one added field:

```text
added_descriptor_fields:
  - safe_source_record_cardinality_bucket
```

The verifier enforces:

```text
single_signal_change_only: true
forbidden_prior_signals_declared: true
m027_baseline_locked: true
m028_baseline_locked: true
m029_baseline_locked: true
r035_non_validation_declared: true
r038_review_required: true
```

## Cardinality distribution

Observed cardinality distribution in the controlled fixture:

```text
source_record_cardinality_single: 12
constant_signal_risk: true
```

This means the selected signal is currently constant across the 6 query and 6 candidate descriptors. S03 should expect this signal to behave as a negative-control or neutral signal unless the embedding model's token interactions produce incidental ranking differences.

## Baselines preserved

M027 baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

M028 bounded source-order result:

```text
mrr: 0.916667
recall_at_1: 0.833333
recall_at_3: 1.0
runtime_boundary_confirmed: 1.0
```

M029 bounded anchor-family result:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

## Verification evidence

The following checks passed in the current session:

```text
builder run: pass
verifier run: pass
focused regression tests: 20 passed
LSP diagnostics: no diagnostics for builder, verifier, and tests
```

The regression tests include fail-closed cases for:

```text
reused M028 signal
reused M029 signal
source_order_index leakage
expected candidate leakage
raw text fragment leakage
invalid selected-signal enum
descriptor token mismatch
cardinality derivation mismatch
query/candidate cardinality mismatch
base source hash mismatch
false redaction marker
missing lifecycle marker
M027 baseline mutation
M028 baseline mutation
M029 baseline mutation
constant-signal-risk marker mismatch
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

S03 should score `safe_materialized_descriptor_with_source_record_cardinality_v1` locally with:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
raw_vectors_persisted: false
```

S03 must compare M030 metrics against M027, M028, and M029 while preserving post-scoring-only labels.

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
