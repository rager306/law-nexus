# M199-3q54bv — S04 N2 acceptance report: Layer-2 and Layer-3 gates and verdict

This is the D378 operationalization of the D351 Layer-2/3 N2 acceptance gate,
measured over the frozen capture layer (S02: 159/159 record-for-record parity
against the `provenance=rule-seed` seed) and the frozen resolve layer (S03
dump). It ships an honest HOLD, not a green α: no dual-annotated gold exists,
so no accuracy beyond the sample is claimed anywhere in this report.

Companion machine-readable artifact:
`prd/migration/rust-evidence/m199-s04-n2-acceptance.json` — the closed
`npa-lawref-n2-acceptance/v1` envelope with a fail-closed reader and
executable pins in `crates/ln-decode/tests/npa_lawref_acceptance_contract.rs`.
Layer-1 is cited from D363 (M198 C3 convergence), not remeasured: this report
never walks the 43,785-XML corpus.

## Verdict — N2 (D351 Layer-2/3)

| layer | gate | verdict | basis |
|---|---|---|---|
| Layer-1 corpus convergence | D351 Layer-1 predicates | PASS (cited) | Cited from D363 (M198 C3: C2→C3 Δppm 0, tail Jaccard 1.0, census 43,785/43,785/0). Not re-run here; no corpus sweep in S04. |
| Layer-2 dual-annotation α | Krippendorff α ≥ 0.8 over a dual-annotated gold sample | HOLD | No second annotator exists, so `alpha_sample` is JSON null; the 159-record rule-seed is distant supervision, sample ≠ gold (D366); DS-noise incomplete 46.7% (21/45) and inaccurate 8.3% (2/24), verdict do-not-treat-as-gold. |
| Layer-3 resolution | span-exact accuracy vs gold | INCONCLUSIVE vs gold; DIAGNOSTIC vs seed | `resolution_accuracy` is null: no gold canonical anchors exist. Coverage 86 Some / 73 None over the 159 seed captures (R070 rows all None); canonical dedup 46 groups / 23 with 2+ members / 23 singletons over the tracked S03 dump. |
| Combined N2 (D351 Layer-2/3) | both layers pass | NOT PASS | Layer-2 HOLD and Layer-3 INCONCLUSIVE cannot combine to PASS; `combined_status` stays NOT_PASS. |

## Alpha — formula shipped toy-pinned, sample α not computed

- Formula: `krippendorff-nominal-two-rater-coincidence/v1` — two-rater nominal
  Krippendorff α in coincidence form (Artstein & Poesio 2008; protocol §9),
  implemented as tests-only exact i64-rational helpers in the acceptance
  contract suite and pinned on inline toys: perfect agreement = 1/1
  (ppm 1000000), systematic binary disagreement = -9/10 (ppm -900000), counted
  mix (A,A)/(A,A)/(A,B)/(B,B) = 8/15 (ppm 533333).
- `alpha_sample` is JSON null and `alpha_gate` is HOLD: the sample α is not
  computed because there is no second annotator (D366 laundering guard — the
  formula is never run against the rule-seed or against the one-rater DS-noise
  prose).
- Multi-label encoding if two raters existed (protocol §9): α per closed slot
  — the eight slots of protocol §5 (`marker_chain`, `hier_nums`, `date`,
  `doc_no`, `law_code`, `anaphora`, `range`, `quoted_enum`) — plus span
  presence (`not_a_reference` matches only `not_a_reference`, protocol §8).
  This report emits no per-slot sample numbers.

## Table A — span-exact P/R/F1 vs provenance=rule-seed

Diagnostic span-exact P/R/F1 vs provenance=rule-seed, not gold: the 159/159
record-for-record parity is the S02 construction pin, not human F1 and not
Layer-2 acceptance. The DS-noise 46.7 percent incomplete rate on the
20-fragment subsample remains the human-recall diagnostic. Match key
`(fragment_id, start, end, pattern_id)`.

| pattern_id | tp | fp | fn |
|---|---:|---:|---:|
| range_candidate | 33 | 0 | 0 |
| date-docno-window | 32 | 0 | 0 |
| abbrev-hier-chain | 32 | 0 | 0 |
| anaphora_candidate | 28 | 0 | 0 |
| fullword-ref | 26 | 0 | 0 |
| abbrev-amendment-window | 6 | 0 | 0 |
| quoted-enum | 2 | 0 | 0 |
| overall | 159 | 0 | 0 |

precision_ppm = recall_ppm = f1_ppm = 1000000.

## Table B — head TokenKind vs seed

Head-TokenKind diagnostic vs provenance=rule-seed, not gold: the seed kind
column comes from the same rule harvest, so the 159/159 parity makes this F1
exactly 1.0 by construction; it is not Layer-2 acceptance. Match key
`(fragment_id, start, end, pattern_id)`; predicted head = first TokenKind of
the capture token_kind_seq, actual = the seed kind.

| kind | n | tp | fp | fn |
|---|---:|---:|---:|---:|
| Abbrev | 38 | 38 | 0 | 0 |
| Word | 56 | 56 | 0 | 0 |
| HierNum | 33 | 33 | 0 | 0 |
| Date | 32 | 32 | 0 | 0 |
| overall | 159 | 159 | 0 | 0 |

Same construction property: precision_ppm = recall_ppm = f1_ppm = 1000000 by
parity, not a quality measurement.

## Table C — resolution coverage (Layer-3 diagnostic)

Layer-3 coverage over the seed sample, not gold-anchor accuracy: no gold
canonical anchors exist, resolution_accuracy stays null, and R070 amendment
and date windows stay out of scope. Coverage counts observable shapes and
never correctness. Alignment key `(start, end, pattern_id)` over the 159 seed
captures.

| pattern_id | n | n_anchor_some | n_members_pair | n_anchor_none |
|---|---:|---:|---:|---:|
| abbrev-amendment-window | 6 | 0 | 0 | 6 |
| abbrev-hier-chain | 32 | 32 | 0 | 0 |
| anaphora_candidate | 28 | 8 | 0 | 20 |
| date-docno-window | 32 | 0 | 0 | 32 |
| fullword-ref | 26 | 26 | 0 | 0 |
| quoted-enum | 2 | 0 | 0 | 2 |
| range_candidate | 33 | 20 | 20 | 13 |
| total | 159 | 86 | 20 | 73 |

Expected shapes (from the JSON pins): amendment and date-docno windows stay
anchor=None (R070 out of scope); a hyphen-continuing equal-endpoint range
stays anchor=None with empty members (a false range, never a Layer-3 miss);
document-level anaphora anchors None (the doc sink never mints doc_*);
настоящей статьи maps to art_ctx or the stacked art frame when one exists;
ranges resolve as the expanded endpoint pair, never an integer enumeration.

Live degenerate: npa-frag-009 [562, 573) range_candidate — classification
unresolved-false-range, counted_as_false_negative=false: it is a Table A true
positive and a Table C coverage-None at once.

## Table D — canonical dedup over the tracked S03 dump

Canonical-dedup quality counted over the tracked S03 dump - a read-only
projection, never a second canon and never regenerated here: S03 shipped
grouping and this table only counts it; no gold exists, so no precision of
grouping is claimed. The art_ctx group is the honest missing-frame token and
its size is NOT a quality win (the dump's synthetic roadmap demo groups are
counted dump-wide).

| n_groups | n_groups_ge2 | n_singletons | art_ctx_group_size |
|---|---:|---:|---:|
| 46 | 23 | 23 | 9 |

Presence pins: art_7.29..art_7.32, art_16.6, art_ctx, art_26.2/par_1.
`art_ctx` is not a Work identity: it is the honest missing-frame token for
anaphora with no prior frame in the same src, and its group size is NOT a
quality win.

## Why the seed cannot be gold — the S01 DS-noise measurement

Cited from `m199-s01-ds-noise.md` (S01, one rater, deterministic scanner
output reviewed offline): incomplete 21/45 = 46.7% of true reference cores
have no overlapping seed span; inaccurate 2/24 = 8.3% of seed spans are wrong
(both boundary/endpoint classes, not fabrications); verdict
do-not-treat-as-gold / pre-annotation. This measurement — not any α number —
is why Layer-2 stays HOLD and why the seed can never be laundered into the
agreement gate. No α number is written into ds-noise.md and none may be
(executable pin in the contract suite).

## S02 leftovers — known limitations, not fixed in S04

Recorded at S02 closeout as known limitations of the frozen capture layer.
They are not bugs to fix in this slice and were not patched in capture:

1. amendment `scan_filler_forward(16/4)` off-by-one versus the seed
   `gap < 16` / `gap < 4`;
2. quoted-enum dropped the Space-guard;
3. Abbrev-headed quoted-enum captures an empty `marker_chain`;
4. the `того же` matcher branch is unseeded;
5. broken-table capture yields an empty `Vec`.

## What HOLD does not authorize

- Flipping ADR-0028 — it stays `[proposed]`.
- Closing R070, R035, or R038 — all stay open/active; R038 fires here as
  executable review pins over this report pair and the contract suite, not as
  a rewrite of lawref.rs, and the requirement itself stays standing.
- Any product-readiness or bundesrecht-quality claim.
- Treating 159/159 as human F1 — it is the S02 construction pin
  (record-for-record parity over the seed), never recall against human cores.
- Treating `art_ctx` as a Work identity — it is the honest missing-frame
  token.
- Treating the M197 TokenKind sidecar P/R/F1 as this gate (D364) — that is a
  lexer regression pin, not Layer-2 acceptance.
- LLM pre-annotation — forbidden (protocol §11: deterministic pipeline; an LLM
  pass would add a second noise source requiring its own DS-style
  measurement).

## Proof ceiling [bounded]

Consultant-only decoded fragments (Consultant ≠ Garant; no Garant ODT). The
sample is the D367 frame: N_docs = 40 documents drawn into 180 tracked
fragments — 180 fragments are not 180 acts, and none of the rates above is a
corpus-wide number. This report is bounded lifecycle evidence, not legal
interpretation.

## Non-claims

- No official-publication claim: decoded fragments are working copies, not the
  official publication.
- R070 amendment and date windows stay open and out of scope for every number
  in this report.
- The 159-record rule-seed is distant supervision: sample ≠ gold, never human
  annotation.
- No inter-coder agreement is claimed because no second annotator exists;
  alpha_sample stays JSON null.
- Layer-2 is HOLD: the formula ships toy-pinned, with no accuracy claim beyond
  the sample.
- The report claims no resolution accuracy: gold canonical anchors do not
  exist; coverage is not correctness.
- The report flips no ADR-0028 and ships no FSM behavior; the src surface is
  frozen.
- This report is bounded lifecycle evidence, not legal interpretation.
- Layer-1 PASS is cited from D363 (M198), not remeasured here.
- 159/159 is not human F1: record-for-record parity over the seed is a
  construction property, not recall against human cores.
- M197 TokenKind sidecar P/R/F1 is a lexer regression pin, not this Layer-2
  gate.

## Artifacts and contract pins

- `prd/migration/rust-evidence/m199-s04-n2-acceptance.json` — the
  closed-envelope machine-readable report (this file mirrors it; tables are
  copied with captions intact).
- `crates/ln-decode/tests/npa_lawref_acceptance_contract.rs` — the executable
  spec: two-rater nominal α toys, the fail-closed reader, HOLD invariants,
  live-recompute pins (Tables A–D), the byte-determinism round-trip, markdown
  pins, and the R038 review home (`r038_*` tests over the report pair, the
  seed JSONL, src/lawref.rs, and Cargo.toml).
- One-shot generator:
  `cargo test -p ln-decode --offline --test npa_lawref_acceptance_contract generate_n2_acceptance_dump_writes_tracked_projection -- --ignored --nocapture`
  — the default battery reads the tracked file and never writes.
