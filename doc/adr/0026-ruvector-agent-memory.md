---
id: ADR-0026
title: RuVector as agent memory layer for the meta-parser
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-14
supersedes: none
related: [ADR-0014, ADR-0025, ADR-0019, ADR-0017]
---

# ADR-0026: RuVector as agent memory layer for the meta-parser

## Status

**Accepted [proposed]** — design recorded. Moves to `[bounded]` when the
graph port, vector port, and observation store ship with TDD coverage.

## Context

ADR-0025 establishes `ln-consultant-parser` as a separate crate for
Consultant-specific extraction (hyperlinks, catalog, cross-act edges).
The meta-parser design (this session) calls for a self-learning loop
where the parser accumulates observations, an agent proposes YAML
updates, and the system converges toward full coverage.

This requires a **persistent memory layer** that survives restarts,
stores graph relationships + vector embeddings + full-text indexes,
and enables semantic search and graph inference. ADR-0014 establishes
RuVector as the primary infrastructure (redb graph + RVF vectors +
BM25 hybrid + GNN reranking). USER-bge-m3 (1024d, local, open-weight)
is the bounded embedding baseline.

## Decision

RuVector serves as the **agent memory layer** for the meta-parser.
All extracted knowledge, observations, and learned patterns persist in
the graph (redb) and vector store (RVF).

### What persists in the graph (redb)

- Document nodes: Work, Expression, ComponentConcept, AmendingAct
- Edge nodes: CrossActEdge (amends/cites/implements/specifies/conflicts_with)
- Observation nodes: unresolved patterns, coverage gaps, ambiguous classifications
- Learning rule nodes: proposed YAML patches, validation results
- Edition chain nodes: per-edition AST snapshots with drift scores

### What persists in vectors (RVF)

- Article text embeddings: 1024d (USER-bge-m3)
- Semantic search: "find articles similar to ст. 93 44-ФЗ"
- BM25 hybrid: full-text + vector for document discovery

### SONA (Semantic Ontology Network Agent)

Graph-topology inference layer:
- Transitivity: A→B→C implies A indirectly_affects C
- Bridge detection: high-betweenness articles connecting domains
- Coverage heatmap: graph regions with sparse edges
- Pattern propagation: discovered patterns validated across corpus

### GNN reranking

Confidence recalibration based on graph neighborhood density:
- Dense neighborhood → higher confidence (corroborated by many edges)
- Sparse neighborhood → lower confidence (potential false positive)

### Agent cycle with RuVector

```
PARSE → STORE in graph + vectors → QUERY (Cypher/BM25/vector)
  → SONA infer → GNN rerank → PROPOSE (YAML patches, download queue)
  → VALIDATE (re-parse + delta) → PERSIST (idempotent MERGE)
```

## Consequences

- `ln-consultant-parser` depends on RuVector ports `[proposed]` (graph, vector, hybrid).
- Agent observations are durable — survive restarts, accumulate over time.
- Coverage tracking is a graph query, not a file scan.
- SONA infers relationships that the parser cannot extract from text alone.
- GNN provides confidence calibration beyond context-pattern matching.
- Idempotent MERGE: re-parsing updates, never duplicates.

## Non-claims

- `[proposed]` design: RuVector ports not yet implemented in ln-consultant-parser.
- USER-bge-m3 1024d is runtime compatibility evidence, not Russian legal
  retrieval quality proof (ADR-0014; S10).
- GigaChat/managed embeddings are excluded (human decision).
- SONA inferences are graph-topology-derived, not legal authority.
- GNN reranking is advisory confidence calibration, not legal proof.

## References

- ADR-0014 (RuVector primary infrastructure)
- ADR-0025 (Consultant parser separate crate)
- ADR-0019 (cross-act edge kinds)
- ADR-0017 (CTV; edition chain → diff → events)
- S10 (USER-bge-m3 1024d bounded baseline)
