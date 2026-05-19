---
milestone: M028-yejcai
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Safe Structural Descriptor Remediation Inputs Proof

S02 implements the M028 one-signal descriptor remediation bridge. It consumes M027 materialized descriptor inputs and adds exactly one selected safe structural signal.

## Selected signal

```text
selected_signal: safe_source_order_neighborhood_bucket
single_signal_change_only: true
```

No other descriptor representation change is introduced in S02.

## Inputs

Base descriptor inputs:

```text
prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json
```

Materialization source for safe order metadata:

```text
prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json
```

Contract:

```text
prd/research/ontology_architecture_requirements/64-safe-structural-descriptor-remediation-contract.md
```

## Outputs

Builder:

```text
scripts/build-safe-structural-descriptor-remediation-inputs.py
```

Verifier:

```text
scripts/verify-safe-structural-descriptor-remediation-inputs.py
```

Enhanced descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json
```

Tests:

```text
tests/test_safe_structural_descriptor_remediation_inputs.py
```

## Result

```text
schema_version: safe-structural-descriptor-remediation-inputs/v1
representation_kind: safe_materialized_descriptor_with_neighborhood_v1
selected_signal: safe_source_order_neighborhood_bucket
added_descriptor_fields: [safe_source_order_neighborhood_bucket]
query_descriptor_count: 6
candidate_descriptor_count: 6
m027_baseline_locked: true
```

Immutable baseline:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
score_count: 36
```

## Derivation boundary

The new signal is derived only from safe materialized source order structure:

```text
materialized_candidate_ref
source_order_index
candidate_kind
source_anchor_ref
source_anchor_sha256
```

The builder does not read labels, expected candidates, raw source text, generated answer prose, generated queries, raw vectors, managed API payloads, or absolute paths.

## Signal enum

Allowed values:

```text
source_order_neighbor_first
source_order_neighbor_after_source_block
source_order_neighbor_between_evidence_spans
source_order_neighbor_before_late_gap
source_order_neighbor_late
```

## Verification coverage

Regression tests cover:

- checked-in enhanced manifest passes;
- builder emits exactly one added signal;
- CLI verifier emits compact OK JSON;
- manifest shape and forbidden fragment absence;
- extra signal rejection;
- expected candidate ID rejection;
- raw-text fragment rejection;
- invalid selected-signal enum rejection;
- descriptor token mismatch rejection;
- base source hash mismatch rejection;
- materialization source hash mismatch rejection;
- false redaction flag rejection;
- missing lifecycle marker rejection;
- M027 baseline mutation rejection.

## Final verification

Final S02 verification evidence:

```text
gsd_exec[584dc175-e13f-447a-9c8e-0ad199d71d0c]
```

Verification chain:

```text
uv run python scripts/build-safe-structural-descriptor-remediation-inputs.py
uv run python scripts/verify-safe-structural-descriptor-remediation-inputs.py
uv run pytest tests/test_safe_structural_descriptor_remediation_inputs.py -q
uv run ruff check scripts/build-safe-structural-descriptor-remediation-inputs.py scripts/verify-safe-structural-descriptor-remediation-inputs.py tests/test_safe_structural_descriptor_remediation_inputs.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python enhanced descriptor marker verification
```

Observed result:

```text
builder: status ok
verifier: status ok
tests: 14 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for builder and verifier reported no diagnostics.

## S03 handoff

S03 should score only the enhanced descriptor token strings from:

```text
prd/research/ontology_architecture_requirements/fixtures/safe_structural_descriptor_remediation_inputs.json
```

S03 must compare metrics against the immutable M027 baseline and preserve post-scoring-only labels.

## Non-claims

This proof does not validate R035 and does not prove parser completeness, product retrieval quality, legal-answer correctness, legal interpretation authority, production ETL readiness, graph-vector/HNSW behavior, hybrid retrieval quality, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
