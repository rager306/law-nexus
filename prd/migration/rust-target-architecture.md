# Rust target architecture

**Status:** `[proposed]`.  
**Authority:** ADR-0004, ADR-0005, ADR-0007; R063–R065.

## Target state

law-nexus product and domain behavior runs entirely in Rust. There is no PyO3,
FFI, shared-library Python bridge, or Python product fallback. A thin Python
repository-control CLI may remain only for process orchestration and repository
governance.

The current Python product remains intact until complete Rust parity. It is not
archived component-by-component. Final cutover moves it wholesale to
`python_archive/` after all gates pass.

## Workspace

```text
Cargo.toml                    # workspace membership, shared profiles/lints
Cargo.lock
crates/
├── law-nexus-core/           # pure domain, invariants, IDs, schemas
├── law-nexus-parser/         # Consultant XML and later Garant ODT
├── law-nexus-graph/          # graph records, Cypher safety, FalkorDB adapter
├── law-nexus-retrieval/      # embeddings, ranking, EvidenceSpan/Citation safety
├── law-nexus-application/    # ingest/retrieve/use-case orchestration
└── law-nexus-cli/            # Rust product binaries only
harness/                      # Python repository control plane (ADR-0007)
python_archive/               # historical Python after final cutover only
```

Start with these six crates. Split further only when a measured compile,
ownership, release or dependency seam justifies it.

## Dependency direction

```text
law-nexus-cli
      |
law-nexus-application
   /          \
law-nexus-parser   law-nexus-retrieval
      \          /          |
        law-nexus-graph -----+
              |
        law-nexus-core
```

Enforced rules:

1. `law-nexus-core` imports no other project crate and performs no I/O.
2. Adapters implement traits owned by inner crates; inner crates never import
   concrete adapters.
3. `law-nexus-application` owns use-case orchestration, not infrastructure.
4. `law-nexus-cli` is the Rust product composition root.
5. Python harness invokes `law-nexus-cli` processes only and never links crates.
6. ACP/git-lex is absent from workspace, dependencies, CI and product vocabulary.

## Crate responsibilities

### `law-nexus-core`

- source/document/edition identities and stable hash contracts;
- hierarchy levels and record forms;
- `LegalUnit`, `EvidenceSpan`, `Citation`, `NormStatement`;
- validation, fail-closed evidence rules and reason-code enums;
- generated-Cypher safety policy abstractions;
- serde and schemars representations;
- ports/traits for source parsing, graph access and embedding as needed.

Allowed dependencies should be small and deterministic: `serde`, `schemars`,
`thiserror`, hashing/time crates only when justified. No Tokio, HTTP, database,
filesystem or model clients.

### `law-nexus-parser`

- streaming Consultant WordML parsing via `quick-xml`;
- deterministic block and hierarchy extraction;
- FRBR-style act/edition identity derivation;
- internal/external references;
- preamble/appendix and diagnostic-only markers;
- temporal markers and deontic candidate extraction;
- source profiles and future Garant ODT support;
- ordered parallel file processing with deterministic merge.

Parsing errors are typed and contextual: source identity, phase, byte/element
location where available, reason code and safe detail. Raw legal text is not
logged by default.

### `law-nexus-graph`

- graph node/edge record contracts and staging graph builder;
- internal-reference resolution and unresolved-node preservation;
- generated-Cypher deterministic validation;
- FalkorDB Rust client adapter behind core/application traits;
- idempotent loading, counts, cleanup, retry classification and query timeouts.

The graph crate does not declare legal correctness from connectivity alone.

### `law-nexus-retrieval`

- local/open-weight embedding adapter boundary;
- exact, vector and graph-filtered retrieval composition;
- deterministic EvidenceSpan/Citation assembly and validation;
- no-answer behavior and candidate-only boundaries;
- bounded ranking metrics and benchmark records.

LLM composition, if retained, remains outer and non-authoritative. It cannot
bypass evidence or citation validation.

### `law-nexus-application`

- import, profile, build graph, retrieve and verify use cases;
- concurrency/resource orchestration;
- job/result status, retries and structured failure state;
- no concrete filesystem/database/model dependencies in use-case logic.

### `law-nexus-cli`

Product entrypoints:

```text
law-nexus source inventory
law-nexus source profile
law-nexus parse consultant
law-nexus graph stage
law-nexus graph load
law-nexus retrieve
law-nexus verify evidence
law-nexus status
```

All commands support stable JSON output, explicit output directories,
non-mutating check mode where meaningful, timeouts, structured exit codes and
secret-safe diagnostics.

## Concurrency model

- Rayon for independent CPU-bound file parsing and deterministic indexed merge.
- Tokio only for real async I/O boundaries (FalkorDB/network/model calls), not
  pure domain/parser functions.
- Bounded queues/channels with explicit memory budgets; no unbounded fan-out.
- Stable output order is independent of task completion order.
- One document failure is recorded without corrupting successful documents;
  policy decides fail-whole-run versus partial artifact publication.

## Memory model

- stream XML rather than constructing whole-document DOMs;
- process one block/document window at a time;
- retain only indexes needed for reference resolution;
- spill or two-pass where global resolution would exceed budget;
- expose peak RSS and allocation-sensitive benchmarks;
- avoid copies of full legal text in diagnostics and graph records.

## Error and observability contract

Every subsystem uses typed errors with:

- stable reason code;
- phase/component;
- source-safe identity;
- retryability;
- severity;
- context without secrets/raw provider bodies;
- causal source via `std::error::Error`.

CLI reports include duration, input/output fingerprints, counts, warning/error
summaries and artifact paths. The harness aggregates reports but does not
reinterpret legal semantics.

## Testing strategy

- unit and table tests for deterministic rules;
- property tests for IDs, ranges, hierarchy parentage and parser invariants;
- golden fixtures for source/artifact behavior;
- negative tests for malformed sources, invalid records, unresolved evidence,
  unsafe Cypher and citation failures;
- real FalkorDB integration tests with cleanup;
- benchmark and peak-memory scenarios;
- whole-system UAT with Python product execution disabled.

## Cutover invariant

No Python product directory moves until:

1. every capability in `python-capability-parity-matrix.md` is implemented;
2. reconciled artifact manifests reproduce in Rust;
3. Rust unit/property/integration/security/performance/UAT gates pass;
4. all product CLIs exist in `law-nexus-cli`;
5. the Python harness contains no product imports or rules;
6. a final repository scan proves Rust is the only product runtime.
