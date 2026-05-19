---
milestone: M021-qk4lze
slice: S03
source_slice: S02
status: load-csv-runtime-findings
requirement_scope:
  - R037
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# FalkorDB LOAD CSV Runtime Findings

This artifact preserves the concrete M021/S02 LOAD CSV runtime findings before S03 evaluates the `falkordb-bulk-loader` scale path. It is bounded ingest evidence only.

## Executive summary

M021/S02 proved a small tracked CSV ingest path against local FalkorDB using `LOAD CSV WITH HEADERS`. The proof passed with four safe node rows and three safe relationship rows. It also discovered a runtime-specific file URI constraint: in the current Docker/import-folder setup, `file://legal_units.csv` failed, while `IMPORT_FOLDER /data` plus `file:///legal_units.csv` worked.

This matters for future work because CSV file access failures must be separated from graph-model or retrieval-quality failures.

## Runtime result

Final proof report:

```text
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
```

Final runtime disposition:

```text
load_csv_passed
```

Final verification evidence:

```text
gsd_exec[6c9d8f33-2d88-49df-9520-2a69222af69b]
```

## What worked

| Question | Result | Evidence |
| --- | --- | --- |
| Did local FalkorDB start? | Yes. | `container_runtime.status=started`, `image_reference=falkordb/falkordb:edge`. |
| Was cleanup successful? | Yes. | `container_runtime.cleanup_status=deleted`. |
| Was CSV access configured through Docker import-folder? | Yes. | `file_access.mode=docker_import_mount`, `container_import_folder=/data`. |
| Did node rows load? | Yes. | `source_counts.node_rows=4`, `graph_counts.node_count=4`. |
| Did relationship rows load? | Yes. | `source_counts.relationship_rows=3`, `graph_counts.relationship_count=3`. |
| Were temporal categories preserved? | Yes. | `graph_counts.current_nodes=3`, `graph_counts.inactive_nodes=1`. |
| Was idempotency checked? | Yes. | `idempotency.mode=MERGE rerun`, `status=passed`, duplicate counts 0/0. |
| Were unsafe durable fields excluded? | Yes. | Redaction flags exclude raw source text, raw vectors, secrets, external payloads, absolute paths, and `.gsd/exec` proof anchors. |

## File URI finding

Initial diagnostic probing showed that this form failed in the current FalkorDB Docker/import-folder runtime:

```text
file://legal_units.csv
```

The working form was:

```text
IMPORT_FOLDER /data
file:///legal_units.csv
file:///legal_unit_edges.csv
```

The verifier therefore starts FalkorDB with the tracked fixture directory mounted at `/data`, sets `FALKORDB_ARGS=IMPORT_FOLDER /data`, and uses `file:///...` URI form in `LOAD CSV WITH HEADERS` queries.

## Source fixtures

S02 fixtures:

```text
prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_units.csv
prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_unit_edges.csv
```

The fixtures intentionally contain safe IDs and categorical fields only. They do not contain raw legal text.

Expected counts:

| Count | Value |
| --- | ---: |
| Source node rows | 4 |
| Source relationship rows | 3 |
| Graph nodes | 4 |
| Graph relationships | 3 |
| Current nodes | 3 |
| Inactive nodes | 1 |

## Ingest semantics proven

M021/S02 proves the following small-ingest mechanics:

1. A local FalkorDB container can be started for a bounded CSV ingest proof.
2. A tracked fixture directory can be exposed through Docker import-folder configuration.
3. `LOAD CSV WITH HEADERS` can load safe node and relationship CSV fixtures.
4. Values are treated as strings unless converted; the verifier uses `toInteger(row['rank'])` for rank fields.
5. Stable IDs plus `MERGE` can support a rerun idempotency smoke for this fixture.
6. Source row counts can be reconciled against graph node/relationship counts.
7. The proof report can stay redacted and non-authoritative.

## What this does not prove

These are non-claims:

- It does not validate R037 broadly; it is a bounded small LOAD CSV smoke.
- It does not validate R035; R035 remains active.
- It does not prove `falkordb-bulk-loader` or `GRAPH.BULK` scale readiness; S03 owns that assessment.
- It does not prove product retrieval quality.
- It does not prove parser completeness.
- It does not prove production FalkorDB readiness.
- It does not prove graph-vector, HNSW, or hybrid retrieval behavior.
- It does not prove legal-answer correctness.
- It does not prove pilot or 1000-document readiness.

## S03 handoff

S03 should use this baseline when evaluating bulk loading:

1. Treat LOAD CSV as the proven small-ingest path for M021.
2. Treat `file:///...` under `IMPORT_FOLDER /data` as the runtime-confirmed Docker import-folder pattern.
3. Do not assume bulk-loader idempotency; check whether `falkordb-bulk-insert`/`GRAPH.BULK` is create-new-graph oriented.
4. Compare source row counts to graph counts for any bulk-loader smoke.
5. If bulk-loader is unavailable, emit `BULK_LOADER_UNAVAILABLE` rather than treating M021 retrieval work as failed.
6. Preserve non-claims: a tiny bulk-loader smoke must not become production-scale or pilot-readiness evidence.

## Verification

T01 verification marker:

```bash
uv run python - <<'PY'
from pathlib import Path
p=Path('prd/research/ontology_architecture_requirements/17-falkordb-load-csv-runtime-findings.md')
text=p.read_text()
required=['IMPORT_FOLDER /data','file:///legal_units.csv','file://legal_units.csv','load_csv_passed','4','3','idempotency','non-claims']
missing=[s for s in required if s not in text]
assert not missing, missing
print('load csv findings documented')
PY
```
