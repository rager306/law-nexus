//! Immutable, fragment-local local-grammar frames (D384, S03).
//!
//! The YAML contract is design data only (D216/D098); these Rust types are
//! intentionally defined here rather than generated from it. Frames are
//! structural alternatives above the covering lexer. They do not mint
//! identities, join blocks, authorize inheritance, or expand arithmetic
//! designation ranges. A `TextSpan` is the sole anchor coordinate and must be
//! supplied from one decoded fragment on character boundaries.

use crate::domain::TextSpan;
use crate::morphology::LegalMarkerKind;

/// The only two frame families admitted by D384.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameKind {
    ActRequisites,
    StructuralDesignation,
}

/// Provenance of an inherited or explicit member field. The authorized
/// current-document variant is reserved for the D381 sidecar and cannot be
/// constructed by S03 frame constructors.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DerivationSource {
    ExplicitMember,
    SameSeriesHead,
    PriorFrame,
    AuthorizedCurrentDocumentRequisites,
}

/// Closed enumeration FSM from D384. Terminal states never transition again.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnumerationState {
    NotEvaluated,
    Candidate,
    Compatible,
    Conflicting,
    Incomplete,
    Rejected,
}

/// An event which can advance the local enumeration FSM.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EnumerationTransition {
    LocalRolesAndValuesCaptured,
    AuthorizedFieldClaimsAgree,
    ExplicitOrInheritedClaimsDisagree,
    RequiredOwnerOrValueMissing,
    GrammarOrBoundContractRefused,
}

impl EnumerationState {
    /// Apply exactly one D384 transition; invalid or terminal transitions are
    /// refused without changing the state.
    pub const fn transition(self, event: EnumerationTransition) -> Option<Self> {
        match (self, event) {
            (Self::NotEvaluated, EnumerationTransition::LocalRolesAndValuesCaptured) => {
                Some(Self::Candidate)
            }
            (Self::Candidate, EnumerationTransition::AuthorizedFieldClaimsAgree) => {
                Some(Self::Compatible)
            }
            (Self::Candidate, EnumerationTransition::ExplicitOrInheritedClaimsDisagree) => {
                Some(Self::Conflicting)
            }
            (Self::Candidate, EnumerationTransition::RequiredOwnerOrValueMissing) => {
                Some(Self::Incomplete)
            }
            (Self::Candidate, EnumerationTransition::GrammarOrBoundContractRefused) => {
                Some(Self::Rejected)
            }
            _ => None,
        }
    }

    pub const fn is_terminal(self) -> bool {
        matches!(
            self,
            Self::Compatible | Self::Conflicting | Self::Incomplete | Self::Rejected
        )
    }
}

/// Lifecycle status of a proposed frame, separate from enumeration state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameStatus {
    Proposed,
    Ambiguous,
    Rejected,
}

/// Closed diagnostics; competing frames are retained rather than selected by
/// proximity or source order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FrameDiagnostic {
    FrameMemberLimitReached,
    ConflictingFramesRetained,
    OwnerUnresolved,
    GrammarContractRefused,
}

impl FrameDiagnostic {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::FrameMemberLimitReached => "frame_member_limit_reached",
            Self::ConflictingFramesRetained => "conflicting_frames_retained",
            Self::OwnerUnresolved => "owner_unresolved",
            Self::GrammarContractRefused => "grammar_contract_refused",
        }
    }
}

/// One structural member, carrying its literal value and derivation evidence.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameMember {
    pub value: String,
    pub value_span: TextSpan,
    pub derivation: DerivationSource,
    pub evidence: Vec<TextSpan>,
    pub state: EnumerationState,
}

impl FrameMember {
    pub fn new(
        value: String,
        value_span: TextSpan,
        derivation: DerivationSource,
        evidence: Vec<TextSpan>,
        state: EnumerationState,
    ) -> Self {
        Self {
            value,
            value_span,
            derivation,
            evidence,
            state,
        }
    }
}

/// One step in a fragment-local owner path. Every step has independent proof
/// evidence; no step is an identity or a document-wide context reference.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnerPathStep {
    pub value: String,
    pub span: TextSpan,
    pub evidence: Vec<TextSpan>,
}

impl OwnerPathStep {
    pub fn new(value: String, span: TextSpan, evidence: Vec<TextSpan>) -> Self {
        Self {
            value,
            span,
            evidence,
        }
    }
}

/// Shared shape for the two D384 frame families.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoordinatingFrame {
    pub frame_kind: FrameKind,
    pub local_anchor: TextSpan,
    pub head_roles: Vec<String>,
    pub members: Vec<FrameMember>,
    pub separators: Vec<TextSpan>,
    pub continuation: bool,
    pub alternatives: Vec<FrameMember>,
    pub bounds: FrameBounds,
    pub status: FrameStatus,
    pub diagnostic: Option<FrameDiagnostic>,
}

/// Explicit bound metadata carried by a frame, without pretending proposed
/// values are final corpus limits.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct FrameBounds {
    pub max_members: usize,
    pub max_expanded_candidates: usize,
}

/// Structural designation frame with endpoint-pair policy. Expansion itself
/// belongs to the later resolve side and is deliberately absent here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralDesignationFrame {
    pub local_anchor: TextSpan,
    pub marker: LegalMarkerKind,
    pub values: Vec<FrameMember>,
    pub owner_path: Vec<OwnerPathStep>,
    pub expansion_policy: ExpansionPolicy,
    pub status: FrameStatus,
    pub diagnostic: Option<FrameDiagnostic>,
}

/// The sole S03 expansion declaration; it is not an arithmetic enumerator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ExpansionPolicy {
    EndpointPair,
}

/// [proposed] G06 bound, with at least 2x headroom over the bounded smoke
/// baseline; T04 may pin a reviewed final value.
pub const PROPOSED_MAX_FRAME_MEMBERS: usize = 64;
/// [proposed] G07 resolve-side candidate bound. S03 only declares it.
pub const PROPOSED_MAX_EXPANDED_CANDIDATES: usize = 64;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FrameLimitOutcome {
    Accepted,
    LimitReached,
}

impl FrameLimitOutcome {
    pub const fn is_accepted(self) -> bool {
        matches!(self, Self::Accepted)
    }
    pub const fn diagnostic(self) -> Option<FrameDiagnostic> {
        match self {
            Self::Accepted => None,
            Self::LimitReached => Some(FrameDiagnostic::FrameMemberLimitReached),
        }
    }
}

/// Stateless G06 admission decision. Existing members are never truncated.
pub const fn on_frame_limit(accepted_members: usize) -> FrameLimitOutcome {
    if accepted_members < PROPOSED_MAX_FRAME_MEMBERS {
        FrameLimitOutcome::Accepted
    } else {
        FrameLimitOutcome::LimitReached
    }
}

/// Immutable result of attempting to append a member to a coordinating frame.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrameAdmission {
    pub frame: CoordinatingFrame,
    pub outcome: FrameLimitOutcome,
}

impl CoordinatingFrame {
    /// Constructs a proposed frame. S03 constructors cannot create the
    /// authorized-current-document derivation; callers receive that source
    /// only from a future D381 sidecar integration.
    pub fn new(
        frame_kind: FrameKind,
        local_anchor: TextSpan,
        head_roles: Vec<String>,
        members: Vec<FrameMember>,
        separators: Vec<TextSpan>,
        continuation: bool,
        alternatives: Vec<FrameMember>,
    ) -> Self {
        Self {
            frame_kind,
            local_anchor,
            head_roles,
            members,
            separators,
            continuation,
            alternatives,
            bounds: FrameBounds {
                max_members: PROPOSED_MAX_FRAME_MEMBERS,
                max_expanded_candidates: PROPOSED_MAX_EXPANDED_CANDIDATES,
            },
            status: FrameStatus::Proposed,
            diagnostic: None,
        }
    }

    /// Returns a new value; the original frame and its members are untouched.
    pub fn admit_member(&self, member: FrameMember) -> FrameAdmission {
        match on_frame_limit(self.members.len()) {
            FrameLimitOutcome::Accepted => {
                let mut next = self.clone();
                next.members.push(member);
                FrameAdmission {
                    frame: next,
                    outcome: FrameLimitOutcome::Accepted,
                }
            }
            FrameLimitOutcome::LimitReached => {
                let mut rejected = self.clone();
                rejected.status = FrameStatus::Rejected;
                rejected.diagnostic = FrameLimitOutcome::LimitReached.diagnostic();
                FrameAdmission {
                    frame: rejected,
                    outcome: FrameLimitOutcome::LimitReached,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn span(start: usize) -> TextSpan {
        TextSpan::try_new(start, start + 1).unwrap()
    }
    fn member(start: usize) -> FrameMember {
        FrameMember::new(
            "x".into(),
            span(start),
            DerivationSource::ExplicitMember,
            vec![span(start)],
            EnumerationState::Candidate,
        )
    }

    #[test]
    fn vocabulary_is_closed_to_exactly_two_frame_kinds() {
        assert_eq!(FrameKind::ActRequisites as u8, 0);
        assert_eq!(FrameKind::StructuralDesignation as u8, 1);
    }

    #[test]
    fn fsm_has_only_contract_transitions_and_terminal_states() {
        assert_eq!(
            EnumerationState::NotEvaluated
                .transition(EnumerationTransition::LocalRolesAndValuesCaptured),
            Some(EnumerationState::Candidate)
        );
        assert_eq!(
            EnumerationState::Candidate
                .transition(EnumerationTransition::GrammarOrBoundContractRefused),
            Some(EnumerationState::Rejected)
        );
        assert!(EnumerationState::Rejected.is_terminal());
        assert_eq!(
            EnumerationState::Rejected
                .transition(EnumerationTransition::AuthorizedFieldClaimsAgree),
            None
        );
    }

    #[test]
    fn frame_limit_rejects_without_losing_existing_members() {
        let mut frame = CoordinatingFrame::new(
            FrameKind::ActRequisites,
            span(0),
            vec![],
            vec![],
            vec![],
            false,
            vec![],
        );
        for index in 0..PROPOSED_MAX_FRAME_MEMBERS {
            frame = frame.admit_member(member(index + 1)).frame;
        }
        let result = frame.admit_member(member(999));
        assert_eq!(result.outcome, FrameLimitOutcome::LimitReached);
        assert_eq!(result.frame.status, FrameStatus::Rejected);
        assert_eq!(
            result.frame.diagnostic,
            Some(FrameDiagnostic::FrameMemberLimitReached)
        );
        assert_eq!(result.frame.members.len(), PROPOSED_MAX_FRAME_MEMBERS);
    }

    #[test]
    fn structural_designation_declares_endpoint_pair_without_expansion() {
        let frame = StructuralDesignationFrame {
            local_anchor: span(0),
            marker: LegalMarkerKind::Statya,
            values: vec![member(1), member(3)],
            owner_path: vec![],
            expansion_policy: ExpansionPolicy::EndpointPair,
            status: FrameStatus::Proposed,
            diagnostic: None,
        };
        assert_eq!(frame.values.len(), 2);
        assert_eq!(frame.expansion_policy, ExpansionPolicy::EndpointPair);
    }
}
