# NPA source-to-analysis JSONL integration contract

**Status:** `[bounded]` design contract (no runtime in this task)
**Owning slice:** `M214-es3jvw` / `S01` — T01 tracked contract;
executable seam and tests are S01/T02–T03, document output is S02
**Authority:** ADR-0013 (universal multi-source parser), ADR-0015
(hexagonal verification architecture), ADR-0028 (typed lexer / dual
tokenizer), ADR-0029 (requisites-anchored member assembly — anchor
boundary), ADR-0016 (structural legal identity), ADR-0009 (five-clock
safety contract); decisions D603 (anchor coordinates), D628/D631
(reader coordinate base), D633/D634 (reader seal + independent
verifier), D638 (R1000 remainder under M213), D640 (cleaned JSONL
envelope), D650/D651 (horizon correction)
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

S02 fixes the full record field lists in a successor revision of this
file; S01 fixes the discipline and the mandatory identity/coordinate/
outcome fields.

### 8.1 Layout

LF-delimited JSONL, exactly one trailing LF:

```text
line 0        manifest   kind = "npa_analysis_manifest"
line 1        policies   kind = "npa_analysis_policies"
lines 2..n-1  records    family in { document, fragment, member, relation,
                                     classification, context, diagnostic }
line n        footer     kind = "npa_analysis_footer"
```

Every line is one compact JSON object (fixed key order, no embedded
newline). Structural break (missing/misordered manifest/policies/
footer, empty interior line, CR, trailing record) is a closed typed
refusal, never a silent success.

### 8.2 Manifest (mandatory identity)

`source`, `parent`, `document_version_ref`, `source_revision`,
`decoder_profile`, `profile`, `version`, `generator`,
`non_authoritative: true`, `limits`.

### 8.3 Policies (mandatory non-claims)

`counts_scope: integrity_not_coverage`,
`semantic_scope: not_legal_gold`,
`temporal_scope: identity_and_coordinates_only`,
`promotion: none`,
`authenticity: integrity_only_not_authenticity`,
`corpus_transfer: no_restricted_corpus`,
`non_authoritative: true`.

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
non-cyclic seals mirroring `source_package`/`cleaned_projection`.

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

- S02 must not claim full analysis/context export or semantic gold and
  must not auto-close R1000.
- S03's read-back/verifier must recompute from the pinned parent and
  must not trust the analysis seals (D634 pattern); the resealed
  semantic-tamper battery must detect substituted source refs and
  relations.
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
no partial result is presented as complete.

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
- **Requirement binding gap:** M214 has no DB requirement binding
  (the requirements projection returns no rows for M214). The S02+
  planner must record the binding through the sanctioned requirements
  path before S02 begins: R1000 primary; R081/R069/R077/R063/R038/R071
  supporting-only; nothing auto-closed. This is a planning gate for
  S02, not a T01 blocker.

## 14. Verification surface (S01)

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
- **Examples:** §11–§12 are normative and must stay consistent with the
  Rust enums they name.

## 15. Out of scope

Reader/cleaning/normalization changes, XML re-parse, tokenizer
rewrites, temporal/force/applicability/retrieval semantics, LLM
extraction, corpus-wide acceptance, the full record schema (S02), the
read-back/verifier implementation (S03), and the end-to-end acceptance
report (S04). The M207 Python companion format is not adopted as the
Rust analysis format.

## 16. References

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
- `prd/migration/rust-evidence/` (portable evidence; count/hash-only).
