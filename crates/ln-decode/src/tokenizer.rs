/// One token produced by the private alphabetic splitter.
///
/// `AlphabeticToken` is consumed by references, temporal and unknown_forms.
/// It is intentionally distinct from [`CoveringWord`]: the two producers are
/// not aliases (ADR-0028 dual tokenizer), and neither view can be substituted
/// for the other.
pub(crate) struct AlphabeticToken {
    pub(crate) normalized: String,
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// One alphabetic Word projected from the public covering lexer.
///
/// `CoveringWord` is consumed by morphology only. It is intentionally distinct
/// from [`AlphabeticToken`], whose splitter view includes abbreviation stems.
pub(crate) struct CoveringWord {
    pub(crate) normalized: String,
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// Tokenize text into alphabetic sequences with UTF-8 byte offsets.
///
/// Non-alphabetic characters act as delimiters. Each token's `normalized`
/// field is the lowercase form of the original text slice. Does **not**
/// fold `ё`→`е`. Digit runs are skipped. Used by references, temporal,
/// and unknown_forms — not by morphology.
pub(crate) fn tokenize(text: &str) -> Vec<AlphabeticToken> {
    let mut result = Vec::new();
    let mut chars = text.char_indices().peekable();
    while let Some((start, character)) = chars.next() {
        if !character.is_alphabetic() {
            continue;
        }
        let mut end = start + character.len_utf8();
        while let Some(&(index, next)) = chars.peek() {
            if !next.is_alphabetic() {
                break;
            }
            chars.next();
            end = index + next.len_utf8();
        }
        result.push(AlphabeticToken {
            normalized: text[start..end].to_lowercase(),
            start,
            end,
        });
    }
    result
}

/// Alphabetic covering [`crate::lexer::TokenKind::Word`] tokens, lowercase,
/// `ё`/`е` not folded. Digit-only `Word` runs from `lex` are dropped.
///
/// Morphology reads this projection. Abbrev stems (`ст.` → `Abbrev{st}`) are
/// absent by construction. Do not substitute for [`tokenize`].
pub(crate) fn words_from_covering(text: &str) -> Vec<CoveringWord> {
    crate::lexer::lex(text)
        .into_iter()
        .filter(|token| token.kind == crate::lexer::TokenKind::Word)
        .filter_map(|token| {
            let start = token.span.start();
            let end = token.span.end();
            let slice = &text[start..end];
            if !slice.chars().any(char::is_alphabetic) {
                return None;
            }
            Some(CoveringWord {
                normalized: slice.to_lowercase(),
                start,
                end,
            })
        })
        .collect()
}

#[cfg(test)]
mod covering_word_projection_tests {
    use super::{tokenize, words_from_covering};

    #[test]
    fn abbrev_stem_is_alphabetic_split_not_covering_word() {
        let text = "ст. 5";
        let alpha: Vec<String> = tokenize(text)
            .into_iter()
            .map(|token| token.normalized)
            .collect();
        let covering: Vec<String> = words_from_covering(text)
            .into_iter()
            .map(|token| token.normalized)
            .collect();
        assert_eq!(alpha, ["ст".to_owned()]);
        assert!(covering.is_empty(), "Abbrev{{st}} must not project as Word");
    }

    #[test]
    fn fullword_article_is_covering_word_with_source_span() {
        let text = "статьи 5";
        let words = words_from_covering(text);
        assert_eq!(words.len(), 1);
        assert_eq!(words[0].normalized, "статьи");
        assert_eq!(&text[words[0].start..words[0].end], "статьи");
    }

    #[test]
    fn typed_views_have_no_cross_conversion_or_legacy_word_token() {
        let src_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
        let mut source = String::new();
        for entry in std::fs::read_dir(&src_dir).expect("ln-decode src must be readable") {
            let path = entry.expect("source entry must be readable").path();
            if path.extension().is_some_and(|ext| ext == "rs") {
                source.push_str(
                    &std::fs::read_to_string(path).expect("Rust source must be readable"),
                );
            }
        }
        assert!(source.contains("struct AlphabeticToken"));
        assert!(source.contains("struct CoveringWord"));
        let legacy_struct = ["struct ", "WordToken"].concat();
        let alpha_to_covering = ["impl From<AlphabeticToken> for ", "CoveringWord"].concat();
        let covering_to_alpha = ["impl From<CoveringWord> for ", "AlphabeticToken"].concat();
        assert!(!source.contains(&legacy_struct));
        assert!(!source.contains(&alpha_to_covering));
        assert!(!source.contains(&covering_to_alpha));
    }
}
