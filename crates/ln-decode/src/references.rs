use crate::domain::{ParagraphStyle, ParsedBlock, TextSpan};
use crate::tokenizer::tokenize;

/// Bounded lexical reference classes. They do not identify a referenced target.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ReferenceMentionKind {
    Article,
    Point,
}

/// A lexical structural reference mention in decoded block text.
///
/// The number is syntax-checked but not resolved against a document hierarchy.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReferenceMention {
    kind: ReferenceMentionKind,
    number: String,
    text_span: TextSpan,
    term_span: TextSpan,
    number_span: TextSpan,
}

impl ReferenceMention {
    pub fn kind(&self) -> ReferenceMentionKind {
        self.kind
    }

    pub fn number(&self) -> &str {
        &self.number
    }

    pub fn text_span(&self) -> TextSpan {
        self.text_span
    }

    pub fn term_span(&self) -> TextSpan {
        self.term_span
    }

    pub fn number_span(&self) -> TextSpan {
        self.number_span
    }
}

fn classify_term(term: &str) -> Option<ReferenceMentionKind> {
    match term {
        "статья" | "статьи" | "статье" | "статью" | "статей" | "статьёй" | "статьей"
        | "статьями" | "статьях" => Some(ReferenceMentionKind::Article),
        "пункт" | "пункта" | "пункту" | "пунктом" | "пункте" | "пункты" | "пунктов" | "пунктам"
        | "пунктами" | "пунктах" => Some(ReferenceMentionKind::Point),
        _ => None,
    }
}

fn number_after(text: &str, term_end: usize) -> Option<(usize, usize)> {
    let suffix = &text[term_end..];
    let mut number_start = term_end;
    let mut saw_horizontal_whitespace = false;
    for character in suffix.chars() {
        if character == ' ' || character == '\t' {
            saw_horizontal_whitespace = true;
            number_start += character.len_utf8();
        } else {
            break;
        }
    }
    if !saw_horizontal_whitespace {
        return None;
    }

    let bytes = text.as_bytes();
    if !bytes.get(number_start).is_some_and(u8::is_ascii_digit) {
        return None;
    }
    let mut end = number_start;
    while bytes.get(end).is_some_and(u8::is_ascii_digit) {
        end += 1;
    }
    loop {
        if bytes.get(end) != Some(&b'.') {
            break;
        }
        if !bytes.get(end + 1).is_some_and(u8::is_ascii_digit) {
            break;
        }
        end += 1;
        while bytes.get(end).is_some_and(u8::is_ascii_digit) {
            end += 1;
        }
    }

    let remainder = &text[end..];
    if remainder.starts_with("..")
        || remainder
            .strip_prefix('.')
            .and_then(|rest| rest.chars().next())
            .is_some_and(char::is_alphabetic)
        || remainder
            .chars()
            .next()
            .is_some_and(|character| character.is_alphabetic() || character == '_')
    {
        return None;
    }
    Some((number_start, end))
}

/// Extract bounded internal reference mentions from provider-neutral decoded text.
///
/// Returned values are lexical candidates only. They contain no resolved target,
/// relation identity, citation authority or source-coordinate translation.
pub fn extract_reference_mentions(block: &ParsedBlock) -> Vec<ReferenceMention> {
    if block.style() == ParagraphStyle::ProviderComment {
        return Vec::new();
    }

    tokenize(block.text())
        .into_iter()
        .filter_map(|term| {
            let kind = classify_term(&term.normalized)?;
            let (number_start, number_end) = number_after(block.text(), term.end)?;
            Some(ReferenceMention {
                kind,
                number: block.text()[number_start..number_end].to_owned(),
                text_span: TextSpan::try_new(term.start, number_end)
                    .expect("term and following number form a non-empty decoded span"),
                term_span: TextSpan::try_new(term.start, term.end)
                    .expect("alphabetic term has a non-empty decoded span"),
                number_span: TextSpan::try_new(number_start, number_end)
                    .expect("validated number has a non-empty decoded span"),
            })
        })
        .collect()
}
