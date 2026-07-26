use crate::domain::SourceSpan;

const LEGAL_ABBREVIATIONS: &[&str] = &["ст", "п", "ч", "ред", "г"];
const CLOSING_PUNCTUATION: &[char] = &['»', '”', '"', '\'', ')', ']', '}'];

/// Exact non-empty span of one bounded legal sentence candidate.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct SentenceSpan {
    source_span: SourceSpan,
}

impl SentenceSpan {
    pub fn source_span(self) -> SourceSpan {
        self.source_span
    }

    pub fn start(self) -> usize {
        self.source_span.start()
    }

    pub fn end(self) -> usize {
        self.source_span.end()
    }
}

fn previous_char(text: &str, index: usize) -> Option<char> {
    text[..index].chars().next_back()
}

fn next_char(text: &str, index: usize) -> Option<char> {
    text[index..].chars().next()
}

fn word_before(text: &str, end: usize) -> &str {
    let mut start = end;
    for (index, character) in text[..end].char_indices().rev() {
        if !character.is_alphabetic() {
            break;
        }
        start = index;
    }
    &text[start..end]
}

fn is_decimal_point(text: &str, index: usize) -> bool {
    previous_char(text, index).is_some_and(|value| value.is_ascii_digit())
        && next_char(text, index + 1).is_some_and(|value| value.is_ascii_digit())
}

fn is_legal_abbreviation(text: &str, index: usize) -> bool {
    let normalized = word_before(text, index).to_lowercase();
    LEGAL_ABBREVIATIONS.contains(&normalized.as_str())
}

fn is_numeric_list_marker(text: &str, segment_start: usize, index: usize) -> bool {
    let candidate = text[segment_start..index].trim();
    !candidate.is_empty()
        && candidate.chars().all(|value| value.is_ascii_digit())
        && next_char(text, index + 1).is_some_and(char::is_whitespace)
}

fn trimmed_span(text: &str, start: usize, end: usize) -> Option<SentenceSpan> {
    let candidate = &text[start..end];
    let left = candidate
        .char_indices()
        .find(|(_, character)| !character.is_whitespace())
        .map(|(index, _)| start + index)?;
    let right = candidate
        .char_indices()
        .rev()
        .find(|(_, character)| !character.is_whitespace())
        .map(|(index, character)| start + index + character.len_utf8())?;
    SourceSpan::try_new(left, right)
        .ok()
        .map(|source_span| SentenceSpan { source_span })
}

/// Split text into bounded sentence candidates with exact source byte spans.
///
/// The implementation supports a small explicit legal-abbreviation list,
/// decimal points, leading numeric list markers, and directly adjacent closing
/// quotes/brackets. It does not claim general Russian sentence segmentation.
pub fn split_legal_sentences(text: &str) -> Vec<SentenceSpan> {
    let mut sentences = Vec::new();
    let mut segment_start = 0;
    let mut consumed_until = 0;

    for (index, character) in text.char_indices() {
        if index < consumed_until {
            continue;
        }
        let terminal = match character {
            '!' | '?' => true,
            '.' => {
                !is_decimal_point(text, index)
                    && !is_legal_abbreviation(text, index)
                    && !is_numeric_list_marker(text, segment_start, index)
            }
            _ => false,
        };
        if !terminal {
            continue;
        }

        let first_end = index + character.len_utf8();
        let mut punctuation_end = first_end;
        for (relative, next) in text[first_end..].char_indices() {
            if !matches!(next, '.' | '!' | '?') {
                break;
            }
            punctuation_end = first_end + relative + next.len_utf8();
        }
        let mut end = punctuation_end;
        for (relative, closing) in text[punctuation_end..].char_indices() {
            if !CLOSING_PUNCTUATION.contains(&closing) {
                break;
            }
            end = punctuation_end + relative + closing.len_utf8();
        }
        if let Some(sentence) = trimmed_span(text, segment_start, end) {
            sentences.push(sentence);
        }
        segment_start = end;
        consumed_until = end;
    }

    if let Some(sentence) = trimmed_span(text, segment_start, text.len()) {
        sentences.push(sentence);
    }
    sentences
}
