//! Source-backed semantic scope claims with deterministic bounded extraction.
//!
//! This module produces candidates only. Claims are not legal facts or NormRules;
//! every claim retains a source-local anchor and extraction is fail-closed at a
//! per-block budget.

use crate::document_context::{
    AnalysisOverlay, BlockId, SourceBlock, Terminal, TextSpan, ThisRefEvidence,
};
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
    SemanticClaim::new(kind, block, span, vec![span]).expect("source span is non-empty")
}

/// Extract explicit semantic cues from one source block.
pub fn extract_semantic_claims(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    let mut candidates = BTreeSet::new();
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

pub fn extract(
    block: &SourceBlock,
    overlay: &AnalysisOverlay,
    this_refs: &[ThisRefEvidence],
    max_claims: usize,
) -> ExtractionOutcome {
    extract_semantic_claims(block, overlay, this_refs, max_claims)
}

/// The four singular slots needed before a candidate can be considered complete.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum CandidateSlot {
    Actor,
    Action,
    Object,
    Polarity,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormRuleCandidate {
    candidate_id: String,
    actor: SemanticClaim,
    action: SemanticClaim,
    object: SemanticClaim,
    polarity: SemanticClaim,
    conditions: Vec<SemanticClaim>,
    exceptions: Vec<SemanticClaim>,
    temporal_qualifier: Vec<SemanticClaim>,
    anchors: Vec<TextSpan>,
}

impl NormRuleCandidate {
    pub fn candidate_id(&self) -> &str {
        &self.candidate_id
    }
    pub fn actor(&self) -> &SemanticClaim {
        &self.actor
    }
    pub fn action(&self) -> &SemanticClaim {
        &self.action
    }
    pub fn object(&self) -> &SemanticClaim {
        &self.object
    }
    pub fn polarity(&self) -> &SemanticClaim {
        &self.polarity
    }
    pub fn conditions(&self) -> &[SemanticClaim] {
        &self.conditions
    }
    pub fn exceptions(&self) -> &[SemanticClaim] {
        &self.exceptions
    }
    pub fn temporal_qualifier(&self) -> &[SemanticClaim] {
        &self.temporal_qualifier
    }
    pub fn anchors(&self) -> &[TextSpan] {
        &self.anchors
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum AbstentionReason {
    MissingActor,
    MissingAction,
    MissingObject,
    MissingPolarity,
    ConflictingSlots,
    ContextTerminal(Terminal),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AbstentionRecord {
    reasons: Vec<AbstentionReason>,
    missing: Vec<CandidateSlot>,
    claims: Vec<SemanticClaim>,
    anchors: Vec<TextSpan>,
}
impl AbstentionRecord {
    pub fn reasons(&self) -> &[AbstentionReason] {
        &self.reasons
    }
    pub fn missing(&self) -> &[CandidateSlot] {
        &self.missing
    }
    pub fn claims(&self) -> &[SemanticClaim] {
        &self.claims
    }
    pub fn anchors(&self) -> &[TextSpan] {
        &self.anchors
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectionOutcome {
    Complete(Box<NormRuleCandidate>),
    Abstained(AbstentionRecord),
}

fn id_for(claims: &[SemanticClaim]) -> String {
    claims
        .iter()
        .map(|c| {
            format!(
                "{}:{}-{}",
                c.block().get(),
                c.span().start(),
                c.span().end()
            )
        })
        .collect::<Vec<_>>()
        .join("|")
}

/// Projects only a resolved, non-conflicting, fully slotted scope. No default
/// actor and no condition dropping are possible because required fields are owned.
pub fn project_norm_rule(
    claims: impl IntoIterator<Item = SemanticClaim>,
    terminal: Terminal,
) -> ProjectionOutcome {
    let mut claims: Vec<_> = claims.into_iter().collect();
    claims.sort();
    let anchors = claims
        .iter()
        .flat_map(|c| c.evidence().iter().copied())
        .collect();
    if terminal != Terminal::Resolved {
        return ProjectionOutcome::Abstained(AbstentionRecord {
            reasons: vec![AbstentionReason::ContextTerminal(terminal)],
            missing: Vec::new(),
            claims,
            anchors,
        });
    }
    let mut slots = [Vec::new(), Vec::new(), Vec::new(), Vec::new()];
    let mut conditions = Vec::new();
    let mut exceptions = Vec::new();
    let mut temporal = Vec::new();
    for claim in &claims {
        match claim.kind() {
            SemanticClaimKind::Actor => slots[0].push(claim.clone()),
            SemanticClaimKind::Action => slots[1].push(claim.clone()),
            SemanticClaimKind::Object => slots[2].push(claim.clone()),
            SemanticClaimKind::Polarity => slots[3].push(claim.clone()),
            SemanticClaimKind::Condition => conditions.push(claim.clone()),
            SemanticClaimKind::Exception => exceptions.push(claim.clone()),
            SemanticClaimKind::TemporalQualifier => temporal.push(claim.clone()),
        }
    }
    let missing = [
        CandidateSlot::Actor,
        CandidateSlot::Action,
        CandidateSlot::Object,
        CandidateSlot::Polarity,
    ]
    .into_iter()
    .enumerate()
    .filter_map(|(i, slot)| slots[i].is_empty().then_some(slot))
    .collect::<Vec<_>>();
    let conflicting = slots.iter().any(|slot| slot.len() > 1);
    let mut reasons = missing
        .iter()
        .map(|slot| match slot {
            CandidateSlot::Actor => AbstentionReason::MissingActor,
            CandidateSlot::Action => AbstentionReason::MissingAction,
            CandidateSlot::Object => AbstentionReason::MissingObject,
            CandidateSlot::Polarity => AbstentionReason::MissingPolarity,
        })
        .collect::<Vec<_>>();
    if conflicting {
        reasons.push(AbstentionReason::ConflictingSlots);
    }
    if !reasons.is_empty() {
        return ProjectionOutcome::Abstained(AbstentionRecord {
            reasons,
            missing,
            claims,
            anchors,
        });
    }
    let candidate_id = id_for(&claims);
    ProjectionOutcome::Complete(Box::new(NormRuleCandidate {
        candidate_id,
        actor: slots[0].remove(0),
        action: slots[1].remove(0),
        object: slots[2].remove(0),
        polarity: slots[3].remove(0),
        conditions,
        exceptions,
        temporal_qualifier: temporal,
        anchors,
    }))
}
