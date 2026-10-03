# Reader-projection contract over the frozen source package

**Status:** `[bounded]`
**Owning slice:** M212-c25p2o / S03 — `crates/ln-decode/src/reader_projection.rs`
(`reader_projection`) and `crates/ln-decode/src/reader_verifier.rs`
(`reader_verifier`, planned); tests
`crates/ln-decode/tests/reader_projection_contract.rs` and
`crates/ln-decode/tests/reader_projection_tamper.rs` (planned)
**Upstream contract:** `prd/architecture/reader-view-contract.md` (S02, frozen,
`[bounded]`) — closed reader vocabularies, coordinate base, ownership map and
coverage partition
**Upstream substrate:** `prd/architecture/source-jsonl-contract.md` (frozen,
`[bounded]`) — the decoded `source_package` model
**Authority:** ADR-0013 (universal multi-source parser architecture),
ADR-0015 (hexagonal verification architecture), ADR-0029
(requisites-anchored member assembly — anchor boundary), D631 (S02 reader
coordinate base), D633 (S03 content seal and resealed semantic-tamper
semantics), D634 (independent verifier recomputes from the substrate), D636/D637
(S04 root-bound gate and boundary), D602/D328 (serde stays module-scoped to
`source_package`)
**Lifecycle ceiling:** this is a bounded reader-navigation projection over
already-verified decoded source. It is **not** an R1000 closure artifact, not a
CST/AST, not a temporal `StructuralAst`, and not expert legal gold. It closes no
requirement. R1000 stays active; S03 is a projection plus an independent
verifier, not a closure.

## 1. Purpose

S02 fixed the nouns (closed view/segment/origin/semantic/reference
vocabularies), the coordinate base (`FragmentRef` / `ElementRef` /
`source_pos` / `ReaderFragmentSpan`) and the ownership map plus coverage
partition. S03 turns those primitives into a **producer**:

- a deterministic **view forest** (`ProjectedView` records with `parent_view`
  and ordered `children`);
- ordered **source-fragment and derived segment** records (`ProjectedSegment`);
- **unresolved reference** records (`ProjectedReference`);
- a canonical serialization and a claim-free content seal; and
- an **independent verifier** (`reader_verifier`) that recomputes the expected
  view/segment/coverage/order/provenance semantics from the substrate — using
  `reader_contract` primitives, never the builder — and rejects loss and
  ownership substitution even after the projection has been resealed.

Pinned provider profile: `reader_wordml_profile/v1`. Raw decoded text, no
character normalization, provider-bounded Consultant WordML.

## 2. Non-claims

- Raw decoded text only. No normalization (nbsp, guillemets, dashes) is applied;
  NBSP and whitespace are preserved verbatim.
- **Not** XML byte coordinates. `ReaderFragmentSpan` indexes only the decoded
  `value` of a text record; `ElementRef` / `source_pos` name element records.
- **Not** a temporal `StructuralAst`, CST, Component Concept, CTV,
  `SourceBlock`, or `SourceBlockRecord`.
- Provider-bounded: Consultant WordML only; no universal XML or Garant support.
- **No** legal completeness, source authenticity, corpus coverage, or citation
  resolution. `content_hash` is an integrity/version pin, not authenticity. The
  reader never asserts legal or normative authority.
- No clean-view or normalization pass; no XML re-parse. Every walk reads
  substrate records only.

## 3. Record schema

All ids are assigned by the builder in deterministic order. Ids are opaque
tokens; the verifier compares records by substrate coordinates
(`element_ref`, `fragment_ref`), not by id equality across runs.

### 3.1 `ProjectedView`

| field | type | meaning |
|---|---|---|
| `id` | `ViewId` (`vN`) | assigned after view order |
| `kind` | `ReaderViewKind` | closed view vocabulary |
| `element_ref` | `ElementRef` | substrate element anchoring the view |
| `parent_view` | `Option<ViewId>` | nearest valid container on the real parent chain |
| `children` | `Vec<ViewId>` | child views, ordered by `source_pos` (kind tie-break) |
| `segment_refs` | `Vec<SegmentId>` | owned segments in event order (primary only) |
| `reference_refs` | `Vec<ReferenceId>` | owned references in event order |
| `flags.empty` | `bool` | primary: owns no segment; navigation: has no children |

View set (union, deduplicated by `(kind, element_ref)`):

1. every element whose role is `paragraph`, `table`, `row`, `cell` or `note`;
2. every distinct residual anchor owned by a text record
   (`partition_primary_views`), i.e. both `text` and `tail` slots;
3. every distinct residual anchor owned by a `control`, `note_reference`,
   `field`, `unknown` or `foreign` element.

View order is `source_pos` ascending; a `source_pos` shared by a paragraph and
its cell-level residual tie-breaks `paragraph` before `residual`, so the order
is total and deterministic. `parent_view` comes from the real parent chain
(`paragraph`/`residual`/`table`/`note` → nearest `cell`/`note`; `row` → nearest
`table`; `cell` → nearest `row`); navigation content is reached through
`children`, so a container is never a second owner of the same fragment.

### 3.2 `ProjectedSegment`

| field | type | meaning |
|---|---|---|
| `id` | `SegmentId` (`sN`) | assigned in construction order |
| `view` | `ViewId` | owning view |
| `ordinal` | `usize` | position within the view |
| `segment_kind` | `ReaderSegmentKind` | `text` or `derived` |
| `fragment_ref` | `Option<FragmentRef>` | source fragment (text only) |
| `slot` | `Option<TextSlot>` | `text` or `tail` (text only) |
| `span` | `Option<ReaderFragmentSpan>` | whole-fragment span, re-validated (text only) |
| `output_start` / `output_end` | `usize` | position in the view's decoded output |
| `chars` | `usize` | decoded character count |
| `origin` | `SegmentOrigin` | `source_fragment` or `derived:<kind>` |
| `semantic` | `ReaderSemantic` | closed semantic vocabulary |
| `contextual` | `bool` | `semantic != body` |
| `element_ref` | `ElementRef` | owner element |
| `source_pos` | `usize` | owner element pre-order index |
| `text` | `Option<String>` | generated literal for derived segments |

Every text record becomes **exactly one** source-fragment segment with
`span = 0..value.len()` and a mandatory `check_fragment_span` re-validation
(`SpanInvalid` on failure). A documented control (`tab` / `br` / `cr`, with
`br type="page"` → page break) becomes a derived segment carrying the
documented literal, no fragment and no span. Order is reconstructed from the
substrate document-event walk (`text_ref` before children, then each child's
`tail_ref`), never re-parsed from XML.

### 3.3 `ProjectedReference`

| field | type | meaning |
|---|---|---|
| `id` | `ReferenceId` (`rN`) | assigned in construction order |
| `view` | `ViewId` | same ownership view as the element |
| `ordinal` | `usize` | position within the view |
| `reference_type` | `ReaderReferenceType` | closed reference vocabulary |
| `element_ref` | `ElementRef` | reference element |
| `source_pos` | `usize` | element pre-order index |
| `resolved` | `bool` | always `false` in S03 |

`inert_payload` does not exist: the substrate retains all decoded text and has
no exclusion records. References never participate in the primary partition and
are never promoted to a `paragraph` / `residual` view.

### 3.4 `ReaderProjection`

`ReaderProjection { views, segments, references, content_hash }`. The canonical
serialization covers the record stream; a full wire manifest/footer/metrics is
S04.

## 4. Canonical serialization and content seal

Canonical serialization is a hand-rolled writer (`std::fmt::Write`), not a
serde derive: ascending key order, 2-space indent, LF-terminated, stable
escaping, mirroring the `source_package` canonical-JSON discipline. Two calls on
equal records produce identical bytes.

The content seal is a `Sha256` digest over the canonical bytes, module-scoped to
`reader_projection.rs`. This extends the D602 `sha2` allowance to the reader
projection but **does not** extend serde: `serde`/`serde_json` stay scoped to
`source_package`, and the older decoder/lexer/LawRef modules stay
serialization-free (D328). `reseal()` recomputes the seal; `content_hash()`
returns it.

The seal is an integrity/version pin only. **The verifier does not read
`content_hash`.** Tamper resistance comes from independent recomputation of
semantics, not from the hash, so a resealed semantic rewrite still fails.

## 5. Independent verifier semantics

`reader_verifier::verify_projection(projection, records) -> Result<(), Vec<VerifyFinding>>`
recomputes the expected semantics from `records` through `reader_contract`
primitives and compares. The verifier **must not** call
`reader_projection::build_projection` and **must not** trust the projection's
own records, ordering, labels or seal. It re-derives, independently:

- the view forest (view keys, `parent_view`, `children`, `flags.empty`);
- per-view membership and order (independent document-event order);
- segment provenance (`fragment_ref` owner, whole-fragment span re-validated,
  `origin`, `semantic`/`contextual`, derived literal vs `control_derived_kind`);
- coverage (every `tN` exactly once among primary text segments; a fragment in
  the wrong view is `fragment_in_wrong_view`);
- references (membership, type, `resolved == false`).

### 5.1 Closed `VerifyCode`

| code | meaning |
|---|---|
| `view_unexpected` | a view not derivable from the substrate |
| `view_missing` | an expected view absent from the projection |
| `view_parent_mismatch` | `parent_view` differs from the real-chain container |
| `view_children_mismatch` | `children` set or order differs |
| `view_empty_flag_mismatch` | `flags.empty` differs from recomputation |
| `segment_ref_dangling` | `segment_refs` names no segment record |
| `segment_membership_or_order_mismatch` | segment missing, extra or misordered |
| `segment_source_mismatch` | fragment/span/slot/owner provenance differs |
| `segment_owner_mismatch` | segment assigned to the wrong view |
| `derived_not_control` | derived segment whose element is not a documented control |
| `derived_render_mismatch` | derived literal differs from the documented literal |
| `derived_invented_source_span` | derived segment carries a source fragment/span |
| `reference_membership_mismatch` | reference missing, extra or in the wrong view |
| `reference_resolved` | a reference is marked resolved |
| `duplicate_fragment_reference` | a `tN` referenced more than once |
| `dangling_fragment_reference` | a reference names no substrate text record |
| `missing_fragment_reference` | a substrate text record is not referenced |
| `fragment_in_wrong_view` | a fragment is owned by a view other than its owner |

A projection that loses content, reassigns ownership, promotes a derived control
to a source segment, or permutes segment order fails with the matching code even
after `reseal()`.

## 6. Slice boundary S03 / S04

S03 delivered the projection and its independent verifier. S04 (M212-c25p2o/S04)
keeps the authoritative sketch scope — audited diverse fixtures, a root-bound
reader transfer gate with typed refusal, unsupported-case accounting, and the
resealed semantic-tamper battery — and deliberately does **not** expand into the
full reader wire (D637).

| Surface | Disposition |
|---|---|
| view forest, ordered segments, references; canonical record-stream bytes; content seal; `reseal()` | delivered (S03) |
| independent `reader_verifier` with the §5.1 closed `VerifyCode` (D634) | delivered (S03) |
| pinned mixed fixture battery + resealed-tamper battery | delivered (S03) |
| 12 audited frozen self-authored diverse fixtures (sha256-pinned) | delivered (S04) — `prd/architecture/reader-fixture-manifest.md` |
| root-bound transfer gate + typed refusal + unsupported accounting | delivered (S04) — `prd/architecture/reader-transfer-gate.md` |
| diverse independent-recomputation battery + diverse resealed tamper battery | S04 T03/T04 |
| full wire manifest/footer/metrics | remaining (out of S04 scope, D637) |
| read-back/exporter; Hold/TextOnly; navigation links; `source_completion` | remaining (out of S04 scope, D637) |

Out of scope for S03/S04: clean-view/normalization, XML re-parse, tokenization,
CLI, temporal `StructuralAst`/CST/CTV, and any R1000 closure or
legal-completeness claim. R1000 remains active.

## 7. Verification surface (S03)

- Inline unit tests in `reader_projection.rs`: synthetic and fixture view sets,
  parent/children, deterministic order, malformed-substrate fail-closed, and the
  absence of a serialization dependency.
- `crates/ln-decode/tests/reader_projection_contract.rs` (T05): pinned mixed
  fixture (`fixtures/reader/mixed-wordml.xml`, sha256 `d2fc1cd1…`) through
  `source_package::capture`; all view kinds; ordered segment lists per primary
  view against a handwritten oracle; derived controls without span; coverage
  total/duplicate-free/dangling-free; `verify_projection == Ok`; stable
  `content_hash`.
- `crates/ln-decode/tests/reader_projection_tamper.rs` (T05): untampered `Ok`;
  then loss, cross-view ownership swap, derived promotion, and order permutation
  each `reseal()`ed; each yields `Err` with the expected `VerifyCode` and a
  changed `content_hash`.

The scratch prototypes (`tmp/pageindex/iteration14`, `authoritative: false`) are
a characterization source only, never an oracle. Their `exclusion` /
`inert_payload` / `locator` / component-envelope concepts are rejected by S02
and are not ported.
