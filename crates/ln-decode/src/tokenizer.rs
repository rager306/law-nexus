/// One alphabetic token in decoded text with normalized lowercase form.
///
/// Shared by morphology, references, temporal and unknown_forms modules.
/// Not part of the public API.
pub(crate) struct WordToken {
    pub(crate) normalized: String,
    pub(crate) start: usize,
    pub(crate) end: usize,
}

/// Tokenize text into alphabetic sequences with UTF-8 byte offsets.
///
/// Non-alphabetic characters act as delimiters. Each token's `normalized`
/// field is the lowercase form of the original text slice.
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
