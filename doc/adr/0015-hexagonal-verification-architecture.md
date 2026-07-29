---
id: ADR-0015
title: Hexagonal verification architecture for law-nexus
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-29
superseds: none
related: [ADR-0004, ADR-0005, ADR-0007, ADR-0010, ADR-0012, ADR-0013, ADR-0014, D098, D056]
---

# ADR-0015: Hexagonal verification architecture for law-nexus

## Status

**Accepted `[bounded]` process decision.** law-nexus already practices overlapping
verification contours (domain/application tests, port-oriented contracts,
hostile adapter proofs, thin system journeys, governor/preflight process gates,
and lifecycle-tagged evidence). This ADR freezes that architecture as durable
policy and names the next process increments without claiming they are already
implemented.

**Critical ceiling:** this ADR does **not** claim that shared `ln-testkit`
contract crates, executable crate-dependency allowlists, proptest/mutation
nightlies, real RuVector/TEI adapter contracts, or production packaging
verification already exist as complete infrastructure. Those remain
`[proposed]` follow-ons unless separately proven.

## Context

law-nexus is a Rust-only product runtime with hexagonal per-capability crates
(`domain` / `ports` / `application` / `adapters`), a thin Python repository
harness (ADR-0007), hostile case proofs (HC-01..HC-20), bounded real-fixture
tracers for Consultant WordML and Garant ODT (ADR-0013), and process anti-drift
gates (governor/preflight, D098 lifecycle tags, ADR-0012 consequential evidence).

A traditional pyramid of `unit → integration → E2E` is insufficient here because:

1. legal/parser/retrieval claims must stay lifecycle-honest (D098);
2. in-memory fakes can over-prove application behavior that real adapters will
   not share;
3. process drift (CI, residual scripts, overclaims) has historically consumed
   more product focus than missing unit tests;
4. LLM/agent output and approximate retrieval must not use exact-string oracles.

External research on Ports & Adapters, contract testing, property/model-based
testing, and deterministic concurrency is useful only when adapted to these
constraints. Product runtime proof remains authoritative over research prose.

## Decision

Adopt **overlapping verification contours** as the law-nexus verification
architecture `[bounded]`. Prefer semantic oracles, shared port contracts, hostile
proofs, thin real journeys, and process gates over mock choreography or large
end-to-end suites.

### 1. Verification contours

| Contour | What it proves | Oracle | Dependencies |
|---|---|---|---|
| Domain semantic | value objects, policies, transitions | invariants / algebraic properties | no I/O |
| Application functional | use cases through driving ports | results, events, state, effects | deterministic fakes only |
| Port contracts | one semantics for every adapter of a port | shared contract suite | InMemory, Hostile, Real |
| Adapter integration | real protocol/serialization/error behavior | real external behavior | TEI/RuVector/redb when present |
| Composition | wiring of product CLI / runners | critical path starts and fails closed | near-production composition |
| System journeys | few business-critical end paths | observable system result | real fixtures, bounded |
| Architecture / process | dependency direction, lifecycle, residual debt | allowlist + governor/preflight | cargo metadata, tracked docs |
| Concurrency / resilience | interleavings, crashes, partitions | safety/liveness invariants | only when workers/durability exist |

These contours are mandatory as **policy**. Not every contour is fully instrumented
yet; missing instrumentation is process debt, not permission to skip the contour
when changing related code.

### 2. Port contract rule `[proposed]` for shared suite infra, `[bounded]` for intent

Every outbound port that has more than one adapter **must** have one semantic
contract suite exercised by:

1. the in-memory/fake adapter;
2. any hostile adapter;
3. each real adapter when it lands.

**In-memory fakes are not exempt.** Application tests may use a fake only when
that fake participates in the port contract suite (or the suite is explicitly
absent as tracked process debt for that port).

Minimum contract concerns by port class:

- **BlockDecoder:** family isolation (Consultant ≠ Garant); valid byte spans;
  unknown/hostile inputs fail closed or surface diagnostics; no silent data loss.
- **GraphStore / VectorStore:** identity uniqueness; not-found; no partial write;
  deterministic or explicitly unordered enumeration; dimension mismatch fail-closed.
- **Embedding:** fixed declared dimension for the TEI path; empty/oversized fail;
  no raw legal text logging.
- **Citation:** missing ≠ invented; invalid mirror rejected; provenance required.
- **Temporal / promote / gate ports:** no future knowledge; candidate ≠
  authoritative; promote only after independent verification; retry does not
  double-promote.

Shared suite packaging (`ln-testkit` or equivalent) is `[proposed]` until the
crate and first suites exist.

### 3. Semantic oracles over choreography `[bounded]`

Prefer assertions on:

- resulting state;
- domain events / diagnostics;
- authority and provenance;
- fail-closed error kinds;
- lifecycle tags and non-claims.

Do **not** default to asserting:

- exact internal call counts;
- helper method order;
- adapter-private implementation details;
- exact approximate ranking or free-form LLM text.

Interaction assertions are allowed only when the interaction itself is policy
(for example: promote forbidden before verify; audit before authoritative write).

### 4. Hostile and real-fixture proof `[bounded]`

Hostile adapter and hostile input suites remain first-class. Real-document
tracers remain `[bounded]` one-fixture-per-provider evidence unless a later
slice proves broader corpus coverage.

Consultant WordML and Garant ODT remain independent risk profiles (ADR-0013).
Do not mix provider assumptions in fixtures, contracts, or oracles.

### 5. Lifecycle honesty and non-claims `[bounded]`

Every consequential verification claim must carry a D098 lifecycle tag:

- `[proposed]` — direction only;
- `[smoke]` / `[bounded]` — limited real evidence;
- `[validated]` — only with independent proof that matches the claim ceiling;
- `[deferred]` — explicitly not now.

Release smoke, in-memory contracts, and synthetic probes must record **non-claims**
when they do not prove production packaging, corpus completeness, legal
correctness, or real infrastructure readiness (ADR-0012 / ADR-0014 ceilings).

`[validated]` storage/retrieval claims require real adapter evidence, not only
InMemory success.

### 6. Determinism as a port `[bounded]` intent

Inject or control:

- clock;
- id / fingerprint sources where product-visible;
- embedding port;
- filesystem/network boundaries.

Tests must not depend on wall-clock sleeps, shared mutable global ports, or
unordered golden output without canonicalization. CLI/JSON comparisons may
exclude explicit timing fields such as `duration_ms`.

### 7. Architecture dependency checks `[proposed]` executable, `[bounded]` design

Target dependency direction:

```text
domain
  ↑
application (defines ports)
  ↑
adapters/*
  ↑
bootstrap / product-cli / hc runners
```

Executable allowlist checking via `cargo metadata` (xtask or governor check) is
`[proposed]` until implemented. Design intent is already binding: domain must
not depend on adapters, Tokio, HTTP clients, or vendor SDKs.

### 8. Property, model-based, metamorphic, mutation, fuzz `[proposed]`

Adopt selectively when ROI is clear:

| Tool / method | Target | When |
|---|---|---|
| proptest | pure domain (spans, normalize, IDs, AST) | after pure cores stabilize |
| state-machine model | promote/gate/replay lifecycles | when stateful cores exist |
| metamorphic | retrieval/evidence relations | before ranking quality claims |
| cargo-mutants | domain/application nightlies | after contract suites exist |
| cargo-fuzz | hostile XML/ODT/codecs | after parser contracts solid |
| Miri/Kani | unsafe / tiny pure algorithms only | if unsafe appears |
| Loom/Shuttle/Turmoil | concurrency/crash only | when workers/durability exist |

Do **not** add Cucumber/BDD or Pact for internal Rust traits. Do **not** make
100% line coverage a quality gate.

### 9. CI profiles `[bounded]` policy

**Every PR / local gate (when relevant paths change):**

- `cargo fmt`, `clippy -D warnings`, `check`, targeted/workspace tests;
- process-only harness tests;
- ADR lifecycle conformance;
- governor/preflight when architecture/process surfaces change;
- port contracts for touched ports (once suites exist).

**Nightly / deeper:**

- full hostile HC set;
- proptest/mutants for domain/application;
- real adapter contracts when available.

**Before release claims:**

- release CLI smoke with non-claims;
- real-adapter contracts for any `[validated]` storage/retrieval claim;
- migration/recovery scenarios when durable storage is product-selected.

### 10. Anti-slop / crap-code detectors `[bounded]` process direction

Treat the following as process debt or gate failures, not style nits:

| Class | Example | Direction |
|---|---|---|
| Fake luxury | InMemory lacks conflicts/uniqueness | shared port contracts |
| Overclaim | `[validated]` from in-memory only | lifecycle + non-claims |
| Oracle collapse | verifier reuses builder helper | independent oracle rule |
| Process drift | dead CI steps, orphan scripts | governor residual scans |
| Choreography tests | assert call order of repository | ban unless policy |
| Nondeterministic goldens | wall clock / unordered maps | determinism ports |
| Residual historical active debt | product-era Python still active | archive waves |
| Dead tooling deps | unused import-linter after archival | dependency hygiene |

## Consequences

### Positive

- Agents and humans share one verification vocabulary aligned with hexagonal
  ports and D098 lifecycle honesty.
- Fake adapters stop being a silent source of false confidence.
- Hostile proofs, real tracers, and process gates remain first-class rather than
  being replaced by generic E2E volume.
- Future `ln-testkit`, crate allowlist, proptest, and mutation work have a home
  without premature implementation.

### Negative / costs

- Writing shared contracts is more work than ad-hoc tests.
- Some current InMemory adapters may fail once honest contracts exist; that is
  desired signal.
- Nightly mutation/fuzz cost appears later.

### Neutral

- Existing HC runners, decode/storage/query contracts, product CLI smoke, and
  governor/preflight remain authoritative until replaced by stronger shared
  suites.

## Non-claims

- No claim that `ln-testkit` already exists.
- No claim that crate-dependency allowlist is already enforced in CI.
- No claim that RuVector/TEI/redb contracts are validated.
- No claim that release packaging/deployment is proven.
- No claim of corpus completeness, legal correctness, or citation completeness.
- No claim that proptest/mutants/fuzz/Loom/Turmoil are currently required on every PR.

## Follow-on process increments

1. ~~Introduce shared port-contract packaging and force InMemory through it.~~
   **M145 `[bounded]`:** `crates/ln-testkit` provides VectorStore/GraphStore
   shared helpers; InMemory adapters are exercised from ln-testkit tests.
2. ~~Add executable crate dependency allowlist (xtask and/or governor).~~
   **M145 `[bounded]`:** `scripts/verify-crate-dependency-allowlist.py` plus
   tracked `prd/architecture/crate-dependency-allowlist.json`, wired into
   preflight/pre-commit/CI. Full domain/application/adapter layer tagging
   remains open.
3. Extend governor diagnostics for fake-without-contract and overclaim patterns.
   **M146 `[bounded]` inventory only:**
   `scripts/verify-port-contract-coverage.py` reports InMemory adapters not yet
   covered by ln-testkit (default report-only; `--strict` optional).
4. Add proptest to pure decode/query cores; mutants on domain/application nightlies.
5. When real storage lands, run the **same** contracts against real adapters.
6. ~~Expand shared suites beyond storage ports (decode, citation, promote, …).~~
   **M146 `[bounded]`:** citation + promotion shared contracts landed in
   ln-testkit with InMemory (and hostile citation negative). Decode and most
   other capability InMemory adapters remain uncovered inventory debt.

## References

- ADR-0004 / ADR-0005 — Rust product and target architecture
- ADR-0007 — Python harness boundary
- ADR-0010 — evidence kernel gates
- ADR-0012 — consequential evidence protocol
- ADR-0013 — multi-source parser boundary
- ADR-0014 — RuVector infrastructure ceiling
- D098 — lifecycle tags
- D056 — independent proof-review against vacuous tests
- `.agents/skills/law-nexus-rust/references/verification-matrix.md`
