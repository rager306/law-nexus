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

id_type!(PromotionOpId, "promotion operation id");
id_type!(InputDigest, "input digest");
id_type!(CommitId, "commit id");
id_type!(AcceptedSetId, "accepted set id");

/// Sealed publication authority surface. HC-04 must never mint this on D116 success.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationAuthority {
    _sealed: (),
}

pub const PROMOTION_ATTEMPT_POLICY_VERSION: &str = "hc04:promotion-attempt:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PromotionAttemptState {
    InProgress,
    Cancelled,
    Committed,
}

impl PromotionAttemptState {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::InProgress => "in-progress",
            Self::Cancelled => "cancelled",
            Self::Committed => "committed",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PromotionAttemptEvent {
    Cancel,
    Commit,
}

impl PromotionAttemptEvent {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Cancel => "cancel",
            Self::Commit => "commit",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PromotionTransitionRefusal {
    AlreadyCommitted,
    AlreadyCancelled,
}

/// Deterministic FSM for HC-04 / D116 curated promotion attempts.
///
/// `Committed` is terminal/absorbing (idempotent retry never creates a second
/// commit and never reverts to `InProgress` or `Cancelled`); `Cancelled` admits
/// an identical-digest retry via `Commit` (HC-04 `identical_retry_after_cancel`).
#[derive(Debug, Clone, Copy, Default)]
pub struct PromotionAttemptFsm;

impl DeterministicFsm for PromotionAttemptFsm {
    type State = PromotionAttemptState;
    type Event = PromotionAttemptEvent;
    type RejectionReason = PromotionTransitionRefusal;

    fn policy_version(&self) -> &'static str {
        PROMOTION_ATTEMPT_POLICY_VERSION
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(state, PromotionAttemptState::Committed)
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        PromotionTransitionRefusal::AlreadyCommitted
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, event) {
            (PromotionAttemptState::InProgress, PromotionAttemptEvent::Cancel) => {
                Ok(PromotionAttemptState::Cancelled)
            }
            (
                PromotionAttemptState::InProgress | PromotionAttemptState::Cancelled,
                PromotionAttemptEvent::Commit,
            ) => Ok(PromotionAttemptState::Committed),
            (PromotionAttemptState::Cancelled, PromotionAttemptEvent::Cancel) => Err(
                StepError::InvalidTransition(PromotionTransitionRefusal::AlreadyCancelled),
            ),
            (PromotionAttemptState::Committed, _) => Err(StepError::InvalidTransition(
                PromotionTransitionRefusal::AlreadyCommitted,
            )),
        }
    }
}

pub const PROMOTION_ATTEMPT_GRAPH_SPEC: GraphSpec = GraphSpec {
    name: "ln-promote::PromotionAttemptFsm",
    initial: "in-progress",
    states: &["in-progress", "cancelled", "committed"],
    terminals: &["committed"],
    transitions: &[
        EdgeSpec {
            from: "in-progress",
            event: "cancel",
            to: "cancelled",
        },
        EdgeSpec {
            from: "in-progress",
            event: "commit",
            to: "committed",
        },
        EdgeSpec {
            from: "cancelled",
            event: "commit",
            to: "committed",
        },
    ],
    forbidden_direct_edges: &[
        ForbiddenEdge {
            from: "committed",
            to: "in-progress",
            rationale: "Committed promotion attempt is immutable and cannot reopen",
        },
        ForbiddenEdge {
            from: "committed",
            to: "cancelled",
            rationale: "Committed promotion attempt cannot be retroactively cancelled",
        },
    ],
    allow_guarded_branching: false,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PromotionOutcome {
    Cancelled,
    Committed,
    AlreadyCommitted,
    RejectedMismatch,
    Incomplete,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionRecord {
    pub op_id: PromotionOpId,
    pub accepted_set_id: AcceptedSetId,
    pub input_digest: InputDigest,
    pub state: PromotionAttemptState,
    pub commit_id: Option<CommitId>,
    pub commit_digest: Option<InputDigest>,
    pub publication_authority: Option<PublicationAuthority>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionResult {
    pub outcome: PromotionOutcome,
    pub op_id: PromotionOpId,
    pub commit_id: Option<CommitId>,
    pub commit_digest: Option<InputDigest>,
    pub publication_authority: Option<PublicationAuthority>,
}

impl PromotionResult {
    pub fn has_publication_authority(&self) -> bool {
        self.publication_authority.is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_op_id() {
        assert!(PromotionOpId::parse("").is_err());
    }

    #[test]
    fn accepts_stable_op_id() {
        assert_eq!(PromotionOpId::parse("P1").unwrap().as_str(), "P1");
    }
}
