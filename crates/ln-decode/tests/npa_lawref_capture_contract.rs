//! Contract tests for the LawRef capture layer (M199 S02 T01).
//!
//! T01 ships the capture SURFACE: the `LawRef` product type over the frozen
//! covering lexer and the `npa_lawref_precedence` YAML table (KBO-R025/R030).
//! Matching is T02's business: `capture_lawrefs` is stub-ok empty, and the
//! first-proof expectations live behind `#[ignore]` so the default suite
//! stays green until T02 implements the matchers and removes the ignore.
//!
//! Every fixture is an inline string; the corpus (`consru_export`) is never
//! opened. No `#[path]` include of `npa_lawref_support` (D335): this suite
//! reads the tracked src and YAML files directly.

use std::fs;
use std::path::Path;

use ln_decode::lawref::{capture_lawrefs, LawRef, LawRefPrecedence};
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
// (d) Stub-ok capture: empty results, nothing logged, corpus never opened.
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
// First proof (RED by design in T01): behind #[ignore], T02 removes it.
// ---------------------------------------------------------------------------

#[test]
#[ignore = "T01 ships the capture surface as a stub-ok empty capture; T02 implements the precedence-table matchers and removes this ignore"]
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
