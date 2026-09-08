//! Clean-room C1 hostile token contour contract for the public NPA lexer.
//!
//! These cases are authored in-tree from documented NPA drafting shapes and
//! the hostile classes recorded by Review 27. This suite uses no vendor code,
//! vendor data, or vendor runtime (in particular, rutokenizer GPL-3.0,
//! Pullenti, and razdel are not dependencies or fixtures).
//!
//! This is diagnostic in-tree hostile evidence at stratum C1. It is not a
//! corpus admission manifest: the complete `hostile_case_manifest` envelope
//! (parser revision, corpus snapshot hash, and per-entry content hashes)
//! remains the responsibility of later corpus slices. Therefore this suite
//! deliberately does not modify `npa-corpus-control.yaml`.

use ln_decode::lexer::{lex, NpaToken, TokenKind};

fn kinds(tokens: &[NpaToken]) -> Vec<TokenKind> {
    tokens.iter().map(|token| token.kind).collect()
}

fn lexemes<'a>(tokens: &[NpaToken], source: &'a str) -> Vec<&'a str> {
    tokens.iter().map(|token| token.lexeme(source)).collect()
}

/// Every hostile contour must remain a true covering stream, including empty
/// and Unicode inputs. This also checks that every span is a UTF-8 boundary.
fn assert_covering(source: &str) {
    let tokens = lex(source);
    let mut rebuilt = String::new();
    let mut previous_end = 0;
    for token in &tokens {
        let start = token.span.start();
        let end = token.span.end();
        assert!(start < end, "non-empty token span required for {source:?}");
        assert_eq!(
            start, previous_end,
            "token spans must be contiguous for {source:?}"
        );
        assert!(source.is_char_boundary(start));
        assert!(source.is_char_boundary(end));
        rebuilt.push_str(token.lexeme(source));
        previous_end = end;
    }
    assert_eq!(
        previous_end,
        source.len(),
        "token stream must reach EOF for {source:?}"
    );
    assert_eq!(
        rebuilt, source,
        "lexer must not silently drop bytes for {source:?}"
    );
}

#[test]
fn clean_room_hostile_case_table_is_covering_and_closed() {
    // The table intentionally mixes token contours, not corpus excerpts.
    let cases = [
        "",
        "   ",
        "ё й",
        "ст.",
        "статьи",
        "Статьи",
        "пп.",
        "01.01.2020",
        "1.2",
        "195-ФЗ",
        "г.",
        "100 руб.",
        "И. И. Иванов",
        "пп. \"а\" в конце",
        "1. \"пункт\"",
        "ст. 1.2, от 01.01.2020",
    ];
    for source in cases {
        assert_covering(source);
    }
}

#[test]
fn utf8_words_have_exact_char_boundary_byte_spans() {
    let source = "ё й";
    let tokens = lex(source);
    assert_eq!(
        kinds(&tokens),
        [TokenKind::Word, TokenKind::Space, TokenKind::Word]
    );
    assert_eq!(lexemes(&tokens, source), ["ё", " ", "й"]);
    assert_eq!(
        (tokens[0].span.start(), tokens[0].span.end()),
        (0, "ё".len())
    );
    assert_eq!(
        (tokens[2].span.start(), tokens[2].span.end()),
        ("ё ".len(), source.len())
    );
}

#[test]
fn abbreviation_confusions_are_longest_first_and_case_bound() {
    let st = lex("ст.");
    assert_eq!(st.len(), 1);
    assert_eq!(st[0].kind, TokenKind::Abbrev);
    assert_eq!(st[0].abbrev_id.map(|id| id.as_str()), Some("st"));

    for source in ["статьи", "Статьи"] {
        let tokens = lex(source);
        assert_eq!(
            kinds(&tokens),
            [TokenKind::Word],
            "{source} stays a full word"
        );
    }

    let pp = lex("пп.");
    assert_eq!(kinds(&pp), [TokenKind::Abbrev]);
    assert_eq!(pp[0].abbrev_id.map(|id| id.as_str()), Some("pp"));
}

#[test]
fn date_and_hierarchy_windows_do_not_confuse_each_other() {
    let date = lex("01.01.2020");
    assert_eq!(kinds(&date), [TokenKind::Date]);
    assert_eq!(date[0].lexeme("01.01.2020"), "01.01.2020");

    let hierarchy = lex("1.2");
    assert_eq!(kinds(&hierarchy), [TokenKind::HierNum]);
    assert!(!hierarchy.iter().any(|token| token.kind == TokenKind::Date));

    // A date embedded next to another numeric window must retain its own
    // exact span; the surrounding punctuation/space is still covered.
    let source = "x 01.01.2020 (1.2)";
    let tokens = lex(source);
    assert!(tokens
        .iter()
        .any(|token| { token.kind == TokenKind::Date && token.lexeme(source) == "01.01.2020" }));
    assert!(tokens
        .iter()
        .any(|token| { token.kind == TokenKind::HierNum && token.lexeme(source) == "1.2" }));
    assert_covering(source);
}

#[test]
fn docno_hyphen_is_pinned_to_production_classification() {
    for source in ["195-ФЗ", "5-ФКЗ"] {
        let tokens = lex(source);
        assert_eq!(kinds(&tokens), [TokenKind::DocNo], "{source}");
        assert_eq!(tokens[0].lexeme(source), source);
    }
}

#[test]
fn ambiguous_abbreviations_and_initials_fail_closed() {
    let city = lex("г. Москва");
    assert_eq!(city[0].kind, TokenKind::Abbrev);
    assert_eq!(city[0].abbrev_id.map(|id| id.as_str()), Some("g"));
    assert!(!city.iter().any(|token| token.kind == TokenKind::LawCode));

    let money = lex("100 руб.");
    assert!(!money.iter().any(|token| token.kind == TokenKind::Abbrev));
    assert!(!money.iter().any(|token| token.abbrev_id.is_some()));

    let initials = lex("И. И. Иванов");
    assert!(initials.iter().all(|token| token.abbrev_id.is_none()));
    assert!(initials.iter().any(|token| token.kind == TokenKind::Word));
}

#[test]
fn enum_markers_survive_hostile_positions_without_panicking() {
    let quoted = lex("пп. \"а\"");
    assert_eq!(lexemes(&quoted, "пп. \"а\""), ["пп.", " ", "\"", "а", "\""]);
    assert_eq!(quoted[3].kind, TokenKind::EnumMarker);

    let trailing = lex("текст 1.");
    assert!(!trailing
        .iter()
        .any(|token| token.kind == TokenKind::EnumMarker));

    let block_end = lex("1. текст");
    assert_eq!(block_end[0].kind, TokenKind::EnumMarker);
    assert_covering("1. текст");
}

#[test]
fn empty_and_whitespace_only_inputs_are_empty_or_space_only() {
    assert!(lex("").is_empty());
    let whitespace = lex(" \t\n");
    assert_eq!(kinds(&whitespace), [TokenKind::Space]);
    assert_covering("");
    assert_covering(" \t\n");
}

#[test]
fn token_kind_is_closed_and_unknown_shapes_fall_back_without_unknown_variants() {
    let sources = ["неизвестный §", "№ 149-ФЗ", "@@@", "ё", "100 руб."];
    for source in sources {
        let tokens = lex(source);
        assert_covering(source);
        for token in tokens {
            assert!(matches!(
                token.kind,
                TokenKind::Word
                    | TokenKind::Abbrev
                    | TokenKind::HierNum
                    | TokenKind::Date
                    | TokenKind::DocNo
                    | TokenKind::EnumMarker
                    | TokenKind::LawCode
                    | TokenKind::Punct
                    | TokenKind::Space
            ));
        }
    }
}
