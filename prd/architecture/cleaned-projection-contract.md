# Cleaned-projection wire contract over the frozen source package

**Status:** `[bounded]`
**Owning slice:** M213-t6p7d0 / S01 — `prd/architecture/cleaned-projection-contract.md`;
consumer `crates/ln-decode/src/cleaned_wire.rs` (planned) and
`crates/ln-decode/tests/cleaned_projection_wire.rs` (planned)
**Upstream substrate:** `prd/architecture/source-jsonl-contract.md` (frozen,
`[bounded]`) — the decoded `source_package` model
**Upstream contract:** `prd/architecture/reader-projection-contract.md` (frozen,
`[bounded]`) — the reader view forest, ordered segments and references
**Authority:** ADR-0013 (universal multi-source parser architecture),
ADR-0015 (hexagonal verification architecture), ADR-0029 (requisites-anchored
member assembly — anchor boundary), D600/D601 (full-text JSONL and format
versioning), D633 (serde-free canonical writer + `sha2` seal for reader-modules),
D637/D638 (reader-wire remainder and M213 scope), D639 (inline full-text
channel), D640 (envelope, completion marker and two non-cyclic seals), D641
(S01 boundary). D602/D328 hold: `serde`/`serde_json` stay module-scoped to
`source_package`.
**Lifecycle ceiling:** this is a bounded wire envelope over an already-verified
decoded source and its reader projection. It is **not** an R1000 closure
artifact, not a CST/AST, not a temporal `StructuralAst`, and not expert legal
gold. It closes no requirement. R1000 stays active.

## 1. Purpose

M212-c25p2o left the reader projection as one pretty JSON object
(`reader_projection::canonical_projection_bytes`) with no envelope, no contract
version and no incompleteness marker (D637), and no decoded text on the wire:
`ProjectedSegment` carries only `fragment_ref`/`slot`/`span`, while the decoded
`value` lives only in the substrate `TextRecord`. R1000/D600 require the target
JSONL to carry the **full decoded text** of the source act, not locator-only
structure.

This contract fixes the wire form of the **cleaned structural JSONL projection**
so S02 (`cleaned_wire` writer, structural inspection, read-back,
independent verification, battery), S03 (navigation links) and S04
(Hold/TextOnly semantics) have one unambiguous specification:

- an LF-delimited JSONL envelope `manifest → policies → records → footer`;
- a declared contract version and profile;
- an explicit inline full-sentence text channel (`segment.text`);
- a closed, honest completion marker (`complete` / `incomplete`) that never
  lets a structural break succeed silently; and
- two non-cyclic integrity seals mirroring `source_package`.

This document is the source of the schema for the `ln_decode::cleaned_wire`
module. It fixes D639, D640 and D641.

## 2. Non-claims

- **Not** an R1000 closure artifact. It is one bounded input to the wider R1000
  program; requirement closure is owned by M213 as a whole, not by this slice.
- **Not** a CST, AST, Component Concept, CTV, `SourceBlock`, `SourceBlockRecord`,
  or temporal `StructuralAst`.
- **Not** normative, and **no** legal completeness, source authenticity, corpus
  coverage, or citation resolution is claimed.
- `records_seal_hash` / `manifest_hash` are **integrity, not authenticity**: an
  actor controlling the bytes can recompute them. A verifier must not trust the
  seal; independent verification is owned by S02.
- `cleaned_projection_wordml/v1` is provider-bounded to Consultant WordML. Raw
  decoded text only; **no** character normalization (NBSP, guillemets, dashes)
  is applied.
- Counts and hashes are **integrity, not coverage**. A record count, a text-byte
  sum, or a green seal must never be presented as full-text coverage or as
  evidence of legal completeness.
- This slice defines a **wire envelope**, not a read-back: reconstruction of
  `Record`s from the JSONL, `verify_projection` reuse, and any independent
  verifier are S02. The S01 structural inspection in §10 is a structure-only
  surface, not a read-back.
- The display-cleaning/suppression rule (iteration-21), navigation links, the
  Hold/TextOnly classification, the CLI, and atomic filesystem publish are
  **out of scope** (§11).

## 3. Envelope layout

One UTF-8 LF-delimited document, exactly one trailing LF:

```text
line 0        manifest   kind = "cleaned_projection_manifest"
line 1        policies   kind = "cleaned_projection_policies"
lines 2..n-1  records    kind in { "cleaned_projection_view",
                                   "cleaned_projection_segment",
                                   "cleaned_projection_reference" }
line n        footer     kind = "cleaned_projection_footer"
```

Records are grouped in the fixed order `view` (all views, in
`ReaderProjection.views` order), then `segment` (all segments, in
`ReaderProjection.segments` order), then `reference` (all references, in
`ReaderProjection.references` order). Records are never interleaved across
groups. Within a group the order is exactly the projection order; no reordering,
deduplication or id reassignment is permitted by the writer.

Every line is exactly one **compact** JSON object: ascending key order, no
whitespace between tokens, and **no embedded newline** inside any string (raw
C0 `\n`/`\r`/`\t` are escaped as `\n`/`\r`/`\t`). Two renders on equal input
produce byte-identical output.

The reader rejects, as a closed typed refusal (never as a silent success):

- missing trailing LF;
- any carriage return (`\r`) anywhere;
- an empty interior line (or an empty document);
- a missing, duplicated, or misordered `manifest` or `policies`;
- a missing, duplicated, or misordered `footer`;
- any line after the footer;
- an unknown `kind`, schema, or contract version.

```text
precedent: source_package reader rejects MissingTrailingLf, CarriageReturn,
EmptyLine, MissingManifest, MisorderedManifest, MissingFooter, MisorderedFooter
and trailing records after the footer (source-jsonl-contract.md §3).
```

Contract constants:

| name | value |
|---|---|
| family / schema | `law-nexus/cleaned-projection/v1` |
| contract version | `1` |
| model | `law-nexus/cleaned-projection-model/v1` |
| profile | `cleaned_projection_wordml/v1` |
| capability | `cleaned_projection_jsonl` |

## 4. Manifest (line 0)

Exactly one `manifest` line, first. Required keys (all present; an absent key is a
typed rejection, `null` is used only where declared):

| field | type | meaning |
|---|---|---|
| `kind` | `"cleaned_projection_manifest"` | closed line discriminator |
| `schema` | `"law-nexus/cleaned-projection-manifest/v1"` | closed schema tag |
| `version` | `1` | contract version |
| `model` | `"law-nexus/cleaned-projection-model/v1"` | closed model tag |
| `profile` | `"cleaned_projection_wordml/v1"` | pinned provider profile |
| `capability` | `"cleaned_projection_jsonl"` | closed capability tag |
| `generator` | object `{name, version}` | producing tool identity |
| `source` | object `{sha256, bytes}` | copied from the substrate manifest `source` |
| `parent` | object `{records_seal_hash, manifest_hash}` | pins the substrate footer seals |
| `limits` | object `{max_line_bytes, max_records, max_text_bytes}` | §9 |
| `non_authoritative` | `true` | derived, non-authoritative projection |

`generator.name` is a stable tool id (e.g. `ln-decode.cleaned_wire`),
`generator.version` is a string.

`parent.records_seal_hash` / `parent.manifest_hash` are the **substrate**
`source_package` footer values (not this document's seals): they pin the exact
upstream package the projection was built from. Both are 64 lowercase hex or
`null` (a substrate footer may carry `null` before sealing; an unsealed parent
pins `null`).

`source.sha256` is 64 lowercase hex; `source.bytes` is the original input byte
count. Both are integrity evidence, not authenticity.

## 5. Policies (line 1)

Exactly one `policies` line, immediately after the manifest. Required keys:

| field | value |
|---|---|
| `kind` | `"cleaned_projection_policies"` |
| `schema` | `"law-nexus/cleaned-projection-policies/v1"` |
| `version` | `1` |
| `cleaning_mode` | `"display_only_reversible"` |
| `text_retention` | `"full_decoded_text_retained_inline"` |
| `hold_text_only` | `"no_decoded_text_loss_permitted"` |
| `counts_scope` | `"integrity_not_coverage"` |
| `unknown_context` | `"retained_and_addressable"` |
| `normalization` | `"raw_decoded_text_no_char_normalization"` |
| `authenticity` | `"integrity_only_not_authenticity"` |
| `non_authoritative` | `true` |

A separate `policies` line (rather than a manifest sub-object as in
`source_package`) makes the cleaning and no-loss declarations independently
observable and machine-checkable. `hold_text_only` and `counts_scope` state
plainly that Hold/TextOnly never permit decoded-text loss (D600) and that the
counts are integrity, not coverage (D601, M213 success criterion #3).

## 6. Record schemas (lines 2..n-1)

All keys are required-present on every record of their type; an absent key is a
typed rejection, and `null` is used where a field does not apply (mirroring
`source-jsonl-contract.md` §4.2). Ids are opaque tokens assigned by the builder;
a read-back (S02) compares by substrate coordinates, not by id across runs.

### 6.1 `view`

| field | type | meaning |
|---|---|---|
| `kind` | `"cleaned_projection_view"` | closed line discriminator |
| `schema` | `"law-nexus/cleaned-projection-view/v1"` | closed schema tag |
| `view_kind` | closed view token | `paragraph` / `residual` / `table` / `row` / `cell` / `note` |
| `id` | `"vN"` or projection id | view id |
| `element_ref` | string | substrate element anchoring the view |
| `parent_view` | string or `null` | nearest valid container view |
| `children` | array of ids | child views, in projection order |
| `segment_refs` | array of ids | owned segments, in projection order |
| `reference_refs` | array of ids | owned references, in projection order |
| `flags` | object `{empty: bool}` | primary owns no segment; navigation has no children |

`kind` is the envelope-level discriminator; the reader-facing view vocabulary is
carried separately in `view_kind`. `flags.empty` is a nested object with the
single required key `empty`.

### 6.2 `segment`

| field | type | meaning |
|---|---|---|
| `kind` | `"cleaned_projection_segment"` | closed line discriminator |
| `schema` | `"law-nexus/cleaned-projection-segment/v1"` | closed schema tag |
| `id` | `"sN"` or projection id | segment id |
| `view` | view id | owning view |
| `ordinal` | u64 | position within the view |
| `segment_kind` | `"text"` or `"derived"` | closed segment vocabulary |
| `fragment_ref` | `"tN"` or `null` | source fragment (text only) |
| `slot` | `"text"` or `"tail"` or `null` | source slot (text only) |
| `span` | object or `null` | `{fragment, start, end}` whole-fragment span (text only) |
| `output_start` / `output_end` | u64 | position in the view's decoded output |
| `chars` | u64 | decoded character count of `text` |
| `origin` | closed token | `source_fragment` / `derived:tab` / `derived:line_break` / `derived:page_break` |
| `semantic` | closed token | `body` / `whitespace` / `field_code` / `revision_insertion` / `revision_deletion` / `derived_separator` / `empty` |
| `contextual` | bool | `semantic != body` |
| `element_ref` | string | owner element |
| `source_pos` | u64 | owner element pre-order index |
| `text` | string | **always present** — the full decoded text (see below) |
| `text_chars` | u64 | `text.chars().count()` |
| `text_bytes` | u64 | `text.len()` (UTF-8) |

**Text channel (D639).** The `text` field is present on **every** segment and is
the inline full-text carrier:

- a `source` segment (`segment_kind="text"`) carries the substrate
  `TextRecord.value` found by `fragment_ref` (with `owner`/`slot` consistent),
  preserving `fragment_ref`/`slot`/`span` provenance alongside the text;
- a `derived` segment carries the documented literal (`\t` for `tab`, `\n` for
  `line_break`/`page_break`) and has `fragment_ref = null`, `slot = null`,
  `span = null`.

No separate `text` record kind is introduced: by the reader coverage partition
every `tN` belongs to exactly one primary view, so the inline channel yields
exactly one occurrence of each fragment (D639). Provenance fields are `null` on
derived segments and never fabricated.

### 6.3 `reference`

| field | type | meaning |
|---|---|---|
| `kind` | `"cleaned_projection_reference"` | closed line discriminator |
| `schema` | `"law-nexus/cleaned-projection-reference/v1"` | closed schema tag |
| `id` | `"rN"` or projection id | reference id |
| `view` | view id | owning view |
| `ordinal` | u64 | position within the view |
| `reference_type` | closed token | `note_reference` / `endnote_reference` / `comment_reference` / `annotation_reference` / `field` / `unknown_wordml_element` / `foreign_element` |
| `element_ref` | string | reference element |
| `source_pos` | u64 | element pre-order index |
| `resolved` | `false` | always `false` in S01 (no citation resolution) |

## 7. Ordering and seals

Two non-cyclic integrity seals mirror `source_package`; both are 64 lowercase hex
strings and neither feeds back into its own input.

Let `bytes(line)` be the exact UTF-8 bytes of that line **excluding** its
terminating LF.

### 7.1 `records_seal_hash`

```text
records_seal_hash = sha256(
      bytes(policies_line)
   || bytes(record_line_0)
   || bytes(record_line_1)
   || ...
   || bytes(record_line_{k-1})
)
```

The policies line and every record line (views, then segments, then references)
are concatenated in file order, with no extra separator beyond the exact line
bytes. The manifest line and the footer line are excluded, so the digest is
independent of the footer that carries it.

### 7.2 `manifest_hash`

```text
manifest_hash = sha256(
      bytes(manifest_line)
   || "\n"
   || records_seal_hash              (64 lowercase hex chars)
   || "\n"
   || bytes(footer_body)
)
```

where `footer_body` is the canonical footer line with `records_seal_hash = null`
and `manifest_hash = null` (the keys remain present with a JSON `null` value).
The two LF separators are literal single bytes.

`records_seal_hash` does not depend on the footer; `manifest_hash` depends on the
manifest, `records_seal_hash` and the footer body with both seal fields nulled.
The construction is therefore non-cyclic and each seal is a pure function of
content that precedes it in the file. A reader recomputes both and rejects a
mismatch.

## 8. Completion and honest incompleteness

The footer (last line, exactly one) carries:

| field | type | meaning |
|---|---|---|
| `kind` | `"cleaned_projection_footer"` | closed line discriminator |
| `schema` | `"law-nexus/cleaned-projection-footer/v1"` | closed schema tag |
| `version` | `1` | contract version |
| `completion` | `"complete"` or `"incomplete"` | closed completion |
| `completion_basis` | closed token | primary basis |
| `incomplete_reasons` | array of closed tokens | non-empty iff `incomplete`; empty iff `complete` |
| `counts` | object | §8.2 |
| `records_seal_hash` | 64 lowercase hex | §7.1 |
| `manifest_hash` | 64 lowercase hex | §7.2 |
| `non_authoritative` | `true` | derived, non-authoritative projection |

### 8.1 Closed vocabularies

```text
completion           ∈ { complete, incomplete }
completion_basis     ∈ { bounded_projection_complete, hold, text_only,
                         limit_reached, unsupported_source, caller_scope }
incomplete_reasons[] ∈ { hold, text_only, limit_reached, unsupported_source,
                         caller_scope }
```

Invariants:

- `completion == "complete"` requires
  `completion_basis == "bounded_projection_complete"` and
  `incomplete_reasons == []`;
- `completion == "incomplete"` requires `incomplete_reasons` to be non-empty and
  to contain `completion_basis`;
- any other combination is a typed refusal (`CompletionMarkerInvalid`).

### 8.2 Two distinct remainder cases

- **Structural break** (missing/misordered manifest, policies or footer; missing
  trailing LF; CR; empty interior line; unknown `kind`/schema/version; trailing
  line after the footer) is a **fail-closed typed refusal**. It is never emitted
  and never reported as success — a truncated artifact cannot masquerade as a
  shorter-but-valid one.
- **Integrity-preserving partial export** (Hold/TextOnly, a reached cap, an
  unsupported source, or a caller-declared scope) is serialized with
  `completion = "incomplete"` and a closing `incomplete_reasons` set. It is
  honest output, not an error, and never `complete`.

A `complete` projection additionally requires that every substrate `TextRecord`
is attributed to exactly one source `segment`: zero missing and zero duplicate
(non-cyclic `complete`-with-loss is refused, D639). Counts and seals remain
integrity evidence: they certify structural consistency, not text coverage.

### 8.3 Counts

`counts` is an object of `u64` totals recomputed from the emitted records:
`views`, `segments`, `references`, `source_segments`, `derived_segments`,
`text_chars`, `text_bytes`, `records`. These are integrity counters for
provenance and comparison (D601); they are explicitly **not** a coverage or
completeness claim, and `policies.counts_scope` declares this on the wire.

## 9. Limits (hard fail-closed, validate-before-write)

`WireLimits { max_line_bytes: u64, max_records: u64, max_text_bytes: u64 }`.

| limit | default | scope |
|---|---|---|
| `max_line_bytes` | 64 MiB | each emitted line, measured before it is written |
| `max_records` | 4,000,000 | total `view` + `segment` + `reference` records |
| `max_text_bytes` | 512 MiB | sum of `text_bytes` over all segments |

The writer validates **before** writing any line: every line must be within
`max_line_bytes`, the record total within `max_records`, and the summed inline
`text_bytes` within `max_text_bytes`. A violation is a typed refusal, and no
partial projection is emitted. The manifest copies the effective limits used by
the writer so a consumer can see the bounds the artifact was produced under.

## 10. Verification surface (S01)

S01 ships a **structure-only** inspection
(`cleaned_wire::inspect_cleaned_wire`) plus a battery; it is explicitly **not** a
read-back (no `Record` reconstruction, no `verify_projection` reuse — that is
S02).

The inspection checks: exactly one trailing LF; no `\r`; no empty interior line;
exactly one `manifest` first, one `policies` second, one `footer` last; no line
after the footer; closed `kind`/schema/version on every line; the §8 completion
invariants; the 64-lowercase-hex-or-`null` shape of `source.sha256`,
`parent.records_seal_hash`/`parent.manifest_hash`, `records_seal_hash` and
`manifest_hash`. It returns a `WireEnvelopeSummary { contract_version, records,
completion, ... }`.

Closed refusal codes for structural truncation (S01): `MissingTrailingLf`,
`CarriageReturn`, `EmptyLine`, `MissingManifest`, `MisorderedManifest`,
`MissingPolicies`, `MisorderedPolicies`, `MissingFooter`, `MisorderedFooter`,
`TrailingRecordAfterFooter`, `UnknownKind`, `SchemaMismatch`, `VersionMismatch`,
`CompletionMarkerInvalid`, `HashShapeInvalid`, plus the limit/text-loss/
provenance codes of the writer.

Battery coverage (`crates/ln-decode/tests/cleaned_projection_wire.rs`,
handwritten oracle, never generated by the module under test): the pinned
`mixed-wordml.xml` fixture and the positive reader fixtures through
`source_package::capture` → `build_projection` → `render_cleaned_projection`
→ `inspect_cleaned_wire`; line-0 manifest, line-1 policies, last-line footer;
`version == 1`; one compact object per line; byte-identical repeated renders;
the full-text invariant (every substrate `TextRecord.value` in exactly one
source segment; summed `text_bytes` equals the substrate footer `text_bytes`;
derived segments carry no fragment/span; `verify_projection` stays `Ok`);
fail-closed truncation cases; and `completion`/`incomplete_reasons` behavior.
No raw decoded legal text is logged.

## 11. Out of scope

Reserved for the named downstream slices; S01 only reserves the fields and the
closed syntax:

| surface | owner |
|---|---|
| display-cleaning / suppression rule (iteration-21 profiles and omission manifest) | remaining / not-required-for-R1000 |
| read-back reconstruction of `Record`s and any exporter | S02 |
| independent verifier over the reconstructed artifact (round-trip, resealed semantic tamper) | S02 |
| navigation links and node addressability (heading/body/annex/table/footnote, source order) | S03 — delivered (§12) |
| Hold/TextOnly classification semantics | S04 — delivered (§13) |
| representative-corpus acceptance | S04 — delivered (§13) |
| CLI, filesystem atomic publish | S04 — delivered (§13) |

The S01 contract reserves `completion_basis` / `incomplete_reasons` and their
closed syntax only; it does not decide what qualifies as Hold or TextOnly. The
S01 inspection is structural and is not an independent verifier. R1000 remains
active.

## 12. Navigation and node addressability (S03)

**Status:** `[bounded]`
**Owning slice:** M213-t6p7d0 / S03 — delivered in
`crates/ln-decode/src/cleaned_nav.rs` and
`crates/ln-decode/src/cleaned_nav_verifier.rs`; battery
`crates/ln-decode/tests/cleaned_navigation.rs`
**Upstream:** the S02 read-back `CleanedProjection` plus the frozen
`source_package::Package`

S02 reconstructs the `ReaderProjection` from the wire artifact; the artifact
carries view/segment/reference *anchors* but no unified addressable node space.
S03 adds a **read-only** navigation layer that resolves one node by address,
follows structural links, walks to a parent or a root, reads the deterministic
document order, and follows the reverse anchors of an element or a fragment. It
is a pure offline in-memory library: no filesystem, network, database, or API
surface, and no runtime monitor.

The navigation layer never mutates the projection:
`ProjectedReference.resolved` stays `false` (a closed invariant of the frozen
`reader_verifier`). The reference target, when one exists, lives only in a
`NavLink`.

### 12.1 Unified node address

`NodeAddress` is a closed three-variant address over three distinct id spaces:

```text
NodeAddress ∈ { View(ViewId), Segment(SegmentId), Reference(ReferenceId) }
```

The variant is part of the identity: `vN`, `sN` and `rN` never collide. Every
projected view, segment and reference is exactly one node; `NavNode` carries the
address, the XML `element_ref` anchor, the `source_pos` pre-order element
position taken from the `Package` (never parsed from an `eN` token), the
per-view `ordinal` for segments and references, the `owning_view` (a view's
`parent_view`, otherwise the segment/reference `view` field), and a kind-specific
`NavNodeBody` (`View`/`Segment`/`Reference`).

### 12.2 Link kinds

| kind | from → to | meaning |
|---|---|---|
| `Contains` | view → child view | the `children` relation |
| `Owns` | view → segment, view → reference | the `segment_refs`/`reference_refs` relation |
| `ResolvesTo` | reference → note view | bounded in-package note resolution (§12.4) |
| `Precedes` | node → next node | adjacency in document/source order |

Bounds: a node never resolves outside its own `Package`; a resolution is never
fabricated to satisfy a caller.

### 12.3 Anchors are queries, not nodes

An XML element anchor is not itself a node. Reverse lookups are queries over the
index: `anchors_of_element(&ElementRef) -> &[NodeAddress]` (every node anchored
on that element, in record order) and `anchors_of_fragment(&FragmentRef) ->
Option<&NodeAddress>` (the single source segment that names the fragment).

### 12.4 Bounded note resolution

For `reference_type == note_reference` the definition element is the
`footnote`; for `endnote_reference` it is the `endnote`. A definition matches
when its Clark-qualified name has that local name **and** its Clark-attribute
local name `id` equals the reference anchor's `id` value. Exactly one matching
definition **and** exactly one `Note` view anchored on it yields one `ResolvesTo`
link from the reference to that view. The closed outcomes are:

| situation | outcome |
|---|---|
| exactly one definition and exactly one note view | `ResolvesTo` link |
| zero definitions, or zero anchored note views, or no `id` attribute | `resolve_reasons[ref] = NoMatchingNoteDefinition` |
| more than one definition or more than one note view | `MultipleMatchingNoteDefinitions` |
| the reference element is absent from the substrate | `MissingAnchorElement` |
| any other `reference_type` | `NotAResolvableReference` |

`ProjectedReference.resolved` is never set; absence of a target is a recorded
outcome, not an invented link. `NavResolveReason` is closed and carries `as_str`.

### 12.5 Two deterministic orders

- **Record order** (`record_order`): all views in `projection.views` order, then
  all segments in `projection.segments` order, then all references in
  `projection.references` order.
- **Document/source order** (`source_order`): views sorted by the `Package`
  pre-order position of their `element_ref`, with a stable tie-break on the
  `projection.views` index; then, per view, its `segment_refs` ordered by
  `ordinal`; then, per view, its `reference_refs` ordered by `ordinal`.

Both orders are total over the node set (no duplicates, no omissions) and are
deterministic across repeated builds on equal input. `Precedes` is exactly the
adjacency chain of `source_order`.

### 12.6 Fail-closed codes

`build_nav_index` / `build_nav_index_from_wire` return a closed `NavError`:

| `NavErrorKind` | meaning |
|---|---|
| `DuplicateNodeId` | two nodes share one address |
| `DanglingViewRef` | a `children` entry names an absent view |
| `DanglingSegmentRef` | a `segment_refs` entry names an absent segment |
| `DanglingReferenceRef` | a `reference_refs` entry names an absent reference |
| `MissingOwningView` | a segment/reference `view` names an absent view |
| `DanglingParentView` | a `parent_view` names an absent view |
| `MissingAnchorElement` | an `element_ref`/`fragment_ref` has no substrate record |
| `ArtifactUnreadable` | the wire artifact could not be read back (detail is the closed `WireError` kind) |
| `CyclicViewGraph` | the `parent_view` chain contains a cycle |

`NavError.detail` and `NavFinding.detail` carry ids, closed codes and counters
only; decoded fragment text is never interpolated.

### 12.7 Independent verification

`cleaned_nav_verifier::verify_nav_index(&NavIndex, &CleanedProjection, &Package)`
re-derives its oracle from the projection plus the package with a private walk
(it never calls the builder and never trusts the index's own fields as proof).
It returns `Ok(())` or one typed `NavFinding` per violated invariant:

| `NavVerifyCode` | meaning |
|---|---|
| `NodeSetMismatch` | index node set or grouped record order disagrees with the projection |
| `SourceOrderMismatch` | index `source_order` disagrees with the independently recomputed one |
| `LinkDangling` | a link endpoint does not resolve to an indexed node |
| `LinkDuplicateOrMisordered` | a duplicate link, or the `Precedes` chain differs from the recomputed source order |
| `AnchorMissing` | an element, fragment or span anchor is absent or out of bounds |
| `ResolvedFlagViolated` | a projected reference carries `resolved == true` |

The battery (`cleaned_navigation.rs`) is a third, handwritten oracle: it pins
the `mixed-wordml.xml` fixture and the nine positive reader fixtures by sha256,
recomputes the node set, both orders and the note resolution independently, and
proves tamper fail-closed on a mutated index clone and on a hand-tampered
projection.

### 12.8 Non-claims

This is **not** a graph projection, **not** citation resolution, **not** region
classification, **not** CST/AST/CTV, and **not** a legal-completeness or corpus
coverage claim. `WireError`/seal integrity is S02; Hold/TextOnly classification
is S04. R1000 stays active.

## 13. Hold/TextOnly semantics, CLI, atomic publish and declared corpus slice (S04)

**Status:** `[bounded]`
**Owning slice:** M213-t6p7d0 / S04 — delivered in
`crates/ln-decode/src/cleaned_completion.rs`,
`crates/ln-decode/src/cleaned_publish.rs`,
`crates/ln-decode/src/cleaned_cli.rs` and
`crates/ln-decode/tests/cleaned_projection_corpus.rs`
**Upstream:** the S01 wire envelope (§8), the S02 read-back and independent
verifier, and the S03 navigation layer (§12)

### 13.1 Closed scope declaration to completion mapping

§8.1 reserves the `completion_basis` / `incomplete_reasons` syntax; S04 closes
what qualifies as Hold or TextOnly. `ScopeDeclaration` is a closed
producer vocabulary: a declaration states what the producer actually projected,
never a legal claim, and never permits decoded-text loss.

| `ScopeDeclaration` | declaration token | `completion_for` mapping |
|---|---|---|
| `WholeProjection` | `complete` | `Complete` |
| `StructureHold` | `hold` | `Incomplete { basis: Hold, reasons: [Hold] }` |
| `TextOnlyScope` | `text_only` | `Incomplete { basis: TextOnly, reasons: [TextOnly] }` |
| `NarrowedScope` | `caller_scope` | `Incomplete { basis: CallerScope, reasons: [CallerScope] }` |
| `UnsupportedSource` | `unsupported_source` | `Incomplete { basis: UnsupportedSource, reasons: [UnsupportedSource] }` |

`ScopeDeclaration::from_token` is fail-closed: an unknown token is a
`CompletionError::UnknownToken` that carries no payload string, so a
caller-supplied token never reaches a wire diagnostic. `limit_reached` is
**not** a declaration and is never produced by `completion_for`: a reached
writer cap is discovered by the writer's own validate-before-write (§9), not
declared by a caller. `Complete` is therefore reachable if and only if the
source class is `SupportedWordml` and the declaration is `WholeProjection`;
every other pair yields an `Incomplete` whose non-empty reason set contains its
basis (§8.1).

`classify_completion(source_class, declaration)` applies one honest correction
over `completion_for`: a source that is not supported WordML can never be
`Complete`, so a declared `Complete` becomes
`Incomplete { basis: UnsupportedSource, reasons: [UnsupportedSource] }`, and an
already-`Incomplete` completion keeps its basis and gains `UnsupportedSource`
exactly once (deduplicated, deterministic order).

### 13.2 Hold and TextOnly are honest partial bases

Hold and TextOnly declare that the **structural or normative interpretation** is
incomplete or inapplicable. They say nothing about the text channel: the decoded
text channel stays **full** for a `complete`, a `hold` and a `text_only`
artifact alike, and decoded-text loss remains forbidden
(`policies.hold_text_only`). The writer's text-loss check runs on the
`Complete` branch only (§8.2); the S04 battery therefore proves text safety
independently, on a declared corpus slice, by its own traversal of
`Package.records()` rather than by trusting the completion marker.

### 13.3 `cleaned-project` CLI

The `ln-decode` crate ships one deterministic, stdlib-only binary,
`cleaned-project`, over three commands:

| command | inputs | effect |
|---|---|---|
| `export` | exactly one of `--from-xml <path>` / `--package <path>`; `--completion <token>`; optional `--out <path>` | capture/gate/project, then export the cleaned artifact to `--out` (atomic) or stdout |
| `read` | `--artifact <path>` | read back the artifact and print a counts-only summary |
| `verify` | `--artifact <path> --package <path>` | run the independent verifier over the read-back |

Exit codes are closed: `0` (ok), `2` (usage / unknown flag), `3` (publication
unwritable), `4` (artifact IO / verification failure), `5` (input XML, package,
capture or projection unreadable). The CLI reads no clock, locale or environment
variable and iterates no hash map, so a repeated run on equal inputs is
byte-identical. Diagnostics carry closed codes and counters only; stderr never
carries raw decoded text.

`--from-xml` gates through `reader_gate::gate_reader` (supported WordML only),
while `--package` classifies the decoded records freely. An out-of-profile
package is therefore exported as an honest
`Incomplete { basis: UnsupportedSource }` rather than refused.

### 13.4 Atomic publication

`cleaned_publish::write_cleaned_projection_atomic(path, artifact)` writes a
sibling `<path>.tmp` in the same directory and renames it onto `path`. On any
error the tmp file is removed and a typed `WireError { kind: WriteFailed }` is
returned, so a reader never observes a half-written artifact and no `*.tmp`
survives a successful publication. Only atomic **visibility** is claimed: no
`fsync`, durability or crash-recovery guarantee is claimed.

### 13.5 Declared corpus slice

The acceptance battery (`cleaned_projection_corpus.rs`) declares a bounded slice
of the tracked `law-source/consultant` **fixture vault** (not the corpus):
the 82 top-level `*.xml` fixtures, each at most the `Limits::default()`
`max_input_bytes` cap (64 MiB), with `.deprecated/` excluded. A bounded sub-slice
of six explicitly named documents is pinned by sha256 and driven for all three
of `WholeProjection`, `StructureHold` and `TextOnlyScope`:

- `fs::read` → sha256 pin → `capture` → `gate_reader` (`SupportedWordml`) →
  `build_projection`;
- for each declaration: `export_cleaned_projection` → `read_cleaned_wire` →
  `verify_cleaned_wire`; the read-back completion token, basis and reasons match
  the handwritten expectation; a second export is byte-identical;
- an independent traversal of `Package.records()` proves every substrate
  `TextRecord.value` appears exactly once in the inline text channel, none is
  missing or duplicated, and the declared `chars` / `text_bytes` are the
  recomputed `chars()` / `len()`;
- `build_nav_index_from_wire` + `verify_nav_index` accept the incomplete
  artifact too (the S03 connection); and
- `write_cleaned_projection_atomic` publishes and reads back with no leftover
  `*.tmp`.

A separate `#[ignore]` runner attempts all 82 fixtures out-of-band (the sweep
does not fit the 600 s evidence cap): each fixture within the fail-closed
serialized-package cap runs capture, gate, project and one `Complete` export →
read → verify, logging counters and file names only. The declared-slice bound is
on **input** bytes (`max_input_bytes`, 64 MiB); `capture` additionally enforces
`max_package_bytes` (512 MiB) over the canonical serialized package, so a fixture
whose expanded package exceeds that cap is recorded as a closed `PackageTooLarge`
outcome, neither silently accepted nor skipped. At least one of the 82 fixtures
— the ~32.6 MiB unified-nomenclature decision
(`reshenie-soveta-evraziiskoi-ekonomicheskoi-komissii-…-nomenklatury-…`) — is
recorded as oversized rather than processed; the remaining fixtures are captured,
gated, projected and round-tripped. The per-fixture `PackageTooLarge` boundary
is therefore a **non-claim** of full-slice processability: the bounded
six-document sub-slice above is the affirmative text-safety proof, and the
82-fixture sweep is an honest attempt whose cap-exceeding members are reported,
not hidden.

### 13.6 Non-claims

This is a bounded acceptance over the **declared** slice only. It is **not**
corpus coverage — `law-source/consultant` is a fixture vault, and the corpus is
`consru_export/exports/`. Seals and counts remain integrity, not coverage; the
battery makes no source-authenticity, legal-completeness or citation-resolution
claim. Display-cleaning/suppression stays out of scope. R1000 stays active, and
its closure is owned by milestone M213 as a whole, not by S04.
