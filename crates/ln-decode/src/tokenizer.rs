/// One alphabetic token in decoded text with normalized lowercase form.
///
/// Shared by morphology, references, temporal and unknown_forms modules.
/// Not part of the public API.
///
/// Two producers exist and are not aliases (ADR-0028 dual tokenizer):
/// [`tokenize`] splits on non-letters (`ст. 5` → stem `ст`);
/// [`words_from_covering`] projects alphabetic [`crate::lexer::TokenKind::Word`]
/// tokens from the covering lexer (`ст. 5` → no Word; `статьи 5` → `статьи`).
pub(crate) struct WordToken {
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
pub(crate) fn tokenize(text: &str) -> Vec<WordToken> {
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
        result.push(WordToken {
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
pub(crate) fn words_from_covering(text: &str) -> Vec<WordToken> {
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
            Some(WordToken {
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
}
