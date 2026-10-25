# Intermediate-source document-structure and navigation contract

**Status:** `[bounded]`
**Owning slice:** M223-d2q075 / S06 — design pin for
`crates/ln-decode/src/reader_navigation.rs` (`reader_navigation`, T02/T03); tests
`crates/ln-decode/tests/reader_navigation.rs`; counts-only census binary
`crates/ln-decode/src/bin/reader-nav.rs` (T04); census harness
`scripts/m223_s06_navigation_census.py` + `scripts/test_m223_s06_navigation_census.py`
(T04); slice battery `scripts/test_m223_s06_contract.py` (T05)
**Upstream wire contracts (frozen, `[bounded]`):**
`prd/architecture/source-jsonl-contract.md`,
`prd/architecture/reader-view-contract.md`,
`prd/architecture/reader-projection-contract.md`,
`prd/architecture/cleaned-projection-contract.md`,
`prd/architecture/npa-analysis-jsonl-contract.md`
**Upstream acceptance contract:** `prd/architecture/intermediate-source-acceptance-contract.md`
(§4 reading order versus record order, §5 composite provenance, §7 consumers
without XML reparsing, §8 whole-corpus acceptance boundary, §10 non-claims)
**Upstream slice contracts:** `prd/architecture/intermediate-source-reading-order-contract.md`
(S04 `reader_reading_order` / `reader_composite`),
`prd/architecture/intermediate-source-clean-view-contract.md` (S05
`reader_clean_view` / `reader_clean_profile/v1`), and
`crates/ln-decode/src/reader_projection.rs` (frozen reader projection producer)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0029 (requisites-anchored member
assembly — anchor boundary), D631 (S02 reader coordinate base), D633 (S03 reader
content seal), D634 (independent verifier recomputes from the substrate),
D639/D640 (cleaned JSONL envelope and non-cyclic seals), D733 (S04 reading-order
and composite-coordinate design pin), D734/D735 (S05 clean-view design pin and
its R1000 supporting-only reconciliation), **D736 (this design pin: document
structure and navigation model, additive-only)**, D602/D328 (serde stays
module-scoped to `source_package`)
**Lifecycle ceiling:** this is a bounded design pin plus a read-only navigation
index over already-verified decoded source. It is **not** an R1000 closure
artifact, not a CST/AST, not a temporal `StructuralAst`, not physical pagination,
and not expert legal gold. It closes no requirement. R1000 stays
active/unclosed.

## 1. Purpose and non-claims

### 1.1 Purpose

S03 delivered the frozen reader projection (view forest with `parent_view` and
ordered `children`, ordered source-fragment and derived segments, unresolved
reference records, source positions) and its independent verifier. S04 delivered
`reader_reading_order` (per-view reading order re-derived from the substrate
event walk) and `reader_composite` (composite coordinates). S05 delivered the
filtered clean view (`reader_clean_view` / `reader_clean_profile/v1`).

Acceptance contract §7 assigns the **navigation** consumer a projection-only
surface:

> The three consumers — **navigation**, the **tokenizer**, and **graph
> projection** — read the materialized JSONL layers only. They must not re-open
> the source XML to recover structure, reading order, provenance, or identity.
>
> | Navigation (S06) | reader projection views/segments/references + source positions | re-walk XML for parent/subtree/neighbour structure |

S06 delivers that navigation surface. The concrete surface this document fixes:

- **`reader_navigation`** (T02): `NodeAddress` (`View` | `Segment` | `Reference`
  — three non-overlapping id spaces), `NavNodeKind`, `NavNodeBody` (the
  `View`/`Segment`/`Reference` body forms), `NavNode`, `NavLinkKind`
  (`Contains` | `Owns` | `ResolvesTo` | `Precedes`), `NavLink`, and
  `NavigationIndex { nodes_by_address, source_order, links, element_index,
  fragment_index }` built by
  `build_navigation(&ReaderProjection, &ReadingOrderIndex, &[Record])`.
- Structure and path: `parent` / `children` (from `parent_view`), `path_to_root`
  (root-first, bounded visited-set), `siblings`.
- Neighbours: `Precedes` in source order, reading-order `next` / `prev` from the
  S04 `ReadingOrderIndex`.
- Subtree text: `subtree_text(&ViewId, &CleanView) -> SubtreeText { primary,
  service }` aggregated over the descendant **primary** views in reading order
  through the S05 `CleanView`.
- References: a note / endnote reference resolves to **exactly one** note view
  (`NavLinkKind::ResolvesTo`) or carries **exactly one** closed
  `NavResolveReason` — never an invented link.
- Typed fail-closed `NavErrorKind` and closed `NavResolveReason`.

### 1.2 Non-claims

- **Not** an R1000 closure artifact. It is one bounded navigation index feeding
  the wider R1000 program; closure is owned by M223 as a whole (S07 full run),
  not by S06.
- **Not** semantic or legal. Structure, neighbours, and reference resolution
  assert *document structure*, never legal authority, legal completeness, or
  normative citation resolution.
- **Not** temporal. No `StructuralAst`, no time/edition/commencement
  interpretation; navigation is a spatial structure over one decoded document.
- **Not** physical pagination. A derived `page_break` stays a derived separator
  (S05 `service`); it is never a page boundary, never a page number, and never
  an input to `precedes` / `next` / `prev`. No page model exists in this
  contract.
- **Not** authenticity. Any `content_hash` / sha256 pin is an integrity/version
  pin; a party controlling the bytes can recompute it.
- **Not** an XML re-parse. Every walk reads the frozen reader projection, the
  S04 `ReadingOrderIndex`, the S05 `CleanView`, and substrate `Record`s only.
- **Not** whole-corpus materialization. S06 defines and proves the surface on
  tracked fixtures and a bounded seeded real-corpus census; whole-corpus
  materialization of navigation over all accepted documents is S05–S07 evidence,
  not an S06 closure.
- **Not** a clean view and **not** a rule profile. The clean view and
  `reader_clean_profile/v1` are owned by S05 and are **consumed** here read-only;
  S06 does not re-open, extend, or re-describe them.
- Provider-bounded to Consultant WordML (`reader_wordml_profile/v1`).
- Read-only: the navigation index never mutates, reseals, or re-bases the
  projection, the reading-order index, or the clean view.

## 2. Navigation model

### 2.1 Three non-overlapping address spaces

`NodeAddress` has exactly three variants, each an opaque id space that never
collides with the others:

```
NodeAddress::View(ViewId)           // vN  — a reader-projection view
NodeAddress::Segment(SegmentId)     // sN  — a projected segment
NodeAddress::Reference(ReferenceId) // rN  — a projected reference
```

The three spaces are disjoint by construction: a `vN` is never a `sN` or an
`rN`. Ids are the projection's opaque tokens; the index compares nodes by
substrate coordinates (`element_ref`, `fragment_ref`), never by cross-run id
equality. A `NodeAddress` that names an absent record is refused with
`NavErrorKind::MissingAnchor*`, never defaulted.

### 2.2 Nodes

`NavNode` is the index entry for one address:

```
NavNode {
    address: NodeAddress,
    kind: NavNodeKind,          // View | Segment | Reference
    body: NavNodeBody,          // the variant-specific payload
    source_pos: usize,          // owner element pre-order index (ordering fact)
}
```

`NavNodeKind` is the closed three-value kind (`View`, `Segment`, `Reference`)
and mirrors the address variant.

`NavNodeBody` carries the variant-specific, read-only projection data:

- **`View` form** — `{ view_kind: ReaderViewKind, element_ref: ElementRef,
  parent_view: Option<ViewId>, primary: bool }`. `primary` distinguishes a
  primary view (owns text segments) from a navigation view (carries no text).
- **`Segment` form** — `{ view: ViewId, segment_kind: ReaderSegmentKind,
  origin: SegmentOrigin, fragment_ref: Option<FragmentRef>,
  slot: Option<TextSlot>, span: Option<ReaderFragmentSpan>,
  semantic: ReaderSemantic, element_ref: ElementRef }`. A derived segment
  carries no `fragment_ref` and no span; a consumer must not invent one
  (acceptance contract §5).
- **`Reference` form** — `{ view: ViewId, reference_type: ReaderReferenceType,
  element_ref: ElementRef }`. References are always unresolved in the frozen
  projection (`resolved == false`); S06 adds **no** resolution flag to the
  projection — resolution lives only as a `ResolvesTo` link plus a
  `NavResolveReason` inside the index.

### 2.3 Links

`NavLink` is a directed, typed edge between two addresses:

```
NavLink { from: NodeAddress, to: NodeAddress, kind: NavLinkKind }
```

`NavLinkKind` is closed:

| kind | from → to | meaning |
|---|---|---|
| `Contains` | View → View | structural parent → child, from `parent_view` / `children` |
| `Owns` | View → Segment, View → Reference | view ownership of its segments / references |
| `ResolvesTo` | Reference → View | a resolvable reference to exactly one note view |
| `Precedes` | Node → Node | **source order** successor among siblings in the same parent |

`Contains`, `Owns`, and `Precedes` are built in T02; `ResolvesTo` is added in
T03 together with the closed `NavResolveReason`.

### 2.4 `NavigationIndex`

`NavigationIndex` is the read-only product of `build_navigation`:

```
NavigationIndex {
    nodes_by_address: BTreeMap<NodeAddress, NavNode>,
    source_order:     Vec<NodeAddress>,          // document pre-order (source_pos)
    links:            Vec<NavLink>,              // Contains / Owns / Precedes / ResolvesTo
    element_index:    BTreeMap<ElementRef, Vec<NodeAddress>>,
    fragment_index:   BTreeMap<FragmentRef, Vec<NodeAddress>>,
    resolve_reasons:  BTreeMap<ReferenceId, NavResolveReason>, // closed, one per unresolved ref
}
```

`source_order` is the **document pre-order** (owner `source_pos`), the ordering
fact used for `precedes`. It is distinct from reading order (§4).

Public accessors:

```
build_navigation(&ReaderProjection, &ReadingOrderIndex, &[Record])
    -> Result<NavigationIndex, Vec<NavError>>
resolve(&NodeAddress)                 -> Result<&NavNode, NavError>
children(&ViewId)                     -> &[ViewId]
parent(&ViewId)                       -> Option<ViewId>
path_to_root(&ViewId)                 -> Result<Vec<ViewId>, NavError>  // root-first
siblings(&ViewId)                     -> &[ViewId]
neighbours(&ViewId)                   -> Neighbours { prev, next }       // reading order
owning_view(&NodeAddress)             -> ViewId
anchors_of_element(&ElementRef)       -> &[NodeAddress]
anchors_of_fragment(&FragmentRef)     -> &[NodeAddress]
resolve_reason(&ReferenceId)          -> Option<NavResolveReason>
subtree_text(&ViewId, &CleanView)     -> Result<SubtreeText, NavError>
```

`build_navigation` is `serde`-free and `std`-only. It **does not** call
`reader_projection::build_projection`, does not re-parse XML, and does not trust
the projection's own ordering, labels, or seal. It re-derives structure from the
projection's `parent_view` / `children` records and the substrate, and takes
reading order from the S04 `ReadingOrderIndex` (never from the projection's
`ordinal`).

Closed failure kinds — `NavErrorKind`:

| kind | meaning |
|---|---|
| `DuplicateNodeId` | two records claim the same address id space token |
| `MissingAnchorElement` | an address or link names no substrate element |
| `MissingAnchorFragment` | an address or link names no substrate text fragment |
| `MissingAnchorView` | a link or accessor names no view in the projection |
| `MissingAnchorSegment` | a link or accessor names no segment record |
| `MissingAnchorReference` | a link or accessor names no reference record |
| `ParentCycle` | `parent_view` / `children` form a cycle, so `path_to_root` is unbounded |
| `UnreadableSubstrate` | a substrate record is malformed or unreadable |

Every failure is fail-closed: a partial or clamped index is never returned. The
`NavError.detail` never embeds raw decoded text (it names coordinates only).

## 3. Structure and path

### 3.1 Parent and children

`parent(&ViewId)` and `children(&ViewId)` are read from the frozen projection's
`parent_view` and ordered `children`. The projection already fixes that
`parent_view` is the nearest valid container on the real parent chain and that
`children` is ordered by `source_pos` (kind tie-break); S06 does not re-derive
the forest from XML and does not re-parent. Navigation content is reached
through `children`, so a container is never a second owner of the same fragment
(reader-projection contract §3.1).

### 3.2 `path_to_root` (root-first, bounded)

`path_to_root(&ViewId)` returns the ancestor chain **root-first** — the outermost
view first, the queried view last — by walking `parent_view` to the root. The
walk is bounded by a **visited-set**: if a view is revisited, the projection has
a cycle and the call fails closed with `NavErrorKind::ParentCycle`. The bound
guarantees termination on any input, including a hostile cyclic `parent_view`.

### 3.3 Siblings

`siblings(&ViewId)` returns the other children of the same `parent_view`, in the
parent's `children` order. A root view (no parent) has no siblings. Siblings are
**structural** (shared parent), not reading-order and not `precedes` order; the
two are related but distinct surfaces (§4).

## 4. Neighbours

Two distinct neighbour relations are exposed, and the contract fixes their
sources:

1. **Source-order `precedes`** — `NavLinkKind::Precedes` links a node to its
   source-order successor among the siblings in the same parent, using
   `source_order` (owner `source_pos`). `precedes` answers "which node comes next
   in the document", not "which text is read next".
2. **Reading-order `next` / `prev`** — `neighbours(&ViewId)` returns the previous
   and next **primary** view in reading order, taken from the S04
   `ReadingOrderIndex::reading_order` (the substrate event walk). Reading order is
   reconstructed from the event walk and **never** from `semantic`, from
   `source_pos` alone, or from record order (acceptance contract §4; S04
   contract §2.3).

The two relations must be distinguishable in tests: a tail fragment whose
capture owner differs from its semantic owner, or several shared `Body`
fragments, can make source order and reading order diverge. `neighbours` is
defined over primary views only; a navigation view is refused with
`NavErrorKind::MissingAnchorView` (or is simply not in the reading order) rather
than being silently included.

## 5. Subtree text

`subtree_text(&ViewId, &CleanView) -> SubtreeText { primary, service }` returns
the text of the view's **subtree** (the view and all descendant views) in
**reading order**, split into two channels:

- `primary` — the concatenation of the S05 `CleanView` `Primary` units over the
  subtree's primary views, in reading order;
- `service` — the concatenation of the S05 `CleanView` `Service` units over the
  subtree's primary views, in reading order.

Load-bearing rules:

1. **Text comes only from the S05 `CleanView`.** The navigation index stores no
   text of its own; navigation views carry no text (`primary == false`), and a
   `NavNodeBody::View` never carries a text field. Subtree text is assembled by
   asking the `CleanView` for the ordered units of each descendant primary view.
2. **Reading order governs the assembly.** Descendant primary views are visited
   in the S04 reading order, and within a view the `CleanView` units are already
   in reading order.
3. **No XML re-parse and no invented fragments.** `subtree_text` never re-parses
   XML, never invents a `fragment_ref` / span for a derived unit, and never
   re-bases S05 provenance. A derived separator (including a `page_break`)
   contributes its `service` literal and is never treated as a page boundary.
4. **Empty subtrees are empty, not defaulted.** A subtree with no primary text
   yields empty `primary` and `service`, never a placeholder.

## 6. References and resolution

### 6.1 Resolution is derived, never invented

The frozen projection records references with `resolved == false` and no
resolution target. S06 derives resolution inside the index only:

- A `NoteReference` / `EndnoteReference` resolves by matching its **substrate
  `w:id` attribute** to the note definition element with the same `w:id`, and
  then to the note view whose `element_ref` is that definition.
- **Success requires exactly one** matching note definition **and exactly one**
  note view for that definition. On success the index records a
  `NavLinkKind::ResolvesTo` link from the reference address to the note view
  address, and `resolve_reason` returns `None`.
- **Failure is closed and explicit.** When resolution is not unique or not
  possible, the index records **no** `ResolvesTo` link and stores exactly one
  `NavResolveReason` for the reference. The reference is never silently dropped,
  never guessed, and never linked to a best-effort target.

### 6.2 Closed `NavResolveReason`

| reason | meaning |
|---|---|
| `NoMatchingNoteDefinition` | no note definition element carries the reference's `w:id` |
| `MultipleMatchingNoteDefinitions` | more than one note definition carries the same `w:id` |
| `NotAResolvableReference` | the reference type is not a note / endnote reference |
| `MissingAnchorElement` | the reference or its definition names no substrate element |
| `MissingNoteView` | a unique definition exists but no note view anchors it |

`resolve_reason(&ReferenceId)` returns `Some(reason)` exactly for references with
no `ResolvesTo` link and `None` exactly for resolved references. Every reference
address in `nodes_by_address` has exactly one of: a `ResolvesTo` link, or one
`NavResolveReason`. There is no third state.

## 7. Consumers without XML re-parse

Navigation reads only the materialized JSONL layers plus the S04 reading-order
index and the S05 clean view. It must not re-open the source XML to recover
structure, reading order, provenance, or identity (acceptance contract §7):

| Navigation reads | Navigation must not |
|---|---|
| reader projection `parent_view` / `children` (structure) | re-walk XML for parent / subtree structure |
| reader projection segments / references + source positions | re-walk XML for neighbour structure |
| S04 `ReadingOrderIndex` (reading order) | derive reading order from `semantic`, `source_pos`, or record order |
| S05 `CleanView` (text channels) | re-parse XML for text; invent a fragment / span for a derived control |
| substrate `w:id` attributes (reference resolution) | re-parse XML for reference endpoints |

If navigation needs a fact that is absent from the JSONL, the fix is to extend
the producer under a tracked contract, never to add a hidden XML pass.

## 8. Additive-only over the five frozen wire contracts

This design is **additive-only**. The five upstream wire contracts below are
frozen as of the S06 design. The sha256 of each tracked file **at design time**
is pinned in the machine-readable inventory block. **No upstream contract is
changed silently.** Any extension to one of them is a recorded revision or a
recorded decision — never a quiet edit. T05's slice battery recomputes these
hashes and fails on drift; a drift is an explicit re-pin, not a silent update.

Frozen upstream wire-contract inventory (design-time sha256):

| Contract | sha256 |
|---|---|
| `prd/architecture/source-jsonl-contract.md` | `2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6` |
| `prd/architecture/reader-view-contract.md` | `80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d` |
| `prd/architecture/reader-projection-contract.md` | `95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e` |
| `prd/architecture/cleaned-projection-contract.md` | `7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e` |
| `prd/architecture/npa-analysis-jsonl-contract.md` | `a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb` |

Machine-readable form (T05 parses this block; keep one entry per line):

```
<!-- frozen-contract-inventory:begin -->
sha256:2ddfe7da95e3adc0c341965f709001e2cdd67ccca3b22b7970ee06ad1dc0d9f6 prd/architecture/source-jsonl-contract.md
sha256:80a846fffedace7d78ef0b80faf14085eb05037a4aa7baca92de415f1b7d1b7d prd/architecture/reader-view-contract.md
sha256:95d0f127f8b1cf72dc2dcaec97271c408ca0543cb8487f7839af57553c6eec3e prd/architecture/reader-projection-contract.md
sha256:7d167e434c4640b539406ddd5de39286d30b1e2efeb43bfdaa603b76b0313c4e prd/architecture/cleaned-projection-contract.md
sha256:a3f51100679613a7f76c84a7282b50a5e31dc43abc4f652e221fd745136f00cb prd/architecture/npa-analysis-jsonl-contract.md
<!-- frozen-contract-inventory:end -->
```

### 8.1 Immutability of the six §2 files and the frozen JSONL

The **six tracked §2 files** named by the acceptance contract (the accepted base
revision) are **not** modified by S06. Their design-time sha256 pins:

| File | sha256 |
|---|---|
| `crates/ln-decode/src/reader_projection.rs` | `0d4e9f40d8d85da1b55496cc0f843aa7b837e1ffcdae1b40b9dfd51e0f997246` |
| `crates/ln-decode/src/reader_verifier.rs` | `3b9f3b267f57892216038fd19ff692d051c3868aa41140b59a9fe04314498c5f` |
| `crates/ln-decode/src/npa_analysis_wire.rs` | `80cbe03e5425cd4981242043dd9a822f9546994b2309e83a66d8b38f03663f88` |
| `crates/ln-decode/tests/reader_tail_semantics.rs` | `eba6187abcd813dfd9b71010d489fd645a2ae5a9bb2f8f2bcb29e3bd5f423c2c` |
| `crates/ln-decode/tests/npa_analysis_strict_admission.rs` | `6be0a721be429ea2f447aec80426e44f2a9b741416e693a7ce3797513c768e43` |
| `crates/ln-decode/tests/m222_f07_audit.rs` | `019136892dfa5acbe4ec028e42eb8ec552c2c48fb0fe0c1f74cdbbebd006be64` |

The frozen `prd/architecture/*.jsonl` tracked artifacts are **not** modified:

| File | sha256 |
|---|---|
| `prd/architecture/architecture_items.jsonl` | `3ef86ce1e2c8969d4f919b3cae31621acf0fb3d6d49334bbc05d89ab9c85d966` |
| `prd/architecture/architecture_edges.jsonl` | `ce53dc0e1e4d2851aac538827ced9a9e007e4af3ce54d2b98b780b7739616818` |

Machine-readable form (T05 parses this block; keep one entry per line):

```
<!-- immutability-pins:begin -->
sha256:0d4e9f40d8d85da1b55496cc0f843aa7b837e1ffcdae1b40b9dfd51e0f997246 crates/ln-decode/src/reader_projection.rs
sha256:3b9f3b267f57892216038fd19ff692d051c3868aa41140b59a9fe04314498c5f crates/ln-decode/src/reader_verifier.rs
sha256:80cbe03e5425cd4981242043dd9a822f9546994b2309e83a66d8b38f03663f88 crates/ln-decode/src/npa_analysis_wire.rs
sha256:eba6187abcd813dfd9b71010d489fd645a2ae5a9bb2f8f2bcb29e3bd5f423c2c crates/ln-decode/tests/reader_tail_semantics.rs
sha256:6be0a721be429ea2f447aec80426e44f2a9b741416e693a7ce3797513c768e43 crates/ln-decode/tests/npa_analysis_strict_admission.rs
sha256:019136892dfa5acbe4ec028e42eb8ec552c2c48fb0fe0c1f74cdbbebd006be64 crates/ln-decode/tests/m222_f07_audit.rs
sha256:3ef86ce1e2c8969d4f919b3cae31621acf0fb3d6d49334bbc05d89ab9c85d966 prd/architecture/architecture_items.jsonl
sha256:ce53dc0e1e4d2851aac538827ced9a9e007e4af3ce54d2b98b780b7739616818 prd/architecture/architecture_edges.jsonl
<!-- immutability-pins:end -->
```

S06 adds new files (`reader_navigation.rs`, its test, the `reader-nav` binary,
the census scripts, the slice battery, the evidence artifacts) and registers one
module (`pub mod reader_navigation;`) plus one `[[bin]]` in
`crates/ln-decode/Cargo.toml` — additive edits only.

### 8.2 Machine-readable navigation model block

T05 parses this block and fails on drift between it and the `reader_navigation`
source declarations. Exactly one line per model element:

```
<!-- navigation-model:begin -->
address:View id_space:v
address:Segment id_space:s
address:Reference id_space:r
node_kind:View
node_kind:Segment
node_kind:Reference
link_kind:Contains
link_kind:Owns
link_kind:ResolvesTo
link_kind:Precedes
resolve_reason:NoMatchingNoteDefinition
resolve_reason:MultipleMatchingNoteDefinitions
resolve_reason:NotAResolvableReference
resolve_reason:MissingAnchorElement
resolve_reason:MissingNoteView
<!-- navigation-model:end -->
```

## 9. S03 reconciliation

S06 reconciles with the S03 baseline
(`prd/migration/rust-evidence/m223-s03-baseline-run.json`, schema
`m223-s03-baseline-run/v1`):

| fact | value |
|---|---|
| corpus entries | 43785 |
| accepted | 43785 |
| refused | 0 |
| incomplete | 0 |
| R1000 status | `active/unclosed` |

Navigation is defined and exercised **per accepted document** on tracked
fixtures and a bounded seeded real-corpus census. Whole-corpus materialization of
navigation over all 43 785 accepted documents is **S05–S07 evidence**, not S06
closure. S06 must not restate S03's integrity/count result as a semantic or legal
claim: the S03 run is an acceptance/integrity baseline, not a semantic oracle
(acceptance contract §8.2). `s03_baseline_reconciled` in the S06 evidence
artifact records the four numbers and `r1000_status` above, and nothing more.

## 10. Slice boundaries S05 / S06 and S06 / S07

| Surface | Disposition |
|---|---|
| versioned rule profile + clean-view model with preserved provenance + typed errors | S05 (T01/T02) — `reader_clean_view`; **consumed read-only by S06** |
| navigation model (address spaces, nodes, links, index), structure / path / siblings, neighbours, subtree text, reference resolution, typed errors | S06 (T01–T03) — `reader_navigation` |
| bounded seeded real-corpus navigation census (counts only, redacted) | S06 (T04) |
| design pin + additive-only + S03 reconciliation + slice battery | S06 (T01/T05) |
| whole-corpus materialization of navigation over all 43 785 accepted documents | S05–S07 |
| tokenizer + graph projection (document identity keyed, no XML re-parse) | S07 |
| R1000 closure, legal completeness, source authenticity, normative citation resolution, normalization, physical pagination, temporal structure | not S06; remains out of scope |

S06 consumes the S05 clean view for its declared consumer and does **not** re-open
the S05 rule profile. Out of scope for S06: normalization, XML re-parse,
tokenization, graph projection, CLI beyond the counts-only census binary,
temporal `StructuralAst`/CST/CTV, physical pagination, cross-document links, and
any R1000 closure. R1000 stays active.

## 11. Threat surface

- **Untrusted projection / order / clean-view input → fail-closed.**
  `build_navigation` validates address existence, id-space uniqueness, anchor
  existence, parent/child consistency, and reading-order membership; every
  violation is a typed `NavErrorKind`, never a partial or clamped index.
  `path_to_root` is bounded by a visited-set, so a hostile cyclic `parent_view`
  cannot loop; it fails with `ParentCycle`.
- **No invented link.** Reference resolution never guesses: a non-unique or
  non-existent target yields a closed `NavResolveReason`, never a `ResolvesTo`
  link to a best-effort target.
- **No pagination surface.** A derived `page_break` stays an S05 `service`
  separator; the index exposes no page number, page boundary, or page model, and
  no pagination field appears in the census artifact.
- **Decoded legal text is not a secret.** The decoded text is provider-bounded
  Consultant WordML already admitted by the reader projection; it is not
  classified. Redaction applies to **evidence artifacts**, not to the in-memory
  model: `m223-s06-navigation-census.json` and
  `m223-s06-navigation-battery.json` carry only paths, counters, and hashes — no
  raw decoded text. Decoded text is permitted only inside Rust tests over the
  tracked fixtures.
- **Inputs are admission-verified.** The index consumes an already-verified
  `ReaderProjection`, the S04 `ReadingOrderIndex`, the S05 `CleanView`, and
  substrate `Record`s; it does not re-parse XML, does not re-open the corpus, and
  does not relax S03 admission.
- **No rebasing / silent loss.** Provenance is copied, not re-based; a reference
  with no resolution is retained with an explicit closed reason, not dropped.

## 12. Requirement impact

- **R1000 — supporting-only. Do not close.** S06 delivers a bounded navigation
  index that supports the wider R1000 program (S05–S07 materialize it per accepted
  document); it is not an R1000 closure artifact and must not be reported as one.
  R1000 stays `active/unclosed` (acceptance contract §10; precedent: S03/S04/S05,
  D735).
- No other R-ID is bound or re-labelled by S06. S06 adds no new requirement; it
  advances no requirement to `validated`.

## 13. Verification surface

- `crates/ln-decode/src/reader_navigation.rs` (T02) inline unit tests: structure
  on the pinned mixed fixture and a synthetic forest; `path_to_root` root-first
  and the bounded cycle refusal; siblings / `precedes` / reading-order `next` /
  `prev`; typed refusals; the absence of a `serde` dependency.
- `crates/ln-decode/tests/reader_navigation.rs` (T03): handwritten oracles over
  the tracked fixtures `mixed-wordml.xml` (structure, path, siblings, `precedes`,
  reading-order `next` / `prev`, `subtree_text`, `footnoteReference` `w:id=1` →
  `ResolvesTo`, `w:id=2` → a closed reason), `navigation-demo.xml` (table, nested
  note, and a `page_break` that is **not** a page boundary — the negative on the
  pagination surface), `notes-nested.xml` (note-in-cell and nested notes);
  wire read-back parity (read-back navigation equals the direct build); and
  negatives (cyclic `path_to_root`, missing anchor typed error, unresolvable
  reference → reason).
- `crates/ln-decode/src/bin/reader-nav.rs` + `scripts/m223_s06_navigation_census.py`
  (T04): a counts-only, redacted census over a deterministic seeded sample of the
  S02 manifest (`prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl`),
  emitting `prd/migration/rust-evidence/m223-s06-navigation-census.json`
  (schema `m223-s06-navigation-census/v1`) with counts, per-kind tallies,
  resolved / unresolved-by-reason tallies, max depth / path length, subtree
  character counts, and hash bindings — no raw text. Invariants:
  `resolved + unresolved == references`, `path_to_root` is terminal, no cycles,
  no pagination fields. A missing corpus is a fail-closed harness error.
- `scripts/test_m223_s06_contract.py` (T05): (a) this document exists and carries
  the required sections/markers ("Navigation model", "Structure and path",
  "Neighbours", "Subtree text", "References and resolution", "Consumers without
  XML re-parse", "Additive-only", "S03 reconciliation", "Slice boundaries",
  "Threat surface", "Requirement impact", "Verification surface",
  `frozen-contract-inventory` block, `navigation-model` block,
  `immutability-pins` block, `active/unclosed`, `43785`, `reader_navigation`);
  (b) the five pinned sha256 values match the tracked files **exactly** (drift →
  explicit re-pin, never silent); (c) the S03 baseline is reconciled
  (entries = accepted = 43785, refused = 0, incomplete = 0, R1000
  active/unclosed, status `complete`); (d) the census artifact has schema v1, is
  redacted, satisfies `resolved + unresolved == references`, and its pinned
  contract hash matches; (e) immutability: the six §2 files and the frozen
  `prd/architecture/*.jsonl` match the pinned sha256; (f) it emits
  `prd/migration/rust-evidence/m223-s06-navigation-battery.json`
  (schema `m223-s06-navigation-battery/v1`) with counters/hashes and
  `non_claims`, carrying only paths, counters, and hashes.
- Cleanliness battery: `cargo test -p ln-decode --offline --lib
  reader_navigation`; `cargo test -p ln-decode --offline --test
  reader_navigation`; `cargo test -p ln-decode --offline`; `cargo fmt --all
  --check`; `cargo check --workspace --offline`; `cargo clippy --workspace
  --all-targets --offline -- -D warnings`; `uv run python
  scripts/verify-adr-conformance.py`.

## 14. References

- `prd/architecture/intermediate-source-acceptance-contract.md` §4 (reading
  order versus record order), §5 (composite provenance), §7 (consumers without
  XML reparsing), §8 (whole-corpus acceptance boundary), §10 (non-claims).
- `prd/architecture/intermediate-source-reading-order-contract.md` (S04
  `reader_reading_order` reading order and `reader_composite` coordinates).
- `prd/architecture/intermediate-source-clean-view-contract.md` (S05
  `reader_clean_view` / `reader_clean_profile/v1`; §9 hands S06 the clean view).
- `prd/architecture/reader-projection-contract.md` §3.1 (`ProjectedView`), §3.2
  (`ProjectedSegment`), §3.3 (`ProjectedReference`), §5 (independent verifier
  semantics).
- `prd/architecture/reader-view-contract.md` §4 (coordinate base), §5
  (ownership), §6 (coverage partition).
- `crates/ln-decode/src/reader_contract.rs` (`ReaderViewKind`,
  `ReaderSegmentKind`, `ReaderSemantic`, `ReaderReferenceType`,
  `ReaderFragmentSpan`).
- `prd/migration/rust-evidence/m223-s03-baseline-run.json` (S03 baseline).
- `prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl` (S02 manifest
  consumed by the T04 census).
