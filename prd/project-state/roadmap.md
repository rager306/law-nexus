# Roadmap

This roadmap summarizes both the project proof roadmap and the documentation-package roadmap. It is derived from `prd/project-state/data/roadmap.json` and `prd/project-state/data/next-milestones.json`.

## Project proof roadmap

| Range | Theme | Boundary |
|---|---|---|
| M001-M010 | Architecture review, PRD consistency, parser direction, and baseline architecture verification | Foundations only, not production readiness. |
| M011-M030 | GraphRAG, FalkorDB, retrieval, ontology, evidence, and semantic scoring proof cycles | Bounded proof cycles, not final retrieval quality or ontology/product readiness. |
| M031-M034 | Consultant XML source structuring, MiniMax-assisted discovery, graph context staging, and workline recovery | Source workflow evidence, not parser completeness for all sources. |
| M035-M046 | Reusable ACP construction, default registry integration, RDF projection proof, and projection hardening | ACP governance/projection mechanics, not full decision lifecycle governance or RDF/SHACL/SPARQL engine proof. |
| M047 | Project-state documentation pack | Cold-reader docs, JSON, and diagrams; not new product/runtime proof. |

See `prd/project-state/diagrams/milestone-timeline.mmd` for the compressed timeline.

## Current milestone

`M047-igv5e2 — law-nexus Project State Documentation Pack` is active.

Its purpose is to create a cold-reader package with Markdown docs, parseable JSON summaries, and Mermaid diagrams while preserving source/projection and proof boundaries.

## M047 package roadmap

M047 builds the package in this order:

1. S01 — documentation contract and evidence inventory.
2. S02 — machine-readable project-state JSON.
3. S03 — Mermaid project-state diagrams.
4. S04 — human-facing docs.
5. S05 — reader-test and closeout.

Current package state:

- S01 complete: `prd/project-state/DOCUMENTATION-CONTRACT.md` exists.
- S02 complete: eight JSON files exist under `prd/project-state/data/`.
- S03 complete: five Mermaid files exist under `prd/project-state/diagrams/`.
- S04 complete: six human-facing docs exist under `prd/project-state/`.
- S05 in progress: reader-test completed; independent review and final closeout are the remaining gates.

## Recommended next milestone after M047

**ACP Decision Lifecycle Workflow** is the recommended next milestone.

Why: ACP now has fixture records, default registry inclusion, recovery/export surfaces, hardened RDF projection diagnostics, and a non-writing diff mode. The next control-plane gap is safe lifecycle governance for decisions.

Expected outputs:

- decision lifecycle contract;
- safe promotion verifier or workflow check;
- tests for accepted/deferred/rejected/superseded transitions;
- authority-required enforcement;
- proof-gate coverage enforcement;
- blocked-action and non-claim preservation checks;
- source-anchor safety checks;
- R038-aware independent review evidence.

## Alternatives

These are valid only if their trigger becomes more important than decision lifecycle governance:

| Alternative | Choose when | Boundary |
|---|---|---|
| RDF engine spike | Engine-executed RDF/SPARQL proof becomes valuable. | Do not promote RDF output to architecture source truth. |
| SHACL engine spike | Actual SHACL engine validation becomes valuable beyond deterministic structural smoke. | Do not claim ontology correctness without separate proof. |
| Isolated git-lex alignment spike | Identity/provenance alignment with git-lex becomes priority. | Do not initialize git-lex in the main repository. |
| ACP recovery/dashboard views | Human/operator navigation becomes more urgent than lifecycle governance. | Dashboard/recovery views remain derived diagnostics. |

## Planning constraints

Future milestones should:

- use GSD milestone/slice/task tools;
- run GitNexus impact before editing code symbols;
- run GitNexus detect changes before commits;
- use tracked relative source anchors only;
- avoid ignored execution-log anchors and absolute local paths;
- keep product/legal/runtime/parser/FalkorDB/retrieval claims bounded unless separate proof exists.
