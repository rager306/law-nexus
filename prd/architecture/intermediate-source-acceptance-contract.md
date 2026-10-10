# Intermediate source acceptance contract (XML to JSONL)

**Status:** `[bounded]`
**Owning slice:** `M223-d2q075` / `S01` — T01. This document pins the consumer
contract and the corpus acceptance boundary; it executes no corpus pass and
closes no requirement.
**Accepted revision:** the six tracked files listed in §2. T01 accepted the S01
auto-commit (`53a469e`, `chore: auto-commit after gate-evaluate`,
`GSD-Unit: M223-d2q075/S01/gates+Q3,Q4`) without overwriting it, then closed
the decoded-key duplicate gap S01 surfaced (§2.4) by editing
`crates/ln-decode/src/npa_analysis_wire.rs` and adding a permanent negative
regression in `crates/ln-decode/tests/npa_analysis_strict_admission.rs`. The
accepted revision of those two files is their post-remediation content; the
other four are unchanged from `53a469e`. Any later change to these files or to
the frozen inputs below invalidates the acceptance record and requires a new
revision.
**Upstream contracts (frozen):**
`prd/architecture/source-jsonl-contract.md` (`[bounded]`),
`prd/architecture/reader-view-contract.md` (`[bounded]`),
`prd/architecture/reader-projection-contract.md` (`[bounded]`),
`prd/architecture/cleaned-projection-contract.md` (`[bounded]`),
`prd/architecture/npa-analysis-jsonl-contract.md` (`[bounded]`)
**Authority:** ADR-0013 (universal multi-source parser architecture), ADR-0015
(hexagonal verification architecture), ADR-0028 (typed lexer / dual tokenizer),
ADR-0029 (requisites-anchored member assembly — anchor boundary), ADR-0016
(structural legal identity); decisions D602/D328 (serde stays module-scoped to
`source_package`), D603 (anchor coordinates), D631 (reader coordinate base),
D633 (reader seal and resealed semantic-tamper semantics), D634 (independent
verifier recomputes from the substrate), D639/D640 (cleaned inline text channel
and envelope seals), D658 (analysis envelope family scope), D690/D691
(mode-aware six/seven admission; caller-declared versus analysis coordinates)
**Lifecycle ceiling:** this is a bounded acceptance and consumer-contract pin
over already-verified decoded source. It is **not** an R1000 closure artifact,
not a CST/AST, not a temporal `StructuralAst`, not lexical gold, and not
expert legal gold. It closes no requirement. M223 **advances R1000** on its
evidence path — it delivers the corpus-acceptance boundary and the consumer
contract the intermediate source must satisfy — but it must **not auto-close**
R1000, and no M223 slice closes R1000. Closure is a separate, evidence-gated
decision this milestone does not own.

---

## 1. Purpose

M223 turns the frozen decoded-source pipeline into a **corpus-scale
intermediate source**: one XML-to-JSONL materialization with clean consumer
views for **navigation**, the **tokenizer**, and **graph projection**, without
re-parsing XML downstream. Before the full-corpus run (S03) and the consumers
(S06/S07), S01 fixes four facts:

1. the base fixes already on disk are reviewed and independently verified, and
   the decoded-key duplicate gap they exposed is closed with a permanent
   regression (§2, §2.4);
2. the consumer contract — source versus clean views, reading order versus
   record order, composite provenance, graph document identity, and the
   no-reparse rule — is pinned (§3–§7);
3. the whole-corpus acceptance boundary, in which **a refusal is not a
   success** and **integrity is not semantics**, is pinned (§8);
4. each downstream slice is re-assessed as feasible against that boundary
   (§9).

This document is the authority the later slices consume. It does not run the
corpus; S02 owns the inventory and resource calibration, S03 owns the
resumable baseline run.

## 2. Accepted base revision and its independent verification

T01 accepted the S01 diff over six tracked files without overwriting it, then
closed the decoded-key duplicate gap that diff exposed (§2.4) by editing two of
those files:

| File | Role |
|---|---|
| `crates/ln-decode/src/reader_projection.rs` | tail semantic context in the producer |
| `crates/ln-decode/src/reader_verifier.rs` | independent recomputation in the verifier |
| `crates/ln-decode/src/npa_analysis_wire.rs` | strict JSON grammar and strict admission |
| `crates/ln-decode/tests/reader_tail_semantics.rs` | tail-semantics regression oracle |
| `crates/ln-decode/tests/npa_analysis_strict_admission.rs` | grammar/schema/version/capability admission oracle |
| `crates/ln-decode/tests/m222_f07_audit.rs` | independent-verifier and resealed-tamper oracle |

Frozen tracked artifacts `prd/architecture/*.jsonl` were not modified. The five
behaviors below were verified independently of any narrative: by reading the
producer, verifier, and scanner source, and by running the three targeted
regression suites plus the fresh full `ln-decode` package suite (§11). Targeted
evidence is 15 tests across 3 suites; the full package suite ran 1,291 passed /
0 failed / 6 ignored after the fix (§11).

### 2.1 Tail semantic context derives from the capture owner's parent

A `TextSlot::Tail` fragment is the
content *after* a closed element and therefore belongs to the **parent's**
content, not to the closed element's role. The producer and the verifier both
select the semantic context accordingly:

- `reader_projection.rs:536` `text_semantic(...)`: for `TextSlot::Tail` the
  context owner is `element.parent.as_deref()` (`:550`); for `TextSlot::Text`
  it is the capture owner.
- `reader_verifier.rs:285` `text_semantic(...)`: the same rule, recomputed from
  the substrate index (`:296`), independently of the projection.

The **capture owner is unchanged**: `segment.element_ref` is still the closed
element that captured the tail, and `segment.slot` is still `tail`.
`reader_tail_semantics.rs::closed_deletion_and_field_do_not_contaminate_following_tails`
and `::tails_retain_open_ancestors_but_not_closed_inner_roles` assert both facts
together — `AFTER_CODE` keeps owner `e7` and slot `tail` while its semantic is
`body`, and `СТАРОЕ` keeps owner `e4` while its semantic is
`revision_deletion` derived from the still-open `<w:del>` parent, not from the
closed `<w:instrText>` capture owner (the fragment follows the closed
`</w:instrText>` while `<w:del>` is still open).

### 2.2 The verifier is independent of the producer

`reader_verifier::verify_projection` recomputes the expected semantics from
`package.records()` (the substrate) rather than from the projection artifact,
and `reader_verifier.rs` does not call `reader_projection::build_projection`.
The two `text_semantic` routines are **separate implementations**: the verifier
does not share the producer's helper. This is producer/artifact independence.

**Non-claim (honest limitation):** the two routines share the *same algorithm*
by construction, so they share any systematic semantic defect. Independence
here means the verifier cannot be fooled by a mutated projection artifact; it
does **not** mean an independent semantic oracle. Semantic truth for the
corpus is owned by the independent oracle/holdout work in §8, not by this
verifier.

### 2.3 A resealed semantic rewrite is still refused

The content seal is an integrity/version pin, never an authorization.
`reader_tail_semantics.rs` clones a verified projection, reseals it, flips a
tail segment's `semantic` and its `contextual` flag coherently, reseals again
(so the seal is fresh), and asserts the verifier returns
`VerifyCode::SegmentSourceMismatch`. A fresh seal over rewritten semantics is
not accepted (`reader-tail-semantics`, 2 tests).

### 2.4 Strict JSON grammar, schema, version, and capability admission

`npa_analysis_wire.rs` validates the whole line grammar before extracting
top-level members, and refuses on admission:

- `scan_value` delegates to `scan_strict_value` with a depth cap
  `MAX_JSON_DEPTH = 64`; `scan_json_string` rejects bad escapes and unescaped
  control characters; numbers reject leading zeros, missing fraction/exponent
  digits, and `+`; literals must be exactly `true`/`false`/`null`; containers
  reject malformed separators, `[1,]`, `[1 2]`, `{"a":1,}`, `[}` and trailing
  bytes.
- Duplicate top-level and nested keys are refused on the **decoded** key text,
  both by the scanner (`scan_strict_value`, `keys.insert`) and by
  `JsonFields::parse` (`canonical_keys.insert`): `canonical_object_key` decodes
  each key through `unescape_json_inner` before the comparison, so a
  decoded-equivalent escaped copy (`"version"` vs `"\u0076ersion"`) is a
  duplicate, and a key that cannot be decoded is refused fail-closed.
- Per-line `schema` must equal the closed schema for that line's token, and the
  manifest must carry `version == CONTRACT_VERSION` and
  `capability == CAPABILITY`.

`npa_analysis_strict_admission.rs` (7 tests) and `m222_f07_audit.rs` (6 tests)
exercise this with an **independent seal oracle** (`reseal` /
`independently_reseal`) that never calls a production seam helper: valid
six-/seven-family envelopes are accepted; forged `version` (`2`, `0`, `-1`,
`1.0`, `1e0`, `"1"`, `null`, `01`), forged `capability`, forged
`schema` on each line, malformed ignored values, and an over-deep value are all
refused **after resealing**, and the refusal is an admission failure, not a
`SealMismatch`.

**Decoded-key duplicate admission (Q3 gap closed in T01).** S01 first found
that the duplicate-key checks compared **raw** key slices, so `"version"` and
`"\u0076ersion"` were not detected as a duplicate and a resealed manifest
carrying both passed `inspect_npa_analysis_wire`, `read_back_npa_analysis`, and
`verify_npa_analysis_wire`. T01 closed the gap in the same slice:

- the scanner and `JsonFields::parse` now compare the **decoded** key text
  (`canonical_object_key` → `unescape_json_inner`), so two keys that decode
  alike are duplicates regardless of escaping;
- a key that cannot be decoded (for example a lone surrogate escape) is
  refused, so the check is fail-closed and every admitted key has one canonical
  form;
- `get` still resolves admitted members by their literal spelling, so no valid
  envelope contract or frozen receipt changes: valid envelopes use literal
  ASCII keys, for which decoding is the identity.

`npa_analysis_strict_admission.rs::resealed_escaped_duplicate_key_is_refused`
is the permanent negative regression: it reseals
`"version":1,"\u0076ersion":2` with the independent oracle and asserts that
`inspect_npa_analysis_wire`, `read_back_npa_analysis`, and
`verify_npa_analysis_wire` all refuse it, and that the literal duplicate is
refused too (the decoded comparison is not narrower than the raw one).
`malformed_ignored_json_values_are_refused` additionally covers a nested
escaped duplicate (`{"a":1,"\u0061":2}`).

## 3. Source versus clean views

Three derived layers sit over the same immutable decoded source, and each
consumer must name which layer it reads:

| Layer | Module | Carries | Does not carry |
|---|---|---|---|
| **Source package** (decoded source) | `source_package` | all decoded element topology and **all** decoded text, verbatim; footer seals over the record stream and the manifest | cleaning, normalization, XML byte coordinates |
| **Reader projection** (reading views) | `reader_projection` / `reader_contract` | the reader view forest, ordered source-fragment and derived segments, references, decoded-fragment spans, source positions | clean-text separation, tokenization, analysis |
| **Cleaned projection** (clean text channel) | `cleaned_wire` | the same structure with an **inline full-sentence text channel** and a versioned cleaning rule set, plus a completion marker | legal semantics, citation resolution |
| **Analysis envelope** (document-scoped analysis) | `npa_analysis_records` / `npa_analysis_wire` | typed members, relations, classifications, diagnostics, opt-in context | raw decoded corpus copies |

The **source view is conservative**: it preserves every decoded fragment with
no exclusion, so no content class is silently dropped.

There are two distinct "clean" artifacts, and a consumer must name which one it
reads:

- the **existing cleaned envelope** (`cleaned_wire`) is **lossless**. Its
declared policy is `full_decoded_text_retained_inline` and
`source_content_retained_no_suppression`; it retains all decoded content inline
and does not suppress content, reorder within a group, or normalize raw decoded
text (`prd/architecture/cleaned-projection-contract.md`). It is a structural
carrier with a clean inline text channel, **not** a filtered view. Its frozen
policy must not be re-described as lossy by this contract.
- the **future filtered / display / tokenizer view** (S05) is the artifact where
primary text is separated from service content under **separately versioned**
rules with an explicit source mapping. Only this future view may drop, reorder,
or transform content, and only within its declared rule set.

The acceptance rule applies to the future filtered view only:

> A filtered view may drop, reorder, or transform content only within its
declared, versioned rule set, and every retained unit must resolve to its source
by one of the two provenance forms in §5. A filtered view that loses the mapping
is a defect, not a view.

No layer may be treated as a competing source of truth. Generated JSONL is a
derived, non-authoritative projection over the decoded source
(`prd/architecture/*.jsonl` stay frozen and are never regenerated in place by
this milestone).

## 4. Reading order versus record order

Two orders must not be conflated, and the S01 tail fix is exactly the place
they diverge:

- **Record order** is a *storage* fact: text records are emitted `t0..tM` in
  document order, and the source package serializes elements first, then texts.
  Ids are opaque; the verifier compares records by substrate coordinates
  (`element_ref`, `fragment_ref`), never by id equality across runs.
- **Reading order** is a *reader* fact: the text flow a reader sees. The
  reader projection reconstructs it from the substrate event walk
  (`text_ref` before children, then each child's `tail_ref`) — never by
  re-parsing XML.

A tail is the canonical case where the two differ. Its **capture owner** is the
closed element that physically captured the text, but its **semantic context**
is the parent, because after the element closes the reader is back inside the
parent's content (§2.1). This is a **classification** fact, not an ordering
fact: `text_semantic` only labels a segment, it never sorts. Reading order is
reconstructed by the substrate event walk (`reader_projection.rs:574`-`660`
`document_events`: `text_ref` before children, then each child's `tail_ref`)
and fixed by the per-view `ordinal`/sequence coordinates. Several fragments can
share `ReaderSemantic::Body`, so their mutual order is recoverable only from the
walk, never from the semantic label. Consumers must use the event-walk order
and per-view `ordinal` for text flow and provenance, and record order for
identity, coverage, and determinism. A consumer that derives reading order from
the semantic label, from `source_pos` alone, or that treats a tail's capture
owner as its semantic owner, is wrong.

## 5. Composite provenance

No single identifier is sufficient provenance. There are **two provenance
forms**, one per segment kind, and a consumer must use the right one:

**Source-fragment segment** (`ReaderSegmentKind::Text`, `origin =
source_fragment`):

```
document identity  (§6)
  ⊕ element_ref   (capture owner, eN)
  ⊕ slot          (text | tail)
  ⊕ fragment_ref  (tN)
  ⊕ decoded span  ([start, end) over the fragment's decoded value)
  ⊕ source_pos    (owner element pre-order index)
```

**Derived-control segment** (`ReaderSegmentKind::Derived` from `tab` / `br` /
`cr`, `origin = derived:<kind>`):

```
document identity  (§6)
  ⊕ element_ref   (the documented control element, eN)
  ⊕ source_pos    (control element pre-order index)
  ⊕ derived kind  (tab | line_break | page_break)
  ⊕ rule/profile  (the versioned derivation rule that produced the literal)
```

A derived control has **no** `fragment_ref` and **no** span by construction
(`reader_projection.rs:926`-`944`; `reader-projection-contract.md` §3.2); a
consumer must not invent one. A token span that crosses several fragments or a
derived separator is a **composite range**: an ordered list of source spans
plus the derived kinds between them, carried as ordered `output_start` /
`output_end` units — not a single fictitious fragment slice. Each component is
owned by a different fact: `fragment_ref`/`span` live in `reader_contract`;
`element_ref`/`slot`/`source_pos` are substrate coordinates; document identity
binds the whole group to one verified parent. The composite is **read-only**: a
consumer may project it into its own coordinates, but may not rebase it onto a
different source, drop the owner, invent a fragment for a derived control, or
re-derive it from XML. Reassigning a fragment to the wrong owner or view is a
`fragment_in_wrong_view` / `segment_owner_mismatch` defect and is refused by
the verifier.

## 6. Graph document identity

The graph projection (S07) must key nodes, members, and relations by
**document identity**, never by a fragment id alone: fragment ids (`tN`,
`eN`) are local to one document and collide across the corpus. The identity
is the composite pinned by the analysis contract §4.1/§4.2:

- `source.sha256` and `source.bytes` — copied from the parent manifest, never
  recomputed; integrity evidence, not authenticity;
- `parent.records_seal_hash` / `parent.manifest_hash` — the parent seals;
- the document version triple `DocumentVersionRef` =
  (`document_version_ref`, `source_revision`, `decoder_profile`).

Binding rules: all records in one unit belong to exactly one document version;
two units sharing `document_version_ref` but differing in `source_revision` or
`decoder_profile` are different versions and must not be merged; a record
citing a fragment whose parent identity differs from the unit's pinned identity
is refused (`CrossDocument` / `SourceIdentityMismatch`) and is never rebased.
Cross-document relations remain out of scope unless a later slice owns them
explicitly.

## 7. Consumers without XML reparsing

The three consumers — **navigation**, the **tokenizer**, and **graph
projection** — read the materialized JSONL layers only. They must not re-open
the source XML to recover structure, reading order, provenance, or identity:

| Consumer | Reads | Must not |
|---|---|---|
| Navigation (S06) | reader projection views/segments/references + source positions | re-walk XML for parent/subtree/neighbour structure |
| Tokenizer (S07) | clean text channel + source fragment/spans + derived controls (kind + source element, no fragment) + document identity | re-parse XML for text or boundaries; invent a fragment/span for a derived control |
| Graph projection (S07) | document identity + typed members/relations | key by local fragment id; re-parse XML for relation endpoints |

The no-reparse rule is the whole point of materializing an intermediate source:
if a consumer needs a fact that is absent from the JSONL, the fix is to extend
the producer under a tracked contract, not to add a hidden XML pass. Detecting
XML re-parsing by a consumer is part of the S07 acceptance.

## 8. Whole-corpus acceptance boundary

This section defines what "accepted over the corpus" will mean. It is a
boundary, not a result; S01 runs no corpus pass.

### 8.1 Every input has a terminal outcome; refusal is not success

The full pinned corpus is processed under an **inventory manifest** (S02), and
every manifest entry reaches exactly one terminal outcome: a derived artifact
with recorded identity/seals, or a **typed, bounded refusal**. A refusal is
**not** a functional success and must never be counted as one. Corpus
statistics report `accepted`, `refused` (by closed reason class), and
`incomplete` separately; a run with refusals does not "pass" merely because it
did not crash.

### 8.2 Integrity is not semantics

Integrity (seals, manifest binding, determinism, no-loss coverage) and
semantics (a correct reading of the legal text) are **separate facts**. A green
integrity verdict is not a semantic verdict. Semantic acceptance requires an
**independent oracle or holdout** (§8.4) and is reported in its own channel.
The reader verifier of §2.2 is an artifact-independence check, not a semantic
oracle.

### 8.3 Corpus pins (carried, re-verified in S02)

| Pin | Value at S01 |
|---|---|
| Corpus root | `consru_export/consru_export/exports` |
| XML file count | 43,785 (re-confirmed at S01, independently by the reviewer) |
| Total bytes | 3,789,431,364 (re-confirmed at S01, independently by the reviewer; S02 owns the authoritative manifest) |
| Max single-file bytes | 29,372,660 (re-confirmed at S01, independently by the reviewer; S02 owns the authoritative manifest) |
| Disk free at original measurement | 21 GB (S01 observed 20 GB) |

S02 owns the authoritative hash manifest of every XML entry and the
re-verification of these pins. At S01 an independent reviewer recomputed all
three from file sizes alone (`find -L ... -name '*.xml' -printf '%s\n' | awk`),
without reading document contents; S01 records them so the milestone boundary
is explicit and drift is visible.

**S02 authoritative values** (T01, `m223-s02-corpus-manifest.jsonl`,
`inventory_digest`
`sha256:aa7e14e31059c906f291423a2e8151f8bf0f857e9fd7370545d7e3b5800766dd`):

| Pin | Value at S02 (authoritative) |
|---|---|
| Corpus root | `consru_export/consru_export/exports` |
| XML file count | 43,785 |
| Total bytes | 3,789,431,364 |
| Max single-file bytes | 29,372,660 |
| Inventory digest | `sha256:aa7e14e31059c906f291423a2e8151f8bf0f857e9fd7370545d7e3b5800766dd` |
| Subdir counts | courts 5,667; fas 30,399; npa 916; xml 6,803 |

S02 re-derived all three pins from content hashes, not file sizes: the manifest
header records `pins.match = true` and `pins.drift = []`. The S01 table above is
kept as history; it was recomputed from file sizes alone.

### 8.4 Independent oracle / holdout

Corpus-wide outcomes (§8.1) and independent semantic checking (§8.2) are
separate deliverables with separate evidence. The oracle/holdout is built from
human- or independently-authored expectations, never from the producer's own
output, and never from the producer's helper functions. A holdout set is
withheld from any tuning and reported as a distinct result set.

### 8.5 Resource probes

S02 measures the cleaned path over the corpus and reports **median, p95, and
max** wall time and memory per input, plus the **complex classes** that drive
the tail (largest files, deepest trees, densest tables, largest text). A single
average is not an acceptance signal; the tail and the complex classes are.
S02 decides, from these probes, whether a full corpus run is feasible and at
what bound (§9).

**S02 result (T03).** The cleaned-path probe (`m223-s02-clean-path-probe.json`)
measured 300/300 accepted over a deterministic stratified sample (size deciles +
the largest 50). The feasibility decision (`m223-s02-corpus-feasibility.json`)
projects export and read-back separately and sums them with a **stated**
reconciliation-overhead and uncertainty margin: ≈4,874 s export + ≈1,791 s
read-back, giving a ≈2.89 h projected total wall; the conservative cleaned-layer
volume is ≈33.11 GB (decile-stratified 33.11 GB; aggregate-ratio cross-check
32.46 GB) and
the sampled peak-RSS tail is 3.0 GiB. Runtime limits are recorded as **stop
thresholds** (polled enforcement, not promised upper bounds), and the decision
authorises a conditional attempt gated on a mandatory preflight; see §9.

### 8.6 Resumability tied to input, code, and rules hashes

A resumable corpus run must bind each receipt to the three hash families that
determine its meaning:

- **input**: the per-file `source.sha256` (and byte count) from the inventory
  manifest;
- **code**: the source revision of the reader/admission pipeline actually
  executed (the aggregate content hash over tracked files, not a guess from
  HEAD);
- **rules**: the decoder/cleaner profile and contract version (for example
  `reader_wordml_profile/v1`, `npa_analysis_jsonl` version `1`,
  `cleaned_projection_wordml/v1`).

Resume is valid only when all three match. A receipt whose input hash matches
but whose code or rules hash has moved is stale and must be recomputed. This
mirrors the binding-field discipline of
`prd/architecture/npa-acceptance-contract.yaml` (`parser_revision`,
`inventory_digest`, `profile`, `limit`, `source_revision`) and the
`testedSourceRevision` content-hash rule.

### 8.7 Parked downstream stays parked

No parked downstream milestone (M208-wrz6fg, M215–M220, and any other parked
consumer program) is resumed, reopened, or bound by this contract. M223 may
**name** its consumers, but it does not un-park their work.

## 9. Slice feasibility reassessment

Re-assessed against §8 after S01's verification:

| Slice | Feasibility | Basis / gate |
|---|---|---|
| S01 base acceptance + contract | **accepted (T01)** | decoded-key gap closed (§2.4); 15 targeted tests pass; full `ln-decode` suite 1,291 passed / 0 failed / 6 ignored; fmt/check/clippy/ADR clean; contract pinned here |
| S02 inventory + resource calibration | **accepted (T01 manifest) / decided `full-stream-discard` (T03)** | authoritative manifest `m223-s02-corpus-manifest.jsonl` (43,785 entries, pins match, `inventory_digest` `sha256:aa7e14e3…`); cleaned-path probe `m223-s02-clean-path-probe.json` (300/300 accepted; export median 0.067 s / p95 10.53 s / max 57.41 s; read-back median 0.045 s / p95 1.34 s / max 12.14 s; peak RSS max 3.0 GiB); feasibility decision `m223-s02-corpus-feasibility.json`: projected total wall ≈2.89 h (export ≈4,874 s + read-back ≈1,791 s + stated overhead/uncertainty), conservative cleaned layer ≈33.11 GB, full persistence needs ≥39,734,841,675 B free disk (15.86 GB present), so the full run streams and discards, persisting receipts only; stop thresholds (not upper bounds) wall 14,400 s / RSS 6,291,456 KiB / artifact 2,147,483,648 B |
| S03 resumable baseline run | **feasible, gated on S02 decision `full-stream-discard`** | needs S02's manifest + S02's feasibility decision; the decision is a *conditional attempt* authorization: it streams and discards artifacts, persists per-file receipts, halts on a stop threshold, and resumes from receipts bound to input/code/rules hashes (§8.6); the mandatory preflight re-checks actual free disk and available memory; typed refusals are not success and a partial pass is never reported as full (§8.1) |
| S04 reading order + composite coordinates | **feasible** | coordinate base and tail semantics are fixed (§2.1, §5) |
| S05 clean views with provenance | **feasible** | versioned-rule + source-mapping requirement fixed (§3) |
| S06 document structure/navigation | **feasible** | navigation reads the reader projection, no XML re-parse (§7) |
| S07 consumers + final corpus run | **feasible, gated on S02–S06** | tokenizer + graph keyed by document identity (§6), no XML re-parse (§7), separate oracle/holdout (§8.4) |

No silent descoping: any reduction of these boundaries requires an explicit,
recorded reassessment, not a quiet scope cut.

## 10. Non-claims

- Not a requirement closure. M223 advances R1000 on its evidence path but does
  not close it; R1000 stays active/unclosed, and no M223 slice closes R1000.
- Not a corpus result. S01 runs no corpus pass; §8 is a boundary. The §8.3
  pins were re-confirmed at S01 from file sizes, but S02 owns the authoritative
  hash manifest.
- Not semantic truth. Integrity, completeness, and semantic acceptance remain
  three separate facts (§8.2); the reader verifier is artifact-independent, not
  a semantic oracle (§2.2).
- Not authenticity. `source.sha256` and the seals are integrity evidence; a
  party controlling the bytes can recompute them.
- Decoded-form duplicate admission is in scope and shipped: the scanner and
  parser canonicalize keys before the duplicate check, so a decoded-equivalent
  escaped duplicate is refused (§2.4).
- No lifecycle promotion, no legal-completeness or citation-resolution claim,
  no corpus-wide breadth claim beyond what S02–S07 will separately earn.
- No parked downstream un-parked (§8.7).

## 11. Evidence

- Targeted regression (fresh run after the §2.4 fix):
  `cargo test -p ln-decode --offline --test npa_analysis_strict_admission`
  — 7 passed / 0 failed / 0 ignored, including the new permanent
  `resealed_escaped_duplicate_key_is_refused`.
- Full `ln-decode` package suite (fresh run after the fix):
  `cargo test -p ln-decode --offline` — 1,291 passed / 0 failed / 6 ignored
  across 113 `test result` groups; raw log
  `.gsd/exec/ln-decode-full-battery.txt`. This is the `ln-decode` package
  suite (not every workspace package). It also covers the other two targeted
  suites: `reader_tail_semantics.rs` (2) and `m222_f07_audit.rs` (6), so the
  three-suite total is 15 tests (7 + 2 + 6).
- Cleanliness (each a separate command, no shell control syntax):
  `cargo fmt --all --check`; `cargo check --workspace --offline`;
  `cargo clippy --workspace --all-targets --offline -- -D warnings`;
  `uv run python scripts/verify-adr-conformance.py` (status `ok`,
  `finding_count` 0).
- Independent review (fresh context, read-only): a `reviewer` subagent
  reviewed `npa_analysis_wire.rs`, the new negative regression, and this
  contract. It independently re-ran the targeted suites and confirmed 15
  passed across the 3 suites and the decoded-key refusal at all three
  admission surfaces, and returned **APPROVE** with no residual blocking
  finding.
- The §2.4 gap is no longer a parent-run probe: it is a permanent negative
  regression (`resealed_escaped_duplicate_key_is_refused`) that reseals the
  decoded-equivalent duplicate with the independent oracle and asserts all
  three admission surfaces refuse it.

## 12. References

- ADR-0013, ADR-0015, ADR-0016, ADR-0028, ADR-0029.
- `prd/architecture/source-jsonl-contract.md`,
  `reader-view-contract.md`, `reader-projection-contract.md`,
  `cleaned-projection-contract.md`, `npa-analysis-jsonl-contract.md`,
  `npa-acceptance-contract.yaml`.
- `crates/ln-decode/src/reader_projection.rs`,
  `reader_verifier.rs`, `npa_analysis_wire.rs`, `source_package.rs`,
  `reader_contract.rs`.
- `crates/ln-decode/tests/reader_tail_semantics.rs`,
  `npa_analysis_strict_admission.rs`, `m222_f07_audit.rs`.
- D602/D328, D603, D631, D633, D634, D639/D640, D658, D690/D691.
