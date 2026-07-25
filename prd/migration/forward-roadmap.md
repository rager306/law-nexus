# law-nexus Forward Roadmap

**Date:** 2026-07-24
**Status:** `[proposed]`
**Source ADR set:** 0004, 0005, 0007, 0008, 0009, 0010, 0011, 0012, 0013, 0014
**Decisions:** D130 (KnowQL), D131 (stem morphology), D132 (RuVector), D133 (proof ceiling)

## State of the System

### What's proven (20/20 hostile cases)

All 20 hostile-case contracts have bounded runtime PASS:

| HC | Crate | What it proves |
|----|-------|----------------|
| HC-01 | ln-observe | Source boundary, partial-byte rejection |
| HC-02 | ln-inventory | Idempotent curated intake |
| HC-03 | ln-dispose | Premature-promotion rejection |
| HC-04 | ln-promote | Dual-commit / mismatch rejection |
| HC-05 | ln-decode | Malicious decoder rejection |
| HC-06 | ln-gate | In-place bypass rejection |
| HC-07 | ln-identity | Erasure / cross-family merge rejection |
| HC-08 | ln-relation | Open-relation rejection |
| HC-09 | ln-temporal | Clock substitution rejection |
| HC-10 | ln-work | Progress-to-legal mapping rejection |
| HC-11 | ln-closure | Progress-as-completeness rejection |
| HC-12 | ln-projection | Authoritative-label injection rejection |
| HC-13 | ln-admission | Vendor-capacity inflation rejection |
| HC-14 | ln-replay | Duplicate-effect injection rejection |
| HC-15 | ln-publish | Competing-writer rejection |
| HC-16 | ln-accelerate | Label mutation / direct-promotion rejection |
| HC-17 | ln-query | Gap-invention rejection |
| HC-18 | ln-citation | Mirror-relabel / anchor-invention rejection |
| HC-19 | ln-diagnostic | Secret / raw-text / injection blocking |
| HC-20 | ln-conformance | Meta-suite aggregation (20/0/0) |

These prove **adversarial contracts only**. Real product behavior is unproven.

### What's proven (parser infrastructure)

- `WordMLStreamingDecoder` (quick-xml NsReader, zero-copy)
- Tested on real 22MB Consultant XML file: 53,119 paragraphs extracted without OOM
- binData base64 blobs skipped
- WordML namespace handling correct

### What's proven (RuVector infrastructure)

25 isolated functional checks in `/tmp/ruvector-test`:

| # | Capability | Status |
|---|-----------|--------|
| 1–8 | RVF store: create, ingest, search, persist | ✅ |
| 9–10 | GraphDB: nodes, edges, hyperedges, property filter | ✅ |
| 11–12 | GraphDB redb persistence | ✅ |
| 13 | BM25 hybrid search (RRF) | ✅ |
| 14–15 | GNN reranking (diffusion, mincut) | ✅ |
| 16 | Cypher parse + semantic analysis | ✅ |
| 17 | RAG multi-hop (KnowledgeGraph) | ✅ |
| 18 | Dual storage pipeline (RVF + redb) | ✅ |
| 19 | Temporal point-in-time query | ✅ |
| 20 | Version history (sorted lineage) | ✅ |
| 21 | Amendment chain (SUPERSEDED_BY) | ✅ |
| 22 | KnowQL FIND ARTICLE | ✅ |
| 23 | KnowQL FIND REFERENCES | ✅ |
| 24 | KnowQL FIND OBLIGATIONS | ✅ |
| 25 | KnowQL FIND HISTORY + CITE | ✅ |

**These are bounded synthetic proof only.** Real corpus, ONNX embedding, and citation byte-traceability are NOT verified (per ADR-0014 proof ceiling).

### What's missing (critical gaps)

| Gap | Severity | Blocks |
|-----|----------|--------|
| ODT adapter (Garant .odt) | CRITICAL | Reading Garant source files |
| hierarchy.rs, references.rs, temporal.rs, deontic.rs | CRITICAL | Legal structure extraction |
| Real ONNX embedding (USER-bge-m3, not HashEmbedding) | HIGH | Semantic retrieval quality |
| RuVector integration into law-nexus workspace | HIGH | Storage runtime |
| Authority flow: parser → ln-promote → ln-publish → store | HIGH | Real product pipeline |
| KnowQL parser (real syntax, not AST PoC) | MEDIUM | User-facing query |
| Witness audit pipeline (wired to operations) | MEDIUM | Evidence integrity trail |
| Citation contract enforcement (byte traceability) | MEDIUM | Verified legal answers |
| End-to-end integration test | HIGH | Pipeline validation |
| Golden corpus integration | MEDIUM | Quality baseline |

## ADR Status Matrix

| ADR | Topic | Lifecycle | What it proves | What it needs |
|-----|-------|-----------|----------------|----------------|
| 0004 | Rust migration | `[proposed]` | 41 crates, 20 HC PASS, WordML parser | Full product pipeline, Python archival |
| 0005 | Rust target architecture | `[proposed]` | Hexagonal pattern proven | ADR stale (proposes mega-crates; reality is per-HC ln-*) |
| 0007 | Python harness | `[proposed]` | Governor (27 pass), preflight (5 checks) | Consolidated CLI command groups |
| 0008 | Authority ceiling | `[bounded]` | HC-04/15/16 PASS | Real authority flow with corpus |
| 0009 | Five-clock temporal | `[bounded]` | HC-09 PASS | Real legal-date parsing |
| 0010 | Evidence kernel | `[bounded]` | HC-05/07/08/10/14 PASS | Real graph evidence storage |
| 0011 | KOF-DA ownership | `[bounded]` | 20 owners proven | Production enforcement |
| 0012 | Evidence protocol | `[bounded]` | M111/M112 applied | Applied to every future selection |
| 0013 | Universal parser | `[proposed]` | WordML adapter works | ODT adapter, hierarchy/morphology/refs/temporal/deontic extractors |
| 0014 | RuVector infra | `[proposed]` | 25 isolated checks | Real corpus + ONNX + citation contract |

## Roadmap

Critical path (each milestone blocks the next):

```text
M130: Parser Domain Types + Morphology
   ├── M130-S1: ln-decode domain types: ParsedBlock, ParagraphStyle,
   │            HierarchyLevel, HierarchyNode
   ├── M130-S2: morphology.rs: stem_match(), negation detector
   │            (стать[ьяейёю], пункт[ауомы], обязан[аоы]?, вправе)
   └── M130-S3: sentence_split.rs: LegalSentenceSplitter
                with legal abbreviations allowlist
   Verify: cargo test -p ln-decode passes
   Promotes: ADR-0013 [proposed] → [bounded] (domain types only)
```

```text
M131: Hierarchy Extractor + Consultant Full Parse
   Real 44-FZ file parsing: Глава → § → Статья → Часть → Пункт → Подпункт
   Tests against real consultant/ fixtures
   Verify: hierarchy matches frozen manifest for known files
```

```text
M132: ODT Adapter + Garant Parse
   zip crate + quick-xml NsReader on content.xml
   Style map: s1=BodyText, s9=Comment (ГАРАНТ), s15=Heading
   Provider comment filtering
   Critical: do NOT inherit WordML assumptions (per ADR-0013 correction)
   Verify: parse 44-fz.odt without OOM, extract structural text
```

```text
M133: References + Temporal + Deontic Extractors
   ReferenceExtractor: стать[ьяейёю] N, пункт N
   TemporalMarkerExtractor: вступает в силу, утрачивает силу
   DeonticDetector: обязан/вправе/запрещается + negation context
   All operate on ParsedBlock text (format-independent)
```

```text
M134: Parser Golden Pipeline
   GoldenEvaluator: parse vs human-verified fixtures
   Corpus coverage report
   Cross-format validation (Consultant vs Garant same law)
   Parser self-improvement: marker hit-rate, unknown form collector
   Verify: parser quality stable across corpus
   Promotes: ADR-0013 [bounded] → [validated]
```

```text
M135: RuVector Integration (replaces M135-M139 from previous roadmap)
   M135-S1: Workspace integration
             Add ruvector-core, ruvector-graph, rvf-runtime to law-nexus
             Create ln-storage crate (RuVector ↔ ln-* domain bridge)
             Verify: cargo build --workspace compiles
   M135-S2: ONNX embedding adapter
             USER-bge-m3 1024d via ort crate (ONNX Runtime)
             Implement EmbeddingProvider trait (not HashEmbedding)
             Verify: real Russian legal text → 1024d vector
   M135-S3: Real corpus verification gate [PROMOTES ADR-0014]
             Parse real 44-fz.odt → embed (USER-bge-m3) → store in RVF
             Parse same → graph nodes/edges → store in redb
             KnowQL query returns result traceable to source .odt
             Verify: byte offset matches source file
             Promotes: ADR-0014 [proposed] → [bounded]
   M135-S4: Citation contract enforcement [PROMOTES ADR-0014]
             Returned text must match source bytes exactly
             Source authority check (official vs mirror)
             Fail-closed no-answer behavior
             Promotes: ADR-0014 [bounded] → [validated]
```

```text
M136: KnowQL Executor
   Real parser (pest or nom grammar)
   AST → RuVector operations translator
   7 query types from PoC become production:
     FIND ARTICLE, FIND ABOUT, FIND REFERENCES,
     FIND OBLIGATIONS, FIND HISTORY, FIND DEONTIC, CITE
   Witness integration (every query logged)
```

```text
M137: Application Composition + Product CLI
   Composition root wiring ln-decode → ln-promote → ln-publish → ln-storage
   Product CLI: ingest → profile → build → load → retrieve → verify → status
   Job management: phase/failure persistence, timeouts, cleanup
```

```text
M138: Whole-System Parity
   Schema/determinism/failure parity vs frozen Python artifacts
   End-to-end test: real .odt → query → byte-traceable answer
   1× corpus benchmark; security/license audit
   UAT with Python product disabled
```

```text
M139: Python Product Archival Cutover
   Move src/law_nexus/ → python_archive/product/
   Keep src/law_nexus_harness/ as control-plane
   Update all docs for Rust-only
   Promotes: ADR-0004 → [validated], ADR-0005 → [validated]
```

## Priority and Critical Path

| # | Milestone | Depends on | Blocks | Est. scope |
|---|-----------|-----------|--------|------------|
| 1 | M130 | — | M131-M134 | Foundation: types + morphology |
| 2 | M131 | M130 | M134 | Hierarchy on real Consultant files |
| 3 | M132 | M130 | M134 | ODT adapter (Garant source format) |
| 4 | M133 | M130 | M134 | References, temporal, deontic extractors |
| 5 | M134 | M131-M133 | M135 | Golden corpus + parser validation |
| 6 | M135 | M134 | M136-M138 | RuVector + ONNX + citation contract |
| 7 | M136 | M135 | M137 | KnowQL executor (production parser) |
| 8 | M137 | M136 | M138 | Product CLI |
| 9 | M138 | M137 | M139 | Parity + benchmarks + UAT |
| 10 | M139 | M138 | — | Python archival |

**Critical path: 10 milestones, all sequential.** No parallelism possible because each milestone builds on the previous.

## Verification Gates (where lifecycle tags advance)

| Gate | What it proves | ADR transition |
|------|----------------|-----------------|
| After M130-S3 | Domain types compile + morphology patterns tested | ADR-0013 [proposed]→[bounded] (domain only) |
| After M134 | Parser pipeline works end-to-end on real corpus | ADR-0013 [bounded]→[validated] |
| After M135-S3 | Real 44-fz.odt → embed → store → query, byte-traceable | ADR-0014 [proposed]→[bounded] |
| After M135-S4 | Citation: returned text matches source bytes | ADR-0014 [bounded]→[validated] |
| After M138 | End-to-end Python parity PASS | ADR-0004 →[validated], ADR-0005 →[validated] |
| After M139 | Python product archived; Rust-only active | All ADRs at final lifecycle |

## Dependency Map (Cargo)

```toml
# ln-storage bridges domain types to RuVector
[dependencies]
ln-decode = { path = "../ln-decode" }              # ParsedBlock
ruvector-core = { version = "2", features = ["storage", "hnsw", "simd"] }
ruvector-graph = { version = "2", features = ["full"] }
rvf-runtime = { version = "2" }                    # RVF storage format

# ln-query uses KnowQL + RuVector
[dependencies]
ln-storage = { path = "../ln-storage" }
ln-decode = { path = "../ln-decode" }
ort = { version = "2" }                           # ONNX Runtime for USER-bge-m3

# ln-citation enforces byte traceability
[dependencies]
ln-storage = { path = "../ln-storage" }
ln-query = { path = "../ln-query" }
```

## Out of Scope

| Item | Why out |
|------|--------|
| LLM-based extraction | D098 anti-drift: LLM is non-authoritative; only algorithmic from source bytes |
| GigaChat integration | Memory: explicitly excluded |
| PyO3 / in-process Python bridge | ADR-0006 rejected |
| Production-scale (100K+ documents) | Not measured; bounded synthetic proof only |
| FalkorDB integration | Replaced by RuVector (ADR-0014) |
| `Old_project/` code reuse | Prior art only, not trusted implementation |

## Non-Claims

- This roadmap is `[proposed]` planning, not commitment.
- Milestone numbering and grouping may shift based on verification results.
- 20 HC bounded synthetic proofs are not production claims.
- 25 RuVector isolated checks are not end-to-end pipeline claims.
- Real corpus integration (USER-bge-m3 ONNX, real 44-fz.odt) remains unproven.
- No legal correctness claim at any stage.
- No performance claim at scale (corpus size, query latency under load).
