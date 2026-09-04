//! Contract tests for the LawRef capture layer (M199 S02 T01/T02).
//!
//! T01 shipped the capture SURFACE: the `LawRef` product type over the
//! frozen covering lexer and the `npa_lawref_precedence` YAML table
//! (KBO-R025/R030). T02 lifts the seven S01 seed matchers into
//! `capture_lawrefs`: the first-proof expectations run un-ignored and the
//! S01 sample comparison is disk-backed (manifest-indexed fragments +
//! rule-seed JSONL, parsed by a tiny hand-rolled reader, D328).
//!
//! Inline fixtures stay inline; the corpus (`consru_export`) is never
//! opened. No `#[path]` include of `npa_lawref_support` (D335): this suite
//! reads the tracked src and YAML files directly.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::lawref::{capture_lawrefs, LawRef, LawRefPrecedence, LawRefSlots};
use ln_decode::lexer::{lex, TokenKind};
use ln_decode::prefix_catalog::EMBEDDED_ONTOLOGY_YAML;

// ---------------------------------------------------------------------------
// (a) Green: the embedded precedence table parses with the closed canon.
// ---------------------------------------------------------------------------

const SEVEN_PATTERN_IDS: [&str; 7] = [
    "abbrev-hier-chain",
    "abbrev-amendment-window",
    "date-docno-window",
    "fullword-ref",
    "quoted-enum",
    "range_candidate",
    "anaphora_candidate",
];

fn embedded_precedence() -> LawRefPrecedence {
    LawRefPrecedence::embedded()
        .expect("embedded kb-ontology.yaml must carry a valid npa_lawref_precedence table")
}

#[test]
fn embedded_yaml_parses_with_seven_pattern_ids_and_nonempty_allowlists() {
    let precedence = embedded_precedence();

    let mut got: Vec<&str> = precedence.pattern_ids.iter().map(String::as_str).collect();
    got.sort_unstable();
    let mut want = SEVEN_PATTERN_IDS.to_vec();
    want.sort_unstable();
    assert_eq!(
        got, want,
        "the closed seven-pattern canon is exactly the YAML table"
    );

    // Layer A documents the frozen lexer start orders (capture never rescans).
    assert_eq!(
        precedence.digit_start_order,
        ["Date", "HierNum", "DocNo", "EnumMarker"]
    );
    assert_eq!(
        precedence.letter_start_order,
        ["Abbrev", "EnumMarker", "LawCode", "Word"]
    );
    // Layer B pins the overlap policy and candidate order.
    assert_eq!(precedence.overlap_date_docno_inside_amendment, "drop");
    assert_eq!(precedence.overlap_same_pattern_containment, "drop");
    assert_eq!(precedence.sort_key, ["start", "end", "pattern_id"]);

    // The matcher allowlists are the plan canon; the YAML is the single
    // source (src carries no copy - the src pin below guards that).
    assert_eq!(
        precedence.chain_abbrev_ids,
        ["st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd"]
    );
    assert_eq!(precedence.amendment_abbrev_ids, ["red", "izm"]);
    assert_eq!(precedence.quoted_marker_abbrev_ids, ["p", "pp"]);
    assert_eq!(
        precedence.fullword_tails,
        ["статьи", "пункта", "закона", "года"]
    );
    assert_eq!(
        precedence.anaphora_heads,
        ["настоящей", "настоящего", "настоящая", "того"]
    );
}

// ---------------------------------------------------------------------------
// (b) Hostile: the table fails closed with Err (never panic), naming the key.
// ---------------------------------------------------------------------------

fn parse_embedded_mutated(mutate: impl FnOnce(&str) -> String) -> Result<LawRefPrecedence, String> {
    LawRefPrecedence::parse_yaml(&mutate(EMBEDDED_ONTOLOGY_YAML))
}

#[test]
fn hostile_extra_key_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replacen(
            "    pattern_ids: [",
            "    future_hint: invented-keys-fail-closed\n    pattern_ids: [",
            1,
        )
    })
    .expect_err("an invented key must fail closed");
    assert!(
        error.contains("unknown key 'future_hint'"),
        "expected the closed-key rejection to name the key, got: {error}"
    );
}

#[test]
fn hostile_unknown_pattern_id_fails_closed() {
    let error = parse_embedded_mutated(|yaml| yaml.replace("range_candidate", "ghost-pattern"))
        .expect_err("an unknown pattern id must fail closed");
    assert!(
        error.contains("unknown pattern id 'ghost-pattern'"),
        "expected the closed-canon rejection, got: {error}"
    );
}

#[test]
fn hostile_empty_pattern_ids_fail_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace(
            "pattern_ids: [abbrev-hier-chain, abbrev-amendment-window, date-docno-window, fullword-ref, quoted-enum, range_candidate, anaphora_candidate]",
            "pattern_ids: []",
        )
    })
    .expect_err("an empty pattern table must fail closed");
    assert!(
        error.contains("empty pattern table"),
        "expected the empty-table rejection, got: {error}"
    );
}

#[test]
fn hostile_missing_layer_a_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace(
            "    digit_start_order: [Date, HierNum, DocNo, EnumMarker]\n",
            "",
        )
    })
    .expect_err("a missing layer A key must fail closed");
    assert!(
        error.contains("layer A is missing key 'digit_start_order'"),
        "expected the layer-A rejection, got: {error}"
    );
}

#[test]
fn hostile_missing_layer_b_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace("    overlap_same_pattern_containment: drop\n", "")
    })
    .expect_err("a missing layer B key must fail closed");
    assert!(
        error.contains("layer B is missing key 'overlap_same_pattern_containment'"),
        "expected the layer-B rejection, got: {error}"
    );
}

#[test]
fn hostile_layer_a_order_drift_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace(
            "digit_start_order: [Date, HierNum, DocNo, EnumMarker]",
            "digit_start_order: [HierNum, Date, DocNo, EnumMarker]",
        )
    })
    .expect_err("a layer-A order drift must fail closed: layer A documents the frozen lexer");
    assert!(
        error.contains("frozen lexer order"),
        "expected the frozen-order rejection, got: {error}"
    );
}

#[test]
fn hostile_unknown_overlap_policy_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace(
            "overlap_date_docno_inside_amendment: drop",
            "overlap_date_docno_inside_amendment: keep",
        )
    })
    .expect_err("an unknown overlap policy must fail closed");
    assert!(
        error.contains("unknown overlap policy 'keep'"),
        "expected the closed-policy rejection, got: {error}"
    );
}

#[test]
fn hostile_duplicate_key_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replacen(
            "    sort_key: [start, end, pattern_id]",
            "    sort_key: [start, end, pattern_id]\n    sort_key: [start, end, pattern_id]",
            1,
        )
    })
    .expect_err("a duplicate key must fail closed");
    assert!(
        error.contains("duplicate key 'sort_key'"),
        "expected the duplicate-key rejection, got: {error}"
    );
}

#[test]
fn hostile_allowlist_id_outside_lexicon_fails_closed() {
    let error = parse_embedded_mutated(|yaml| {
        yaml.replace(
            "quoted_marker_abbrev_ids: [p, pp]",
            "quoted_marker_abbrev_ids: [p, zz]",
        )
    })
    .expect_err("an allowlist id outside npa_abbrev_lexicon must fail closed");
    assert!(
        error.contains("id 'zz' is outside npa_abbrev_lexicon"),
        "expected the lexicon-membership rejection, got: {error}"
    );
}

#[test]
fn hostile_missing_heading_fails_closed() {
    let error =
        LawRefPrecedence::parse_yaml("vocabulary:\n  npa_abbrev_lexicon:\n    st: \"ст.\"\n")
            .expect_err("a missing npa_lawref_precedence heading must fail closed");
    assert!(
        error.contains("npa_lawref_precedence:") && error.contains("missing"),
        "the error must name the heading, got: {error}"
    );
}

// ---------------------------------------------------------------------------
// (c) The capture type exists in src/lawref.rs and is never a TokenKind.
// ---------------------------------------------------------------------------

#[test]
fn src_lawref_is_capture_type_not_tokenkind() {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let lawref_path = manifest_dir.join("src/lawref.rs");
    let lawref_src = fs::read_to_string(&lawref_path)
        .unwrap_or_else(|err| panic!("read {}: {err}", lawref_path.display()));
    assert!(
        lawref_src.contains("pub struct LawRef"),
        "the capture type must exist in src/lawref.rs"
    );
    for pattern in ["enum LawRef", "type LawRef"] {
        assert!(
            !lawref_src.contains(pattern),
            "LawRef must stay a struct, not '{pattern}'"
        );
    }
    // No resolution-time identifiers on the capture surface (S02 T01 ships
    // capture only; anchors and anaphora resolution belong to later steps).
    for forbidden in ["eId", "canonical_anchor", "resolve_anaphora"] {
        assert!(
            !lawref_src.contains(forbidden),
            "src/lawref.rs must not name '{forbidden}' (capture, not resolution)"
        );
    }
    // No #[path] include of test support in src (D335).
    assert!(
        !lawref_src.contains("#[path"),
        "src must not #[path]-include test support"
    );
    // The module is wired into the public surface.
    let lib_src = fs::read_to_string(manifest_dir.join("src/lib.rs")).expect("read src/lib.rs");
    assert!(
        lib_src.contains("pub mod lawref;"),
        "lawref must be a public ln-decode module"
    );

    // And it is NOT a lexer token kind: the closed nine-kind set stays
    // closed and Editorial stays absent (no tenth kind).
    let lexer_path = manifest_dir.join("src/lexer.rs");
    let lexer_src = fs::read_to_string(&lexer_path)
        .unwrap_or_else(|err| panic!("read {}: {err}", lexer_path.display()));
    assert!(
        !lexer_src.contains("TokenKind::LawRef"),
        "TokenKind::LawRef must not exist in src/lexer.rs"
    );
    let enum_body = token_kind_enum_body(&lexer_src);
    for kind in [
        "Word",
        "Abbrev",
        "HierNum",
        "Date",
        "DocNo",
        "EnumMarker",
        "LawCode",
        "Punct",
        "Space",
    ] {
        assert!(
            enum_body.contains(kind),
            "closed kind {kind} must stay in TokenKind"
        );
    }
    assert!(
        !enum_body.contains("LawRef"),
        "LawRef must not become a TokenKind variant"
    );
    assert!(
        !enum_body.contains("Editorial"),
        "Editorial must stay absent from TokenKind (no tenth kind)"
    );
}

/// Extracts the body of `pub enum TokenKind` from the lexer source so the
/// closed-kind pins read the variant list, not the (mentioning) doc comments.
fn token_kind_enum_body(lexer_src: &str) -> &str {
    let decl = lexer_src
        .find("pub enum TokenKind")
        .expect("src/lexer.rs must declare `pub enum TokenKind`");
    let body_start = decl
        + lexer_src[decl..]
            .find('{')
            .expect("enum TokenKind body open");
    let body_end = body_start
        + lexer_src[body_start..]
            .find('}')
            .expect("enum TokenKind body close");
    &lexer_src[body_start..body_end]
}

// ---------------------------------------------------------------------------
// (d) Hostile capture input stays empty (empty src, `руб.`); nothing logged.
// ---------------------------------------------------------------------------

#[test]
fn capture_stub_returns_empty_for_empty_and_hostile_input() {
    assert!(
        capture_lawrefs("").is_empty(),
        "empty source: stub-ok empty capture"
    );
    assert!(
        capture_lawrefs("руб.").is_empty(),
        "hostile currency initial: stub-ok empty capture"
    );
}

#[test]
fn lawref_user_text_slices_source_and_span_fails_closed() {
    let src = "ч. 2 ст. 15";
    // "ст. 15" starts at byte 6 (ч.=3 bytes, space, `2`, space).
    let law_ref = LawRef::try_new(
        6,
        14,
        "abbrev-hier-chain".to_owned(),
        "Abbrev,Space,HierNum".to_owned(),
        LawRefSlotsForTest::default(),
    )
    .expect("non-empty span must construct");
    assert_eq!(law_ref.user_text(src), "ст. 15");
    assert!(LawRef::try_new(
        6,
        6,
        "abbrev-hier-chain".to_owned(),
        String::new(),
        LawRefSlotsForTest::default()
    )
    .is_err());
}

type LawRefSlotsForTest = ln_decode::lawref::LawRefSlots;

// ---------------------------------------------------------------------------
// First proof (un-ignored in T02): the chained capture + the C2 hostile
// initial contour.
// ---------------------------------------------------------------------------

#[test]
fn first_proof_chain_and_hostile_initial() {
    // First proof: the chained abbrev-hier-chain capture.
    let refs = capture_lawrefs("ч. 2 ст. 15");
    assert_eq!(refs.len(), 1, "chained markers collapse into one candidate");
    assert_eq!(refs[0].pattern_id, "abbrev-hier-chain");
    assert_eq!(refs[0].slots.marker_chain, ["ch", "st"]);
    assert_eq!(refs[0].slots.hier_nums, ["2", "15"]);

    // Hostile contour (C2 fold): the uppercase initial Ч. is not an abbrev
    // (one-letter lexemes stay lowercase-exact), so no LawRef may be headed
    // by it; the lowercase `ст. 33` chain behind it may still fire.
    let refs = capture_lawrefs("Ч. 1.1 ст. 33");
    assert!(
        refs.iter().all(|law_ref| law_ref.span.start() != 0),
        "the hostile initial must not become a reference head: {:?}",
        refs.iter()
            .map(|law_ref| (law_ref.pattern_id.as_str(), law_ref.span.start()))
            .collect::<Vec<_>>()
    );
}

// ---------------------------------------------------------------------------
// (e) S01 sample consumption (T02): capture over the 180 manifest-indexed
//     fragments must equal the 159-record rule seed, record for record.
// ---------------------------------------------------------------------------

/// Repo-root-relative evidence directory holding the tracked S01 artifacts.
fn evidence_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../prd/migration/rust-evidence")
}

/// Tracked fragment fixture directory.
fn fixture_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa-lawref")
}

/// Comparison record: fragment identity + offsets + pattern id + slots
/// (Q3: never the fragment text itself).
#[derive(Debug, PartialEq, Eq, Clone)]
struct CaptureRecord {
    fragment_id: String,
    start: usize,
    end: usize,
    pattern_id: String,
    slots: LawRefSlots,
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

#[test]
fn sample_capture_matches_rule_seed_record_for_record_and_is_deterministic() {
    let manifest = fs::read_to_string(evidence_dir().join("m199-s01-gold-sample-manifest.json"))
        .expect("read the S01 gold sample manifest");
    let fragments = manifest_fragments(&manifest);
    assert_eq!(
        fragments.len(),
        180,
        "the sample manifest must index the 180 tracked fragments"
    );

    // Seed provenance stays `rule-seed`, not gold (D366): this comparison
    // reads the rule-seed JSONL and never treats it as α-input.
    let seed_src = fs::read_to_string(evidence_dir().join("m199-s01-rule-seed.jsonl"))
        .expect("read the S01 rule seed");
    let mut expected: Vec<CaptureRecord> = seed_src
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(parse_seed_record)
        .collect();
    assert_eq!(expected.len(), 159, "the rule seed holds 159 records");

    // The 180 fixture txt files stay on disk; this test reads them by path
    // and compares fragment_id + offsets + pattern_id + slots only.
    let mut produced: Vec<CaptureRecord> = Vec::new();
    for (fragment_id, file) in &fragments {
        let src = fs::read_to_string(fixture_dir().join(file))
            .unwrap_or_else(|err| panic!("read fragment {fragment_id} ({file}): {err}"));
        let first = capture_lawrefs(&src);
        let second = capture_lawrefs(&src);
        let spans = |refs: &[LawRef]| {
            refs.iter()
                .map(|law_ref| {
                    (
                        law_ref.span.start(),
                        law_ref.span.end(),
                        law_ref.pattern_id.clone(),
                    )
                })
                .collect::<Vec<_>>()
        };
        assert_eq!(
            spans(&first),
            spans(&second),
            "capture of {fragment_id} must be deterministic"
        );
        produced.extend(first.into_iter().map(|law_ref| CaptureRecord {
            fragment_id: fragment_id.clone(),
            start: law_ref.span.start(),
            end: law_ref.span.end(),
            pattern_id: law_ref.pattern_id.clone(),
            slots: law_ref.slots.clone(),
        }));
    }

    let sort_key = |record: &CaptureRecord| {
        (
            record.fragment_id.clone(),
            record.start,
            record.end,
            record.pattern_id.clone(),
        )
    };
    produced.sort_by_key(sort_key);
    expected.sort_by_key(sort_key);

    // The S01 harvest already carried outer chains only and no date-docno
    // window nested inside an amendment window, so the YAML layer-B drop
    // policies must converge the fire-all set onto the seed exactly: the
    // lift target is all 159 records, no counted delta.
    assert_eq!(
        produced, expected,
        "capture over the 180-fragment sample must equal the rule seed record for record"
    );

    // Roadmap demo: captured fields visible on real sample rows.
    let chain = produced
        .iter()
        .find(|record| {
            record.pattern_id == "abbrev-hier-chain"
                && !record.slots.marker_chain.is_empty()
                && !record.slots.hier_nums.is_empty()
        })
        .expect("the sample must hold a chain row with marker_chain and hier_nums");
    assert!(
        !chain.slots.marker_chain.is_empty() && !chain.slots.hier_nums.is_empty(),
        "chain rows must surface marker_chain and hier_nums"
    );
    let window = produced
        .iter()
        .find(|record| record.pattern_id == "abbrev-amendment-window")
        .expect("the sample must hold an amendment window row");
    assert!(
        window.slots.date.is_some() && window.slots.doc_no.is_some(),
        "amendment windows must surface date and doc_no slots: {:?}",
        window.slots
    );
}

// ---------------------------------------------------------------------------
// (f) T03 hostile pins at the LawRef contour (C2 fold, D356/MEM1328): the
// fold contours pinned at lexer level must hold one level up, too —
// capitalized one-letter initials, `руб.`, and dates never head a capture
// and never reach a slot. Inline strings only; the corpus stays closed.
// ---------------------------------------------------------------------------

#[test]
fn hostile_capitalized_one_letter_initials_never_head_lawrefs() {
    for src in ["Ч. 1.1 ст. 33", "П. Иванов", "А. 2 п. 3", "Г. Москва"] {
        // kind Word for the head proves no Abbrev id exists: ids ride the
        // Abbrev kind only (one-letter lexemes stay lowercase-exact).
        let tokens = lex(src);
        assert_eq!(tokens[0].kind, TokenKind::Word, "{src}: head lexeme");
        assert_eq!(tokens[1].kind, TokenKind::Punct, "{src}: head dot");
        for law_ref in capture_lawrefs(src) {
            assert!(
                law_ref.span.start() >= 3,
                "{src}: {} covers the hostile initial at {}..{}",
                law_ref.pattern_id,
                law_ref.span.start(),
                law_ref.span.end()
            );
        }
    }

    // The guard bites the head only: lowercase tails behind the initial
    // still capture, never anchored at the initial's bytes (`Х.` is 3 bytes:
    // a 2-byte cyrillic capital plus the dot).
    let refs = capture_lawrefs("Ч. 1.1 ст. 33");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].pattern_id, "abbrev-hier-chain");
    assert_eq!(refs[0].span.start(), 8, "`ст.` starts past the initial");
    assert_eq!(refs[0].slots.marker_chain, ["st"]);
    assert_eq!(refs[0].slots.hier_nums, ["33"]);

    let refs = capture_lawrefs("А. 2 п. 3");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].span.start(), 6, "`п.` starts past the initial");
    assert_eq!(refs[0].slots.marker_chain, ["p"]);
    assert_eq!(refs[0].slots.hier_nums, ["3"]);

    assert!(
        capture_lawrefs("П. Иванов").is_empty(),
        "a capitalized initial with no reference tail captures nothing"
    );
    assert!(capture_lawrefs("Г. Москва").is_empty());
}

#[test]
fn hostile_rub_is_never_an_abbrev_id_nor_a_lawref() {
    // `руб.` sits outside the closed 17-id lexicon (D329): Word + Punct in
    // the frozen lexer, no Abbrev id, and never a LawRef head.
    let tokens = lex("руб.");
    assert_eq!(tokens.len(), 2, "руб. lexes as Word + Punct");
    assert_eq!(tokens[0].kind, TokenKind::Word);
    assert_eq!(tokens[1].kind, TokenKind::Punct);
    assert!(
        capture_lawrefs("руб.").is_empty(),
        "руб. must not head any LawRef candidate"
    );
}

#[test]
fn pp_is_one_abbrev_and_may_start_a_chain_capture() {
    // `пп.` is ONE longest-first Abbrev (D330 rule 1) and a legal chain head
    // (pp sits in the YAML chain_abbrev_ids); the capture slots carry the
    // pp id end-to-end through the embedded lexicon.
    let tokens = lex("пп.");
    assert_eq!(tokens.len(), 1, "`пп.` must stay one token");
    assert_eq!(tokens[0].kind, TokenKind::Abbrev);

    let refs = capture_lawrefs("пп. 1");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].pattern_id, "abbrev-hier-chain");
    assert_eq!(refs[0].slots.marker_chain, ["pp"]);
    assert_eq!(refs[0].slots.hier_nums, ["1"]);

    let refs = capture_lawrefs("пп. 1 ст. 2");
    assert_eq!(refs.len(), 1, "a pp-led chain collapses into one candidate");
    assert_eq!(refs[0].slots.marker_chain, ["pp", "st"]);
    assert_eq!(refs[0].slots.hier_nums, ["1", "2"]);
}

#[test]
fn date_beats_hier_num_in_lex_and_never_lands_in_hier_nums() {
    // Layer A: the frozen lexer mints Date on `dd.mm.yyyy` and capture never
    // rescans digits — a date must never reach a `hier_nums` slot.
    let src = "ст. 01.01.2028";
    let tokens = lex(src);
    assert!(
        tokens.iter().any(|token| token.kind == TokenKind::Date),
        "the frozen lexer must mint Date on dd.mm.yyyy"
    );
    assert!(
        !tokens.iter().any(|token| token.kind == TokenKind::HierNum),
        "dd.mm.yyyy is never a HierNum"
    );
    assert!(
        capture_lawrefs(src).is_empty(),
        "marker + date mints no capture: a Date is no number token and a lone Date is no window"
    );

    // Inside a wider line the date stays out of every capture slot.
    let refs = capture_lawrefs("ч. 2 от 01.01.2028");
    assert_eq!(refs.len(), 1, "only the abbrev-hier chain fires");
    assert_eq!(refs[0].slots.hier_nums, ["2"]);
    for law_ref in &refs {
        assert!(
            !law_ref
                .slots
                .hier_nums
                .iter()
                .any(|num| num.contains("01.01.2028")),
            "a dd.mm.yyyy lexeme must never land in hier_nums"
        );
        assert!(law_ref.slots.date.is_none(), "no capture holds the date");
    }
}

// ---------------------------------------------------------------------------
// (g) T03 freeze pins: ln-decode gains no parsing/CLI deps and the closed
// lexer kind set gains no LawRef variant (capture stays a src/lawref type).
// Fixture/sidecar mtimes are freeze-checked in the task battery (no git),
// never inside a tracked test.
// ---------------------------------------------------------------------------

#[test]
fn freeze_no_parsing_deps_and_no_lawref_tokenkind() {
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let cargo_toml = fs::read_to_string(manifest_dir.join("Cargo.toml"))
        .expect("read crates/ln-decode/Cargo.toml");
    for dependency in ["serde", "clap", "walkdir"] {
        assert!(
            !cargo_toml.contains(dependency),
            "ln-decode must not gain a '{dependency}' dependency (D328: hand-rolled JSON)"
        );
    }
    let lexer_src =
        fs::read_to_string(manifest_dir.join("src/lexer.rs")).expect("read src/lexer.rs");
    assert!(
        !lexer_src.contains("TokenKind::LawRef"),
        "the closed nine-kind lexer set must not gain TokenKind::LawRef"
    );
    let lawref_src =
        fs::read_to_string(manifest_dir.join("src/lawref.rs")).expect("read src/lawref.rs");
    for forbidden in ["eId", "canonical_anchor"] {
        assert!(
            !lawref_src.contains(forbidden),
            "src/lawref.rs must not name '{forbidden}' (capture, not resolution)"
        );
    }
}

// ---------------------------------------------------------------------------
// (h) T03 precedence-table artifact (KBO-R025/R030): the tracked
// `prd/migration/rust-evidence/m199-s02-precedence-table.json` is an
// observable demo of the YAML canon — never a second canon. Reading is
// hand-rolled JSON (D328: no serde in ln-decode).
// ---------------------------------------------------------------------------

/// Repo-root-relative path of the tracked precedence-table dump.
fn precedence_dump_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../prd/migration/rust-evidence/m199-s02-precedence-table.json")
}

/// Closed envelope key set of the dump artifact; every other key must be an
/// `npa_lawref_precedence` YAML table key (extra keys fail closed).
const DUMP_ENVELOPE_KEYS: [&str; 4] = ["schema", "schema_version", "lifecycle", "non_claims"];

/// Mandatory non-claim substrings of the dump (slice plan T03 item 3).
const DUMP_MANDATORY_NON_CLAIMS: [&str; 7] = [
    "R070 open",
    "not official publication",
    "sample ≠ gold",
    "no resolution accuracy",
    "no alpha",
    "no ADR-0028 lifecycle flip",
    "Consultant-only",
];

/// Hand-rolled reader for the dump's top-level `"key": value` pairs (D328):
/// returns the raw value text — quoted scalar, digit run, or bracketed list.
/// Escapes, nested objects, and unsupported value forms fail closed;
/// duplicate keys are rejected by the round-trip check below.
fn dump_entries(dump_text: &str) -> Result<Vec<(String, String)>, String> {
    let body = dump_text.trim();
    let Some(body) = body.strip_prefix('{') else {
        return Err("dump must be a JSON object (missing opening '{')".to_owned());
    };
    let Some(body) = body.strip_suffix('}') else {
        return Err("dump must be a single JSON object (missing closing '}')".to_owned());
    };
    let chars: Vec<char> = body.chars().collect();
    let mut cursor = 0usize;
    let mut entries: Vec<(String, String)> = Vec::new();
    while cursor < chars.len() {
        while cursor < chars.len() && (chars[cursor].is_whitespace() || chars[cursor] == ',') {
            cursor += 1;
        }
        if cursor >= chars.len() {
            break;
        }
        let Some('"') = chars.get(cursor).copied() else {
            return Err("dump entries must open with a quoted key".to_owned());
        };
        cursor += 1;
        let mut key = String::new();
        loop {
            let Some(ch) = chars.get(cursor).copied() else {
                return Err("unterminated dump key".to_owned());
            };
            cursor += 1;
            match ch {
                '"' => break,
                '\\' => return Err("dump keys must not carry escape sequences".to_owned()),
                other => key.push(other),
            }
        }
        while cursor < chars.len() && chars[cursor].is_whitespace() {
            cursor += 1;
        }
        if chars.get(cursor) != Some(&':') {
            return Err(format!("dump key '{key}' must be followed by ':'"));
        }
        cursor += 1;
        while cursor < chars.len() && chars[cursor].is_whitespace() {
            cursor += 1;
        }
        match chars.get(cursor).copied() {
            Some('"') => {
                cursor += 1;
                let mut value = String::from("\"");
                loop {
                    let Some(ch) = chars.get(cursor).copied() else {
                        return Err(format!("unterminated string value for '{key}'"));
                    };
                    cursor += 1;
                    match ch {
                        '"' => break,
                        '\\' => {
                            return Err(format!(
                                "string value for '{key}' must not carry escape sequences"
                            ))
                        }
                        other => value.push(other),
                    }
                }
                value.push('"');
                entries.push((key, value));
            }
            Some('[') => {
                let mut value = String::new();
                let mut depth = 0usize;
                let mut in_string = false;
                loop {
                    let Some(ch) = chars.get(cursor).copied() else {
                        return Err(format!("unterminated list value for '{key}'"));
                    };
                    cursor += 1;
                    value.push(ch);
                    match ch {
                        '"' => in_string = !in_string,
                        '[' if !in_string => depth += 1,
                        ']' if !in_string => {
                            depth -= 1;
                            if depth == 0 {
                                break;
                            }
                        }
                        _ => {}
                    }
                }
                entries.push((key, value));
            }
            Some(ch) if ch.is_ascii_digit() => {
                let mut value = String::new();
                while cursor < chars.len() && chars[cursor].is_ascii_digit() {
                    value.push(chars[cursor]);
                    cursor += 1;
                }
                entries.push((key, value));
            }
            _ => {
                return Err(format!(
                    "dump key '{key}' carries an unsupported value form (string, number, list)"
                ))
            }
        }
    }
    Ok(entries)
}

fn parse_dump_string(value: &str) -> Result<String, String> {
    let inner = value
        .strip_prefix('"')
        .and_then(|rest| rest.strip_suffix('"'))
        .ok_or_else(|| format!("expected a JSON string, got: {value}"))?
        .to_owned();
    if inner.contains('\\') {
        return Err("dump strings must not carry escape sequences".to_owned());
    }
    Ok(inner)
}

fn parse_dump_number(value: &str) -> Result<u64, String> {
    let trimmed = value.trim();
    if trimmed.is_empty() || !trimmed.bytes().all(|byte| byte.is_ascii_digit()) {
        return Err(format!("expected a JSON number, got: {value}"));
    }
    trimmed
        .parse()
        .map_err(|err| format!("number parse failed for '{value}': {err}"))
}

fn parse_dump_string_list(value: &str) -> Result<Vec<String>, String> {
    let inner = value
        .strip_prefix('[')
        .and_then(|rest| rest.strip_suffix(']'))
        .ok_or_else(|| format!("expected a JSON string list, got: {value}"))?;
    let mut items = Vec::new();
    let mut current = String::new();
    let mut in_string = false;
    for ch in inner.chars() {
        match ch {
            '"' => {
                in_string = !in_string;
                current.push(ch);
            }
            ',' if !in_string => {
                items.push(current.trim().to_owned());
                current.clear();
            }
            _ => current.push(ch),
        }
    }
    if in_string {
        return Err("unterminated string inside a dump list".to_owned());
    }
    if !current.trim().is_empty() {
        items.push(current.trim().to_owned());
    }
    items.iter().map(|item| parse_dump_string(item)).collect()
}

/// Hand-rolled key reader for the `npa_lawref_precedence:` sibling map
/// (mirrors the lawref heading rule: rows deeper than the heading's indent,
/// comments stripped, stop at the next sibling heading).
fn precedence_table_keys(yaml: &str) -> Result<Vec<String>, String> {
    const HEADING: &str = "npa_lawref_precedence:";
    let mut keys = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in yaml.lines() {
        let line = raw.split('#').next().unwrap_or(raw);
        let trimmed = line.trim();
        if trimmed.is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if !in_map {
            if trimmed == HEADING {
                in_map = true;
                heading_indent = indent;
            }
            continue;
        }
        if indent <= heading_indent {
            break;
        }
        let Some((key, _)) = trimmed.split_once(':') else {
            return Err(format!("{HEADING} holds a non 'key: value' line"));
        };
        keys.push(key.trim().to_owned());
    }
    if !in_map {
        return Err(format!("{HEADING} heading is missing"));
    }
    Ok(keys)
}

/// Full round-trip: closed envelope, dump precedence keys ⊆ YAML table keys,
/// and every dumped value equals the parsed YAML table field for field.
fn assert_dump_round_trips(dump_text: &str, yaml: &str) -> Result<(), String> {
    let entries = dump_entries(dump_text)?;
    for (index, (key, _)) in entries.iter().enumerate() {
        if entries[..index].iter().any(|(seen, _)| seen == key) {
            return Err(format!("dump: duplicate key '{key}'"));
        }
    }
    for (key, _) in &entries {
        if !DUMP_ENVELOPE_KEYS.contains(&key.as_str())
            && !precedence_table_keys(yaml)?.iter().any(|name| name == key)
        {
            return Err(format!(
                "dump: extra key '{key}' is neither an envelope key nor an npa_lawref_precedence YAML key"
            ));
        }
    }
    for key in DUMP_ENVELOPE_KEYS {
        if !entries.iter().any(|(name, _)| name == key) {
            return Err(format!("dump: closed envelope is missing key '{key}'"));
        }
    }

    let string_value = |key: &str| -> Result<String, String> {
        parse_dump_string(
            entries
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value.as_str())
                .ok_or_else(|| format!("dump is missing key '{key}'"))?,
        )
    };
    let number_value = |key: &str| -> Result<u64, String> {
        parse_dump_number(
            entries
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value.as_str())
                .ok_or_else(|| format!("dump is missing key '{key}'"))?,
        )
    };
    let list_value = |key: &str| -> Result<Vec<String>, String> {
        parse_dump_string_list(
            entries
                .iter()
                .find(|(name, _)| name == key)
                .map(|(_, value)| value.as_str())
                .ok_or_else(|| format!("dump is missing key '{key}'"))?,
        )
    };

    if string_value("schema")? != "npa-lawref-precedence-dump/v1" {
        return Err("dump: schema must be 'npa-lawref-precedence-dump/v1'".to_owned());
    }
    if number_value("schema_version")? != 1 {
        return Err("dump: schema_version must be 1".to_owned());
    }
    if string_value("lifecycle")? != "[bounded]" {
        return Err("dump: lifecycle must stay '[bounded]'".to_owned());
    }
    let non_claims = list_value("non_claims")?;
    if non_claims.is_empty() {
        return Err("dump: non_claims must be non-empty".to_owned());
    }
    let joined = non_claims.join("\n");
    for mandatory in DUMP_MANDATORY_NON_CLAIMS {
        if !joined.contains(mandatory) {
            return Err(format!("dump: non_claims must carry '{mandatory}'"));
        }
    }

    let precedence = LawRefPrecedence::parse_yaml(yaml)
        .map_err(|err| format!("npa_lawref_precedence must parse for the round-trip: {err}"))?;
    let expect_list = |key: &str, want: &[String]| -> Result<(), String> {
        let got = list_value(key)?;
        if got == want {
            Ok(())
        } else {
            Err(format!(
                "dump key '{key}' = {got:?} does not round-trip the YAML table {want:?}"
            ))
        }
    };
    expect_list("pattern_ids", &precedence.pattern_ids)?;
    expect_list("digit_start_order", &precedence.digit_start_order)?;
    expect_list("letter_start_order", &precedence.letter_start_order)?;
    expect_list("sort_key", &precedence.sort_key)?;
    expect_list("chain_abbrev_ids", &precedence.chain_abbrev_ids)?;
    expect_list("amendment_abbrev_ids", &precedence.amendment_abbrev_ids)?;
    expect_list(
        "quoted_marker_abbrev_ids",
        &precedence.quoted_marker_abbrev_ids,
    )?;
    expect_list("fullword_tails", &precedence.fullword_tails)?;
    expect_list("anaphora_heads", &precedence.anaphora_heads)?;
    let expect_scalar = |key: &str, want: &str| -> Result<(), String> {
        let got = string_value(key)?;
        if got == want {
            Ok(())
        } else {
            Err(format!(
                "dump key '{key}' = '{got}' does not round-trip the YAML table '{want}'"
            ))
        }
    };
    expect_scalar(
        "overlap_date_docno_inside_amendment",
        &precedence.overlap_date_docno_inside_amendment,
    )?;
    expect_scalar(
        "overlap_same_pattern_containment",
        &precedence.overlap_same_pattern_containment,
    )?;
    Ok(())
}

#[test]
fn precedence_dump_round_trips_against_the_yaml_canon() {
    let dump = fs::read_to_string(precedence_dump_path())
        .expect("the tracked precedence-table dump must be readable");
    assert_dump_round_trips(&dump, EMBEDDED_ONTOLOGY_YAML)
        .expect("the dump must round-trip against the YAML table");
}

#[test]
fn hostile_extra_dump_key_fails_closed() {
    let dump = fs::read_to_string(precedence_dump_path())
        .expect("the tracked precedence-table dump must be readable");
    let mutated = dump.replacen("{", "{\n  \"future_hint\": 1,", 1);
    assert_ne!(
        mutated, dump,
        "the hostile mutation must change the dump text"
    );
    let error = assert_dump_round_trips(&mutated, EMBEDDED_ONTOLOGY_YAML)
        .expect_err("an extra dump key must fail closed");
    assert!(
        error.contains("future_hint") && error.contains("npa_lawref_precedence"),
        "expected the extra-key rejection to name the key, got: {error}"
    );
}
