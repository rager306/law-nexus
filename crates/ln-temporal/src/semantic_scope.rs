//! Source-backed semantic scope claims with deterministic bounded extraction.
//!
//! This module produces candidates only. Claims are not legal facts or NormRules;
//! every claim retains a source-local anchor and extraction is fail-closed at a
//! per-block budget.

use crate::document_context::{AnalysisOverlay, BlockId, SourceBlock, TextSpan, ThisRefEvidence};
use std::collections::BTreeSet;

/// Closed role vocabulary for the semantic scope contour.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum SemanticClaimKind {
    Actor,
    Action,
    Object,
    Polarity,
    Condition,
    Exception,
    TemporalQualifier,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum ClaimError {
    EmptySpan,
    MissingEvidence,
    EvidenceOutsideClaim,
}

/// A source-backed semantic claim. `evidence` is non-empty by construction.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SemanticClaim {
    kind: SemanticClaimKind,
    block: BlockId,
    span: TextSpan,
    evidence: Vec<TextSpan>,
}

impl SemanticClaim {
    pub fn new(
        kind: SemanticClaimKind,
        block: BlockId,
        span: TextSpan,
        evidence: Vec<TextSpan>,
    ) -> Result<Self, ClaimError> {
        if span.start() >= span.end() {
            return Err(ClaimError::EmptySpan);
        }
        if evidence.is_empty() {
            return Err(ClaimError::MissingEvidence);
        }
        if evidence.iter().any(|anchor| {
            anchor.start() >= anchor.end()
                || anchor.start() < span.start()
                || anchor.end() > span.end()
        }) {
            return Err(ClaimError::EvidenceOutsideClaim);
        }
        Ok(Self {
            kind,
            block,
            span,
            evidence,
        })
    }

    pub const fn kind(&self) -> SemanticClaimKind {
        self.kind
    }
    pub const fn block(&self) -> BlockId {
        self.block
    }
    pub const fn span(&self) -> TextSpan {
        self.span
    }
    pub fn evidence(&self) -> &[TextSpan] {
        &self.evidence
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct ClaimLimit {
    pub limit: usize,
    pub attempted: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExtractionOutcome {
    claims: Vec<SemanticClaim>,
    limit: Option<ClaimLimit>,
}

impl ExtractionOutcome {
    pub fn claims(&self) -> &[SemanticClaim] {
        &self.claims
    }
    pub const fn limit(&self) -> Option<ClaimLimit> {
        self.limit
    }
    pub const fn was_limited(&self) -> bool {
        self.limit.is_some()
    }
}

#[derive(Debug, Clone, Copy)]
struct Cue {
    kind: SemanticClaimKind,
    marker: &'static str,
}

const CUES: &[Cue] = &[
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "обязан",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "должен",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "вправе",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "запрещается",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "не вправе",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "shall",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "must not",
    },
    Cue {
        kind: SemanticClaimKind::Polarity,
        marker: "must",
    },
    Cue {
        kind: SemanticClaimKind::Condition,
        marker: "если",
    },
    Cue {
        kind: SemanticClaimKind::Condition,
        marker: "при условии",
    },
    Cue {
        kind: SemanticClaimKind::Condition,
        marker: "provided that",
    },
    Cue {
        kind: SemanticClaimKind::Exception,
        marker: "кроме",
    },
    Cue {
        kind: SemanticClaimKind::Exception,
        marker: "за исключением",
    },
    Cue {
        kind: SemanticClaimKind::Exception,
        marker: "except",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "до",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "после",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "в течение",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "с момента",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "before",
    },
    Cue {
        kind: SemanticClaimKind::TemporalQualifier,
        marker: "after",
    },
];

fn spans_for<'a>(text: &'a str, marker: &'a str) -> impl Iterator<Item = TextSpan> + 'a {
    text.match_indices(marker)
        .filter_map(|(start, found)| TextSpan::new(start, start + found.len()).ok())
}

fn claim(kind: SemanticClaimKind, block: BlockId, span: TextSpan) -> SemanticClaim {
    // `span` comes from source text or a validated ThisRefEvidence, therefore it
    // is also the narrowest explainable evidence anchor.
    SemanticClaim::new(kind, block, span, vec![span]).expect("source span is non-empty")
}

/// Extract explicit semantic cues from one source block.
///
/// Results are sorted and deduplicated. Once `max_claims` is reached, later
/// candidates are refused with a typed limit while already admitted claims stay.
pub fn extract_semantic_claims(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    let mut candidates = BTreeSet::new();

    // Overlay signals are deliberately only source-backed candidates: their
    // frame/continuation identity selects the block, while the block text is
    // the retained anchor (no actor is invented outside source text).
    if overlay
        .frames()
        .iter()
        .any(|frame| frame.block() == block.id())
        || overlay.frames().iter().any(|frame| {
            overlay.continuation_heads(frame.id()).contains(&frame.id())
                && frame.block() == block.id()
        })
    {
        if let Ok(span) = TextSpan::new(0, block.text().len()) {
            if span.start() < span.end() {
                candidates.insert(claim(SemanticClaimKind::Actor, block.id(), span));
            }
        }
    }
    for evidence in this_refs
        .iter()
        .filter(|e| block.text().as_bytes().get(e.span().start()).is_some())
    {
        if evidence.span().end() <= block.text().len() {
            candidates.insert(claim(SemanticClaimKind::Actor, block.id(), evidence.span()));
        }
    }

    for cue in CUES {
        for span in spans_for(block.text(), cue.marker) {
            candidates.insert(claim(cue.kind, block.id(), span));
            // A negated cue is still Polarity; retaining the source span makes
            // the negative modality explicit instead of normalizing it away.
        }
    }

    let attempted = candidates.len();
    let claims: Vec<_> = candidates.into_iter().take(max_claims).collect();
    let limit = (attempted > claims.len()).then_some(ClaimLimit {
        limit: max_claims,
        attempted,
    });
    ExtractionOutcome { claims, limit }
}

/// Short alias for callers that already operate on a source block.
pub fn extract(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    extract_semantic_claims(block, overlay, this_refs, max_claims)
}
