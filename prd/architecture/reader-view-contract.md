# Reader-view contract over the frozen source package

**Status:** `[bounded]`
**Owning slice:** M212-c25p2o / S02 — `crates/ln-decode/src/reader_contract.rs`
(public module `ln_decode::reader_contract`, planned)
**Upstream substrate:** `prd/architecture/source-jsonl-contract.md` (frozen,
`[bounded]`) — the decoded `source_package` model
**Authority:** ADR-0013 (universal multi-source parser architecture),
ADR-0015 (hexagonal verification architecture), ADR-0029 (requisites-anchored
member assembly — anchor boundary), D631 (S02 reader coordinate base),
D602/D328 (serde boundary), D603 (anchor `LocalSpan` precedent)
**Lifecycle ceiling:** this is a bounded reader-navigation contract over already
verified decoded source. It is **not** an R1000 closure artifact, not a CST/AST,
not a temporal `StructuralAst`, and not expert legal gold. It closes no
requirement. R1000 stays active; this slice is a contract, not a closure.

## 1. Purpose

This contract fixes the first reader layer above the frozen decoded substrate. It
names which reader **views** exist, how each text fragment is owned by exactly
one primary view, and how source facts are distinguished from generated control
text — all without XML byte coordinates, because the substrate stores none.

The substrate (`source-jsonl-contract.md`) carries element records (`eN`,
pre-order, with `parent`/`child_index`/`clark_tag`/`attrs`/`text_ref`/`tail_ref`)
and text records (`tN`, document order, with `owner`/`slot`/`value`/`chars`/
`bytes`). It explicitly leaves reader/cleaning/literal-run projection out of
scope. This document is the contract for that first reader layer:

- closed **view** vocabulary `[bounded]` (paragraph / residual / table / row /
  cell / note);
- a **coordinate base** built from substrate ids (`FragmentRef`, `ElementRef`,
  `source_pos`) plus a half-open UTF-8 byte span inside a decoded fragment;
- an **ownership** rule that assigns every text record to exactly one primary
  view;
- a **coverage partition** over text records;
- a **control/reference** classification that separates source facts from
  generated controls and unresolved references;
- a pinned provider profile `reader_wordml_profile/v1`.

S02 fixes the vocabulary, the coordinate base with span validation, the
ownership map, the coverage partition and the control/reference classification.
Building the view forest, the segment records, serialization, the independent
verifier, metrics and the tamper battery belong to S03/S04 (§10).

## 2. Non-claims

- Raw decoded text only. This reader applies **no** character normalization. The
  normalization declared in `prd/parser/profiles/consultant_wordml.yaml`
  (nbsp -> space, guillemets -> quote, en-dash -> hyphen) is Phase B clean work
  and is out of scope here. NBSP and whitespace are preserved verbatim.
- Provider-bounded. This is Consultant WordML only. Consultant WordML and Garant
  are different formats; no universal XML or cross-provider support is claimed.
- **Not** ADR-0017 `TextAnchor`, **not** `EvidenceSpan`, **not** the domain
  `SourceSpan` (which is an XML-byte artifact), and **not** the iteration-13
  element-index `locator`. The reader coordinate base is a decoded-fragment
  coordinate base, not an XML byte coordinate base.
- **Not** a temporal `StructuralAst`, CST, Component Concept, CTV,
  `SourceBlock`, or `SourceBlockRecord`. Reader views are decoded-source
  navigation, not temporal semantics.
- ADR-0029 fixes requisites **anchors** for NPA member assembly. This reader
  coordinate base shares the half-open UTF-8 byte span discipline (D603) but is
  a different coordinate system; it defines no requisites anchor and feeds no
  member assembly here.
- No legal completeness, source authenticity, corpus coverage, or citation
  resolution is claimed. `reader_wordml_profile/v1` is a processing pin, not a
  correctness or authority judgment.

## 3. Closed vocabularies

All tokens below are the wire vocabulary **scoped to
`reader_wordml_profile/v1`**. The Rust type names are `Reader*` (`ReaderViewKind`,
`ReaderSegmentKind`, `ReaderDerivedKind`, `ReaderSemantic`,
`ReaderReferenceType`, `ReaderViewKey`, `ReaderFragmentSpan`). The wire token
`paragraph` is the reader view label; it is **not** the §3 temporal-model
«абзац/§» citation label. Unknown tokens fail closed with a typed error; they are
never silently mapped to a default.

### 3.1 `view_kind`

| token | class | carries |
|---|---|---|
| `paragraph` | primary | text-owning; must not carry `children` |
| `residual` | primary | text-owning bucket for material outside a paragraph; must not carry `children` |
| `table` | navigation | structure only; must not carry `segment_refs` |
| `row` | navigation | structure only; must not carry `segment_refs` |
| `cell` | navigation | structure only; must not carry `segment_refs` |
| `note` | navigation | structure only; must not carry `segment_refs` |

primary = {`paragraph`, `residual`}; navigation = {`table`, `row`, `cell`,
`note`}. A primary view is text-bearing; a navigation view references the same
material through its `children`. `residual` is an explicit owner, not an
"unknown" bucket.

### 3.2 `segment_kind`

| token | meaning |
|---|---|
| `text` | source-backed segment; names one fragment |
| `derived` | generated segment from a documented control; no source span |

### 3.3 `origin`

| token | meaning |
|---|---|
| `source_fragment` | the segment names a substrate text fragment |
| `derived:tab` | generated TAB from a documented WordML `w:tab` |
| `derived:line_break` | generated LF from documented WordML `w:br` / `w:cr` |
| `derived:page_break` | generated LF from documented WordML `w:br w:type="page"` |

There is deliberately no separate `pageBreak` element in WordML. A page break is
`w:br` with `w:type="page"`; every other `w:br` (and `w:cr`) is a line break.
A `derived:*` segment carries no fragment reference and no source span (§4).

### 3.4 `semantic`

| token | meaning |
|---|---|
| `body` | body text |
| `whitespace` | retained whitespace |
| `field_code` | field instruction / field character text |
| `revision_insertion` | text under an insertion revision |
| `revision_deletion` | text under a deletion revision |
| `derived_separator` | generated control separator |
| `empty` | empty fragment |

No value asserts normative or legal authority.

### 3.5 `reference_type`

| token | meaning |
|---|---|
| `note_reference` | footnote reference |
| `endnote_reference` | endnote reference |
| `comment_reference` | comment reference |
| `annotation_reference` | annotation reference |
| `field` | field element |
| `unknown_wordml_element` | WordML-namespaced element outside the known vocabulary |
| `foreign_element` | element outside all WordML namespaces |

`inert_payload` is **excluded**. The substrate retains all decoded text and has
no exclusion records, so no payload class is dropped and no `inert_payload`
reference can arise. A reference never inflates the fragment partition (§6); its
`resolved` state is always false.

### 3.6 Controls

Only a namespace-valid, documented control is rendered. An element outside this
documented vocabulary is retained as a reference, never guessed as a control.

| WordML element | `derived` kind | literal |
|---|---|---|
| `tab` | `derived:tab` | `"\t"` |
| `br` | `derived:line_break` | `"\n"` |
| `cr` | `derived:line_break` | `"\n"` |
| `br` with `type="page"` | `derived:page_break` | `"\n"` |

## 4. Coordinate base

| type | definition |
|---|---|
| `FragmentRef` | a substrate text record id, `tN`, in document order |
| `ElementRef` | a substrate element record id, `eN`, in pre-order |
| `source_pos` | index of an element among element records (pre-order) |
| `ReaderViewKey` | `{ kind: ReaderViewKind, element_ref: ElementRef }` |
| `ReaderFragmentSpan` | `{ fragment: FragmentRef, start: usize, end: usize }` |

`ReaderFragmentSpan` is a **half-open UTF-8 byte range `[start, end)` inside the
decoded `value`** of the referenced text record. It mirrors the D603 /
`npa_anchor::check_span` discipline and its `SpanError`:

| condition | `ContractErrorKind` |
|---|---|
| `start >= end` | `EmptyOrInverted` |
| `end > value.len()` | `OutOfBounds` |
| `start` or `end` not a UTF-8 char boundary | `NotCharBoundary` |

A text segment in S02 covers the **whole** fragment: `start = 0`,
`end = value.len()`. The half-open span type leaves room for sub-fragment runs in
a later Phase B without a schema change.

**Explicit non-claim:** this is **not XML byte coordinates**. The substrate
stores no XML byte offsets; a `ReaderFragmentSpan` indexes only decoded text,
and an `ElementRef` / `source_pos` identifies an element record, not a byte
range in the source document.

## 5. Ownership

Each element receives a role from its `clark_tag` (namespace + local name) and
the WordML sets in §7. The primary-view ownership rule is:

1. **Primary paragraph** — if the element has a `paragraph`-role ancestor on the
   real `parent` chain, its primary view is the **nearest** such ancestor:
   `(paragraph, nearest_para)`.
2. **Residual** — otherwise the primary view is a residual anchored by
   `residual_anchor(eid)`: walk up the real `parent` links to the first parent
   whose role is in {`table`, `row`, `cell`, `note`}; the current element becomes
   the anchor: `(residual, anchor)`. If no such parent exists, the outermost
   reachable element is the anchor. A residual can anchor any element.
3. **Tail** — a child's tail is text in the **parent's** content, so
   `tail_view_key(child)` is `(paragraph, parent)` when the parent's role is
   `paragraph`, and otherwise `(residual, residual_anchor(child))`. A tail after
   a paragraph inside a cell therefore stays a cell-level residual rather than
   being absorbed by the paragraph view.
4. **Real-chain container walk** — ancestor lookups walk the substrate `parent`
   links and take the **closest** valid container (no fixed per-kind priority
   list). No XML re-parse is performed.
5. **Unknown / foreign** — ownership is never guessed. An element outside the
   known WordML vocabulary is classified as a **reference**
   (`unknown_wordml_element`, or `foreign_element` for a foreign namespace) and
   is **not** itself a paragraph or residual view. Text inside an unknown/foreign
   subtree still receives its primary owner by the same rule as any other text
   (nearest paragraph ancestor, else residual anchor). Being an owner of nested
   text does not promote the unknown/foreign element to a view.

All walks iterate substrate records; the XML is never parsed again.

## 6. Coverage partition

Every substrate text record (both `text` and `tail` slots) is referenced by
**exactly one** primary view (`paragraph` or `residual`). The partition
invariants are:

- count of primary-view fragment refs equals count of text records;
- every `tN` appears exactly once across primary views (no duplicate, no
  missing, no dangling reference);
- a text record that is not covered, or covered twice, is a contract failure.

Ancestor and navigation views (`table`, `row`, `cell`, `note`) reference the same
material through their `children`; therefore coverage is **not** the sum of the
text of every view. The partition is computed only over primary-view fragment
refs, so a fragment is never counted twice through its enclosing container.

## 7. WordML vocabulary (candidate sets, independently reviewed)

### 7.1 Namespaces

| namespace URI | label |
|---|---|
| `http://schemas.microsoft.com/office/word/2003/wordml` | WordML 2003 |
| `http://schemas.openxmlformats.org/wordprocessingml/2006/main` | WordprocessingML 2006 |
| `http://purl.oclc.org/ooxml/wordprocessingml/main` | OOXML transitional |

An element is a WordML element only when its Clark namespace is one of these
three **and** its local name is in the relevant set below. A foreign-namespaced
`tab` is not a control.

### 7.2 Local-name sets

These sets are the **candidate dictionary** carried from the iteration-14
scratch model (`tmp/pageindex/iteration14`, `authoritative: false`) after
independent review. They are not canonical and are not gold; the Rust module in
T02 restates them as closed consts.

| set | locals |
|---|---|
| note definition (`NOTE_DEF_LOCALS`) | `footnote`, `endnote` |
| note reference (`NOTE_REFERENCE_LOCALS`) | `footnoteReference` -> `note_reference`, `endnoteReference` -> `endnote_reference`, `commentReference` -> `comment_reference`, `annotationRef` -> `annotation_reference` |
| field (`FIELD_LOCALS`) | `fldChar`, `instrText`, `fldSimple` |
| control (`CONTROL_LOCALS`) | `tab`, `br`, `cr` |
| container (`CONTAINER_LOCALS`) | `wordDocument`, `body`, `tblGrid`, `styles` |
| revision | `ins` (insertion), `del` (deletion) |
| known WordML context | the documented WordML local set (paragraph/run/text/table/property/style/header/footer/bookmark/pict/object/drawing locals, etc.) |
| property container | any local ending in `Pr`, plus `tblPrEx` |

Role mapping: `p`->paragraph, `tbl`->table, `tr`->row, `tc`->cell,
`footnote`/`endnote`->note, a control local->control, a note-reference local->
reference, a field local->field, `ins`/`del`->revision, a known WordML local or
property container->context, otherwise unknown; a foreign namespace->foreign.

## 8. Profile pin

| pin | value |
|---|---|
| profile | `reader_wordml_profile/v1` |
| text form | raw decoded text; no char normalization |
| provider | Consultant WordML (provider-bounded; not Garant) |
| coordinate base | `FragmentRef` + half-open UTF-8 byte `ReaderFragmentSpan` inside the decoded value, `ElementRef` + `source_pos` |
| controls | documented WordML `tab`/`br`/`cr` only, including `br type="page"` |
| references | the seven types in §3.5; `resolved` always false |

## 9. Deltas vs iteration 13 / iteration 14

The scratch prototypes (`tmp/pageindex/iteration13`, `iteration14`) are
`authoritative: false`. They are a characterization source and a candidate
dictionary, **not** an oracle and **not** gold. The Rust contract deliberately
departs from them:

| scratch it13 / it14 | Rust `source_package` substrate | reader contract decision |
|---|---|---|
| `exclusion` records, `payload_region`, `inert_payload` | no exclusion records; all decoded text retained | drop exclusion / `inert_payload`; no payload branch is ported as empty |
| element-index `locator`, `source_locator` on fragments/segments | no locator | replace with `ElementRef` + `source_pos` (pre-order index) and `ReaderFragmentSpan`; do not invent a locator list |
| `source_utf8_start`/`end` (it13 stored one fragment per text event) | `tN` is an atomic text/tail slot | text segment is the whole fragment (`0..value.len()`); span type still allows later sub-fragment runs |
| it13 ElementTree parse; it14 walks the parent bundle | records are already canonical (`parent`/`child_index`, element pre-order, text document order) | ownership/tail/ancestor walks use `parent` links only, no XML re-parse |
| `raw_attrs` on element | `attrs` Clark-map | reference detail is read from the Clark `attrs` map; `raw_attrs` is not mapped |
| component envelope, hashes, `source_completeness = UNVERIFIED` | no envelope; substrate already verified | drop envelope / hashes / completeness; S02 is a view/coordinate contract, not a second file format |

## 10. Slice boundary S02 / S03

| S02 (this slice) | S03 / S04 (later) |
|---|---|
| closed vocabularies as Rust enums/structs | build `reader_view` / `reader_segment` / `reader_reference` records |
| `ReaderFragmentSpan` / `ElementRef` / `source_pos` + `check_fragment_span` / `ContractError` | full segment construction: output/source ranges, semantic/contextual |
| ownership map `view_key` (paragraph / residual anchor, tail, nearest container) | full view forest: children order, `parent_view` |
| coverage partition over text records | coverage partition + metrics + serialization + independent verifier + tamper battery |
| control/reference classification dictionaries (closed) | render controls into segments, reference records, `source_completion` |

Out of scope for S02: view/segment/reference **record files**, serialization,
hashing/envelope, independent verifier, clean/normalization, tokenization, CLI.

## 11. Verification surface (S02)

The S02 battery is `crates/ln-decode/tests/reader_view_contract.rs` over the
pinned mixed fixture `crates/ln-decode/tests/fixtures/reader/mixed-wordml.xml`,
read through `source_package::capture`. It asserts:

- non-empty element/text records over a document mixing paragraphs, tail
  residuals, `w:tbl>w:tr>w:tc>w:p`, a footnote definition with a
  `footnoteReference`, `tab`/`br`/`br type="page"` controls, `fldSimple` and
  `instrText`, `ins`/`del` revisions, an unknown WordML element, a foreign
  namespace element carrying text, and verbatim NBSP;
- the coverage partition invariants of §6 (counts equal, each `tN` exactly once,
  no duplicate/missing/dangling);
- per-view ordered fragment lists compared against a handwritten oracle (written
  from the XML, never generated by the code under test);
- controls produce a `derived` kind with no fragment ref and no source span,
  while each text record has a whole-fragment span with a valid
  `check_fragment_span`;
- unknown/foreign elements classify as references and are not primary views,
  while their nested text still gets a primary owner;
- negative cases: inverted / out-of-bounds / non-char-boundary spans and unknown
  wire tokens return typed errors;
- the fixture sha256 pinned in the test.

## 12. Out of scope

Reader/cleaning/literal-run projection beyond this contract; view/segment/
reference record files; JSON serialization; hashing or component envelope;
independent verifier; metrics; tamper battery; character normalization;
tokenization; CLI; any CST/AST/CTV/StructuralAst claim. No full-corpus run is
performed; evidence is fixture-bounded. Source-fact vs generated-control
distinction is proven on the S02 battery, not claimed corpus-wide.
