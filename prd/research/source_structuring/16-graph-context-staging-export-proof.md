# M033 S02 — Graph Context Staging Export Proof

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S02 — Candidate to Staging Export`
- Proof status: `draft_t01_export_contract`
- Requirement advanced: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

S02 exports accepted deterministic verifier decisions into run-scoped `graph_context` staging artifacts. The export is a staging/export operation only. It does not create FalkorDB production graph data, does not load a graph runtime, does not validate legal correctness, and does not validate R037.

The export uses S01's pure conversion helper and writes durable-shaped outputs in temporary workspaces during proof runs.

## Input artifact classes

S02 consumes already-produced runtime artifacts:

- `runtime/discovery/<run_id>/candidate_hypotheses.jsonl`
- `runtime/verifier/<run_id>/verifier_decisions.jsonl`
- optionally `runtime/external-review/<run_id>/review_pack.json`
- optionally `runtime/external-review/<run_id>/review_pack.md`

Candidate rows remain non-authoritative MiniMax-derived structural proposals. Verifier rows are deterministic structural decisions. Only verifier status `accepted` can become a staged graph-context record.

## Output location

The export writes under:

```text
runtime/graph-context/<run_id>/
  graph_context_staging.jsonl
  graph_context_diagnostics.jsonl
  graph_context_summary.json
```

## Output files

### `graph_context_staging.jsonl`

Contains staged records created from accepted candidates. Each row must use schema `m033.s01.graph-context-staging.v1` and include:

- stable `graph_context_id`;
- `run_id`;
- `candidate_id`;
- `decision_id`;
- `record_kind`;
- `staging_status: staged`;
- candidate refs;
- verifier refs;
- trajectory refs;
- source refs;
- optional attempt/review pack refs;
- non-claims for legal correctness, parser completeness, R035, R037, and R038.

### `graph_context_diagnostics.jsonl`

Contains skipped rows and safe diagnostics for candidates that cannot be staged. Expected reason classes:

- `verifier-status-not-accepted`;
- `candidate-id-invalid`;
- `decision-id-invalid`;
- `unsupported-record-kind`;
- `source-refs-missing`;
- `unsafe-source-ref`.

Diagnostics must not echo unsafe local absolute paths, raw provider payloads, raw vectors, secrets, or legal-answer prose.

### `graph_context_summary.json`

Contains summary counts and safe refs:

```json
{
  "schema_version": "m033.s01.graph-context-summary.v1",
  "run_id": "RUN-...",
  "status": "graph_context_staging_exported",
  "accepted": 1,
  "staged": 1,
  "skipped": 0,
  "diagnostics": 0,
  "output_refs": [
    "runtime/graph-context/RUN-.../graph_context_staging.jsonl",
    "runtime/graph-context/RUN-.../graph_context_diagnostics.jsonl",
    "runtime/graph-context/RUN-.../graph_context_summary.json"
  ],
  "non_authoritative": true
}
```

## Helper and CLI shape

Planned helper:

```python
export_graph_context_staging(workspace_root, *, run_id, candidate_rows=None, decision_rows=None, review_pack_refs=None)
```

Planned CLI:

```text
graph-context-stage <run_id>
```

The CLI should read runtime discovery/verifier artifacts for the run and print summary JSON with output refs and counts.

## Diagnostics behavior

Every candidate row should result in one of:

- a staged record in `graph_context_staging.jsonl` when the deterministic verifier decision is accepted and provenance is safe;
- a diagnostic row in `graph_context_diagnostics.jsonl` when verifier status is not accepted, provenance is missing/unsafe, or record kind is unsupported.

Missing candidate/decision matches should be diagnostics, not hidden omissions.

## Implementation evidence

S02 implemented graph-context staging export in code:

- `graph_context_directory()` returns `runtime/graph-context/<run_id>/`.
- `export_graph_context_staging()` writes:
  - `graph_context_staging.jsonl`
  - `graph_context_diagnostics.jsonl`
  - `graph_context_summary.json`
- CLI command `graph-context-stage <run_id>` runs the export from existing runtime discovery/verifier artifacts.

Focused tests prove:

- accepted verifier decisions produce staged graph_context rows;
- non-accepted decisions produce skipped diagnostics;
- unmatched candidates produce `missing-verifier-decision` diagnostics;
- CLI smoke can run mocked `discover --verify-candidates` followed by `graph-context-stage` in a temporary workspace;
- output refs are workspace-relative;
- staged rows preserve non-authoritative and R037 non-validation boundaries.

## Non-claims

S02 export does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- production ETL readiness;
- FalkorDB graph ingestion;
- R035 validation;
- R037 validation;
- R038 validation.

## T01 verification markers

This proof intentionally includes `graph_context_staging.jsonl`, `graph_context_diagnostics.jsonl`, `graph_context_summary.json`, `accepted`, `skipped`, `diagnostics`, `R035`, `R037`, and `R038`.
