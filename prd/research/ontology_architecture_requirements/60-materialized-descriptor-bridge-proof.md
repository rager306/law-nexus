---
milestone: M027-vxdy7c
slice: S03
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Materialized Descriptor Bridge Proof

S03 derives safe descriptor inputs from S02 materialized candidate records. This moves the M027 chain from safe materialized `EvidenceSpan` / `SourceBlock` candidates toward descriptor scoring without reintroducing raw legal text, expected labels, expected candidate IDs, ranks, generated answer prose, or query text.

## Inputs

Materialization source:

```text
prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json
```

Source representation:

```text
parser-evidence-span-materialization/v1
safe_materialized_evidence_candidates_v1
```

## Outputs

Builder:

```text
scripts/build-materialized-descriptor-inputs.py
```

Verifier:

```text
scripts/verify-materialized-descriptor-inputs.py
```

Descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/materialized_descriptor_inputs.json
```

Tests:

```text
tests/test_materialized_descriptor_inputs.py
```

## Descriptor result

```text
schema_version: materialized-descriptor-inputs/v1
representation_kind: safe_materialized_descriptor_v1
query_descriptor_count: 6
candidate_descriptor_count: 6
source_materialization_verified: true
```

## Derivation boundary

Descriptors are derived only from materialized structural fields:

```text
candidate_kind
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
source_order_index_bucket
```

The bridge does not read or persist expected labels, expected candidate IDs, ranks, raw source text, legal-answer prose, generated queries, or managed embedding/runtime payloads.

## Safe descriptor shape

Each descriptor record contains safe IDs, safe source references, source anchor hashes, bounded enum descriptors, descriptor tokens, and non-authoritative markers.

Descriptor tokens follow:

```text
field_name:bounded_enum_value
```

Example token classes:

```text
candidate_kind:evidence_span
structural_unit_kind:paragraph
citation_granularity:article_or_evidence_span
content_role:retrieval_candidate
temporal_status:unknown_temporal_status
materialization_method:content_xml_order_anchor
source_order_index_bucket:middle_source_order
```

## Verification coverage

Regression tests cover:

- checked-in manifest passes;
- builder emits safe derivation fields;
- CLI verifier emits compact OK JSON;
- manifest shape and forbidden fragment absence;
- raw text field rejection;
- expected candidate ID rejection;
- raw-text fragment rejection;
- absolute path rejection;
- bad materialization hash rejection;
- invalid enum rejection;
- descriptor token mismatch rejection;
- false redaction flag rejection;
- non-materialized source ID rejection;
- missing lifecycle marker rejection.

## Final verification

Final S03 verification evidence:

```text
gsd_exec[5837d88d-4629-4709-9fbc-e747ca103eb5]
```

Verification chain:

```text
uv run python scripts/build-materialized-descriptor-inputs.py
uv run python scripts/verify-materialized-descriptor-inputs.py
uv run pytest tests/test_materialized_descriptor_inputs.py -q
uv run ruff check scripts/build-materialized-descriptor-inputs.py scripts/verify-materialized-descriptor-inputs.py tests/test_materialized_descriptor_inputs.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python materialized descriptor bridge marker verification
```

Observed result:

```text
builder: status ok
verifier: status ok
regression tests: 14 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for builder and verifier reported no diagnostics.

## Handoff to S04

S04 may score only the safe descriptor token strings from the materialized-derived descriptor manifest. S04 must keep labels/evaluation separate from descriptor inputs and must preserve the local/open-weight runtime boundary if it performs semantic scoring.

## Non-claims

This proof does not validate R035 and does not prove parser completeness, product retrieval quality, legal-answer correctness, legal interpretation authority, production ETL readiness, graph-vector/HNSW behavior, hybrid retrieval quality, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
