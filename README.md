# law-nexus

**A citation-safe, evidence-verifiable legal graph for Russian normative acts.**

The goal is to turn a normative act into a graph-vector representation for exact
article / semantic search, temporal filtering by edition and effective date, and
provable answers with legal citations. **The LLM is never legal authority** —
every checkable operation is deterministic and source-anchored.

> **Status:** `[bounded]` product runtime foundation — twenty exclusive Rust
> capability-owner crates with hostile contracts green, real Consultant/Garant
> parser adapters, and a bounded retrieval pipeline. The workspace has 45
> members in total: 20 capability owners, 20 hostile-case runners,
> `ln-product-cli`, `ln-testkit`, `ln-storage`, `ln-status`, and proposed
> `ln-applicability` (fail-closed abstention kernel only). **No**
> `[validated]` product capability
> exists yet: real-corpus retrieval, citation safety, and live RuVector/TEI
> remain `[proposed]`. Truth over optimism (D098): every state claim is
> lifecycle-tagged; nothing is smoothed up to `[validated]`.

[![repository-quality](https://github.com/rager306/law-nexus/actions/workflows/repository-quality.yml/badge.svg)](https://github.com/rager306/law-nexus/actions/workflows/repository-quality.yml)

## What this is (and is not)

law-nexus is a **Rust-only product runtime** with a thin Python repository-control
harness. It owns the law-specific substance: Russian legal evidence, the
Consultant/Garant parser, a temporal legal ontology, and citation-safe retrieval.

| It is | It is not |
|---|---|
| A Rust workspace of twenty exclusive `ln-*` capability crates (ADR-0011) with 20/20 hostile contracts `[bounded]` green | Parser-complete, corpus-ready, or a working product. No `[validated]` capability. |
| Bounded real adapters: Consultant WordML + Garant ODT parsers (ADR-0013 `[bounded]`); real cosine-similarity retrieval (M161 `[bounded]`); deterministic CLI pipeline (M163) | Legal correctness, citation-safe answers, live RuVector/TEI, or real-corpus validation. |
| A temporal legal ontology design spine L1→L7 (ADR-0016..0022, all `[proposed]`) | An implemented ontology runtime. All seven layers are design substance awaiting TDD implementation. |
| An anti-drift discipline: D098 lifecycle tags, living truth oracle, and Governor ADR/lifecycle/retired-era probes | A Python product, a historical FalkorDB deployment, or a historical ACP/git-lex runtime (all decommissioned). |

## Current status (D098 lifecycle tags)

Latest tracked product/design band: **M165** (`[proposed]` ontology design only).
The current documentation/control baseline includes post-D150 assessments 13–18,
the parser G0–G3 acceptance protocol, controlled temporal vocabulary and
presentation-drift checks, and a D7-quarantined historical readiness index.
These are repository-control improvements, not product implementation.

D5/D6/EA-05 alignment and D7/EA-06 derived-registry quarantine are complete as
documentation/process stages; EA-07 completed with `NO-BLOCK` at `430ebfd`;
EA-08 completed with warnings and D149 at `962a4e7`; EA-09 independently assessed
revision `120d44b`; EA-10 human disposition D150 accepted that exact packet
**with findings**. D150 does not accept later revisions. The latest remediation
assessment is [`assessment/18-post-semantic-control-remediation.md`](assessment/18-post-semantic-control-remediation.md),
which records remaining human-owned semantic decisions and Rust/evidence work
without successor acceptance, TSG closure, or lifecycle promotion.

Repository-control snapshot at clean post-remediation revision `f09416f`: full
Python suite `435 passed, 4 skipped`; Governor `54 PASS / 1 advisory WARN / 0
ERROR / 0 TOOL ERROR`; preflight `7 PASS / 1 advisory WARN / 0 ERROR`. The retained warning is
`historical-test-debt-visibility`. These counts are process evidence only. See
[`prd/project-state/roadmap.md`](prd/project-state/roadmap.md); sequence
completion and green repository checks are not product readiness.

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

[RETIRED DIRECTIONS — not active truth]
  ACP/git-lex and the Python product runtime are decommissioned;
  FalkorDB is superseded by the proposed RuVector direction.
```

See [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md) for the living truth oracle
(**read that first**, not this README).

## Architectural ideas

The architecture is organized around **authority, evidence, and failure
boundaries**, not around framework layers or one large legal-domain model.
Canonical detail remains in [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md) and the
active ADRs; this section explains how the pieces fit together.

### 1. Exclusive capability ownership

ADR-0011 assigns each of twenty consequential capabilities to exactly one
primary Rust crate. An invoker, adapter, projection, or runner may contribute to
a capability but cannot become its co-owner. This prevents two components from
minting conflicting authoritative outcomes.

```text
source observation -> immutable inventory -> review/disposition -> promotion
      -> decode -> lifecycle gate -> identity -> relation -> temporal state
      -> work/dependency/replay -> publication -> query/citation/diagnostics
```

The chain is not a claim that every stage is product-ready. It is an ownership
map with `[bounded]` hostile-contract evidence. Cross-capability composition
uses explicit ports rather than shared mutable domain state.

### 2. Hexagonal boundaries per capability

Capability crates follow the ADR-0015 direction:

```text
Domain rules and value objects
        ^
Application use cases + ports
        ^
Adapters (InMemory, hostile, parser, future infrastructure)
        ^
Composition roots (`ln-product-cli`, HC runners)
```

Dependencies point toward policy. Adapters cannot redefine legal/domain
outcomes. Shared port-contract suites in `ln-testkit` exercise compatible
semantics across in-memory, hostile, and real adapters where those adapters
exist. InMemory success remains `[bounded]`; it cannot validate a live backend.

### 3. Evidence before authority

Promotion and publication are separate. Candidate, inferred, retrieved, or
LLM-produced material remains non-authoritative until the owning deterministic
gates accept complete source-bound evidence. Missing provenance produces an
explicit unknown/no-answer/fail-closed result rather than an invented answer.
An LLM may assist with discovery or explanation, but it cannot establish legal
truth, lifecycle promotion, or a citation anchor.

### 4. Five clocks and event-derived legal state

ADR-0009 separates source, publication, legal-effective, observed and
system-transaction time. They must not silently substitute for each other. The
proposed L1-L7 temporal ontology builds on that kernel:

```text
L1 structural identity (Work / Expression / Manifestation / Item)
 -> L2 component temporal versioning and event-sourced validity
 -> L3 NormativeState (text is not legal status)
 -> L4 hierarchy and explainable conflict
 -> L5 judicial/FAS/control-practice overlay over the same five clocks
 -> L6 transitional provisions and derived risk
 -> L7 versioned industry profiles
 -> ADR-0023 applicability decision/trace ownership boundary
```

All L1-L7 layers remain `[proposed]`. Event taxonomies, NormRule IR,
applicability DSL, stable temporal APIs, and unified error contracts are not yet
accepted. Their names in the glossary are stop-signals where marked
`deferred-undefined`, not instructions to generate Rust types.

### 5. Provider-isolated parsing

Consultant WordML and Garant ODT are independent adapters behind shared parser
contracts. Their fixtures and oracles must not borrow assumptions from each
other. The current evidence reaches parser protocol G1 `[bounded]`: one tracked
real document per provider plus structural/hostile contracts. G2 requires a
representative multi-fixture corpus with independent annotations and
human-owned thresholds; G3 requires independent source-bound acceptance.

### 6. Infrastructure behind ports

`ln-storage` owns graph, vector, and embedding port contracts. InMemory cosine
ranking is real but bounded; deterministic CLI vectors are deliberately
non-semantic. ADR-0014 selects RuVector and local TEI/USER-bge-m3 as the
`[proposed]` target, but no live RuVector/TEI product path or citation-safe
real-corpus retrieval is claimed. Historical FalkorDB is not active
infrastructure.

### 7. Two control planes, no bridge

Rust is the only product runtime. Python under `src/law_nexus_harness/` is a
subprocess repository-control plane for Governor, preflight, ADR/document
checks, and CI orchestration. It contains no product/domain rules and there is
no PyO3/FFI bridge. Archived Python product code is prior art only.

### 8. Anti-drift without authority laundering

D098 lifecycle tags keep claims at their evidence ceiling. Governor, generated
registries, assessments, roadmaps, and GitNexus diagnose consistency; they do
not define architecture or legal meaning. Canonical authority is the
living oracle plus accepted active ADRs, while product claims additionally need
source, tests, runtime, and real-document evidence appropriate to the claim.

## Repository map

### Rust workspace: 45 members

| Group | Members | Responsibility |
|---|---|---|
| Capability owners (20) | `ln-observe`, `ln-inventory`, `ln-dispose`, `ln-promote`, `ln-decode`, `ln-gate`, `ln-identity`, `ln-relation`, `ln-temporal`, `ln-work`, `ln-closure`, `ln-projection`, `ln-admission`, `ln-replay`, `ln-publish`, `ln-accelerate`, `ln-query`, `ln-citation`, `ln-diagnostic`, `ln-conformance` | Exclusive HC-01..HC-20 domain/application ownership from ADR-0011. |
| Hostile runners (20) | `ln-hc01-runner` .. `ln-hc20-runner` | Process-level bounded hostile-case executables; proof harnesses, not additional capability owners. |
| Composition | `ln-product-cli` | `law-nexus-inspect` health/inspect composition root and observable JSON failure surface. |
| Shared infrastructure | `ln-storage` | Graph, vector, and embedding port contracts plus bounded InMemory adapters; not a KOF-DA primary owner. |
| Shared verification | `ln-testkit` | Reusable port-contract suites and hostile fixtures; test support, not product authority. |
| Repository tracer | `ln-status` | Deterministic status/failure/sleep/output subprocess tracer for repository-harness verification; not a product capability owner. |
| Proposed protocol kernel | `ln-applicability` | ADR-0023 fail-closed abstention-only applicability evaluator `[proposed]`; not a KOF-DA owner and not Applicable/NotApplicable product proof. |

Most capability crates use `domain.rs`, `ports.rs`, `application.rs`, and
`adapters.rs`; crate integration/hostile tests live under `crates/*/tests/`.
The root [`Cargo.toml`](Cargo.toml) is the executable workspace inventory.

### Tracked repository surfaces

| Path | Role and authority boundary |
|---|---|
| `prd/ARCHITECTURE.md` | Living architecture truth oracle — **read first**. |
| `doc/adr/` | Accepted/proposed architectural decision substance and lifecycle ownership. |
| `prd/PRODUCT.md`, `prd/REQUIREMENTS.md` | Published `[proposed]` product contract and requirements projection; not validated behavior. |
| `prd/temporal-legal-model.md` | `[proposed]` glossary/crosswalk, TL-G01–12 gates, paper cases, and explicit 14-area completeness matrix. |
| `prd/architecture/` | Governance contracts and D7-quarantined derived registry/views; diagnostics, never source truth. |
| `prd/parser/` | Active thin parser schemas, profiles, examples, golden contract, and G0–G3 acceptance protocol. |
| `prd/migration/` | Rust migration, decommission, evidence, and detailed forward planning. |
| `prd/project-state/` | Cold-reader roadmap projection and its tracked data source. |
| `assessment/` | D0/EA assessment packet and post-D150 bounded gap/remediation assessments; no automatic acceptance. |
| `crates/` | Rust product source, capability contracts, adapters, runners, and Rust tests. |
| `src/law_nexus_harness/` | Thin Python repository harness only: CLI, Governor, preflight, ADR matrix, result/subprocess support. |
| `scripts/` | Active deterministic repository verification/generation entrypoints. |
| `tests/` | Python repository-control, documentation, hostile-policy, and generator tests. |
| `law-source/consultant/`, `law-source/garant/` | Tracked real provider fixtures; bounded evidence, not an authoritative or representative legal corpus. |
| `.github/workflows/`, `.pre-commit-config.yaml` | CI and local quality-gate wiring. |
| `CHANGELOG.md` | Human-readable delivery history; not architecture authority. |

Only tracked active surfaces are listed here. Retired implementations and local
tooling are intentionally omitted from cold-reader navigation.

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

## Architecture (pointers, not duplicates)

- **Living truth oracle:** [`prd/ARCHITECTURE.md`](prd/ARCHITECTURE.md)
- **Product Contract + requirements projection (`[proposed]`, EA-02 `ready-for-assessment`):**
  [`prd/PRODUCT.md`](prd/PRODUCT.md) + [`prd/REQUIREMENTS.md`](prd/REQUIREMENTS.md).
  EA-10 D150 accepted the documentation/process assessment packet with findings; it did not promote these `[proposed]` documents or validate product/legal readiness.
- **Rust workspace:** `crates/ln-*` — see the repository map for the executable
  44-member inventory and the distinction between twenty ADR-0011 owners,
  runners, composition, shared infrastructure/verification, and the repository
  tracer. Hexagonal boundaries (ADR-0015): domain → ports → application →
  adapters.
- **Python harness:** `src/law_nexus_harness/` (ADR-0007 `[validated]`) —
  repository control-plane only: governor, preflight, ADR/Cargo/GSD/CI
  orchestration. No product/domain logic, no forbidden PyO3/FFI.
- **ADRs:** [`doc/adr/`](doc/adr/) — MADR-format with mandatory D098 lifecycle
  tags. Direction (ADR-0004..0015) + temporal legal ontology chain
  (ADR-0016..0022) + ADR-0023 applicability ownership boundary + ADR-0024
  non-authoritative Review Case intake/disposition contour `[proposed]`. Index:
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

## Short roadmap

The detailed, tracked cold-reader roadmap is
[`prd/project-state/roadmap.md`](prd/project-state/roadmap.md); migration and
proof-gate detail lives under [`prd/migration/`](prd/migration/).

**Open sequencing decision:** parser-G2-first, CTV-first, and
infrastructure-first have materially different costs and dependencies.
Assessment 18 intentionally leaves that choice human-owned. The candidate fronts
below are deliberately **not ordered** and this README does not silently resolve
their dependencies or investment priority.

- **Keep the repository boundary green — ongoing control.** Preserve
   Rust-only product ownership, lifecycle honesty, provider isolation, glossary
   stop-signals, document freshness, and the historical-view quarantine. This
   is maintenance, not a substitute for product work.
- **Reach parser G2 — candidate evidence front, human criteria required.** Build
   independent multi-fixture Consultant and Garant structural goldens with
   source hashes, annotations, hostile cases, and accepted quality and
   representativeness thresholds. Current ceiling remains G1 `[bounded]`.
- **Implement L2 CTV — candidate ontology runtime front.** After parser-data
   readiness is accepted, define human-owned event/correction contracts and
   implement event-sourced component versions, bitemporal audit history, and
   fail-closed resolution in Rust. No event enum or stable API has yet been
   accepted.
- **Land real TEI/RuVector adapters — evidence-gated infrastructure front.**
   Exercise shared port contracts against local USER-bge-m3 embeddings and
   RuVector storage, including dimensions, provenance, recovery, and hostile
   failures. InMemory evidence cannot satisfy this step.
- **Close retrieval and citation gates.** Introduce accepted evidence-span and
   citation contracts, exact source-byte round trips, real-corpus retrieval
   evaluation, explainable results, and no-answer behavior before any legal
   answer claim.
- **Expand temporal/legal reasoning only by explicit decisions.** NormRule IR,
   applicability DSL/runtime, conflict/practice/transition/profile layers,
   deterministic APIs, error taxonomy, and executable legal goldens require
   named human owners plus TDD and source-bound review.
- **Validate and release only after matching proof.** R035/R038, operational recovery, security,
   concurrency/scale, representative legal review, packaging, and release
   evidence must match the scope of any `[validated]` claim.

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
uv run python -m law_nexus_harness.governor     # process + ADR/lifecycle/retired-era probes
uv run python -m law_nexus_harness.preflight
uv run pytest -q                               # full suite; CI process suite is a subset
uv run python scripts/verify-adr-conformance.py

# Rust product gates
cargo fmt --check --all
cargo clippy --workspace --offline --all-targets -- -D warnings
cargo test --workspace --offline
```

Governor ADR/lifecycle probes (advisory unless noted) include:

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

The tracked Product Contract and requirements projection are published
`[proposed]` documents with EA-02 state `ready-for-assessment`; EA-10 D150
accepted the assessment packet, not product behavior or these documents as
validated product authority.

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
- Architectural decision substance is published in [`doc/adr/`](doc/adr/);
  unpublished workflow state cannot replace an ADR.
- Historical ACP/git-lex is **archive-only**; historical FalkorDB is **not active**;
  the active graph/vector target is RuVector (ADR-0014 `[proposed]`).
- Retired ADR IDs **0001/0002/0003/0006** have no files under `doc/adr/`; cite only
  with historical/retired/rejected qualifiers (governor `adr-retired-id-ban`).
