# law-nexus Product Architecture Matrix and Forward Roadmap

**Status:** `[proposed]`
**Date:** 2026-07-24
**Author:** pi session after M129 (20/0/0 hostile case aggregate)

## Current State

All 20 hostile cases have bounded Rust runtime PASS. These prove adversarial
contracts (dual-writer rejection, fail-closed, non-authority enforcement) in
synthetic hexagonal seams. They do NOT prove real product behavior.

### What exists

- **41 Rust crates** (20 domain + 20 runners + 1 status tracer)
- **Python product reference** (parser, hierarchy, retrieval, citation, staging)
- **Python harness** (governor, preflight, subprocess runner, architecture/ADR checks)
- **Frozen baselines** (corpus manifest, golden cases, ADR registry)

### What does NOT exist

- Real Rust parser for Consultant XML or Garant ODT
- Rust FalkorDB client or graph materialization
- Rust embedding/vector/retrieval pipeline
- Rust citation-safe answer assembly
- Rust product CLI beyond status/hc-runners
- ruVector integration
- Whole-system parity testing
- Any product capability validated as `[validated]`

## Matrix: Module → Deficiency → Feature → Milestone → Dependency

### Layer 1: Domain Types (R3)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Source/Document/Edition ID | ln-observe | Synthetic only; no real Rust types matching Python domain | Rust SourceDocument, ActEdition, SourceBlock, EvidenceSpan, NormStatement, LegalUnit, Citation types with serde/schemars | None | R0 baseline (done) |
| Hierarchy types | ln-observe | No Rust RawBlock/level/parent | Rust hierarchy types matching frozen manifest | None | Source types |
| Temporal types | ln-temporal | Synthetic clock only | Rust ActVersion, EffectiveDate, TimeBoundary | None | Source types |
| Authority types | ln-publish | Synthetic PublicationAuthority | Rust AuthoritySurface, PublicationRecord matching D120 | None | Source types |

### Layer 2: Parser (R4)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Consultant XML parser | ln-decode | Bounded real WordML adapter (M132); no FRBR IDs, relation builders or full corpus coverage | Real `quick-xml` streaming parser for Consultant XML: FRBR IDs, relation builders, golden evaluator | None | R3 domain types |
| Garant ODT parser | ln-decode | Bounded real ODT adapter (M133); no full ODF/style coverage or corpus coverage | Full ODF element/style coverage and multi-document Garant corpus | None | R3, Consultant parser |
| Parser pipeline | ln-decode | Shared hierarchy/morphology/sentence and reference/temporal/deontic lexical candidates (M131-M134); no relation/norm builders, staging graph builder or golden evaluator | Hierarchy/relation/norm builders, staging graph builder, golden evaluator | None | Both parsers |

### Layer 3: Graph (R5-R6)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| FalkorDB Rust client | None | Does not exist | Verified Rust client for FalkorDB with parameterized queries, timeouts, error taxonomy | ruVector could provide graph/vector bridge (separate-role) | R3-R5 |
| Graph materialization | ln-relation, ln-projection | Synthetic only | Real graph ingest: idempotent MERGE, relation/reference edges, cleanup | None | FalkorDB client |
| Generated Cypher safety | ln-query | Synthetic only | Deterministic Cypher validation before execution; parameter binding; injection rejection | None | FalkorDB client |

### Layer 4: Retrieval and Citation (R7)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Embedding adapter | None | Does not exist | Local/open-weight embedding model adapter (USER-bge-m3 or equivalent) in Rust | ruVector can provide vector store/compute (separate-role, ADR-0012) | R3 domain types |
| Exact retrieval | ln-query | Synthetic only | Article/clause exact match retrieval from materialized graph | None | FalkorDB graph |
| Vector retrieval | None | Does not exist | Vector similarity search over EvidenceSpan embeddings | ruVector vector store integration candidate; FalkorDB vector index alternative | Embedding adapter |
| Graph-filtered retrieval | ln-query, ln-relation | Synthetic only | Temporal + authority + relation graph traversal for filtered retrieval | None | Exact + vector retrieval |
| Citation assembly | ln-citation | Synthetic only | EvidenceSpan→Citation binding with source-authority check; missing-anchor fail-closed | None | Graph-filtered retrieval |
| Output validator | ln-diagnostic | Synthetic only | No-answer/candidate-only output validation; reason codes; safe diagnostic emission | ruVector diagnostic sink candidate (ADR-0012 separate-role) | Citation assembly |

### Layer 5: Application and CLI (R8)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Ingest use case | ln-observe, ln-inventory | Synthetic only | Real ingest: parse → profile → build → load → verify pipeline | None | R4-R7 |
| Composition root | None | Does not exist | Rust composition root wiring all adapters | None | All use cases |
| Product CLI | ln-status | Tracer only | Stable CLI: ingest, profile, build, load, retrieve, verify, status | None | Composition root |
| Job/state management | ln-work, ln-replay | Synthetic only | Phase/failure persistence, timeouts, cleanup, resource budgets | None | Product CLI |

### Layer 6: Conformance and Parity (R9)

| Module | Crates | Deficiency | Feature needed | ruVector/Other | Depends |
|--------|--------|------------|----------------|----------------|---------|
| Whole-system parity | ln-conformance | Oracle only | Schema/determinism/failure parity vs frozen Python artifacts | None | R3-R8 complete |
| Conformance meta-suite | ln-conformance | Honest oracle only | Real HC-01 through HC-20 verdicts from Rust product runtime | None | Whole-system parity |
| Performance benchmarks | None | Does not exist | 1×/10× corpus benchmarks; memory profile; concurrency | ruVector performance potential for vector compute | Product CLI |
| Security audit | None | Does not exist | Dependency/license/vulnerability audit | None | Product CLI |

### Layer 7: Python Cutover (R10)

| Module | Deficiency | Feature needed | Depends |
|--------|------------|----------------|---------|
| Python archival | Python product still active | Move all `src/law_nexus/` to `python_archive/product/`; keep `src/law_nexus_harness/` | R9 PASS |
| Docs rewrite | Docs reference Python product | Update README, ARCHITECTURE, ADR, requirements for Rust-only | Python archival |

## ruVector Integration Points

Per ADR-0012, ruVector is `separate-role`: agent runtime, memory, adaptive
retrieval, and optional graph/vector computation. It is never ledger or legal
authority. Integration candidates:

| Integration point | Phase | Role | Boundary |
|-------------------|-------|------|----------|
| Vector store for EvidenceSpan embeddings | R7 | Replace or augment FalkorDB vector index | Separate-role; law-nexus owns citation authority, not ruVector |
| Adaptive retrieval ranking | R7 | Boost/penalize retrieval candidates based on agent feedback | Non-authoritative; output validator must remain fail-closed |
| Diagnostic aggregation | R7-R8 | Aggregate and redact diagnostic signals across pipeline phases | Must route through ln-diagnostic safe emission; raw legal text forbidden |
| Agent memory for session context | R8+ | Store agent conversation/retrieval context across sessions | Separate-role; never product ledger or legal authority |
| Graph/vector computation acceleration | R7 | Batch vector similarity for large corpus retrieval | Performance optimization; correctness must be verifiable without ruVector |

**Key constraint:** ruVector may never become a hard dependency for product
correctness. If ruVector is unavailable, law-nexus must fall back to FalkorDB
vector index or exact retrieval. The output validator and citation assembly
must work identically with or without ruVector.

## Deficiency Priority (Клей — Fix Order)

Deficiencies must be fixed in dependency order. Each layer depends on the
previous one:

```text
R3 Provider-neutral parser domain contracts
  └─ R4 Parser adapters (Consultant XML and Garant ODT independently)
       └─ R5 Shared extractors and golden parser pipeline
            └─ R6 TEI HTTP + RuVector components behind Rust ports
                 └─ R7 Typed KnowQL, temporal retrieval and exact citations
                      └─ R8 Application composition and product CLI
                           └─ R9 Whole-system acceptance
                                └─ R10 Python cutover
```

## Forward Roadmap: Product Milestones M131–M140

M130 closed repository-control debt. The current product sequence is owned by
`prd/migration/forward-roadmap.md` and summarized here without creating a second
independent numbering scheme.

| Milestone | Phase | Title | Risk | Bounded output |
|-----------|-------|-------|------|----------------|
| M131 | R3 | Parser domain contracts and morphology foundation | high | Provider-neutral validated Rust types and deterministic primitives |
| M132 | R4 | Consultant hierarchy adapter | critical | Real Consultant XML hierarchy evidence against frozen fixtures |
| M133 | R4 | Garant ODT adapter | critical | Independent real ODT structural evidence; no WordML assumption inheritance |
| M134 | R4 | Shared reference, temporal and deontic extractors | critical | Format-independent bounded extractor contracts |
| M135 | R5 | Parser golden pipeline | high | Joined Consultant/Garant/extractor evidence and quality baseline |
| M136 | R6 | TEI and RuVector integration with recovery | high | HTTP embeddings, RVF/redb adapters and injected-failure recovery evidence |
| M137 | R7 | Typed KnowQL executor | high | law-nexus-owned typed operations over graph/vector ports |
| M138 | R8 | Application composition and product CLI | medium | Observable Rust composition root and job failure surfaces |
| M139 | R9 | Whole-system acceptance | critical | Real-source end-to-end, performance, security and UAT evidence |
| M140 | R10 | Python product archival cutover | critical | One controlled move after complete Rust acceptance |

After M131, Consultant, Garant and shared extractor slices may advance where
inputs are independent; M135 joins them. M136–M140 remain sequential. Every
lifecycle advancement requires its own tracked evidence and cannot be inferred
from synthetic infrastructure checks.

## Non-Claims

- This matrix is `[proposed]` planning. No product capability is claimed.
- ADR-0014 selects RuVector components at `[proposed]`; external synthetic
  research does not prove product integration, recovery, retrieval quality or readiness.
- FalkorDB is historical-only and has no active product milestone.
- TEI is an HTTP adapter behind `EmbeddingPort`, not embedded Python or in-process ONNX.
- All 20 hostile case crates are `[bounded]` synthetic proof, not product
  validation.
- Migration phases R3-R10 follow the frozen roadmap in
  `prd/migration/rust-migration-roadmap.md`.
