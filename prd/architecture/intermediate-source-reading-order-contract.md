# Intermediate-source reading-order and composite-coordinate contract

**Status:** `[bounded]`
**Owning slice:** M223-d2q075 / S04 — design pin for
`crates/ln-decode/src/reader_reading_order.rs` (`reader_reading_order`, T02) and
`crates/ln-decode/src/reader_composite.rs` (`reader_composite`, T03); tests
`crates/ln-decode/tests/reader_reading_order.rs` and
`crates/ln-decode/tests/reader_composite.rs`; slice battery
`scripts/test_m223_s04_contract.py` (T04)
**Upstream wire contracts (frozen, `[bounded]`):**
`prd/architecture/source-jsonl-contract.md`,
`prd/architecture/reader-view-contract.md`,
`prd/architecture/reader-projection-contract.md`,
`prd/architecture/cleaned-projection-contract.md`,
`prd/architecture/npa-analysis-jsonl-contract.md`
**Upstream acceptance contract:** `prd/architecture/intermediate-source-acceptance-contract.md`
(§4 reading order versus record order, §5 composite provenance, §8 whole-corpus
acceptance boundary)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0029 (requisites-anchored member
assembly — anchor boundary), D631 (S02 reader coordinate base), D633 (S03
reader content seal / resealed semantic-tamper semantics), D634 (independent
verifier recomputes from the substrate), D639/D640 (cleaned JSONL envelope and
non-cyclic seals), D658 (NPA analysis envelope), D733 (this design pin: reading
order and composite coordinates, additive-only), D602/D328 (serde stays
module-scoped to `source_package`)
**Lifecycle ceiling:** this is a bounded design pin plus a read-only coordinate
surface over already-verified decoded source. It is **not** an R1000 closure
artifact, not a CST/AST, not a temporal `StructuralAst`, and not expert legal
gold. It closes no requirement. R1000 stays active/unclosed.

## 1. Purpose and non-claims

### 1.1 Purpose

S03 (`reader_projection` + `reader_verifier`) delivered the producer and the
independent verifier for the reader view forest over an already-verified decoded
source. Two gaps remain for S05–S07 consumers:

1. **Reading order is not a first-class, independently re-derivable surface.**
   The projection stores ordered segments with per-view `ordinal` and
   `output_start`/`output_end`, and the verifier recomputes per-view order
   internally, but there is no public accessor that makes "reading order is
   *not* record order" explicit and no independent re-derivation of reading
   order that a consumer can call without trusting the projection's own record
   stream.
2. **Composite coordinates do not exist.** A token span that crosses several
   fragments or a derived separator cannot be addressed: `ProjectedSegment.span`
   is always a whole-fragment span (`start = 0`, `end = value.len()`), and no
   type expresses an ordered list of source sub-spans plus derived kinds.

This document pins the design of both surfaces so T02 and T03 have one
unambiguous specification and S05–S07 (corpus materialization) have one shared
point of support.

The concrete surfaces this document fixes:

- **`reader_reading_order`** (T02): `ReadingOrderIndex::build(&ReaderProjection,
  &[Record])` independently re-derives the per-view reading order from the
  substrate event walk and compares it to the projection; public accessors
  `reading_order(&ViewId) -> &[SegmentId]`, `view_output(&ViewId) -> String`,
  `record_order(&[Record]) -> Vec<FragmentRef>`, and
  `is_record_order_coincident(...)`; fail-closed
  `ReadingOrderErrorKind::{OrderMismatch, OrdinalGap, OutputGap, UnknownSegment,
  NotPrimaryView}`.
- **`reader_composite`** (T03): `CompositeAddress`, `CompositeRange`,
  `CompositeUnit` (`SourceSpan` | `Derived`), `resolve_composite(...)`, and
  `to_address()` round-trip; fail-closed
  `CompositeErrorKind::{UnknownView, NotPrimaryView, EmptyOrInverted,
  OutOfBounds, NotCharBoundary, SpanInvalid}`.

### 1.2 Non-claims

- **Not** an R1000 closure artifact. It is one bounded coordinate surface feeding
  the wider R1000 program; closure is owned by M223 as a whole, not by S04.
- **Not** a CST, AST, Component Concept, CTV, `SourceBlock`, `SourceBlockRecord`,
  or temporal `StructuralAst`.
- **Not** XML byte coordinates. `ReaderFragmentSpan` indexes only the decoded
  `value` of a text record; `ElementRef` / `source_pos` name element records.
- **Not** a semantic oracle and **not** legal completeness, source authenticity,
  corpus coverage, or citation resolution. Reading order is reconstructed from
  the substrate event walk, never from a semantic label (acceptance contract §4).
- **Not** a clean-view or normalization pass; no XML re-parse. Every walk reads
  substrate records only.
- Provider-bounded to Consultant WordML (`reader_wordml_profile/v1`).
- Read-only: neither surface mutates, reseals, or re-bases the projection.

## 2. Reading order versus record order

### 2.1 The substrate event walk is the only source of reading order

Reading order is the text flow a reader sees. It is reconstructed from the
substrate document-event walk and fixed by per-view coordinates, and from
nothing else. The walk is the same pre-order capture uses
(`crates/ln-decode/src/reader_projection.rs` `document_events`):

1. an element's own `text_ref` (its text fragment) is emitted **before** its
   children, in capture order;
2. then each child is visited in order, and after each child its `tail_ref` (the
   parent-content text that follows the closed child) is emitted, then the next
   sibling.

`ProjectedSegment` records carry `ordinal` (position within the owning view) and
`output_start` / `output_end` (position in the view's decoded output). These
coordinates are the canonical reading-order fact for a view.

### 2.2 Record order is a storage fact

Record order is emitted `t0..tM` in document order, and the source package
serializes elements first, then texts. Ids are opaque; records are compared by
substrate coordinates (`element_ref`, `fragment_ref`), never by id equality
across runs. Record order is used for **identity, coverage, and determinism** —
not for text flow.

### 2.3 Reading order MUST NOT be derived from semantic, `source_pos`, or record order

A consumer is wrong if it derives reading order from any of:

- the `semantic` label — several fragments can share `ReaderSemantic::Body`, so
  their mutual order is recoverable only from the walk, never from the label;
- `source_pos` alone — `source_pos` is an element pre-order index, not a text
  position, and does not order text fragments of shared owners;
- record order (`t0..tM`).

### 2.4 The tail is the canonical divergence: capture owner ≠ semantic owner

A `TextSlot::Tail` fragment is the content *after* a closed element, so its
**capture owner** is the closed element that physically captured it, while its
**semantic context** is the parent (acceptance contract §2.1; reader-view
contract §5 rule 3). This is a *classification* fact, not an ordering fact:
`text_semantic` only labels a segment, it never sorts. T02 must prove the
divergence on a tail fragment where capture owner ≠ semantic owner, and on
several shared `Body` fragments whose mutual order is walk-only.

### 2.5 T02 model

`reader_reading_order` is `serde`-free, `std`-only, and modeled after
`reader_verifier` (independent recomputation from `&[Record]` through
`reader_contract` primitives; it must not call
`reader_projection::build_projection` and must not trust the projection's own
ordering, labels, or seal).

```
ReadingOrderIndex::build(&ReaderProjection, &[Record])
    -> Result<ReadingOrderIndex, Vec<ReadingOrderError>>
reading_order(&ViewId) -> &[SegmentId]        // per-view order, independent of record order
view_output(&ViewId)   -> String              // concatenated text/derived literal in reading order
record_order(&[Record]) -> Vec<FragmentRef>   // document order of tN substrate (contrast surface)
is_record_order_coincident(&[Record]) -> bool // explicit comparison surface
```

Closed failure kinds — `ReadingOrderErrorKind`:

| kind | meaning |
|---|---|
| `OrderMismatch` | re-derived per-view order differs from the projection's `ordinal`/segment sequence |
| `OrdinalGap` | per-view ordinals are not a contiguous `0..n` |
| `OutputGap` | `output_start`/`output_end` are not contiguous (or overflow the view output) |
| `UnknownSegment` | the projection references a `SegmentId` with no record |
| `NotPrimaryView` | a non-primary (navigation) view was asked for reading order |

A **resealed reorder is not accepted**: the index re-derives order from the
substrate, so permuting the projection's record stream (even with a fresh
`content_hash`) yields `OrderMismatch`.

## 3. Composite coordinates

### 3.1 Two provenance forms (acceptance contract §5)

A construction can cross several runs: two text fragments separated by a derived
control, a page break, etc. No single identifier is sufficient provenance, so
there are **two provenance forms**, one per segment kind:

- **Source-fragment segment** (`ReaderSegmentKind::Text`, `origin =
  source_fragment`): document identity ⊕ `element_ref` (capture owner, `eN`) ⊕
  `slot` (`text` | `tail`) ⊕ `fragment_ref` (`tN`) ⊕ decoded span `[start, end)`
  over the fragment's decoded value ⊕ `source_pos`.
- **Derived-control segment** (`ReaderSegmentKind::Derived` from `tab` / `br` /
  `cr`, `origin = derived:<kind>`): document identity ⊕ `element_ref` (the
  documented control element) ⊕ `source_pos` ⊕ derived kind (`tab` |
  `line_break` | `page_break`) ⊕ rule/profile.

A derived control has **no** `fragment_ref` and **no** span by construction; a
consumer must not invent one. A adjacency token span across several fragments or
a derived separator is a **composite range**: an ordered list of source spans
plus the derived kinds between them — not a single fictitious fragment slice.

### 3.2 T03 model

`reader_composite` is `serde`-free, `std`-only.

```
CompositeAddress { view: ViewId, output_start: usize, output_end: usize }
                  // half-open range over the view's decoded output

CompositeUnit = SourceSpan { segment, fragment_ref, slot,
                             span: ReaderFragmentSpan,
                             element_ref, source_pos }
              | Derived    { segment, kind: ReaderDerivedKind,
                             element_ref, source_pos }

CompositeRange { view: ViewId, units: Vec<CompositeUnit> }

resolve_composite(&ReaderProjection, &CompositeAddress)
    -> Result<CompositeRange, CompositeError>
CompositeRange::to_address() -> CompositeAddress   // round-trip
```

`resolve_composite` splits the addressed range over the view's ordered segments
via `reader_reading_order`. For every intersected text segment it emits a
sub-span `[start-offset, end-offset)` and validates it with
`reader_contract::check_fragment_span`. A derived segment yields a `Derived`
unit with no `fragment_ref` and no span. The result preserves provenance
read-only: it is copied, never re-based onto a different source, and never
re-derived from XML.

Closed failure kinds — `CompositeErrorKind`:

| kind | meaning |
|---|---|
| `UnknownView` | the address names no view in the projection |
| `NotPrimaryView` | composite resolution is defined only over primary views |
| `EmptyOrInverted` | `output_start >= output_end` |
| `OutOfBounds` | `output_end` exceeds the view's decoded output length |
| `NotCharBoundary` | a sub-span boundary is not a UTF-8 char boundary |
| `SpanInvalid` | `check_fragment_span` rejects a computed sub-span |

### 3.3 Invariants T03 must prove on the pinned mixed fixture

- a construction across two text fragments separated by a derived `tab`
  resolves to `[SourceSpan, Derived, SourceSpan]` with preserved provenance;
- a range across a page break resolves with the `page_break` derived unit;
- start/end inside a fragment produce sub-spans (`start > 0` / `end < len`);
- out-of-range / inverted / non-char-boundary / unknown-view / non-primary each
  yield the matching typed refusal;
- a derived unit never carries a fragment or span;
- provenance is read-only: resolving twice yields byte-identical units and the
  input projection is unchanged.

## 4. Additive-only over the frozen upstream wire contracts

This design is **additive-only**. The five upstream wire contracts below are
frozen as of the S04 design. The sha256 of each tracked file **at design time**
is pinned in the machine-readable inventory block. **No upstream contract is
changed silently.** Any extension to one of them is a recorded revision or a
recorded decision — never a quiet edit. T04's slice battery recomputes these
hashes and fails on drift; a drift is an explicit re-pin, not a silent update.

Frozen upstream wire-contract inventory (design-time sha256):

| Contract | sha256 |
|---|---|
| `prd/architecture/source-jsonl-contract.md` | `2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6` |
| `prd/architecture/reader-view-contract.md` | `80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d` |
| `prd/architecture/reader-projection-contract.md` | `95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e` |
| `prd/architecture/cleaned-projection-contract.md` | `7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e` |
| `prd/architecture/npa-analysis-jsonl-contract.md` | `a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb` |

Machine-readable form (T04 parses this block; keep one entry per line):

```
<!-- frozen-contract-inventory:begin -->
sha256:2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6 prd/architecture/source-jsonl-contract.md
sha256:80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d prd/architecture/reader-view-contract.md
sha256:95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e prd/architecture/reader-projection-contract.md
sha256:7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e prd/architecture/cleaned-projection-contract.md
sha256:a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb prd/architecture/npa-analysis-jsonl-contract.md
<!-- frozen-contract-inventory:end -->
```

Additional immutability constraints carried from the acceptance contract §2 and
§8:

- the **six tracked §2 files** (`crates/ln-decode/src/reader_projection.rs`,
  `reader_verifier.rs`, `npa_analysis_wire.rs`,
  `crates/ln-decode/tests/reader_tail_semantics.rs`,
  `npa_analysis_strict_admission.rs`, `m222_f07_audit.rs`) are **not** modified
  by S04;
- frozen `prd/architecture/*.jsonl` tracked artifacts are **not** modified;
- S04 adds new files (`reader_reading_order.rs`, `reader_composite.rs`, their
  tests, the slice battery, the evidence artifact) and registers the two modules
  in `crates/ln-decode/src/lib.rs` — an additive edit only.

## 5. S03 reconciliation

S04 reconciles with the S03 baseline (`prd/migration/rust-evidence/m223-s03-baseline-run.json`,
schema `m223-s03-baseline-run/v1`):

| fact | value |
|---|---|
| corpus entries | 43785 |
| accepted | 43785 |
| refused | 0 |
| incomplete | 0 |
| R1000 status | `active/unclosed` |

Reading order and composite coordinates are defined and exercised **per accepted
document**. Whole-corpus materialization of these surfaces over all 43 785
accepted documents is S05–S07, not S04. S04 must not restate S03's
integrity/count result as a semantic or legal claim: the S03 run is an
acceptance/integrity baseline, not a semantic oracle (acceptance contract §8.2).
`s03_baseline_reconciled` in the S04 evidence artifact records the four numbers
and `r1000_status` above, and nothing more.

## 6. Threat surface

- **Address tampering → fail-closed.** A `CompositeAddress` is untrusted input.
  `resolve_composite` validates view existence, primary-only scope, half-open
  ordering, bounds, char boundaries, and every computed sub-span via
  `check_fragment_span`; every violation is a typed refusal, never a partial or
  clamped result. Reading-order re-derivation is independent of the projection
  artifact, so a resealed reorder is refused.
- **Decoded legal text is not a secret.** The decoded text is provider-bounded
  Consultant WordML already admitted by the reader projection; it is not
  classified. Redaction applies to **evidence artifacts**, not to the in-memory
  model: `m223-s04-reading-order-battery.json` carries only paths, counters, and
  hashes — no raw decoded text. Decoded text is permitted only inside Rust tests
  over the tracked fixture.
- **Inputs are admission-verified projection records.** Both surfaces consume an
  already-verified `ReaderProjection` plus substrate `Record`s; they do not
  re-parse XML, do not re-open the corpus, and do not relax the S03 admission.
- **Idempotence / no rebasing.** Composite provenance is copied, not re-based; a
  consumer may project it into its own coordinates but may not drop the owner,
  invent a fragment for a derived control, or reassign a fragment to the wrong
  view (acceptance contract §5).

## 7. Requirement impact

- **R1000 — supporting-only. Do not close.** S04 delivers a bounded coordinate
  surface that supports the wider R1000 program (S05–S07 materialize it per
  accepted document); it is not an R1000 closure artifact and must not be
  reported as one. R1000 stays `active/unclosed` (acceptance contract §10;
  precedent: S03).
- No other R-ID is bound or re-labelled by S04. S04 adds no new requirement; it
  advances no requirement to `validated`.

## 8. Verification surface

- `crates/ln-decode/tests/reader_reading_order.rs` (T02): reading order of the
  primary view against a handwritten XML oracle on the pinned mixed fixture
  (`crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml`, sha256
  `d2fc1cd1…`); reading order ≠ `source_pos` order and ≠ `semantic` order (tail
  capture-owner divergence + several shared `Body` fragments); `record_order` ≠
  per-view reading order; malformed projection (ordinal gap / output gap) is a
  typed refusal; a resealed reorder is refused.
- `crates/ln-decode/tests/reader_composite.rs` (T03): the §3.3 invariants on the
  same fixture.
- `scripts/test_m223_s04_contract.py` (T04): (a) this document exists and carries
  the required sections/markers ("reading order vs record order", "composite
  coordinates", "frozen contract inventory", "S03 reconciliation"); (b) the five
  pinned sha256 values match the tracked files **exactly** (drift → explicit
  re-pin, never silent); (c) the S03 baseline is reconciled
  (entries = accepted = 43785, refused = 0, incomplete = 0, R1000
  active/unclosed); (d) it emits
  `prd/migration/rust-evidence/m223-s04-reading-order-battery.json`
  (schema `m223-s04-reading-order-battery/v1`) with counters/hashes and
  `non_claims`, carrying only paths, counters, and hashes.
- Cleanliness battery: `cargo test -p ln-decode --offline --test
  reader_reading_order --test reader_composite`; `cargo test -p ln-decode
  --offline`; `cargo fmt --all --check`; `cargo check --workspace --offline`;
  `cargo clippy --workspace --all-targets --offline -- -D warnings`;
  `uv run python scripts/verify-adr-conformance.py`.

## 9. Slice boundary S04 / S05

| Surface | Disposition |
|---|---|
| reading-order index, independent re-derivation, record-order contrast, typed errors | S04 (T02) — `reader_reading_order` |
| composite coordinates via runs with preserved provenance, typed errors | S04 (T03) — `reader_composite` |
| design pin + additive-only + S03 reconciliation + slice battery | S04 (T01/T04) |
| whole-corpus materialization of reading order + composite coordinates over all 43 785 accepted documents | S05–S07 |
| R1000 closure, legal completeness, source authenticity, citation resolution | not S04; remains out of scope |

Out of scope for S04: clean-view/normalization, XML re-parse, tokenization, CLI,
temporal `StructuralAst`/CST/CTV, and any R1000 closure. R1000 stays active.

## 10. References

- `prd/architecture/intermediate-source-acceptance-contract.md` §4 (reading
  order versus record order), §5 (composite provenance), §8 (whole-corpus
  acceptance boundary), §10 (non-claims).
- `prd/architecture/reader-view-contract.md` §4 (coordinate base), §5
  (ownership), §6 (coverage partition).
- `prd/architecture/reader-projection-contract.md` §3.2 (`ProjectedSegment`),
  §5 (independent verifier semantics).
- `prd/architecture/source-jsonl-contract.md`,
  `prd/architecture/cleaned-projection-contract.md`,
  `prd/architecture/npa-analysis-jsonl-contract.md`.
- `prd/migration/rust-evidence/m223-s03-baseline-run.json` (S03 baseline).
