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
| `doc/adr/` | MADR ADRs 0004–0022 (0001/0002/0003/0006 retired, not present) |
| `doc/adr-architecture-cross-matrix.md` | ADR × surface matrix + governor design |
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
  (ADR-0016..0022). Index: [`doc/adr/README.md`](doc/adr/README.md).
- **Temporal legal ontology (design spine, all `[proposed]`):** seven progressive
  layers — **ADR-0016** FRBR/LRMoo identity (L1) → **ADR-0017** CTV (L2, paper
  arXiv:2506.07853 v5 adapted) → **ADR-0018** NormativeState (L3) →
  **ADR-0019** hierarchy/conflict (L4) → **ADR-0020** practice overlay (L5) →
  **ADR-0021** transitional/risk (L6) → **ADR-0022** industry profiles (L7).
  Design only until each layer ships TDD + fail-closed resolver.
- **ADR/process matrix:** [`doc/adr-architecture-cross-matrix.md`](doc/adr-architecture-cross-matrix.md)

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
2. **[`doc/adr/README.md`](doc/adr/README.md)** — ADR index: direction + temporal ontology chain.
3. **[`doc/adr-architecture-cross-matrix.md`](doc/adr-architecture-cross-matrix.md)** — ADR × surface matrix.
4. **`.gsd/REQUIREMENTS.md`** — capability/quality-attribute requirements.
5. **`.gsd/DECISIONS.md`** — decision register (governance events; early D-rows may be historical).
6. **`.gsd/ROADMAP.md`** — milestone trajectory.
7. **[`prd/archive/README.md`](prd/archive/README.md)** — PRD vault map (not product truth). Root `archive/` is fully gitignored archaeology.

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
- Decisions live in `.gsd/DECISIONS.md` (governance events) and
  [`doc/adr/`](doc/adr/) (architectural substance) — complementary, not duplicate.
- Historical ACP/git-lex is **archive-only**; historical FalkorDB is **not active**;
  the active graph/vector target is RuVector (ADR-0014 `[proposed]`).
- Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`; cite only
  with historical/retired/rejected qualifiers (governor `adr-retired-id-ban`).
