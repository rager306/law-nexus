# law-nexus Forward Roadmap

**Date:** 2026-07-24
**Status:** `[proposed]`
**Sequence authority:** M130 is repository-control debt; this roadmap owns the non-conflicting product sequence M131–M140 and supersedes older product milestone numbering.
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

An isolated external harness reported bounded synthetic behavior for RVF
create/insert/search/reopen, GraphDB CRUD/persistence, hybrid/reranking components,
toy temporal records and hand-built query demos. It used synthetic fixtures and
placeholder embeddings. This is research input, not tracked product proof and not
a readiness claim.

Real corpus, TEI embedding, cross-store recovery, typed KnowQL execution and
citation byte traceability are not verified. `ruvector-graph` Cypher execution is
not relied upon; law-nexus owns a typed application executor over storage ports.

### What's missing (critical gaps)

| Gap | Severity | Blocks |
|-----|----------|--------|
| ODT adapter (Garant .odt) | CRITICAL | Reading Garant source files |
| hierarchy.rs, references.rs, temporal.rs, deontic.rs | CRITICAL | Legal structure extraction |
| Real TEI HTTP embedding (USER-bge-m3 1024d, not HashEmbedding) | HIGH | Semantic retrieval quality |
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
| 0007 | Python harness | `[proposed]` | Executable governor and composed preflight contracts | Milestone-close operational evidence |
| 0008 | Authority ceiling | `[bounded]` | HC-04/15/16 PASS | Real authority flow with corpus |
| 0009 | Five-clock temporal | `[bounded]` | HC-09 PASS | Real legal-date parsing |
| 0010 | Evidence kernel | `[bounded]` | HC-05/07/08/10/14 PASS | Real graph evidence storage |
| 0011 | KOF-DA ownership | `[bounded]` | 20 owners proven | Production enforcement |
| 0012 | Evidence protocol | `[bounded]` | M111/M112 applied | Applied to every future selection |
| 0013 | Universal parser | `[bounded]` | Independent Consultant/Garant adapters, shared hierarchy/morphology/sentence primitives and one tracked real document per provider | References/temporal/deontic candidates, representative golden corpus and citation mapping |
| 0014 | RuVector infra | `[proposed]` | Bounded external synthetic research only | TEI, real corpus, recovery, typed queries and exact citations |

## Roadmap

Critical path (each milestone blocks the next):

```text
M131: Parser Domain Types + Morphology
   ├── M131-S1: ln-decode domain types: ParsedBlock, ParagraphStyle,
   │            HierarchyLevel, HierarchyNode
   ├── M131-S2: morphology.rs: stem_match(), negation detector
   │            (стать[ьяейёю], пункт[ауомы], обязан[аоы]?, вправе)
   └── M131-S3: sentence_split.rs: LegalSentenceSplitter
                with legal abbreviations allowlist
   Verify: cargo test -p ln-decode passes
   Promotes: ADR-0013 [proposed] → [bounded] (domain types only)
```

```text
M132: Hierarchy Extractor + Consultant Bounded Parse [complete]
   Independent fail-closed WordML adapter behind BlockDecoderPort
   Shared bounded markers: Раздел, Глава, §, Статья
   One tracked real Consultant fixture: 167 blocks / 22 supported markers
   Non-claims: no full hierarchy, corpus parity or citation mapping
```

```text
M133: ODT Adapter + Garant Bounded Parse [complete]
   Pinned minimal zip + in-memory bounded content.xml intake
   Independent fail-closed ODF adapter; no WordML assumptions
   Provider comments retained as classified blocks and excluded by later shared extractors
   One tracked real 44-fz.odt: 5,124 blocks / 140 supported markers
   Non-claims: no full ODF/style coverage, corpus parity or citation mapping
```

```text
M134: Shared Lexical Candidate Extractors [active]
   ReferenceMention: bounded forms of статья/пункт + number; no endpoint resolution
   TemporalPhrase: вступает/утрачивает силу forms; no date or five-clock fact
   DeonticLexeme: обязан/вправе/запрещается + lexical negation; no NormStatement
   All operate on ParsedBlock text and exclude ProviderComment blocks
```

```text
M135: Parser Golden Pipeline
   GoldenEvaluator: parse vs human-verified fixtures
   Corpus coverage report
   Cross-format validation (Consultant vs Garant same law)
   Parser self-improvement: marker hit-rate, unknown form collector
   Verify: parser quality stable across corpus
   Promotes: ADR-0013 [bounded] → [validated]
```

```text
M136: RuVector Integration
   M136-S1: Storage port contracts and bounded dependency probe
             Define VectorStorePort and GraphStorePort before adapters
             Verify selected crate revisions, licenses and minimal APIs
   M136-S2: TEI HTTP embedding adapter
             USER-bge-m3 1024d through EmbeddingPort
             Validate model identity, dimensions, finite values and failures
             Verify: real Russian legal text → exactly 1024d vector
   M136-S3: RVF and redb adapters with recovery
             Materialize real parser records through application ports
             Add operation journal, idempotent replay and failure injection
             Verify reopen, reconciliation and competing-writer behavior
   M136-S4: Real retrieval and citation gate [PROMOTES ADR-0014]
             Measure lexical/dense complementarity on a real temporal corpus
             Execute typed KnowQL operations without Cypher-stub reliance
             Enforce exact source-span citation and fail-closed no-answer
             Promotes ADR-0014 [proposed] → [bounded] only
```

```text
M137: KnowQL Executor
   Real parser (pest or nom grammar)
   AST → RuVector operations translator
   7 query types from PoC become production:
     FIND ARTICLE, FIND ABOUT, FIND REFERENCES,
     FIND OBLIGATIONS, FIND HISTORY, FIND DEONTIC, CITE
   Witness integration (every query logged)
```

```text
M138: Application Composition + Product CLI
   Composition root wiring ln-decode → ln-promote → ln-publish → ln-storage
   Product CLI: ingest → profile → build → load → retrieve → verify → status
   Job management: phase/failure persistence, timeouts, cleanup
```

```text
M139: Whole-System Acceptance
   Rust contracts and real evidence are authoritative
   Frozen Python artifacts are bounded comparison inputs only
   End-to-end test: real source document → query → byte-traceable answer
   1× corpus benchmark; security/license audit
   UAT with Python product disabled
```

```text
M140: Python Product Archival Cutover
   Move src/law_nexus/ → python_archive/product/
   Keep src/law_nexus_harness/ as control-plane
   Update all docs for Rust-only
   Promotes: ADR-0004 → [validated], ADR-0005 → [validated]
```

## Priority and Critical Path

| # | Milestone | Depends on | Blocks | Est. scope |
|---|-----------|-----------|--------|------------|
| 1 | M131 | — | M132-M135 | Foundation: types + morphology |
| 2 | M132 | M131 | M135 | Hierarchy on real Consultant files |
| 3 | M133 | M131 | M135 | ODT adapter (Garant source format) |
| 4 | M134 | M131 | M135 | References, temporal, deontic extractors |
| 5 | M135 | M132-M134 | M136 | Golden corpus + parser validation |
| 6 | M136 | M135 | M137-M139 | RuVector + TEI + recovery + citation contract |
| 7 | M137 | M136 | M138 | KnowQL executor (production parser) |
| 8 | M138 | M137 | M139 | Product CLI |
| 9 | M139 | M138 | M140 | Parity + benchmarks + UAT |
| 10 | M140 | M139 | — | Python archival |

**Critical path: 10 milestones.** After M131, the Consultant hierarchy, Garant ODT and shared extractor slices can advance independently where their inputs do not overlap; M135 joins their evidence. Storage, query, composition, acceptance and archival remain sequential after that join.

## Verification Gates (where lifecycle tags advance)

| Gate | What it proves | ADR transition |
|------|----------------|-----------------|
| After M131-S3 | Domain types compile + morphology patterns tested | ADR-0013 [proposed]→[bounded] (domain only) |
| After M135 | Parser pipeline works end-to-end on real corpus | ADR-0013 [bounded]→[validated] |
| After M136-S3 | Real parser records persist and recover across RVF/redb failures | ADR-0014 remains [proposed] |
| After M136-S4 | Real temporal retrieval plus exact citation tamper matrix | ADR-0014 [proposed]→[bounded] |
| After M139 | Whole-system acceptance with Python disabled | ADR-0004/0005/0014 may advance only if every planned gate passes |
| After M140 | Python product archived; Rust-only active | All ADRs at final lifecycle |

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
- External RuVector synthetic harness results are not end-to-end pipeline claims.
- Real corpus integration (TEI USER-bge-m3 1024d, real Consultant/Garant documents) remains unproven.
- No legal correctness claim at any stage.
- No performance claim at scale (corpus size, query latency under load).
