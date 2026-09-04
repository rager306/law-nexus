//! Contract tests for the M199 S04 N2 acceptance report (Layer-2 / Layer-3
//! gates and the combined verdict).
//!
//! S04 ships D351 Layer-2/3 as an acceptance report, not a third FSM. The
//! dual-annotated gold does not exist (D366: the 159-record rule-seed is
//! distant supervision, and one rater vs a machine is not inter-coder
//! agreement), so the sample alpha is NOT computable. This suite therefore
//! pins three things and nothing more:
//!
//! 1. the executable two-rater nominal Krippendorff alpha formula
//!    (coincidence form, Artstein & Poesio 2008; protocol §9) as private
//!    evaluation helpers over inline toys - exact i64 rationals, no IEEE
//!    equality, first proof green immediately (no `#[ignore]`, no D373);
//! 2. the closed `npa-lawref-n2-acceptance/v1` envelope with a fail-closed
//!    reader (extra keys, numeric `alpha_sample`, `combined_status: PASS`,
//!    and an unbounded lifecycle all fail closed naming the key);
//! 3. the tracked HOLD invariants (`alpha_sample: null`, `combined_status:
//!    NOT_PASS`) so T02 fills tables against a fixed path pin. D378 is
//!    the operationalization of D351; the formula is never run against the
//!    159-record seed (D366 laundering guard);
//! 4. the T02 Tables A-D: span-exact P/R/F1 vs the `provenance=rule-seed`
//!    records (match key `(fragment_id, start, end, pattern_id)`), the
//!    head-TokenKind table, the Layer-3 coverage counts over
//!    `resolve_lawrefs` (never accuracy: `resolution_accuracy` stays null),
//!    and the S03-dump dedup counts;
//! 5. the live-recompute pin: the tracked tables must equal a fresh
//!    computation over the 180 manifest fragments and the tracked S03 dump,
//!    so any fixture or resolver drift turns the suite red (the MEM236
//!    `--check` analog).
//!
//! Evaluation helpers are private to this suite - never a src module. The
//! JSON readers are hand-rolled in the S03 `analyze_dump` style (D328), with
//! no `#[path]` include of test support (D335): the tiny seed/manifest
//! reader family is copied from `npa_lawref_capture_contract.rs`. The
//! corpus (`consru_export`) is never opened and `tests/fixtures/npa/` is
//! never walked (D364). Q3 threat surface: errors name keys and rules,
//! never fragment text; tables carry fragment_id plus offsets only.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::lawref::{capture_lawrefs, LawRefSlots};
use ln_decode::lawref_resolve::resolve_lawrefs;

/// Repo-root-relative evidence directory holding the tracked artifacts
/// (the capture-contract path idiom).
fn evidence_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../prd/migration/rust-evidence")
}

/// Repo-root-relative path of the tracked N2 acceptance report (T01 writes
/// the HOLD skeleton; T02/T03 fill the tables against this path pin).
fn acceptance_report_path() -> PathBuf {
    evidence_dir().join("m199-s04-n2-acceptance.json")
}

/// Repo-root-relative path of the S01 ds-noise assessment. Read-only here:
/// the alpha gate belongs to S04, so no alpha number is ever written into
/// that file (the existing sample-contract pin, re-asserted below).
fn ds_noise_report_path() -> PathBuf {
    evidence_dir().join("m199-s01-ds-noise.md")
}

// ---------------------------------------------------------------------------
// Two-rater nominal Krippendorff alpha (coincidence form, exact rationals).
// ---------------------------------------------------------------------------

/// Exact rational alpha: `num / den`, always reduced, `den > 0`. No IEEE
/// equality anywhere; toys pin exact fractions and a derived ppm.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct AlphaRatio {
    num: i64,
    den: i64,
}

impl AlphaRatio {
    fn new(num: i64, den: i64) -> Self {
        assert!(den > 0, "alpha denominator must stay positive");
        let sign = if num < 0 { -1 } else { 1 };
        let magnitude = num.abs();
        let g = gcd(magnitude, den);
        Self {
            num: sign * (magnitude / g),
            den: den / g,
        }
    }

    fn one() -> Self {
        Self { num: 1, den: 1 }
    }

    fn zero() -> Self {
        Self { num: 0, den: 1 }
    }

    /// `round(alpha * 1_000_000)` half away from zero, integer math only.
    fn ppm(&self) -> i64 {
        let scaled = self.num.abs() * 2_000_000 + self.den;
        let magnitude = scaled / (2 * self.den);
        if self.num < 0 {
            -magnitude
        } else {
            magnitude
        }
    }
}

fn gcd(mut a: i64, mut b: i64) -> i64 {
    while b != 0 {
        let rest = a % b;
        a = b;
        b = rest;
    }
    a
}

/// Two-rater nominal Krippendorff alpha over paired codes, coincidence form
/// (Artstein & Poesio 2008; protocol §9). Both raters code the same units in
/// order; codes are opaque strings. Missing codes fail closed (no silent
/// drop). Coincidence: each pair `(a, b)` adds 1 to `o[a][b]` and 1 to
/// `o[b][a]`, so agreement on `c` adds 2 to `o[c][c]`; `n_c = Σ_k o[c][k]`;
/// `n = Σ_c n_c = 2 * n_units`; nominal `δ(c,k) = 0` if `c == k` else `1`;
/// `D_o = (n - Σ_c o[c][c]) / n`; `D_e = (n² - Σ_c n_c²) / (n(n-1))`;
/// `α = 1 - D_o/D_e`, with the degenerate all-mass-on-one-category rule
/// `α = 1` iff `D_o == 0` else `0`. Errors name the rule, never the coded
/// strings (Q3).
fn krippendorff_nominal_alpha(
    ratings_a: &[&str],
    ratings_b: &[&str],
) -> Result<AlphaRatio, String> {
    const RULE: &str = "krippendorff-nominal-two-rater-coincidence/v1";
    if ratings_a.is_empty() {
        return Err(format!(
            "alpha: empty input - no coded units to score ({RULE})"
        ));
    }
    if ratings_a.len() != ratings_b.len() {
        return Err(format!(
            "alpha: length mismatch - both raters must code the same units, got {} vs {} ({RULE})",
            ratings_a.len(),
            ratings_b.len()
        ));
    }
    let mut codes: Vec<&str> = Vec::new();
    for code in ratings_a.iter().chain(ratings_b.iter()) {
        if code.is_empty() {
            return Err(format!(
                "alpha: missing code - every unit needs an opaque code from each rater, no silent drop ({RULE})"
            ));
        }
        if !codes.contains(code) {
            codes.push(code);
        }
    }
    let width = codes.len();
    let index_of = |code: &str| -> usize {
        codes
            .iter()
            .position(|seen| *seen == code)
            .expect("codes were collected above")
    };
    let at = |i: usize, j: usize| i * width + j;
    let mut o = vec![0i64; width * width];
    for (a, b) in ratings_a.iter().zip(ratings_b.iter()) {
        let (i, j) = (index_of(a), index_of(b));
        o[at(i, j)] += 1;
        o[at(j, i)] += 1;
    }
    let n_c: Vec<i64> = (0..width)
        .map(|c| (0..width).map(|j| o[at(c, j)]).sum())
        .collect();
    let n: i64 = n_c.iter().sum();
    let diagonal: i64 = (0..width).map(|c| o[at(c, c)]).sum();
    let sum_of_squares: i64 = n_c.iter().map(|nc| nc * nc).sum();
    let d_e_num = n * n - sum_of_squares;
    let d_o_num = n - diagonal;
    if d_e_num == 0 {
        // All mass on one category: expected disagreement is zero.
        return Ok(if d_o_num == 0 {
            AlphaRatio::one()
        } else {
            AlphaRatio::zero()
        });
    }
    Ok(AlphaRatio::new(d_e_num - d_o_num * (n - 1), d_e_num))
}

#[test]
fn krippendorff_nominal_two_rater_perfect_agreement_is_one() {
    // 10 identical pairs: all coincidence mass on one category with perfect
    // agreement, so the degenerate rule pins alpha at exactly 1.
    let ratings = vec!["slot:obligation"; 10];
    let alpha =
        krippendorff_nominal_alpha(&ratings, &ratings).expect("identical fully coded units");
    assert_eq!(
        (alpha.num, alpha.den),
        (1, 1),
        "perfect agreement is exactly 1"
    );
    assert_eq!(alpha.ppm(), 1_000_000, "alpha_ppm pins at 1000000");
}

#[test]
fn krippendorff_nominal_two_rater_systematic_disagreement_is_not_positive() {
    // Binary 50/50 where rater B codes the exact opposite of rater A on
    // every unit: each disagreeing pair adds 1 to both off-diagonal cells,
    // so o[O][P]=o[P][O]=10; n_O=n_P=10; n=2*n_units=20; diagonal=0.
    // D_o = 20/20 = 1; D_e = (400-(100+100))/(20*19) = 200/380 = 10/19;
    // alpha = 1 - 1/(10/19) = 1 - 19/10 = -9/10 (negative, as it must be).
    let mut a = Vec::new();
    let mut b = Vec::new();
    for unit in 0..10 {
        if unit < 5 {
            a.push("code:obligation");
            b.push("code:permission");
        } else {
            a.push("code:permission");
            b.push("code:obligation");
        }
    }
    let alpha = krippendorff_nominal_alpha(&a, &b).expect("fully coded units");
    assert!(
        alpha.num <= 0,
        "systematic disagreement must not score positive, got {}/{}",
        alpha.num,
        alpha.den
    );
    assert_eq!(
        (alpha.num, alpha.den),
        (-9, 10),
        "the exact value is -9/10 (-900000 ppm)"
    );
    assert_eq!(alpha.ppm(), -900_000);
}

#[test]
fn krippendorff_nominal_two_rater_counted_mix_matches_rational() {
    // Four pairs (A,A), (A,A), (A,B), (B,B). Coincidence: o[A][A]=4,
    // o[B][B]=2, o[A][B]=o[B][A]=1; n_A=5, n_B=3, n=8.
    // D_o = (8-6)/8 = 1/4. D_e = (64-(25+9))/56 = 30/56 = 15/28.
    // alpha = 1 - (1/4)/(15/28) = 1 - 7/15 = 8/15.
    // alpha_ppm = round half-up of 8/15 * 1e6 = round(533333.33) = 533333.
    let alpha = krippendorff_nominal_alpha(
        &["code:A", "code:A", "code:A", "code:B"],
        &["code:A", "code:A", "code:B", "code:B"],
    )
    .expect("the counted mix is fully coded");
    assert_eq!((alpha.num, alpha.den), (8, 15), "alpha is exactly 8/15");
    assert_eq!(alpha.ppm(), 533_333, "round half-up of 8/15 * 1e6");
}

#[test]
fn krippendorff_rejects_length_mismatch_and_missing_codes_naming_the_rule() {
    let coded = ["code:obligation", "code:permission"];

    let empty = krippendorff_nominal_alpha(&[], &[]).expect_err("empty input must fail closed");
    assert!(
        empty.contains("empty"),
        "the empty rejection must name the rule, got: {empty}"
    );
    assert!(
        !coded.iter().any(|code| empty.contains(code)),
        "errors never echo coded strings"
    );

    let mismatch = krippendorff_nominal_alpha(&coded, &coded[..1])
        .expect_err("length mismatch must fail closed");
    assert!(
        mismatch.contains("length"),
        "the mismatch rejection must name the rule, got: {mismatch}"
    );
    assert!(
        !coded.iter().any(|code| mismatch.contains(code)),
        "errors never echo coded strings"
    );

    let missing = krippendorff_nominal_alpha(
        &["code:obligation", ""],
        &["code:obligation", "code:permission"],
    )
    .expect_err("a missing code must fail closed");
    assert!(
        missing.contains("missing"),
        "the missing-code rejection must name the rule, got: {missing}"
    );
    assert!(
        coded.iter().all(|code| !missing.contains(code)),
        "errors never echo coded strings"
    );
}

// ---------------------------------------------------------------------------
// Span-exact P/R/F1 (diagnostic vs the rule-seed; never Layer-2 acceptance).
// ---------------------------------------------------------------------------

/// Span-exact match key: protocol `(start, end, kind)` with the N2 kind
/// carried by `pattern_id`, keyed inside the fragment.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct MatchKey {
    fragment_id: String,
    start: usize,
    end: usize,
    pattern_id: String,
}

fn match_key(fragment_id: &str, start: usize, end: usize, pattern_id: &str) -> MatchKey {
    MatchKey {
        fragment_id: fragment_id.to_owned(),
        start,
        end,
        pattern_id: pattern_id.to_owned(),
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
struct PrfCounts {
    tp: usize,
    fp: usize,
    missed: usize,
}

/// True/false positives and misses by exact match-key intersection.
fn prf_counts(predicted: &[MatchKey], actual: &[MatchKey]) -> PrfCounts {
    let tp = predicted.iter().filter(|key| actual.contains(key)).count();
    PrfCounts {
        tp,
        fp: predicted.len() - tp,
        missed: actual.len() - tp,
    }
}

/// `round(numerator / denominator * 1_000_000)` half-up, integer math; 0 on
/// a zero denominator (empty-input convention, documented in the report
/// caption).
fn ppm_half_up(numerator: usize, denominator: usize) -> usize {
    if denominator == 0 {
        return 0;
    }
    (numerator * 2_000_000 + denominator) / (2 * denominator)
}

/// `P = TP/(TP+FP)`, `R = TP/(TP+FN)`, `F1 = 2TP/(2TP+FP+FN)` (count-form
/// of `2PR/(P+R)`), as integer ppm.
fn prf_ppm(counts: PrfCounts) -> (usize, usize, usize) {
    (
        ppm_half_up(counts.tp, counts.tp + counts.fp),
        ppm_half_up(counts.tp, counts.tp + counts.missed),
        ppm_half_up(2 * counts.tp, 2 * counts.tp + counts.fp + counts.missed),
    )
}

#[test]
fn span_prf_counts_and_ppm_match_the_rational() {
    // Tiny toy: 3 predicted keys vs 3 actual keys overlapping on exactly 2
    // gives TP=2, FP=1, FN=1 -> P = R = F1 = 2/3 -> 666667 ppm (round
    // half-up of 666666.67). Sample tables stay empty until T02.
    let predicted = vec![
        match_key("toy-frag", 0, 10, "range_candidate"),
        match_key("toy-frag", 20, 30, "range_candidate"),
        match_key("toy-frag", 40, 50, "marker_chain"),
    ];
    let actual = vec![
        match_key("toy-frag", 0, 10, "range_candidate"),
        match_key("toy-frag", 20, 30, "range_candidate"),
        match_key("toy-frag", 40, 50, "date_docno"),
    ];
    let counts = prf_counts(&predicted, &actual);
    assert_eq!(
        counts,
        PrfCounts {
            tp: 2,
            fp: 1,
            missed: 1
        }
    );
    assert_eq!(
        prf_ppm(counts),
        (666_667, 666_667, 666_667),
        "P = R = F1 = 2/3"
    );
}

// ---------------------------------------------------------------------------
// Closed acceptance envelope reader (S03 analyze_dump style; D328 hand-roll).
// ---------------------------------------------------------------------------

/// The exact closed key set of `npa-lawref-n2-acceptance/v1`.
const ACCEPTANCE_ENVELOPE_KEYS: [&str; 19] = [
    "schema",
    "schema_version",
    "lifecycle",
    "layer1_status",
    "layer2_status",
    "layer3_status",
    "combined_status",
    "alpha_sample",
    "alpha_status",
    "alpha_gate",
    "alpha_formula",
    "span_prf_vs_seed",
    "resolution_coverage",
    "resolution_accuracy",
    "dedup_quality",
    "ds_noise",
    "non_claims",
    "seed_n",
    "fragment_n",
];

/// Substrings the non_claims set must carry: the report may not quietly stop
/// denying the things it must deny (D366 laundering guard).
const MANDATORY_NON_CLAIMS: [&str; 11] = [
    "official-publication",
    "R070",
    "sample ≠ gold",
    "rule-seed",
    "no second annotator",
    "HOLD",
    "no resolution accuracy",
    "no ADR-0028",
    "bounded",
    "not legal interpretation",
    "159/159 is not human F1",
];

/// The exact closed key set of the ds_noise sub-object.
const DS_NOISE_KEYS: [&str; 6] = [
    "n_fragments",
    "verdict",
    "incomplete_ppm",
    "incomplete_fraction",
    "inaccurate_ppm",
    "inaccurate_fraction",
];

/// Parsed view of the acceptance report against the closed envelope.
#[derive(Debug)]
struct AcceptanceView {
    schema: String,
    schema_version: usize,
    lifecycle: String,
    layer1_status: String,
    layer2_status: String,
    layer3_status: String,
    combined_status: String,
    alpha_sample_is_null: bool,
    alpha_status: String,
    alpha_gate: String,
    alpha_formula: String,
    span_prf: SpanPrfView,
    resolution_coverage: CoverageView,
    dedup_quality: DedupView,
    resolution_accuracy_is_null: bool,
    ds_noise: DsNoiseView,
    non_claims: Vec<String>,
    seed_n: usize,
    fragment_n: usize,
}

/// Parsed view of the ds_noise sub-object (S01 rates, integer ppm plus the
/// fraction each ppm was rounded from).
#[derive(Debug)]
struct DsNoiseView {
    n_fragments: usize,
    verdict: String,
    incomplete_ppm: usize,
    incomplete_fraction: String,
    inaccurate_ppm: usize,
    inaccurate_fraction: String,
}

/// Closed-envelope parse of the acceptance report; every violation fails
/// closed naming the key (Q3).
fn analyze_acceptance(text: &str) -> Result<AcceptanceView, String> {
    let inner = text
        .trim()
        .strip_prefix('{')
        .ok_or_else(|| "acceptance report must be a JSON object".to_owned())?
        .strip_suffix('}')
        .ok_or_else(|| "acceptance report must be one closed JSON object".to_owned())?;
    let top = json_object_members(inner)?;
    for (index, (key, _)) in top.iter().enumerate() {
        if top[..index].iter().any(|(seen, _)| seen == key) {
            return Err(format!("acceptance: duplicate key '{key}'"));
        }
    }
    for (key, _) in &top {
        if !ACCEPTANCE_ENVELOPE_KEYS.contains(&key.as_str()) {
            return Err(format!(
                "acceptance: extra key '{key}' is outside the closed npa-lawref-n2-acceptance/v1 envelope"
            ));
        }
    }
    for key in ACCEPTANCE_ENVELOPE_KEYS {
        if !top.iter().any(|(name, _)| name == key) {
            return Err(format!(
                "acceptance: closed envelope is missing key '{key}'"
            ));
        }
    }
    let string_field = |key: &str| acceptance_string_field(&top, key);
    let number_field = |key: &str| acceptance_number_field(&top, key);
    let schema = string_field("schema")?;
    let schema_version = number_field("schema_version")?;
    let lifecycle = string_field("lifecycle")?;
    if lifecycle != "[bounded]" {
        return Err(format!(
            "lifecycle: must stay '[bounded]', got '{lifecycle}'"
        ));
    }
    let combined_status = string_field("combined_status")?;
    if combined_status == "PASS" {
        return Err(
            "combined_status: 'PASS' is not claimable while alpha_sample is unmeasured and the rule-seed is not gold"
                .to_owned(),
        );
    }
    // alpha_sample stays JSON null until a second independent annotator
    // exists; a numeric or string alpha fails closed naming the key (D366).
    let alpha_raw = raw_field(&top, "alpha_sample")?;
    if alpha_raw.trim() != "null" {
        return Err(format!(
            "alpha_sample: must be JSON null (no second annotator exists), got '{alpha_raw}'"
        ));
    }
    // No gold canonical anchors exist, so no resolution accuracy number can
    // appear either.
    let accuracy_raw = raw_field(&top, "resolution_accuracy")?;
    if accuracy_raw.trim() != "null" {
        return Err(format!(
            "resolution_accuracy: must be JSON null (no gold canonical anchors), got '{accuracy_raw}'"
        ));
    }
    let non_claims = acceptance_string_list(raw_field(&top, "non_claims")?)?;
    let joined = non_claims.join("\n");
    for mandatory in MANDATORY_NON_CLAIMS {
        if !joined.contains(mandatory) {
            return Err(format!(
                "non_claims: missing mandatory substring '{mandatory}'"
            ));
        }
    }
    let span_prf = parse_span_prf(raw_field(&top, "span_prf_vs_seed")?)?;
    let resolution_coverage = parse_coverage(raw_field(&top, "resolution_coverage")?)?;
    let dedup_quality = parse_dedup(raw_field(&top, "dedup_quality")?)?;
    let ds_noise = analyze_ds_noise(raw_field(&top, "ds_noise")?)?;
    Ok(AcceptanceView {
        schema,
        schema_version,
        lifecycle,
        layer1_status: string_field("layer1_status")?,
        layer2_status: string_field("layer2_status")?,
        layer3_status: string_field("layer3_status")?,
        combined_status,
        alpha_sample_is_null: true,
        alpha_status: string_field("alpha_status")?,
        alpha_gate: string_field("alpha_gate")?,
        alpha_formula: string_field("alpha_formula")?,
        span_prf,
        resolution_coverage,
        dedup_quality,
        resolution_accuracy_is_null: true,
        ds_noise,
        non_claims,
        seed_n: number_field("seed_n")?,
        fragment_n: number_field("fragment_n")?,
    })
}

/// Raw (untyped) member value of the top-level object.
fn raw_field<'a>(top: &'a [(String, String)], key: &str) -> Result<&'a str, String> {
    top.iter()
        .find(|(name, _)| name == key)
        .map(|(_, value)| value.as_str())
        .ok_or_else(|| format!("acceptance: missing '{key}'"))
}

fn acceptance_string_field(top: &[(String, String)], key: &str) -> Result<String, String> {
    let raw = raw_field(top, key)?;
    let inner = raw
        .trim()
        .strip_prefix('"')
        .ok_or_else(|| format!("'{key}' must be a JSON string"))?
        .strip_suffix('"')
        .ok_or_else(|| format!("'{key}' must be a closed JSON string"))?;
    if inner.contains('\\') {
        return Err(format!("'{key}' must not carry escape sequences"));
    }
    Ok(inner.to_owned())
}

fn acceptance_number_field(top: &[(String, String)], key: &str) -> Result<usize, String> {
    let raw = raw_field(top, key)?;
    raw.trim()
        .parse::<usize>()
        .map_err(|_| format!("'{key}' must be a JSON number, got '{raw}'"))
}

// ---------------------------------------------------------------------------
// T02 closed table parsers: the three computed report objects (Tables A-D).
// ---------------------------------------------------------------------------

/// Closed key set of the span_prf_vs_seed object (Tables A and B).
const SPAN_PRF_KEYS: [&str; 6] = [
    "caption",
    "match_key",
    "provenance",
    "overall",
    "per_pattern",
    "head_token_kind_vs_seed",
];

/// Closed key set of an overall P/R/F1 row (`fn` is the JSON spelling of the
/// false-negative count; the Rust field is `missed` to dodge the keyword).
const PRF_OVERALL_KEYS: [&str; 6] = ["tp", "fp", "fn", "precision_ppm", "recall_ppm", "f1_ppm"];

/// Closed key set of one Table A per-pattern row.
const SPAN_PATTERN_ROW_KEYS: [&str; 4] = ["pattern_id", "tp", "fp", "fn"];

/// Closed key set of the head_token_kind_vs_seed object (Table B).
const HEAD_KIND_KEYS: [&str; 4] = ["caption", "match_key", "rows", "overall"];

/// Closed key set of one Table B row.
const HEAD_KIND_ROW_KEYS: [&str; 5] = ["kind", "n", "tp", "fp", "fn"];

/// Closed key set of the resolution_coverage object (Table C).
const COVERAGE_KEYS: [&str; 5] = [
    "caption",
    "alignment_key",
    "per_pattern",
    "expected_shape_pins",
    "live_degenerate",
];

/// Closed key set of one Table C row.
const COVERAGE_ROW_KEYS: [&str; 5] = [
    "pattern_id",
    "n",
    "n_anchor_some",
    "n_members_pair",
    "n_anchor_none",
];

/// Closed key set of the live_degenerate pin object.
const LIVE_DEGENERATE_KEYS: [&str; 6] = [
    "fragment_id",
    "start",
    "end",
    "pattern_id",
    "classification",
    "counted_as_false_negative",
];

/// Closed key set of the dedup_quality object (Table D).
const DEDUP_KEYS: [&str; 8] = [
    "caption",
    "source",
    "n_groups",
    "n_groups_ge2",
    "n_singletons",
    "art_ctx_group_size",
    "art_ctx_note",
    "presence_pins",
];

/// Overall span-exact P/R/F1: raw counts plus the integer-ppm rates.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct PrfOverall {
    tp: usize,
    fp: usize,
    missed: usize,
    precision_ppm: usize,
    recall_ppm: usize,
    f1_ppm: usize,
}

/// One Table A row: span-exact counts per pattern id.
#[derive(Debug, Clone, PartialEq, Eq)]
struct SpanPatternRow {
    pattern_id: String,
    tp: usize,
    fp: usize,
    missed: usize,
}

/// One Table B row: head-TokenKind counts per closed lexer kind.
#[derive(Debug, Clone, PartialEq, Eq)]
struct HeadKindRow {
    kind: String,
    n: usize,
    tp: usize,
    fp: usize,
    missed: usize,
}

/// Table B: the head-TokenKind diagnostic with its own rule-seed caption.
#[derive(Debug, Clone, PartialEq, Eq)]
struct HeadKindView {
    caption: String,
    match_key: String,
    rows: Vec<HeadKindRow>,
    overall: PrfOverall,
}

/// Tables A+B: the span-exact and head-kind diagnostics vs the rule seed.
#[derive(Debug, Clone, PartialEq, Eq)]
struct SpanPrfView {
    caption: String,
    match_key: String,
    provenance: String,
    overall: PrfOverall,
    per_pattern: Vec<SpanPatternRow>,
    head_token_kind: HeadKindView,
}

/// One Table C row: resolution coverage per pattern id (never accuracy).
#[derive(Debug, Clone, PartialEq, Eq)]
struct CoverageRow {
    pattern_id: String,
    n: usize,
    n_anchor_some: usize,
    n_members_pair: usize,
    n_anchor_none: usize,
}

/// The live degenerate the report pins: an unresolved false range that is
/// never a false negative.
#[derive(Debug, Clone, PartialEq, Eq)]
struct LiveDegenerate {
    fragment_id: String,
    start: usize,
    end: usize,
    pattern_id: String,
    classification: String,
    counted_as_false_negative: bool,
}

/// Table C: Layer-3 coverage shapes with the required non-accuracy caption.
#[derive(Debug, Clone, PartialEq, Eq)]
struct CoverageView {
    caption: String,
    alignment_key: String,
    per_pattern: Vec<CoverageRow>,
    expected_shape_pins: Vec<String>,
    live_degenerate: LiveDegenerate,
}

/// Table D: canonical-dedup quality counted over the tracked S03 dump.
#[derive(Debug, Clone, PartialEq, Eq)]
struct DedupView {
    caption: String,
    source: String,
    n_groups: usize,
    n_groups_ge2: usize,
    n_singletons: usize,
    art_ctx_group_size: usize,
    art_ctx_note: String,
    presence_pins: Vec<String>,
}

/// Members of a raw JSON object validated against a closed key set: no
/// duplicates, no extras, none missing. Every violation names the key (Q3).
fn closed_members(raw: &str, label: &str, keys: &[&str]) -> Result<Vec<(String, String)>, String> {
    let members = json_object_members(object_body(raw)?)?;
    for (index, (key, _)) in members.iter().enumerate() {
        if members[..index].iter().any(|(seen, _)| seen == key) {
            return Err(format!("{label}: duplicate key '{key}'"));
        }
    }
    for (key, _) in &members {
        if !keys.contains(&key.as_str()) {
            return Err(format!(
                "{label}: extra key '{key}' is outside the closed table envelope"
            ));
        }
    }
    for key in keys {
        if !members.iter().any(|(name, _)| name == key) {
            return Err(format!("{label}: closed envelope is missing key '{key}'"));
        }
    }
    Ok(members)
}

/// A caption must carry every required substring (the non-claim the table
/// cannot quietly stop making).
fn require_caption_substrings(label: &str, caption: &str, needles: &[&str]) -> Result<(), String> {
    for needle in needles {
        if !caption.contains(needle) {
            return Err(format!("{label}: caption must carry '{needle}'"));
        }
    }
    Ok(())
}

/// JSON boolean field of a raw member value.
fn acceptance_bool_field(members: &[(String, String)], key: &str) -> Result<bool, String> {
    match raw_field(members, key)?.trim() {
        "true" => Ok(true),
        "false" => Ok(false),
        other => Err(format!("'{key}' must be a JSON boolean, got '{other}'")),
    }
}

/// Parses an overall P/R/F1 row.
fn parse_prf_overall(raw: &str, label: &str) -> Result<PrfOverall, String> {
    let members = closed_members(raw, label, &PRF_OVERALL_KEYS)?;
    let number = |key: &str| acceptance_number_field(&members, key);
    Ok(PrfOverall {
        tp: number("tp")?,
        fp: number("fp")?,
        missed: number("fn")?,
        precision_ppm: number("precision_ppm")?,
        recall_ppm: number("recall_ppm")?,
        f1_ppm: number("f1_ppm")?,
    })
}

/// Parses Table B (head TokenKind vs the seed's stored kind).
fn parse_head_kind(raw: &str) -> Result<HeadKindView, String> {
    const LABEL: &str = "span_prf_vs_seed.head_token_kind_vs_seed";
    let members = closed_members(raw, LABEL, &HEAD_KIND_KEYS)?;
    let caption = acceptance_string_field(&members, "caption")?;
    require_caption_substrings(LABEL, &caption, &["provenance=rule-seed", "not gold"])?;
    let mut rows = Vec::new();
    for item in json_array_items(raw_field(&members, "rows")?)? {
        let row_members = closed_members(item, &format!("{LABEL} row"), &HEAD_KIND_ROW_KEYS)?;
        let number = |key: &str| acceptance_number_field(&row_members, key);
        rows.push(HeadKindRow {
            kind: acceptance_string_field(&row_members, "kind")?,
            n: number("n")?,
            tp: number("tp")?,
            fp: number("fp")?,
            missed: number("fn")?,
        });
    }
    Ok(HeadKindView {
        caption,
        match_key: acceptance_string_field(&members, "match_key")?,
        rows,
        overall: parse_prf_overall(raw_field(&members, "overall")?, &format!("{LABEL}.overall"))?,
    })
}

/// Parses Tables A+B (span-exact P/R/F1 plus the head-TokenKind table).
fn parse_span_prf(raw: &str) -> Result<SpanPrfView, String> {
    const LABEL: &str = "span_prf_vs_seed";
    let members = closed_members(raw, LABEL, &SPAN_PRF_KEYS)?;
    let caption = acceptance_string_field(&members, "caption")?;
    require_caption_substrings(
        LABEL,
        &caption,
        &[
            "provenance=rule-seed",
            "not gold",
            "not Layer-2 acceptance",
            "human-recall diagnostic",
        ],
    )?;
    let provenance = acceptance_string_field(&members, "provenance")?;
    if provenance != "rule-seed" {
        return Err(format!(
            "{LABEL}: provenance must stay 'rule-seed', got '{provenance}'"
        ));
    }
    let mut per_pattern = Vec::new();
    for item in json_array_items(raw_field(&members, "per_pattern")?)? {
        let row_members = closed_members(item, &format!("{LABEL} row"), &SPAN_PATTERN_ROW_KEYS)?;
        let number = |key: &str| acceptance_number_field(&row_members, key);
        per_pattern.push(SpanPatternRow {
            pattern_id: acceptance_string_field(&row_members, "pattern_id")?,
            tp: number("tp")?,
            fp: number("fp")?,
            missed: number("fn")?,
        });
    }
    Ok(SpanPrfView {
        caption,
        match_key: acceptance_string_field(&members, "match_key")?,
        provenance,
        overall: parse_prf_overall(raw_field(&members, "overall")?, &format!("{LABEL}.overall"))?,
        per_pattern,
        head_token_kind: parse_head_kind(raw_field(&members, "head_token_kind_vs_seed")?)?,
    })
}

/// Parses Table C (Layer-3 coverage, never accuracy).
fn parse_coverage(raw: &str) -> Result<CoverageView, String> {
    const LABEL: &str = "resolution_coverage";
    let members = closed_members(raw, LABEL, &COVERAGE_KEYS)?;
    let caption = acceptance_string_field(&members, "caption")?;
    require_caption_substrings(
        LABEL,
        &caption,
        &["coverage over the seed sample", "not gold-anchor accuracy"],
    )?;
    let mut per_pattern = Vec::new();
    for item in json_array_items(raw_field(&members, "per_pattern")?)? {
        let row_members = closed_members(item, &format!("{LABEL} row"), &COVERAGE_ROW_KEYS)?;
        let number = |key: &str| acceptance_number_field(&row_members, key);
        per_pattern.push(CoverageRow {
            pattern_id: acceptance_string_field(&row_members, "pattern_id")?,
            n: number("n")?,
            n_anchor_some: number("n_anchor_some")?,
            n_members_pair: number("n_members_pair")?,
            n_anchor_none: number("n_anchor_none")?,
        });
    }
    let degenerate_members = closed_members(
        raw_field(&members, "live_degenerate")?,
        &format!("{LABEL}.live_degenerate"),
        &LIVE_DEGENERATE_KEYS,
    )?;
    let degenerate_string = |key: &str| acceptance_string_field(&degenerate_members, key);
    Ok(CoverageView {
        caption,
        alignment_key: acceptance_string_field(&members, "alignment_key")?,
        per_pattern,
        expected_shape_pins: acceptance_string_list(raw_field(&members, "expected_shape_pins")?)?,
        live_degenerate: LiveDegenerate {
            fragment_id: degenerate_string("fragment_id")?,
            start: acceptance_number_field(&degenerate_members, "start")?,
            end: acceptance_number_field(&degenerate_members, "end")?,
            pattern_id: degenerate_string("pattern_id")?,
            classification: degenerate_string("classification")?,
            counted_as_false_negative: acceptance_bool_field(
                &degenerate_members,
                "counted_as_false_negative",
            )?,
        },
    })
}

/// Parses Table D (S03-dump dedup counts).
fn parse_dedup(raw: &str) -> Result<DedupView, String> {
    const LABEL: &str = "dedup_quality";
    let members = closed_members(raw, LABEL, &DEDUP_KEYS)?;
    let caption = acceptance_string_field(&members, "caption")?;
    require_caption_substrings(
        LABEL,
        &caption,
        &[
            "art_ctx",
            "NOT a quality win",
            "no gold",
            "S03 shipped grouping",
        ],
    )?;
    let number = |key: &str| acceptance_number_field(&members, key);
    Ok(DedupView {
        caption,
        source: acceptance_string_field(&members, "source")?,
        n_groups: number("n_groups")?,
        n_groups_ge2: number("n_groups_ge2")?,
        n_singletons: number("n_singletons")?,
        art_ctx_group_size: number("art_ctx_group_size")?,
        art_ctx_note: acceptance_string_field(&members, "art_ctx_note")?,
        presence_pins: acceptance_string_list(raw_field(&members, "presence_pins")?)?,
    })
}

/// Closed parse of the ds_noise sub-object.
fn analyze_ds_noise(raw: &str) -> Result<DsNoiseView, String> {
    let members = json_object_members(object_body(raw)?)?;
    for (key, _) in &members {
        if !DS_NOISE_KEYS.contains(&key.as_str()) {
            return Err(format!(
                "ds_noise: extra key '{key}' is outside the closed envelope"
            ));
        }
    }
    for key in DS_NOISE_KEYS {
        if !members.iter().any(|(name, _)| name == key) {
            return Err(format!("ds_noise: closed envelope is missing key '{key}'"));
        }
    }
    let number = |key: &str| acceptance_number_field(&members, key);
    let string = |key: &str| acceptance_string_field(&members, key);
    Ok(DsNoiseView {
        n_fragments: number("n_fragments")?,
        verdict: string("verdict")?,
        incomplete_ppm: number("incomplete_ppm")?,
        incomplete_fraction: string("incomplete_fraction")?,
        inaccurate_ppm: number("inaccurate_ppm")?,
        inaccurate_fraction: string("inaccurate_fraction")?,
    })
}

/// Members of a raw JSON object body (string-aware, depth-aware).
fn json_object_members(body: &str) -> Result<Vec<(String, String)>, String> {
    let bytes = body.as_bytes();
    let mut cursor = 0usize;
    let mut members = Vec::new();
    loop {
        while cursor < bytes.len() && (bytes[cursor].is_ascii_whitespace() || bytes[cursor] == b',')
        {
            cursor += 1;
        }
        if cursor >= bytes.len() {
            return Ok(members);
        }
        if bytes[cursor] != b'"' {
            return Err(format!(
                "acceptance member {cursor} must open with a quoted key"
            ));
        }
        let (key, next) = json_string_at(body, cursor)?;
        cursor = next;
        while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() {
            cursor += 1;
        }
        if bytes.get(cursor) != Some(&b':') {
            return Err(format!("acceptance key '{key}' must be followed by ':'"));
        }
        cursor += 1;
        while cursor < bytes.len() && bytes[cursor].is_ascii_whitespace() {
            cursor += 1;
        }
        let end = json_value_end(body, cursor)?;
        members.push((key, body[cursor..end].to_owned()));
        cursor = end;
    }
}

/// Reads the `"..."` string starting at `start`; returns the value and the
/// end offset. Escapes fail closed.
fn json_string_at(text: &str, start: usize) -> Result<(String, usize), String> {
    let bytes = text.as_bytes();
    if bytes.get(start) != Some(&b'"') {
        return Err("expected a JSON string".to_owned());
    }
    let mut value = String::new();
    let mut cursor = start + 1;
    while let Some(&byte) = bytes.get(cursor) {
        match byte {
            b'"' => return Ok((value, cursor + 1)),
            b'\\' => return Err("acceptance strings must not carry escape sequences".to_owned()),
            _ => {
                let ch = text[cursor..]
                    .chars()
                    .next()
                    .ok_or_else(|| "invalid string boundary".to_owned())?;
                value.push(ch);
                cursor += ch.len_utf8();
            }
        }
    }
    Err("unterminated JSON string".to_owned())
}

/// End offset of the JSON value starting at `start` (string, number, null
/// literal, array, or object; balanced and string-aware). Anything else
/// fails closed.
fn json_value_end(text: &str, start: usize) -> Result<usize, String> {
    match text.as_bytes().get(start) {
        Some(b'"') => json_string_at(text, start).map(|(_, end)| end),
        Some(byte) if byte.is_ascii_digit() => {
            let mut end = start;
            while text
                .as_bytes()
                .get(end)
                .is_some_and(|byte| byte.is_ascii_digit())
            {
                end += 1;
            }
            if text.as_bytes().get(end) == Some(&b'.') {
                end += 1;
                while text
                    .as_bytes()
                    .get(end)
                    .is_some_and(|byte| byte.is_ascii_digit())
                {
                    end += 1;
                }
            }
            if matches!(text.as_bytes().get(end), Some(b'e') | Some(b'E')) {
                end += 1;
                if matches!(text.as_bytes().get(end), Some(b'+') | Some(b'-')) {
                    end += 1;
                }
                while text
                    .as_bytes()
                    .get(end)
                    .is_some_and(|byte| byte.is_ascii_digit())
                {
                    end += 1;
                }
            }
            Ok(end)
        }
        Some(b'n') if text[start..].starts_with("null") => Ok(start + 4),
        Some(b't') if text[start..].starts_with("true") => Ok(start + 4),
        Some(b'f') if text[start..].starts_with("false") => Ok(start + 5),
        Some(open @ (b'[' | b'{')) => {
            let close = if *open == b'[' { b']' } else { b'}' };
            let mut depth = 0usize;
            let mut in_string = false;
            let mut cursor = start;
            while let Some(&byte) = text.as_bytes().get(cursor) {
                if in_string {
                    match byte {
                        b'\\' => {
                            return Err(
                                "acceptance strings must not carry escape sequences".to_owned()
                            )
                        }
                        b'"' => in_string = false,
                        _ => {}
                    }
                } else {
                    match byte {
                        b'"' => in_string = true,
                        b'[' | b'{' => depth += 1,
                        b']' | b'}' => {
                            depth -= 1;
                            if depth == 0 && byte == close {
                                return Ok(cursor + 1);
                            }
                        }
                        _ => {}
                    }
                }
                cursor += 1;
            }
            Err("unterminated JSON container".to_owned())
        }
        _ => Err(format!("unsupported JSON value at byte {start}")),
    }
}

/// Top-level items of a raw JSON array (string-aware, depth-aware split).
fn json_array_items(raw: &str) -> Result<Vec<&str>, String> {
    let trimmed = raw.trim();
    let inner = trimmed
        .strip_prefix('[')
        .ok_or_else(|| format!("expected a JSON array, got: {trimmed}"))?
        .strip_suffix(']')
        .ok_or_else(|| "unterminated JSON array".to_owned())?;
    let mut items = Vec::new();
    let mut depth = 0usize;
    let mut in_string = false;
    let mut start: Option<usize> = None;
    for (offset, &byte) in inner.as_bytes().iter().enumerate() {
        if in_string {
            match byte {
                b'\\' => {
                    return Err("acceptance strings must not carry escape sequences".to_owned())
                }
                b'"' => in_string = false,
                _ => {}
            }
            continue;
        }
        match byte {
            b'"' => {
                in_string = true;
                start = start.or(Some(offset));
            }
            b'[' | b'{' => {
                depth += 1;
                start = start.or(Some(offset));
            }
            b']' | b'}' => depth -= 1,
            b',' if depth == 0 => {
                if let Some(begin) = start.take() {
                    items.push(inner[begin..offset].trim());
                }
            }
            byte if byte.is_ascii_whitespace() => {}
            _ => start = start.or(Some(offset)),
        }
    }
    if in_string {
        return Err("unterminated JSON string".to_owned());
    }
    if let Some(begin) = start {
        items.push(inner[begin..].trim());
    }
    Ok(items.into_iter().filter(|item| !item.is_empty()).collect())
}

fn object_body(raw: &str) -> Result<&str, String> {
    raw.trim()
        .strip_prefix('{')
        .ok_or_else(|| format!("expected a JSON object, got: {raw}"))?
        .strip_suffix('}')
        .ok_or_else(|| "unterminated JSON object".to_owned())
}

fn acceptance_string_list(raw: &str) -> Result<Vec<String>, String> {
    json_array_items(raw)?
        .iter()
        .map(|item| {
            let inner = item
                .strip_prefix('"')
                .ok_or_else(|| format!("non_claims item must be a JSON string: {item}"))?
                .strip_suffix('"')
                .ok_or_else(|| "non_claims item must be a closed JSON string".to_owned())?;
            if inner.contains('\\') {
                return Err("non_claims must not carry escape sequences".to_owned());
            }
            Ok(inner.to_owned())
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Green / hostile pins over the tracked skeleton.
// ---------------------------------------------------------------------------

/// The T02-filled report parses against the closed envelope and holds the
/// laundering guard: alpha null, HOLD layer-2, INCONCLUSIVE layer-3,
/// NOT_PASS combined, the required rule-seed captions, and the ds-noise
/// rates as integer ppm with the exact fractions each ppm was rounded from.
#[test]
fn acceptance_schema_accepts_null_alpha_sample_with_hold_status() {
    let text = fs::read_to_string(acceptance_report_path())
        .expect("the tracked N2 acceptance report must be readable");
    let view =
        analyze_acceptance(&text).expect("the report must parse against the closed envelope");
    assert_eq!(view.schema, "npa-lawref-n2-acceptance/v1");
    assert_eq!(view.schema_version, 1);
    assert_eq!(view.lifecycle, "[bounded]");
    assert_eq!(
        view.layer1_status, "PASS",
        "Layer-1 is cited from D363, not remeasured here"
    );
    assert_eq!(view.layer2_status, "HOLD");
    assert_eq!(view.layer3_status, "INCONCLUSIVE");
    assert_eq!(view.combined_status, "NOT_PASS");
    assert!(
        view.alpha_sample_is_null,
        "sample alpha stays unmeasured: no second annotator exists"
    );
    assert!(
        view.non_claims.len() >= MANDATORY_NON_CLAIMS.len(),
        "the report carries at least the mandatory non-claims"
    );
    assert_eq!(view.alpha_status, "not-computed-no-second-annotator");
    assert_eq!(view.alpha_gate, "HOLD");
    assert_eq!(
        view.alpha_formula,
        "krippendorff-nominal-two-rater-coincidence/v1"
    );
    assert!(
        view.resolution_accuracy_is_null,
        "no gold anchors, so no resolution accuracy claim"
    );
    // T02 tables: the required rule-seed captions plus the headline pins.
    for needle in [
        "provenance=rule-seed",
        "not gold",
        "not Layer-2 acceptance",
        "human-recall diagnostic",
    ] {
        assert!(
            view.span_prf.caption.contains(needle),
            "the span caption must carry '{needle}', got: {}",
            view.span_prf.caption
        );
    }
    assert_eq!(view.span_prf.provenance, "rule-seed");
    assert_eq!(view.span_prf.overall.tp, 159);
    assert_eq!(view.span_prf.overall.fp, 0);
    assert_eq!(view.span_prf.overall.missed, 0);
    assert_eq!(
        (
            view.span_prf.overall.precision_ppm,
            view.span_prf.overall.recall_ppm,
            view.span_prf.overall.f1_ppm
        ),
        (1_000_000, 1_000_000, 1_000_000),
        "159/159 record parity pins all three rates at 1000000 ppm"
    );
    assert_eq!(view.span_prf.head_token_kind.overall.tp, 159);
    assert_eq!(
        view.resolution_coverage.live_degenerate.classification,
        "unresolved-false-range"
    );
    assert!(
        !view
            .resolution_coverage
            .live_degenerate
            .counted_as_false_negative,
        "the false range is coverage-None, never a false negative"
    );
    assert_eq!(
        view.dedup_quality.n_groups,
        view.dedup_quality.n_groups_ge2 + view.dedup_quality.n_singletons
    );
    for needle in [
        "art_ctx",
        "NOT a quality win",
        "no gold",
        "S03 shipped grouping",
    ] {
        assert!(
            view.dedup_quality.caption.contains(needle),
            "the dedup caption must carry '{needle}', got: {}",
            view.dedup_quality.caption
        );
    }
    assert_eq!(view.ds_noise.n_fragments, 20);
    assert_eq!(view.ds_noise.verdict, "do-not-treat-as-gold");
    assert_eq!(
        view.ds_noise.incomplete_ppm, 466_667,
        "21/45 = 466666.67 ppm, round half-up"
    );
    assert_eq!(view.ds_noise.incomplete_fraction, "21/45");
    assert_eq!(
        view.ds_noise.inaccurate_ppm, 83_333,
        "2/24 = 83333.33 ppm, round half-up"
    );
    assert_eq!(view.ds_noise.inaccurate_fraction, "2/24");
    assert_eq!(view.seed_n, 159);
    assert_eq!(view.fragment_n, 180);
}

/// D366 laundering guard: a numeric alpha_sample fails closed naming the
/// key - 0.8, 1, and the quoted "1.0" are all rejections.
#[test]
fn acceptance_schema_rejects_numeric_alpha_sample() {
    let text = fs::read_to_string(acceptance_report_path()).expect("read the skeleton");
    for hostile in ["0.8", "1", "\"1.0\""] {
        let mutated = text.replacen(
            "\"alpha_sample\": null",
            &format!("\"alpha_sample\": {hostile}"),
            1,
        );
        assert_ne!(mutated, text, "the hostile mutation must change the report");
        let error =
            analyze_acceptance(&mutated).expect_err("a numeric alpha_sample must fail closed");
        assert!(
            error.contains("alpha_sample"),
            "expected the alpha_sample rejection to name the key, got: {error}"
        );
    }
}

#[test]
fn acceptance_schema_rejects_extra_key_naming_it() {
    let text = fs::read_to_string(acceptance_report_path()).expect("read the skeleton");
    let mutated = text.replacen('{', "{\n  \"future_hint\": 1,", 1);
    assert_ne!(mutated, text, "the hostile mutation must change the report");
    let error = analyze_acceptance(&mutated).expect_err("an extra key must fail closed");
    assert!(
        error.contains("future_hint") && error.contains("extra key"),
        "expected the extra-key rejection to name the key, got: {error}"
    );
}

#[test]
fn acceptance_schema_rejects_pass_combined_status() {
    let text = fs::read_to_string(acceptance_report_path()).expect("read the skeleton");
    let mutated = text.replacen(
        "\"combined_status\": \"NOT_PASS\"",
        "\"combined_status\": \"PASS\"",
        1,
    );
    assert_ne!(mutated, text, "the hostile mutation must change the report");
    let error = analyze_acceptance(&mutated).expect_err("a PASS combined status must fail closed");
    assert!(
        error.contains("combined_status"),
        "expected the PASS rejection to name the key, got: {error}"
    );
}

#[test]
fn acceptance_schema_rejects_unbounded_lifecycle() {
    let text = fs::read_to_string(acceptance_report_path()).expect("read the skeleton");
    let mutated = text.replacen(
        "\"lifecycle\": \"[bounded]\"",
        "\"lifecycle\": \"[open]\"",
        1,
    );
    assert_ne!(mutated, text, "the hostile mutation must change the report");
    let error = analyze_acceptance(&mutated).expect_err("an unbounded lifecycle must fail closed");
    assert!(
        error.contains("lifecycle"),
        "expected the lifecycle rejection to name the key, got: {error}"
    );
}

/// The S01 ds-noise report keeps its sample-contract invariant: the alpha
/// gate belongs to S04, so that file must never bind α to '=' or an ASCII
/// digit. This suite only re-reads the tracked md; it is never written.
#[test]
fn ds_noise_report_still_binds_no_alpha_number() {
    let text = fs::read_to_string(ds_noise_report_path()).expect("read the S01 ds-noise report");
    for (index, ch) in text.char_indices() {
        if ch == 'α' {
            let after = text[index + ch.len_utf8()..].trim_start();
            assert!(
                !(after.starts_with('=') || after.starts_with(|c: char| c.is_ascii_digit())),
                "ds-noise.md must not bind α to a number (the alpha gate belongs to S04)"
            );
        }
    }
}

/// The T01 freeze: the capture module stays vocabulary-frozen and ln-decode
/// gains no reporting dependencies (style copied from the S03
/// `resolution_freeze_pins_hold`).
#[test]
fn acceptance_freeze_pins_hold() {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let cargo_toml = fs::read_to_string(manifest_dir.join("Cargo.toml")).expect("read Cargo.toml");
    for dependency in ["serde", "clap", "walkdir", "krippendorff"] {
        assert!(
            !cargo_toml.contains(dependency),
            "ln-decode must not gain a '{dependency}' dependency (hand-rolled readers and formulas, D328)"
        );
    }
    let lawref_src = fs::read_to_string(manifest_dir.join("src/lawref.rs")).expect("read lawref");
    for vocabulary in ["eId", "canonical_anchor", "resolve_anaphora"] {
        assert!(
            !lawref_src.contains(vocabulary),
            "the capture module must stay frozen against '{vocabulary}' (the resolution vocabulary lives in lawref_resolve)"
        );
    }
}

// ---------------------------------------------------------------------------
// (h) T02 live sample: the tiny hand-rolled seed/manifest readers copied
//     verbatim from `npa_lawref_capture_contract.rs` (no `#[path]` include,
//     D335) over the frozen 180-fragment / 159-record sample.
// ---------------------------------------------------------------------------

/// Tracked fragment fixture directory (the capture-contract path idiom).
fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

/// Repo-root-relative path of the tracked S03 resolution demo dump. Table D
/// reads it and never regenerates it (the S03 generator stays ignored).
fn resolution_dump_path() -> PathBuf {
    evidence_dir().join("m199-s03-resolution-demo.json")
}

/// Reads `": \"value\""` starting just after a JSON key token. The tracked
/// seed/manifest strings carry no escape sequences; any escape fails loudly.
fn json_string_after_colon(rest: &str) -> Option<String> {
    let rest = rest.trim_start().strip_prefix(':')?.trim_start();
    let rest = rest.strip_prefix('"')?;
    let mut value = String::new();
    for ch in rest.chars() {
        match ch {
            '"' => return Some(value),
            '\\' => return None,
            _ => value.push(ch),
        }
    }
    None
}

/// Value of `"key": "..."` anywhere in the record line.
fn json_string_field(line: &str, key: &str) -> Option<String> {
    let needle = format!("\"{key}\"");
    let found = line.find(&needle)?;
    json_string_after_colon(&line[found + needle.len()..])
}

/// Numeric value of `"key": <digits>` anywhere in the record line.
fn json_number_field(line: &str, key: &str) -> Option<usize> {
    let needle = format!("\"{key}\"");
    let found = line.find(&needle)?;
    let rest = line[found + needle.len()..].trim_start();
    let rest = rest.strip_prefix(':')?.trim_start();
    let digits: String = rest.chars().take_while(|ch| ch.is_ascii_digit()).collect();
    digits.parse().ok()
}

/// Comparison record: fragment identity + offsets + pattern id + slots
/// (Q3: never the fragment text itself). Copied verbatim.
#[derive(Debug, PartialEq, Eq, Clone)]
struct CaptureRecord {
    fragment_id: String,
    start: usize,
    end: usize,
    pattern_id: String,
    slots: LawRefSlots,
}

/// One hand-parsed `m199-s01-rule-seed.jsonl` record (D328: no serde).
fn parse_seed_record(line: &str) -> CaptureRecord {
    let needle = "\"slots\":";
    let found = line.find(needle).expect("seed record must carry slots");
    let body = &line[found + needle.len()..];
    let open = body.find('{').expect("slots must be an object");
    // Balanced-brace close: the only nesting is the range object.
    let mut depth = 0usize;
    let mut close = open;
    for (offset, ch) in body[open..].char_indices() {
        match ch {
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    close = open + offset;
                    break;
                }
            }
            _ => {}
        }
    }
    let mut slots = LawRefSlots::default();
    for member in json_top_level_members(&body[open + 1..close]) {
        let (name, value) = member.split_once(':').expect("slot member key: value");
        let name = name.trim().trim_matches('"');
        let value = value.trim();
        match name {
            "marker_chain" => slots.marker_chain = json_string_list(value).expect("marker_chain"),
            "hier_nums" => slots.hier_nums = json_string_list(value).expect("hier_nums"),
            "date" => slots.date = json_opt_string(value),
            "doc_no" => slots.doc_no = json_opt_string(value),
            "law_code" => slots.law_code = json_opt_string(value),
            "anaphora" => slots.anaphora = json_opt_string(value),
            "quoted_enum" => slots.quoted_enum = json_opt_string(value),
            "range" => slots.range = json_opt_range(value),
            other => panic!("unknown seed slot key '{other}'"),
        }
    }
    CaptureRecord {
        fragment_id: json_string_field(line, "fragment_id").expect("seed record fragment_id"),
        start: json_number_field(line, "start").expect("seed record start"),
        end: json_number_field(line, "end").expect("seed record end"),
        pattern_id: json_string_field(line, "pattern_id").expect("seed record pattern_id"),
        slots,
    }
}

/// Splits a JSON object body on top-level commas (nesting is only the range
/// object and the string lists; tracked seed strings carry no escapes).
fn json_top_level_members(body: &str) -> Vec<&str> {
    let mut members = Vec::new();
    let mut depth = 0usize;
    let mut in_string = false;
    let mut start = 0usize;
    for (offset, ch) in body.char_indices() {
        match ch {
            '"' => in_string = !in_string,
            '[' | '{' if !in_string => depth += 1,
            ']' | '}' if !in_string => depth -= 1,
            ',' if !in_string && depth == 0 => {
                members.push(body[start..offset].trim());
                start = offset + 1;
            }
            _ => {}
        }
    }
    let tail = body[start..].trim();
    if !tail.is_empty() {
        members.push(tail);
    }
    members
}

fn json_string_list(value: &str) -> Option<Vec<String>> {
    let inner = value.strip_prefix('[')?.strip_suffix(']')?.trim();
    if inner.is_empty() {
        return Some(Vec::new());
    }
    inner
        .split(',')
        .map(|item| json_string_scalar(item.trim()))
        .collect()
}

fn json_string_scalar(value: &str) -> Option<String> {
    let body = value.strip_prefix('"')?.strip_suffix('"')?;
    body.find('\\').is_none().then(|| body.to_owned())
}

fn json_opt_string(value: &str) -> Option<String> {
    if value == "null" {
        None
    } else {
        json_string_scalar(value)
    }
}

fn json_opt_range(value: &str) -> Option<(String, String)> {
    let inner = value.strip_prefix('{')?.strip_suffix('}')?.trim();
    let mut from = None;
    let mut to = None;
    for member in json_top_level_members(inner) {
        let (name, value) = member.split_once(':').expect("range member key: value");
        match name.trim().trim_matches('"') {
            "from" => from = Some(json_string_scalar(value.trim()).expect("range.from")),
            "to" => to = Some(json_string_scalar(value.trim()).expect("range.to")),
            other => panic!("unknown range member '{other}'"),
        }
    }
    Some((from.expect("range.from"), to.expect("range.to")))
}

/// Hand-rolled manifest reader (D328: no serde): the (`id`, `file`) pairs of
/// the `fragments` array in document order. Anchored on the array so the
/// strata/documents entries carrying ids are never picked up.
fn manifest_fragments(manifest: &str) -> Vec<(String, String)> {
    let anchor = manifest
        .find("\"fragments\"")
        .expect("manifest must index a fragments array");
    let array_start = anchor
        + manifest[anchor..]
            .find('[')
            .expect("fragments must be an array");
    let mut depth = 0usize;
    let mut array_end = manifest.len();
    for (offset, byte) in manifest.as_bytes()[array_start..].iter().enumerate() {
        match byte {
            b'[' => depth += 1,
            b']' => {
                depth -= 1;
                if depth == 0 {
                    array_end = array_start + offset;
                    break;
                }
            }
            _ => {}
        }
    }
    let body = &manifest[array_start + 1..array_end];
    let mut fragments = Vec::new();
    let mut cursor = 0usize;
    while let Some(found) = body[cursor..].find("\"id\"") {
        let after = cursor + found + "\"id\"".len();
        let Some(id) = json_string_after_colon(&body[after..]) else {
            break;
        };
        let Some(file_found) = body[after..].find("\"file\"") else {
            break;
        };
        let Some(file) = json_string_after_colon(&body[after + file_found + "\"file\"".len()..])
        else {
            break;
        };
        assert!(
            file == format!("{id}.txt"),
            "manifest file field must mirror the fragment id: {id} vs {file}"
        );
        fragments.push((id, file));
        cursor = after;
    }
    fragments
}

/// One seed row extended by the head TokenKind the seed already stores
/// (Table B reads it; the slots stay for the amendment-window shape pin).
#[derive(Debug, Clone, PartialEq, Eq)]
struct SeedRecord {
    fragment_id: String,
    start: usize,
    end: usize,
    kind: String,
    pattern_id: String,
    slots: LawRefSlots,
}

/// Parses one seed row: the copied record reader plus the `kind` field.
fn parse_seed_row(line: &str) -> SeedRecord {
    let record = parse_seed_record(line);
    SeedRecord {
        kind: json_string_field(line, "kind").expect("seed record kind"),
        fragment_id: record.fragment_id,
        start: record.start,
        end: record.end,
        pattern_id: record.pattern_id,
        slots: record.slots,
    }
}

/// The frozen sample: the 180 manifest fragments plus the 159 seed records.
struct LiveSample {
    fragments: Vec<(String, String)>,
    seed: Vec<SeedRecord>,
}

fn load_sample() -> LiveSample {
    let manifest = fs::read_to_string(evidence_dir().join("m199-s01-gold-sample-manifest.json"))
        .expect("read the S01 gold sample manifest");
    let fragments = manifest_fragments(&manifest);
    assert_eq!(
        fragments.len(),
        180,
        "the sample manifest must index the 180 tracked fragments"
    );
    let seed_src = fs::read_to_string(evidence_dir().join("m199-s01-rule-seed.jsonl"))
        .expect("read the S01 rule seed");
    let seed: Vec<SeedRecord> = seed_src
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(parse_seed_row)
        .collect();
    assert_eq!(seed.len(), 159, "the rule seed holds 159 records");
    LiveSample { fragments, seed }
}

// ---------------------------------------------------------------------------
// (i) T02 Tables A-D: the live computation over the sample and the dump.
// ---------------------------------------------------------------------------

/// Plan-pinned seed histogram (the 159 records decompose exactly like this).
const SEED_HIST: [(&str, usize); 7] = [
    ("range_candidate", 33),
    ("date-docno-window", 32),
    ("abbrev-hier-chain", 32),
    ("anaphora_candidate", 28),
    ("fullword-ref", 26),
    ("abbrev-amendment-window", 6),
    ("quoted-enum", 2),
];

/// Table B rows in plan order.
const HEAD_KIND_ORDER: [&str; 4] = ["Abbrev", "Word", "HierNum", "Date"];

/// Required span caption (Table A): diagnostic vs the rule seed, never gold,
/// with the DS-noise human-recall diagnostic called out.
const SPAN_CAPTION: &str = "Diagnostic span-exact P/R/F1 vs provenance=rule-seed, not gold: the 159/159 record-for-record parity is the S02 construction pin, not human F1 and not Layer-2 acceptance. The DS-noise 46.7 percent incomplete rate on the 20-fragment subsample remains the human-recall diagnostic.";

/// The Table A/B match key (protocol kind = pattern_id, never TokenKind).
const SPAN_MATCH_KEY: &str = "(fragment_id, start, end, pattern_id)";

/// Required head-kind caption (Table B): same rule-seed discipline.
const HEAD_CAPTION: &str = "Head-TokenKind diagnostic vs provenance=rule-seed, not gold: the seed kind column comes from the same rule harvest, so the 159/159 parity makes this F1 exactly 1.0 by construction; it is not Layer-2 acceptance.";

/// The Table B match key: head = first TokenKind, actual = the seed kind.
const HEAD_MATCH_KEY: &str = "(fragment_id, start, end, pattern_id); predicted head = first TokenKind of the capture token_kind_seq, actual = the seed kind";

/// Required coverage caption (Table C): coverage over the seed sample, never
/// gold-anchor accuracy.
const COVERAGE_CAPTION: &str = "Layer-3 coverage over the seed sample, not gold-anchor accuracy: no gold canonical anchors exist, resolution_accuracy stays null, and R070 amendment and date windows stay out of scope. Coverage counts observable shapes and never correctness.";

/// The observable shape pins Table C carries (the live-verifiable ones are
/// asserted inside `compute_coverage` while counting).
const EXPECTED_SHAPE_PINS: [&str; 6] = [
    "abbrev-amendment-window: every seed capture stays anchor=None (R070 amendment windows out of scope)",
    "date-docno-window: every seed capture stays anchor=None (R070 date-docno windows out of scope)",
    "range_candidate with equal endpoints continuing a hyphen split: anchor=None, members=[] - a false range, never a Layer-3 miss",
    "document-level anaphora (Кодекса / Положения / закона / Федерального): anchor=None - the doc sink never mints doc_*",
    "настоящей статьи anaphora: art_ctx as the honest missing-frame token, or the stacked art_N frame when one exists",
    "ranges resolve as the expanded ENDPOINT PAIR (exactly two members), never an integer enumeration",
];

/// Required dedup caption (Table D): counted, not claimed; art_ctx is not a
/// quality win.
const DEDUP_CAPTION: &str = "Canonical-dedup quality counted over the tracked S03 dump - a read-only projection, never a second canon and never regenerated here: S03 shipped grouping and this table only counts it; no gold exists, so no precision of grouping is claimed. The art_ctx group is the honest missing-frame token and its size is NOT a quality win (the dump's synthetic roadmap demo groups are counted dump-wide).";

/// Where Table D's numbers come from (read-only, never regenerated).
const DEDUP_SOURCE: &str = "prd/migration/rust-evidence/m199-s03-resolution-demo.json (tracked; read-only, the S03 generator stays ignored)";

/// The honest art_ctx caption: a missing-frame token, not a quality win.
const ART_CTX_NOTE: &str = "art_ctx is the honest missing-frame token for anaphora with no prior frame in the same src: its group size is NOT a quality win";

/// Presence pins that must exist as S03 dump paths.
const DEDUP_PRESENCE_PINS: [&str; 4] = [
    "art_7.29..art_7.32",
    "art_16.6",
    "art_ctx",
    "art_26.2/par_1",
];

/// Predicted match keys plus head TokenKinds: one `capture_lawrefs` pass
/// over each of the 180 tracked fragments.
fn predicted_keys_and_heads(sample: &LiveSample) -> Vec<(MatchKey, String)> {
    let mut predicted = Vec::new();
    for (fragment_id, file) in &sample.fragments {
        let src = fs::read_to_string(fixture_dir().join(file))
            .unwrap_or_else(|err| panic!("read fragment {fragment_id} ({file}): {err}"));
        for capture in capture_lawrefs(&src) {
            let head_kind = capture
                .token_kind_seq
                .split(',')
                .next()
                .unwrap_or_default()
                .to_owned();
            predicted.push((
                MatchKey {
                    fragment_id: fragment_id.clone(),
                    start: capture.span.start(),
                    end: capture.span.end(),
                    pattern_id: capture.pattern_id.clone(),
                },
                head_kind,
            ));
        }
    }
    predicted
}

/// Views the raw counts as the report's overall P/R/F1 row.
fn prf_overall(counts: PrfCounts) -> PrfOverall {
    let (precision_ppm, recall_ppm, f1_ppm) = prf_ppm(counts);
    PrfOverall {
        tp: counts.tp,
        fp: counts.fp,
        missed: counts.missed,
        precision_ppm,
        recall_ppm,
        f1_ppm,
    }
}

/// Tables A+B: capture over the 180 fragments vs the 159 seed records.
/// Overall and per-pattern parity must be exact (the cheap 159/159 pin);
/// the head-kind table re-pairs every capture with its seed row.
fn compute_span_prf(sample: &LiveSample) -> SpanPrfView {
    let predicted = predicted_keys_and_heads(sample);
    let predicted_keys: Vec<MatchKey> = predicted.iter().map(|(key, _)| key.clone()).collect();
    let actual_keys: Vec<MatchKey> = sample
        .seed
        .iter()
        .map(|row| MatchKey {
            fragment_id: row.fragment_id.clone(),
            start: row.start,
            end: row.end,
            pattern_id: row.pattern_id.clone(),
        })
        .collect();

    let overall_counts = prf_counts(&predicted_keys, &actual_keys);
    assert_eq!(
        (overall_counts.tp, overall_counts.fp, overall_counts.missed),
        (159, 0, 0),
        "capture over the 180-fragment sample must equal the rule seed exactly"
    );

    let mut per_pattern = Vec::new();
    for (pattern_id, want_n) in SEED_HIST {
        let seed_n = sample
            .seed
            .iter()
            .filter(|row| row.pattern_id == pattern_id)
            .count();
        assert_eq!(seed_n, want_n, "seed histogram drift for {pattern_id}");
        let pred: Vec<MatchKey> = predicted_keys
            .iter()
            .filter(|key| key.pattern_id == pattern_id)
            .cloned()
            .collect();
        let act: Vec<MatchKey> = actual_keys
            .iter()
            .filter(|key| key.pattern_id == pattern_id)
            .cloned()
            .collect();
        let counts = prf_counts(&pred, &act);
        assert_eq!(
            (counts.tp, counts.fp, counts.missed),
            (want_n, 0, 0),
            "per-pattern span parity drifted for {pattern_id}"
        );
        per_pattern.push(SpanPatternRow {
            pattern_id: pattern_id.to_owned(),
            tp: counts.tp,
            fp: 0,
            missed: 0,
        });
    }
    assert_eq!(
        per_pattern.iter().map(|row| row.tp).sum::<usize>(),
        159,
        "the seven pattern rows must sum to 159"
    );

    let mut head_rows = Vec::new();
    let mut head_totals = PrfCounts::default();
    for kind in HEAD_KIND_ORDER {
        let seed_n = sample.seed.iter().filter(|row| row.kind == kind).count();
        let mut counts = PrfCounts::default();
        for (key, _head_kind) in predicted.iter().filter(|(_, head)| head.as_str() == kind) {
            let seed_row = sample.seed.iter().find(|row| {
                row.fragment_id == key.fragment_id
                    && row.start == key.start
                    && row.end == key.end
                    && row.pattern_id == key.pattern_id
            });
            match seed_row {
                Some(row) if row.kind == kind => counts.tp += 1,
                _ => counts.fp += 1,
            }
        }
        for row in sample.seed.iter().filter(|row| row.kind == kind) {
            let matched = predicted.iter().any(|(key, head)| {
                head.as_str() == kind
                    && key.fragment_id == row.fragment_id
                    && key.start == row.start
                    && key.end == row.end
                    && key.pattern_id == row.pattern_id
            });
            if !matched {
                counts.missed += 1;
            }
        }
        assert_eq!(
            (counts.tp, counts.fp, counts.missed),
            (seed_n, 0, 0),
            "head-kind parity drifted for {kind}"
        );
        head_totals.tp += counts.tp;
        head_totals.fp += counts.fp;
        head_totals.missed += counts.missed;
        head_rows.push(HeadKindRow {
            kind: kind.to_owned(),
            n: seed_n,
            tp: counts.tp,
            fp: counts.fp,
            missed: counts.missed,
        });
    }
    assert_eq!(
        (head_totals.tp, head_totals.fp, head_totals.missed),
        (159, 0, 0),
        "head-kind parity must be total (the seed kind is a construction property)"
    );

    SpanPrfView {
        caption: SPAN_CAPTION.to_owned(),
        match_key: SPAN_MATCH_KEY.to_owned(),
        provenance: "rule-seed".to_owned(),
        overall: prf_overall(overall_counts),
        per_pattern,
        head_token_kind: HeadKindView {
            caption: HEAD_CAPTION.to_owned(),
            match_key: HEAD_MATCH_KEY.to_owned(),
            rows: head_rows,
            overall: prf_overall(head_totals),
        },
    }
}

/// Test-side copy of the src false-range shape: `src[end]` opens a
/// hyphen-split number (`-2` of the `16.6 - 16.6` lexer split).
fn hyphen_continuation(src: &str, end: usize) -> bool {
    src.as_bytes().get(end) == Some(&b'-')
        && src[end + 1..]
            .chars()
            .next()
            .is_some_and(|ch: char| ch.is_ascii_digit())
}

/// Table C: walks the same 180 fragments through `resolve_lawrefs`, aligns
/// every resolution to the 159 seed captures by `(fragment_id, start, end,
/// pattern_id)`, and counts coverage shapes - never correctness. The R070
/// windows, the false hyphen-split range, and the pair-only members pin are
/// asserted live while counting.
fn compute_coverage(sample: &LiveSample) -> CoverageView {
    let seed_keys: Vec<MatchKey> = sample
        .seed
        .iter()
        .map(|row| MatchKey {
            fragment_id: row.fragment_id.clone(),
            start: row.start,
            end: row.end,
            pattern_id: row.pattern_id.clone(),
        })
        .collect();
    let mut counts_by_pattern: BTreeMap<String, [usize; 4]> = BTreeMap::new();
    let mut false_ranges = 0usize;
    for (fragment_id, file) in &sample.fragments {
        let src = fs::read_to_string(fixture_dir().join(file))
            .unwrap_or_else(|err| panic!("read fragment {fragment_id} ({file}): {err}"));
        let captures = capture_lawrefs(&src);
        let resolved = resolve_lawrefs(&src);
        assert_eq!(
            captures.len(),
            resolved.len(),
            "{fragment_id}: the resolver consumes the frozen captures one-for-one"
        );
        for (capture, resolution) in captures.iter().zip(resolved.iter()) {
            // Alignment contract: the resolver's capture IS this capture.
            assert_eq!(resolution.capture.span.start(), capture.span.start());
            assert_eq!(resolution.capture.span.end(), capture.span.end());
            assert_eq!(resolution.capture.pattern_id, capture.pattern_id);
            let key = MatchKey {
                fragment_id: fragment_id.clone(),
                start: capture.span.start(),
                end: capture.span.end(),
                pattern_id: capture.pattern_id.clone(),
            };
            assert!(
                seed_keys.contains(&key),
                "{fragment_id}: coverage aligns to the 159 seed captures only"
            );
            let counts = counts_by_pattern
                .entry(capture.pattern_id.clone())
                .or_insert([0usize; 4]);
            counts[0] += 1;
            if resolution.anchor.is_some() {
                counts[1] += 1;
            } else {
                counts[3] += 1;
            }
            if resolution.members.len() == 2 {
                counts[2] += 1;
            }
            // Shape pins, live while counting.
            assert!(
                resolution.members.is_empty() || resolution.members.len() == 2,
                "{fragment_id}: members stay empty or the expanded pair, never an enumeration"
            );
            if matches!(
                capture.pattern_id.as_str(),
                "abbrev-amendment-window" | "date-docno-window"
            ) {
                assert!(
                    resolution.anchor.is_none(),
                    "{fragment_id}: R070 windows stay anchor=None"
                );
            }
            if capture.pattern_id == "range_candidate" {
                if let Some((from, to)) = capture.slots.range.as_ref() {
                    if from == to && hyphen_continuation(&src, capture.span.end()) {
                        false_ranges += 1;
                        assert!(
                            resolution.anchor.is_none() && resolution.members.is_empty(),
                            "{fragment_id}: the false hyphen-split range stays unresolved"
                        );
                    }
                }
            }
        }
    }
    assert!(
        false_ranges >= 1,
        "the live sample must carry the false hyphen-split range shape"
    );

    let mut per_pattern = Vec::new();
    for (pattern_id, counts) in &counts_by_pattern {
        per_pattern.push(CoverageRow {
            pattern_id: pattern_id.clone(),
            n: counts[0],
            n_anchor_some: counts[1],
            n_members_pair: counts[2],
            n_anchor_none: counts[3],
        });
    }
    assert_eq!(
        per_pattern.iter().map(|row| row.n).sum::<usize>(),
        159,
        "coverage must align to all 159 seed captures"
    );
    for (pattern_id, want_n) in SEED_HIST {
        let row = per_pattern
            .iter()
            .find(|row| row.pattern_id == pattern_id)
            .unwrap_or_else(|| panic!("missing coverage row for {pattern_id}"));
        assert_eq!(row.n, want_n, "coverage n for {pattern_id}");
        assert_eq!(row.n_anchor_some + row.n_anchor_none, row.n);
        assert!(row.n_members_pair <= row.n_anchor_some);
    }

    // Live degenerate: npa-frag-009 [562,573) is the unresolved false range,
    // classified unresolved-false-range and never a false negative.
    let frag009 =
        fs::read_to_string(fixture_dir().join("npa-frag-009.txt")).expect("read npa-frag-009");
    let captures = capture_lawrefs(&frag009);
    let position = captures
        .iter()
        .position(|capture| {
            capture.pattern_id == "range_candidate"
                && capture.span.start() == 562
                && capture.span.end() == 573
        })
        .expect("npa-frag-009 must carry the [562,573) range_candidate capture");
    let resolved = resolve_lawrefs(&frag009);
    let degenerate = &resolved[position];
    assert!(
        degenerate.anchor.is_none()
            && degenerate.members.is_empty()
            && degenerate.dedup_key.is_none(),
        "npa-frag-009 [562,573) stays the unresolved false range"
    );

    CoverageView {
        caption: COVERAGE_CAPTION.to_owned(),
        alignment_key: "(start, end, pattern_id) over the 159 seed captures".to_owned(),
        per_pattern,
        expected_shape_pins: EXPECTED_SHAPE_PINS
            .iter()
            .map(|pin| pin.to_string())
            .collect(),
        live_degenerate: LiveDegenerate {
            fragment_id: "npa-frag-009".to_owned(),
            start: 562,
            end: 573,
            pattern_id: "range_candidate".to_owned(),
            classification: "unresolved-false-range".to_owned(),
            counted_as_false_negative: false,
        },
    }
}

/// Closed top-level key set of the tracked S03 resolution demo dump.
const RESOLUTION_DUMP_KEYS: [&str; 6] = [
    "schema",
    "schema_version",
    "lifecycle",
    "non_claims",
    "roadmap_rows",
    "dedup_groups",
];

/// Closed key set of one dedup_groups entry.
const DEDUP_GROUP_KEYS: [&str; 2] = ["path", "member_spans"];

/// One counted S03 dedup group: the canonical path plus its member count.
#[derive(Debug, Clone, PartialEq, Eq)]
struct DumpGroup {
    path: String,
    n_members: usize,
}

/// Parsed view of the S03 dump: the dedup groups only (Table D counts; it
/// never re-canons). Extra keys fail closed naming the key (Q7).
#[derive(Debug, Clone, PartialEq, Eq)]
struct ResolutionDump {
    groups: Vec<DumpGroup>,
}

/// Fail-closed hand-rolled parse of the S03 dump (D328: no serde).
fn parse_resolution_dump(text: &str) -> Result<ResolutionDump, String> {
    const LABEL: &str = "resolution dump";
    let top = json_object_members(object_body(text)?)?;
    for (index, (key, _)) in top.iter().enumerate() {
        if top[..index].iter().any(|(seen, _)| seen == key) {
            return Err(format!("{LABEL}: duplicate key '{key}'"));
        }
    }
    for (key, _) in &top {
        if !RESOLUTION_DUMP_KEYS.contains(&key.as_str()) {
            return Err(format!(
                "{LABEL}: extra key '{key}' is outside the closed npa-lawref-resolution-demo/v1 envelope"
            ));
        }
    }
    for key in RESOLUTION_DUMP_KEYS {
        if !top.iter().any(|(name, _)| name == key) {
            return Err(format!("{LABEL}: closed envelope is missing key '{key}'"));
        }
    }
    let schema = acceptance_string_field(&top, "schema")?;
    if schema != "npa-lawref-resolution-demo/v1" {
        return Err(format!(
            "{LABEL}: schema must be 'npa-lawref-resolution-demo/v1', got '{schema}'"
        ));
    }
    let schema_version = acceptance_number_field(&top, "schema_version")?;
    if schema_version != 1 {
        return Err(format!(
            "{LABEL}: schema_version must be 1, got {schema_version}"
        ));
    }
    let mut groups: Vec<DumpGroup> = Vec::new();
    for item in json_array_items(raw_field(&top, "dedup_groups")?)? {
        let members = json_object_members(object_body(item)?)?;
        for (key, _) in &members {
            if !DEDUP_GROUP_KEYS.contains(&key.as_str()) {
                return Err(format!(
                    "{LABEL} dedup group: extra key '{key}' is outside the closed entry envelope"
                ));
            }
        }
        for key in DEDUP_GROUP_KEYS {
            if !members.iter().any(|(name, _)| name == key) {
                return Err(format!(
                    "{LABEL} dedup group: closed entry is missing key '{key}'"
                ));
            }
        }
        let path = acceptance_string_field(&members, "path")?;
        let spans = json_array_items(raw_field(&members, "member_spans")?)?;
        if spans.is_empty() {
            return Err(format!("{LABEL}: group '{path}' carries no member_spans"));
        }
        if groups.iter().any(|group| group.path == path) {
            return Err(format!("{LABEL}: duplicate dedup group '{path}'"));
        }
        groups.push(DumpGroup {
            path,
            n_members: spans.len(),
        });
    }
    Ok(ResolutionDump { groups })
}

/// Table D: counts the tracked S03 dump's dedup groups. Read-only: the dump
/// is never regenerated and the counts never claim grouping precision.
fn compute_dedup_quality() -> DedupView {
    let text = fs::read_to_string(resolution_dump_path())
        .expect("read the tracked S03 resolution demo dump");
    let dump = parse_resolution_dump(&text).expect("the tracked S03 dump must parse fail-closed");
    let n_groups = dump.groups.len();
    let n_groups_ge2 = dump
        .groups
        .iter()
        .filter(|group| group.n_members >= 2)
        .count();
    let n_singletons = dump
        .groups
        .iter()
        .filter(|group| group.n_members == 1)
        .count();
    assert_eq!(
        n_groups,
        n_groups_ge2 + n_singletons,
        "groups split exactly into ge2 + singletons"
    );
    let art_ctx_group_size = dump
        .groups
        .iter()
        .find(|group| group.path == "art_ctx")
        .expect("the art_ctx group must exist in the S03 dump")
        .n_members;
    for pin in DEDUP_PRESENCE_PINS {
        assert!(
            dump.groups.iter().any(|group| group.path == pin),
            "presence pin '{pin}' must exist as an S03 dump path"
        );
    }
    DedupView {
        caption: DEDUP_CAPTION.to_owned(),
        source: DEDUP_SOURCE.to_owned(),
        n_groups,
        n_groups_ge2,
        n_singletons,
        art_ctx_group_size,
        art_ctx_note: ART_CTX_NOTE.to_owned(),
        presence_pins: DEDUP_PRESENCE_PINS
            .iter()
            .map(|pin| pin.to_string())
            .collect(),
    }
}

// ---------------------------------------------------------------------------
// (j) T02 one-shot generator: refills the three computed tables of the
//     tracked report from the live computation. Ignored so ordinary test
//     runs never mutate the tracked artifact; the green suite pins the
//     written bytes against a fresh recompute.
// ---------------------------------------------------------------------------

fn render_prf_overall(overall: &PrfOverall) -> String {
    format!("{{\"tp\": {}, \"fp\": {}, \"fn\": {}, \"precision_ppm\": {}, \"recall_ppm\": {}, \"f1_ppm\": {}}}", overall.tp, overall.fp, overall.missed, overall.precision_ppm, overall.recall_ppm, overall.f1_ppm)
}

fn render_span_prf(view: &SpanPrfView) -> String {
    let rows = view
        .per_pattern
        .iter()
        .map(|row| {
            format!(
                "{{\"pattern_id\": \"{}\", \"tp\": {}, \"fp\": {}, \"fn\": {}}}",
                row.pattern_id, row.tp, row.fp, row.missed
            )
        })
        .collect::<Vec<_>>()
        .join(", ");
    let head_rows = view
        .head_token_kind
        .rows
        .iter()
        .map(|row| {
            format!(
                "{{\"kind\": \"{}\", \"n\": {}, \"tp\": {}, \"fp\": {}, \"fn\": {}}}",
                row.kind, row.n, row.tp, row.fp, row.missed
            )
        })
        .collect::<Vec<_>>()
        .join(", ");
    format!("{{\"caption\": \"{}\", \"match_key\": \"{}\", \"provenance\": \"{}\", \"overall\": {}, \"per_pattern\": [{}], \"head_token_kind_vs_seed\": {{\"caption\": \"{}\", \"match_key\": \"{}\", \"rows\": [{}], \"overall\": {}}}}}", view.caption, view.match_key, view.provenance, render_prf_overall(&view.overall), rows, view.head_token_kind.caption, view.head_token_kind.match_key, head_rows, render_prf_overall(&view.head_token_kind.overall))
}

fn render_coverage(view: &CoverageView) -> String {
    let rows = view
        .per_pattern
        .iter()
        .map(|row| {
            format!("{{\"pattern_id\": \"{}\", \"n\": {}, \"n_anchor_some\": {}, \"n_members_pair\": {}, \"n_anchor_none\": {}}}", row.pattern_id, row.n, row.n_anchor_some, row.n_members_pair, row.n_anchor_none)
        })
        .collect::<Vec<_>>()
        .join(", ");
    let pins = view
        .expected_shape_pins
        .iter()
        .map(|pin| format!("\"{pin}\""))
        .collect::<Vec<_>>()
        .join(", ");
    let degenerate = format!("{{\"fragment_id\": \"{}\", \"start\": {}, \"end\": {}, \"pattern_id\": \"{}\", \"classification\": \"{}\", \"counted_as_false_negative\": {}}}", view.live_degenerate.fragment_id, view.live_degenerate.start, view.live_degenerate.end, view.live_degenerate.pattern_id, view.live_degenerate.classification, view.live_degenerate.counted_as_false_negative);
    format!("{{\"caption\": \"{}\", \"alignment_key\": \"{}\", \"per_pattern\": [{}], \"expected_shape_pins\": [{}], \"live_degenerate\": {}}}", view.caption, view.alignment_key, rows, pins, degenerate)
}

fn render_dedup(view: &DedupView) -> String {
    let pins = view
        .presence_pins
        .iter()
        .map(|pin| format!("\"{pin}\""))
        .collect::<Vec<_>>()
        .join(", ");
    format!("{{\"caption\": \"{}\", \"source\": \"{}\", \"n_groups\": {}, \"n_groups_ge2\": {}, \"n_singletons\": {}, \"art_ctx_group_size\": {}, \"art_ctx_note\": \"{}\", \"presence_pins\": [{}]}}", view.caption, view.source, view.n_groups, view.n_groups_ge2, view.n_singletons, view.art_ctx_group_size, view.art_ctx_note, pins)
}

/// The T01 non-claims, verbatim: the laundering guard is never rewritten by
/// the table generator.
const T01_NON_CLAIMS: [&str; 11] = [
    "No official-publication claim: decoded fragments are working copies, not the official publication.",
    "R070 amendment and date windows stay open and out of scope for every number in this report.",
    "The 159-record rule-seed is distant supervision: sample ≠ gold, never human annotation.",
    "No inter-coder agreement is claimed because no second annotator exists; alpha_sample stays JSON null.",
    "Layer-2 is HOLD: the formula ships toy-pinned, with no accuracy claim beyond the sample.",
    "The report claims no resolution accuracy: gold canonical anchors do not exist; coverage is not correctness.",
    "The report flips no ADR-0028 and ships no FSM behavior; the src surface is frozen.",
    "This report is bounded lifecycle evidence, not legal interpretation.",
    "Layer-1 PASS is cited from D363 (M198), not remeasured here.",
    "159/159 is not human F1: record-for-record parity over the seed is a construction property, not recall against human cores.",
    "M197 TokenKind sidecar P/R/F1 is a lexer regression pin, not this Layer-2 gate.",
];

/// Renders the whole acceptance report: the T01 envelope verbatim (alpha
/// null, HOLD/INCONCLUSIVE/NOT_PASS, ds-noise, non-claims, 159/180) plus the
/// three computed table objects.
fn render_acceptance_report(
    span: &SpanPrfView,
    coverage: &CoverageView,
    dedup: &DedupView,
) -> String {
    let mut out = String::from("{\n");
    for line in [
        "  \"schema\": \"npa-lawref-n2-acceptance/v1\",",
        "  \"schema_version\": 1,",
        "  \"lifecycle\": \"[bounded]\",",
        "  \"layer1_status\": \"PASS\",",
        "  \"layer2_status\": \"HOLD\",",
        "  \"layer3_status\": \"INCONCLUSIVE\",",
        "  \"combined_status\": \"NOT_PASS\",",
        "  \"alpha_sample\": null,",
        "  \"alpha_status\": \"not-computed-no-second-annotator\",",
        "  \"alpha_gate\": \"HOLD\",",
        "  \"alpha_formula\": \"krippendorff-nominal-two-rater-coincidence/v1\",",
    ] {
        out.push_str(line);
        out.push('\n');
    }
    out.push_str(&format!(
        "  \"span_prf_vs_seed\": {},\n",
        render_span_prf(span)
    ));
    out.push_str(&format!(
        "  \"resolution_coverage\": {},\n",
        render_coverage(coverage)
    ));
    out.push_str(&format!("  \"dedup_quality\": {},\n", render_dedup(dedup)));
    out.push_str("  \"resolution_accuracy\": null,\n");
    out.push_str("  \"ds_noise\": {\n");
    for line in [
        "    \"n_fragments\": 20,",
        "    \"verdict\": \"do-not-treat-as-gold\",",
        "    \"incomplete_ppm\": 466667,",
        "    \"incomplete_fraction\": \"21/45\",",
        "    \"inaccurate_ppm\": 83333,",
        "    \"inaccurate_fraction\": \"2/24\"",
    ] {
        out.push_str(line);
        out.push('\n');
    }
    out.push_str("  },\n");
    out.push_str("  \"non_claims\": [\n");
    for (index, claim) in T01_NON_CLAIMS.iter().enumerate() {
        let comma = if index + 1 == T01_NON_CLAIMS.len() {
            ""
        } else {
            ","
        };
        out.push_str(&format!("    \"{claim}\"{comma}\n"));
    }
    out.push_str("  ],\n");
    out.push_str("  \"seed_n\": 159,\n  \"fragment_n\": 180\n}\n");
    out
}

/// The one-shot T02 generator: refills the tracked report's three computed
/// tables from the live computation. Run explicitly with `--ignored`, then
/// review the diff; the non-ignored suite re-pins the written bytes.
#[test]
#[ignore = "one-shot T02 generator: run with cargo test -p ln-decode --offline --test npa_lawref_acceptance_contract write_acceptance -- --ignored --nocapture, then review the diff"]
fn write_acceptance_tables_generator() {
    let sample = load_sample();
    let span = compute_span_prf(&sample);
    let coverage = compute_coverage(&sample);
    let dedup = compute_dedup_quality();
    let json = render_acceptance_report(&span, &coverage, &dedup);
    fs::write(acceptance_report_path(), &json).expect("write the tracked N2 acceptance report");
    let reread = fs::read_to_string(acceptance_report_path())
        .expect("reread the tracked N2 acceptance report");
    analyze_acceptance(&reread)
        .expect("the regenerated report must parse against the closed envelope");
    println!(
        "rewrote the tracked acceptance report: {}",
        acceptance_report_path().display()
    );
}

// ---------------------------------------------------------------------------
// (k) T02 green recompute pin + negative tests.
// ---------------------------------------------------------------------------

/// The MEM236 `--check` analog: the tracked tables must equal a fresh live
/// computation, so fixture, seed, dump, or resolver drift turns the suite
/// red instead of silently reporting stale numbers.
#[test]
fn acceptance_tables_match_the_live_recompute() {
    let text = fs::read_to_string(acceptance_report_path())
        .expect("the tracked N2 acceptance report must be readable");
    let view =
        analyze_acceptance(&text).expect("the report must parse against the closed envelope");
    let sample = load_sample();
    assert_eq!(
        view.span_prf,
        compute_span_prf(&sample),
        "Tables A/B must equal the live recompute (stale tables fail here)"
    );
    assert_eq!(
        view.resolution_coverage,
        compute_coverage(&sample),
        "Table C must equal the live recompute (stale tables fail here)"
    );
    assert_eq!(
        view.dedup_quality,
        compute_dedup_quality(),
        "Table D must equal the live recompute (stale tables fail here)"
    );
}

/// The 16.6 negative: npa-frag-009 [562,573) is the unresolved false range -
/// anchor None, empty members, no dedup key - and it IS a seed record, so it
/// is a Table A true positive and a Table C coverage-None at once, never a
/// Layer-3 false negative.
#[test]
fn npa_frag_009_false_range_is_unresolved_and_never_a_false_negative() {
    let src =
        fs::read_to_string(fixture_dir().join("npa-frag-009.txt")).expect("read npa-frag-009");
    assert!(
        hyphen_continuation(&src, 573),
        "npa-frag-009 [562,573) must continue a hyphen split to be the false range"
    );
    let captures = capture_lawrefs(&src);
    let position = captures
        .iter()
        .position(|capture| {
            capture.pattern_id == "range_candidate"
                && capture.span.start() == 562
                && capture.span.end() == 573
        })
        .expect("the false-range capture must exist");
    let resolved = resolve_lawrefs(&src);
    let row = &resolved[position];
    assert!(row.anchor.is_none(), "the false range stays unresolved");
    assert!(row.members.is_empty(), "no pair members for a false range");
    assert!(row.dedup_key.is_none(), "no dedup key for a false range");
    let sample = load_sample();
    assert!(
        sample.seed.iter().any(|row| {
            row.fragment_id == "npa-frag-009"
                && row.start == 562
                && row.end == 573
                && row.pattern_id == "range_candidate"
        }),
        "the degenerate is a seed record: a Table A TP, never an FN"
    );
}

/// Table C completeness: the seven rows cover all 159 seed captures, every
/// row's some+none partition its n, and the R070 windows stay anchor=None
/// row-wide. Amendment windows carry their date/doc_no slots on the seed
/// side (the shape feed for the coverage pin).
#[test]
fn resolution_coverage_counts_align_with_the_seed_hist() {
    let sample = load_sample();
    for row in sample
        .seed
        .iter()
        .filter(|row| row.pattern_id == "abbrev-amendment-window")
    {
        assert!(
            row.slots.date.is_some() && row.slots.doc_no.is_some(),
            "seed amendment windows must surface date and doc_no slots"
        );
    }
    let coverage = compute_coverage(&sample);
    assert_eq!(
        coverage.per_pattern.iter().map(|row| row.n).sum::<usize>(),
        159
    );
    for row in &coverage.per_pattern {
        assert_eq!(row.n_anchor_some + row.n_anchor_none, row.n);
        assert!(row.n_members_pair <= row.n_anchor_some);
    }
    for pattern in ["abbrev-amendment-window", "date-docno-window"] {
        let row = coverage
            .per_pattern
            .iter()
            .find(|row| row.pattern_id == pattern)
            .expect("the R070 coverage row");
        assert_eq!(
            (row.n_anchor_some, row.n_anchor_none),
            (0, row.n),
            "{pattern} stays anchor=None (R070 out of scope)"
        );
    }
    assert_eq!(
        coverage.live_degenerate.classification, "unresolved-false-range",
        "the degenerate is classified, never counted as a Layer-3 miss"
    );
    assert!(!coverage.live_degenerate.counted_as_false_negative);
}

/// The enumeration ban, live: no resolution ever mints more than the
/// expanded endpoint pair.
#[test]
fn resolved_members_never_exceed_the_expanded_pair() {
    let sample = load_sample();
    for (fragment_id, file) in &sample.fragments {
        let src = fs::read_to_string(fixture_dir().join(file))
            .unwrap_or_else(|err| panic!("read fragment {fragment_id} ({file}): {err}"));
        for resolution in resolve_lawrefs(&src) {
            assert!(
                resolution.members.len() <= 2,
                "{fragment_id}: members never enumerate past the expanded pair"
            );
        }
    }
}

/// Q7: an extra key inside any of the three computed table objects fails
/// closed naming the table and the key.
#[test]
fn hostile_extra_key_in_each_table_object_fails_closed() {
    let text = fs::read_to_string(acceptance_report_path())
        .expect("the tracked N2 acceptance report must be readable");
    for (label, anchor) in [
        ("span_prf_vs_seed", "\"span_prf_vs_seed\": {"),
        ("resolution_coverage", "\"resolution_coverage\": {"),
        ("dedup_quality", "\"dedup_quality\": {"),
    ] {
        let mutated = text.replacen(anchor, &format!("{anchor}\n    \"future_hint\": 1,"), 1);
        assert_ne!(
            mutated, text,
            "the hostile mutation must change the report ({label})"
        );
        let error = analyze_acceptance(&mutated).expect_err("an extra table key must fail closed");
        assert!(
            error.contains("future_hint") && error.contains(label),
            "expected the {label} extra-key rejection to name the key, got: {error}"
        );
    }
}

/// Q7: this suite parses the S03 dump for Table D, so an extra dump key must
/// fail closed there too.
#[test]
fn hostile_extra_key_in_the_s03_dump_fails_closed() {
    let text =
        fs::read_to_string(resolution_dump_path()).expect("the tracked S03 dump must be readable");
    let mutated = text.replacen('{', "{\n  \"future_hint\": 1,", 1);
    assert_ne!(mutated, text, "the hostile mutation must change the dump");
    let error = parse_resolution_dump(&mutated).expect_err("an extra dump key must fail closed");
    assert!(
        error.contains("future_hint") && error.contains("extra key"),
        "expected the dump extra-key rejection to name the key, got: {error}"
    );
}
