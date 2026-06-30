# Reactive Event Vocabulary and Job Ledger Contract

**Milestone:** M083-25gxp3  
**Status:** [proposed] architecture contract  
**Depends on:** D101, R060, R061, R062  
**Scope:** event vocabulary and local job ledger shape for a future bounded reactive shell  

## Purpose

This contract defines the first event vocabulary and local job ledger shape for the law-nexus reactive shell direction. It is a design contract only: M083 does not implement a runtime queue, worker, async API, production Legal Nexus orchestrator, or durable job store.

## Non-claims

This contract does **not** prove:

- async/reactive runtime behavior exists;
- legal correctness;
- parser completeness;
- retrieval quality;
- model or embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex source-truth authority.

Event logs and job ledger records are operational/debug evidence only. They must not be promoted into legal/product proof.

## Source-truth and guardrail context

- **D101:** use a bounded reactive shell around the synchronous deterministic core, not an async-first rewrite.
- **R060:** future async work requires durable job state with fingerprints, lifecycle status, phase, attempts, last error, produced artifacts, proof level, and non-claims.
- **R061:** deterministic domain/policy/validation boundaries remain synchronous or pure unless a seam proves async value.
- **R062:** future reactive work must emit structured decision/failure traces with trace IDs, correlation IDs, job IDs, reason codes, fingerprints, lifecycle/proof tags, redaction status, produced artifacts, and compact trace bundles.

## Pilot seam selection

### First pilot: source inventory

M083 selects **source inventory** as the first event/job pilot family.

Why this seam first:

- Source inventory is naturally event-like: a source file can appear, disappear, or change fingerprint.
- It is lower risk than graph/retrieval/embedding runtime jobs.
- It can produce useful trace/job records without legal-answering claims.
- It aligns with R060/R062: source paths, fingerprints, inventory outputs, and diagnostics are safe bounded job metadata when redacted and path-normalized.
- GitNexus found `ParserInventoryUseCase` exactly at `Class:src/law_nexus/application/parser_inventory.py:ParserInventoryUseCase`.
- GitNexus impact for `ParserInventoryUseCase` was LOW, with direct upstream impact limited to `src/law_nexus/composition.py` import.
- GitNexus impact for `ParserInventoryUseCase.build_parser_fixture_inventory` was LOW, with direct upstream impact limited to tests.

### Second family: parser golden-case jobs

M083 records **parser golden-case jobs** as the second event family, not the first implementation pilot.

Why second:

- M079 made parser golden-case build/evaluate core package-owned.
- GitNexus found `build_evaluation_result` exactly at `Function:src/law_nexus/adapters/sources/parser_golden_cases.py:build_evaluation_result`.
- GitNexus impact for `build_evaluation_result` was LOW/zero upstream in the current graph.
- Golden-case jobs are useful regression events, but they depend on source/parser artifact stability.

### Deferred event families

The following remain deferred until source/parser contracts are more stable:

- graph ingest/proof jobs;
- retrieval quality jobs;
- embedding batch jobs;
- Legal Nexus runtime orchestration.

These surfaces involve external dependencies, quality claims, or production-readiness risks and need separate proof milestones.

## Event family definitions

### Source inventory event family

Purpose: detect and explain source fixture inventory changes without treating inventory events as legal/source-truth proof.

| Event name | Emitted when | Required reason codes |
|---|---|---|
| `source_inventory_job_queued` | A source inventory build/check is requested. | `manual_check_requested`, `source_tree_scan_requested`, `scheduled_check_requested` |
| `source_inventory_scan_started` | The inventory scan begins. | `job_started` |
| `source_fixture_seen` | A candidate source fixture is observed. | `source_seen`, `source_hash_changed`, `source_hash_unchanged` |
| `source_fixture_classified` | A source fixture gets a bounded source role/type classification. | `fixture_in_scope`, `fixture_out_of_scope`, `classification_unknown` |
| `source_inventory_built` | Inventory payload is produced. | `inventory_built`, `inventory_reused` |
| `source_inventory_artifact_written` | Inventory artifact is written or confirmed fresh. | `artifact_written`, `artifact_fresh`, `artifact_stale` |
| `source_inventory_job_failed` | Inventory job fails or blocks. | `input_invalid`, `source_missing`, `write_conflict_detected`, `validation_failed` |

Minimum source inventory job inputs:

- source root path, repository-relative;
- allowed file patterns;
- prior inventory artifact path, if any;
- expected output artifact path;
- scan mode (`check`, `build`, `dry_run`);
- lifecycle/proof tag.

### Parser golden-case event family

Purpose: explain parser golden-case build/evaluate jobs as regression checks after source/parser artifact changes.

| Event name | Emitted when | Required reason codes |
|---|---|---|
| `parser_golden_job_queued` | Golden-case build/evaluate is requested. | `source_inventory_changed`, `parser_artifact_changed`, `manual_check_requested` |
| `parser_golden_cases_built` | Golden-case cases are built or reused. | `cases_built`, `cases_reused`, `artifact_fresh`, `artifact_stale` |
| `parser_golden_evaluation_started` | Evaluation begins. | `job_started` |
| `parser_golden_case_evaluated` | One golden case receives a bounded evaluation result. | `case_passed`, `case_failed`, `case_skipped`, `case_blocked` |
| `parser_golden_diagnostics_written` | Evaluation diagnostics/report is written. | `diagnostics_written`, `no_diagnostics` |
| `parser_golden_regression_detected` | A fail-closed regression is detected. | `diagnostic_error`, `missing_evidence`, `unexpected_relation`, `artifact_invalid` |
| `parser_golden_job_failed` | Build/evaluation job fails or blocks. | `input_invalid`, `artifact_missing`, `json_invalid`, `validation_failed`, `write_conflict_detected` |

Minimum parser golden-case job inputs:

- source artifact paths;
- golden-case artifact path;
- evaluation output path;
- expected case classes;
- parser/source artifact fingerprints;
- lifecycle/proof tag.

## Job lifecycle state machine

Allowed states:

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> running -> blocked
queued -> skipped
failed -> queued
blocked -> queued
```

State meanings:

| State | Meaning | Required trace evidence |
|---|---|---|
| `queued` | Work is requested but not started. | job id, reason code, input fingerprint, requested artifact refs |
| `running` | Work has started. | phase, attempt, started_at |
| `succeeded` | Work completed and artifacts/diagnostics are available or confirmed fresh. | output fingerprint, produced artifacts, proof level, non-claims |
| `failed` | Work ended with a bounded failure. | last error code/message, retryability, phase, attempt |
| `blocked` | Work cannot safely proceed without an external precondition. | blocker code, recovery instruction, missing dependency/artifact |
| `skipped` | Work was intentionally not run. | skip reason, freshness/fingerprint evidence |

Invalid transitions:

- `succeeded -> running` without a new job id;
- `failed -> succeeded` without a retry event;
- `blocked -> succeeded` without an unblock/retry event;
- any transition without `reason_code`.

## Reason-code taxonomy

Reason codes must be short, stable, machine-readable strings. Initial taxonomy:

| Category | Reason codes |
|---|---|
| Request | `manual_check_requested`, `scheduled_check_requested`, `source_tree_scan_requested` |
| Freshness | `source_hash_changed`, `source_hash_unchanged`, `artifact_fresh`, `artifact_stale` |
| Scope | `fixture_in_scope`, `fixture_out_of_scope`, `classification_unknown` |
| Execution | `job_started`, `cases_built`, `cases_reused`, `inventory_built`, `inventory_reused` |
| Result | `case_passed`, `case_failed`, `case_skipped`, `case_blocked`, `diagnostics_written`, `no_diagnostics` |
| Failure | `input_invalid`, `source_missing`, `artifact_missing`, `json_invalid`, `validation_failed`, `write_conflict_detected` |
| Regression | `diagnostic_error`, `missing_evidence`, `unexpected_relation`, `artifact_invalid` |
| Recovery | `retry_scheduled`, `retry_exhausted`, `blocked_waiting_for_artifact`, `blocked_waiting_for_user` |

Future implementation may add reason codes, but must not reuse a code with a changed meaning.

## Local job ledger record schema

M083 recommends a local append-only JSONL ledger first. SQLite can follow after the event vocabulary stabilizes. FalkorDB-backed job state is deferred until graph/runtime proof maturity.

Minimum ledger record:

```json
{
  "schema_version": "law-nexus-job-ledger/v1",
  "ts": "2026-06-30T00:00:00Z",
  "event_name": "source_inventory_job_queued",
  "trace_id": "trace-...",
  "correlation_id": "corr-...",
  "job_id": "job-...",
  "parent_job_id": null,
  "job_type": "source_inventory",
  "component": "source-inventory-ledger",
  "phase": "queue",
  "status_before": null,
  "status_after": "queued",
  "reason_code": "manual_check_requested",
  "attempt": 0,
  "retryable": false,
  "source_ref": "law-source/consultant/44-FZ-2026.xml",
  "artifact_ref": "prd/parser/source_fixture_inventory.json",
  "input_fingerprint": "sha256:...",
  "output_fingerprint": null,
  "produced_artifacts": [],
  "proof_level": "bounded",
  "lifecycle_tag": "bounded",
  "non_claims": ["job ledger events are operational/debug evidence only"],
  "redaction_applied": true,
  "safe_details": {},
  "error_code": null,
  "error_class": null,
  "error_message": null,
  "recovery_instruction": null
}
```

Required fields are those shown above. Optional extension fields must be namespaced under `safe_details` unless they become part of a future schema version.

## Trace bundle shape

A future implementation must be able to export a compact trace bundle by `trace_id` or `job_id`:

```text
trace_bundle_version
trace_id
correlation_id
root_job_id
summary
jobs[]
events[]
state_transitions[]
decisions[]
failures[]
produced_artifacts[]
input_fingerprints[]
output_fingerprints[]
proof_levels[]
non_claims[]
redaction_summary
recovery_instruction
```

Trace bundles must be bounded enough for an agent to read without dumping raw legal text or provider payloads.

## Storage option comparison

| Option | Use now? | Pros | Cons | Decision |
|---|---:|---|---|---|
| Append-only JSONL under tracked/ignored local runtime path | Yes for first prototype | Simple, inspectable, easy to diff in tests when fixture-backed | Needs compaction/indexing later | Recommended first implementation target. |
| SQLite local ledger | Later | Queryable, transaction support, better for many jobs | More schema/migration work | Use after JSONL contract proves stable. |
| FalkorDB-backed job state | Deferred | Could connect operational and graph views | Risks confusing runtime trace with graph/legal proof | Do not use until graph/runtime proof maturity. |
| External queue/broker | Deferred | Real concurrency and worker coordination | Premature infrastructure | Not needed for first bounded pilot. |

## Idempotency and single-writer rules

- `job_id` identifies one execution attempt; retries get a new event with incremented `attempt` and same `correlation_id`.
- `input_fingerprint` must be computed before work starts.
- A job may write artifacts only if its input fingerprint still matches the pre-write check.
- For generated artifacts, one job type owns one artifact path at a time.
- Concurrent writes to the same artifact path are invalid until a lock/single-writer mechanism exists.
- Reusing a fresh artifact must emit a `skipped` or `succeeded` event with `artifact_fresh`, not silently do nothing.
- Partial writes must use temp files plus atomic replace in any future implementation.

## Redaction and portability rules

Ledger records and trace bundles must not include:

- credentials, tokens, or environment secrets;
- raw embeddings or large vector payloads;
- unnecessary raw legal text;
- provider payload dumps;
- ignored `.gsd/exec` references as durable source anchors;
- absolute local paths when repository-relative paths are available.

Allowed references:

- repository-relative source paths;
- repository-relative artifact paths;
- source/artifact hashes;
- bounded diagnostics;
- lifecycle/proof tags;
- non-claim strings.

## Adoption ladder

1. **[proposed] Contract only** — M083 defines vocabulary and ledger schema.
2. **[proposed] Fixture-backed JSONL writer tests** — future milestone implements pure ledger record builder and validator, no queue.
3. **[proposed] Source inventory pilot** — future milestone wraps source inventory build/check with append-only ledger events.
4. **[proposed] Parser golden-case pilot** — future milestone emits golden-case build/evaluate job events.
5. **[deferred] SQLite ledger** — only after JSONL schema stabilizes.
6. **[deferred] Worker/queue runtime** — only after source/parser pilots prove value.
7. **[deferred] Graph/retrieval/Legal Nexus orchestration** — only after product proof gates mature.

## Validator expectations

S03 must validate that this artifact contains:

- first and second event families;
- job lifecycle state machine;
- reason-code taxonomy;
- local ledger schema with R060/R062 fields;
- trace bundle shape;
- storage option comparison;
- idempotency and single-writer rules;
- redaction and portability rules;
- adoption ladder;
- non-claims and no-runtime implementation boundary.
