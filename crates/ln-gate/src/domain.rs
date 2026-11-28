use std::error::Error;
use std::fmt;

use ln_fsm::graph::{EdgeSpec, ForbiddenEdge, GraphSpec};
use ln_fsm::{DeterministicFsm, StepError};

const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}

impl fmt::Display for IdError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid {}: {}", self.kind, self.reason)
    }
}

impl Error for IdError {}

fn parse_id(kind: &'static str, value: &str, max_len: usize) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > max_len {
        return Err(IdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.'))
    {
        return Err(IdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! id_type {
    ($name:ident, $kind:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);
        impl $name {
            pub fn parse(value: &str) -> Result<Self, IdError> {
                parse_id($kind, value, MAX_ID_LEN).map(Self)
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(CandidateId, "candidate id");
id_type!(EvidenceRef, "evidence ref");
id_type!(GateVersion, "gate version");
id_type!(InputChainDigest, "input chain digest");

pub const C10_GATE_VERSION: &str = "c10:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LifecycleType {
    ExtractedCandidate,
    VerifiedAssertion,
}

impl LifecycleType {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::ExtractedCandidate => "extracted-candidate",
            Self::VerifiedAssertion => "verified-assertion",
        }
    }
}

/// C10 gate lifecycle transition event checked by [`GateLifecycleFsm`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GateLifecycleEvent {
    PromoteToVerified {
        in_place: bool,
        has_evidence: bool,
        confidence: u8,
    },
    DemoteToExtracted,
}

impl GateLifecycleEvent {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::PromoteToVerified { .. } => "promote-to-verified",
            Self::DemoteToExtracted => "demote-to-extracted",
        }
    }
}

/// Typed FSM refusal emitted by [`GateLifecycleFsm`].
///
/// Distinct from [`GateReason`] so `EvidenceChainSatisfied` is unrepresentable
/// as an FSM rejection and non-in-place terminal/demotion refusals never
/// misreport `"in-place-mutation"`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GateTransitionRefusal {
    InPlaceMutation,
    ConfidenceOnly,
    MissingEvidenceChain,
    TerminalLifecycleImmutable,
    InvalidLifecycleTransition,
}

impl GateTransitionRefusal {
    pub const fn to_gate_reason(self) -> GateReason {
        match self {
            Self::InPlaceMutation => GateReason::InPlaceMutation,
            Self::ConfidenceOnly => GateReason::ConfidenceOnly,
            Self::MissingEvidenceChain => GateReason::MissingEvidenceChain,
            Self::TerminalLifecycleImmutable => GateReason::TerminalLifecycleImmutable,
            Self::InvalidLifecycleTransition => GateReason::InvalidLifecycleTransition,
        }
    }
}

/// Deterministic C10 evidence-kernel gate FSM (`HC-06`).
///
/// Enforces:
/// - `VerifiedAssertion` is terminal/absorbing (immutable outcome never demotes
///   and never re-mints);
/// - `in_place == true` is always refused (`GateTransitionRefusal::InPlaceMutation`);
/// - empty evidence chain is always refused (`GateTransitionRefusal::ConfidenceOnly`
///   when `confidence >= 90`, else `GateTransitionRefusal::MissingEvidenceChain`).
#[derive(Debug, Clone, Copy, Default)]
pub struct GateLifecycleFsm;

impl DeterministicFsm for GateLifecycleFsm {
    type State = LifecycleType;
    type Event = GateLifecycleEvent;
    type RejectionReason = GateTransitionRefusal;

    fn policy_version(&self) -> &'static str {
        C10_GATE_VERSION
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(state, LifecycleType::VerifiedAssertion)
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        event: &Self::Event,
    ) -> Self::RejectionReason {
        match event {
            GateLifecycleEvent::PromoteToVerified { in_place: true, .. } => {
                GateTransitionRefusal::InPlaceMutation
            }
            _ => GateTransitionRefusal::TerminalLifecycleImmutable,
        }
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, *event) {
            (
                LifecycleType::ExtractedCandidate,
                GateLifecycleEvent::PromoteToVerified {
                    in_place,
                    has_evidence,
                    confidence,
                },
            ) => {
                if in_place {
                    return Err(StepError::GuardRejected(
                        GateTransitionRefusal::InPlaceMutation,
                    ));
                }
                if !has_evidence {
                    let reason = if confidence >= 90 {
                        GateTransitionRefusal::ConfidenceOnly
                    } else {
                        GateTransitionRefusal::MissingEvidenceChain
                    };
                    return Err(StepError::GuardRejected(reason));
                }
                Ok(LifecycleType::VerifiedAssertion)
            }
            (LifecycleType::ExtractedCandidate, GateLifecycleEvent::DemoteToExtracted) => Err(
                StepError::InvalidTransition(GateTransitionRefusal::InvalidLifecycleTransition),
            ),
            (LifecycleType::VerifiedAssertion, _) => Err(StepError::InvalidTransition(
                GateTransitionRefusal::TerminalLifecycleImmutable,
            )),
        }
    }
}

pub const GATE_LIFECYCLE_GRAPH_SPEC: GraphSpec = GraphSpec {
    name: "ln-gate::GateLifecycleFsm",
    initial: "extracted-candidate",
    states: &["extracted-candidate", "verified-assertion"],
    terminals: &["verified-assertion"],
    transitions: &[EdgeSpec {
        from: "extracted-candidate",
        event: "promote-to-verified",
        to: "verified-assertion",
    }],
    forbidden_direct_edges: &[ForbiddenEdge {
        from: "verified-assertion",
        to: "extracted-candidate",
        rationale: "VerifiedAssertion is an immutable C10 outcome and must never demote",
    }],
    allow_guarded_branching: false,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateOutcome {
    InsufficientEvidence,
    InvalidTransition,
    AcceptedNewOutcome,
}

impl GateOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::InsufficientEvidence => "insufficient-evidence",
            Self::InvalidTransition => "invalid-transition",
            Self::AcceptedNewOutcome => "accepted-new-outcome",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateReason {
    ConfidenceOnly,
    InPlaceMutation,
    MissingEvidenceChain,
    EvidenceChainSatisfied,
    TerminalLifecycleImmutable,
    InvalidLifecycleTransition,
}

impl GateReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ConfidenceOnly => "confidence-only",
            Self::InPlaceMutation => "in-place-mutation",
            Self::MissingEvidenceChain => "missing-evidence-chain",
            Self::EvidenceChainSatisfied => "evidence-chain-satisfied",
            Self::TerminalLifecycleImmutable => "terminal-lifecycle-immutable",
            Self::InvalidLifecycleTransition => "invalid-lifecycle-transition",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateRecord {
    pub candidate_id: CandidateId,
    pub lifecycle_type: LifecycleType,
    pub evidence_refs: Vec<EvidenceRef>,
    pub predecessor: Option<CandidateId>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateRequest {
    pub candidate_id: CandidateId,
    pub requested_type: LifecycleType,
    pub confidence: u8,
    pub evidence_refs: Vec<EvidenceRef>,
    /// When true, caller asks to mutate the same identity in place.
    pub in_place: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateResult {
    pub gate_version: GateVersion,
    pub outcome: GateOutcome,
    pub reason: GateReason,
    pub original_id: CandidateId,
    pub original_type: LifecycleType,
    pub resulting_id: CandidateId,
    pub resulting_type: LifecycleType,
    pub predecessor: Option<CandidateId>,
    pub input_chain_digest: InputChainDigest,
    pub confidence_used_as_authority: bool,
}

pub fn digest_chain(candidate_id: &CandidateId, evidence_refs: &[EvidenceRef]) -> InputChainDigest {
    let mut material = candidate_id.as_str().to_owned();
    for item in evidence_refs {
        material.push('|');
        material.push_str(item.as_str());
    }
    // FNV-1a diagnostic digest only; not cryptographic authority.
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in material.as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    InputChainDigest::parse(&format!("fnv1a64:{hash:016x}")).expect("static digest")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_candidate_id() {
        assert!(CandidateId::parse("").is_err());
    }

    #[test]
    fn digest_is_deterministic() {
        let id = CandidateId::parse("C1").unwrap();
        let ev = vec![EvidenceRef::parse("E1").unwrap()];
        assert_eq!(digest_chain(&id, &ev), digest_chain(&id, &ev));
    }
}
