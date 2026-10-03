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
so S02 (`cleaned_wire` writer, structural inspection, battery), S03
(navigation links) and S04 (Hold/TextOnly semantics, read-back and independent
verification) have one unambiguous specification:

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
| display-cleaning / suppression rule (iteration-21 profiles and omission manifest) | S04 / later |
| read-back reconstruction of `Record`s and any exporter | S02 |
| independent verifier over the reconstructed artifact (round-trip, resealed semantic tamper) | S02 |
| navigation links and node addressability (heading/body/annex/table/footnote, source order) | S03 |
| Hold/TextOnly classification semantics | S04 |
| representative-corpus acceptance | S04 |
| CLI, filesystem atomic publish | S04 |

The S01 contract reserves `completion_basis` / `incomplete_reasons` and their
closed syntax only; it does not decide what qualifies as Hold or TextOnly. The
S01 inspection is structural and is not an independent verifier. R1000 remains
active.
