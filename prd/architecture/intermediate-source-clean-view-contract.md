# Intermediate-source clean-view and versioned-rule-profile contract

**Status:** `[bounded]`
**Owning slice:** M223-d2q075 / S05 — design pin for
`crates/ln-decode/src/reader_clean_view.rs` (`reader_clean_view`, T02); tests
`crates/ln-decode/tests/reader_clean_view.rs`; bounded real-corpus census
`scripts/m223_s05_real_class_census.py` + `scripts/test_m223_s05_real_class_census.py`
(T03); slice battery `scripts/test_m223_s05_contract.py` (T04)
**Upstream wire contracts (frozen, `[bounded]`):**
`prd/architecture/source-jsonl-contract.md`,
`prd/architecture/reader-view-contract.md`,
`prd/architecture/reader-projection-contract.md`,
`prd/architecture/cleaned-projection-contract.md`,
`prd/architecture/npa-analysis-jsonl-contract.md`
**Upstream acceptance contract:** `prd/architecture/intermediate-source-acceptance-contract.md`
(§3 source versus clean views, §4 reading order versus record order, §5
composite provenance, §8 whole-corpus acceptance boundary, §10 non-claims)
**Upstream slice contracts:** `prd/architecture/intermediate-source-reading-order-contract.md`
(S04 `reader_reading_order`), and `crates/ln-decode/src/reader_projection.rs`
(frozen reader projection producer)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0029 (requisites-anchored member
assembly — anchor boundary), D631 (S02 reader coordinate base), D633 (S03
reader content seal), D634 (independent verifier recomputes from the
substrate), D639/D640 (cleaned JSONL envelope and non-cyclic seals), D733
(S04 reading-order and composite-coordinate design pin), **D734 (this design
pin: clean-view model and versioned rule profile, additive-only)**, D602/D328
(serde stays module-scoped to `source_package`)
**Lifecycle ceiling:** this is a bounded design pin plus a read-only filtered
view over already-verified decoded source. It is **not** an R1000 closure
artifact, not a CST/AST, not a temporal `StructuralAst`, not normalization, and
not expert legal gold. It closes no requirement. R1000 stays active/unclosed.

## 1. Purpose and non-claims

### 1.1 Purpose

S03 delivered the frozen reader projection (view forest, ordered source-fragment
and derived segments, semantics, spans) and its independent verifier. S04
delivered `reader_reading_order`, which re-derives per-view reading order from
the substrate event walk and refuses a resealed reorder. Neither surface is a
**filtered view**: no layer separates primary text from service content, and no
versioned rule set declares what is primary, service, or dropped.

Acceptance contract §3 requires exactly that surface:

> the **future filtered / display / tokenizer view** (S05) is the artifact where
> primary text is separated from service content under **separately versioned**
> rules with an explicit source mapping. Only this future view may drop,
> reorder, or transform content, and only within its declared rule set.

S05 delivers that filtered view. The concrete surface this document fixes:

- **`reader_clean_view`** (T02): `CleanRuleProfile::v1()` — the versioned,
  closed rule profile `reader_clean_profile/v1`; `CleanDisposition`
  (`Primary` | `Service` | `Dropped`); `CleanUnit` (`Source` | `Derived` |
  `Dropped`) carrying provenance by one of the two acceptance-contract §5 forms;
  `CleanView::build(&ReaderProjection, &ReadingOrderIndex, &[Record])` and
  accessors `profile_id()`, `units()`, `primary_text()`, `service_text()`,
  `view_ids()`; fail-closed `CleanErrorKind::{UnknownView, NotPrimaryView,
  UnknownSegment, SpanInvalid, SourceMappingIncomplete}`.

### 1.2 Non-claims

- **Not** an R1000 closure artifact. It is one bounded filtered view feeding the
  wider R1000 program; closure is owned by M223 as a whole, not by S05.
- **Not** semantic or legal. Primary/service classification asserts *display
  role*, never legal authority, legal completeness, or citation resolution.
- **Not** normalization. The clean view preserves decoded bytes verbatim
  (including NBSP and astral code points); it does not fold, trim, or re-encode.
  Normalization is out of scope (acceptance contract §3, §10).
- **Not** authenticity. `content_hash` and the rule profile are integrity/version
  pins; a party controlling the bytes can recompute them.
- **Not** a lossless carrier and **not** a re-description of the cleaned
  envelope. The existing `cleaned_wire` envelope stays lossless
  (`full_decoded_text_retained_inline`, `source_content_retained_no_suppression`);
  its frozen policy must never be re-described as lossy by this contract. The
  clean view is a *separate* filtered layer.
- **Not** an XML re-parse. Every walk reads substrate records and the frozen
  reader projection only.
- **Not** whole-corpus materialization. S05 defines and proves the surface on
  real classes (tracked fixtures + bounded seeded census); whole-corpus
  materialization is S05–S07 evidence, not an S05 closure.
- Provider-bounded to Consultant WordML (`reader_wordml_profile/v1`).
- Read-only: the clean view never mutates, reseals, or re-bases the projection.

## 2. Source versus clean views boundary

Acceptance contract §3 fixes where the clean view sits. Three derived layers sit
over the same immutable decoded source, and each consumer names the layer it
reads:

| Layer | Module | May drop / reorder / transform? |
|---|---|---|
| Source package (decoded source) | `source_package` | no — preserves every decoded fragment with no exclusion |
| Reader projection (reading views) | `reader_projection` / `reader_contract` | no — ordered and lossless over fragments |
| Filtered clean view (this contract) | `reader_clean_view` | **yes** — only within the declared, versioned rule set |
| Cleaned projection (clean inline text) | `cleaned_wire` | no — lossless `full_decoded_text_retained_inline` |

The boundary is explicit:

1. **The clean view is the only layer that may drop, reorder, or transform
   content.** A consumer that drops or reorders at any other layer is a defect.
2. **Every retained unit resolves to its source by one of the two §5 provenance
   forms.** A clean view that loses the mapping is a defect, not a view.
3. **The `cleaned_wire` envelope stays lossless.** Its frozen policy is
   `full_decoded_text_retained_inline` and `source_content_retained_no_suppression`;
   this contract does not re-describe it as lossy and does not merge the two.
4. **No layer is a competing source of truth.** The clean view is a derived,
   non-authoritative projection over the decoded source; frozen generated JSONL
   (`prd/architecture/*.jsonl`) is never regenerated in place.

The acceptance rule, verbatim from §3, governed this design:

> A filtered view may drop, reorder, or transform content only within its
> declared, versioned rule set, and every retained unit must resolve to its
> source by one of the two provenance forms in §5. A filtered view that loses
> the mapping is a defect, not a view.

## 3. Versioned rule profile `reader_clean_profile/v1`

### 3.1 The profile is closed and total over the semantic vocabulary

`reader_clean_profile/v1` declares **exactly one disposition per
`ReaderSemantic` class** and is **total** over the closed seven-class
vocabulary (`crates/ln-decode/src/reader_contract.rs` `ReaderSemantic`). Each
class carries one stable rule id, one disposition, and a short justification.
A class with no declared disposition is not representable: profile construction
is a closed match, and the real-corpus census (T03) fails closed on an observed
class with no declared disposition.

Dispositions:

| Class | Rule id | Disposition | Justification |
|---|---|---|---|
| `body` | `rcv1_body` | `primary` | Main body text is the primary reading surface. |
| `whitespace` | `rcv1_whitespace` | `service` | Whitespace is structural/formatting, not primary text; kept as service so it is never silently lost. |
| `field_code` | `rcv1_field_code` | `service` | `instrText` field instructions are reader-service metadata, not displayed text. |
| `revision_insertion` | `rcv1_revision_insertion` | `primary` | Inserted text is current legal text and remains primary. |
| `revision_deletion` | `rcv1_revision_deletion` | `service` | Deleted text is retained as service; it is **not** discarded. |
| `derived_separator` | `rcv1_derived_separator` | `service` | A generated tab/line-break/page-break literal is boundary service, not primary text. |
| `empty` | `rcv1_empty` | `dropped` | An empty fragment carries no text; dropping it is declared and classified, and it still retains dropped-unit provenance. |

### 3.2 No revision class is discarded silently

This is a load-bearing invariant. Every revision class is classified, and no
revision class is treated as garbage:

- `revision_insertion` → `primary` (current text stays visible);
- `revision_deletion` → `service` (removed text stays addressable, not lost).

A `dropped` disposition applies only to `empty`; a revision class may never be
declared `dropped`. The census (T03) fails closed if a revision class is
observed and its declared disposition is `dropped`, and proves
`revision_insertion_observed` / `revision_deletion_observed` on real classes.

### 3.3 Machine-readable profile block

T02 declares the profile in code; T04 parses this block and fails on drift
between the block and the source declarations. Exactly one line per class:

```
<!-- clean-rule-profile:begin -->
profile:reader_clean_profile/v1
rule:rcv1_body class:body disposition:primary
rule:rcv1_whitespace class:whitespace disposition:service
rule:rcv1_field_code class:field_code disposition:service
rule:rcv1_revision_insertion class:revision_insertion disposition:primary
rule:rcv1_revision_deletion class:revision_deletion disposition:service
rule:rcv1_derived_separator class:derived_separator disposition:service
rule:rcv1_empty class:empty disposition:dropped
<!-- clean-rule-profile:end -->
```

## 4. Source mapping (acceptance contract §5)

No single identifier is sufficient provenance. Each **retained** clean unit (in
both `Primary` and `Service` dispositions) carries exactly one of two §5
provenance forms; a **dropped** unit carries a rule id and element coordinates
but no fabricated fragment.

### 4.1 Source-fragment unit (`CleanUnit::Source`)

For a `ReaderSegmentKind::Text` segment with `origin = source_fragment`:

```
fragment_ref  (tN)
  ⊕ slot        (text | tail)
  ⊕ span        ([start, end) over the fragment's decoded value)
  ⊕ element_ref (capture owner, eN)
  ⊕ source_pos  (owner element pre-order index)
```

The span is validated with `reader_contract::check_fragment_span` against the
decoded value; a non-char-boundary or out-of-bounds span is a typed
`SpanInvalid` refusal.

### 4.2 Derived unit (`CleanUnit::Derived`)

For a `ReaderSegmentKind::Derived` segment with `origin = derived:<kind>`:

```
kind        (tab | line_break | page_break)
  ⊕ element_ref (the documented control element, eN)
  ⊕ source_pos  (control element pre-order index)
  ⊕ literal     (the generated literal)
```

A derived unit has **no** `fragment_ref` and **no** span by construction; the
clean view must not invent one.

### 4.3 Dropped unit (`CleanUnit::Dropped`)

A dropped unit carries:

```
rule_id      (the declaring rule, e.g. rcv1_empty)
  ⊕ element_ref
  ⊕ source_pos
```

and structurally carries **no** `fragment_ref` and **no** `span`. Dropping is a
declared, classified action, not a silent loss: the dropped unit remains
addressable by rule id and element coordinates.

### 4.4 Provenance is read-only

Provenance is copied from the frozen projection and the substrate, never
re-based onto a different source, never re-derived from XML, and never mutated
in place. Building the clean view twice over the same inputs yields
byte-identical units and leaves the input projection unchanged.

## 5. Order and provenance consumption

- The clean view consumes **S04 `reader_reading_order::ReadingOrderIndex`** for
  order and the **frozen `ReaderProjection`** for the segments. It does not call
  `reader_projection::build_projection` again and does not re-parse XML.
- Reading order is the **event-walk order** (`ReadingOrderIndex::reading_order`),
  never derived from `semantic`, from `source_pos` alone, or from record order
  (acceptance contract §4).
- `CleanView::build` walks each **primary** view in reading order, classifies
  each segment by `segment.semantic` through the profile, and emits a `CleanUnit`
  with preserved provenance. Non-primary (navigation) views are refused with
  `NotPrimaryView`.
- Re-derivation is independent of the projection artifact: S04's
  `ReadingOrderIndex::build` already refuses a resealed reorder with
  `OrderMismatch`, so a reordered projection cannot produce a clean view.

## 6. Additive-only over the five frozen wire contracts

This design is **additive-only**. The five upstream wire contracts below are
frozen as of the S05 design. The sha256 of each tracked file **at design time**
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
  by S05;
- frozen `prd/architecture/*.jsonl` tracked artifacts are **not** modified;
- S05 adds new files (`reader_clean_view.rs`, its test, the census scripts, the
  slice battery, the evidence artifacts) and registers one module in
  `crates/ln-decode/src/lib.rs` — an additive edit only.

## 7. S03 reconciliation

S05 reconciles with the S03 baseline
(`prd/migration/rust-evidence/m223-s03-baseline-run.json`, schema
`m223-s03-baseline-run/v1`):

| fact | value |
|---|---|
| corpus entries | 43785 |
| accepted | 43785 |
| refused | 0 |
| incomplete | 0 |
| R1000 status | `active/unclosed` |

The clean-view rules are defined and exercised **per accepted document** on real
classes. Whole-corpus materialization of the clean view over all 43 785 accepted
documents is **S05–S07 evidence**, not S05 closure. S05 must not restate S03's
integrity/count result as a semantic or legal claim: the S03 run is an
acceptance/integrity baseline, not a semantic oracle (acceptance contract §8.2).
`s03_baseline_reconciled` in the S05 evidence artifact records the four numbers
and `r1000_status` above, and nothing more.

## 8. Real-class obligation

The rule set is proven on **real classes**, not only on synthetic fixtures:

1. **Tracked diverse fixtures** (`crates/ln-decode/tests/fixtures/reader/diverse/`)
   exercise each disposition on real WordML shapes (text-only, fields and
   revisions, controls, residual/whitespace/tails, encoding including NBSP and
   astral, empty structure). Fixtures are tracked files, never gitignored local
   paths.
2. **Bounded seeded real-corpus census** (T03) samples 24–32 accepted XML
   deterministically from the S02 manifest (seed + size deciles + largest tail),
   runs the existing release `cleaned-project` binary, tallies the observed
   `semantic` (and origin/derived kind) classes, and verifies each observed
   class has a declared disposition. An uncovered class is fail-closed.
3. **A revision class may never be declared garbage.** If
   `revision_insertion` or `revision_deletion` is observed, the census asserts
   its disposition is not `dropped`.

The census artifact carries only paths, counts, and hashes — no raw decoded
text (redaction, §10).

## 9. Slice boundary S05 / S06

| Surface | Disposition |
|---|---|
| versioned rule profile + clean-view model with preserved provenance + typed errors | S05 (T01/T02) — `reader_clean_view` |
| real-class proof: tracked diverse fixtures + bounded seeded census | S05 (T02/T03) |
| design pin + additive-only + S03 reconciliation + slice battery | S05 (T01/T04) |
| whole-corpus materialization of the clean view over all 43 785 accepted documents | S05–S07 |
| R1000 closure, legal completeness, source authenticity, citation resolution, normalization | not S05; remains out of scope |

S06 consumes the clean view for its declared consumer (navigation / tokenizer /
graph projection per acceptance contract §3) but does not re-open the rule
profile. Out of scope for S05: normalization, XML re-parse, temporal
`StructuralAst`/CST/CTV, CLI changes, and any R1000 closure. R1000 stays active.

## 10. Threat surface

- **Untrusted projection / order input → fail-closed.** `CleanView::build`
  validates view existence, primary-only scope, segment resolution, and every
  retained span via `check_fragment_span`; every violation is a typed refusal
  (`UnknownView`, `NotPrimaryView`, `UnknownSegment`, `SpanInvalid`,
  `SourceMappingIncomplete`), never a partial or clamped result. A resealed
  reorder is refused upstream by `ReadingOrderIndex` (`OrderMismatch`).
- **Profile drift → fail-closed.** The machine-readable profile block and the
  `reader_clean_view` source declarations must agree; T04 fails on drift. A class
  with no disposition is refused, not defaulted.
- **Decoded legal text is not a secret.** The decoded text is provider-bounded
  Consultant WordML already admitted by the reader projection; it is not
  classified. Redaction applies to **evidence artifacts**, not to the in-memory
  model: `m223-s05-real-class-census.json` and
  `m223-s05-clean-view-battery.json` carry only paths, counters, and hashes — no
  raw decoded text. Decoded text is permitted only inside Rust tests over the
  tracked fixtures.
- **Inputs are admission-verified.** The clean view consumes an already-verified
  `ReaderProjection` plus substrate `Record`s; it does not re-parse XML, does not
  re-open the corpus, and does not relax S03 admission.
- **No rebasing / silent loss.** Provenance is copied, not re-based. A dropped
  unit is classified with its rule id and coordinates; no revision class is
  discarded silently.

## 11. Requirement impact

- **R1000 — supporting-only. Do not close.** S05 delivers a bounded filtered view
  that supports the wider R1000 program (S05–S07 materialize it per accepted
  document); it is not an R1000 closure artifact and must not be reported as one.
  R1000 stays `active/unclosed` (acceptance contract §10; precedent: S03/S04).
- No other R-ID is bound or re-labelled by S05. S05 adds no new requirement; it
  advances no requirement to `validated`.

## 12. Verification surface

- `crates/ln-decode/tests/reader_clean_view.rs` (T02): on the tracked diverse
  fixtures — `body -> Primary` with `primary_text == decoded` and empty
  `service_text`; `field_code -> Service`, `revision_insertion -> Primary`,
  `revision_deletion -> Service` with fragment/span preserved and no revision
  unit dropped; derived tab/line-break/page-break `-> Service` with derived
  provenance and no fragment/span; `whitespace -> Service` and residual `body ->
  Primary`; NBSP/astral preserved verbatim; `empty -> Dropped` with rule id and
  no fabricated fragment; every retained unit resolves by a §5 form; malformed
  projection, non-primary view, and idempotent rebuild.
- `scripts/test_m223_s05_real_class_census.py` (T03): `uncovered_classes == []`,
  the profile is total over the seven classes, observed revision classes are not
  `dropped`, the artifact is redacted, `profile_id == reader_clean_profile/v1`,
  the sample is deterministic, and a missing real corpus is a fail-closed
  harness error.
- `scripts/test_m223_s05_contract.py` (T04): (a) this document exists and carries
  the required sections/markers ("source versus clean views", `clean-rule-profile`
  block, "source mapping", "S03 reconciliation", "slice boundary S05 / S06",
  "real-class obligation"); (b) the five pinned sha256 values match the tracked
  files **exactly** (drift → explicit re-pin, never silent); (c) the S03 baseline
  is reconciled (entries = accepted = 43785, refused = 0, incomplete = 0, R1000
  active/unclosed); (d) the profile block is total over the seven `ReaderSemantic`
  classes and matches the `reader_clean_view.rs` declarations; (e) the T03 census
  artifact reports `uncovered_classes == []` and `profile_id ==
  reader_clean_profile/v1`; (f) it emits
  `prd/migration/rust-evidence/m223-s05-clean-view-battery.json` (schema
  `m223-s05-clean-view-battery/v1`) with counters/hashes and `non_claims`,
  carrying only paths, counters, and hashes.
- Cleanliness battery: `cargo test -p ln-decode --offline --test
  reader_clean_view`; `cargo test -p ln-decode --offline`; `cargo fmt --all
  --check`; `cargo check --workspace --offline`; `cargo clippy --workspace
  --all-targets --offline -- -D warnings`; `uv run python
  scripts/verify-adr-conformance.py`.

## 13. References

- `prd/architecture/intermediate-source-acceptance-contract.md` §3 (source
  versus clean views), §4 (reading order versus record order), §5 (composite
  provenance), §8 (whole-corpus acceptance boundary), §10 (non-claims).
- `prd/architecture/intermediate-source-reading-order-contract.md` (S04 reading
  order and composite coordinates).
- `prd/architecture/reader-projection-contract.md` §3.2 (`ProjectedSegment`),
  §5 (independent verifier semantics).
- `prd/architecture/cleaned-projection-contract.md` (lossless inline text
  channel — not re-described here).
- `crates/ln-decode/src/reader_contract.rs` (`ReaderSemantic`,
  `ReaderDerivedKind`, `ReaderFragmentSpan`, `check_fragment_span`).
- `prd/migration/rust-evidence/m223-s03-baseline-run.json` (S03 baseline).
- `prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl` (S02 manifest
  consumed by the T03 census).
