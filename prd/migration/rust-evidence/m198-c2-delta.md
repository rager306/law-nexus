# M198-das7v8 — C2 full-corpus sweep delta (C1 → C2)

Cycle pair: `C1` (pre-retune, lowercase-exact `scan_abbrev`) vs `C2`
(post-retune, stem-ge-2 Unicode fold from S02/T02). Same binary
`npa-corpus-sweep`, same closed schema `npa-corpus-sweep/v1`, same decoder
`ConsultantWordMlBlockDecoder`, same 43,785-file census. Artifacts:

- C1: `prd/migration/rust-evidence/m198-c1-npa-corpus-sweep.jsonl` (frozen)
- C2: `prd/migration/rust-evidence/m198-c2-npa-corpus-sweep.jsonl` (this cycle)
- npa-family pre-retune baseline: `prd/migration/rust-evidence/m198-c2-npa-family-baseline.jsonl` (S02/T01)

Contract pins: C1 `t03_*`, baseline `t04_*`, C2 `t05_tracked_c2_full_corpus_pins`
in `crates/ln-decode/tests/npa_corpus_sweep_contract.rs`. No absolute Abbrev
count is pinned in the contract — the C2 measurement lives here.

## Totals

| metric | C1 | C2 | Δ |
|---|---:|---:|---:|
| files_seen | 43 785 | 43 785 | 0 |
| files_decoded | 43 785 | 43 785 | 0 |
| files_failed | 0 | 0 | 0 |
| word_tokens | 109 223 321 | 109 217 416 | −5 905 |
| marker_hits | 2 627 165 | 2 627 165 | 0 |
| marker_coverage_ppm | 24 053 | 24 054 | +1 |

Δppm = +1 (denominator effect only: `marker_hits` is byte-identical; only
`word_tokens` moved). This is a morphological metric — the retune did **not**
close any part of the marker-coverage gap.

## kind_hist (Δ only for moved kinds)

| kind | C1 | C2 | Δ |
|---|---:|---:|---:|
| Word | 109 223 321 | 109 217 416 | −5 905 |
| Abbrev | 989 940 | 995 529 | +5 589 |
| EnumMarker | 1 127 513 | 1 127 829 | +316 |
| Punct | 22 336 293 | 22 331 052 | −5 241 |
| HierNum / Date / DocNo / LawCode / Space | unchanged | unchanged | 0 |

Token conservation is exact: ΔWord = −(ΔAbbrev + ΔEnumMarker) = −5 905.
Mechanics of the two secondary effects:

- **Abbrev +5 589**: heading forms (`Абз.`, `Ст.`, `Гл.`, `См.`, `ПП.`,
  `Изм.`, …) fold onto canonical ids; each fold absorbs exactly the lexeme's
  trailing dot, so Punct loses one dot per plain fold.
- **Punct −5 241**, not −5 589: 348 folds had the dot merged into a larger
  greedy Punct run in C1 (e.g. `ст.),`), so absorbing the dot did not remove a
  whole Punct token.
- **EnumMarker +316**: downstream of the same dot absorption. When the folded
  abbreviation consumes exactly `stem + '.'`, an opening quote that C1's
  greedy Punct run swallowed (`."` as one token) now lands on a token start,
  so the quoted subpoint label branch (`"а"` → `Punct + EnumMarker + Punct`)
  fires where C1 missed it. `kind_hist.EnumMarker` and `shapes.enum_marker`
  agree (+316 / +316).

## abbrev_hits (all 17 ids)

| id | C1 | C2 | Δ |
|---|---:|---:|---:|
| st | 435 234 | 435 810 | +576 |
| stst | 0 | 0 | 0 |
| ch | 127 172 | 127 172 | 0 |
| p | 140 443 | 140 443 | 0 |
| pp | 18 828 | 19 422 | +594 |
| podp | 1 352 | 1 359 | +7 |
| abz | 1 574 | 1 790 | +216 |
| gl | 1 195 | 1 201 | +6 |
| razd | 163 | 163 | 0 |
| pril | 33 | 38 | +5 |
| prim | 35 | 40 | +5 |
| red | 83 809 | 83 867 | +58 |
| izm | 890 | 1 183 | +293 |
| utv | 3 464 | 3 469 | +5 |
| sm | 4 255 | 8 078 | +3 823 |
| sr | 16 | 17 | +1 |
| g | 171 477 | 171 477 | 0 |

ΣΔ = +5 589 = Δkind_hist.Abbrev (cross-check passes). Reading:

- One-letter ids `ch` / `p` / `g` are **byte-identical** (Δ = 0): the
  lowercase-exact rule for 1-letter lexemes held — hostile initials
  (`Ч.`, `П.`, `А.`, `Г.`) minted no Abbrevs (Q3 pass at corpus scale).
- `stst` stays **0** in both cycles: `СТ.СТ.` does not occur; the fold did not
  manufacture hits.
- Largest movers are heading-form folds: `sm` +3 823 (`См.`), `st` +576
  (`Ст.`), `pp` +594, `izm` +293, `abz` +216.

## d329 (all 9 keys)

| id | C1 | C2 | npa-family baseline (T01) |
|---|---:|---:|---:|
| gl | 1 195 | 1 201 | 6 |
| razd | 163 | 163 | 0 |
| podp | 1 352 | 1 359 | 0 |
| abz | 1 574 | 1 790 | 197 |
| pril | 33 | 38 | 0 |
| prim | 35 | 40 | 1 |
| stst | 0 | 0 | 0 |
| utv | 3 464 | 3 469 | 47 |
| sr | 16 | 17 | 2 |

8 of 9 fire on the full corpus in **both** cycles; `stst` is the only global
zero and stays zero post-fold. This is the empirical basis of the D329 NARROW
decision (operative rule KEEP, empirical claim narrowed).

## unknown_tail top-10 set overlap (cap 50)

Top-10 (both cycles, identical counts):

| # | lexeme | count (C1 = C2) |
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

Set overlap **10/10** (Jaccard 1.0); the full cap-50 tail is identical as a
set with identical counts. The corpus-wide tail is dominated by
courts/fas volume words, so the retune's tail evacuations (npa heading forms
`Абз.` / `Ст.` / `Гл.` / `См.`) stay below the global cap-50 horizon and show
up in the `abbrev_hits` deltas instead. The histogram was **not poisoned**:
no capital-initial (`А`, `В`, `Г`, `Ч`, …) or `руб` entry moved — the
fail-closed 1-letter-exact rule did its job (Q3).

## № / D330 — KEEP

- No `numero` Abbrev id exists: the 17-id lexicon is closed
  (`catalog_coverage` pin), the closed JSONL schema has no numero key, and
  the fail-closed reader rejects extra keys (`proof5_closed_key_reader_fails_on_extra_key`).
- Zero hits everywhere it could show: npa-family baseline (916 XML) — none;
  C1/C2 `shapes` — `doc_no` unchanged (332 196 = 330 431 ФЗ + 1 765 ФКЗ);
  research census — `№` = 0 in npa 916 / courts 800 / fas 800 / xml 400.
- Latin `N` + digits-`ФЗ` (≈ 298 910 occurrences in npa per research census)
  stays `Word + DocNo`; `№` stays `Punct`. DocNo is **not** widened.

## Non-claims

- **R070 stays open** — this task does not terminate it.
- **ADR-0028 remains `[proposed]`** — no ADR status change from a sweep cycle.
- **LawRef FSM: not started** — the sweep informs it, nothing more.
- **N2-gate = S03** — the C1/C2 pair is S03's input; this report is not the gate.
- **Morphology was not calibrated** — Δppm = +1 is a denominator artifact;
  do not read it as "C2 closed 2.41%" or any part of marker coverage.
- Schema v1, the 8 record kinds, the D352 unknown-tail class, and the cap of
  50 are unchanged; S03 can read the C1/C2 pair without schema drift.
