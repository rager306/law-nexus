use crate::domain::SourceSpan;

/// Bounded lexical marker classes. They are not legal-effect conclusions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LegalMarkerKind {
    Statya,
    Punkt,
    Obyazan,
    Vprave,
    Zapret,
}

/// One exact lexical marker occurrence in source text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MorphologyMatch {
    kind: LegalMarkerKind,
    source_span: SourceSpan,
    negated: bool,
}

impl MorphologyMatch {
    pub fn kind(self) -> LegalMarkerKind {
        self.kind
    }

    pub fn source_span(self) -> SourceSpan {
        self.source_span
    }

    pub fn start(self) -> usize {
        self.source_span.start()
    }

    pub fn end(self) -> usize {
        self.source_span.end()
    }

    pub fn negated(self) -> bool {
        self.negated
    }
}

#[derive(Debug)]
struct Token {
    normalized: String,
    start: usize,
    end: usize,
}

fn tokens(text: &str) -> Vec<Token> {
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
        result.push(Token {
            normalized: text[start..end].to_lowercase(),
            start,
            end,
        });
    }
    result
}

fn classify(word: &str) -> Option<LegalMarkerKind> {
    match word {
        "статья" | "статьи" | "статье" | "статью" | "статьёй" | "статьей" | "статьями"
        | "статьях" => Some(LegalMarkerKind::Statya),
        "пункт" | "пункта" | "пункту" | "пунктом" | "пункте" | "пункты" | "пунктов" | "пунктам"
        | "пунктами" | "пунктах" => Some(LegalMarkerKind::Punkt),
        "обязан" | "обязана" | "обязано" | "обязаны" => {
            Some(LegalMarkerKind::Obyazan)
        }
        "вправе" => Some(LegalMarkerKind::Vprave),
        "запрещается" | "запрещен" | "запрещён" | "запрещена" | "запрещено" | "запрещены" => {
            Some(LegalMarkerKind::Zapret)
        }
        _ => None,
    }
}

/// Find bounded Russian legal marker forms in deterministic source order.
///
/// `negated` means only that the immediately preceding whitespace-separated
/// token is `не`. It does not assign modality or legal effect.
pub fn find_legal_markers(text: &str) -> Vec<MorphologyMatch> {
    let tokens = tokens(text);
    let mut matches = Vec::new();
    for (index, token) in tokens.iter().enumerate() {
        let Some(kind) = classify(&token.normalized) else {
            continue;
        };
        let negated = index.checked_sub(1).is_some_and(|previous_index| {
            let previous = &tokens[previous_index];
            previous.normalized == "не"
                && text[previous.end..token.start]
                    .chars()
                    .all(char::is_whitespace)
        });
        let source_span = SourceSpan::try_new(token.start, token.end)
            .expect("alphabetic token always has a non-empty source span");
        matches.push(MorphologyMatch {
            kind,
            source_span,
            negated,
        });
    }
    matches
}
