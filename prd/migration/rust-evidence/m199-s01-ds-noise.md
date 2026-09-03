# DS-noise assessment: M199-3q54bv / S01 / T03 — rule-seed is pre-annotation, do-not-treat-as-gold

- artifact: `prd/migration/rust-evidence/m199-s01-ds-noise.md`
- lifecycle: `[bounded]`
- milestone / slice / task: M199-3q54bv / S01 / T03
- date: 2026-09-03
- annotator_id=seed-reviewer-1 (single executor rater; one rater vs a machine is **not** inter-coder agreement)
- seed under assessment: `prd/migration/rust-evidence/m199-s01-rule-seed.jsonl` (159 candidate spans over 180 tracked fragments; scanner in `crates/ln-decode/tests/npa_lawref_support/mod.rs` over the frozen C2 `lex()`)

## 1. What was measured

One rater (`seed-reviewer-1`) reviewed a deterministic nested subsample of **20** fragments against the rule-seed spans and coded every divergence with the DS-NER noise split (Ding 2025 via assessment/25 §5.2; operationalized taxonomy from SANTA, Zhang et al., arXiv:2305.04076, and RoSTER, Meng et al. 2021):

- **incomplete** (false negative): a human-visible user-reference core in the fragment with **no overlapping seed span**.
- **inaccurate** (false positive / wrong slot): a seed span that is not a reference core, truncates a structured endpoint, attaches the wrong head/slot, or mixes two references.

Rater convention (stated so the numbers are reproducible): a seed span is counted *correct* when it covers a reference core exactly as written (enumeration/requisite itself; a preceding preposition or governing fullword noun is boundary convention, not an error, unless the noun+number forms its own numbered core — e.g. `части 6.8`, `частями 7, 7.1` — which is then its own core). Quotes below are span-level lexemes only; no block text is reproduced (threat surface).

## 2. Subsample: n = 20, ≥ 2 per primary family, deterministic

Selection is rule-based, not cherry-picked: largest-remainder allocation over family fragment counts (npa 118 / fas 23 / courts 22 / xml 17 of 180), then a midpoint stride over each family's sorted fragment ids (selector: `ds_noise_subsample` in `npa_lawref_support`). Per-family counts: npa **13**, fas **2**, courts **2**, xml **3**.

| family | fragments |
|---|---|
| courts | npa-frag-124, npa-frag-135 |
| fas | npa-frag-146, npa-frag-158 |
| npa | npa-frag-005, npa-frag-014, npa-frag-023, npa-frag-032, npa-frag-041, npa-frag-050, npa-frag-060, npa-frag-069, npa-frag-078, npa-frag-087, npa-frag-096, npa-frag-105, npa-frag-114 |
| xml | npa-frag-166, npa-frag-172, npa-frag-178 |

## 3. Results

| family | seed spans | correct | inaccurate | missed (incomplete) | true cores T | incomplete rate (missed/T) |
|---|---|---|---|---|---|---|
| npa | 19 | 17 | 2 | 13 | 32 | 40.6% |
| courts | 2 | 2 | 0 | 2 | 4 | 50.0% |
| fas | 1 | 1 | 0 | 4 | 5 | 80.0% |
| xml | 2 | 2 | 0 | 2 | 4 | 50.0% |
| **total** | **24** | **22** | **2** | **21** | **45** | **46.7%** |

- **incomplete rate: 21/45 = 46.7%** of true reference cores have no overlapping seed span.
- **inaccurate rate: 2/24 = 8.3%** of seed spans are wrong (both boundary/endpoint classes, not fabrications).

## 4. Slot-confusion notes (span-level only)

1. **Non-`-ФЗ` requisite numbers are the dominant incomplete class (≈13 of 21 misses):** `lex()` mints `DocNo` only for the `digits-ФЗ`/`digits-ФКЗ` shape, so requisites like `27.12.2012 N 1416`, `12.01.2026 N 01-05`, `23.12.2024 N б/н`, `24.12.2024 N АК/18682/24`, `19.02.2024 N 32`, `21.03.2017 N 508-р`, `14.04.2017 N 446`, `09.12.2014 N 1339`, `13.02.2015 N 89`, `14.02.2014 N 55`, `14.09.2020 N 558`, `10.12.2024 N 1` seed nothing. Courts/fas fragments are almost entirely requisite-shaped, hence their high incomplete rates.
2. **Range endpoint truncation (inaccurate):** `16.6 - 16.6-2` seeds `range{from: 16.6, to: 16.6}` — the `-2` suffix of the second endpoint is not part of a HierNum lexeme, so the `range` slot carries a wrong endpoint.
3. **Anaphora head attachment (inaccurate):** `настоящего Федерального закона` seeds the anaphora span over `настоящего Федерального` — the matcher attaches the first following Word as the head noun, but the head is `закона`.
4. **Fullword inventory gaps (incomplete):** inflected/ plural tails beyond the four genitive fullwords do not seed: `части 6.8`, `частями 7, 7.1`; bare-number ranges (`18 - 18.2`) do not fire because only HierNum endpoints are matched; `(см. 5.2)` misses because `см.` is outside the chain marker inventory; `УИК РФ` misses because act codes beyond `ФЗ`/`ФКЗ` are not LawCode.

## 5. Verdict

**do-not-treat-as-gold / pre-annotation.** The rule-seed is distant supervision with a measured incomplete rate of 46.7% and an inaccurate rate of 8.3% on this subsample. It may be used only as pre-annotation input with explicit `provenance=rule-seed` (protocol §10); it must never be presented as gold, never laundered into an agreement score, and never counted as the Layer-2 annotation. Adjudication and the agreement gate (Krippendorff's α at the S04 threshold) belong to S04; **no α is computed here and no α value appears in any S01 artifact.**

## 6. Non-claims

- The sample and the seed are **not** official-publication provenance (R070 stays open).
- The seed is **not** a LawRef implementation, act tree, or clause segmentation; no LawRef type exists in `src/`.
- This report is **not** the N2-gate acceptance decision and is **not** legal interpretation.
- n=20/45-core tallies are a bounded diagnostic on one rater, not a precision/recall benchmark of `lex()` or of any product component.
- **no LLM pre-annotation** was used: the rater is the executing agent reviewing deterministic scanner output offline; no model pass touched the fragments.

## 7. Literature gap

Ding 2025 (DS-NER, IEEE TKDE) was consulted **via assessment/25 §5.2 only; the primary PDF was not retrieved or re-read** — recorded as a bounded literature gap. The operationalized incomplete/inaccurate split follows the standard distant-supervision noise taxonomy documented in SANTA (Zhang et al., arXiv:2305.04076) and RoSTER (Meng et al. 2021). No Ding-specific formulas (confidence reweighting, teacher–student, GCE loss) are claimed or used — S01 has no trainer.
