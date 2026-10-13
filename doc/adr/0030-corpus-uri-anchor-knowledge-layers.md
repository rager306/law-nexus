---
id: ADR-0030
title: Consultant URI anchor as cross-system legal identity and JSON-LD knowledge layers over the XML→JSONL spine
status: Proposed
lifecycle: "[proposed]"
date: 2026-10-13
supersedes: none
related: [ADR-0016, ADR-0017, ADR-0020, ADR-0029, ADR-0028, ADR-0027, ADR-0013, ADR-0009, ADR-0015]
---

# ADR-0030: Consultant URI anchor as cross-system legal identity and JSON-LD knowledge layers over the XML→JSONL spine

## Status

`[proposed]` design decision. No runtime, no semantic acceptance (D667), no R1000 closure, no lifecycle promotion of ADR-0016..0022 / 0028 / 0029, no parked milestone released, no JSON-LD migration of the intermediate wire files (review 29 scope stands).

## Context

M223-d2q075 completed the XML→JSONL spine (source capture → reader projection → cleaned wire → analysis → consumers) over the full pinned 43 785-entry corpus: 43 783 accepted + 2 documented pinned-threshold residuals, verify-ledger exit 0, single binding, no XML re-parse in consumers. ARCHITECTURE.md names L2 CTV the first implementation priority once parser data is ready; that condition is now met.

Two identity planes must be kept distinct:

- **integrity identity** — `SourceIdentity ⊕ DocumentVersionRef` plus the `code_revision`/`binary` binding; it changes with every pipeline re-run under a new binding;
- **legal identity** — this act, this edition; stable across pipeline versions and across выгрузки. The JSONL spine is integrity-first by construction and cannot serve as the knowledge-graph key surface.

The Consultant link surface provides exactly one cross-system legal-identity anchor: the **URI token family**.

- offline `consultantplus://offline/ref=…` — an **opaque token**. law-nexus cannot decode it (keying material lives in the external Consru project). The catalog stores the full token verbatim as `editions.source_id`; the sanctioned join is an **exact-token match**. Searching by an extracted/decoded document number yields zero matches (verified).
- internal `consultantplus-internal://<fld>/<key>#P<para>` — open grammar (100% parse); decomposes to `(bank, document_key, para)`; `<fld>` is not a constant (34646/35946/0xFFFF variants); `para=4294967295` denotes the whole document.
- Resolution of targets to local files is dead (courts 5%, fas 4%, xml-ed 0%); the catalog is the sanctioned resolution oracle. Graphs and indexes must key by tokens/keys, never by file paths.

Practice/control banks (courts, FAS) are, by working assumption, **single-version** documents: no editions, no CTV machinery. Their temporality lives at the edge level (cited norms as of the issuing document's date) and at the content level (periods, events), not at the document level. This corresponds to ADR-0020 (L5 practice overlay: first-class temporality over the five clocks, non-authoritative).

## Decision

**D1 — Consultant URI anchor is a first-class legal-identity anchor, preserved byte-exact everywhere.** It appears in the JSONL identity envelope of every document, as graph node aliases, in edge records, and in publication artifacts. It is never decoded, never re-derived, never normalized. Joins are: exact-token match against the catalog (`editions.source_id`) for offline URIs; parse-based `(bank, document_key, para)` for internal URIs. A battery-level invariant asserts byte-exact URI survival across every transformation (same discipline as `assert_no_raw_text`).

**D2 — Practice/control banks are single-version.** No CTV/edition machinery is applied to them. Their identity is one URI anchor + `(bank, document_key)` + issue date; `document_groups` gains an explicit `non-normative` class (no normative ladder) so the assembly FSM and coverage checks do not silently misreport ~22k documents. Non-claim: discovering revisable practice documents is an explicit contract revision, not a silent exception.

**D3 — Practice temporality elaboration is sequenced after normative temporality.** The as-of-date qualification of practice→normative edges (which edition was in force at the citing document's date) is a hard consumer of the normative edition timeline (`edition_ast_at` over the corpus). Until that timeline exists (K1), edge qualification is not attempted; edges are extracted with raw source dates only. Where multiple candidate dates exist (decision date / event date / publication date), the system records all candidates plus an explicit qualification type (`as_of_decision_date` / `as_of_event` / `Unknown`) and never picks a legal interpretation unilaterally.

**D4 — The temporal model is built over the materialized JSONL layers** (reader projection + analysis envelope + navigation index + identity), never over raw XML at runtime. XML remains the capture input and the integrity/fallback anchor (binData retention stands). A fact missing from the JSONL is a producer extension under a tracked contract, never a hidden XML pass. The S05 clean view is a display channel, not the structural substrate of the temporal model.

**D5 — A JSON-LD knowledge layer family is added alongside the spine** as derived, non-authoritative, deterministic and reversible projections (D046 discipline):

- **G1 identity/edition graph** — URI anchors, Work/Expression mapping (ADR-0016 L1; ELI-compatible URNs per R5-07), edition timeline;
- **G2 reference graph** — mentions → targets, intra- and corpus-wide, with closed qualification types;
- **G3 temporal graph** — CTV events and as-of resolution (materialization of the normative temporality runtime);
- **G4 practice overlay** — decisions, citations, content periods (ADR-0020).

Layer invariants: legal-identity keys (URI/ELI-compatible), source anchors on every node, redaction (no raw decoded text), hash-binding to the source JSONL revision (drift detectable), RDF tooling confined to analysis/interop (R066 anti-runtime stands).

**D6 — Layer builders reuse the decode crates** (`ln-decode`, `ln-consultant-parser`); there is no second parser. Two build modes are admitted: in-spine sinks for facts the spine already carries, and XML-fed rebuilds (same crates) for signal the spine does not carry (tables, footnotes, binData-adjacent structure). Every layer carries a builder version and a source-anchor manifest enabling three-way reconciliation: XML ↔ JSONL ↔ JSON-LD.

## Rationale

The strict JSONL spine (frozen contracts, hashes, admission) and a free, semantically rich graph layer are complements, not competitors: the spine's strictness is exactly what makes an evolvable knowledge layer safe. The knowledge layers give the program: a stable legal-identity graph that survives pipeline re-binding; cross-document reference/temporal/practice graphs as first-class artifacts; an experiment plane for evolving semantics (P6–P9, L5/L6 vocabulary) without touching frozen contracts; a standards-based interop surface (ELI/LRMoo/URI anchors); and a cheap graph sandbox that de-risks the M217 storage decision. The `@context` vocabulary work coincides with the FRBR bridge of the normative temporality stage — the mapping is done once and serves both.

## Consequences

- Normative temporality (edition timeline over the corpus) precedes practice temporality elaboration (D3).
- The M217 storage decision is de-risked: knowledge is materialized in a portable standard form before a serving technology is chosen.
- R066 remains in force: no RDF/SPARQL tooling in product runtime paths.
- The JSONL spine stays frozen; layer extensions follow the producer-extension rule (D4).
- Vocabulary mapping (closed vocabularies → ELI/LRMoo/`cc:`) becomes a shared tracked artifact.

## Non-claims

Not semantic or legal acceptance; not authenticity evidence; not normalization; not physical pagination; not R1000 closure; not corpus-wide link correctness; not an un-parking of M208/M217–M220. Layer existence does not promote any `[proposed]` ADR to `[bounded]`/`[validated]`.

## Planned verification (at implementation)

1. Byte-exact URI survival invariant across every transformation (battery-level).
2. Exact-token catalog join tests (`editions.source_id`), including the zero-match negative for decoded-number search.
3. Single-version lift tests for practice banks (explicit `non-normative` class; no CTV machinery applied).
4. Layer determinism/reversibility: JSONL → JSON-LD re-derivation identity; three-way XML↔JSONL↔JSON-LD reconciliation.
5. As-of edge qualification tests strictly after the edition timeline exists (D3).
6. Redaction invariant over all published layer artifacts.

## References

ADR-0016 (L1 FRBR/LRMoo, R5-07 ELI/URI mapping), ADR-0017 (L2 CTV), ADR-0020 (L5 practice overlay), ADR-0009 (five clocks), ADR-0028 (typed lexer), ADR-0029 (requisites-anchored member assembly), ADR-0027 (multi-layer link classifier), ADR-0013 (universal parser), ADR-0015 (hexagonal verification); assessment 28 (NPA semantic process: P0–P9 + four FSMs; meta/prompt authority), assessment 34 (foundation readiness audit F01–F06 closures), review 29 (admission/model coherence; JSON-LD scope note), `prd/architecture/npa-semantic-process.yaml`, `prd/architecture/kb-ontology-*.md`, M223 consumer acceptance contract (`intermediate-source-consumer-acceptance-contract.md`), D046/D667/D738/D739/D740.
