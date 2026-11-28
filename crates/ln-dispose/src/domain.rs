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

id_type!(InventoryItemId, "inventory item id");
id_type!(ReviewEvidenceId, "review evidence id");
id_type!(PromotionRequestId, "promotion request id");
id_type!(PromotionAttemptId, "promotion attempt id");
id_type!(CommitId, "commit id");

pub const DISPOSITION_POLICY_VERSION: &str = "hc03:disposition:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DispositionState {
    Pending,
    Quarantined,
    Accepted,
    Rejected,
}

impl DispositionState {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pending => "pending",
            Self::Quarantined => "quarantined",
            Self::Accepted => "accepted",
            Self::Rejected => "rejected",
        }
    }

    pub const fn is_accepted(self) -> bool {
        matches!(self, Self::Accepted)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DispositionEvent {
    Quarantine,
    ReopenPending,
    Accept,
    Reject,
}

impl DispositionEvent {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Quarantine => "quarantine",
            Self::ReopenPending => "reopen-pending",
            Self::Accept => "accept",
            Self::Reject => "reject",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DispositionTransitionRefusal {
    TerminalDispositionImmutable,
    InvalidTransition,
}

/// Deterministic HC-03 disposition lifecycle FSM.
///
/// `Accepted` and `Rejected` are terminal states; `Pending` and `Quarantined`
/// never carry acceptance authorization until an explicit `Accept` transition.
#[derive(Debug, Clone, Copy, Default)]
pub struct DispositionFsm;

impl DeterministicFsm for DispositionFsm {
    type State = DispositionState;
    type Event = DispositionEvent;
    type RejectionReason = DispositionTransitionRefusal;

    fn policy_version(&self) -> &'static str {
        DISPOSITION_POLICY_VERSION
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(
            state,
            DispositionState::Accepted | DispositionState::Rejected
        )
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        DispositionTransitionRefusal::TerminalDispositionImmutable
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, event) {
            (DispositionState::Pending, DispositionEvent::Quarantine) => {
                Ok(DispositionState::Quarantined)
            }
            (DispositionState::Quarantined, DispositionEvent::ReopenPending) => {
                Ok(DispositionState::Pending)
            }
            (
                DispositionState::Pending | DispositionState::Quarantined,
                DispositionEvent::Accept,
            ) => Ok(DispositionState::Accepted),
            (
                DispositionState::Pending | DispositionState::Quarantined,
                DispositionEvent::Reject,
            ) => Ok(DispositionState::Rejected),
            (DispositionState::Pending, DispositionEvent::ReopenPending)
            | (DispositionState::Quarantined, DispositionEvent::Quarantine) => Err(
                StepError::InvalidTransition(DispositionTransitionRefusal::InvalidTransition),
            ),
            (DispositionState::Accepted | DispositionState::Rejected, _) => {
                Err(StepError::InvalidTransition(
                    DispositionTransitionRefusal::TerminalDispositionImmutable,
                ))
            }
        }
    }
}

pub const DISPOSITION_GRAPH_SPEC: GraphSpec = GraphSpec {
    name: "ln-dispose::DispositionFsm",
    initial: "pending",
    states: &["pending", "quarantined", "accepted", "rejected"],
    terminals: &["accepted", "rejected"],
    transitions: &[
        EdgeSpec {
            from: "pending",
            event: "quarantine",
            to: "quarantined",
        },
        EdgeSpec {
            from: "quarantined",
            event: "reopen-pending",
            to: "pending",
        },
        EdgeSpec {
            from: "pending",
            event: "accept",
            to: "accepted",
        },
        EdgeSpec {
            from: "quarantined",
            event: "accept",
            to: "accepted",
        },
        EdgeSpec {
            from: "pending",
            event: "reject",
            to: "rejected",
        },
        EdgeSpec {
            from: "quarantined",
            event: "reject",
            to: "rejected",
        },
    ],
    forbidden_direct_edges: &[
        ForbiddenEdge {
            from: "accepted",
            to: "pending",
            rationale: "Accepted disposition is terminal and cannot reopen",
        },
        ForbiddenEdge {
            from: "accepted",
            to: "quarantined",
            rationale: "Accepted disposition is terminal and cannot be quarantined",
        },
        ForbiddenEdge {
            from: "accepted",
            to: "rejected",
            rationale: "Accepted disposition is terminal and cannot flip to rejected",
        },
        ForbiddenEdge {
            from: "rejected",
            to: "accepted",
            rationale: "Rejected disposition is terminal and cannot flip to accepted",
        },
        ForbiddenEdge {
            from: "rejected",
            to: "pending",
            rationale: "Rejected disposition is terminal and cannot reopen to pending",
        },
        ForbiddenEdge {
            from: "rejected",
            to: "quarantined",
            rationale: "Rejected disposition is terminal and cannot return to quarantined",
        },
    ],
    allow_guarded_branching: false,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DispositionReason {
    Incomplete,
    Conflict,
    Unauthorized,
    Accepted,
    RejectedReasonCoded,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Disposition {
    pub item_id: InventoryItemId,
    pub state: DispositionState,
    pub reason: DispositionReason,
    pub evidence_ids: Vec<ReviewEvidenceId>,
    pub accepted_commit_id: Option<CommitId>,
    pub promotion_identity: Option<PromotionIdentity>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PromotionIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PromotionOutcome {
    Rejected,
    Committed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionResult {
    pub outcome: PromotionOutcome,
    pub reason: DispositionReason,
    pub commit_id: Option<CommitId>,
    pub promotion_identity: Option<PromotionIdentity>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_reject_unsafe_values() {
        assert!(InventoryItemId::parse("").is_err());
        assert!(ReviewEvidenceId::parse("bad id").is_err());
        assert!(PromotionRequestId::parse("a/b").is_err());
    }
}
