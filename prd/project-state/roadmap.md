# Roadmap

> **Source of truth:** `prd/ARCHITECTURE.md` (living truth oracle) and `.gsd/milestones/*` (GSD state).
> This page is a derived cold-reader summary. When it disagrees with the oracle
> or GSD state, those win. Derived from `prd/project-state/data/roadmap.json`.
> Refreshed 2026-06-22 (post-M069).

## Where we are now

```
[STRUCTURAL FOUNDATION — M069 DONE, M068 PENDING VALIDATION]
  M068 (onion package src/law_nexus + ADR-0001 + MADR ADR standard ADR-0002
        + compliance gate)                 🟡 needs-attention (NOT complete;
        'pre-commit+CI wire' only half-met — pre-commit wired, CI not)
  M069 (ADR-0003 library-boundary contract + gate-green standing tree)  ✅ complete

[PRODUCT TRACK — RESUMES HERE]
  Consultant XML Parser Hardening (M034 corrected roadmap)   ← NEXT
    7 slices: baseline lock → lxml eval → structural rules →
              semantic diagnostics → razdel/pymorphy3 →
              source-span/stable-ID → final proof package

[DOWNSTREAM — BLOCKED until parser data ready]
  graph materialization → retrieval / citation-safe answers →
  R035 / R037 / R038 validation
```

**Pending validation:** M068-xi4034 is `active` / `blocked` — its validation is
`needs-attention` (the S03 "pre-commit+CI wire" success criterion is only
half-met: pre-commit is wired and green, but `.github/workflows` CI is not).
Resolve by wiring CI OR rescoping the criterion, then re-run
`gsd_validate_milestone` to pass and complete M068. M069 is complete
independently.

The ACP/git-lex era (M035–M067) is **CLOSED**: the reusable core was
externalized to `/root/git-lex-kit-acp/` and law-nexus became a profile consumer
(M067, D097). Per **D098**, that era was itself meta-drift; ACP is now frozen to
**checkpoint mode** (detect+log+flag, non-blocking) until parser data is ready.
Do not treat ACP/RDF/SHACL/SPARQL/dashboards as source truth or as the next
milestone.

## Project proof roadmap

| Range | Theme | Boundary |
|---|---|---|
| M001-M010 | Architecture review, PRD consistency, parser direction, and baseline architecture verification | Foundations only, not production readiness. |
| M011-M030 | GraphRAG, FalkorDB, retrieval, ontology, evidence, and semantic scoring proof cycles | Bounded proof cycles, not final retrieval quality or ontology/product readiness. |
| M031-M034 | Consultant XML source structuring, MiniMax-assisted discovery, graph context staging, and workline recovery | Source workflow evidence, not parser completeness for all sources. |
| M035-M067 | ACP / git-lex reusable-core era — construction, registry, RDF projection, then **externalization** | **CLOSED.** Core externalized (M067, D097); law-nexus is a profile consumer. This era was itself meta-drift (D098); ACP is frozen to checkpoint mode. Not source truth, not the next milestone. |
| M068-M070 | Structural foundation crystallization + roadmap freshness guard — onion package, ADR standard, compliance gate, library-boundary contract, anti-drift guard | Anti-drift infrastructure only. M069 **complete**, M070 **complete**; M068 **needs-attention** (pre-commit+CI wire half-met). Repo is now a package (`src/law_nexus`). Does NOT validate R035/R037/R038, does NOT harden the parser, does NOT introduce FalkorDB/graph/retrieval. |

See `prd/project-state/diagrams/milestone-timeline.mmd` for the compressed
timeline (note: the diagram predates M068-M069 and should be refreshed when the
parser-hardening milestone nears).

## Current milestone

`M070-rqcvnx — Roadmap freshness guard` is **complete**.

It fixed the stale project-state roadmap (was current=M047, next=ACP — contradicting
D098) to the truthful trajectory and added a pytest freshness-guard
(`tests/test_project_state_roadmap_freshness.py`) that parses `.gsd/STATE.md` as
source of truth so the roadmap cannot silently drift again. The guard fails if
the roadmap's `current_milestone` lags the latest GSD milestone.

> **Note:** M068-xi4034 precedes this milestone and is **not yet complete** —
> its validation is `needs-attention` (pre-commit+CI wire half-met). See
> "Pending validation" below.

## Recommended next milestone

**Consultant XML Parser Hardening from the M009 baseline** (the M034 corrected
roadmap) is the recommended next milestone.

Why: the structural foundation is laid (M068/M069); per D098 and the M034
corrected roadmap, the product track resumes at parser hardening **before** any
graph/retrieval/R035-R038 work, all of which are downstream-blocked on parsed
data. The parser-hardening milestone is a proof-gated, non-overclaiming pass on
the existing M009 Consultant WordML hierarchy baseline.

Plan: `prd/research/source_structuring/25-corrected-consultant-xml-parser-roadmap.md`
— S01 baseline lock → S02 `lxml` equivalence eval → S03 structural rules →
S04 semantic diagnostics → S05 `razdel`/`pymorphy3` eval → S06 source-span/
stable-ID → S07 final proof package.

**Non-validation:** does NOT validate R035/R037/R038; does NOT introduce
FalkorDB/graph/vector/retrieval; does NOT claim parser completeness or legal
correctness.

## Downstream — blocked until parser data ready

| Capability | Blocker | Current status |
|---|---|---|
| FalkorDB legal graph (production) | needs materialized graph from parsed corpus | `[bounded]` synthetic smoke |
| Retrieval / citation-safe answers | needs real EvidenceSpan/SourceBlock fixtures from parsed corpus | `[bounded]` smoke only |
| R035 (ontology architecture) | needs registry extractor integration + accepted proof-gate evidence (documentation-only is insufficient) | `[proposed]` active, not validated |
| R037 (FalkorDB ingest/runtime) | needs production ingest from real corpus | `[bounded]` active, partially evidenced |
| R038 (independent review) | standing review gate | `[bounded]` active |

## Alternatives

Valid only if their trigger becomes more important than parser hardening:

| Alternative | Choose when | Constraint |
|---|---|---|
| FalkorDB graph materialization | Parser proof yields a stable record stream. | Do not start before parser-hardening proof; no R037 claim from synthetic smoke. |
| Adaptix boundary-record↔domain-form mapping | ADR-0003's reserved mapping becomes needed (parser product wires boundary-records into domain). | Premature until parser-hardening produces the consumer. |
| ACP unfreeze (observational only) | A concrete drift is detected+logged, or the user explicitly directs it. | ACP expands ONLY observation, never into a blocking gate (D098); do not re-enter the M035-M063 meta-drift. |

## Frozen (not active tracks)

- **ACP** — checkpoint mode (detect+log+flag) until parser data ready (D098). Not a milestone, not a gate.
- **R035 / R037 / R038 validation** — not validatable from documentation/projection evidence alone; deferred to downstream product-data milestones.

## Planning constraints

Future milestones should:

- use GSD milestone/slice/task tools;
- run GitNexus impact before editing code symbols;
- run GitNexus detect_changes before commits;
- use tracked relative source anchors only (no `.gsd/exec`, absolute, ignored, or raw-payload anchors);
- keep product/legal/runtime/parser/FalkorDB/retrieval claims bounded unless separate proof exists;
- apply D098 lifecycle tags (`[proposed]`/`[bounded]`/`[smoke]`/`[validated]`/`[deferred]`) on architectural/state claims; never smooth a bounded/proposed claim up to `[validated]`.
