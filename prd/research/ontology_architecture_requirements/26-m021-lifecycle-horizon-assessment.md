---
milestone: M021-qk4lze
slice: S07
status: lifecycle-assessment
requirement_scope:
  - R035
  - R037
non_authoritative: true
created_at: 2026-05-18
---

# M021 Lifecycle Horizon Assessment

M021 established a bounded post-M020 proof horizon for FalkorDB ingestion and EvidenceSpan retrieval. The milestone materially advances R035 and R037, but it does not validate either requirement broadly. Both remain active with clearer evidence and next-horizon ownership.

## Evidence summary

| Slice | Evidence | Result | Boundary |
| --- | --- | --- | --- |
| S01 | `16-falkordb-csv-ingest-proof-contract.md` | Ingest contract defined loader paths, fixture shape, counts, idempotency, diagnostics, and non-claims. | Contract only; no runtime load. |
| S02 | `falkordb_csv_ingest_proof.json` | `LOAD CSV` passed with 4 nodes, 3 relationships, MERGE rerun idempotency, and cleanup. | Small fixture only; not production ingest. |
| S03 | `falkordb_bulk_loader_proof.json` and `19-falkordb-loader-recommendation.md` | `falkordb-bulk-insert` via `uvx --from falkordb-bulk-loader` passed tiny create-new-graph smoke. | No idempotent bulk update or production-scale proof. |
| S04 | `evidence_span_golden_retrieval_cases.json` and `21-evidence-span-golden-retrieval-proof.md` | Six-case EvidenceSpan/SourceBlock golden fixture verified. | Fixture construction only; no retrieval metrics. |
| S05 | `evidence_span_local_retrieval_metrics_proof.json` and `23-evidence-span-local-retrieval-metrics-proof.md` | Local `deepvk/USER-bge-m3` runtime confirmed; fixture metrics all passed at 1.0. | Seed fixture metrics only; not product retrieval quality. |
| S06 | `graph_filtered_retrieval_integration_proof.json` and `25-graph-filtered-retrieval-integration-proof.md` | Local FalkorDB graph-filtered integration passed with citation preservation and baseline comparison. | Safe fixture IDs only; not product, parser, graph-vector, or production readiness. |

## R037 lifecycle recommendation

Recommended lifecycle state:

```text
active / partially evidenced
```

Why:

- S02 proved the small `LOAD CSV` path with Docker import folder behavior and idempotent MERGE rerun.
- S03 proved a tiny bulk-loader create-new-graph path.
- S06 proved safe graph materialization can compose with retrieval filtering.

What remains open:

- larger corpus ingest;
- skipped/failed row accounting;
- resource profile and timeout behavior;
- bulk-loader update/upsert semantics;
- production data loading policy;
- operational recovery and observability for failed ingest.

Next owner:

```text
Future ingest-scale / production-data-loading milestone
```

## R035 lifecycle recommendation

Recommended lifecycle state:

```text
active / strongly advanced, not validated
```

Why:

- S04 created a verified EvidenceSpan/SourceBlock golden set.
- S05 confirmed local/open-weight runtime boundary and passed fixture-level retrieval metrics.
- S06 composed graph filtering, temporal/stale handling, citation preservation, and baseline comparison in local FalkorDB.

What remains open:

- broader corpus retrieval quality;
- representative real-document parser completeness;
- graph-vector/HNSW or hybrid retrieval behavior if later required;
- generated-query safety if generated Cypher becomes part of the product path;
- legal-answer correctness and non-authoritative answer rendering;
- production FalkorDB behavior and resource profile;
- pilot-scale readiness.

Next owner:

```text
Future retrieval-quality and production-readiness horizon after M021
```

## What M021 now enables

M021 enables the next planning horizon to start from verified prerequisites rather than speculation:

1. FalkorDB can load and query a small legal-evidence-shaped fixture locally.
2. `LOAD CSV` and bulk-loader roles are distinct and documented.
3. EvidenceSpan/SourceBlock retrieval cases exist as safe IDs with positive and negative coverage.
4. Local `deepvk/USER-bge-m3` runtime boundary is confirmed in this environment.
5. Graph-filtered retrieval can preserve citation IDs and reject stale/unsupported/no-answer routes over the fixture.

## What M021 does not enable

M021 does not authorize:

- closing R035;
- closing R037;
- production retrieval quality claims;
- graph-vector or HNSW claims;
- hybrid retrieval quality claims;
- parser completeness claims;
- legal-answer correctness claims;
- production FalkorDB readiness claims;
- bulk-loader production readiness claims;
- 1000-document or pilot readiness claims;
- managed embedding API fallback.

## Recommended next horizon

The next horizon should be one of these, in order of evidence dependency:

1. **Representative corpus retrieval quality:** expand beyond the six-case fixture while preserving safe IDs and redaction.
2. **Parser-to-EvidenceSpan materialization:** prove real Garant ODT or accepted source extraction produces EvidenceSpan/SourceBlock records compatible with S04-S06 contracts.
3. **Operational ingest scale:** stress LOAD CSV and bulk-loader on a larger tracked synthetic corpus with row-level diagnostics and resource metrics.
4. **Answer rendering safety:** evaluate citation-bound non-authoritative answer templates over retrieved evidence without legal-authority overclaim.

Do not start graph-vector/HNSW or pilot-readiness claims until the above prerequisites are either completed or explicitly descoped.

## Validation posture

S07 should validate the milestone as a bounded proof milestone if final verification passes. That validation should say:

```text
M021 passed its bounded success criteria.
```

It should not say:

```text
R035 is validated.
R037 is validated.
Production retrieval is ready.
Pilot readiness is proven.
```
