---
milestone: M021-qk4lze
slice: S03
status: bulk-loader-viability
requirement_scope:
  - R037
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# FalkorDB Bulk Loader Viability Assessment

This artifact records the M021/S03 pre-runtime viability check for the `falkordb-bulk-loader` scale path. It follows the S02 LOAD CSV baseline and does not claim production scale readiness.

## Executive summary

The `falkordb-bulk-insert` command is not installed globally in the current shell, but it is available through `uvx --from falkordb-bulk-loader falkordb-bulk-insert --help`. That is enough to proceed with a bounded runtime smoke in T03 without adding a permanent project dependency.

S03 should treat `falkordb-bulk-loader` as a client-side CSV loader that connects to FalkorDB via `--server-url` and uses `GRAPH.BULK` under the hood. It is a scale-path candidate, not an idempotent update mechanism by default.

## CLI availability

Probe command:

```bash
uvx --from falkordb-bulk-loader falkordb-bulk-insert --help
```

Evidence:

```text
gsd_exec[9c73e53f-8f2a-46d2-86a8-a6d6df4fd2a0]
```

Findings:

| Check | Result |
| --- | --- |
| Global `falkordb-bulk-insert` on PATH | Not found in the probe. |
| `uvx --from falkordb-bulk-loader falkordb-bulk-insert --help` | Passed and printed CLI usage. |
| Permanent dependency added to project | No. T03 should use `uvx` unless the project later decides to pin the loader. |

## Command shape from current CLI help

The current help output shows:

```text
Usage: falkordb-bulk-insert [OPTIONS] GRAPH
```

Relevant options:

| Option | Meaning for M021 |
| --- | --- |
| `-u`, `--server-url TEXT` | Redis/FalkorDB connection URL, e.g. `redis://127.0.0.1:6381`. |
| `-n`, `--nodes TEXT` | Node CSV file; label inferred from filename. |
| `-N`, `--nodes-with-label TEXT...` | Explicit label followed by node CSV path. Preferred for M021 smoke. |
| `-r`, `--relations TEXT` | Relationship CSV file; type inferred from filename. |
| `-R`, `--relations-with-type TEXT...` | Explicit relationship type followed by relation CSV path. Preferred for M021 smoke. |
| `-d`, `--enforce-schema` | Require schema described in CSV headers. Preferred for predictable M021 proof. |
| `-j`, `--id-type TEXT` | Node ID type, `STRING` or `INTEGER`. M021 should use `STRING`. |
| `-s`, `--skip-invalid-nodes` | Can skip duplicate node IDs instead of erroring. Should not be used for happy-path proof unless specifically testing duplicate behavior. |
| `-e`, `--skip-invalid-edges` | Can skip invalid edge endpoints. Should not be used for happy-path proof unless specifically testing skip behavior. |
| `-i`, `--index TEXT` | Optional range index creation. Out of scope for the first tiny smoke unless needed later. |
| `-f`, `--full-text-index TEXT` | Optional full-text index creation. Out of scope for the first tiny smoke. |

## Schema/header implications

The S02 LOAD CSV fixtures are good source data, but T03 may need derived temporary bulk-loader CSV files because the bulk-loader schema format expects special typed headers.

Expected node header shape for T03:

```text
:ID(LegalUnit),kind:STRING,source_record_id:STRING,act_edition_id:STRING,ontology_class:STRING,temporal_status:STRING,rank:INT
```

Expected relationship header shape:

```text
:START_ID(LegalUnit),:END_ID(LegalUnit),edge_type:STRING,evidence_span_id:STRING,citation_key:STRING,rank:INT
```

Recommended command shape for the smoke:

```bash
uvx --from falkordb-bulk-loader falkordb-bulk-insert \
  --server-url redis://127.0.0.1:<port> \
  --enforce-schema \
  --id-type STRING \
  --nodes-with-label LegalUnit <nodes.csv> \
  --relations-with-type LINKS_TO <relationships.csv> \
  <graph-name>
```

## GRAPH.BULK and create-new-graph caveat

Documentation for `GRAPH.BULK` says the endpoint is used to build a graph from binary batches and verifies that the graph key is unused when `BEGIN` is used. This means the bulk-loader path should be treated as a full/new-graph load path until runtime proof shows otherwise.

M021/S03 must not infer the same idempotent update behavior that S02 tested with LOAD CSV and `MERGE`. If T03 runs a tiny bulk smoke, it should use a unique graph name and count the loaded graph once. Idempotent update/upsert remains a separate future proof unless explicitly implemented and verified.

## Blocked diagnostics

T03 should use these statuses if the runtime smoke cannot proceed:

| Diagnostic | Meaning |
| --- | --- |
| `BULK_LOADER_UNAVAILABLE` | `uvx` cannot run the bulk-loader command or package resolution fails. |
| `BULK_LOADER_RUNTIME_FAILED` | FalkorDB starts, but the loader command fails. |
| `BULK_LOADER_COUNTS_MISMATCH` | Loader exits successfully, but graph counts do not match source counts. |
| `BULK_LOADER_SCHEMA_UNSUPPORTED` | The expected typed CSV schema cannot be accepted by the current loader. |
| `BULK_LOADER_CLEANUP_FAILED` | Runtime/container cleanup fails. |

A blocked bulk-loader result does not invalidate S02's LOAD CSV proof and should not block later retrieval fixture work if M021 chooses to proceed with LOAD CSV as the small-ingest baseline.

## Recommendation before T03

Proceed with a tiny smoke using `uvx --from falkordb-bulk-loader falkordb-bulk-insert` and generated temporary bulk-loader schema CSV files derived from the tracked S02 fixtures. Use a unique graph name and verify counts through the FalkorDB Python client after import.

## Non-claims

This artifact does not claim:

- bulk-loader runtime smoke has passed;
- bulk-loader scale readiness is proven;
- R037 is validated broadly;
- R035 is validated;
- production FalkorDB readiness is proven;
- retrieval quality, parser completeness, legal-answer correctness, graph-vector/HNSW behavior, or pilot readiness is proven.

## Verification

T02 verification marker:

```bash
uv run python - <<'PY'
from pathlib import Path
text=Path('prd/research/ontology_architecture_requirements/18-falkordb-bulk-loader-viability.md').read_text()
required=['falkordb-bulk-insert','GRAPH.BULK','server-url','schema','create-new-graph','blocked diagnostics']
missing=[s for s in required if s not in text]
assert not missing, missing
print('bulk loader viability documented')
PY
```
