use crate::{
    domain::{ParagraphStyle, ParsedBlock, TextSpan},
    morphology::{find_legal_markers, LegalMarkerKind},
};

/// Bounded deontic lexeme classes. They are not legal modality conclusions.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DeonticLexemeKind {
    Obligation,
    Permission,
    Prohibition,
}

/// One lexical deontic marker in decoded block text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DeonticLexeme {
    kind: DeonticLexemeKind,
    text_span: TextSpan,
    negated: bool,
}

impl DeonticLexeme {
    pub fn kind(self) -> DeonticLexemeKind {
        self.kind
    }

    pub fn text_span(self) -> TextSpan {
        self.text_span
    }

    /// Whether the morphology primitive found an immediately preceding `не`.
    ///
    /// This does not invert modality or assign legal effect.
    pub fn negated(self) -> bool {
        self.negated
    }
}

/// Project existing bounded morphology markers into deontic lexeme candidates.
///
/// The output contains no actor/action scope, `NormStatement`, confidence,
/// authority, source-coordinate mapping or legal-effect conclusion.
pub fn extract_deontic_lexemes(block: &ParsedBlock) -> Vec<DeonticLexeme> {
    if block.style() == ParagraphStyle::ProviderComment {
        return Vec::new();
    }

    find_legal_markers(block.text())
        .into_iter()
        .filter_map(|marker| {
            let kind = match marker.kind() {
                LegalMarkerKind::Obyazan => DeonticLexemeKind::Obligation,
                LegalMarkerKind::Vprave => DeonticLexemeKind::Permission,
                LegalMarkerKind::Zapret => DeonticLexemeKind::Prohibition,
                LegalMarkerKind::Statya | LegalMarkerKind::Punkt => return None,
            };
            Some(DeonticLexeme {
                kind,
                text_span: marker.text_span(),
                negated: marker.negated(),
            })
        })
        .collect()
}
