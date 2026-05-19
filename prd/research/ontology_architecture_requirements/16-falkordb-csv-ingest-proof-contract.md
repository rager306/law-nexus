---
milestone: M021-qk4lze
slice: S01
requirement_scope:
  - R037
  - R035
status: ingest-proof-contract
non_authoritative: true
created_at: 2026-05-18
---

# FalkorDB CSV Ingest Proof Contract

This contract defines the bounded CSV ingest proof for M021. It exists so S02 and S03 can verify FalkorDB data loading before graph-backed retrieval metrics depend on loaded graph state.

This document is not runtime proof. It is a contract and handoff artifact. Runtime evidence must come from S02/S03 commands and reports.

## Purpose

M021 must separate three concerns that are easy to conflate:

1. **Ingest mechanics** — whether CSV data can be loaded into FalkorDB with repeatable counts and safe diagnostics.
2. **Graph model shape** — whether the loaded nodes and relationships represent LegalGraph proof fixtures correctly.
3. **Retrieval quality** — whether local retrieval finds correct EvidenceSpan/SourceBlock candidates.

S01 covers only the first two as a contract. It does not prove retrieval quality.

## Capability evidence levels

| Mechanism | Evidence level entering S01 | Intended use in M021 | Required runtime proof before claims |
| --- | --- | --- | --- |
| FalkorDB `LOAD CSV` | docs-backed | Small interactive smoke for tracked CSV fixtures and Docker/import-folder behavior. | S02 must run local FalkorDB, load nodes and relationships, compare source row counts to graph counts, and record cleanup or blocked diagnostics. |
| `falkordb-bulk-loader` / `falkordb-bulk-insert` | docs-backed | Scale-path assessment for larger CSV graph loads. | S03 must verify CLI availability and either run a small import or record precise blocked diagnostics. |
| `GRAPH.BULK` | docs-backed through bulk-loader docs/spec | Underlying bulk-loader mechanism; create-new-graph oriented. | S03 must not assume update/idempotent semantics without proof. |
| Python client `Graph.query` / `Graph.ro_query` | prior runtime evidence in project | Verification counts and graph cleanup after load. | S02/S03 must run count queries and cleanup commands in the current environment. |

## Loader decision matrix

| Criterion | `LOAD CSV` | `falkordb-bulk-loader` / `GRAPH.BULK` |
| --- | --- | --- |
| Best fit | Small smoke, interactive proof, debugging CSV shape, verifying file access. | Larger imports, repeated full graph builds, batch loading when schema is known. |
| M021 role | S02 runtime smoke. | S03 scale-path evaluation. |
| Input access | FalkorDB resolves `file://` paths relative to its configured import/data directory; Docker requires mounting or copying files into the accessible directory. Remote HTTPS support exists in docs but is not allowed for durable project proof unless separately approved. | Client-side CSV paths passed to loader CLI; connects to server via URL such as `redis://127.0.0.1:6379`. |
| Type handling | CSV values are strings by default; Cypher must convert values with functions such as `toInteger`. | Loader can infer types or enforce schema with typed headers such as `name:STRING`, `rank:INT`, `:ID(Label)`, `:START_ID(Label)`, and `:END_ID(Label)`. |
| Idempotency | Must be explicit in Cypher via `MERGE` and stable IDs. Duplicate behavior must be tested. | `GRAPH.BULK` is create-new-graph oriented; idempotent update/upsert must not be assumed. Graph naming/cleanup strategy must be explicit. |
| Verification | Count source rows, graph nodes, graph relationships, duplicate rows, skipped rows, failed rows, and cleanup status. | Same count verification, plus loader CLI version, server URL, schema mode, skip-invalid settings, and index creation behavior if used. |
| Non-claims | Does not prove scale, production readiness, retrieval quality, legal correctness, parser completeness, or vector/HNSW behavior. | A small bulk smoke does not prove production scale or pilot readiness. |

## Minimal graph fixture shape for S02

S02 should create tracked CSV fixtures under a path such as:

```text
prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/
```

The fixture should be intentionally small and safe. It should contain no raw legal text. Use stable IDs and categorical fields only.

### Node CSV: `legal_units.csv`

Recommended columns:

| Column | Type intent | Required | Notes |
| --- | --- | ---: | --- |
| `id` | string | yes | Stable source-backed unit ID, e.g. `LU-M021-001`. |
| `kind` | string | yes | Example values: `LegalUnit`, `SourceBlock`, `EvidenceSpan`. |
| `source_record_id` | string | yes | Safe source record ID, not raw text. |
| `act_edition_id` | string | yes | Example: `ED-M014-44FZ-2026-01-01`. |
| `ontology_class` | string | yes | Proof-local class such as `procurement_rule` or `citation_evidence`. |
| `temporal_status` | string | yes | `current` or `inactive`. |
| `rank` | integer | no | Optional deterministic ordering field; convert with `toInteger`. |

Expected labels in LOAD CSV smoke:

```cypher
MERGE (:LegalUnit {id: row['id']})
```

If the fixture includes multiple `kind` values, S02 may still use a single `LegalUnit` label for smoke simplicity, while preserving `kind` as a property. This avoids dynamic label assumptions.

### Relationship CSV: `legal_unit_edges.csv`

Recommended columns:

| Column | Type intent | Required | Notes |
| --- | --- | ---: | --- |
| `source_id` | string | yes | Existing `legal_units.csv` ID. |
| `target_id` | string | yes | Existing `legal_units.csv` ID. |
| `type` | string | yes | Example values: `CONTAINS`, `CITES`, `EVIDENCES`. |
| `evidence_span_id` | string | no | Safe evidence span ID when applicable. |
| `citation_key` | string | no | Safe citation key when applicable. |
| `rank` | integer | no | Optional deterministic edge ordering field. |

S02 should avoid dynamic relationship types in the first smoke unless FalkorDB query syntax is verified for that pattern. A conservative smoke can use one relationship type, e.g. `:LINKS_TO`, and preserve original `type` as a property. If S02 chooses separate relationship types such as `:CONTAINS` and `:CITES`, it must verify each count separately.

## Expected S02 fixture counts

The first S02 fixture should be small enough to inspect manually and large enough to cover positive and stale rows:

| Count field | Expected value |
| --- | ---: |
| `expected_source_node_rows` | 4 |
| `expected_source_relationship_rows` | 3 |
| `expected_node_count` | 4 |
| `expected_relationship_count` | 3 |
| `expected_current_nodes` | 3 |
| `expected_inactive_nodes` | 1 |
| `expected_duplicate_node_rows` | 0 for first pass; duplicate behavior tested in a separate rerun or duplicate fixture. |
| `expected_failed_rows` | 0 for happy path. |

S02 may choose slightly different counts only if the report records the exact expected values and explains why.

## LOAD CSV smoke query shape

S02 should prefer parameterized or generated query strings inside a verifier script rather than durable raw query logs. The durable report may include query class and count fields, but should not persist raw query text if it includes environment paths.

Illustrative Cypher shape:

```cypher
LOAD CSV WITH HEADERS FROM 'file://legal_units.csv' AS row
MERGE (u:LegalUnit {id: row['id']})
SET u.kind = row['kind'],
    u.source_record_id = row['source_record_id'],
    u.act_edition_id = row['act_edition_id'],
    u.ontology_class = row['ontology_class'],
    u.temporal_status = row['temporal_status'],
    u.rank = toInteger(row['rank'])
```

Relationship shape:

```cypher
LOAD CSV WITH HEADERS FROM 'file://legal_unit_edges.csv' AS row
MATCH (source:LegalUnit {id: row['source_id']}),
      (target:LegalUnit {id: row['target_id']})
MERGE (source)-[r:LINKS_TO {source_id: row['source_id'], target_id: row['target_id'], type: row['type']}]->(target)
SET r.evidence_span_id = row['evidence_span_id'],
    r.citation_key = row['citation_key'],
    r.rank = toInteger(row['rank'])
```

The smoke may use `CREATE` only for a throwaway graph that is deleted before rerun. Use `MERGE` if rerun/idempotency is being tested.

## S02 report schema

S02 should write a compact tracked report, for example:

```text
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
```

Required report fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Report schema version, e.g. `falkordb-csv-ingest-proof/v1`. |
| `milestone_id` / `slice_id` | `M021-qk4lze` / `S02`. |
| `runtime_disposition` | `load_csv_passed`, `blocked`, or `failed_closed`. |
| `container_runtime.status` | `started`, `skipped`, `blocked`, or `failed`. |
| `file_access.mode` | `docker_import_mount`, `copied_to_container`, `client_side_loader`, or `blocked`. |
| `loader.mechanism` | `LOAD CSV`. |
| `source_counts` | Source node/relationship row counts from CSV. |
| `graph_counts` | Graph node/relationship counts from FalkorDB queries. |
| `idempotency` | Rerun result, duplicate count, or explicit not-tested rationale. |
| `diagnostic_codes` | Stable blocked/failure code list. |
| `cleanup_status` | `deleted`, `not_needed`, or `failed`. |
| `redaction` | Booleans confirming no raw legal text, secrets, raw vectors, or absolute paths are persisted. |
| `non_claims` | Explicit proof boundaries. |

## Diagnostic vocabulary

S02/S03 should use stable diagnostic codes:

| Code | Meaning | Expected behavior |
| --- | --- | --- |
| `CSV_FILE_ACCESS_BLOCKED` | FalkorDB could not access the CSV path through `file://`. | Return blocked/failed_closed; include safe remediation hint about import-folder/mount configuration. |
| `LOAD_CSV_RUNTIME_FAILED` | FalkorDB accepted file path but LOAD CSV query failed. | Return failed_closed with sanitized error class. |
| `LOAD_CSV_COUNTS_MISMATCH` | Source row counts and graph counts do not match. | Return failed_closed; do not proceed to retrieval proof. |
| `LOAD_CSV_IDEMPOTENCY_FAILED` | Rerun created duplicate nodes/edges when MERGE/idempotency was expected. | Return failed_closed; do not claim repeatable ingest. |
| `LOAD_CSV_CLEANUP_FAILED` | Test graph/container could not be cleaned up. | Return failed_closed or needs-attention depending on residue. |
| `BULK_LOADER_UNAVAILABLE` | `falkordb-bulk-insert` or package is not installed or cannot run. | S03 may record blocked scale-path diagnostics without failing S02. |
| `BULK_LOADER_COUNTS_MISMATCH` | Bulk-loaded graph counts do not match source counts. | Return failed_closed for scale-path proof. |
| `UNSAFE_INGEST_ARTIFACT` | Report contains raw legal text, raw vectors, secrets, provider payloads, absolute paths, or `.gsd/exec` paths as proof anchors. | Fail proof artifact validation. |

## Idempotency and cleanup rules

S02 should test repeatability in one of two acceptable ways:

1. **Throwaway graph mode:** create a unique graph name, load once, verify counts, delete graph/container, and record that idempotency is not claimed beyond isolated graph cleanup.
2. **MERGE rerun mode:** load the same CSV twice with stable IDs and `MERGE`, then verify node and relationship counts remain unchanged.

For early M021, MERGE rerun mode is preferred because retrieval proof will eventually need stable graph identity. If relationship MERGE semantics are awkward, S02 may test node idempotency first and explicitly defer relationship idempotency to S06 or a runtime-readiness milestone.

Cleanup must be recorded. If a container is started only for the proof, cleanup should be `deleted` or the report must explain residual state.

## Bulk-loader S03 handoff

S03 should not block S02. S03 evaluates the scale path after S02 proves small ingest mechanics.

S03 should verify:

- installed command name, expected `falkordb-bulk-insert`;
- package/version if available;
- server URL handling;
- node and relationship CSV header requirements;
- whether schema enforcement is required for project data;
- whether graph must be new or can be updated;
- count verification after import;
- skip-invalid node/edge behavior if tested;
- index creation flags if relevant.

If the CLI cannot be installed or run in the current environment, S03 should produce `BULK_LOADER_UNAVAILABLE` with a specific remediation path, not a broad failure of M021.

## S02 handoff

S02 should create:

- `prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_units.csv`
- `prd/research/ontology_architecture_requirements/fixtures/falkordb_ingest/legal_unit_edges.csv`
- `scripts/verify-falkordb-csv-ingest-proof.py`
- `tests/test_falkordb_csv_ingest_proof.py`
- `prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json`

S02 pass criteria:

1. Local FalkorDB starts or a deterministic blocked report is produced.
2. `LOAD CSV` loads the fixture nodes and relationships, or fails closed with a stable diagnostic.
3. `expected_node_count` equals graph node count.
4. `expected_relationship_count` equals graph relationship count.
5. Current/inactive node counts match expected values.
6. Idempotency mode is tested or explicitly bounded.
7. Cleanup status is recorded.
8. Durable proof artifacts contain no raw legal text, secrets, raw vectors, provider payloads, absolute paths, or `.gsd/exec` proof anchors.

Blocked diagnostics are acceptable only if they are precise. A blocked LOAD CSV result advances operational understanding but does not satisfy R037 ingest proof.

## Non-claims

This contract does not claim:

- CSV ingest has been runtime-validated; S02/S03 must prove that.
- R037 is validated.
- R035 is validated.
- Product retrieval quality is proven.
- Parser completeness is proven.
- FalkorDB production readiness is proven.
- Graph-vector, HNSW, or hybrid retrieval behavior is proven.
- Legal-answer correctness is proven.
- Pilot or 1000-document readiness is proven.
- Bulk loader scale readiness is proven from docs alone.

## Verification commands

S01 contract verification:

```bash
uv run python - <<'PY'
from pathlib import Path
p=Path('prd/research/ontology_architecture_requirements/16-falkordb-csv-ingest-proof-contract.md')
text=p.read_text()
required=['LOAD CSV','falkordb-bulk-loader','GRAPH.BULK','source row','node count','relationship count','idempotency','non-claims']
missing=[s for s in required if s not in text]
assert not missing, missing
print('ingest contract present')
PY
```

S02 should add a real runtime verifier command and tests. S01 intentionally does not claim runtime pass.
