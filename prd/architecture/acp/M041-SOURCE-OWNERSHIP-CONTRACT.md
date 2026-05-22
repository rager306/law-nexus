# M041 ACP Source Ownership Contract

**Date:** 2026-05-21

## Status

Contract artifact for `M041-y19crg / S01`.

This document defines how ACP records and derived outputs fit into the architecture source-of-truth hierarchy before any canonical registry integration is attempted.

## Verdict

ACP Markdown records are source evidence for ACP governance. ACP derived JSON/JSONL outputs are generated proof artifacts, not source truth.

Therefore a future canonical registry integration must be owned by a generator that reads ACP source records or verified recovery/projection inputs and emits canonical registry records through a checked workflow. It must not copy derived ACP JSONL directly into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

## Source ownership classification

This section is the source ownership classification for ACP integration.

| Artifact class | Examples | Ownership | May feed canonical registry? | Rule |
| --- | --- | --- | --- | --- |
| ACP source records | `prd/architecture/acp/fixtures/minimal-chain/*.md` | ACP source evidence | Yes, through a checked generator only | Treat as source evidence for ACP governance mechanics, not product proof. |
| ACP contract/decision docs | `M037-*`, `M038-*`, `M039-*`, `M040-*`, this file | PRD/architecture source evidence | Yes, as source anchors and decision context | Use as source anchors for governance decisions and non-claims. |
| ACP recovery view | `derived/recovery-view.json` | Derived ACP view | Yes, only as checked intermediate input | Must be refreshed and validated; not source truth by itself. |
| ACP preview projection | `derived/architecture-projection.preview.json` | Derived preview | No direct canonical feed | Preview evidence only; cannot become canonical registry rows directly. |
| ACP canonical-shaped custom output | `derived/canonical-projection.items.jsonl`, `derived/canonical-projection.edges.jsonl` | Derived proof output | Yes, only as acceptance evidence for generator behavior | Do not copy into canonical JSONL; regenerate through approved workflow. |
| Canonical architecture registry | `architecture_items.jsonl`, `architecture_edges.jsonl` | Derived canonical projection | Already canonical generated view | Must remain owned by architecture extraction/build flow. |

## Generator ownership rule

A future ACP canonical registry integration must define a named generator owner before writing tracked canonical JSONL. Acceptable owner options are:

1. extend `scripts/extract-prd-architecture-items.py` to include ACP source records;
2. add a separate ACP canonical extractor that emits to custom paths, then compose through a checked architecture build step;
3. keep ACP custom-only and defer canonical composition.

M041 S02 should test option 2 as a custom integrated fixture only. It should not update the canonical extraction/build flow.

## Allowed source anchors

Canonical ACP records may anchor to:

- ACP Markdown source records under `prd/architecture/acp/fixtures/`;
- ACP contract, decision, and assessment docs under `prd/architecture/acp/`;
- ACP exporter/checker source under `scripts/`;
- ACP tests under `tests/`;
- PRD/research docs under `prd/research/architecture/` when they define ACP intent or profile.

All anchors must be repository-relative and tracked.

## Blocked anchors

Do not use:

- local absolute paths;
- ignored transient execution-log paths;
- external URLs as proof anchors;
- raw provider payloads;
- raw vectors;
- raw legal text;
- generated ACP JSONL as the only source anchor for a canonical row.

Generated ACP JSONL may appear as test input or acceptance evidence, but canonical rows must also trace to source ACP records or contract docs.

## Promotion rules

### Prompt records

Prompt records may enter canonical-shaped or future canonical registry output only as `prompt_record` with source/provenance status.

They must not:

- validate implementation;
- validate architecture decisions;
- validate legal correctness;
- validate parser or retrieval quality.

### Proposals

Proposal records may enter as `proposal`, not as accepted decisions.

### Decision candidates

Decision candidates may enter as `decision_candidate` with `authority_required: true`.

They must not become `decision` records unless a later accepted authority and proof-gate workflow explicitly promotes them.

### Proof gates

Proof gates may enter as `proof_gate`, but the presence of a gate does not satisfy the gate.

### Health findings

Health findings may enter as `health_finding`, `risk`, or future health-diagnostic records only if they remain blockers/diagnostics, not proof of readiness.

## S02 custom integrated fixture requirements

S02 should build custom integrated outputs, not tracked canonical outputs:

```text
prd/architecture/acp/derived/integrated-registry.items.jsonl
prd/architecture/acp/derived/integrated-registry.edges.jsonl
```

The integrated fixture should combine:

- current `prd/architecture/architecture_items.jsonl`;
- current `prd/architecture/architecture_edges.jsonl`;
- ACP canonical-shaped custom item/edge outputs.

The fixture checker should verify:

- JSONL parses;
- schema validity;
- no duplicate IDs;
- all edge endpoints exist;
- source anchors are safe and repository-relative;
- no blocked anchors are used;
- ACP prompt records and decision candidates remain non-authoritative;
- tracked canonical JSONL files remain unchanged/current.

## Required non-claims

ACP-integrated custom fixture rows must preserve non-claims that they do not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## Blocked actions

- Directly copy `canonical-projection.items.jsonl` into `architecture_items.jsonl`.
- Directly copy `canonical-projection.edges.jsonl` into `architecture_edges.jsonl`.
- Treat `canonical-projection.*.jsonl` as canonical registry truth.
- Treat ACP prompt provenance as implementation proof.
- Treat ACP decision candidates as accepted architecture decisions.
- Treat proof gate definitions as proof gate satisfaction.
- Use custom-path verifier success as evidence that tracked architecture registry is current.

## Boundary preservation

This contract does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## S03 decision input

S03 should decide among:

1. keep ACP integration custom-only;
2. plan a future canonical generator integration milestone with a named owner;
3. revise the ACP source ownership model if S02 exposes fixture or verifier mismatch.

Default bias: keep custom-only until a named canonical generator owner is chosen and proof-gated.
