# law-nexus Project State

This package is the cold-reader entry point for the current `law-nexus` project state.

`law-nexus` is a proof-heavy LegalGraph Nexus repository. It is building verified architecture, parser/source-structuring, graph/retrieval, and Architecture Control Plane (ACP) foundations for Russian legal evidence workflows. It is not a production legal-answering system yet.

## Read this first

Use these files depending on what you need:

| Need | Read |
|---|---|
| Project overview | `prd/project-state/data/project-overview.json` |
| Roadmap | `prd/project-state/roadmap.md` |
| Architecture | `prd/project-state/architecture.md` |
| Verification status | `prd/project-state/verification.md` |
| ACP concept and state | `prd/project-state/acp.md` |
| Next-agent handoff | `prd/project-state/handoff.md` |

Diagrams live in `prd/project-state/diagrams/`. Machine-readable state lives in `prd/project-state/data/`.

## Current state

- Last completed milestone: `M046-x5gmog — ACP RDF Projection Hardening`.
- Active milestone: `M047-igv5e2 — law-nexus Project State Documentation Pack`.
- Current architecture registry counts: 63 items, 98 edges.
- Current ACP contribution: 5 governance items, 7 governance edges.
- Current RDF projection counts: 161 RDF resources, 422 Turtle statements.
- Current active requirements: `R035`, `R037`, `R038`.

## Source of truth

Authoritative evidence remains in PRD, GSD, ADR/decision artifacts, source code, tests, runtime proof, and real-document evidence.

The following are derived and non-authoritative:

- architecture JSONL registry projections;
- architecture graph reports;
- ACP recovery/projection outputs;
- RDF/SHACL/SPARQL projection outputs;
- this project-state documentation package;
- JSON summaries and Mermaid diagrams.

If this package conflicts with source evidence, the source evidence wins.

## What is verified

The current static architecture verifier passes. ACP record checks pass. The custom RDF projection check and non-writing diff pass. Focused RDF projection tests pass.

See `prd/project-state/verification.md` for commands and boundaries.

## What is not verified

The project-state package does not validate:

- `R035`;
- `R037`;
- `R038`;
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

## ACP in one paragraph

ACP is a reusable Architecture Control Plane. It tracks architecture prompt records, proposals, decision candidates, proof gates, health findings, allowed and blocked actions, non-claims, and recovery/projection surfaces. In `law-nexus`, ACP is proven as a bounded governance and projection layer, not yet as a full decision lifecycle workflow.

See `prd/project-state/acp.md` and `prd/project-state/diagrams/acp-control-plane.mmd`.

## Recommended next milestone

The recommended next milestone is **ACP Decision Lifecycle Workflow**.

It should define safe promotion from `decision_candidate` to accepted, deferred, rejected, or superseded decisions with authority checks, proof-gate checks, blocked-action enforcement, source-anchor safety, non-claim preservation, and R038-aware independent review evidence.

## Diagrams

- `prd/project-state/diagrams/system-overview.mmd`
- `prd/project-state/diagrams/acp-control-plane.mmd`
- `prd/project-state/diagrams/proof-boundary-map.mmd`
- `prd/project-state/diagrams/milestone-timeline.mmd`
- `prd/project-state/diagrams/data-flow.mmd`

## Verify current state

Run:

```bash
uv run python scripts/verify-architecture-graph.py
uv run python scripts/verify-acp-records.py
uv run python scripts/export-architecture-rdf-projection.py --check
uv run python scripts/export-architecture-rdf-projection.py --diff
uv run pytest tests/test_architecture_rdf_projection.py
```

Passing these commands means the current static and projection checks pass within their bounded scope. It does not promote any unverified product, legal, parser, runtime, or engine claims.
