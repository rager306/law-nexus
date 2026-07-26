---
id: ADR-0014
title: RuVector components as proposed graph and vector infrastructure
status: Accepted
lifecycle: "[proposed]"
date: 2026-07-24
related: [ADR-0004, ADR-0005, ADR-0007, ADR-0009, ADR-0010, ADR-0012, ADR-0013, D130, D131, D132, D133]
---

# ADR-0014: RuVector components as proposed graph and vector infrastructure

## Status

**Accepted `[proposed]`.** The direction is selected, but product integration and
readiness are not proven. Synthetic capability checks are bounded evidence only.

## Decision

Use selected RuVector components behind law-nexus ports as the proposed graph and
vector infrastructure:

- RVF-backed vector storage behind a law-nexus vector-store port;
- redb-backed graph CRUD behind a law-nexus graph-store port;
- hybrid retrieval components only after real-corpus complementarity evidence;
- witness or audit components only as infrastructure beneath law-nexus evidence
  and authority policy.

This is not a claim that RuVector is one ready, integrated database platform for
law-nexus. Application and domain layers own legal identity, hierarchy, temporal
state, authority, citations, query semantics, recovery policy and cross-store
consistency.

## Architecture boundary

```text
Rust domain
  legal identities, temporal state, evidence and citation invariants
       |
Rust ports
  EmbeddingPort | VectorStorePort | GraphStorePort | QueryExecutorPort
       |
Rust application
  ingest, materialize, retrieve, cite, recover
       |
adapters
  TEI HTTP       | RVF            | redb GraphDB   | typed KnowQL executor
```

Dependencies point inward. Adapters do not define domain policy. Python has no
product role and no PyO3, FFI or shared-library bridge is allowed.

### Embeddings

`[proposed]` `EmbeddingPort` will use an HTTP adapter to the separately operated
TEI service with `deepvk/USER-bge-m3` and 1024-dimensional vectors. The accepted
path is not in-process ONNX and not `HashEmbedding`; no product adapter claim is
made yet.

### Graph and KnowQL

law-nexus relies on verified GraphDB CRUD primitives, not on the current
`ruvector-graph` Cypher execution path. Source inspection found its sequential
executor returning an empty result, so it is not a product query engine proof.
KnowQL must have a law-nexus-owned typed application executor over graph/vector
ports. A hand-built AST demo does not prove a user-facing parser or executor.

### Cross-store consistency

RVF and redb are separate persistence components. Dual writes are not assumed
atomic. A product integration must define an operation journal, idempotent replay,
crash recovery, reconciliation and observable partial-failure state before any
combined-store readiness claim.

## Evidence and proof ceiling

The isolated RuVector harness demonstrated bounded synthetic behavior for RVF
create/insert/search/reopen, GraphDB CRUD/persistence, hybrid and reranking
components, temporal toy records, and hand-built query demos. This evidence:

- uses synthetic fixtures and placeholder embeddings;
- does not use real parsed Consultant or Garant records;
- does not prove legal retrieval quality or hybrid complementarity;
- does not prove crash consistency, concurrency or scale;
- does not prove exact citations or source-byte round trips;
- does not validate RuVector product integration.

Historical harness evidence is retained outside law-nexus as bounded research.
Durable law-nexus proof must use tracked repository-relative artifacts; absolute
local paths and raw provider payloads are not proof anchors.

## Promotion gates

ADR-0014 remains `[proposed]` until all required gates produce tracked evidence.

### Gate 1: TEI to RVF contract

- real Russian legal text is sent through the TEI HTTP adapter;
- response shape, model identity and exactly 1024 finite dimensions are checked;
- dimension/model mismatch, timeout and unavailable service fail closed;
- vectors persist and reopen through the selected RVF adapter.

Passing this gate is bounded integration evidence, not retrieval-quality proof.

### Gate 2: Real graph materialization

- real parser output is mapped through domain/application code into GraphDB CRUD;
- identity, hierarchy, temporal and evidence invariants remain law-nexus-owned;
- reopen and deterministic reconciliation are demonstrated.

### Gate 3: Recovery and concurrency

- journaled dual-store operation survives injected failures between RVF and redb;
- retry is idempotent and observable;
- competing writers cannot create contradictory authoritative state.

### Gate 4: Retrieval and citation

- a real temporal query uses a real document corpus;
- dense and lexical branches show measured complementarity;
- returned evidence is traceable to the exact source span;
- citation tampering and unsupported answers fail closed.

Only complete real-corpus integration plus recovery evidence may move the ADR to
`[bounded]`. `[validated]` additionally requires whole-system acceptance,
operational failure evidence, exact citation gates and representative UAT. No
single synthetic check can promote the lifecycle.

## Consequences

- FalkorDB is historical-only and has no active product, runtime or CI role.
- TEI is an external embedding adapter; service health is an operational
  dependency, not domain authority.
- RuVector dependencies are introduced only in thin proof slices after parser
  data is ready and after license/API verification at the selected revision.
- GNN or adaptive reranking remains non-authoritative and cannot bypass baseline
  evidence/citation policy.
- Product integration must preserve domain → ports → application → adapters.

## Non-claims

- No RuVector product runtime is currently ready.
- No real-corpus semantic quality, scale or legal-correctness claim is made.
- No Cypher executor capability is claimed.
- No cross-store atomicity or recovery capability is claimed.
- No citation byte-safety capability is claimed.
- No lifecycle level above `[proposed]` is claimed.

## Verification ownership

- Repository direction and lifecycle drift: `law-nexus-harness governor`.
- Early repository orchestration: `law-nexus-harness preflight`.
- Product proof: future Rust integration tests and tracked real-corpus evidence.
- Architecture registry reports remain derived and non-authoritative.
