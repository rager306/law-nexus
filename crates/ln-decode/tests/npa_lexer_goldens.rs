//! T03 full-coverage golden equality: the public covering lexer versus the
//! S01 sidecar on every tracked fragment (M197 S02).
//!
//! Sweeps all 44 `tests/fixtures/npa/` fragments through
//! [`ln_decode::lexer::lex`] and compares the stream token-by-token with the
//! S01 oracle (`fz44_npa_tokens.json`): token count, kind string↔enum,
//! abbrev id (equal for `Abbrev`, `None` elsewhere), UTF-8 byte span,
//! char-boundary lexeme slicing, and the covering invariant
//! (concat(lexemes) == text). No serde; npa fixtures are read through the
//! shared loader (`tests/npa_support`), never `include_str!`-ed into `src/`
//! and never decoded from the 5.2 MB source XML — the `#[ignore]`d harvest
//! audit stays in `npa_golden_fixtures.rs`.

#[allow(dead_code)]
mod npa_support;

use ln_decode::lexer::{lex, TokenKind};
use npa_support::{fixtures_dir, load_golden_fixtures, repo_root, LoadedFragment};

/// S01 pinned the fixture set at 44 fragments (the corpus quota plus the
/// syn-001 / syn-002 collision pair); the sweep must cover the whole set,
/// not a bucket subset.
const S01_FRAGMENT_COUNT: usize = 44;

/// Sidecar kind string → closed lexer kind; anything outside the nine-kind
/// S01 set fails the test closed.
fn golden_token_kind(name: &str) -> TokenKind {
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

/// Full token-by-token equality of `lex(text)` against the sidecar: token
/// count, kind, byte span, abbrev id, char-boundary slicing, non-empty
/// spans, and the covering invariant.
fn assert_fragment_matches_golden(fragment: &LoadedFragment) {
    let text: &str = &fragment.text;
    let tokens = lex(text);
    assert_eq!(
        tokens.len(),
        fragment.spans.len(),
        "{}: token count must equal the sidecar",
        fragment.id
    );
    let mut covered = String::with_capacity(text.len());
    for (index, (token, span)) in tokens.iter().zip(&fragment.spans).enumerate() {
        assert_eq!(
            token.kind,
            golden_token_kind(fragment.kinds[index]),
            "{}: kind mismatch at token[{index}]",
            fragment.id
        );
        assert_eq!(
            (token.span.start(), token.span.end()),
            (span.start(), span.end()),
            "{}: span mismatch at token[{index}]",
            fragment.id
        );
        let (start, end) = (token.span.start(), token.span.end());
        assert!(
            text.is_char_boundary(start) && text.is_char_boundary(end),
            "{}: token[{index}] span [{start},{end}) is not on char boundaries",
            fragment.id
        );
        assert!(
            !token.span.is_empty(),
            "{}: token[{index}] span must be non-empty",
            fragment.id
        );
        let lexeme = &text[start..end];
        assert_eq!(
            lexeme, fragment.lexemes[index],
            "{}: lexeme mismatch at token[{index}]",
            fragment.id
        );
        let expected_id = fragment.abbrev_ids[index].clone();
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
        covered.push_str(lexeme);
    }
    assert_eq!(
        covered, text,
        "{}: covering violated — concat(lexemes) must equal the text",
        fragment.id
    );
}

#[test]
fn lex_matches_the_s01_sidecar_on_every_fragment() {
    let fragments = load_golden_fixtures(&fixtures_dir(), &repo_root())
        .expect("NPA golden fixtures must load fail-closed");
    assert_eq!(
        fragments.len(),
        S01_FRAGMENT_COUNT,
        "the S01 fixture set is pinned at 44 fragments"
    );
    for fragment in &fragments {
        assert_fragment_matches_golden(fragment);
    }
}
