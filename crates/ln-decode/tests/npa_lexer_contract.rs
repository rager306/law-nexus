//! S02 contract tests for the public covering lexer `ln_decode::lexer`.
//!
//! T01 pinned the syn-001 sidecar oracle inline; T02 extends the scanner to
//! `EnumMarker` / `DocNo` / `LawCode` (D330 rules 5, 6, 10) and compares
//! whole fragments against the shared S01 loader in `tests/npa_support`
//! (syn-002, enum-list, heading, and lawcode buckets). No serde, no XML
//! decoding: fixture text is read from `tests/fixtures/npa/` at test time.
//! The full 44-fragment sweep stays in T03 (`npa_lexer_goldens`).

// Shared loader: this binary exercises a subset of the S01 oracle module;
// unused-in-this-target items are used by npa_golden_fixtures.rs.
#[allow(dead_code)]
mod npa_support;

use std::path::Path;

use ln_decode::lexer::{lex, AbbrevId, NpaToken, TokenKind};
use npa_support::{fixtures_dir, load_golden_fixtures, repo_root, LoadedFragment};

fn syn_001_text() -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa/syn-001.txt");
    std::fs::read_to_string(&path).expect("tests/fixtures/npa/syn-001.txt must be readable")
}

fn kinds(tokens: &[NpaToken]) -> Vec<TokenKind> {
    tokens.iter().map(|token| token.kind).collect()
}

fn lexemes<'s>(tokens: &[NpaToken], src: &'s str) -> Vec<&'s str> {
    tokens.iter().map(|token| token.lexeme(src)).collect()
}

fn kind_of(name: &str) -> TokenKind {
    match name {
        "Word" => TokenKind::Word,
        "Abbrev" => TokenKind::Abbrev,
        "HierNum" => TokenKind::HierNum,
        "Date" => TokenKind::Date,
        "DocNo" => TokenKind::DocNo,
        "EnumMarker" => TokenKind::EnumMarker,
        "LawCode" => TokenKind::LawCode,
        "Punct" => TokenKind::Punct,
        "Space" => TokenKind::Space,
        other => panic!("sidecar kind '{other}' is outside the closed S01 set"),
    }
}

fn load_fragment(id: &str) -> LoadedFragment {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");
    fragments
        .into_iter()
        .find(|fragment| fragment.id == id)
        .unwrap_or_else(|| panic!("fixture '{id}' must exist"))
}

/// Full token-by-token equality against the S01 sidecar: token count, kind,
/// byte span, and abbrev id (`None` everywhere but `Abbrev`).
fn assert_matches_golden(fragment: &LoadedFragment) {
    let tokens = lex(&fragment.text);
    assert_eq!(
        tokens.len(),
        fragment.spans.len(),
        "{}: token count must equal the sidecar",
        fragment.id
    );
    for (index, (token, span)) in tokens.iter().zip(&fragment.spans).enumerate() {
        assert_eq!(
            token.kind,
            kind_of(fragment.kinds[index]),
            "{}: kind mismatch at token[{index}]",
            fragment.id
        );
        assert_eq!(
            (token.span.start(), token.span.end()),
            (span.start(), span.end()),
            "{}: span mismatch at token[{index}]",
            fragment.id
        );
        let expected_id = fragment.abbrev_ids[index].as_deref();
        match (token.abbrev_id, expected_id) {
            (None, None) => {}
            (Some(actual), Some(expected)) => assert_eq!(
                actual.as_str(),
                expected,
                "{}: abbrev id mismatch at token[{index}]",
                fragment.id
            ),
            (actual, expected) => panic!(
                "{}: abbrev id mismatch at token[{index}]: lexer {actual:?}, sidecar {expected:?}",
                fragment.id
            ),
        }
    }
}

// ---------------------------------------------------------------------------
// T01 surface (kept green; only `1.` locality is re-pinned per D330 rule 6).
// ---------------------------------------------------------------------------

#[test]
fn empty_input_yields_no_tokens() {
    assert!(lex("").is_empty());
}

#[test]
fn whitespace_only_input_is_a_single_space_token() {
    let tokens = lex("   ");
    assert_eq!(kinds(&tokens), [TokenKind::Space]);
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 3));
    assert_eq!(tokens[0].abbrev_id, None);
}

#[test]
fn abbrev_keeps_trailing_dot_and_hier_num_stays_whole() {
    let src = "ст. 15.1";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::Abbrev, TokenKind::Space, TokenKind::HierNum]
    );
    assert_eq!(tokens[0].abbrev_id.map(AbbrevId::as_str), Some("st"));
    assert_eq!(
        tokens[0].lexeme(src),
        "ст.",
        "the abbrev dot stays inside the token"
    );
    assert_eq!(tokens[2].lexeme(src), "15.1");
    assert_eq!((tokens[2].span.start(), tokens[2].span.end()), (6, 10));
}

#[test]
fn pp_is_one_longest_match_abbrev_not_two_p_tokens() {
    let tokens = lex("пп.");
    assert_eq!(
        tokens.len(),
        1,
        "`пп.` must match longest-first as a single token"
    );
    assert_eq!(tokens[0].kind, TokenKind::Abbrev);
    assert_eq!(tokens[0].abbrev_id.map(AbbrevId::as_str), Some("pp"));
    assert_eq!(tokens[0].lexeme("пп."), "пп.");
}

#[test]
fn date_beats_hier_num() {
    let tokens = lex("01.01.2028");
    assert_eq!(tokens.len(), 1);
    assert_eq!(tokens[0].kind, TokenKind::Date);
    assert_ne!(tokens[0].kind, TokenKind::HierNum);
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 10));
}

#[test]
fn undotted_number_is_not_hier_num() {
    // Mid-text `1.` (after a word): EnumMarker locality is start-of-input
    // only and `1.` is never a HierNum — Word + Punct.
    let src = "x 1.";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Space,
            TokenKind::Word,
            TokenKind::Punct
        ]
    );
    assert_eq!(tokens[2].lexeme(src), "1");
    assert_eq!(tokens[3].lexeme(src), ".");
}

#[test]
fn capitalized_ch_is_word_plus_punct_not_abbrev() {
    let src = "Ч. 1.1";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::HierNum
        ]
    );
    assert!(
        tokens.iter().all(|token| token.abbrev_id.is_none()),
        "canonical `ч.` is lowercase"
    );
    assert_eq!(tokens[0].lexeme(src), "Ч");
    assert_eq!(tokens[1].lexeme(src), ".");
    assert_eq!((tokens[3].span.start(), tokens[3].span.end()), (4, 7));
}

#[test]
fn out_of_range_calendar_numbers_fall_back_to_hier_num() {
    // 99 months / 99 days violate the Date ranges: the scanner must not mint
    // a Date token from them, and it must not mistag the shape as EnumMarker.
    let tokens = lex("99.99.2028");
    assert_eq!(tokens.len(), 1);
    assert_eq!(tokens[0].kind, TokenKind::HierNum);
}

#[test]
fn lex_is_covering_and_boundary_safe() {
    let syn_001 = syn_001_text();
    let inputs = [
        "",
        "   ",
        "ст. 15.1",
        "пп.",
        "ст.ст.",
        "01.01.2028",
        "99.99.2028",
        "Ч. 1.1",
        "1.",
        "1) а)",
        "1. Значение",
        "2.3.1",
        "318-ФЗ",
        "N 44-ФЗ",
        "Федеральный",
        "ФКЗ",
        "пп. \"а\"",
        "\"а\").",
        "a,b).",
        "\u{00a0}x",
        "слово",
        "глава",
        "абзац",
        "редакция",
        "Абз. 2",
        "Ст. 33",
        "Гл. 2",
        "СТ.СТ.",
        "П. Иванов",
        "А.",
        "руб.",
        "Г. Москва",
        "Ч. 1.1 ст. 33",
        syn_001.as_str(),
    ];
    for src in inputs {
        let tokens = lex(src);
        let mut rebuilt = String::new();
        for token in &tokens {
            assert!(
                !token.span.is_empty(),
                "spans must be non-empty (TextSpan::try_new)"
            );
            assert!(
                src.is_char_boundary(token.span.start()) && src.is_char_boundary(token.span.end()),
                "spans must sit on char boundaries"
            );
            rebuilt.push_str(&src[token.span.start()..token.span.end()]);
        }
        assert_eq!(
            rebuilt, src,
            "lex must never drop bytes: concat(lexemes) == src"
        );
    }
}

#[test]
fn syn_001_matches_s01_sidecar_token_by_token() {
    let text = syn_001_text();
    let tokens = lex(&text);
    // Oracle: `fz44_npa_tokens.json` fragment syn-001 (S01, 0 markup violations).
    // Byte spans: HierNum [56,60) = "15.1", Date [85,95) = "01.01.2028".
    let expected: [(&str, usize, usize); 15] = [
        ("Word", 0, 26),
        ("Space", 26, 27),
        ("Word", 27, 43),
        ("Punct", 43, 44),
        ("Space", 44, 45),
        ("Word", 45, 55),
        ("Space", 55, 56),
        ("HierNum", 56, 60),
        ("Space", 60, 61),
        ("Word", 61, 79),
        ("Space", 79, 80),
        ("Word", 80, 84),
        ("Space", 84, 85),
        ("Date", 85, 95),
        ("Punct", 95, 96),
    ];
    assert_eq!(
        tokens.len(),
        expected.len(),
        "token count must equal the sidecar"
    );
    for (token, (kind, start, end)) in tokens.iter().zip(expected.iter()) {
        assert_eq!(
            token.kind.as_str(),
            *kind,
            "kind mismatch at span [{start},{end})"
        );
        assert_eq!((token.span.start(), token.span.end()), (*start, *end));
        assert!(token.abbrev_id.is_none(), "syn-001 has no abbreviations");
    }
    assert_eq!(tokens[7].lexeme(&text), "15.1");
    assert_eq!(tokens[13].lexeme(&text), "01.01.2028");
}

// ---------------------------------------------------------------------------
// T02: EnumMarker / DocNo / LawCode units (D330 rules 5, 6, 10).
// ---------------------------------------------------------------------------

#[test]
fn start_digit_dot_is_enum_marker() {
    let src = "1. Значение";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::EnumMarker, TokenKind::Space, TokenKind::Word]
    );
    assert_eq!(
        tokens[0].lexeme(src),
        "1.",
        "the dot stays inside the marker"
    );
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 2));
}

#[test]
fn start_digit_paren_is_enum_marker() {
    for (src, marker) in [
        ("1) планирование", "1)"),
        ("10) взносы", "10)"),
        ("11) специфика", "11)"),
    ] {
        let tokens = lex(src);
        assert_eq!(tokens[0].kind, TokenKind::EnumMarker, "{src}");
        assert_eq!(tokens[0].lexeme(src), marker, "{src}");
    }
}

#[test]
fn start_cyrillic_paren_is_enum_marker() {
    let src = "а) требования";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::EnumMarker, TokenKind::Space, TokenKind::Word]
    );
    assert_eq!(tokens[0].lexeme(src), "а)");
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 3));
}

#[test]
fn heading_number_is_word_punct_not_enum_marker() {
    // fz44-027 shape: `Глава 1. ...` — mid-text `1.` is Word + Punct, never
    // EnumMarker (locality) and never HierNum (no inner digits).
    let src = "Глава 1. ОБЩИЕ ПОЛОЖЕНИЯ";
    let tokens = lex(src);
    assert_eq!(
        lexemes(&tokens, src),
        ["Глава", " ", "1", ".", " ", "ОБЩИЕ", " ", "ПОЛОЖЕНИЯ"]
    );
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Space,
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::Word,
            TokenKind::Space,
            TokenKind::Word
        ]
    );
}

#[test]
fn quoted_enum_marker_beats_greedy_punct() {
    let src = "пп. \"а\"";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Abbrev,
            TokenKind::Space,
            TokenKind::Punct,
            TokenKind::EnumMarker,
            TokenKind::Punct
        ]
    );
    assert_eq!(tokens[0].abbrev_id.map(AbbrevId::as_str), Some("pp"));
    assert_eq!(
        lexemes(&tokens, src),
        ["пп.", " ", "\"", "а", "\""],
        "quotes stay Punct; the letter between them is the EnumMarker"
    );
}

#[test]
fn quoted_marker_closing_punct_stays_greedy() {
    let src = "\"а\").";
    let tokens = lex(src);
    assert_eq!(
        lexemes(&tokens, src),
        ["\"", "а", "\")."],
        "the closing quote and the outer punctuation form one Punct run"
    );
    assert_eq!(
        kinds(&tokens),
        [TokenKind::Punct, TokenKind::EnumMarker, TokenKind::Punct]
    );
}

#[test]
fn close_paren_punct_runs_stay_maximal() {
    let src = "слово), другое).";
    let tokens = lex(src);
    assert_eq!(lexemes(&tokens, src), ["слово", "),", " ", "другое", ")."]);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::Word,
            TokenKind::Punct
        ]
    );
}

#[test]
fn law_code_is_exact_whole_run_equality() {
    let tokens = lex("ФЗ");
    assert_eq!(kinds(&tokens), [TokenKind::LawCode]);
    let src = "ФКЗ от 04.10.2022";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::LawCode,
            TokenKind::Space,
            TokenKind::Word,
            TokenKind::Space,
            TokenKind::Date
        ]
    );
    for src in [
        "Федеральный",
        "федеральный орган",
        "фз",
        "ФЗЫ",
        "Федеральный закон N 318-ФЗ",
    ] {
        assert!(
            !lex(src)
                .iter()
                .any(|token| token.kind == TokenKind::LawCode),
            "'{src}' must never mint a LawCode token"
        );
    }
    assert_eq!(kinds(&lex("Федеральный")), [TokenKind::Word]);
}

#[test]
fn doc_no_keeps_hyphen_and_suffix_in_one_token() {
    for src in ["318-ФЗ", "5-ФКЗ"] {
        let tokens = lex(src);
        assert_eq!(tokens.len(), 1, "'{src}' is one DocNo token");
        assert_eq!(tokens[0].kind, TokenKind::DocNo);
        assert_eq!(tokens[0].lexeme(src), src);
    }
}

#[test]
fn latin_n_stays_word_before_doc_no() {
    let src = "N 44-ФЗ";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::Word, TokenKind::Space, TokenKind::DocNo]
    );
    assert_eq!(tokens[0].lexeme(src), "N", "D330 rule 10: Latin N is Word");
    assert_eq!(
        tokens[2].lexeme(src),
        "44-ФЗ",
        "the hyphen stays inside the DocNo"
    );
}

// ---------------------------------------------------------------------------
// T03: D329 lexicon ids from the YAML `npa_abbrev_lexicon` map + shape units.
// All inputs are in-test `&str` (no new synthetic txt; S01 quotas untouched).
// ---------------------------------------------------------------------------

#[test]
fn d329_abbrev_ids_resolve_from_the_yaml_lexicon() {
    // The D329 subset below has zero hits in the tracked 44-ФЗ corpus; each
    // must still lex from the YAML map as a canonical Abbrev token.
    for (src, id) in [
        ("гл.", "gl"),
        ("разд.", "razd"),
        ("подп.", "podp"),
        ("абз.", "abz"),
        ("прил.", "pril"),
        ("прим.", "prim"),
        ("утв.", "utv"),
        ("ср.", "sr"),
        ("изм.", "izm"),
        ("см.", "sm"),
    ] {
        let tokens = lex(src);
        assert_eq!(tokens.len(), 1, "{src} is a single token");
        assert_eq!(tokens[0].kind, TokenKind::Abbrev, "{src}");
        assert_eq!(
            tokens[0].abbrev_id.map(AbbrevId::as_str),
            Some(id),
            "{src} must carry the canonical YAML id"
        );
        assert_eq!(tokens[0].lexeme(src), src, "{src} keeps its dot inside");
    }
}

#[test]
fn stst_is_one_abbrev_not_two_st_tokens() {
    let tokens = lex("ст.ст.");
    assert_eq!(tokens.len(), 1, "ст.ст. must match longest-first");
    assert_eq!(tokens[0].kind, TokenKind::Abbrev);
    assert_eq!(tokens[0].abbrev_id.map(AbbrevId::as_str), Some("stst"));
    assert_eq!(tokens[0].lexeme("ст.ст."), "ст.ст.");
}

#[test]
fn three_segment_hier_num_is_one_token() {
    let src = "2.3.1";
    let tokens = lex(src);
    assert_eq!(tokens.len(), 1, "2.3.1 is a single HierNum");
    assert_eq!(tokens[0].kind, TokenKind::HierNum);
    assert_eq!(tokens[0].lexeme(src), "2.3.1");
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 5));
}

#[test]
fn g_is_always_abbrev_g_not_a_year_or_city() {
    for src in ["г.", "г. 2028", "г. Москва"] {
        let tokens = lex(src);
        assert_eq!(tokens[0].kind, TokenKind::Abbrev, "{src}");
        assert_eq!(
            tokens[0].abbrev_id.map(AbbrevId::as_str),
            Some("g"),
            "{src}: `г.` never resolves a year or a city"
        );
        assert_eq!(tokens[0].lexeme(src), "г.", "{src}");
    }
}

#[test]
fn full_level_words_stay_words_for_s03_morphology() {
    // C2 (M198 S02/T02): in-word prefixes must not fold onto stem-ge-2
    // lexemes either — `абзац`/`редакция` cut mid-char, never mint abz/red.
    for src in ["глава", "часть", "подпункт", "раздел", "абзац", "редакция"]
    {
        let tokens = lex(src);
        assert_eq!(kinds(&tokens), [TokenKind::Word], "{src} stays a Word");
        assert!(
            tokens.iter().all(|token| token.abbrev_id.is_none()),
            "{src} must not mint an Abbrev id (S03 morphology owns the lexeme)"
        );
    }
}

// ---------------------------------------------------------------------------
// T02: shared-loader fragment equality (not the full 44 sweep — that is T03).
// ---------------------------------------------------------------------------

#[test]
fn syn_002_matches_s01_sidecar_token_by_token() {
    let fragment = load_fragment("syn-002");
    assert_matches_golden(&fragment);
    let text = &fragment.text;
    let tokens = lex(text);
    // Plan pins: list-start marker `1.` keeps its dot at bytes [0,2); the
    // separate in-sentence HierNum `5.1` at [86,89); zero Abbrev tokens.
    assert_eq!(tokens[0].kind, TokenKind::EnumMarker);
    assert_eq!(tokens[0].lexeme(text), "1.");
    assert_eq!((tokens[0].span.start(), tokens[0].span.end()), (0, 2));
    let hier = tokens
        .iter()
        .find(|token| token.kind == TokenKind::HierNum)
        .expect("syn-002 must carry the in-sentence HierNum");
    assert_eq!(hier.lexeme(text), "5.1");
    assert_eq!((hier.span.start(), hier.span.end()), (86, 89));
    assert!(tokens.iter().all(|token| token.abbrev_id.is_none()));
}

#[test]
fn enum_list_fragments_match_s01_sidecar() {
    for id in [
        "fz44-022", "fz44-023", "fz44-024", "fz44-025", "fz44-026", "fz44-031", "fz44-032",
        "fz44-033", "fz44-035", "fz44-040", "fz44-041",
    ] {
        let fragment = load_fragment(id);
        assert_matches_golden(&fragment);
        let tokens = lex(&fragment.text);
        assert_eq!(
            tokens[0].kind,
            TokenKind::EnumMarker,
            "{id} must open with the list-start marker"
        );
    }
    let fz44_023 = load_fragment("fz44-023");
    assert_eq!(lex(&fz44_023.text)[0].lexeme(&fz44_023.text), "1)");
    let fz44_024 = load_fragment("fz44-024");
    assert_eq!(lex(&fz44_024.text)[0].lexeme(&fz44_024.text), "а)");
}

#[test]
fn heading_fragment_fz44_027_matches_s01_sidecar() {
    let fragment = load_fragment("fz44-027");
    assert_matches_golden(&fragment);
    let text = &fragment.text;
    let tokens = lex(text);
    assert_eq!(tokens[0].lexeme(text), "Глава");
    assert_eq!(
        tokens[2].kind,
        TokenKind::Word,
        "heading number is a Word, never HierNum"
    );
    assert_eq!(tokens[2].lexeme(text), "1");
    assert_eq!(tokens[3].kind, TokenKind::Punct, "heading dot stays Punct");
    assert_eq!(tokens[3].lexeme(text), ".");
    assert!(
        !tokens
            .iter()
            .any(|token| token.kind == TokenKind::EnumMarker),
        "a heading mints no EnumMarker"
    );
    assert!(
        !tokens.iter().any(|token| token.kind == TokenKind::HierNum),
        "a heading mints no HierNum"
    );
}

#[test]
fn quoted_enum_marker_corpus_fragments_match_s01_sidecar() {
    // `пп. "X"` subpoint labels: the marker sits mid-fragment, quotes stay
    // Punct on both sides (fz44-039 additionally pins LawCode/DocNo).
    for id in [
        "fz44-011", "fz44-012", "fz44-013", "fz44-014", "fz44-036", "fz44-039", "fz44-042",
    ] {
        let fragment = load_fragment(id);
        assert_matches_golden(&fragment);
        let text = &fragment.text;
        let tokens = lex(text);
        assert!(
            tokens
                .iter()
                .enumerate()
                .any(|(index, token)| token.kind == TokenKind::EnumMarker && index > 0),
            "{id} must pin a mid-fragment quoted EnumMarker"
        );
    }
}

#[test]
fn lawcode_fragments_match_s01_sidecar() {
    for id in ["fz44-001", "fz44-037", "fz44-038", "fz44-039"] {
        let fragment = load_fragment(id);
        assert_matches_golden(&fragment);
    }

    let fz44_037 = load_fragment("fz44-037");
    let text = &fz44_037.text;
    let tokens = lex(text);
    assert!(
        tokens
            .iter()
            .any(|token| token.kind == TokenKind::LawCode && token.lexeme(text) == "ФКЗ"),
        "fz44-037 must pin LawCode ФКЗ"
    );
    let docnos: Vec<&str> = tokens
        .iter()
        .filter(|token| token.kind == TokenKind::DocNo)
        .map(|token| token.lexeme(text))
        .collect();
    for expected in ["5-ФКЗ", "6-ФКЗ", "7-ФКЗ", "8-ФКЗ"] {
        assert!(
            docnos.contains(&expected),
            "fz44-037 must pin DocNo {expected}"
        );
    }
    assert!(
        tokens.iter().any(|token| token.kind == TokenKind::Date),
        "fz44-037 must keep its Date tokens"
    );
    assert!(
        fz44_037
            .abbrev_ids
            .iter()
            .any(|id| id.as_deref() == Some("ch")),
        "fz44-037 must pin Abbrev ch"
    );
    assert!(
        fz44_037
            .abbrev_ids
            .iter()
            .any(|id| id.as_deref() == Some("st")),
        "fz44-037 must pin Abbrev st"
    );

    let fz44_038 = load_fragment("fz44-038");
    let text = &fz44_038.text;
    let tokens = lex(text);
    assert_eq!(
        tokens[0].lexeme(text),
        "П",
        "capitalized `П.` is Word + Punct, never an Abbrev"
    );
    assert_eq!(tokens[1].kind, TokenKind::Punct);
    assert_eq!(tokens[1].lexeme(text), ".");
    assert!(
        tokens
            .iter()
            .any(|token| token.kind == TokenKind::LawCode && token.lexeme(text) == "ФЗ"),
        "fz44-038 must pin LawCode ФЗ"
    );
    assert!(
        tokens
            .iter()
            .any(|token| token.kind == TokenKind::DocNo && token.lexeme(text) == "124-ФЗ"),
        "fz44-038 must pin DocNo 124-ФЗ"
    );
}

// ---------------------------------------------------------------------------
// C2 (M198 S02/T02): stem-ge-2 Unicode fold and new-form contracts. Lexemes
// with >= 2 alphabetic chars match case-insensitively (Абз./Ст./Гл./СТ.СТ.);
// one-letter lexemes (ч./п./г.) stay lowercase-exact so hostile initials
// never mint Abbrevs (Q3 fail-closed).
// ---------------------------------------------------------------------------

/// Capitalized heading forms fold onto their lowercase canonical lexemes
/// (the C1 npa finding: heading Абз./Ст./Гл. sat in the unknown tail).
#[test]
fn capitalized_stem_ge2_heading_forms_fold_to_abbrevs() {
    for (src, id, head) in [
        ("Абз. 2", "abz", "Абз."),
        ("Ст. 33", "st", "Ст."),
        ("Гл. 2", "gl", "Гл."),
    ] {
        let tokens = lex(src);
        assert_eq!(
            kinds(&tokens),
            [TokenKind::Abbrev, TokenKind::Space, TokenKind::Word],
            "{src} must lex Abbrev + Space + Word"
        );
        assert_eq!(
            tokens[0].abbrev_id.map(AbbrevId::as_str),
            Some(id),
            "{src}: the capitalized form must carry the canonical lowercase id"
        );
        assert_eq!(tokens[0].lexeme(src), head, "{src} keeps its dot inside");
    }
}

/// `СТ.СТ.` is ONE longest-first `stst` token, never two `st` tokens.
#[test]
fn fully_uppercase_stst_is_one_longest_first_abbrev() {
    let src = "СТ.СТ.";
    let tokens = lex(src);
    assert_eq!(tokens.len(), 1, "СТ.СТ. must match stst longest-first");
    assert_eq!(tokens[0].kind, TokenKind::Abbrev);
    assert_eq!(tokens[0].abbrev_id.map(AbbrevId::as_str), Some("stst"));
    assert_eq!(tokens[0].lexeme(src), src);
}

/// Hostile initials: one-letter lexemes are lowercase-exact, so `П.` and
/// `А.` stay Word + Punct and never mint the Abbrev `p`.
#[test]
fn hostile_capitalized_initials_stay_word_plus_punct() {
    let src = "П. Иванов";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::Word
        ],
        "capitalized `П.` must not fold onto the one-letter `п.`"
    );
    assert_eq!(tokens[0].lexeme(src), "П");
    assert!(tokens.iter().all(|token| token.abbrev_id.is_none()));

    let tokens = lex("А.");
    assert_eq!(kinds(&tokens), [TokenKind::Word, TokenKind::Punct]);
    assert!(tokens.iter().all(|token| token.abbrev_id.is_none()));
}

/// `Г. Москва` (capitalized city initial) stays Word + Punct: the 1-letter
/// `г.` is lowercase-exact even though the fold exists for stem-ge-2.
#[test]
fn hostile_capitalized_g_stays_word_not_abbrev_g() {
    let src = "Г. Москва";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::Word
        ],
        "`Г.` must not fold onto the lowercase-exact `г.`"
    );
    assert_eq!(tokens[0].lexeme(src), "Г");
    assert!(tokens.iter().all(|token| token.abbrev_id.is_none()));
}

/// `руб.` is not a lexicon id and must never become one (no C2 lexeme
/// growth): Word + Punct.
#[test]
fn hostile_rub_is_word_plus_punct_never_a_lexicon_id() {
    let src = "руб.";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::Word, TokenKind::Punct],
        "руб. must stay outside the 17-id lexicon"
    );
    assert!(tokens.iter().all(|token| token.abbrev_id.is_none()));
}

/// proof1 sentence across the fold: capitalized `Ч.` stays Word + Punct
/// while lowercase `ст.` keeps minting Abbrev st.
#[test]
fn mixed_hostile_and_abbrev_proof1_sentence() {
    let src = "Ч. 1.1 ст. 33";
    let tokens = lex(src);
    assert_eq!(
        kinds(&tokens),
        [
            TokenKind::Word,
            TokenKind::Punct,
            TokenKind::Space,
            TokenKind::HierNum,
            TokenKind::Space,
            TokenKind::Abbrev,
            TokenKind::Space,
            TokenKind::Word
        ],
        "proof1 mix: `Ч.` Word+Punct, `1.1` HierNum, `ст.` Abbrev st"
    );
    assert_eq!(tokens[0].lexeme(src), "Ч");
    assert_eq!(
        tokens[5].abbrev_id.map(AbbrevId::as_str),
        Some("st"),
        "lowercase `ст.` keeps its canonical id after the fold"
    );
}
