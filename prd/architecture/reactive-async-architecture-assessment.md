# Reactive and Asynchronous Architecture Assessment

**Milestone:** M081-zfxrxb  
**Status:** [proposed] architecture assessment  
**Scope:** law-nexus execution model, orchestration, and future runtime architecture  
**Evidence inputs:** `prd/ARCHITECTURE.md`, `prd/02_architecture.md`, GitNexus queries, code inventory over `src/law_nexus/` and `scripts/`  

## Purpose

This document inventories how law-nexus could become more reactive and asynchronous, what that would give the project, and where it would add risk. It is an architecture assessment, not an implementation proof.

## Non-claims

This assessment does **not** prove:

- legal correctness;
- parser completeness;
- retrieval quality;
- model or embedding quality;
- generated-Cypher correctness;
- FalkorDB production readiness;
- ACP/git-lex source-truth authority;
- that async/reactive runtime behavior already exists.

## Current execution model

law-nexus is currently best described as a **deterministic batch/proof harness architecture** with package-owned seams and script wrappers:

| Area | Current model | Evidence | Implication |
|---|---|---|---|
| Domain | Mostly pure deterministic models/policies. | `src/law_nexus/domain/*`, `src/law_nexus/application/generated_cypher_policy.py` | Keep synchronous/pure; async here would add noise. |
| Application use cases | Small synchronous use-case classes delegating to injected builders/validators. | GitNexus exact context for `ParserInventoryUseCase`; exact context for `make_consultant_hierarchy_use_case`; `SourceHierarchyUseCase`. | Good boundary for future orchestration wrappers. |
| Source/parser adapters | Deterministic file/fixture parsing and builders. | `src/law_nexus/adapters/sources/*`, M079/M080 package migrations. | Candidate for incremental file-event jobs, but parsing itself should remain deterministic. |
| Scripts | CLI/proof wrappers run to completion. | `scripts/build-*`, `scripts/verify-*`; M077-M080 residual script migration docs. | Keep as reproducible proof/compatibility entrypoints. Reactive layer should call package APIs, not scripts. |
| Graph/retrieval/embedding proofs | Mostly proof-runtime wrappers and adapter helpers. | GitNexus query returned `run_proof`, FalkorDB connect/query flows; `proof_environment`, retrieval proof helpers. | Async may help external I/O and long jobs, but proof semantics need dedicated milestones. |
| Legal Nexus orchestrator | Architecture concept only, not validated runtime. | `prd/ARCHITECTURE.md` mentions `COMP-LEGAL-NEXUS-ORCHESTRATOR` as unimplemented/unproven. | Natural future home for reactive orchestration, but currently [proposed]/[bounded]. |

## Current async/reactive inventory

Code inventory found no broad async runtime layer in `src/law_nexus`. There are scattered text hits for `stream`, `event`, `build`, `run`, and `check`, but these are mostly deterministic parsing/proof terms, not an event-driven runtime.

Current state:

- no project-wide event bus;
- no durable job queue;
- no async use-case interface family;
- no async graph/retrieval orchestration layer;
- no durable retry/dead-letter model;
- no file-watch or source-change event pipeline;
- no live reactive UI/API runtime.

This is not a defect by itself. For the current project maturity, deterministic batch proof is valuable because it keeps evidence reproducible.

## Candidate boundaries for reactive/asynchronous adoption

| Candidate | Why it fits | Example future event/job | Required guardrails |
|---|---|---|---|
| Source discovery and fixture inventory | File-system/source changes are naturally event-like. | `SourceDiscovered`, `SourceFingerprintChanged`, `FixtureInventoryBuilt`. | Stable source IDs, idempotent writes, source hash checks, no legal claim promotion. |
| Parser/source structuring jobs | Parsing can be long-running and independent per source. | `ParseRequested`, `ParserRecordBuilt`, `ParserDiagnosticRaised`. | Deterministic parser outputs, bounded diagnostics, artifact freshness checks. |
| Golden-case evaluation | Evaluation is already a repeatable check over artifacts. | `GoldenCasesBuilt`, `GoldenCasesEvaluated`, `RegressionDetected`. | Fail-closed diagnostics, versioned golden cases, explicit non-claims. |
| Graph ingest/proof jobs | Graph load/proof can be external I/O bound. | `GraphLoadRequested`, `GraphLoadSucceeded`, `GraphLoadFailed`. | Idempotent graph writes, proof-level labels, no production FalkorDB claim without runtime proof. |
| Retrieval/embedding evaluation | Embeddings and retrieval benchmarks can be slow and resource-bound. | `EmbeddingBatchQueued`, `RetrievalBenchmarkCompleted`. | Managed GigaChat paths remain excluded; local model provenance; quality non-claims. |
| Legal Nexus orchestration | Future runtime needs query planning, policy checks, retrieval, graph queries, answer validation. | `LegalQueryReceived`, `PlanProposed`, `EvidenceResolved`, `AnswerValidated`. | LLM non-authoritative, citation-safe output validator, policy gates, audit log. |

## Boundaries that should stay synchronous/pure

| Boundary | Why not make it async first |
|---|---|
| Domain objects and policies | Deterministic, testable, low-I/O; async would reduce clarity. |
| Parser record validation | Should remain simple, local, fail-closed checks. |
| Generated-Cypher safety policy | Must stay deterministic and easy to reason about. |
| Citation-safe answer validation rules | Should be pure/observable before any async runtime wraps them. |
| Architecture proof/registry claims | Derived governance surfaces are not runtime source truth and should not become event authority. |

## What a reactive/asynchronous law-nexus would give

Potential benefits:

1. **Incremental processing** — only changed sources need re-parsing, re-indexing, and re-evaluation.
2. **Better long-job handling** — parser, graph ingest, embedding, and retrieval benchmarks can become resumable jobs instead of one-shot scripts.
3. **Failure visibility** — durable job state can record phase, source hash, last error, retry count, and proof level.
4. **Parallelism where safe** — independent documents/cases can process concurrently after source IDs and output paths are stable.
5. **Agent-friendly operations** — future agents can inspect a queue/job ledger instead of re-running broad scripts blindly.
6. **Future interactive UX** — Legal Nexus can eventually react to query events, evidence resolution, and validation states.
7. **Reduced recomputation** — event fingerprints can avoid rebuilding unchanged parser/retrieval/graph artifacts.

Main costs and risks:

1. **Complexity overhead** — queues, events, retries, idempotency, and observability are extra architecture, not free performance.
2. **Debuggability risk** — async failures are harder to reproduce unless every job has durable inputs, outputs, and failure state.
3. **Premature runtime drift** — building orchestration before parser/source data is ready can repeat the ACP-era meta-drift problem.
4. **Consistency hazards** — partially completed jobs can make artifacts disagree unless state transitions are explicit.
5. **Proof ambiguity** — event logs are operational evidence, not legal/product proof; proof gates still need tracked artifacts/tests/runtime evidence.
6. **I/O contention** — concurrent graph/file writes can corrupt or race unless write ownership is single-writer or transactional.
7. **Async everywhere anti-pattern** — making pure domain/application logic async would add ceremony without value.

## Architecture options

### Option A — Stay batch-only for now

Keep scripts and package use cases as deterministic run-to-completion workflows.

Pros:

- lowest complexity;
- easiest to reproduce;
- best fit for current bounded proof stage;
- no new infrastructure.

Cons:

- broad rebuilds stay expensive;
- long jobs remain brittle;
- poor incremental observability;
- future interactive runtime still unplanned.

Best when: parser/source data is still unstable and product runtime is not ready.

### Option B — Async-first rewrite

Convert many package APIs and scripts to async, introduce an event bus/queue, and route most execution through it.

Pros:

- maximum concurrency potential;
- clear runtime direction if product were already ready;
- can support interactive UX sooner.

Cons:

- high churn;
- likely over-engineering now;
- risks hiding deterministic proof semantics;
- would require idempotency/locking/observability before value appears;
- conflicts with bounded-wave migration discipline.

Best when: there is a validated runtime product path and stable data contracts. That is not the current state.

### Option C — Bounded reactive shell around synchronous core (recommended)

Keep domain/use-case logic deterministic and synchronous. Add a thin asynchronous/reactive orchestration shell later around package APIs for source-change events, job state, retries, and observability.

Pros:

- preserves reproducibility;
- gives incremental processing and job visibility where useful;
- avoids async pollution in pure logic;
- compatible with current package-boundary migration work;
- allows per-seam adoption and proof.

Cons:

- still needs a job/event data model;
- requires careful idempotency and single-writer rules;
- benefits arrive gradually;
- future runtime queue must be tested like product code, not treated as docs.

Best when: current project needs an architecture direction without destabilizing deterministic proof gates.

## Recommended adoption ladder

**Recommendation:** choose Option C: **bounded reactive shell around a synchronous deterministic core**.

Suggested waves:

1. **[proposed] Event vocabulary only** — define events and lifecycle states, no runtime queue yet.
2. **[proposed] Job ledger prototype** — local durable job records for source/parser/golden-case tasks, with phase/error/retry/source-hash fields.
3. **[proposed] Source-change pilot** — one event family for source inventory or parser fixture fingerprint changes.
4. **[proposed] Parser job pilot** — queue parser/golden-case work per source/case while keeping existing scripts as compatibility wrappers.
5. **[proposed] Graph/retrieval job pilots** — only after source/parser outputs are stable and proof gates exist.
6. **[deferred] Legal Nexus runtime orchestration** — only after validated source/retrieval/graph contracts exist.

Minimum job record shape for a future implementation:

```text
job_id
job_type
source_ref or artifact_ref
input_fingerprint
status: queued | running | succeeded | failed | skipped | blocked
phase
attempt
last_error_code
last_error_message
started_at
finished_at
produced_artifacts
proof_level: proposed | bounded | smoke | validated
non_claims
```

## Trace and logging guardrails

A future reactive shell must be **traceable before it is concurrent**. Async without durable traces would make law-nexus harder to debug than the current deterministic scripts.

### Logging principle

Log **decisions and failure states**, not activity noise.

Useful events answer questions a future debugger will ask:

- why was this job dispatched, skipped, retried, blocked, or marked succeeded;
- which source/artifact fingerprint drove the decision;
- which proof level and lifecycle tag applied;
- which non-claims were carried forward;
- where the bounded output and diagnostics were written;
- what failed, in which phase, and whether retry is safe.

Avoid logs like “entered function X” or raw dumps of legal text, embeddings, model payloads, credentials, or provider responses.

### Minimum trace event shape

Future implementation events should be structured JSONL or equivalent records with stable fields:

```text
ts
trace_id
correlation_id
job_id
parent_job_id
event_name
component
phase
status_before
status_after
source_ref or artifact_ref
input_fingerprint
output_fingerprint
attempt
retryable
proof_level: proposed | bounded | smoke | validated
lifecycle_tag: proposed | bounded | smoke | validated | deferred
reason_code
message
safe_details
produced_artifacts
error_code
error_class
redaction_applied
non_claims
```

Field intent:

- `trace_id` follows one external request, source-change event, or batch run.
- `correlation_id` connects multiple jobs spawned by the same architecture operation.
- `job_id` identifies one durable unit of work.
- `input_fingerprint` and `output_fingerprint` prevent stale artifact confusion.
- `reason_code` should be machine-readable (`source_hash_changed`, `artifact_fresh`, `validation_failed`, `retry_exhausted`).
- `safe_details` must be bounded and secret-safe.

### Required event families

| Event family | Purpose | Example event names |
|---|---|---|
| Job lifecycle | Reconstruct job progression. | `job_queued`, `job_started`, `job_succeeded`, `job_failed`, `job_skipped`, `job_blocked` |
| Decision events | Explain branch decisions. | `source_fingerprint_changed`, `artifact_freshness_checked`, `retry_scheduled`, `non_claims_attached` |
| Failure events | Persist debuggable failure state. | `input_invalid`, `external_dependency_failed`, `write_conflict_detected`, `proof_gate_failed` |
| Artifact events | Link jobs to durable outputs. | `artifact_written`, `artifact_reused`, `artifact_stale`, `diagnostics_written` |
| Boundary events | Prevent proof/authority drift. | `proof_level_assigned`, `lifecycle_tag_assigned`, `claim_boundary_flagged` |

### Failure-state requirements

Every failed or blocked job must persist:

- final phase;
- safe input/artifact reference;
- input fingerprint;
- attempt count;
- last error code;
- bounded error message;
- retryability decision and reason;
- produced partial artifacts, if any;
- cleanup/recovery instruction;
- non-claims and proof-level tags.

A failure without a persisted reason is invalid for future reactive work.

### Redaction and portability rules

Trace/log records must not contain:

- credentials, tokens, environment secrets;
- raw embeddings or unnecessary vector payloads;
- unnecessary raw legal text;
- full provider payloads;
- ignored `.gsd/exec` proof anchors as durable source references;
- absolute local paths when a repository-relative path is available.

Use tracked repository-relative proof anchors and bounded excerpts/hashes. If a trace references legal/source evidence, it should point to tracked parser/source artifacts and source hashes, not duplicate large text.

### Trace bundle expectation

A future job-ledger implementation should be able to produce a compact trace bundle for one `trace_id` or `job_id` containing:

1. job summary;
2. lifecycle transition list;
3. decision events;
4. failure state, if any;
5. produced artifacts;
6. proof level and non-claims;
7. command/runtime evidence pointers.

This trace bundle is operational/debug evidence only. It must not be promoted into legal correctness, parser completeness, retrieval quality, or FalkorDB production proof.

## Decision recommendation

Record an architecture decision to **not** perform an async-first rewrite now. Instead, adopt a bounded reactive shell later, one proofable seam at a time, after event vocabulary and job observability requirements are explicit.

## Open questions for future milestones

1. What should be the first event family: source inventory, parser fixtures, golden cases, or graph ingest?
2. Should the job ledger be file-backed JSONL first, SQLite, or FalkorDB-backed only after graph proof maturity?
3. What is the single-writer rule for generated artifacts?
4. Which artifacts are safe to update concurrently?
5. How should GSD milestones consume job-state evidence without treating it as product proof?
