//! S02 T01 contract tests: the public covering lexer `ln_decode::lexer`.
//!
//! The S01 sidecar JSON (`fz44_npa_tokens.json`) is the oracle; T01 pins the
//! syn-001 fragment inline (kind + byte span + null abbrev id). No serde, no
//! XML decoding: fixture text is read from `tests/fixtures/npa/` at test time.

use std::path::Path;

use ln_decode::lexer::{lex, AbbrevId, NpaToken, TokenKind};

fn syn_001_text() -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/fixtures/npa/syn-001.txt");
    std::fs::read_to_string(&path).expect("tests/fixtures/npa/syn-001.txt must be readable")
}

fn kinds(tokens: &[NpaToken]) -> Vec<TokenKind> {
    tokens.iter().map(|token| token.kind).collect()
}

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
    let src = "1.";
    let tokens = lex(src);
    assert_eq!(kinds(&tokens), [TokenKind::Word, TokenKind::Punct]);
    assert_eq!(tokens[0].lexeme(src), "1");
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
    // 99 months / 99 days violate the Date ranges: the scanner must not mint a
    // Date token from them.
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
        "2.3.1",
        "a,b).",
        "\u{00a0}x",
        "слово",
        "1) а)",
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
