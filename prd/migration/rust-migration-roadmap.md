# Complete Rust transition roadmap

**Status:** `[proposed]` historical R0–R10 transition plan; not current-front authority after M165. Current position is `prd/ARCHITECTURE.md`.
**As-of note:** frozen as transition history on 2026-08-11 at `50173de`; completed sequence does not prove product readiness.
**Goal:** Rust-only product runtime, process-level Python repository harness,
complete ACP/git-lex decommission, and one parity-gated Python archival cutover.

## Non-negotiable boundaries

1. All product/domain behavior moves to Rust (R063).
2. No PyO3, FFI or in-process Python bridge.
3. Python product code remains intact until whole-system parity (R065).
4. Python product code is archived wholesale in one final cutover.
5. The Python harness is repository control only (R064).
6. ACP/git-lex leaves active law-nexus entirely; history is archived (R066).
7. Russian legal evidence, citation safety, deterministic Cypher validation and
   LLM non-authority remain product requirements independent of ACP.

## Execution topology

```text
M107 roadmap/crystallization
          |
D0 inventory + D1 disconnect git-lex hook + D2 preserve general gates
          |
          +-----------------------------+
          |                             |
D3-D6 ACP/git-lex archive        R0-R2 Rust foundation + H01-H04 harness
          |                             |
          +---------------+-------------+
                          |
                  R3-R8 Rust product implementation
                          |
                  R9 whole-system parity
                          |
                  R10 one Python archival cutover
```

Rust foundation and harness may run in parallel with bulk ACP history archival
after D1/D2 remove mutation and preserve general quality gates.

## Milestones and thin slices

### R0 — Reconcile and freeze behavioral baseline

**Risk:** high. **Depends:** M107.

- separate single-document and corpus artifact paths;
- rebuild one canonical corpus manifest;
- freeze hashes, semantic counts, schemas, reason codes and CLI contracts;
- reconcile `prd/ARCHITECTURE.md` contradictions and M105/current artifact drift;
- record fast/full test profiles without repeated rebuilds.

**Proof:** two builds are byte-stable; check mode is non-mutating; manifest and
oracle agree. No Rust implementation begins before this.

### R1 — Cargo workspace tracer bullet

**Risk:** medium. **Depends:** D1/D2, R0 contracts.

Slices:

- R1.1 workspace with `core`, `parser`, `graph`, `retrieval`, `application`, `cli`;
- R1.2 compile-time crate direction and workspace lint policy;
- R1.3 one minimal Rust CLI emits structured status;
- R1.4 CI runs `fmt`, `clippy -D warnings`, unit tests and docs;
- R1.5 architecture negative fixture proves forbidden edge fails.

No product logic yet beyond a tracer status path.

### R2 — Repository harness tracer bullet

**Risk:** medium. **Depends:** R1.3, D2.

Implement H01–H04 from `repository-harness-roadmap.md`: process runner,
architecture/ADR checks, Cargo profile and document freshness. It must launch
Rust only as subprocesses and reject product imports.

### R3 — Rust domain and serialization contracts

**Risk:** high. **Depends:** R0, R1.

Thin slices by aggregate:

1. source/document/edition identity;
2. source blocks and hierarchy types;
3. legal unit and evidence span;
4. citation and norm statement;
5. graph/retrieval request-result contracts;
6. schemas, stable reason-code errors and property tests.

Python product remains unchanged. Parity uses frozen JSON/schema fixtures.

### R4 — Consultant parser vertical slices

**Risk:** critical. **Depends:** R3.

Each slice must read a real fixture and emit the final Rust record shape:

1. document metadata + namespace/path errors;
2. raw block stream + stable identity;
3. article/part/clause hierarchy;
4. chapter/razdel/subclause and parentage;
5. zones and diagnostic-only markers;
6. FRBR act/edition IDs;
7. internal/external references;
8. temporal markers;
9. deontic lexemes and NormStatement candidates;
10. deterministic parallel corpus build.

Proof per slice: unit/property tests, positive/negative real fixtures, artifact
comparison and explicit non-claims. No component cutover.

### R5 — Parser artifact and golden pipeline

**Risk:** high. **Depends:** R4.

- record validation and schema CLI;
- hierarchy/relation/norm builders;
- staging graph builder;
- golden-case evaluator;
- source inventory/probe/identity diagnostics;
- check mode and manifest output;
- harness H05 parity integration.

Proof: canonical corpus outputs and all failure surfaces match the frozen
contract or document an explicitly accepted safer difference.

### R6 — Historical graph execution plan, superseded by ADR-0014

**Status:** `[deferred]` historical transition step; its FalkorDB-specific design
was retired and must not guide current implementation. Current RuVector work is
owned by ADR-0014 `[proposed]` and requires a separate evidence-backed roadmap.

**Risk:** high. **Historical dependencies:** R3, R5.

The original R6 planned a database client, parameterized graph access,
idempotent ingest, relation materialization, deterministic query safety,
integration tests, resource profiling and recovery. Those capability concerns
remain useful questions, but no historical backend, API, test, or deployment
assumption carries into current architecture.

This record proves neither RuVector readiness nor historical production scale.

### R7 — Retrieval and citation safety

**Risk:** high. **Depends:** R5, R6.

- local/open-weight embedding adapter;
- exact/vector/graph-filtered retrieval;
- EvidenceSpan and Citation assembly;
- no-answer and candidate-only behavior;
- output validator and reason codes;
- golden, representative and real-artifact cases;
- LLM composer, if retained, remains optional/non-authoritative.

Proof requires unresolved citation/evidence failures to remain fail-closed.

### R8 — Application and Rust product CLIs

**Risk:** medium. **Depends:** R5–R7.

- ingest/profile/build/load/retrieve/verify use cases;
- Rust composition root;
- stable JSON and human CLI output;
- jobs, phase/failure persistence, timeouts, cleanup and resource budgets;
- end-to-end observability.

All production entrypoints now exist in Rust, but Python remains untouched.

### R9 — Scale, security and whole-system parity

**Risk:** critical. **Depends:** R8, harness H05/H06.

Parallel verification classes:

- schema/determinism/failure parity;
- full corpus artifacts and golden cases;
- FalkorDB integration and cleanup;
- retrieval/citation/generative safety;
- memory and 1×/10× concurrency benchmarks;
- CLI/operational failures;
- dependency/security/license audit;
- independent review of tests and bare artifacts;
- complete UAT with Python product execution disabled.

Any missing capability blocks cutover; no partial archive override.

### R10 — One controlled Python product archival cutover

**Risk:** critical. **Depends:** R9 PASS and D6 PASS.

- create exact manifest of Python product files;
- move entire product implementation/tests/scripts superseded by Rust to
  `python_archive/product/` in one reviewed change;
- preserve allowed `harness/` Python CLI;
- remove Python product dependencies and entrypoints from CI/runtime;
- rewrite README, CHANGELOG, architecture, requirements and runbooks;
- final active-tree scan proves Rust-only product;
- run full Rust CI, harness checks and UAT after the move.

Rollback is the cutover commit, not a runtime fallback.

## Continuous requirements

Every implementation slice must include:

- tests for changed/new Rust behavior;
- one relevant failure/diagnostic check;
- GitNexus/codebase intelligence before high-impact edits and after changes;
- architecture/crate-boundary verification;
- documentation freshness assessment;
- no legal/product claims beyond evidence;
- no ACP/git-lex reintroduction;
- no Python product logic in the harness.

## Definition of done

The transition is complete when Rust is the only active product runtime, all
capabilities and safety contracts pass whole-system proof, performance/memory/
concurrency budgets pass, ACP/git-lex is archive-only, Python product code is
archive-only, and the optional Python harness can be removed without changing
product behavior.
