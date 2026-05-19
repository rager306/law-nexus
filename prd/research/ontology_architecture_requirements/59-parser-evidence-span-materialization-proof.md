---
milestone: M027-vxdy7c
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Parser to EvidenceSpan Materialization Smoke Proof

S02 implements a tiny safe materialization smoke from the controlled Garant ODT source into safe `EvidenceSpan` and `SourceBlock` candidate records. The proof uses ODT `content.xml` structural ordering only and does not persist raw legal text.

## Contract source

```text
prd/research/ontology_architecture_requirements/58-parser-evidence-span-materialization-contract.md
```

## Artifacts

Builder:

```text
scripts/build-parser-evidence-span-materialization.py
```

Verifier:

```text
scripts/verify-parser-evidence-span-materialization.py
```

Materialization artifact:

```text
prd/research/ontology_architecture_requirements/parser_evidence_span_materialization.json
```

Regression tests:

```text
tests/test_parser_evidence_span_materialization.py
```

## Materialization result

```text
schema_version: parser-evidence-span-materialization/v1
representation_kind: safe_materialized_evidence_candidates_v1
status: ok
blocked_reason: none
materialized_candidate_count: 6
safe_source_anchors_verified: true
```

Controlled source:

```text
source_document_ref: law-source/garant/44-fz.odt
```

The artifact records source document hash and safe source anchor hashes. It does not persist source text.

## Safe record boundary

Materialized candidates contain only safe fields such as:

```text
candidate_id
candidate_kind
source_document_ref
source_document_sha256
source_anchor_id
source_anchor_sha256
source_order_index
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
parser_evidence_ref
non_authoritative
```

The smoke builder emits safe `parser-smoke:<safe-id>` evidence refs and deterministic `source_order_index` values from ODT structural order.

## Verification coverage

Regression tests cover:

- checked-in artifact passes;
- CLI verifier emits compact OK JSON;
- artifact shape and forbidden fragment absence;
- raw text field rejection;
- forbidden raw-text fragment rejection;
- absolute path rejection;
- `.gsd/exec` anchor rejection;
- bad source hash rejection;
- invalid enum rejection;
- invalid blocked reason rejection;
- valid blocked payload shape;
- false redaction flag rejection;
- missing lifecycle marker rejection.

## Final verification

Final S02 verification evidence:

```text
gsd_exec[deab78e3-ec45-425e-8244-30ac18b9cdd9]
```

Verification chain:

```text
uv run python scripts/build-parser-evidence-span-materialization.py
uv run python scripts/verify-parser-evidence-span-materialization.py
uv run pytest tests/test_parser_evidence_span_materialization.py -q
uv run ruff check scripts/build-parser-evidence-span-materialization.py scripts/verify-parser-evidence-span-materialization.py tests/test_parser_evidence_span_materialization.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python materialization proof marker verification
```

Observed result:

```text
materialization builder: status ok
materialization verifier: status ok
regression tests: 13 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
proof markers: verified
```

LSP diagnostics for builder and verifier reported no diagnostics.

## Handoff to S03

S03 may derive descriptor inputs from materialized structural fields only:

```text
candidate_kind
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
source_order_index_bucket
```

S3 must not use raw source text, expected labels, expected candidate IDs, ranks, legal-answer prose, or generated queries as descriptor inputs.

## Non-claims

This proof does not validate R035 and does not prove parser completeness, product retrieval quality, legal-answer correctness, legal interpretation authority, production ETL readiness, graph-vector/HNSW behavior, hybrid retrieval quality, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
