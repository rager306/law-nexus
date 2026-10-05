# NPA source-to-analysis JSONL integration contract

**Status:** `[bounded]` successor revision — S02 record schema (§8A) and
the S03 context family, read-back and independent verifier (§8B);
no runtime in this task
**Owning slice:** `M214-es3jvw` / `S01` — T01 tracked contract;
executable seam and tests are S01/T02–T03, document output is S02
**Successor revision:** S02 adds the full record field lists in §8A and
defers the `context` family to S03 (D658); S03 adds the opt-in `context`
family, the `context_incomplete` completion basis and the
read-back/independent-verifier admission in §8B (D661/D662/D663). The
S01 discipline (§1–§7) and the S02 six-family envelope are unchanged;
an empty context stays byte-identical to S02. `[bounded]`
**Authority:** ADR-0013 (universal multi-source parser), ADR-0015
(hexagonal verification architecture), ADR-0028 (typed lexer / dual
tokenizer), ADR-0029 (requisites-anchored member assembly — anchor
boundary), ADR-0016 (structural legal identity), ADR-0009 (five-clock
safety contract); decisions D603 (anchor coordinates), D628/D631
(reader coordinate base), D633/D634 (reader seal + independent
verifier), D638 (R1000 remainder under M213), D640 (cleaned JSONL
envelope), D650/D651 (horizon correction), D655/D656 (M214 requirement
binding), D657 (document-scoped analysis block binding), D658 (S02
envelope format and family scope), D661 (reader-native context
substrate), D662 (opt-in context family + `context_incomplete`), D663
(read-back/verifier independence)
**Upstream evidence contracts:**
`prd/architecture/source-jsonl-contract.md` (`[bounded]`),
`prd/architecture/reader-view-contract.md` (`[bounded]`),
`prd/architecture/reader-projection-contract.md` (`[bounded]`),
`prd/architecture/cleaned-projection-contract.md` (`[bounded]`)
**Upstream analysis surfaces:** `crates/ln-decode/src/npa_anchor.rs`,
`npa_typed.rs`, `npa_link.rs`, `npa_classify.rs`,
`lawref.rs`/`local_grammar.rs`/`morphology.rs`, `document_context.rs`
**Lifecycle ceiling:** this document fixes a design contract. It mints
**no** Rust type, **no** runtime, **no** public API name, **no**
lifecycle promotion, **no** requirement closure. `deferred-undefined`
and `runtime deferred` remain stop-signs. The outcome/refusal names in
§7.1 are **semantic classes** describing required behavior; the exact
Rust identifiers are chosen by S01/T02 and are not frozen here.

---

## 1. Purpose

The audit that preceded M214 found two disconnected Rust paths in
`ln-decode` on the same real documents:

- the **evidence path** — `source_package` (decoded-source JSONL) →
  `reader_contract`/`reader_projection` (reader view forest) →
  `cleaned_wire` (cleaned structural JSONL envelope) — which carries
  source bytes, half-open UTF-8 fragment spans and integrity seals,
  but does not run NPA analysis; and
- the **analysis path** — `npa_anchor`/`npa_typed`/`npa_link`/
  `npa_classify`, `lawref`/`local_grammar`/`morphology` and
  `document_context` — which produces typed members, linked relations,
  classification rows and context claims, but is consumed only as
  fixture planes and corpus counters
  (`npa_report::run_integration_report`,
  `npa_context_baseline::render_jsonl`), never as a document-scoped
  analytical artifact.

This contract fixes the **source-to-analysis boundary** so that S01/T02
can build one minimal executable seam and S02–S04 can materialize,
read back and independently verify a document-scoped analysis JSONL
without guessing identity, coordinates, token views or outcomes.

The contract fixes five things:

1. source and document identity (§4);
2. half-open UTF-8 coordinates (§5);
3. token views (§6);
4. outcomes and provenance (§7);
5. the **companion vs envelope** format decision (§3) and the envelope
   discipline that follows from it (§8).

Temporal scope and downstream admission criteria are pinned in §9 and
§10. Positive and hostile examples are normative in §11–§12.
Remainder reconciliation is §13.

## 2. Non-claims

- **Not** an R1000 closure artifact. R1000 stays active and unclosed
  (D638); M213 delivered the cleaned wire/read-back/verifier/nav/
  Hold/TextOnly remainder, but corpus-wide acceptance was never
  claimed and display-cleaning remains remaining. M214 consumes the
  cleaned/source projection; it must not auto-close R1000.
- **Not** a CST, AST, temporal `StructuralAst`, Component Concept, CTV,
  CLV, `SourceBlock`, `SourceBlockRecord`, `EvidenceSpan`,
  `EvidenceAnchor` or ADR-0017 `TextAnchor`. None of those is minted
  here, and none may be inferred from this document.
- **Not** a semantic or legal gold standard. No legal completeness,
  source authenticity, corpus coverage, retrieval quality or citation
  resolution is claimed.
- **Not** a temporal contract. No clock, force, membership, effect or
  applicability assignment is introduced (§9).
- **Not** a promotion surface. `counts`/`hashes` are integrity, not
  coverage; a green verifier is not semantic correctness.
- **Not** a second source of truth. The analysis artifact is a
  **companion** to the verified source evidence, never a replacement
  for it (§3).
- **Not** a client for the restricted corpus. Portable tracked evidence
  stays count/hash-only; the analysis envelope does not re-carry the
  raw decoded corpus (§8.4, §13).
- **Not** a public API freeze. S01/T02 chooses the exact Rust names;
  this contract fixes the semantics and the reuse constraints only.

## 3. Decision — companion vs envelope

Two reference formats already exist in the repository.

| Axis | **Companion** — `m207-hybrid-records/v1` | **Envelope** — `source_package` / `cleaned_projection` |
|---|---|---|
| Form | one UTF-8 JSON object per file (documents → fragments → bundles) | LF-delimited JSONL: `manifest → (policies) → records → footer` |
| Authority | M207 companion contract `[proposed]` (owned by ADR-0007 harness `[validated]`); "not a Rust product type"; "Rust product must not grow a second domain model of these records" | ADR-0013/0015 production Rust wire, `[bounded]` (D640) |
| Identity | `schema` + `schema_version` only | schema + version + `source.sha256` + `parent` seals + document version |
| Integrity | optional honesty keys | two non-cyclic seals (`records_seal_hash`, `manifest_hash`) |
| Read-back/verifier | external Python validator (`M207_HYBRID_RECORDS_OK`) | in-repo independent verifier (`reader_verifier`, `cleaned_verifier`) |
| Text channel | optional `source_utf8` per fragment | inline full decoded text (`segment.text`) |
| Byte-identity | `json.dumps(..., sort_keys=True)` | compact one-line JSON, fixed order, LF-terminated |

**Decision (by authority): envelope.**

Rationale:

1. The only *production* Rust wire discipline in this repository is the
   LF-JSONL envelope (`source-jsonl-contract.md`, `[bounded]`;
   `cleaned-projection-contract.md`, `[bounded]`; D640). The M207
   companion is explicitly `[proposed]`, owned by the Python control
   plane (ADR-0007), and forbids the Rust product from growing a second
   domain model of it.
2. M214/S03 requires **read-back and independent verification of a
   JSONL** with resealed-tamper detection. That pattern is exactly the
   envelope + parent-pin + independent-recompute pattern already
   implemented in `reader_verifier` (D634) and reused by
   `cleaned_verifier` (D643); a bare companion object has no manifest,
   no seals and no read-back contract.
3. The M214 vision requires the analytical result to be materialized
   **separately from the source evidence** and then read back. Only the
   envelope carries a parent identity that binds an analysis record to
   the exact source bytes it was derived from.

**The envelope is also a companion.** The two are not opposites:
*envelope* is the wire form; *companion* is the evidence relationship.

- The analysis envelope **pins** the verified parent by identity
  (`source.sha256`, `parent.records_seal_hash`/`manifest_hash`,
  document version) and carries half-open spans into that parent.
- It is **never** a second source of truth and **never** re-carries the
  full decoded evidence corpus in place of the parent (§8.4).
- Span resolution requires the pinned parent to be present and
  identity-equal; a missing or mismatched parent is a closed refusal,
  never a silent rebase.

Rejected options:

- bare `m207-hybrid-records/v1`-shaped companion object as the Rust
  analysis format (authority and read-back gap above);
- a self-contained envelope that duplicates raw decoded text and
  becomes a competing corpus copy (violates "materialize separately
  from the source evidence", creates a second source of truth, and
  risks restricted-corpus exposure).

## 4. Source and document identity

### 4.1 Parent evidence identity (mandatory)

The envelope is valid only when it names the verified parent it was
built from:

| Field | Source | Rule |
|---|---|---|
| `source.sha256` | parent `source_package` manifest `source.sha256` | 64 lowercase hex; copied, never recomputed; digest of the original un-normalized input bytes |
| `source.bytes` | parent `source_package` manifest `source.bytes` | original input byte count |
| `parent.schema` | parent envelope family tag | e.g. `law-nexus/cleaned-projection/v1` or `law-nexus/source-package-model/v1` |
| `parent.records_seal_hash` | parent footer seal | 64 lowercase hex or `null` (unsealed parent) |
| `parent.manifest_hash` | parent footer seal | 64 lowercase hex or `null` (unsealed parent) |

`source.sha256` is integrity evidence, **not** authenticity (mirrors
`source-jsonl-contract.md` §2 and `cleaned-projection-contract.md` §2).

### 4.2 Document version identity

One decoded document version is the triple carried by
`document_context::DocumentVersionRef`:

- `document_version_ref` — non-empty stable token;
- `source_revision` — the decoded source revision;
- `decoder_profile` — the pinned decoder profile
  (e.g. `reader_wordml_profile/v1`, `cleaned_projection_wordml/v1`).

Binding rules:

1. All records in one envelope belong to exactly one document version.
2. Two versions that share `document_version_ref` but differ in
   `source_revision` or `decoder_profile` are **different versions**
   and must not be mixed in one envelope.
3. `document_version_ref` alone is not source identity: the byte
   binding is `source.sha256` + the parent seals. A matching
   `document_version_ref` with a different `source.sha256` is a
   `SourceIdentityMismatch` (§7).

### 4.3 Fragment identity

| Field | Type | Rule |
|---|---|---|
| `fragment_ref` | reader `FragmentRef` (`tN`) | resolves to exactly one text record in the pinned parent; globally unique in the envelope |
| `element_ref` | reader `ElementRef` (`eN`) | optional; element-anchored records only |
| analysis `block` | `npa_anchor::LocalSpan.block` | caller-side block index; the wire layer maps `block → fragment_ref` (D603) |

An anchor names the fragment only; document membership is recovered from
the pinned parent catalog, never re-invented. A fragment belongs to
exactly one document version.

### 4.4 Cross-document refusal

- A record that cites a fragment whose parent identity differs from the
  envelope's pinned identity is refused (`CrossDocument` /
  `SourceIdentityMismatch`) — never rebased onto the envelope's source.
- More than one `source.sha256` value per envelope is structurally
  invalid.
- Cross-document relations are out of scope for this contract, exactly
  as they are for `m207-hybrid-records/v1` (`CROSS_DOC_REF`).

## 5. Half-open UTF-8 coordinates

### 5.1 Definition

A source coordinate is a **half-open UTF-8 byte range `[start, end)`**
local to one named fragment's decoded `value`:

- `0 <= start < end <= fragment_byte_len`;
- both bounds sit on UTF-8 code-point boundaries of the fragment text.

Existing authoritative shapes:

| Type | Owner | Carries |
|---|---|---|
| `LocalSpan { block, start, end }` | `npa_anchor` (D603) | block index + byte range |
| `ReaderFragmentSpan { fragment, start, end }` | `reader_contract` (D631) | fragment id + byte range |
| `TextSpan { start, end }` | `domain` | block-relative range, **no** fragment id |
| `SourceSpan` / `SourceLocation` | `domain` | **XML/ODT artifact** byte range — a different coordinate system |

### 5.2 Validation

Validation order mirrors `npa_anchor::check_span` (D603) and
`reader_contract::check_fragment_span`:

1. `EmptyOrInverted` — `start >= end`;
2. `OutOfBounds` — `end > fragment_byte_len`;
3. `NotCharBoundary` — either bound splits a code point.

When validation passes, `&fragment_text[start..end]` is the original
UTF-8 slice and is UTF-8 valid by construction.

### 5.3 Rules

- A coordinate is always bound to **one** fragment; cross-fragment and
  cross-block spans are invalid.
- XML/ODT artifact coordinates (`SourceSpan`) and decoded-text
  coordinates (`TextSpan`, `LocalSpan`, `ReaderFragmentSpan`) are
  distinct; adapters own any mapping, and this contract never mixes
  them.
- A bare `TextSpan` that crosses the wire must first be extended with
  its fragment id to a fragment-qualified shape
  (`ReaderFragmentSpan`-like). A `TextSpan` alone is not a wire
  coordinate.
- `LocalSpan.block` must be mapped to a `fragment_ref` before
  serialization; an unmapped block is a closed refusal, never an
  invented fragment id.
- A mapping request for a coordinate system or fragment kind this seam
  does not support is `UnsupportedMapping`, never a partial or
  best-effort mapping.
- Character offsets, line offsets, byte offsets into the artifact and
  "close enough" spans are all invalid.

## 6. Token views

`ln-decode` keeps three deliberate token producers (ADR-0028 dual
tokenizer, D380/D381). They are **not aliases**, and no `From`/`Into`
conversion between them may be added.

| Producer | View type | Consumers | Semantics |
|---|---|---|---|
| `lexer::lex` | `NpaToken` (closed nine-kind set) | `lawref::capture_lawrefs`, `local_grammar::extract_structural_frames` | covering stream; invariant `text == concat(lexemes)`; `ст.` mints `Abbrev{st}`, never a `Word` |
| `tokenizer::tokenize` | `AlphabeticToken` | `references`, `temporal`, `unknown_forms` | private alphabetic splitter; non-letters are delimiters; includes abbreviation stems (`ст`) |
| `tokenizer::words_from_covering` | `CoveringWord` | `morphology::find_legal_markers` | covering `Word` tokens only; abbreviation stems absent by construction |

Rules:

1. Every analysis record that carries a token-derived outcome declares
   its **token view** (closed: `covering` | `alphabetic` |
   `covering_word`) and its producing rule.
2. Substituting one view for another is refused (`TokenViewMismatch`),
   never silently accepted.
3. A morphology outcome must derive from `covering_word`
   (`words_from_covering`); a reference/temporal/unknown-form outcome
   must derive from the alphabetic splitter; LawRef capture and
   structural frames must derive from `covering` (`lex`).
4. Collapsing the two scanners into one call is rejected until those
   consumers are rewritten over `TokenKind` (ADR-0028 §Dual tokenizer).
5. Token spans are half-open UTF-8 byte ranges on the same fragment
   text and obey §5.
6. TYPE/`kind` labels remain **working labels**, never adopted legal
   TYPE vocabulary (ADR-0029, M207 contract).
7. A context record's nullable `view` follows this rule: token-derived
   request kinds (`OpenSeriesHead`, `ScopedAlias`,
   `CurrentDocumentRequisites`, `ExplicitAnchorLookup`) declare
   `covering` (structural frames and this-ref/LawRef capture derive from
   `lexer::lex`); structural-only request kinds (`AncestorPath`,
   `AdjacentBlocks`) declare `view: null` because they carry no
   token-derived outcome (§8B.2). `[bounded]`

## 7. Outcomes and provenance

### 7.1 Closed typed outcomes (no silent success, no bare `None`)

| Stage | Outcome surface |
|---|---|
| anchor scan | `AnchorDiagnostic::{InvalidSpan, RejectedAnchor(RejectReason), DuplicateOccurrence}` |
| typed member | `TypeDerivation::{WrittenHere, Unresolved}` + `unresolved` + `alternatives` (spans) |
| linking | `LinkDerivation::{TypedAnchor, DocumentHead, ApprovedByQuote, ScopedAlias, ThisDocumentRef, SeriesContinuation, NamedTypeText, Refused}` + `LinkDiagnostic::{OpenSeriesWithoutHead, IncompatibleSeriesHead, TypeNotInherited, HeadFamilyCarryRefused, AliasWithoutDeclaration, HeadUnavailable}` |
| classification | `GraphClass::{IdentifyingAct, Hold, Overlay, Refuse}` + axes B–H + `IdentityKey` (`do_not_project`, `overlay_not_rank`, `deferred-undefined`, `hold` are explicit non-projections) + `ClassificationDiagnostic` |
| local grammar | `FrameStatus::{Proposed, Ambiguous, Rejected}`, `FrameDiagnostic`, `FrameLimitOutcome`, `FrameAdmission`, `EnumerationState` |
| LawRef capture | `LawRefCaptureBatch` limit outcome + `PairDiagnostic` |
| document context | `ContextStatus::{Resolved, Partial, Conflicting, Unavailable, Cycle, Limit}`, `ContextClaimStatus`, `DerivationRelation`, `ContextDiagnostic` |
| source-mapping seam (T02) | closed refusal classes (exact Rust identifiers chosen by T02): coordinate `EmptyOrInverted` / `OutOfBounds` / `NotCharBoundary` (reusing `npa_anchor::SpanError` / `reader_contract::ContractErrorKind` vocabulary), `UnknownFragment`, `CrossDocument`, `SourceIdentityMismatch`, `DocumentVersionMismatch`, `TokenViewMismatch`, `UnsupportedMapping`, envelope-structural refusal, temporal-field-forbidden, corpus-transfer-forbidden |

### 7.2 Provenance rules

1. Every analysis record cites the rule(s) and source span(s) that
   produced it; a record without provenance is invalid.
2. Occurrences are preserved, never merged by identity: a repeated
   `(date, number)` yields `DuplicateOccurrence` plus a separate record
   (D603/D604).
3. Competing hypotheses are retained with their spans
   (`TypedMember.alternatives`, `CoordinatingFrame.alternatives`,
   retained conflicting frames); no proximity/order winner is invented.
4. A refusal is a value, not an error to hide: `GraphClass::Refuse`,
   `IdentityKey::{Hold, DoNotProject, OverlayNotRank, DeferredUndefined}`,
   `ContextStatus::{Unavailable, Cycle, Limit}` and the mapping
   refusals above are all closed, observable outcomes.
5. Fail-closed: a missing/unsupported input yields a typed refusal or
   `Unknown`, never an invented value, never a silent success.

## 8. Envelope discipline (S01-level shape)

S01 fixes the discipline and the mandatory identity/coordinate/outcome
fields. S02 fixes the full record field lists in the successor revision
**§8A** (D658); the shape below stays the envelope skeleton.

### 8.1 Layout

LF-delimited JSONL, exactly one trailing LF:

```text
line 0        manifest   kind = "npa_analysis_manifest"
line 1        policies   kind = "npa_analysis_policies"
lines 2..n-1  records    family in { document, fragment, member, relation,
                                     classification, diagnostic, context }
line n        footer     kind = "npa_analysis_footer"
```

S02 emits the six families `document`/`fragment`/`member`/`relation`/
`classification`/`diagnostic`; S03 adds the seventh `context` family as
an **opt-in** addition (§8B, D662), so an S02 envelope with zero context
records stays byte-identical. Every line is one compact JSON object
(fixed key order, no embedded newline). Structural break
(missing/misordered manifest/policies/footer, empty interior line, CR,
trailing record) is a closed typed refusal, never a silent success.
`[bounded]`

### 8.2 Manifest (mandatory identity)

`source`, `parent`, `document_version_ref`, `source_revision`,
`decoder_profile`, `profile`, `version`, `generator`,
`non_authoritative: true`, `limits`. Exact field list: §8A.4.

### 8.3 Policies (mandatory non-claims)

`counts_scope: integrity_not_coverage`,
`semantic_scope: not_legal_gold`,
`temporal_scope: identity_and_coordinates_only`,
`promotion: none`,
`authenticity: integrity_only_not_authenticity`,
`corpus_transfer: no_restricted_corpus`,
`non_authoritative: true`. Exact field list: §8A.5.

### 8.4 Text channel — companion, not a second corpus

The default and contracted behavior: a `fragment` record carries
`fragment_ref`, `byte_length` and `content_sha256` (integrity, not
coverage); span records index it. The envelope **does not** re-carry
the full decoded evidence corpus. Span resolution requires the pinned
parent; a missing/mismatched parent is a closed refusal.

If S02 later needs a bounded inline fragment-text channel for
standalone verification, that is an explicit schema decision (v2),
not a silent addition, and it must remain count/hash-bounded for
tracked portable evidence.

### 8.5 Footer

`completion: complete|incomplete` with `completion_basis` and
`incomplete_reasons` (non-empty iff incomplete), counts, and the two
non-cyclic seals mirroring `source_package`/`cleaned_projection`. Exact
field list: §8A.6.

## 8A. S02 record schema (successor revision)

This successor revision fixes the full S02 record field lists (D658) on
top of the S01 discipline (§8). Status stays `[bounded]`; no Rust type
is minted here and the exact Rust identifiers remain S02's choice. The
S01 surfaces named below (`ReaderProjection`, `ReaderRecordIndex`,
`SegmentOrigin`, `ReaderViewKind`, `LocalSpan`, `ReaderFragmentSpan`,
`SourceMapping`, `MappingRefusalKind`, `TypedMember`, `TypeDerivation`,
`AnchorDiagnostic`, `LinkedMember`, `LinkDerivation`, `LinkDiagnostic`,
`LinkedRelationKind`, `ClassifiedMember`, `GraphClass`, `IdentityKey`,
`ClassificationDiagnostic`, `DocumentVersionRef`, `ReaderViewKind::is_primary`)
exist in `crates/ln-decode/src` (T01 grep audit). The S02-local names
`AnalysisBlockLayout`, `AnalysisRefusalKind`,
`render_npa_analysis`, `export_npa_analysis`,
`inspect_npa_analysis_wire` and `AnalysisEnvelopeSummary` are introduced
by S02 and do not exist in S01.

### 8A.1 Family set and line kinds

S02 emits exactly six record families. `family` is the record-line
discriminator; manifest/policies/footer keep `kind` (§8.1).

| family | `family` token | per-line `schema` | cardinality |
|---|---|---|---|
| document | `document` | `law-nexus/npa-analysis-document/v1` | exactly one |
| fragment | `fragment` | `law-nexus/npa-analysis-fragment/v1` | one per referenced fragment |
| member | `member` | `law-nexus/npa-analysis-member/v1` | zero or more |
| relation | `relation` | `law-nexus/npa-analysis-relation/v1` | zero or more |
| classification | `classification` | `law-nexus/npa-analysis-classification/v1` | zero or more |
| diagnostic | `diagnostic` | `law-nexus/npa-analysis-diagnostic/v1` | zero or more |

Manifest line 0 carries `kind = "npa_analysis_manifest"`, policies line 1
`kind = "npa_analysis_policies"`, the last line
`kind = "npa_analysis_footer"` (§8.1). The `context` family is deferred
to S03 (D658) and realized as an opt-in seventh family in §8B (D662).
`[bounded]`

### 8A.2 Span object (closed)

Every source reference on the wire is a fragment-qualified half-open
UTF-8 byte span:

```json
{"end":13,"fragment":"t7","start":6}
```

`fragment` is a `reader_contract::FragmentRef` id (`tN`) pinned in the
parent; `start`/`end` are half-open byte offsets into that fragment's
decoded text. A raw `npa_anchor::LocalSpan` (`{block,start,end}`) is
never serialized; it is localized to one fragment first (§8A.3). A
`block` index, a character offset, a line offset and an artifact byte
range are invalid (§5.3).

### 8A.3 Block binding (D657)

`[bounded]` An analysis **block** is one reader primary view
(`ReaderViewKind::Paragraph` or `ReaderViewKind::Residual`, the
`reader-view-contract.md` primary set) in document order; `block` is the
sequential index over non-empty primary views. Navigation views
(`Table`, `Row`, `Cell`, `Note`) are not analysis blocks; the existing
`ReaderViewKind::is_primary` predicate selects the two primary kinds.

`[bounded]` For one block, its ordered **source-fragment segments**
(`SegmentOrigin::SourceFragment`, in `ProjectedView::segment_refs`
order) are concatenated into `block_text`; `SegmentOrigin::Derived`
segments are excluded. The decoded fragment text is read from
`reader_contract::ReaderRecordIndex`
(`ReaderRecordIndex::new(package.records())`), never from a literal.

`AnalysisBlockLayout` is the ordered list of segment entries
`(fragment_ref, block_start, block_end, fragment_start, fragment_end)`;
`block_start`/`block_end` are the segment's half-open offsets in
`block_text`, `fragment_start`/`fragment_end` its offsets in the
fragment. Localizing a `LocalSpan {block,start,end}` is closed:

1. `unmapped_block` — `block` is absent from the layout;
2. `invalid_span` — `start >= end`, or a bound splits a code point;
3. `out_of_bounds` — `[start,end)` leaves `[0, block_text.len())`;
4. `cross_fragment` — `[start,end)` is not inside one segment's
   `[block_start,block_end)`. A span straddling two fragments is a closed
   refusal — never rebased onto one fragment, never silently promoted.

A localized span maps to `ReaderFragmentSpan::new(fragment,
fragment_start + (start - block_start), fragment_start + (end -
block_start))`, then resolves through
`SourceMapping::resolve_fragment_span` and must reproduce
`&block_text[start..end]` via `SourceMapping::slice`. A seam
`MappingRefusalKind` is surfaced with its own stable token.

Closed record refusal vocabulary:

- `AnalysisRefusalKind` (S02-local): `cross_fragment`,
  `unmapped_block`, `invalid_span`, `out_of_bounds`, `limit_reached`;
- any `analysis_source_mapping::MappingRefusalKind` token:
  `empty_or_inverted`, `out_of_bounds`, `not_char_boundary`,
  `unknown_fragment`, `cross_document`, `source_identity_mismatch`,
  `document_version_mismatch`, `token_view_mismatch`,
  `unsupported_mapping`, `envelope_structural`,
  `temporal_field_forbidden`, `corpus_transfer_forbidden`.

A record whose span cannot be localized carries its refusal token
instead of a span; refusal kinds are never dropped and never converted
to success.

### 8A.4 Manifest fields

`kind`, `schema` (`law-nexus/npa-analysis-manifest/v1`), `model`
(`law-nexus/npa-analysis-model/v1`), `profile`
(`npa_analysis_wordml/v1`), `version` (`1`), `capability`
(`npa_analysis_jsonl`), `generator`
(`{name: "ln-decode.npa_analysis_wire", version}`), `source`
(`{sha256, bytes}`, copied from the parent manifest), `parent`
(`{schema, records_seal_hash, manifest_hash}`), `document_version_ref`,
`source_revision`, `decoder_profile`, `limits`
(`{max_line_bytes, max_records}`), `non_authoritative: true`.

The reused shape predicate is
`analysis_source_mapping::check_envelope_shape`; the two optional parent
seals are `null` for an unsealed parent (§4.1).

### 8A.5 Policies fields

`kind`, `schema` (`law-nexus/npa-analysis-policies/v1`), `counts_scope`
(`integrity_not_coverage`), `semantic_scope` (`not_legal_gold`),
`temporal_scope` (`identity_and_coordinates_only`), `promotion`
(`none`), `authenticity` (`integrity_only_not_authenticity`),
`corpus_transfer` (`no_restricted_corpus`), `non_authoritative: true`.

### 8A.6 Footer fields

`kind`, `schema` (`law-nexus/npa-analysis-footer/v1`), `completion`
(`complete` | `incomplete`), `completion_basis`, `incomplete_reasons`
(empty iff complete; otherwise non-empty and containing the basis),
`counts` (`{documents, fragments, members, relations, classifications,
diagnostics, records}`), `records_seal_hash`, `manifest_hash`.

Closed completion bases/reasons: `bounded_analysis_complete` (complete)
and, for an honest partial, `hold`, `text_only`, `refused_record`,
`limit_reached`, `caller_scope`, `unsupported_source`. A refused
analytical record (a non-dropped refusal in the record stream) forces
`incomplete` with basis `refused_record`; a limit or scope partial is
never presented as complete. S03 extends this closed set with
`context_incomplete` and, only when context records are present, a
`contexts` count (§8B.1, §8B.3).

Seals are non-cyclic and recomputable, mirroring `cleaned_wire`:
`records_seal_hash = sha256(bytes(policies_line) || bytes(record_line_0)
|| … || bytes(record_line_k))` over the emitted record lines, and
`manifest_hash = sha256(bytes(manifest_line) || "\n" ||
records_seal_hash || "\n" || footer_body)`, where `footer_body` excludes
the two seal fields.

### 8A.7 Record families

Common to all record lines: `family`, `schema`, `ref` (stable
family-local id). Cross-references use `ref`.

**document** (one) — `family`, `schema`, `ref: "doc"`,
`document_version_ref`, `source_revision`, `decoder_profile`,
`source_sha256`, `projection_content_hash` (nullable; the reader
projection `content_hash`), `blocks`, `primary_views`.

**fragment** (one per referenced fragment) — `family`, `schema`, `ref`
(`tN`), `fragment_ref`, `byte_length`, `content_sha256` (sha256 of the
fragment's decoded UTF-8 bytes). No inline decoded text (§8.4).

**member** — one family, two closed `stage`s (D658):

| stage | fields |
|---|---|
| `typed` | `ref` (`mt:<index>`), `typed_index`, `date`, `number`, `type_name`, `approved_by`, `derivation` (`written_here`\|`unresolved`), `unresolved` (bool), `span`, `type_evidence` (span\|null), `alternatives` (`[{canon, span}]`, `npa_typed::TypeHypothesis` order) |
| `linked` | `ref` (`ml:<member_id>`), `member_id` (`npa_link::LinkedMember.id`), `kind` (`npa_link::LinkedMemberKind`), `derivation` (`npa_link::LinkDerivation`), `alias` (string\|null), `approved_by` (string\|null), `evidence`, `provenance` (array of spans, discovery order) |

Typed records are emitted for every `npa_typed::TypedMember`; linked
records for every `npa_link::LinkedMember`. Typed provenance
(`unresolved`, `alternatives`, `type_evidence`) is preserved even when a
linked record exists for the same anchor.

**relation** — `family`, `schema`, `ref` (`r:<index>`), `kind`
(`npa_link::LinkedRelationKind`), `from`, `to` (`LinkedMember.id`),
`evidence` (array of spans, never one cross-block span), `why`
(producer rule token).

**classification** — `family`, `schema`, `ref` (`c:<member_id>`),
`member_id` (`LinkedMember.id`), `graph` (`npa_classify::GraphClass`),
`legal_class` (`npa_classify::LegalClass`), `competence`
(`npa_classify::Competence`), `identity_key`
(`npa_classify::IdentityKey`), `evidence`, `why` (producer rule token).
The document-scoped record carries the `ClassifiedMember` axes
(A/B/C/identity); the full `ClassificationRow` axes D–H
(`geo`/`issuer`/`normativity`/`binding`/`admin`) stay out of this
envelope revision.

**diagnostic** — `family`, `schema`, `ref` (`d:<index>`), `stage`
(`anchor` | `link` | `classification`), `kind` (closed token, §8A.8),
`refs` (`[{family, ref}]`), `span` (span | null), `rule` (producer
token), `reject_reason` (`inbound` | `minjust` | `date_overlap` |
null), `block` (usize | null).

Provenance rule: a diagnostic that has no producer span carries
`span: null` and a non-empty `refs` naming the member/relation/fragment
it concerns plus the producing `rule`; a diagnostic is never emitted
without provenance and is never swallowed.

### 8A.8 Outcome to wire tokens

| Rust surface | wire field | closed tokens |
|---|---|---|
| `npa_typed::TypeDerivation` | member.derivation (`typed`) | `written_here`, `unresolved` |
| `npa_anchor::AnchorDiagnostic` | diagnostic.kind (`stage=anchor`) | `invalid_span`, `rejected_anchor`, `duplicate_occurrence` |
| `npa_anchor::RejectReason` | diagnostic.reject_reason | `inbound`, `minjust`, `date_overlap` |
| `npa_link::LinkedMemberKind` | member.kind (`linked`) | `anchored`, `named_type` |
| `npa_link::LinkDerivation` | member.derivation (`linked`) | `typed_anchor`, `document_head`, `approved_by_quote`, `scoped_alias`, `this_document_ref`, `series_continuation`, `named_type_text`, `refused` |
| `npa_link::LinkedRelationKind` | relation.kind | `continues_series`, `approved_by`, `scoped_alias`, `this_document_ref`, `head_family_carry` |
| `npa_link::LinkDiagnostic` | diagnostic.kind (`stage=link`) | `open_series_without_head`, `incompatible_series_head`, `type_not_inherited`, `head_family_carry_refused`, `alias_without_declaration`, `head_unavailable` |
| `npa_classify::GraphClass` | classification.graph | `identifying_act`, `hold`, `overlay`, `refuse` |
| `npa_classify::LegalClass` | classification.legal_class | `npa`, `individual_legal_act`, `clarification_letter`, `judicial_act`, `primary_instrument`, `unknown` |
| `npa_classify::Competence` | classification.competence | `international`, `federal`, `subject`, `municipal`, `not_applicable`, `unknown` |
| `npa_classify::IdentityKey` | classification.identity_key | `federal`, `presidential_agency`, `regional_municipal`, `do_not_project`, `overlay_not_rank`, `deferred-undefined`, `hold` |
| `npa_classify::ClassificationDiagnostic` | diagnostic.kind (`stage=classification`) | `span_invalid`, `type_missing`, `unknown_kind` |
| `analysis_source_mapping::MappingRefusalKind` | record.refusal | `empty_or_inverted`, `out_of_bounds`, `not_char_boundary`, `unknown_fragment`, `cross_document`, `source_identity_mismatch`, `document_version_mismatch`, `token_view_mismatch`, `unsupported_mapping`, `envelope_structural`, `temporal_field_forbidden`, `corpus_transfer_forbidden` |

The S02 outcomes (typing/linking/classification) are not token-view
derived, so the six families carry no `view` field; the S03 `context`
record declares `view` per §6 rule 1 (nullable, §8B.2).
Document-context outcomes (`ContextStatus`, `ContextClaimStatus`,
`DerivationRelation`, `ContextDiagnostic`) stay out of S02 (D658) and
enter only through the opt-in S03 `context` family (D662).

### 8A.9 Limits, rendering and structural inspect

`AnalysisLimits {max_line_bytes, max_records}` is validated **before**
any byte is written: a line over `max_line_bytes` or a record count over
`max_records` is refused (`limit_reached`) and no partial envelope is
produced. `AnalysisLimits` defaults and the manifest `limits` object
stay consistent.

`render_npa_analysis` writes compact sorted-key one-line JSON with a
single trailing LF and no embedded newline; `export_npa_analysis`
self-checks the rendered structure. `inspect_npa_analysis_wire(text) ->
AnalysisEnvelopeSummary` is structure-only: it reports `families`
(count per family), `records`, `completion`, `completion_basis`,
`incomplete_reasons` and the presence of `records_seal_hash` /
`manifest_hash`. It does not reconstruct records and does not recompute
seals. `check_envelope_shape` (§8A.3) rejects a structural break;
`check_no_corpus_transfer` and `check_temporal_fields` reject an inline
text channel and a temporal stop-sign field.

## 8B. S03 context family, read-back and independent verifier (successor revision)

`[bounded]` This successor revision fixes the S03 additions (D661/D662/
D663) on top of the S01 discipline (§8) and the S02 six-family envelope
(§8A). Status stays `[bounded]`; no Rust type is minted here and the
exact Rust identifiers remain S03's choice. The S01/S02 surfaces named
below exist in `crates/ln-decode/src` (T01 grep audit):
`AnalysisBlockLayout`, `LocalSpan`, `SourceMapping`,
`MappingRefusalKind`, `ReaderRecordIndex`, `ReaderProjection`,
`DocumentVersionRef`, `ContextStatus`, `ContextClaimStatus`,
`DerivationRelation`, `ContextDiagnostic`, `ContextRequestKind`,
`ContextRequest`, `ContextWorklist`,
`build_document_structure_index`, `build_document_analysis_overlay`,
`extract_act_list_frames`, `extract_structural_frames`,
`capture_lawrefs`, `find_legal_markers`, `recompute_analysis_seals`,
`analyze_document`, `render_npa_analysis`,
`inspect_npa_analysis_wire`. The S03-local names `ContextRecord`,
`ContextClaimRecord`, `ContextDerivationRecord`, `build_context_records`,
`render_npa_analysis_with_context`, `read_back_npa_analysis`,
`AnalysisReadback`, `verify_npa_analysis_wire`, `AnalysisVerifyCode` and
`AnalysisVerifyFinding` are introduced by S03 and do not exist in S02.

### 8B.1 Family set and opt-in

S03 adds the seventh `context` family over the S02 envelope. The family
is **opt-in** (D662): `render_npa_analysis_with_context(request,
contexts)` renders it, while `render_npa_analysis(request)` delegates
with an empty slice and stays the byte-identical S02 six-family
envelope.

| family | `family` token | per-line `schema` | line `kind` | cardinality |
|---|---|---|---|---|
| context | `context` | `law-nexus/npa-analysis-context/v1` | `result` \| `run` | zero or more |

Rules:

1. With an empty `contexts` slice, no `context` record line and no
   `contexts` key in the footer `counts` are emitted; the rendered bytes
   equal the S02 envelope, regression-pinned by the S02 receipt.
2. With at least one context record, the footer `counts` gains the
   `contexts` key; the six S02 counts are unchanged.
3. `FAMILIES` admits the seventh family token so structural inspect
   (`inspect_npa_analysis_wire`) accepts context lines; admission is not
   emission.
4. A context line with an unknown `kind` is a structural refusal
   (`UnknownKind`), never dropped silently. `[bounded]`

### 8B.2 Context tokens, nullable view and anchors

Common to every context line: `family: "context"`, `schema`, `kind`
(`result` | `run`), `ref` (stable family-local id).

**`kind: "result"`** — one context result derived from one
`ContextWorklist` request:

- `request_ref` — the request identity (`ContextRequest`);
- `request_kind` — closed `ContextRequestKind` token: `ancestor_path`,
  `adjacent_blocks`, `open_series_head`, `scoped_alias`,
  `current_document_requisites`, `explicit_anchor_lookup`;
- `view` — nullable closed token per §6 rule 1: `covering` for the
  token-derived request kinds `open_series_head`, `scoped_alias`,
  `current_document_requisites`, `explicit_anchor_lookup`; `null` for
  the structural request kinds `ancestor_path`, `adjacent_blocks`
  (no token-derived outcome);
- `status` — closed `ContextStatus` token: `resolved`, `partial`,
  `conflicting`, `unavailable`, `cycle`, `limit`;
- `claims` — zero or more context claim records, each carrying `field`,
  `claim_status` (closed `ContextClaimStatus`: `explicit`, `inherited`,
  `conflicting`, `unresolved`), `derivation` (closed `DerivationRelation`:
  `derived_from`, `supports`), `source_node_ref`, and a localized
  `anchor` (span or closed refusal);
- `derivations` — zero or more derivation edges, each carrying `from`,
  `to`, `relation` (`derived_from` | `supports`), `status` and a
  localized `anchor`;
- `diagnostics` — zero or more closed `ContextDiagnostic` tokens:
  `missing_document_structure`, `missing_current_requisites`,
  `open_series_without_head`, `incompatible_series_head`,
  `cross_block_continuation_ambiguous`, `scoped_alias_ambiguous`,
  `inherited_field_conflict`, `context_query_limit_reached`,
  `unresolved_after_document_pass`;
- `anchors` — the localized spans consumed by the result.

**`kind: "run"`** — exactly one aggregate line: `requests` (count),
`resolved`, `non_resolved`, per-status counts, the budget/limit outcome
and the aggregate `diagnostics`.

**Anchors (reuse §8A.3, never rebase).** A context anchor is a
block-relative `domain::TextSpan {start,end}` with no fragment id (§5).
Each anchor carries its analysis `block` index as provenance and is
localized through the same `AnalysisBlockLayout` as the S02 records:
`AnalysisBlockLayout::localize(LocalSpan {block,start,end})` →
fragment-qualified `SourceBoundSpan`, then
`SourceMapping::resolve_fragment_span` + `SourceMapping::slice`. A
context anchor is never serialized as a bare `TextSpan` (§5.3). A
localization failure is a closed refusal token from the §8A.3
vocabulary (`unmapped_block`, `invalid_span`, `out_of_bounds`,
`cross_fragment`, or a `MappingRefusalKind` token) carried in place of
the span; a context anchor is never dropped, never rebased and never
converted to success. `[bounded]`

### 8B.3 Completion basis `context_incomplete`

S03 extends the §8A.6 closed completion set with `context_incomplete`:

1. Any emitted context result whose `status != resolved` forces
   `completion = incomplete` with `completion_basis = context_incomplete`
   and a non-empty `incomplete_reasons` list drawn from the closed set
   `context_partial`, `context_conflicting`, `context_unavailable`,
   `context_cycle`, `context_limit` (one reason per distinct
   non-resolved status), plus the basis token itself.
2. `ContextStatus::Limit` is never presented as complete (P4).
3. Fixed precedence, highest first: `limit_reached` (S02 hard limit) >
   `refused_record` (S02 refused analytical record) > `context_incomplete`
   (non-resolved context) > the remaining S02 partial bases (`hold`,
   `text_only`, `caller_scope`, `unsupported_source`) >
   `bounded_analysis_complete`. A refusal is therefore never hidden
   behind a context partial.
4. `complete` is valid only when every emitted context result is
   `resolved` and no S02 refusal or limit applies. `[bounded]`

### 8B.4 Read-back and independent verifier admission

**Read-back.** `read_back_npa_analysis(text) -> Result<AnalysisReadback,
AnalysisWireError>` reconstructs all seven families (manifest, policies,
document, fragment, member, relation, classification, diagnostic,
context) into a typed model, failing closed on a structural break and
reusing `inspect_npa_analysis_wire` for the structural pass. Read-back
does not verify seals.

**Verifier.** `verify_npa_analysis_wire(text, projection: &ReaderProjection,
index: &ReaderRecordIndex, mapping: &SourceMapping) ->
Result<(), Vec<AnalysisVerifyFinding>>`:

1. structural pass (`check_envelope_shape`,
   `inspect_npa_analysis_wire`);
2. recompute both seals with `recompute_analysis_seals` and compare with
   the footer (a non-resealed tamper yields `seal_mismatch`);
3. compare the manifest identity (`source.sha256`, `source.bytes`, the
   `parent` schema and both parent seals, `document_version_ref`,
   `source_revision`, `decoder_profile`, `profile`, `model`) with the
   supplied pinned parent and the analysis frame constants: a resealed
   substitution is a `manifest_identity_mismatch`, never a seal pass —
   a recomputed seal is not identity proof (F01);
4. do not trust the artifact's records or seals: re-derive the canonical
   records from the pinned parent via
   `analyze_document(projection, index, mapping)` and
   `build_context_records(&layout, mapping)`;
5. re-hash every fragment record's decoded bytes against
   `ReaderRecordIndex` (`fragment_hash_mismatch`);
6. re-resolve every span through `SourceMapping::resolve_fragment_span` /
   `SourceMapping::slice` and require the exact substrate slice
   (`span_slice_mismatch`);
7. compare each record's semantic fields (source refs, relations,
   classification `member_id`, context status/view/claims/derivations)
   with the canonical re-derivation (`source_ref_substitution`,
   `relation_substitution`, `context_outcome_mismatch`; a substituted
   `document` record is a `manifest_identity_mismatch`);
8. require every relation `from`/`to` and classification `member_id` to
   name a readback record (`relation_ref_missing`, `member_ref_missing`);
9. check `completion`/`completion_basis`/`incomplete_reasons` against the
   re-derived records (`completion_mismatch`).

`build_projection` is not called; the artifact's own seals are never
accepted as a pass. A valid envelope returns `Ok(())`; otherwise the
verifier returns `Err(findings)` with at least one finding.

Closed `AnalysisVerifyCode`:

| code | detected condition |
|---|---|
| `envelope_structural` | missing/misordered manifest/policies/footer, CR, empty line, unknown kind/family |
| `seal_mismatch` | footer seals differ from the `recompute_analysis_seals` result (non-resealed tamper) |
| `manifest_identity_mismatch` | a manifest or `document` record identity field (`source`/`parent`/document-version triple/`profile`/`model`) differs from the pinned parent, including a resealed substitution |
| `fragment_hash_mismatch` | `fragment.content_sha256` differs from `ReaderRecordIndex` |
| `span_slice_mismatch` | a span does not resolve to its exact substrate slice |
| `source_ref_substitution` | a source ref differs from the canonical re-derivation (including a resealed in-fragment span move) |
| `relation_ref_missing` | a relation `from`/`to` names no readback record |
| `relation_substitution` | a relation `from`/`to`/`kind` differs from the canonical re-derivation |
| `member_ref_missing` | a classification `member_id` names no readback member |
| `context_outcome_mismatch` | a context status/view/claim/derivation differs from the canonical re-derivation |
| `completion_mismatch` | `completion`/`completion_basis`/`incomplete_reasons` inconsistent with the re-derived records |

**Resealed substitution.** Mutating a source span within one fragment, a
relation target, a fragment `content_sha256`, a context `status`, a
manifest `source`/`parent`/document-version/`profile`/`model` identity
field, or deleting a record, then recomputing and patching the footer
seals, must still yield the specific closed code above, because the
verifier re-derives from the pinned parent instead of trusting the
artifact. A recomputed seal is not identity proof: a substituted manifest
identity is `manifest_identity_mismatch`, never a clean pass. `[bounded]`

### 8B.5 Context substrate reuse (D661)

The context records derive from the existing document-context path, not
a second coordinate system: for each `AnalysisBlock` a synthetic
`ParsedBlock` is fed to the unchanged
`build_document_structure_index` → `build_document_analysis_overlay` →
`ContextWorklist::new(Default::default()).run(...)` chain, and each
resulting `SourceBlockNode.local_anchor()` `TextSpan` is localized
through the same `AnalysisBlockLayout` as §8B.2. `document_context` and
`npa_context_baseline` are not rewritten, and the synthetic
`SourceLocation` is never serialized to the wire. `[bounded]`

## 9. Temporal scope (stop-signs)

This contract fixes identity and coordinates only.

- No temporal type, clock role, force status, membership, effect or
  applicability is minted or assigned.
- `edition_date`, `effective_from`/`effective_to`, `TextChangeEvent`,
  `NormativeEffectEvent`, `ComponentMembershipVersion`, `NormRule`,
  `Condition`, `LegalEffect`, `Exception`/`Defeater`,
  `ApplicabilitySelector`, `LegalList` and the other
  `deferred-undefined` glossary rows remain **stop-signs**; they must
  not be inferred from lexical evidence or from this contract.
- ADR-0016..0022 stay `[proposed]`; ADR-0009 five-clock roles are not
  assigned here.
- The former M214 temporal plan is preserved in `214-RESEARCH.md` and
  deferred pending reconciliation with parked `M208-wrz6fg`. It is not
  resumed, restated or superseded here, and no competing temporal
  milestone is created.

## 10. Downstream admission criteria (S02–S04)

A record may enter the document-scoped analysis output only when all
hold:

1. the envelope pins a verified parent and the record's fragment
   resolves inside it (§4.1, §4.3);
2. the span validates as half-open UTF-8 (§5);
3. the outcome is a closed typed value, never a bare `None` (§7.1);
4. the token view is declared and matches the producer (§6);
5. the record's document version triple equals the envelope's (§4.2).

Additional gates:

- S02 records obey §8A: fragment-qualified spans only, a `cross_fragment`
  refusal for a straddling span, closed outcome tokens, no inline decoded
  text, no temporal field and an honest `incomplete` at a refusal or limit.
- S02 must not claim full analysis/context export or semantic gold and
  must not auto-close R1000.
- S03 adds the opt-in `context` family and the read-back/verifier
  admission (§8B). A context record enters only with a localized
  fragment-qualified anchor (or a closed refusal) and a declared nullable
  `view`; any non-resolved `ContextStatus` forces `completion=incomplete`
  with basis `context_incomplete`. `read_back_npa_analysis` reconstructs
  all seven families and `verify_npa_analysis_wire` recomputes from the
  pinned parent, does not trust the artifact seals (D634 pattern), and
  returns a closed `AnalysisVerifyCode`; a resealed substitution of
  source refs, relations or context outcomes must be detected.
- S04 acceptance must keep structural integrity, semantic correctness
  and corpus breadth separate (M214 success criteria).
- Frozen oracles and the M213 cleaned wire bytes are not modified.

## 11. Positive examples (normative)

**P1 — valid span resolves to the original UTF-8 slice.**
Pinned parent has fragment `t7 = "см. ст. 5"` (13 UTF-8 bytes).
Coordinate `{fragment: t7, start: 6, end: 13}` is half-open valid
(6 and 13 are code-point boundaries; 13 == byte length) and resolves
to the exact slice `"ст. 5"`.

**P2 — token views stay separate.**
On the same fragment, `lex()` mints one `Abbrev{st}` (never a `Word`);
`tokenize()` yields the alphabetic stem `ст`; `words_from_covering()`
yields no word for `ст`. A LawRef record declaring `view=covering`, a
reference record declaring `view=alphabetic` and a morphology record
declaring `view=covering_word` are all valid; each keeps its own
half-open span.

**P3 — explicit refusal is a valid outcome.**
A member with no surviving TYPE is admitted as `TypeDerivation::
Unresolved` with `unresolved=true` and its evidence span — not dropped
and not promoted. A classification row may lawfully be
`GraphClass::Refuse` with `IdentityKey::Hold`.

**P4 — context limit is observable.**
A context request that exceeds `worklist_steps` terminates as
`ContextStatus::Limit` with `ContextDiagnostic::ContextQueryLimitReached`;
no partial result is presented as complete. Context records are the
opt-in seventh S03 family (§8B.2) and force `context_incomplete`.

**P5 — block binding produces fragment-qualified spans.**
A primary paragraph view whose ordered source-fragment segments are
`t7 = "см. "` and `t8 = "ст. 5"` yields `block_text = "см. ст. 5"` and a
layout `[(t7,0,6,0,6), (t8,6,13,0,7)]`. A typed member span
`{block:0,start:6,end:13}` localizes to `{fragment:t8,start:0,end:7}` and
resolves to `"ст. 5"`, the exact UTF-8 slice.

**P6 — a diagnostic without its own span keeps provenance.**
`LinkDiagnostic::OpenSeriesWithoutHead` is emitted as a `diagnostic`
record with `span: null`, `kind: "open_series_without_head"`, `rule`
naming the `npa_link` pass and `refs` naming the affected member or
relation — provenance survives the missing span.

## 12. Hostile examples (normative)

| # | Input | Expected refusal |
|---|---|---|
| H1 | span `{start: 7, end: 6}` | `EmptyOrInverted` |
| H2 | span `{start: 0, end: 14}` on 13-byte fragment | `OutOfBounds` |
| H3 | span `{start: 7, end: 8}` where 7 splits `с` | `NotCharBoundary` |
| H4 | `fragment_ref = t999` absent from the pinned parent | `UnknownFragment` |
| H5 | fragment `t7` from document B in an envelope pinned to document A's `source.sha256` | `CrossDocument` |
| H6 | record cites a parent with `source.sha256` different from the envelope's | `SourceIdentityMismatch` |
| H7 | morphology outcome declaring `view=alphabetic` (or any cross-view substitution) | `TokenViewMismatch` |
| H8 | record's `decoder_profile`/`source_revision` differs from the envelope's document-version triple | `DocumentVersionMismatch` |
| H9 | envelope claims a non-null parent seal while the parent is unsealed | `SourceIdentityMismatch` |
| H10 | missing footer / trailing record after footer / embedded CR / misordered manifest | envelope-structural refusal |
| H11 | record carrying an `edition_date`/`effective_from` field | temporal-field-forbidden (§9) |
| H12 | envelope containing raw full-corpus evidence text as a second source | corpus-transfer-forbidden (§8.4) |
| H13 | span straddling two source-fragment segments of one block | `cross_fragment` (never rebased) |
| H14 | `LocalSpan.block` absent from the analysis layout | `unmapped_block` |
| H15 | line over `max_line_bytes`, or record count over `max_records` | `limit_reached` before any byte is written |
| H16 | a refused analytical record presented as `completion: complete` | `refused_record`; a silent complete is invalid |
| H17 | resealed (recompute + footer patch) in-fragment span move of a source ref | `source_ref_substitution` |
| H18 | resealed relation `from`/`to`/`kind` substitution | `relation_substitution` |
| H19 | resealed `ContextStatus` other than `resolved` presented with `completion: complete` | `context_outcome_mismatch` / `completion_mismatch` |
| H20 | a context anchor that leaves its block or straddles two fragments | `out_of_bounds` / `cross_fragment` (never rebased) |
| H21 | resealed manifest `source.sha256`/`source.bytes`, `parent` schema/seals, `source_revision`, `document_version_ref`, `decoder_profile`, `profile` or `model` substitution | `manifest_identity_mismatch` (never a `seal_mismatch` pass) |
| H22 | resealed `document` record identity (`source_sha256`/document-version triple) contradicting the pinned parent | `manifest_identity_mismatch` |

## 13. Remainder reconciliation

- **M208-wrz6fg** remains parked. It is not resumed or reformulated
  here and needs a separate decision. The pre-M214 temporal plan stays
  in `214-RESEARCH.md`.
- **R1000** stays active/unclosed. M213 closed the delivered
  wire/read-back/verifier/nav/Hold/TextOnly remainder, but corpus-wide
  acceptance was never claimed and display-cleaning remains remaining
  (D638). M214 S01 opens a new **consumption** of the cleaned/source
  projection; it must not auto-close R1000. Re-test set:
  `cleaned_projection_verify`, `npa_document_context_contract` +
  `_hostile_contract`, `npa_link_pipeline_integration`, plus the new
  `analysis_source_mapping_*` suites and `cargo fmt`/`clippy`/`check`.
- **D638** wording is extended additively by this slice: M214 consumes
  the cleaned projection and repeats "do not auto-close R1000".
- **D650** binds M214 to the temporal plan (R074/R034/…). That
  executive priority was replaced by **D651**; M214 is not bound to
  R074. The stale M214 requirement identity in D650 is recorded here
  and its supersession is a decision-store action owned outside this
  unit.
- **D651** is confirmed: M215–M220 stay parked; auto/wakeup stay
  stopped; M214 S01–S04 only.
- **S04 outcome (this revision):** S04 ran the pinned provider + work-family
  stratified sample (N=400, seed 20308) through the S01–S03 pipeline and
  produced the separated acceptance report
  (`m214-s04-corpus-acceptance.json`, `verdict=pass`, 400/400 verified, no
  limits, tamper 12/12) plus the durable count/hash-only battery. The
  semantic section stays structural-only (`semantic_reference_status=absent`,
  `promotion=false`); D667 and D668 are confirmed unchanged. S04 does not
  close R1000, does not resume M208 and does not start M215–M220. The
  remainder and non-claims are reconciled in
  `prd/migration/rust-evidence/m214-s04-horizon-reassessment.md`.
- **Requirement binding (D655/D656):** M214 has no DB requirement
  binding (the requirements projection returns no rows for M214). D656
  records the intended binding: **R1000 primary, supporting-only,
  active/unclosed**; R081/R069/R077/R063/R038/R071 supporting-only;
  R080 a supporting classification touch. Nothing is auto-closed and no
  class-matched validation is claimed. The requirements-store write
  (`supporting_slices`/`notes`) remains a carry-forward for a unit that
  holds the requirement tool; the execute-task lane is hard-blocked from
  it (D092). `[bounded]`
- **S02 handoff (from S01/T03):** the executable seam
  (`analysis_source_mapping.rs`), its contract/hostile/integration
  batteries and the count/hash receipt
  `prd/migration/rust-evidence/m214-s01-source-mapping.json` are the
  admitted S01 inputs. S02 must not re-derive coordinates or token views;
  it materializes records on top of the seam. The requirement binding is
  recorded in this revision (D656) and §8A fixes the S02 record schema;
  new suites are `npa_analysis_records_*`, `npa_analysis_wire_*` and
  `npa_analysis_export_integration`.

## 14. Verification surface (S01 + S02 + S03)

- **ADR conformance:** `uv run python scripts/verify-adr-conformance.py`
  (default surface) and explicitly
  `uv run python scripts/verify-adr-conformance.py prd/architecture/npa-analysis-jsonl-contract.md`.
- **Independent contract review:** a reviewer subagent inspects this
  file against the cited ADRs/contracts and the actual Rust types;
  findings are addressed or recorded.
- **Recon (bounded, non-proof):** GitNexus `query`/`context` over the
  source/reader/cleaned and NPA/context modules; CBM project
  `law-nexus-decode-audit` `check_index_coverage` for the touched
  files (best-effort; "no recorded issue" is not completeness).
- **Integration battery (T03):**
  `crates/ln-decode/tests/analysis_source_mapping_integration.rs` drives the
  real `source_package::capture` → `reader_projection::build_projection`
  pipeline into the T02 seam on the approved reader fixtures and one
  declared real input (a tracked bounded Consultant WordML fixture, not the
  restricted corpus). The fragment catalog is built from the reader
  substrate, never from hand-copied text; every resolved span must equal the
  exact substrate UTF-8 slice; tamper, cross-document and Hold/TextOnly
  cases stay closed. Count/hash receipt:
  `prd/migration/rust-evidence/m214-s01-source-mapping.json`.
- **S01 re-test set:** `analysis_source_mapping_contract`,
  `analysis_source_mapping_hostile`, `analysis_source_mapping_integration`,
  `npa_document_context_contract`, `npa_document_context_hostile_contract`,
  `npa_link_pipeline_integration`, `cleaned_projection_verify`, plus
  `cargo fmt --all --check`, `cargo clippy --workspace --all-targets
  --offline -- -D warnings` and `cargo check --workspace --offline`.
- **S02 verification surface (§8A):** suites
  `npa_analysis_records_contract`, `npa_analysis_records_link_classify`,
  `npa_analysis_wire_contract`, `npa_analysis_wire_hostile`,
  `npa_analysis_export_integration`; structural inspect
  `inspect_npa_analysis_wire`; portable count/hash receipt
  `prd/migration/rust-evidence/m214-s02-analysis-export.json`; workspace
  gates `cargo fmt --all --check`, `cargo clippy --workspace
  --all-targets --offline -- -D warnings`, `cargo check --workspace
  --offline`.
  gates `cargo fmt --all --check`, `cargo clippy --workspace
  --all-targets --offline -- -D warnings`, `cargo check --workspace
  --offline`.
- **S03 verification surface (§8B):** suites
  `npa_analysis_context_contract`, `npa_analysis_wire_context`,
  `npa_analysis_verify_contract`, `npa_analysis_verify_hostile`,
  `npa_analysis_export_integration`; read-back `read_back_npa_analysis`;
  independent verifier `verify_npa_analysis_wire` with the closed
  `AnalysisVerifyCode`; portable count/hash receipt
  `prd/migration/rust-evidence/m214-s03-context-verify.json`; workspace
  gates as above.
- **Examples:** §11–§12 are normative and must stay consistent with the
  Rust enums they name.

## 15. S04 corpus acceptance contract (successor revision)

S04 runs the pinned provider + work-family stratified sample of the full
corpus through the S01–S03 pipeline and reports **separated** results. It
fixes three schemas and the closed vocabularies below. Nothing here is a
semantic oracle: the semantic section is structural-only (D667) and the
sample is provider + work-family stratified, not year/type stratified (D668).

### 15.1 Declared-before-run rule

The sample manifest records its thresholds **before** the acceptance run:
`sample_size`, `draw_seed`, the tamper-probe subset size and the resource
budget. The acceptance report copies them from the manifest. A manifest
without a `declared_thresholds` block is refused by `load`/`validate`, and a
threshold may not be inferred from observed results. Declared S04 thresholds:
`sample_size = 400`, `draw_seed = 20308`
(`corpus_sample::DEFAULT_DRAW_SEED`), `tamper_probe_entries = 12`,
`resource_budget_peak_bytes = 4 GiB`, `resource_budget_total_ms = 3600000`,
`min_verified_ratio_ppm = 990000`, `max_limit_events = 0`.

### 15.2 Schemas

| schema | artifact | contents |
|---|---|---|
| `law-nexus/npa-analysis-corpus-sample/v1` | `m214-s04-corpus-sample.json` | declared roots, thresholds, per-entry `relative_path`/`sha256`/`bytes`/`provider`/`document_type`/`work_family`, corpus snapshot sha256, leakage |
| `law-nexus/npa-analysis-corpus-acceptance/v1` | `m214-s04-corpus-acceptance.json` (+ per-entry JSONL) | separated sections, closed counters, declared-vs-observed, verdict |
| `law-nexus/npa-analysis-adjudication-packet/v1` | adjudication packet | text-free, count/hash-only index; `promotion=false`, `semantic_reference_status="absent"` |

### 15.3 Separated report sections (mandatory)

The acceptance report carries these top-level sections, never merged:

- `structural_integrity` — per-entry outcome counters, a `verify_codes`
  histogram, tamper-probe detected/false-negative, `structural_failures`,
  `pass`.
- `semantic_adjudication` — `semantic_reference_status` (`absent`),
  `promotion` (`false`), closed `AdjudicationStatus`, adjudication packet
  schema + sha256. Structural-only (D667); no C5 promotion.
- `limits` — closed `LimitKind` histogram and observed `within_threshold`.
- `resources` — `peak_memory_bytes` (`null` when unavailable, never silently
  zero), wall-time summary, declared budget and `within_budget`.
- `corpus_breadth` — bounded stratified sample counts, `coverage_claim`
  (`null`), `not_year_type_stratified=true`.
- `horizon` — `r1000_status=active`, `m208_status=parked`, display-cleaning
  and next-horizon status.
- `verdict` + `verdict_basis` — closed verdict computed by the declared rules
  below.

A structural failure, a promotion, or a semantic/breadth overclaim can never
yield `verdict=pass`.

### 15.4 Closed vocabularies

- `EntryOutcome`: `verified_ok`, `read_back_refused`, `verify_refused`,
  `decode_refused`, `gate_refused`, `analysis_refused`, `limit_line_bytes`,
  `limit_records`, `manifest_pin_mismatch`.
- `LimitKind`: `line_bytes`, `records`.
- `AdjudicationStatus`: `not_attempted`, `deferred`, `no_reference`.
- `Verdict`: `pass`, `needs_attention`, `fail`.
- `ProviderToken`: `consultant_export`, `garant`.
- `VerifyCode` (within `verify_refused{code}`): the closed
  `AnalysisVerifyCode` set of §8B.4 (`envelope_structural`, `seal_mismatch`,
  `fragment_hash_mismatch`, `span_slice_mismatch`, `source_ref_substitution`,
  `relation_ref_missing`, `relation_substitution`, `member_ref_missing`,
  `context_outcome_mismatch`, `completion_mismatch`).

An unknown token in any of these positions is a `load`/`validate` refusal.

### 15.5 Fail-closed loading

`npa_corpus_acceptance::{CorpusSampleManifest, AcceptanceReport,
AdjudicationPacket}` expose `load`/`validate`. `load` refuses: invalid JSON; a
missing thresholds block; unknown tokens; duplicate entries; `..` or
absolute paths; and any raw-text-bearing field. `validate` additionally
refuses internal inconsistency (counters that do not sum, a `pass` section
with structural failures, a promoted semantic section, a non-null
`coverage_claim`, a non-`active` R1000).

### 15.6 Non-claims

- the corpus sweep is **not** a semantic oracle; the semantic section is
  structural-only and `semantic_reference_status=absent`;
- no C5 promotion, no accuracy claim, no corpus-breadth/coverage claim;
- **R1000 stays active/unclosed**; M208-wrz6fg stays parked;
- count/hash only — no decoded corpus text enters tracked evidence.

## 16. Out of scope

Reader/cleaning/normalization changes, XML re-parse, tokenizer
rewrites, temporal/force/applicability/retrieval semantics, LLM
extraction, corpus-wide acceptance, and the end-to-end acceptance
report (S04). The `context` family, its
`ContextStatus`/`DerivationRelation` semantics, the JSONL read-back and
the independent verifier are fixed in §8B (S03) and are no longer out of
scope. S02's record schema is fixed in §8A. The M207 Python companion
format is not adopted as the Rust analysis format.

## 17. References

- ADR-0013 universal multi-source parser; ADR-0015 hexagonal
  verification; ADR-0028 typed lexer and dual tokenizer; ADR-0029
  requisites-anchored member assembly; ADR-0016 structural identity;
  ADR-0009 five-clock safety contract.
- `prd/architecture/source-jsonl-contract.md`,
  `prd/architecture/reader-view-contract.md`,
  `prd/architecture/reader-projection-contract.md`,
  `prd/architecture/cleaned-projection-contract.md`,
  `prd/architecture/npa-document-context.yaml`,
  `prd/annotation/m207-hybrid-records-contract.md`,
  `prd/temporal-legal-model.md` §3.
- `crates/ln-decode/src/npa_anchor.rs`, `npa_typed.rs`, `npa_link.rs`,
  `npa_classify.rs`, `lawref.rs`, `local_grammar.rs`, `morphology.rs`,
  `tokenizer.rs`, `reader_contract.rs`, `reader_projection.rs`,
  `reader_verifier.rs`, `cleaned_wire.rs`, `cleaned_verifier.rs`,
  `document_context.rs`, `npa_context_baseline.rs`,
  `source_package.rs`, `domain.rs`.
- `crates/ln-decode/src/analysis_source_mapping.rs` (S01 seam);
  `npa_analysis_records.rs` and `npa_analysis_wire.rs` (S02 record +
  envelope modules); `npa_context_records.rs` and
  `npa_analysis_verify.rs` (S03 context records + read-back/verifier
  modules).
- Decisions D655/D656 (M214 requirement binding), D657 (block binding),
  D658 (S02 envelope/family scope), D661 (reader-native context
  substrate), D662 (opt-in context family + `context_incomplete`), D663
  (read-back/verifier independence); receipts
  `prd/migration/rust-evidence/m214-s01-source-mapping.json`,
  `m214-s02-analysis-export.json` and `m214-s03-context-verify.json`.
- `prd/migration/rust-evidence/` (portable evidence; count/hash-only).
