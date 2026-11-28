---
id: ADR-0032
title: Temporal CST/AST core, unified DocumentContext, and ChangeGrammar vertical proving spike
status: Proposed
lifecycle: "[proposed]"
date: 2026-11-28
supersedes: none
related: [ADR-0009, ADR-0011, ADR-0013, ADR-0014, ADR-0015, ADR-0016, ADR-0017, ADR-0018, ADR-0019, ADR-0028, ADR-0029, ADR-0030, ADR-0031]
---

# ADR-0032: Temporal CST/AST core, unified DocumentContext, and ChangeGrammar vertical proving spike

## Status

**Proposed [proposed]** — design and sequencing decision for proving the core
normative-act Temporal CST/AST + `DocumentContext` + `ChangeGrammar` vertical
end-to-end before committing to persistent storage or UI/API investment. No new
Rust public types are minted by this ADR, no `RC*` finding or `TSG-*` row is
closed, no parked milestone (`M208`, `M215–M220`) is auto-released, and no
lifecycle tag on ADR-0014..0031 is promoted.

## Context

An architectural reconciliation against `HEAD` (`prd/architecture/core-gaps-reconciliation.md`)
established four verified facts:

1. **The upstream substrate and downstream shell exist; the causal core bridge is missing.**
   - Lossless CST extraction (`crates/ln-decode/src/source_package.rs`), covering
     lexer (`crates/ln-decode/src/lexer.rs`, ADR-0028), `LocalGrammar`
     (`crates/ln-decode/src/local_grammar.rs`), M211 NPA reference capture
     (ADR-0029, with `RC28-F06..F12` closed), and durable `ThreeCanonEventLog` /
     `CheckoutProjection` (`crates/ln-temporal/src/domain.rs`) are already
     implemented as `[bounded]` / `[proposed]` Rust crates.
   - However, **zero lines** in `crates/` implement amendment-text parsing
     (`ChangeGrammar` / `RC28-F13`, M208 parked) or deterministic legislative
     event compilation (`MC-F` / `MC-PIPE` steps 3–7; `crates/ln-temporal/src/domain.rs`
     explicitly disclaims the crystal compiler and `MicroOperation`).
   - Consequently, `RC28-F17` remains open: the 118-edition 44-ФЗ timeline
     (M224 / ADR-0031) proves post-hoc digest and amend-marker provenance, not
     causal compilation from amending provisions to reconstructed edition deltas.

2. **Two structural debts sit directly on the core path.**
   - `document_context.rs` is duplicated across two crates
     (`crates/ln-decode/src/document_context.rs` and
     `crates/ln-temporal/src/document_context.rs`), creating drift risk before
     wiring amendment parsing.
   - Runtime morphology (`MorphEvidenceSet`) remains deferred
     (`crates/ln-temporal/src/semantic_scope.rs`), leaving agreement and
     case-inflection cues outside a clean optional boundary.

3. **Storage direction is forked while the core query/write shape is unproven.**
   - `prd/ARCHITECTURE.md` carries ADR-0014 (`RuVector [proposed]`), whereas
     ADR-0031 schedules an unexecuted M217 store bake-off (`Oxigraph` /
     `Kuzu+DuckPGQ` / `XTDB`). Locking persistent storage, embedding servers, or
     UI layers before the Temporal CST/AST core proves its real access patterns
     risks building infrastructure around an unverified semantic kernel.

4. **Single-act multi-edition corpus bottleneck.**
   - As measured in ADR-0031, `consru_export` carries populated `edition_number`
     and distinguishable revision dates for only one act (`44-ФЗ`, 118 editions).
     Proving that `WALK-T` / `WALK-I` and `ChangeGrammar` do not overfit `44-ФЗ`
     requires exercising at least one second dated multi-edition act or official
     publication C0/C1 pair.

5. **Synthesis discipline (Pullenti 4.34 clean-room boundary, D380).**
   - Pullenti's `DecreeChange` analyzer demonstrates a strong domain pattern for
     Russian amending statutes: decomposing amending clauses into explicit
     structural slots (`OWNER`, `KIND`, `CHILD`, `VALUE`, `PARAM`, `LOCVALUE`)
     over a token + local-grammar plane.
   - Per D380, `assessment/26`, and `doc/review/review-28-10-09-2026.md`,
     law-nexus adopts **architectural patterns only** — never Pullenti source
     code, compiled dictionaries (`m_ru.dat`), mutable token chains, global
     analyzer init order, uncalibrated numeric thresholds (`max - min <= 200`),
     or `SemanticService` v0.3 heuristics.

## Decision

### D1 — Core-First Vertical Trajectory

Prioritize proving the **Temporal CST/AST + Unified `DocumentContext` +
`ChangeGrammar` vertical** before committing to persistent storage backend
selection, TEI embedding integration, or UI/API expansion:

```text
SourceArtifact (lossless CST green: source_package.rs)
  -> Covering Lexer (lex(), ADR-0028)
  -> Unified DocumentContext + LocalGrammar + optional MorphEvidenceSet
  -> ChangeGrammar (slot decomposition: OWNER / KIND / CHILD / VALUE / PARAM / LOCVALUE)
  -> Typed MicroOperation candidates (Proposed, bounded subset)
  -> Append-only LegalEventAssertion ledger (ThreeCanonEventLog, INV-01/04/05/11)
  -> Deterministic Compiler Fold (WALK-T + WALK-I from earliest oracle)
  -> EditionOracle verification (INV-09a/09b/09c, scoped drift = 0, typed Discrepancy)
```

All semantic planes in `prd/architecture/model-crystal.md` (`MC-SEPARATION`)
stay strictly orthogonal: `Identity`, `Designation`, `SourceExpression`,
`TextContent`, `StructuralMembership`, `EditorialPresence`, `Force`,
`TransitionConstraint`, `ReferenceMention/Binding/Semantics`, and
`AssertionKnowledge`. No stage may collapse text existence into legal force or
use an `EditionOracle` snapshot to overwrite causal history (`MC-F`).

### D2 — Consolidate `DocumentContext` Behind One Crate Boundary

Before introducing `ChangeGrammar`, retire the duplicate `document_context.rs`
implementations (`crates/ln-decode/src/document_context.rs` and
`crates/ln-temporal/src/document_context.rs`) behind a single version-bound
`DocumentContext` contract (preserving ADR-0011 KOF-DA ownership and the
`crate-dependency-allowlist.json` DAG):

- `ln-decode` owns source-anchored structural indexing (`DocumentStructureIndex`),
  covering `lex()` spans, `LocalGrammar` frames, and read-only context lookup.
- `ln-temporal` consumes immutable context snapshots/records via explicit ports
  or value contracts without duplicating document-context resolution logic.
- An explicit optional `MorphEvidenceSet` trait/value boundary is reserved on
  covering `Word` tokens only (per ADR-0028 dual-tokenizer discipline), allowing
  morphology evidence to plug in cleanly when dictionary provenance is gated
  without rewriting lexer, context, or `ChangeGrammar` consumers.

### D3 — Clean-Room `ChangeGrammar` Contract (`RC28-F13` path)

Design `ChangeGrammar` as a pure, deterministic, fail-closed parser plane above
`lex()` + `DocumentContext` + `LocalGrammar`:

- **Slot alphabet (pattern synthesis from Russian drafting practice & Pullenti
  `DecreeChange`, clean-room per D380):**
  - `OWNER` — target normative act and structural locator (`ComponentLocator` /
    `DesignationVersion`, never raw mutable string substitution);
  - `KIND` — amending action verb family mapped strictly onto the closed
    `prd/architecture/operation-registry.yaml` operation families;
  - `CHILD` — target sub-component or anchor inside `OWNER`;
  - `VALUE` — quoted replacement/inserted text span (byte-anchored to source CST);
  - `PARAM` — positional qualifier (`после слов ...`, `в абзаце ...`, `дополнить предложением`);
  - `LOCVALUE` — matched anchor text span within the target component.
- **Bounded initial `MicroOperation` subset (`MC-OPS`):** prove five core
  operations first before widening the surface:
  - `OP-T`: `ReplaceText`, `InsertText`, `DeleteText`
  - `OP-S`: `Attach`
  - `OP-F`: `Repeal` (strictly four-axis per `MC-REPEAL`: `ForceStatus = Repealed`,
    `StructuralMembership = Absent`, `EditorialPresence = Tombstone`,
    `TextAvailability = HistoricalOnly` — never physical child deletion).
- **Fail-closed output (`MC-RES` / `INV-10`):** every parsed clause yields
  `Proposed` candidates carrying byte `EvidenceSpan`, or a typed non-success
  (`TargetNotFound`, `AmbiguousTarget`, `PreconditionMismatch`,
  `BaseVersionMismatch`, `OrderingConflict`, `UnknownEffect`,
  `UnsupportedOperation`, `IncompleteSource`). Never emit `None` or silent
  heuristic fallback.

### D4 — Vertical Proving Spike, Invariants, and Kill/Pivot Criteria

Validate the core model via a narrow, falsifiable vertical spike (executed via
`ce-prototype` or bounded `ce-work` slice, without promoting any ADR lifecycle):

1. **Proving corpus:**
   - Primary C1 chain: `44-ФЗ` baseline edition plus real C1 amending acts
     already acquired in the corpus (`138-ФЗ`, `333-ФЗ`, `484-ФЗ`), replaying
     forward from the earliest available edition oracle (`WALK-I` / `WALK-T`)
     and verifying reconstructed text/structure against the target
     `EditionOracle` (`INV-09c`, `drift = 0` on covered provisions, explicit
     typed `Discrepancy` on uncovered provisions).
   - Non-overfitting control: at least **one non-44-ФЗ act** with two dated
     official/export editions and an explicit amending act, proving no
     44-ФЗ-specific hardcoding.
2. **Mandatory metamorphic invariants (`MC-INV`):**
   - `INV-01`: repeated deterministic replay yields identical root hash;
   - `INV-04`: future scheduled/uncommenced effects never leak into a
     historical checkout;
   - `INV-06`: mutating a reference target never mutates the recorded
     `ReferenceMention` source span;
   - `INV-10`: zero `None` substitutions for legally meaningful typed failures.
3. **Explicit kill / pivot criteria (falsifiability):**
   - If deterministic `ChangeGrammar` coverage on real Russian federal-law
     amending clauses stalls below a human-reviewed useful floor (or produces
     unbounded false-positive `Applied` mutations against `EditionOracle`), do
     **not** introduce opaque LLM auto-patching or heuristic smoothing.
   - Instead, pivot the primary ingestion path to **oracle-diff + structured
     amend provenance** (building on ADR-0031 D1/D3) while retaining
     `ChangeGrammar` as a bounded high-precision extractor for unambiguous
     clause families, with every unresolved delta surfaced as typed
     `UnsupportedOperation` / `Discrepancy` for human adjudication.

### D5 — Decouple Parallel Plumbing Behind Existing Ports

Until the D4 vertical proving spike completes and is human-reviewed:

- Persistent storage selection (`ADR-0014` RuVector `[proposed]` vs `ADR-0031`
  M217 store bake-off `[proposed]`), TEI embedding serving, and API/UI layers
  stay decoupled behind existing hexagonal `ln-storage` and `ln-query` ports.
- Parallel plumbing work may improve adapters, CI, or observability behind
  those ports, but must not hardcode storage schemas or UI projections into the
  Temporal CST/AST core (`ln-decode`, `ln-temporal`, `ln-replay`,
  `ln-kb-ontology`).

## Consequences

- **Positive:** Engineering effort concentrates on the highest-uncertainty,
  highest-value part of law-nexus (`RC28-F13` + `RC28-F17`) with an objective
  `EditionOracle` checksum (`drift = 0`), preventing premature storage/UI
  lock-in.
- **Positive:** Eliminating `document_context.rs` duplication reduces
  maintenance drift across `ln-decode` and `ln-temporal`.
- **Trade-off:** Persistent storage selection (ADR-0014 vs ADR-0031 M217) and
  full-corpus retrieval readiness remain intentionally deferred until the core
  vertical spike delivers measured evidence.
- **Constraint:** Every new public contract or Rust type introduced by the
  spike must still check `prd/temporal-legal-model.md` §3 and respect
  `deferred-undefined` / `runtime deferred` stop-signs and KOF-DA crate
  ownership (ADR-0011).

## Non-claims

- This ADR is `[proposed]` design direction only; it does not validate
  `ChangeGrammar`, Temporal CST/AST compilation, parser G2 readiness, legal
  correctness, or product readiness.
- It does not mint Rust types, release parked milestones (`M208`, `M215–M220`),
  close `RC28-F13`, `RC28-F16`, `RC28-F17`, or any `TSG-*` row, or replace
  human Review Case adjudication (ADR-0024).
- It does not supersede ADR-0014 or ADR-0031; final persistent storage
  selection requires separate post-spike evidence and explicit human decision.
- It authorizes zero Pullenti source code, dictionary files, or numeric
  thresholds in the repository (D380).

## References

- `prd/ARCHITECTURE.md` (living truth oracle)
- `prd/architecture/model-crystal.md` (`MC-F`, `MC-SEPARATION`, `MC-INV`, `MC-PIPE`, `MC-OPS`, `MC-RES`, `MC-DAG`, `MC-REPEAL`)
- `prd/architecture/core-gaps-reconciliation.md` (verified open gaps on `HEAD`)
- `prd/architecture/operation-registry.yaml` (E.2.1 design-only operation contract)
- `prd/temporal-legal-model.md` §3 (controlled vocabulary)
- `doc/adr/0009-five-clock-temporal-model.md`, `doc/adr/0011-kof-da-ownership.md`, `doc/adr/0013-universal-multi-source-parser.md`, `doc/adr/0014-ruvector-primary-infrastructure.md`, `doc/adr/0015-hexagonal-verification-architecture.md`, `doc/adr/0016-frbr-structural-legal-identity.md`, `doc/adr/0017-component-temporal-versioning.md`, `doc/adr/0018-normative-state-resolver.md`, `doc/adr/0019-normative-hierarchy-and-conflict.md`, `doc/adr/0028-typed-lexer-legal-marker-lexicon.md`, `doc/adr/0029-requisites-anchored-member-assembly-fsm.md`, `doc/adr/0030-corpus-uri-anchor-knowledge-layers.md`, `doc/adr/0031-reference-knowledge-layer-contract.md`
- `assessment/26-pullenti-semantic-morphology-synthesis.md` (D380 Pullenti clean-room boundary)
- `assessment/34-rust-npa-foundation-readiness-audit.md` (post-M214 foundation audit)
- `doc/review/review-28-10-09-2026.md` (`RC28-F13`, `RC28-F16`, `RC28-F17`)
