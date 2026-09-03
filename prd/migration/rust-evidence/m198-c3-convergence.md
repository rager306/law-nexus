# M198-das7v8 — C3 convergence report and N2 Layer-1 gate verdict

Cycle `C3` is a convergence re-run, not a third calibration wave and not N2
itself (D351 Layer-1 gate): the frozen C2 matcher — stem-ge-2 Unicode fold,
1-letter lowercase-exact (D356) — re-walked the same 43,785-XML corpus with
zero retune. Same binary `npa-corpus-sweep`, same closed schema
`npa-corpus-sweep/v1`, same decoder `ConsultantWordMlBlockDecoder`, same
eight record kinds in fixed order. Expected and observed: C3 is numerically
equal to C2 on every record; only `header.cycle` differs. Provenance: the C3
walk ran once in S03/T02 (single pass, ~107 s wall time per the C2
precedent); S03/T03 pins and reports it and never re-runs the corpus from
`cargo test`.

## Verdict — N2 Layer-1 gate

**PASS.** Both adjacent cycle pairs pass every D351 Layer-1 predicate:

| predicate | gate (D351) | C1→C2 | C2→C3 | verdict |
|---|---|---|---|---|
| abs(Δppm) | < 5 000 ppm | +1 ppm | 0 ppm | pass |
| top-10 unknown-tail set | equal | equal (Jaccard 1.0) | equal (Jaccard 1.0) | pass |
| census | 43 785 / 43 785 / 0 | met (C1, C2) | met (C2, C3) | pass |

Combined gate = PASS iff both pairs pass all predicates → **PASS**.

PASS closes Layer-1 M198 and authorizes exactly one thing: the next
milestone may start Layer-2 gold-sample dual annotation (Krippendorff
α ≥ 0.8) before any FSM code (D349 rule-first, D350 AKN eId). See "What
PASS does not authorize".

## Artifacts and contract pins

- C1: `prd/migration/rust-evidence/m198-c1-npa-corpus-sweep.jsonl` (frozen)
- C2: `prd/migration/rust-evidence/m198-c2-npa-corpus-sweep.jsonl` (frozen)
- C3: `prd/migration/rust-evidence/m198-c3-npa-corpus-sweep.jsonl` (this cycle)
- npa-family pre-retune baseline:
  `prd/migration/rust-evidence/m198-c2-npa-family-baseline.jsonl` — appendix
  only, never a row of the 3-cycle table.

Contract pins in `crates/ln-decode/tests/npa_corpus_sweep_contract.rs`:
C1 `t03_*`, npa baseline `t04_*`, C2 `t05_tracked_c2_full_corpus_pins`,
Layer-1 gate math `layer1_*` (S03/T01), C3 `t06_tracked_c3_full_corpus_pins`
and `t06_tracked_c3_numerically_equal_c2_except_header_cycle` (S03/T03).
Each cycle has its own path helper, so clobbering C1 or C2 fails its own
pin independently of the C3 pin. The equality pin is the HOLD path: any
C3≠C2 divergence fails the suite and names the divergent key
(`first_diff_path`); the matcher is never retuned from a test failure.

## Totals — 3-cycle table

| metric | C1 | C2 | C3 | Δ C2→C3 |
|---|---:|---:|---:|---:|
| files_seen | 43 785 | 43 785 | 43 785 | 0 |
| files_decoded | 43 785 | 43 785 | 43 785 | 0 |
| files_failed | 0 | 0 | 0 | 0 |
| word_tokens | 109 223 321 | 109 217 416 | 109 217 416 | 0 |
| marker_hits | 2 627 165 | 2 627 165 | 2 627 165 | 0 |
| marker_coverage_ppm | 24 053 | 24 054 | 24 054 | 0 |

The C1→C2 Δppm of +1 is a denominator effect only (`marker_hits`
byte-identical; `word_tokens` −5 905) — carried as a fact from
`m198-c2-delta.md`. C2→C3 is exactly 0 on every totals key.

## kind_hist — C2 vs C3

| kind | C2 | C3 | Δ |
|---|---:|---:|---:|
| Word | 109 217 416 | 109 217 416 | 0 |
| Abbrev | 995 529 | 995 529 | 0 |
| HierNum | 627 921 | 627 921 | 0 |
| Date | 885 333 | 885 333 | 0 |
| DocNo | 332 196 | 332 196 | 0 |
| EnumMarker | 1 127 829 | 1 127 829 | 0 |
| LawCode | 14 291 | 14 291 | 0 |
| Punct | 22 331 052 | 22 331 052 | 0 |
| Space | 107 873 919 | 107 873 919 | 0 |

## abbrev_hits — all 17 ids, C2 = C3

| id | C2 | C3 | Δ |
|---|---:|---:|---:|
| st | 435 810 | 435 810 | 0 |
| stst | 0 | 0 | 0 |
| ch | 127 172 | 127 172 | 0 |
| p | 140 443 | 140 443 | 0 |
| pp | 19 422 | 19 422 | 0 |
| podp | 1 359 | 1 359 | 0 |
| abz | 1 790 | 1 790 | 0 |
| gl | 1 201 | 1 201 | 0 |
| razd | 163 | 163 | 0 |
| pril | 38 | 38 | 0 |
| prim | 40 | 40 | 0 |
| red | 83 867 | 83 867 | 0 |
| izm | 1 183 | 1 183 | 0 |
| utv | 3 469 | 3 469 | 0 |
| sm | 8 078 | 8 078 | 0 |
| sr | 17 | 17 | 0 |
| g | 171 477 | 171 477 | 0 |

The 1-letter ids `ch` / `p` / `g` remain byte-identical at
127 172 / 140 443 / 171 477 — the D356 lowercase-exact rule for 1-letter
lexemes held through the convergence run.

## d329 — all 9 keys, C2 = C3

| id | C2 | C3 | Δ |
|---|---:|---:|---:|
| gl | 1 201 | 1 201 | 0 |
| razd | 163 | 163 | 0 |
| podp | 1 359 | 1 359 | 0 |
| abz | 1 790 | 1 790 | 0 |
| pril | 38 | 38 | 0 |
| prim | 40 | 40 | 0 |
| stst | 0 | 0 | 0 |
| utv | 3 469 | 3 469 | 0 |
| sr | 17 | 17 | 0 |

`stst = 0` stays the only global zero in all three cycles.

## unknown tail — top-10 and cap-50, C2 = C3

Top-10 (identical set and identical counts in both cycles):

| # | lexeme | count (C2 = C3) |
|---|---|---:|
| 1 | руб | 106 089 |
| 2 | А | 46 880 |
| 3 | закона | 38 700 |
| 4 | В | 36 426 |
| 5 | года | 27 591 |
| 6 | М | 25 930 |
| 7 | С | 25 112 |
| 8 | рублей | 23 682 |
| 9 | К | 23 220 |
| 10 | Н | 21 419 |

The whole cap-50 tail (D352) is identical as a ranked (lexeme, count) table,
and the `abbrev_candidate_census` alias of the same ranked table is
identical too. The leftover — руб / one-letter initials / закона / года —
is the documented D356 1-letter-exact remainder: a fact, not a C3 work item
and not touched by the convergence re-run.

## Final marker coverage (D353)

Integer-only formula, no floats:

- `ppm = 1_000_000 * find_legal_markers(text).len() / max(1, Word count)`
- `percent = 100 * ppm / 1_000_000`

Final Layer-1 reading: numerator `marker_hits = 2 627 165`, denominator
`word_tokens = 109 217 416` → `ppm = 24 054` → **percent = 2.4054%**.

This is a marker-frequency census metric over the decoded corpus. It is not
the assessment/25 "~59%" estimate and must not be quoted as that metric.

## D358 recap (D329 narrowed) — cite D358, not the M197-era D329/D330

Operative rule KEEP; empirical claim NARROW: 8 of the 9 section-marker keys
fire corpus-wide in C1/C2/C3, and `stst` is the only global zero (0 in all
three cycles). The corpus sweep informs the rule; it does not calibrate
morphology and does not mint goldens.

## D359 recap (numero KEEP) — cite D359, not D330

No numero Abbrev id exists: the 17-id lexicon stays closed, `№` stays
`Punct`, and `shapes.doc_no` is unchanged at 332 196 = 330 431 ФЗ +
1 765 ФКЗ in C2 and C3 alike. DocNo is not widened.

## What PASS does not authorize

- LawRef FSM code in M198 — none was written; the FSM is not started.
- Flipping ADR-0028 — it remains `[proposed]`.
- Closing R070 — it remains open; this report does not terminate it.
- A morphology "calibrated" claim — the C2→C3 delta is 0 by construction of
  a frozen-matcher re-run; 2.4054% is not "59% gap closed".
- Minting 44-ФЗ goldens.
- Treating the npa-family baseline as a Layer-1 pair member (appendix only).

## Next milestone (Layer-2)

Gold-sample dual annotation with Krippendorff α ≥ 0.8 before any FSM code;
rule-first (D349), AKN eId (D350). This report does not open C4.

## Non-claims

- R070 stays open.
- ADR-0028 remains `[proposed]`.
- LawRef FSM: not started.
- Krippendorff α: not measured — no dual annotation exists yet.
- Morphology: not calibrated.
- No product readiness claim of any kind.
- 2.4054% is a census metric, not "59% gap closed".

## Appendix — npa-family baseline (not a 3-cycle row)

`m198-c2-npa-family-baseline.jsonl`, header cycle `C2-npa-baseline`, 916 npa
XML, pre-retune lowercase-exact matcher (S02/T01). Historical pre-retune
reference only; not part of the Layer-1 C1/C2/C3 pair and never a row of the
totals table.
