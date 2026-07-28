use crate::domain::{ParagraphStyle, ParsedBlock, TextSpan};

/// Bounded unsupported-form classes discovered outside existing taxonomies.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum UnknownFormKind {
    UnsupportedTemporalNearMiss,
    UnsupportedDeonticNearMiss,
    UnsupportedHierarchyPrefix,
}

/// One unsupported lexical form occurrence in decoded block text.
///
/// This value carries only a decoded `TextSpan` and a kind. No raw legal text,
/// resolved target, legal interpretation or authority is present.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct UnknownForm {
    kind: UnknownFormKind,
    span: TextSpan,
}

impl UnknownForm {
    pub fn kind(self) -> UnknownFormKind {
        self.kind
    }

    pub fn span(self) -> TextSpan {
        self.span
    }
}

/// Aggregate counts of unsupported forms per kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct UnknownFormCensus {
    temporal_unsupported: usize,
    deontic_unsupported: usize,
    hierarchy_prefix_unsupported: usize,
}

impl UnknownFormCensus {
    pub fn temporal_unsupported(self) -> usize {
        self.temporal_unsupported
    }

    pub fn deontic_unsupported(self) -> usize {
        self.deontic_unsupported
    }

    pub fn hierarchy_prefix_unsupported(self) -> usize {
        self.hierarchy_prefix_unsupported
    }

    fn from_forms(forms: &[UnknownForm]) -> Self {
        let mut c = Self::default();
        for f in forms {
            match f.kind {
                UnknownFormKind::UnsupportedTemporalNearMiss => c.temporal_unsupported += 1,
                UnknownFormKind::UnsupportedDeonticNearMiss => c.deontic_unsupported += 1,
                UnknownFormKind::UnsupportedHierarchyPrefix => c.hierarchy_prefix_unsupported += 1,
            }
        }
        c
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

const UNSUPPORTED_TEMPORAL: &[&str] = &[
    "вступала",
    "вступало",
    "вступавший",
    "вступающего",
    "вступающему",
    "утрачивал",
    "утрачивавшая",
    "утрачивавший",
    "утрачивающего",
    "утрата",
];

const UNSUPPORTED_DEONTIC: &[&str] = &[
    "нельзя",
    "недопустимо",
    "запретить",
    "запрещение",
    "запрещающий",
    "запрет",
];

const UNSUPPORTED_HIERARCHY: &[&str] = &[
    "подпункт",
    "подпункта",
    "подпункту",
    "подпунктом",
    "подпункте",
    "подпункты",
    "подпунктов",
    "подпунктам",
    "подпунктами",
    "подпунктах",
    "часть",
    "части",
    "частью",
    "частей",
    "частям",
    "частями",
    "частях",
    "параграф",
    "параграфа",
    "параграфу",
    "параграфом",
    "параграфе",
    "параграфы",
    "параграфов",
    "абзац",
    "абзаца",
    "абзацу",
    "абзацем",
    "абзаце",
    "абзацы",
    "абзацев",
];

fn classify_unknown(word: &str) -> Option<UnknownFormKind> {
    if UNSUPPORTED_TEMPORAL.contains(&word) {
        Some(UnknownFormKind::UnsupportedTemporalNearMiss)
    } else if UNSUPPORTED_DEONTIC.contains(&word) {
        Some(UnknownFormKind::UnsupportedDeonticNearMiss)
    } else if UNSUPPORTED_HIERARCHY.contains(&word) {
        Some(UnknownFormKind::UnsupportedHierarchyPrefix)
    } else {
        None
    }
}

/// Collect unsupported lexical forms from raw decoded text.
pub fn collect_unknown_forms_from_text(text: &str) -> Vec<UnknownForm> {
    tokens(text)
        .into_iter()
        .filter_map(|t| {
            classify_unknown(&t.normalized).map(|kind| UnknownForm {
                kind,
                span: TextSpan::try_new(t.start, t.end)
                    .expect("alphabetic token has a non-empty decoded span"),
            })
        })
        .collect()
}

/// Build a deterministic unsupported-form census for a parsed block.
///
/// Returns `UnknownFormCensus::default()` for `ProviderComment` blocks.
pub fn census_unknown_forms(block: &ParsedBlock) -> UnknownFormCensus {
    if block.style() == ParagraphStyle::ProviderComment {
        return UnknownFormCensus::default();
    }
    UnknownFormCensus::from_forms(&collect_unknown_forms_from_text(block.text()))
}
