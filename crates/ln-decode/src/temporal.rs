use crate::domain::{ParagraphStyle, ParsedBlock, TextSpan};

/// Bounded lexical temporal phrase classes. They do not assign a legal clock.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TemporalPhraseKind {
    EntersIntoForce,
    LosesForce,
}

/// One lexical temporal phrase occurrence in decoded block text.
///
/// This value contains no date, clock, applicability or edition state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct TemporalPhrase {
    kind: TemporalPhraseKind,
    text_span: TextSpan,
}

impl TemporalPhrase {
    pub fn kind(self) -> TemporalPhraseKind {
        self.kind
    }

    pub fn text_span(self) -> TextSpan {
        self.text_span
    }
}

#[derive(Debug)]
struct WordToken {
    normalized: String,
    start: usize,
    end: usize,
}

fn words(text: &str) -> Vec<WordToken> {
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

fn is_horizontal_gap(text: &str, left: &WordToken, right: &WordToken) -> bool {
    let gap = &text[left.end..right.start];
    !gap.is_empty()
        && gap
            .chars()
            .all(|character| character == ' ' || character == '\t')
}

fn entry_verb(word: &str) -> bool {
    matches!(word, "вступает" | "вступил" | "вступают")
}

fn loss_verb(word: &str) -> bool {
    matches!(word, "утрачивает" | "утратил" | "утрачивают")
}

/// Extract bounded lexical temporal phrases from provider-neutral decoded text.
///
/// Returned values do not establish dates, five-clock values, legal
/// applicability, effective state or edition changes.
pub fn extract_temporal_phrases(block: &ParsedBlock) -> Vec<TemporalPhrase> {
    if block.style() == ParagraphStyle::ProviderComment {
        return Vec::new();
    }

    let text = block.text();
    let words = words(text);
    let mut phrases = Vec::new();
    for index in 0..words.len() {
        let first = &words[index];
        if entry_verb(&first.normalized) {
            let Some(second) = words.get(index + 1) else {
                continue;
            };
            let Some(third) = words.get(index + 2) else {
                continue;
            };
            if second.normalized == "в"
                && third.normalized == "силу"
                && is_horizontal_gap(text, first, second)
                && is_horizontal_gap(text, second, third)
            {
                phrases.push(TemporalPhrase {
                    kind: TemporalPhraseKind::EntersIntoForce,
                    text_span: TextSpan::try_new(first.start, third.end)
                        .expect("three-word phrase has a non-empty decoded span"),
                });
            }
        } else if loss_verb(&first.normalized) {
            let Some(second) = words.get(index + 1) else {
                continue;
            };
            if second.normalized == "силу" && is_horizontal_gap(text, first, second) {
                phrases.push(TemporalPhrase {
                    kind: TemporalPhraseKind::LosesForce,
                    text_span: TextSpan::try_new(first.start, second.end)
                        .expect("two-word phrase has a non-empty decoded span"),
                });
            }
        }
    }
    phrases
}
