# Architecture

This document describes the current `law-nexus` architecture at a cold-reader level. It is derived from `prd/project-state/data/architecture-map.json` and the architecture registry contract.

## Architecture thesis

`law-nexus` is organized around evidence-first architecture work. Claims should move from source evidence into generated projections and verification surfaces, not the other way around.

The architecture is designed to keep these concerns separate:

1. authoritative evidence;
2. generated registry projections;
3. static verification;
4. ACP governance records;
5. custom derived RDF/SHACL/SPARQL projections;
6. human and machine-readable project-state summaries.

See `prd/project-state/diagrams/system-overview.mmd` and `prd/project-state/diagrams/data-flow.mmd`.

## Layers

| Layer | Authority | Purpose |
|---|---|---|
| Source evidence | authoritative | PRD, GSD, ADR/decision artifacts, source code, tests, runtime proof, and real-document evidence. |
| Legal source structuring | bounded evidence | Consultant XML/source structuring and parser-related proof artifacts. |
| Architecture registry JSONL | generated-derived | Generated item and edge projections used for graph checks and generated views. |
| Architecture verifier | static-check | Checks registry freshness, graph integrity, source anchors, decision fitness, and claim-safety boundaries. |
| Architecture Control Plane | governance-derived | Tracks prompt records, proposals, decision candidates, proof gates, health findings, allowed/blocked actions, and recovery views. |
| RDF/SHACL/SPARQL projection | custom-derived | Diagnostics, recovery, and interoperability projection; not engine-backed proof. |
| Project-state docs | derived-summary | Markdown, JSON, and Mermaid summaries for cold-reader orientation. |

## Source-of-truth boundary

The authoritative layer is source evidence. Derived layers diagnose, summarize, or project architecture state. They do not replace source evidence.

This means:

- Generated JSONL is not architecture doctrine.
- Graph reports are not product readiness proof.
- ACP rows are governance records, not accepted decisions by default.
- RDF/SHACL/SPARQL outputs are custom derived projections, not source truth.
- This documentation package is a summary, not proof.

## Current architecture counts

Current derived registry counts:

- 63 architecture items;
- 98 architecture edges;
- 5 ACP governance items;
- 7 ACP governance edges.

Current RDF projection counts:

- 161 RDF resources;
- 422 Turtle statements;
- 0 current RDF projection diagnostics.

## Main data flow

The high-level data flow is:

```text
legal/source evidence
→ curated extraction
→ generated architecture JSONL
→ graph report and verifier
→ ACP governance/projection surfaces
→ project-state docs
```

The RDF projection flow is:

```text
architecture_items.jsonl + architecture_edges.jsonl
→ custom RDF projection exporter
→ Turtle / SHACL smoke / SPARQL handoff / RDF report
```

## What this architecture does not prove

The current architecture and verification surfaces do not prove:

- parser completeness;
- legal correctness;
- FalkorDB ingestion/runtime loading;
- retrieval quality;
- production readiness;
- independent external review;
- ontology correctness;
- RDF completeness;
- SHACL completeness;
- SPARQL engine correctness;
- git-lex compatibility;
- product Legal KnowQL behavior.

Those claims require separate proof and GSD milestones.
