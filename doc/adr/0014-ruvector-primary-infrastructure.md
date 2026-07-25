---
id: ADR-0014
title: RuVector as primary graph+vector infrastructure (replacing FalkorDB)
status: Accepted
lifecycle: "[proposed]"
date: 2026-07-24
superseds: portions of ADR-0012 (ruVector disposition upgraded from separate-role to primary candidate)
related: [ADR-0004, ADR-0005, ADR-0009, ADR-0010, ADR-0012, ADR-0013, D129, D130, D131]
---

# ADR-0014: RuVector as primary graph+vector infrastructure

## Status

**Accepted [proposed]** — decision recorded after functional verification of all
core capabilities. Moves to `[bounded]` when real legal corpus is ingested
through the full pipeline (parse → embed → graph → query), and to `[validated]`
when citation-safe retrieval returns verified legal answers.

## Context

ADR-0012 assessed ruVector as `separate-role` ("agent runtime, memory, adaptive
retrieval; never ledger or legal authority"). That assessment was based on
limited information. Direct study of the RuVector source code at
`/root/vendor-source/ruvector/` and functional testing of all critical
capabilities revealed that RuVector is a complete Rust-native graph+vector
database with MIT license — not merely an agent-side tool.

Simultaneously, the law-nexus project requires:
- Graph storage with Cypher queries, property filtering, hyperedges
- Vector search with HNSW indexing for 1024d USER-bge-m3 embeddings
- Hybrid search (BM25 + dense vector fusion) for legal text retrieval
- Temporal queries across multiple law editions
- Citation-safe evidence retrieval with byte-offset anchors
- Audit trail for evidence integrity
- All in Rust, MIT-licensed, embedded (no external services)

FalkorDB was the previous candidate but:
- SSPL license (not MIT)
- C-based Redis module (not Rust-native)
- No hybrid search (BM25+vector)
- No self-learning reranking
- No multi-hop RAG engine
- No COW branching for temporal snapshots
- No witness chains for evidence audit

## Decision

**Adopt RuVector as the primary graph+vector infrastructure for law-nexus `[proposed]`.**

### Storage architecture

```
┌────────────────────────────────────────────────────────────┐
│                  law-nexus application layer                │
│                                                            │
│  ln-decode → hierarchy → references → temporal → deontic  │
│  ln-relation → graph nodes/edges                          │
│  ln-query → KnowQL → vector + graph + temporal queries    │
│  ln-citation → EvidenceSpan + Citation assembly           │
└──────────────┬──────────────────────────┬─────────────────┘
               │                          │
       Vector operations          Graph operations
               │                          │
┌──────────────▼─────────┐ ┌──────────────▼──────────────┐
│   RVF file (.rvtext)   │ │   redb file (.redb)         │
│                        │ │                             │
│  VEC_SEG: embeddings   │ │  NODES_TABLE: graph nodes   │
│  INDEX_SEG: HNSW       │ │  EDGES_TABLE: edges         │
│  META_SEG: metadata    │ │  HYPEREDGES_TABLE           │
│  WITNESS_SEG: audit    │ │  METADATA_TABLE             │
│  CRYPTO_SEG: signing   │ │                             │
│  COW_MAP: branching    │ │  GraphDB Cypher engine      │
│  MANIFEST: 4KB boot   │ │  Hyperedges                 │
└────────────────────────┘ └─────────────────────────────┘
```

### Verified capabilities (functional test evidence)

| # | Capability | Test result | Evidence |
|---|-----------|-------------|----------|
| 1 | RVF store create (1024d, RvText, Cosine) | ✅ PASS | `RvfStore::create` returns dim=1024 |
| 2 | Vector ingest (batch, with metadata) | ✅ PASS | 5 legal texts ingested, 0 rejected |
| 3 | Vector search (HNSW, Cosine) | ✅ PASS | Query "принципы" → ranked results |
| 4 | RVF persistence (close → reopen → query) | ✅ PASS | Vectors survive reopen |
| 5 | GraphDB create_node + property query | ✅ PASS | 3 articles + hierarchy metadata |
| 6 | GraphDB create_edge + outgoing query | ✅ PASS | CONTAINS, REFERS_TO edges |
| 7 | GraphDB hyperedge (3+ nodes) | ✅ PASS | CO_REGULATES hyperedge created |
| 8 | GraphDB redb persistence | ✅ PASS | Nodes + edges survive reopen |
| 9 | GraphDB referential integrity | ✅ PASS | Edge to non-existent node rejected |
| 10 | BM25 hybrid search (RRF fusion) | ✅ PASS | BM25+vector combined ranking |
| 11 | GNN diffusion reranking | ✅ PASS | 3 reranker variants tested |
| 12 | GNN mincut reranking | ✅ PASS | Coherence-gated propagation |
| 13 | Cypher parse + semantic analysis | ✅ PASS | 3/3 queries (MATCH, WHERE, LIMIT) |
| 14 | RAG multi-hop (KnowledgeGraph) | ✅ PASS | 2-hop traversal: art:1→art:2→art:3 |
| 15 | Dual storage (RVF + redb) pipeline | ✅ PASS | Vector search → graph traversal works |
| 16 | Dual persistence (both survive) | ✅ PASS | RVF + redb reopen OK |
| 17 | Temporal point-in-time query | ✅ PASS | Article 1 on 2020-06-01 → edition 2019 |
| 18 | Version history (timeline) | ✅ PASS | 3 editions sorted by effective_from |
| 19 | Amendment chain (SUPERSEDED_BY) | ✅ PASS | 2014→2019→2024 lineage |
| 20 | Amendment attribution (AMENDED_BY) | ✅ PASS | 139-ФЗ linked to 2019 edition |
| 21 | Diff between editions (word-level) | ✅ PASS | Added/removed words identified |
| 22 | KnowQL FIND ARTICLE | ✅ PASS | Exact structural lookup |
| 23 | KnowQL FIND REFERENCES | ✅ PASS | Graph traversal from source article |
| 24 | KnowQL FIND OBLIGATIONS | ✅ PASS | Deontic property filter |
| 25 | KnowQL FIND HISTORY | ✅ PASS | Sorted temporal lineage |

### RuVector ADR-029: RVF as canonical format

Per RuVector ADR-029 (2026-02-13), RVF (RuVector Format) is the canonical
binary format for vector storage. Key implications for law-nexus:

- **VEC_SEG**: stores USER-bge-m3 1024d embeddings
- **INDEX_SEG**: HNSW progressive indexing (Layer A/B/C)
- **META_SEG**: legal text metadata, hierarchy level, byte offsets
- **WITNESS_SEG**: tamper-evident audit trail (complements C10/C12/C13 from ADR-0010)
- **CRYPTO_SEG**: Ed25519 + ML-DSA-65 post-quantum signatures for long-term legal integrity
- **COW_MAP_SEG**: Git-like branching for temporal snapshots ("law as of 2024-01-01")
- **Domain profile RvText**: optimized for sentence/document embeddings

redb remains as the graph property store (NODES_TABLE, EDGES_TABLE,
HYPEREDGES_TABLE) with ACID guarantees and mmap zero-copy loading.

### Dependencies

```toml
[dependencies]
ruvector-core = { version = "2", default-features = false, features = ["storage", "hnsw", "simd", "parallel"] }
ruvector-graph = { version = "2", default-features = false, features = ["full"] }
ruvector-gnn-rerank = { version = "2" }  # optional: self-learning reranking
rvf-runtime = { version = "2" }          # RVF storage format
rvf-types = { version = "2" }            # RVF segment types
```

All MIT-licensed. No SSPL, no NC, no proprietary dependencies.

### GNN guardrail

GNN self-learning reranking modifies search results based on usage patterns.
For the legal domain this is a **risk**: "improved" results could drift from
authoritative source text. Guardrail:

1. **Citation-safe assembly** uses baseline vector search results, NOT GNN-enhanced.
2. GNN-reranked results are **non-authoritative** — shown to operator as a hint only.
3. Every citation must trace to exact source text with byte offset, regardless of GNN.
4. The output validator (ln-diagnostic, HC-19) blocks any answer that cannot trace to source.

This preserves the D098 anti-drift principle: LLM and learning systems are
non-authoritative; only algorithmic citation from source text is authoritative.

### What RuVector does NOT replace

| law-nexus component | RuVector contribution | law-nexus owns |
|---------------------|-----------------------|----------------|
| ln-decode (parser) | Nothing | WordML/ODT streaming parser |
| Hierarchy extractor | Nothing | Regex markers (Глава/Статья/Часть) |
| Morphology | Nothing | Stem-based regex (стать[ьяейёю]) |
| References | Nothing | Case-aware regex extraction |
| Temporal (D118) | Nothing | Five-clock model in application |
| Authority (D116/D120) | Proof-gated mutation (infra) | Authority separation in application |
| Evidence kernel (D119) | WITNESS_SEG (audit infra) | C10/C12/C13 in application |
| Citation contract | Nothing | EvidenceSpan + byte offset + source authority |
| KnowQL | Cypher engine (infra) | KnowQL parser + AST + translator |
| Deontic detection | Nothing | Modal verb stem dictionary |

RuVector is **infrastructure**, not domain logic. law-nexus application layer
(ln-* crates) owns all legal semantics. RuVector stores, indexes, searches, and
audits — it does not interpret law.

### Impact on roadmap

```
Previous roadmap (FalkorDB-centric):
  M135: FalkorDB Rust Client        ← REMOVED
  M136: Graph Materialization       ← MERGED
  M137: Embedding Adapter           ← MERGED
  M138: Vector Retrieval            ← MERGED

New roadmap (RuVector-centric):
  M135: RuVector Integration
    ├── RVF vector store (RvText, 1024d, USER-bge-m3)
    ├── redb GraphDB (Cypher, hyperedges, properties)
    ├── EmbeddingProvider adapter (ONNX)
    ├── BM25 hybrid search (RRF fusion)
    ├── GNN reranking (optional, non-authoritative)
    ├── WITNESS_SEG audit trail
    ├── COW branching for temporal snapshots
    └── KnowQL executor (vector + graph + temporal)
```

One milestone replaces four. This is the most significant roadmap simplification.

## Alternatives Considered

### Option A: Stay with FalkorDB

**Pros:** Existing skills, prior art, S10 evidence.
**Cons:** SSPL license, C-based, no hybrid search, no self-learning, no RAG,
no COW branching, no witness chains. Strictly worse than RuVector for every
law-nexus requirement.

### Option B: Custom graph+vector implementation from scratch

**Pros:** Maximum control.
**Cons:** Months of work to reimplement HNSW, Cypher, BM25, GNN, RVF. RuVector
already provides all of these, MIT-licensed, Rust-native, tested.

### Option C: Hybrid FalkorDB + separate vector DB (Qdrant/Milvus)

**Pros:** Best-of-breed for each component.
**Cons:** Two external services, two licenses, operational complexity. RuVector
provides both graph and vector in one embedded library.

## Non-claims

- RuVector integration is `[proposed]` until real legal corpus is ingested end-to-end.
- No production-scale claim (100K+ articles) is made.
- GNN self-learning quality for legal domain is unmeasured.
- RVF format stability for long-term legal archival is unproven.
- FalkorDB is NOT removed — existing skills and prior art remain as reference.
- No legal correctness claim at any stage.

## References

- RuVector source: `/root/vendor-source/ruvector/`
- RuVector ADR-029: RVF canonical format
- Functional test results: 25/25 checks passed (this session)
- ADR-0010: Evidence kernel gates (C10/C12/C13)
- ADR-0012: Previous ruVector `separate-role` disposition (superseded by this ADR)
- ADR-0013: Universal parser architecture (feeds data into RuVector)
- D129: Product architecture matrix
- D131: Stem-based morphology decision
