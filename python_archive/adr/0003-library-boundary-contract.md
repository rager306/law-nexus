---
id: ADR-0003
title: Library boundary — Pydantic, Adaptix, and stdlib dataclasses
status: Accepted
lifecycle: "[validated] (boundary-records Pydantic + stdlib dataclass usage); domain-forms [proposed] (ADR-0001); Adaptix mapping [deferred]"
date: 2026-06-22
supersedes: none
related: [ADR-0001, D001, D035, D037, D046]
---

# ADR-0003: Library boundary — Pydantic, Adaptix, and stdlib dataclasses

## Status

Accepted `[validated]` for the parts of the boundary that are already exercised in
production-shaped verification (the M006 parser boundary-records are Pydantic v2
strict models, and stdlib `@dataclass` is the established shape for verifier and
extractor records across `scripts/`).

The **domain forms** (`src/law_nexus/domain/`) are Pydantic v2 but `[proposed]`
per ADR-0001 — they are D046 shapes that harden when parser data arrives, not
D046 *proof*. The **Adaptix mapping** between parser boundary-records and
domain forms is `[deferred]` — recorded here as a reserved contract, not built,
because no non-trivial mapping exists yet. These tags are not smoothed up: the
contract is `[validated]`, the domain forms are `[proposed]`, the mapping is
`[deferred]`.

## Context

The project uses three data-modelling mechanisms, and a post-M068 boundary
review found that **the rule for which goes where was recorded (D001 → D035 →
D037 → ADR-0001) but not surfaced in the living truth oracle**, and that the
single seam the rule exists to protect was **not contracted**. Three concrete
gaps surfaced:

1. **The oracle is silent.** `prd/ARCHITECTURE.md` — the living truth oracle
   D098 mandates reading first — does not mention the library boundary at all.
   A future agent reasoning from the oracle alone cannot see it.

2. **Adaptix is an orphaned dependency.** D001 reserved `adaptix` for data
   mapping; D035 narrowed that to *non-trivial mapping between boundary DTOs
   and internal records*. Six milestones later (M001 → M068) Adaptix has
   **zero real consumers** — only a tooling-presence test references it. It is
   neither used nor explicitly `[deferred]`, which is exactly the silent-drift
   shape D098 warns against.

3. **The boundary-record ↔ domain-form seam is uncontracted.** There are today
   two parallel Pydantic model sets with **overlapping but distinct** semantics:

   | Concept | Parser boundary-record (`scripts/parser_records.py`) | Domain form (`src/law_nexus/domain/`) |
   |---|---|---|
   | document | `DocumentRecord` (id `DOC-*`, title, record_kind, schema_version) | `SourceDocument` (source_id, source_system, source_provenance_class, sha256, act_number, edition_date) |
   | block | `SourceBlockRecord` (id `BLOCK-*`, document_id, order_index, location, excerpt) | `SourceBlock` (block_id, source_document_id, block_type, order, text, char_start, char_end) |

   The boundary-record carries the I/O contract (id patterns, record_kind,
   explicit `schema_version`, JSONL-shaped, JSON-Schema-generating); the domain
   form carries the domain (provenance class, SHA identity, character spans).
   This is precisely the **boundary-DTO ↔ internal-record** seam D035 reserved
   Adaptix for — but no converter exists and the mapping is not written down.

The forces at play: Pydantic v2 is strongest at I/O boundaries (malformed
external records, field-level diagnostics, JSON Schema, fail-closed
immutability) and is already the recognised shape for future agents (D035,
ADR-0001). Adaptix is strongest at configurable conversion that preserves
domain-model separation — but that value only materialises when mappings become
non-trivial, which they are not while the parser product is not yet wired.
Stdlib `@dataclass` is the right lightweight choice for verifier/extractor
internal records that need no validation, and it is already the established
shape there.

**Significance-gating (self-check, per the README standard):** this decision
meets the *Layer / contract change* criterion — it contracts the boundary
between two model layers (parser I/O records and domain forms) and fixes the
serialization/validation library assignment per layer. It also touches the
*Persistent tech choice* criterion in freezing Pydantic as the domain and
boundary form and Adaptix as the reserved mapping mechanism.

## Decision

Adopt a **three-way library boundary** with one owner per concern, and contract
the seam between parser boundary-records and domain forms as a `[deferred]`
Adaptix mapping.

### 1. Pydantic v2 — domain forms and parser I/O boundary-records `[validated]` / `[proposed]`

Pydantic v2 `BaseModel` is the form for both the domain layer and the parser
I/O boundary:

- **Parser I/O boundary-records** (`scripts/parser_records.py`:
  `DocumentRecord`, `SourceBlockRecord`, `RelationCandidateRecord`,
  `ConsultantHierarchyRecord` over `StrictRecordModel` with
  `extra="forbid", strict=True`, `TypeAdapter`, explicit `schema_version`, and
  generated JSON Schemas) — `[validated]` since M006.
- **Domain forms** (`src/law_nexus/domain/`: `SourceDocument`, `SourceBlock`,
  `LegalUnit`, `ActEdition`, `EvidenceSpan`, `NormStatement`, `Citation`,
  `SourceTier`) — `[proposed]` per ADR-0001: D046 shapes that harden when parser
  data arrives, not D046 proof.

Pydantic owns validation, field-level diagnostics, JSON Schema generation, and
fail-closed immutability (`EvidenceSpan`'s SHA-keyed frozen model is an R034
fail-closed contract).

### 2. stdlib `@dataclass` — verifier and extractor records `[validated]`

Plain `@dataclass(frozen=True)` is the shape for internal records inside
`scripts/` verifiers, extractors, and graph builders (e.g. the architecture
graph extractor's item/edge records, parser-staging graph nodes, install
manifests). These records carry no validation burden — they are produced and
consumed by trusted code — and stdlib dataclasses keep them dependency-free and
recognisable. This is the established pattern across `scripts/` and is left as-is.

### 3. Adaptix — mapping between boundary-records and domain forms `[deferred]`

Adaptix is **reserved, not built** as the mapping layer between parser
boundary-records and domain forms. The contracted mapping pairs are:

| Boundary-record (`scripts/parser_records.py`) | Domain form (`src/law_nexus/domain/`) |
|---|---|
| `DocumentRecord` | `SourceDocument` |
| `SourceBlockRecord` | `SourceBlock` |

Mappings for `LegalUnit`, `ActEdition`, `EvidenceSpan`, and `NormStatement`
enter scope when the parser product introduces them as domain outputs. The
mapping is `[deferred]` until the parser product (per the M034 roadmap) actually
wires the boundary-record stream into the domain — at that point the mappings
become non-trivial and Adaptix is the intended mechanism. Until then Adaptix
remains a declared dependency with no consumer, explicitly tagged `[deferred]`
so its absence is not mistaken for an oversight.

### The seam, in one line

> Parser I/O boundary-records (`[validated]` Pydantic) and domain forms
> (`[proposed]` Pydantic) are distinct models of overlapping concepts; the
> mapping between them is an Adaptix converter, `[deferred]` until the parser
> product wires it.

### Per-claim D098 lifecycle tagging

Following ADR-0001's and ADR-0002's discipline, the claims here are tagged
individually and not smoothed up:

- Parser boundary-records are Pydantic v2 — `[validated]` (M006 strict models,
  JSON Schema, live `TypeAdapter`).
- Domain forms are Pydantic v2 — `[proposed]` (D046 shapes, ADR-0001; harden
  when parser data arrives).
- stdlib `@dataclass` for verifier/extractor records — `[validated]` (long-standing
  established usage across `scripts/`).
- Adaptix mapping boundary-record ↔ domain-form — `[deferred]` (reserved contract,
  no consumer, activates at parser-product milestone).
- The library-boundary rule itself (this ADR) — `[validated]` as a recorded
  contract, because it restates and consolidates already-accepted decisions
  (D001, D035, D037, ADR-0001).

## Consequences

- **What becomes easier.** A future agent (or the parser-product milestone) has
  one place to read the library boundary and the contracted seam. The
  `DocumentRecord ↔ SourceDocument` and `SourceBlockRecord ↔ SourceBlock`
  mapping is named before it is built, so implementing it is a matter of filling
  a contracted converter rather than re-deriving the boundary. The oracle no
  longer hides the rule.

- **What becomes harder.** Two parallel Pydantic model sets must be kept
  coherent as both evolve. When the domain forms harden (`[proposed]` →
  `[validated]`), each contracted mapping pair must be reconciled against the
  boundary-record fields, and the Adaptix converter built — that is real work
  owned by the parser-product milestone, not this ADR.

- **What we will need to revisit.** When the parser product wires the
  boundary-record stream into the domain, promote the Adaptix mapping from
  `[deferred]` to `[bounded]`/`[validated]` and confirm the contracted pairs
  still hold field-for-field. If a future review concludes Adaptix will never be
  justified (the mappings stay trivial), remove it from dependencies and record
  the removal as a superseding decision — do not let it revert to a silent
  orphaned dependency.

## Alternatives Considered

### Option A: Adaptix as the first-line domain form

Model the domain layer with Adaptix instead of Pydantic (`src/law_nexus/domain/`).

- **Pros:** a single mapping-capable library across domain and boundaries;
  avoids a second data-modelling dependency.
- **Cons:** D035 already settled this — Pydantic v2's `BaseModel`/`TypeAdapter`/
  JSON Schema ecosystem is strongest for malformed external records and is the
  most recognisable shape for future agents. ADR-0001 (Option C) explicitly
  rejected dataclasses/attrs/Adaptix for the core on the same grounds. Switching
  the domain to Adaptix would re-open a settled decision with no new evidence.
  **Rejected.**

### Option B: Remove Adaptix from dependencies now

Drop `adaptix` from `pyproject.toml` until a mapping consumer exists.

- **Pros:** no orphaned dependency; smaller dependency surface.
- **Cons:** the boundary-record ↔ domain-form seam is a *contracted future
  mapping* (the pairs are named above), and Adaptix is the intended mechanism
  once it activates. Removing it now means re-adding it (and re-justifying it)
  at the parser-product milestone, and loses the explicit `[deferred]` signal
  that flags the seam as deliberately reserved. The orphaned state is the
  problem, not the dependency — tagging it `[deferred]` (this ADR + the oracle
  line) fixes the drift without churning dependencies. **Rejected.**

### Option C: Build the Adaptix converter now

Implement `DocumentRecord → SourceDocument` and `SourceBlockRecord →
SourceBlock` converters in this slice.

- **Pros:** removes the "uncontracted seam" gap fully, not just on paper.
- **Cons:** there is no real consumer yet — the parser product is not wired
  (M034 roadmap), and the domain forms are still `[proposed]`. Building a
  converter against un-hardened forms produces a converter that will be
  rewritten when the forms harden. D035's own condition ("when mappings become
  non-trivial") is not met. This ADR's job is to *contract* the seam so the
  future converter is a fill-in, not to build it prematurely. **Rejected.**

> All three alternatives either re-open a settled decision, remove a deliberately
> reserved dependency, or build prematurely. The chosen decision contracts the
> seam now and defers the converter until the parser product makes it real.

## References

- **ADR-0001** — Onion package structure for `src/law_nexus`; established the
  domain layer as `[proposed]` Pydantic v2 (Option C rejected dataclasses/attrs/
  Adaptix for the core).
- **ADR-0002** — ADR standard and the compliance-gate / ACP-checkpoint split;
  the `verify-adr-conformance` gate that enforces D098 lifecycle tags on the
  claim files this ADR lives in.
- **D001** — original project tooling baseline reserving `adaptix` for data
  mapping/serialization needs.
- **D035** — Pydantic at parser I/O boundaries for normalized records and JSON
  Schema; Adaptix reserved for non-trivial mapping between boundary DTOs and
  internal records. The canonical boundary decision this ADR consolidates.
- **D037** — Pydantic v2 strict `DocumentRecord`/`SourceBlockRecord`/
  `RelationCandidateRecord` boundary models with JSON Schema (M006/S02).
- **D046** — keep the project-local LegalGraph core as the internal contract;
  the `[proposed]` domain forms are D046 shapes, not D046 proof.
