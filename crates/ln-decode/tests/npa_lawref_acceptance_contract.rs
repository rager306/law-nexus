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
//! 3. the tracked HOLD skeleton (`alpha_sample: null`, `combined_status:
//!    NOT_PASS`) so T02/T03 fill tables against a fixed path pin. D378 is
//!    the operationalization of D351; the formula is never run against the
//!    159-record seed (D366 laundering guard).
//!
//! Evaluation helpers are private to this suite - never a src module. The
//! JSON reader is hand-rolled in the S03 `analyze_dump` style (D328), with
//! no `#[path]` include of test support (D335). The corpus is never opened,
//! the 180 fixtures are never walked, and `capture_lawrefs` /
//! `resolve_lawrefs` are never called over the sample. Q3 threat surface:
//! errors name keys and rules, never fragment text; the skeleton carries no
//! fragment payload.

use std::fs;
use std::path::{Path, PathBuf};

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
    span_prf_vs_seed_caption: String,
    resolution_coverage_caption: String,
    dedup_quality_caption: String,
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
    let span_prf_vs_seed_caption = placeholder_caption(&top, "span_prf_vs_seed")?;
    let resolution_coverage_caption = placeholder_caption(&top, "resolution_coverage")?;
    let dedup_quality_caption = placeholder_caption(&top, "dedup_quality")?;
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
        span_prf_vs_seed_caption,
        resolution_coverage_caption,
        dedup_quality_caption,
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

/// T01 skeleton placeholder: exactly one nonempty `caption` member. T02
/// replaces these objects with the real tables and extends this reader.
fn placeholder_caption(top: &[(String, String)], key: &str) -> Result<String, String> {
    let raw = raw_field(top, key)?;
    let members = json_object_members(object_body(raw)?)?;
    if members.len() != 1 || members[0].0 != "caption" {
        return Err(format!(
            "{key}: the T01 skeleton placeholder must carry exactly one 'caption' member"
        ));
    }
    let caption = acceptance_string_field(&members, "caption")?;
    if caption.is_empty() {
        return Err(format!("{key}: the caption must not be empty"));
    }
    Ok(caption)
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

/// The tracked T01 skeleton parses against the closed envelope and holds the
/// laundering guard: alpha null, HOLD layer-2, INCONCLUSIVE layer-3,
/// NOT_PASS combined, and the ds-noise rates as integer ppm with the exact
/// fractions each ppm was rounded from.
#[test]
fn acceptance_schema_accepts_null_alpha_sample_with_hold_status() {
    let text = fs::read_to_string(acceptance_report_path())
        .expect("the tracked N2 acceptance skeleton must be readable");
    let view =
        analyze_acceptance(&text).expect("the skeleton must parse against the closed envelope");
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
    for caption in [
        &view.span_prf_vs_seed_caption,
        &view.resolution_coverage_caption,
        &view.dedup_quality_caption,
    ] {
        assert!(
            caption.contains("T01 skeleton; tables filled by T02"),
            "the placeholder must name itself as the T01 skeleton, got: {caption}"
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
