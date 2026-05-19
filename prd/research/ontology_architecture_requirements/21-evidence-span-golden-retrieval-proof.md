---
milestone: M021-qk4lze
slice: S04
status: proof
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# EvidenceSpan Golden Retrieval Proof

S04 produced a citation-safe EvidenceSpan/SourceBlock golden retrieval fixture for later local/open-weight retrieval metrics. This is a fixture construction proof only; it does not run retrieval, embeddings, graph filtering, or legal-answer generation.

## Artifacts

Contract:

```text
prd/research/ontology_architecture_requirements/20-evidence-span-golden-retrieval-contract.md
```

Fixture:

```text
prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json
```

Verifier:

```text
scripts/verify-evidence-span-golden-retrieval-cases.py
```

Tests:

```text
tests/test_evidence_span_golden_retrieval_cases.py
```

## Fixture coverage

The fixture uses schema version:

```text
evidence-span-golden-retrieval-cases/v1
```

It contains six required case classes:

| Case class | Expected behavior |
| --- | --- |
| `positive_evidence_span` | Known EvidenceSpan/SourceBlock-backed candidate should be selected. |
| `positive_source_block_marker` | Marker/source-block-level candidate should be selected. |
| `stale_temporal_negative` | Wrong-edition or stale candidate should be rejected. |
| `ambiguous_candidate_set` | Multiple plausible candidates should remain ambiguous. |
| `unsupported_scope` | Unverified scope should be reported as unsupported. |
| `scoped_no_answer` | Scoped query with no candidate should return no-answer. |

Verifier summary:

```json
{
  "status": "ok",
  "case_count": 6,
  "candidate_count": 5,
  "non_authoritative": true,
  "non_claim_boundary": "Fixture construction only; does not validate R035 or prove retrieval quality."
}
```

## Source anchors

The fixture references tracked repo-relative source artifacts only, including:

```text
prd/retrieval/fixtures/offline_citation_retrieval_cases.json
prd/retrieval/fixtures/local_retrieval_quality_benchmark.json
prd/retrieval/fixtures/real_artifact_retrieval_cases.json
prd/parser/consultant_hierarchy_records.json
prd/parser/parser_staging_graph.json
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json
```

Each source artifact entry includes a sha256 hash, and the verifier recomputes the hash before accepting the fixture.

## Safety boundary

The fixture and proof exclude:

- raw legal text;
- source excerpts;
- raw vectors;
- embedding arrays;
- managed provider payloads;
- generated legal-answer prose;
- secrets;
- absolute paths;
- temporary paths;
- `.gsd/exec` paths;
- runtime FalkorDB rows.

The first verifier attempt correctly rejected the fixture because a redaction key included the unsafe fragment `provider_payload`. The fixture now uses `external_payloads_excluded` instead.

## Verification

Final S04 verification evidence:

```text
gsd_exec[af54398e-0dd7-4ce2-8a3b-fec74a23bd22]
```

Command chain:

```bash
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run pytest tests/test_evidence_span_golden_retrieval_cases.py -q
uv run ruff check scripts/verify-evidence-span-golden-retrieval-cases.py tests/test_evidence_span_golden_retrieval_cases.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
verifier: status=ok, case_count=6, candidate_count=5
tests: 8 passed
ruff: All checks passed
architecture verifier: status=ok, failure_count=0
GSD sync drift: status=OK, diagnostics=8, failed=0
```

## Requirement boundary

S04 advances R035 by producing a fixture that future retrieval metrics can evaluate. It does not validate R035 because no local retrieval metrics, graph-filtered retrieval comparison, parser completeness proof, or legal-answer correctness proof has been produced here.

S05 owns local/open-weight retrieval metrics over this golden set.

S06 owns composed graph-filtered retrieval using the S02/S03 ingest evidence plus S04/S05 retrieval evidence.

## Non-claims

This proof does not claim:

- product retrieval quality;
- local embedding quality;
- graph-filtered retrieval quality;
- production FalkorDB readiness;
- parser completeness;
- legal-answer correctness;
- final legal hierarchy correctness;
- graph-vector/HNSW behavior;
- pilot or 1000-document readiness;
- R035 validation.
