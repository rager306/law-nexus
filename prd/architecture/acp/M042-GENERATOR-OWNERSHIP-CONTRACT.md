# M042 ACP Generator Ownership Contract

**Date:** 2026-05-22

## Status

Contract artifact for `M042-jbxawt / S01`.

This contract names the ACP composition seam to prove in M042 and defines ownership boundaries before any canonical registry generation changes.

## Decision

M042 will prove a named custom composition seam called **ACP composition staging**.

The owner of this seam is a dedicated ACP composition checker/generator, separate from the canonical architecture extractor. It may read current canonical registry projections and ACP canonical-shaped custom outputs, then emit custom composition outputs under ACP derived paths. It must not write tracked canonical architecture registry JSONL files.

## Named generator ownership

| Generator or artifact | Owner | Inputs | Outputs | Authority boundary |
| --- | --- | --- | --- | --- |
| Canonical architecture extractor | `scripts/extract-prd-architecture-items.py` | curated PRD/GSD/ADR/source/runtime evidence mappings | `prd/architecture/architecture_items.jsonl`, `prd/architecture/architecture_edges.jsonl` | Derived canonical registry projection only; source evidence remains authoritative. |
| Canonical graph/report builder | `scripts/build-architecture-graph.py` | canonical architecture JSONL | graph/report artifacts under `prd/architecture/` | Derived diagnostics only; not source truth. |
| ACP projection exporter | `scripts/export-acp-architecture-projection.py` | ACP Markdown records and ACP schema | ACP preview and canonical-shaped custom outputs under `prd/architecture/acp/derived/` | ACP proof output only; not canonical truth. |
| ACP integrated fixture checker | `scripts/build-acp-integrated-registry-fixture.py` | canonical JSONL plus ACP canonical-shaped custom outputs | integrated fixture under `prd/architecture/acp/derived/` | M041 custom integration evidence only. |
| ACP composition staging seam | to be implemented in M042 S02 | canonical JSONL plus ACP canonical-shaped custom outputs plus S01/S02 contracts | custom composition outputs under `prd/architecture/acp/derived/` | Named composition proof only; not canonical mutation. |

## Ownership rules

1. The canonical architecture extractor remains the only current owner of tracked canonical registry JSONL generation.
2. The ACP composition staging seam owns only custom composition outputs under `prd/architecture/acp/derived/`.
3. ACP composition staging may validate whether ACP rows are safe to compose with canonical rows, but it cannot promote those rows into tracked canonical registry files.
4. If future work wants canonical integration, it must either extend the canonical extractor or add an explicitly checked architecture-build composition step in a separate milestone.
5. No generator may treat ACP prompt provenance, proposals, or decision candidates as accepted architecture decisions without a later authority/proof-gate workflow.

## Source and derived artifact classification

| Class | Examples | Role in M042 | Rule |
| --- | --- | --- | --- |
| Source evidence | ACP Markdown records, ACP contracts, ACP decisions, PRD architecture contracts, source code, tests | May anchor generated rows and decisions | Must be repository-relative and tracked. |
| Derived canonical projection | `architecture_items.jsonl`, `architecture_edges.jsonl` | Read-only baseline input for custom composition | Do not hand-edit or treat as source truth. |
| Derived ACP projection | ACP recovery, preview, canonical-shaped custom JSONL | Input and acceptance evidence for custom composition | Must be checked/current before composition. |
| Custom composition output | M042 S02 composition outputs | Proof artifact for composition ownership | Must live under ACP derived paths and remain non-authoritative. |
| Canonical graph/report/verifier output | architecture graph report and verifier diagnostics | Final currentness and drift gate | Passing default verifier means static registry checks are green, not runtime/product/legal validation. |

## M042 S02 composition seam requirements

S02 should implement a dedicated command/checker rather than mutating existing canonical extractor behavior.

Required custom output paths:

```text
prd/architecture/acp/derived/composed-registry.items.jsonl
prd/architecture/acp/derived/composed-registry.edges.jsonl
prd/architecture/acp/derived/composition-report.json
```

Required checker behavior:

- read current `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` as read-only inputs;
- read current ACP canonical-shaped custom outputs as read-only inputs;
- emit custom composed outputs only under ACP derived paths;
- refuse `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` as output targets;
- validate JSONL parsing, duplicate IDs, and edge endpoints;
- validate source anchors are repository-relative, tracked, and not ignored transient paths;
- validate ACP decision candidates preserve `authority_required: true`;
- validate required non-claims are present for ACP rows;
- report counts for canonical records, ACP records, composed records, and diagnostics;
- support `--check` stale-output detection.

## Required tests for S02

Tests must cover:

- successful composition with current fixture counts;
- schema validity for composed records;
- duplicate ID rejection;
- broken edge endpoint rejection;
- unsafe source anchor rejection;
- missing ACP non-claim rejection;
- missing `authority_required` on decision candidates;
- stale composed output detection;
- canonical output path refusal;
- canonical architecture JSONL non-mutation.

## Promotion preconditions for future canonical integration

A future milestone may consider canonical integration only if all of the following exist:

1. named generator owner chosen for canonical composition;
2. source evidence anchors for each ACP-derived row;
3. tests proving no direct copy from ACP derived JSONL into canonical JSONL;
4. architecture verifier remains green on default paths;
5. decision-candidate promotion workflow exists for accepted decisions;
6. proof-gate satisfaction is represented separately from proof-gate definition;
7. non-claims remain explicit for R035, R037, R038, parser completeness, legal correctness, FalkorDB ingestion, retrieval quality, production readiness, and independent external review.

## Blocked actions

- Do not copy ACP canonical-shaped custom JSONL into tracked canonical registry JSONL.
- Do not copy ACP integrated or composed custom JSONL into tracked canonical registry JSONL.
- Do not change `scripts/extract-prd-architecture-items.py` in M042 unless a later explicit replan narrows and verifies that change.
- Do not treat custom composition output as source truth.
- Do not treat ACP prompt records as implementation proof.
- Do not treat ACP decision candidates as accepted decisions.
- Do not treat proof-gate definitions as proof-gate satisfaction.
- Do not initialize git-lex or an RDF/dashboard authority layer in the main repository as part of M042.

## Required non-claims

M042 does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## S03 decision inputs

S03 should decide among:

1. keep ACP composition staging custom-only;
2. plan a future canonical extractor/composition integration milestone with a named owner;
3. revise the ownership model if S02 finds composition invariants are too weak.

Default recommendation: keep M042 custom-only and use it as a proof artifact for a later canonical integration milestone only if S02 produces clean diagnostics and tests.
