# law-nexus Forward Roadmap — ADR-Gap Analysis

**Date:** 2026-07-24
**Status:** `[proposed]`

## ADR Status Matrix

| ADR | Topic | Lifecycle | What's proven | What's missing |
|-----|-------|-----------|---------------|----------------|
| 0004 | Rust migration | `[proposed]` | Decision made; 41 crates exist; 20 HC PASS | Full product pipeline; parity; Python archival |
| 0005 | Rust target architecture | `[proposed]` | Crate structure exists; hexagonal pattern proven | ADR-0005 proposes `law-nexus-core`, `law-nexus-parser`, `law-nexus-adapters`, `law-nexus-app` — actual structure evolved to per-HC `ln-*` crates; ADR needs update |
| 0007 | Python harness | `[proposed]` | Harness exists: governor, preflight, subprocess runner | Consolidated CLI command groups (architecture check, cargo check, parity check, docs check) partially done |
| 0008 | Authority ceiling | `[bounded]` | HC-04/15/16 runtime PASS | Product storage/fencing; real authority enforcement |
| 0009 | Five-clock temporal | `[bounded]` | HC-09 runtime PASS | Real legal-date parsing; temporal database |
| 0010 | Evidence kernel | `[bounded]` | HC-05/07/08/10/14 PASS | Real graph evidence storage |
| 0011 | KOF-DA ownership | `[bounded]` | 20 exclusive owners proven | Production ownership enforcement |
| 0012 | Evidence protocol | `[bounded]` | Protocol applied to M111/M112 | Must be applied to every future selection |
| 0013 | Universal parser | `[proposed]` | WordML adapter works; ODT structure analyzed | ODT adapter; hierarchy extractor; morphology; references; temporal markers; deontic |

## Gap Analysis: ADR → Implementation

### Gap 1: ADR-0005 crate topology is stale

ADR-0005 proposes 4 mega-crates (`law-nexus-core`, `law-nexus-parser`, `law-nexus-adapters`, `law-nexus-app`).
Actual reality: 20 domain crates (`ln-observe`, `ln-decode`, ...) + 20 runners + 1 status tracer + harness.

**Action:** Update ADR-0005 to reflect the evolved crate topology (per-HC crates, not mega-crates).

### Gap 2: No real adapters exist (except WordML)

All 20 HC crates have synthetic in-memory adapters only. Real I/O adapters needed:

| Real adapter | For crate | Dependency | Status |
|---|---|---|---|
| WordML streaming decoder | ln-decode | quick-xml | ✅ done |
| ODT streaming decoder | ln-decode | zip + quick-xml | ❌ not started |
| FalkorDB Rust client | ln-relation, ln-projection | redis-rs or custom | ❌ not started |
| Embedding adapter | ln-query | candle/onnxruntime | ❌ not started |
| Filesystem inventory | ln-observe, ln-inventory | std::fs | ❌ not started |

### Gap 3: No shared post-processing extractors

ADR-0013 defines HierarchyExtractor, ReferenceExtractor, TemporalMarkerExtractor, DeonticDetector, LegalSentenceSplitter. None implemented.

### Gap 4: No product CLI

ADR-0005/0007 reference a composition root and product CLI (`cargo run -- ingest/profile/build/load/retrieve/verify`). Only `ln-status` tracer and HC runners exist.

### Gap 5: No embedding pipeline

USER-bge-m3 baseline established (S10, 1024d vectors, local). No Rust embedding adapter exists. ruVector integration candidate identified (ADR-0012 separate-role).

### Gap 6: No graph materialization

FalkorDB ingest path not implemented in Rust. CSV loader and Cypher generation not started.

## Roadmap: Dependency-Ordered Milestones

```text
M130: Parser Domain Types + Morphology (ADR-0013)
  │   ParsedBlock, ParagraphStyle, HierarchyLevel, HierarchyNode
  │   morphology.rs: stem patterns, negation detector
  │   sentence_split.rs: LegalSentenceSplitter
  │
  ├── M131: Hierarchy Extractor + Consultant Full Parse
  │     HierarchyExtractor on real Consultant XML
  │     Extract: Раздел/Глава/Статья/Часть/Пункт/Подпункт
  │     Test: real 44-FZ fixtures
  │
  ├── M132: ODT Adapter + Garant Parse
  │     zip crate + quick-xml NsReader on content.xml
  │     Style map: s1=BodyText, s9=Comment, s15=Heading...
  │     Provider comment filtering (ГАРАНТ blocks)
  │
  ├── M133: References + Temporal + Deontic Extractors
  │     ReferenceExtractor: стать[ьяейёю] N, пункт N
  │     TemporalMarkerExtractor: вступает в силу, утрачивает силу
  │     DeonticDetector: обязан/вправе/запрещается + negation
  │
  └── M134: Parser Golden Pipeline
        GoldenEvaluator: parse vs human-verified fixtures
        Corpus coverage report
        Cross-format validation (Consultant vs Garant same law)
        Parser self-improvement: marker hit-rate, unknown form collector

M135: FalkorDB Rust Client
  │   Evaluate: redis-rs vs custom FalkorDB client
  │   Cypher query execution, timeouts, error taxonomy
  │   Integration tests against running FalkorDB instance
  │
  └── M136: Graph Materialization
        Idempotent MERGE for hierarchy nodes
        REFERS_TO edges from ReferenceExtractor
        Temporal edges from TemporalMarkerExtractor
        Cleanup and idempotency verification

M137: Embedding Adapter
  │   Local USER-bge-m3 (1024d) via candle or onnxruntime
  │   EvidenceSpan → vector
  │   Batch embedding for corpus
  │
  ├── M138: Vector Retrieval
  │     FalkorDB vector index query
  │     ruVector integration pilot (optional, separate-role per ADR-0012)
  │     Similarity search over EvidenceSpan embeddings
  │
  └── M139: Citation-Safe Retrieval
        Exact + vector + graph-filtered retrieval
        EvidenceSpan + Citation assembly
        Output validator: no-answer, candidate-only, fail-closed
        Golden retrieval cases

M140: Application Composition + Product CLI
  │   Composition root wiring all adapters
  │   CLI: ingest → profile → build → load → retrieve → verify → status
  │   Job management: phase/failure persistence, timeouts
  │
  └── M141: Whole-System Parity + Scale
        Schema/determinism/failure parity
        1×/10× corpus benchmarks
        Security/license audit
        UAT with Python product disabled

M142: Python Product Archival Cutover
  │   Move src/law_nexus/ → python_archive/product/
  │   Keep src/law_nexus_harness/ as control-plane
  │   Update all docs for Rust-only
  │
  └── ADR-0005 update: mark [validated] after cutover
      ADR-0004 update: mark [validated] after cutover
```

## Priority Order (Critical Path)

| Priority | Milestone | Why first | Blocks |
|----------|-----------|-----------|--------|
| 1 | M130 | Domain types are foundation for everything | M131-M134 |
| 2 | M131 | Hierarchy extraction is core parser value | M134 |
| 3 | M132 | Garant ODT is second source format | M134 |
| 4 | M133 | References/temporal/deontic complete parser | M134 |
| 5 | M134 | Golden pipeline validates parser quality | M136 |
| 6 | M135 | FalkorDB client enables graph | M136 |
| 7 | M136 | Graph materialization enables retrieval | M138 |
| 8 | M137 | Embeddings enable semantic retrieval | M138 |
| 9 | M138 | Vector retrieval | M139 |
| 10 | M139 | Citation-safe answers | M140 |
| 11 | M140 | Product CLI | M141 |
| 12 | M141 | Parity gates | M142 |
| 13 | M142 | Python archival | — |

## ADR Updates Needed

| ADR | What needs updating | When |
|-----|-------------------|------|
| 0005 | Crate topology: mega-crates → per-HC ln-* crates | M130 start |
| 0004 | Lifecycle: `[proposed]` → `[bounded]` after M130 ships real types | After M130 |
| 0007 | Lifecycle: `[proposed]` → `[bounded]` after harness commands consolidated | After M130 |
| 0013 | Lifecycle: `[proposed]` → `[bounded]` after parser pipeline works end-to-end | After M134 |

## Non-Claims

- This roadmap is `[proposed]` planning, not commitment.
- Milestone numbering is sequential but may shift.
- ruVector integration (M138 optional) depends on ADR-0012 separate-role disposition.
- No legal correctness claim at any stage.
- Python archival (M142) only after whole-system parity PASS (M141).
