# law-nexus

**A citation-safe, evidence-verifiable legal graph for Russian normative acts.**

The goal is to turn a normative act into a graph-vector representation for exact
article / semantic search, temporal filtering by edition and effective date, and
provable answers with legal citations. **The LLM is never legal authority** —
every checkable operation is deterministic and source-anchored.

> **Status:** `[bounded]` product runtime foundation — twenty Rust capability
> crates with hostile contracts green, real Consultant/Garant parser adapters,
> and a bounded retrieval pipeline. **No** `[validated]` product capability
> exists yet: real-corpus retrieval, citation safety, and live RuVector/TEI
> remain `[proposed]`. Truth over optimism (D098): every state claim is
> lifecycle-tagged; nothing is smoothed up to `[validated]`.

[![compliance-gate](https://github.com/rager306/law-nexus/actions/workflows/compliance-gate.yml/badge.svg)](https://github.com/rager306/law-nexus/actions/workflows/compliance-gate.yml)

## What this is (and is not)

law-nexus is a **Rust-only product runtime** with a thin Python repository-control
harness. It owns the law-specific substance: Russian legal evidence, the
Consultant/Garant parser, a temporal legal ontology, and citation-safe retrieval.

| It is | It is not |
|---|---|
| A Rust workspace of twenty exclusive `ln-*` capability crates (ADR-0011) with 20/20 hostile contracts `[bounded]` green | Parser-complete, corpus-ready, or a working product. No `[validated]` capability. |
| Bounded real adapters: Consultant WordML + Garant ODT parsers (ADR-0013 `[bounded]`); real cosine-similarity retrieval (M161 `[bounded]`); deterministic CLI pipeline (M163) | Legal correctness, citation-safe answers, live RuVector/TEI, or real-corpus validation. |
| A temporal legal ontology design spine L1→L7 (ADR-0016..0022, all `[proposed]`) | An implemented ontology runtime. All seven layers are design substance awaiting TDD implementation. |
| An anti-drift discipline: D098 lifecycle tags, living truth oracle, governor ADR/archive/era probes | A Python product, a historical FalkorDB deployment, or a historical ACP/git-lex runtime (all archive-only). |

## Current status (D098 lifecycle tags)

Latest tracked product/design band: **M165** (`[proposed]` ontology design only). D5/D6/EA-05 alignment and D7/EA-06 derived-registry quarantine are complete as documentation/process stages; EA-07 completed with `NO-BLOCK` at `430ebfd`; EA-08 completed with warnings and D149 at `962a4e7`; EA-09 independent assessment at `120d44b` and EA-10 human disposition D150 accepted the documentation/process packet **with findings**. No product implementation is unlocked. See [`prd/project-state/roadmap.md`](prd/project-state/roadmap.md); sequence completion is not product readiness.

```
[FOUNDATION — COMPLETE]
  Rust-only product transition (ADR-0004 [bounded], ADR-0005 [bounded])
  Python repository-control harness (ADR-0007 [validated])
  Five-clock temporal model (ADR-0009 [bounded]) + evidence kernel (ADR-0010 [bounded])
    HC-09/kernel gates prove clock substitution fail-closed; not legal-act correctness
  Promotion/publication authority ceiling (ADR-0008 [bounded])
  KOF-DA ownership: twenty ln-* capability crates (ADR-0011/D123) [bounded]
  Consequential evidence protocol (ADR-0012 [bounded])
  Hexagonal verification architecture (ADR-0015 [bounded])
  20/20 hostile contracts PASS [bounded]

[PARSER — BOUNDED]
  Universal multi-source parser (ADR-0013 [bounded])
    Consultant WordML + Garant ODT adapters, shared hierarchy/morphology/sentence
    and reference/temporal/deontic lexical candidates, one tracked real doc/provider

[RETRIEVAL — BOUNDED, no live corpus]
  M161  real cosine-similarity ranking (InMemory adapter + RetrievalGate) [bounded]
  M163  deterministic CLI pipeline (no hardcoded vectors)             [bounded]
  RuVector graph+vector infra (ADR-0014)                              [proposed]

[TEMPORAL LEGAL ONTOLOGY — DESIGN ONLY]
  ADR-0016 [proposed] L1 FRBR/LRMoo identity
  ADR-0017 [proposed] L2 CTV (component temporal versioning)
  ADR-0018 [proposed] L3 NormativeState
  ADR-0019 [proposed] L4 hierarchy/conflict
  ADR-0020 [proposed] L5 practice overlay
  ADR-0021 [proposed] L6 transitional/risk
  ADR-0022 [proposed] L7 industry profiles
  ADR-0023 [proposed] applicability ownership boundary; runtime [deferred]

[DOWNSTREAM — BLOCKED until parser data + RuVector/TEI ready]
  graph materialization → citation-safe retrieval → R035/R038 validation

[ARCHIVED / HISTORICAL — not active truth]
  ACP/git-lex (archive-only, R066); FalkorDB (historical, ADR-0014 → RuVector);
  Python product code (python_archive/); era skills/scripts/tests (archive/);
  residual PRD research/parser dumps/retrieval proofs (prd/archive/*)
```

See [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md) for the living truth oracle
(**read that first**, not this README).

## Active tree (what agents should open)

| Path | Role |
|------|------|
| `prd/ARCHITECTURE.md` | Living truth oracle — **read first** |
| `prd/PRODUCT.md` + `prd/REQUIREMENTS.md` | `[proposed]` Product Contract + projection; EA-10 D150 accepted the assessment packet, not these documents as a validated product contract |
| `prd/temporal-legal-model.md` | `[proposed]` D3/EA-03 crosswalk; human disposition `ACCEPT-AS-PROPOSED`, O1–O7 design only, no runtime |
| `doc/adr/` | MADR ADRs 0004–0023 (0001/0002/0003/0006 retired, not present) |
| `doc/adr-architecture-cross-matrix.md` | ADR × surface matrix + governor design |
| `prd/architecture/documentation-semantic-control-plan.md` | `[proposed]` documentation correction/control plan (non-authoritative process design) |
| `prd/migration/external-architecture-assessment-roadmap.md` | `[proposed]` independent architecture-assessment roadmap (not product validation) |
| `assessment/00-charter.md` | `[proposed]` D0/EA-00 assessment charter and packet entrypoint (not an accepted assessment) |
| `doc/litho-runbook.md` | Optional Litho/deepwiki-rs derived wiki; local `litho.toml` is gitignored (non-authoritative) |
| `crates/ln-*` | Rust product runtime |
| `src/law_nexus_harness/` | Python control-plane only (governor/preflight/CI) |
| `prd/architecture/` | Derived registry + CI views (non-authoritative) |
| `prd/parser/` | Thin contracts/schemas/profiles/examples only |
| `prd/migration/` | Active roadmaps, rust-evidence, decommission policy |
| `prd/project-state/` | `roadmap.md` + `data/roadmap.json` only |
| `.agents/skills/` (local only, gitignored) | **Active on disk:** `law-nexus-rust`, `russian-legal-evidence`, `pi-skill-creator` |

**Do not treat as active truth** (on disk for archaeology; gitignored vaults):

- `archive/` — historical skills/scripts/tests (gitignored vault)
- `prd/archive/{acp-git-lex,pre-rust-prd,research-era,parser-dumps-era,retrieval-era,...}/` — historical ACP/git-lex and era PRD vaults
- `python_archive/`, `.lex/`, `Old_project/`, `.commandcode/` — historical/local prior art only

## Architecture (pointers, not duplicates)

- **Living truth oracle:** [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md)
- **Product Contract + requirements projection (`[proposed]`, EA-02 `ready-for-assessment`):**
  [`prd/PRODUCT.md`](prd/PRODUCT.md) + [`prd/REQUIREMENTS.md`](prd/REQUIREMENTS.md).
  EA-10 D150 accepted the documentation/process assessment packet with findings; it did not promote these `[proposed]` documents or validate product/legal readiness.
- **Rust workspace:** `crates/ln-*` — twenty exclusive capability-owner crates
  (ADR-0011): `ln-domain`, `ln-temporal`, `ln-identity`, `ln-relation`,
  `ln-citation`, `ln-decode` (universal parser), `ln-storage`, `ln-query`,
  `ln-work` (DOD-FSM), plus `ln-product-cli` and 20 hostile-case runners.
  Hexagonal boundaries (ADR-0015): domain → ports → application → adapters.
- **Python harness:** `src/law_nexus_harness/` (ADR-0007 `[validated]`) —
  repository control-plane only: governor, preflight, ADR/Cargo/GSD/CI
  orchestration. No product/domain logic, no forbidden PyO3/FFI.
- **ADRs:** [`doc/adr/`](doc/adr/) — MADR-format with mandatory D098 lifecycle
  tags. Direction (ADR-0004..0015) + temporal legal ontology chain
  (ADR-0016..0022) + ADR-0023 applicability ownership boundary. Index:
  [`doc/adr/README.md`](doc/adr/README.md).
- **Temporal legal crosswalk (`[proposed]`, paper-only, `ACCEPT-AS-PROPOSED`):**
  [`prd/temporal-legal-model.md`](prd/temporal-legal-model.md) — glossary, fail-closed
  invariants, TL-G01–12 gates, golden cases and ADR-0023 ownership boundary; applicability runtime remains `[deferred]`.
- **Temporal legal ontology (design spine, all `[proposed]`):** seven progressive
  layers — **ADR-0016** FRBR/LRMoo identity (L1) → **ADR-0017** CTV (L2, paper
  arXiv:2506.07853 v5 adapted) → **ADR-0018** NormativeState (L3) →
  **ADR-0019** hierarchy/conflict (L4) → **ADR-0020** practice overlay (L5) →
  **ADR-0021** transitional/risk (L6) → **ADR-0022** industry profiles (L7).
  Design only until each layer ships TDD + fail-closed resolver. **ADR-0023**
  adds the `[proposed]` core applicability-ownership boundary; runtime remains
  `[deferred]`.
- **ADR/process matrix:** [`doc/adr-architecture-cross-matrix.md`](doc/adr-architecture-cross-matrix.md)
- **Documentation correction/control plan (`[proposed]`):**
  [`prd/architecture/documentation-semantic-control-plan.md`](prd/architecture/documentation-semantic-control-plan.md)
- **Independent assessment roadmap (`[proposed]`, documentation only):**
  [`prd/migration/external-architecture-assessment-roadmap.md`](prd/migration/external-architecture-assessment-roadmap.md)
- **D0/EA-00 assessment charter (`[proposed]`, not accepted/frozen):**
  [`assessment/00-charter.md`](assessment/00-charter.md)
- **Derived C4/repo-wiki (optional):** [`doc/litho-runbook.md`](doc/litho-runbook.md).
  Local `litho.toml` and output under `litho.docs/` are gitignored and
  **derived only**; never overwrite the living oracle or ADRs from them (D098).

## Quick start

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/) (Python env) plus a
Rust toolchain (product runtime).

```bash
git clone https://github.com/rager306/law-nexus.git
cd law-nexus
uv sync                       # install Python harness deps
cargo build --workspace       # build the Rust product runtime
```

Run the gates:

```bash
# Python repository-control gates
uv run python -m law_nexus_harness.governor     # process + ADR/archive/era advisory probes
uv run python -m law_nexus_harness.preflight
uv run pytest -q                               # full suite; CI process suite is a subset
uv run python scripts/verify-adr-conformance.py

# Rust product gates
cargo fmt --check --all
cargo clippy --workspace --offline --all-targets -- -D warnings
cargo test --workspace --offline
```

Governor ADR/archive probes (advisory unless noted) include:

- `adr-truth-oracle-sync` (error on lifecycle mismatch)
- `adr-index-completeness`, `adr-doc-matrix-coverage`, `adr-structure-hygiene`
- `adr-cross-surface-matrix`, `adr-retired-id-ban`, `active-surface-era-noise`
- `archive-path-policy` (historical vaults gitignored + untracked)

Inspect the product:

```bash
cargo run -q -p ln-product-cli -- health        # release health smoke
cargo run -q -p ln-product-cli -- inspect <path> # structural + retrieval inspect
```

## Where to read next

1. **[`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md)** — living truth oracle. Read first.
2. **[`prd/PRODUCT.md`](prd/PRODUCT.md)** + **[`prd/REQUIREMENTS.md`](prd/REQUIREMENTS.md)** — `[proposed]` product clauses/projection; EA-10 D150 accepted the assessment packet, not these documents as a validated product contract.
3. **[`doc/adr/README.md`](doc/adr/README.md)** — ADR index: direction + temporal ontology chain.
4. **[`doc/adr-architecture-cross-matrix.md`](doc/adr-architecture-cross-matrix.md)** — ADR × surface matrix.
5. **[`prd/architecture/documentation-semantic-control-plan.md`](prd/architecture/documentation-semantic-control-plan.md)** — `[proposed]` documentation correction/control sequence.
6. **[`assessment/00-charter.md`](assessment/00-charter.md)** — assessment packet entrypoint; EA-10 D150 final disposition is recorded in [`assessment/12-final-disposition.md`](assessment/12-final-disposition.md).
7. **[`prd/migration/`](prd/migration/)** — tracked active planning surfaces; sequence is not readiness proof.
8. **[`doc/litho-runbook.md`](doc/litho-runbook.md)** — optional Litho/deepwiki-rs regen (derived wiki only).
9. **[`prd/archive/README.md`](prd/archive/README.md)** — PRD vault map (not product truth). Root `archive/` is fully gitignored archaeology.

Local `.gsd/**` requirements, decisions, roadmap and execution records support repository workflow but are not published cold-reader authority or sole external proof. The tracked Product Contract and requirements projection are published `[proposed]` documents with EA-02 state `ready-for-assessment`; EA-10 D150 accepted the assessment packet, not product behavior or these documents as validated product authority.

## Non-claims (what this project does **not** prove today)

Following the D098 anti-smoothing discipline, law-nexus today does **not** claim:

- any `[validated]` product capability — all product work is `[bounded]`/`[smoke]`/`[proposed]`;
- parser completeness, Consultant/Garant cross-format parity, or corpus coverage;
- legal correctness, authoritative interpretation, or resolved reference/temporal/deontic claims;
- citation-safe retrieval quality or legal-answer correctness;
- a live RuVector/TEI runtime or real-corpus retrieval;
- an implemented temporal legal ontology runtime — ADR-0016..0022 are `[proposed]` design only;
- R035 / R038 validation;
- that derived architecture registry views (`prd/architecture/*.jsonl`, claims ledger)
  are source of truth — they are non-authoritative projections.

These are explicit deferrals, tracked in the roadmap, not gaps being hidden.

## Governance

- **D098** — anti-drift: mandatory lifecycle tags `[proposed]`/`[bounded]`/
  `[smoke]`/`[validated]`/`[deferred]` on architectural/state claims; never smooth
  a bounded/proposed claim up to `[validated]`.
- **D046** — adoption ladder: project-local evidence kernel is canon; external
  standards (LRMoo/CIDOC-CRM/AKML/ELI/LKIF) are compatibility references.
- Architectural decision substance is published in [`doc/adr/`](doc/adr/).
  Local `.gsd/DECISIONS.md` records workflow/governance events but is not a
  cold-reader authority surface and cannot replace an ADR.
- Historical ACP/git-lex is **archive-only**; historical FalkorDB is **not active**;
  the active graph/vector target is RuVector (ADR-0014 `[proposed]`).
- Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`; cite only
  with historical/retired/rejected qualifiers (governor `adr-retired-id-ban`).
