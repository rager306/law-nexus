---
milestone: M021-qk4lze
slice: S03
status: loader-recommendation
requirement_scope:
  - R037
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# FalkorDB Loader Recommendation After S03

This artifact synthesizes the M021/S02 LOAD CSV proof and M021/S03 bulk-loader proof. It is a bounded ingest recommendation, not production readiness evidence.

## Recommendation

Use both loaders, but for different proof roles:

| Use case | Recommended loader | Why |
| --- | --- | --- |
| Small interactive ingest smoke | `LOAD CSV WITH HEADERS` | Runtime-proven in S02, supports Cypher `MERGE`, idempotency smoke, and fine-grained debugging. |
| Early graph-shape debugging | `LOAD CSV WITH HEADERS` | Easier to inspect failures, file-access configuration, and row-to-count reconciliation. |
| Tiny scale-path smoke | `falkordb-bulk-loader` / `falkordb-bulk-insert` | Runtime-proven in S03 via `uvx`, with typed schema CSVs and matching graph counts. |
| Larger new-graph batch builds | `falkordb-bulk-loader` | Uses `GRAPH.BULK`; intended for efficient bulk graph creation. |
| Idempotent updates/upserts | Not yet proven with bulk-loader | S02 proved idempotent `MERGE` rerun only for LOAD CSV. Bulk-loader report explicitly does not claim idempotent update semantics. |
| Production/pilot scale | Future proof required | Neither S02 nor S03 proves production readiness, resource profile, or pilot scale. |

## Proven facts

### LOAD CSV baseline from S02

Evidence:

```text
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
gsd_exec[6c9d8f33-2d88-49df-9520-2a69222af69b]
```

Results:

- `runtime_disposition=load_csv_passed`
- Container image: `falkordb/falkordb:edge`
- Import folder: `IMPORT_FOLDER /data`
- Working URI form: `file:///legal_units.csv`
- Source rows: 4 nodes, 3 relationships
- Graph counts: 4 nodes, 3 relationships
- Current/inactive nodes: 3 / 1
- Idempotency: `MERGE rerun`, `passed`, duplicate counts 0 / 0
- Cleanup: `deleted`

### Bulk-loader scale-path smoke from S03

Evidence:

```text
prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json
gsd_exec[a7d2153e-596d-400e-8580-ba02f345bacd]
```

Results:

- `runtime_disposition=bulk_loader_passed`
- Invocation: `uvx --from falkordb-bulk-loader`
- Command: `falkordb-bulk-insert`
- Mechanism: `falkordb-bulk-loader`
- Uses `GRAPH.BULK`: true
- Create-new-graph semantics: true
- Idempotent update claimed: false
- Enforced schema: true
- ID type: `STRING`
- Source rows: 4 nodes, 3 relationships
- Graph counts: 4 nodes, 3 relationships
- Current/inactive nodes: 3 / 1
- Cleanup: `deleted`

## Practical details discovered

1. `falkordb-bulk-insert` was not globally installed in the shell, but was usable through `uvx --from falkordb-bulk-loader falkordb-bulk-insert`.
2. The bulk-loader smoke used temporary derived schema CSVs with headers such as `:ID(LegalUnit)`, `:START_ID(LegalUnit)`, and `:END_ID(LegalUnit)`.
3. The S03 bulk-loader proof used a unique graph name and verified counts after import.
4. The S03 proof did not test rerun/update behavior because `GRAPH.BULK` is treated as create-new-graph oriented until further proof.
5. The durable report excludes temporary paths, raw legal text, vectors, secrets, external payloads, absolute paths, and `.gsd/exec` anchors.

## Guidance for later M021 slices

- S04 can rely on the fact that small tracked graph fixtures can be loaded into FalkorDB by either LOAD CSV or bulk-loader.
- S06 should prefer LOAD CSV if it needs idempotent graph updates during iterative retrieval/filter experiments.
- S06 may use bulk-loader if it creates a new graph per run and verifies counts after import.
- Any larger corpus proof must add resource metrics, failed/skipped row accounting, and cleanup diagnostics beyond this tiny smoke.
- Retrieval failures must not be attributed to ingest unless source-to-graph counts fail.

## Non-claims

This recommendation does not claim:

- R037 is fully validated for all graph ingest scenarios.
- R035 is validated.
- Bulk-loader production scale is proven.
- Idempotent bulk-loader updates are proven.
- Parser completeness is proven.
- Product retrieval quality is proven.
- Legal-answer correctness is proven.
- Graph-vector/HNSW or hybrid retrieval behavior is proven.
- Pilot or 1000-document readiness is proven.

## Verification

Final S03 verification evidence:

```text
gsd_exec[a7d2153e-596d-400e-8580-ba02f345bacd]
```

Command chain passed:

```bash
uv run python scripts/verify-falkordb-bulk-loader-proof.py --readiness-timeout 3
uv run pytest tests/test_falkordb_bulk_loader_proof.py -q
uv run ruff check scripts/verify-falkordb-bulk-loader-proof.py tests/test_falkordb_bulk_loader_proof.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```
