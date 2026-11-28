use std::error::Error;
use std::fmt;

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

id_type!(WorkUnitId, "work unit id");
id_type!(CheckpointId, "checkpoint id");
id_type!(DomainSnapshotId, "domain snapshot id");
id_type!(PublicationSnapshotId, "publication snapshot id");

/// Processing policy version for HC-10 transition traces.
pub const WORK_POLICY_VERSION: &str = "hc10:work-state:v1";

/// Application processing states only. Not legal/lifecycle/authority states.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WorkState {
    Requested,
    Running,
    Cancelling,
    Cancelled,
    Failed,
    Committed,
    Stale,
}

impl WorkState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Requested => "requested",
            Self::Running => "running",
            Self::Cancelling => "cancelling",
            Self::Cancelled => "cancelled",
            Self::Failed => "failed",
            Self::Committed => "committed",
            Self::Stale => "stale",
        }
    }
}

/// Processing events that may advance work state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WorkEvent {
    Start,
    Cancel,
    CancelAck,
    Resume,
    Fail,
    Commit,
    MarkStale,
}

impl WorkEvent {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Start => "start",
            Self::Cancel => "cancel",
            Self::CancelAck => "cancel_ack",
            Self::Resume => "resume",
            Self::Fail => "fail",
            Self::Commit => "commit",
            Self::MarkStale => "mark_stale",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TransitionOutcome {
    Transitioned,
    InvalidTransition,
    StaleCheckpoint,
    RetryExhausted,
    LegalMutationRejected,
}

impl TransitionOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Transitioned => "transitioned",
            Self::InvalidTransition => "invalid-transition",
            Self::StaleCheckpoint => "stale",
            Self::RetryExhausted => "retry-exhausted",
            Self::LegalMutationRejected => "legal-mutation-rejected",
        }
    }
}

/// Attempt to map processing progress onto legal/domain authority labels.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LegalMappingAttempt {
    None,
    ProgressAsVerified,
    ProgressAsCurrent,
    ProgressAsLegalState,
    MutateLifecycle,
    MutateClock,
    MutateIdentity,
    MutateRelation,
    MutateAuthority,
}

impl LegalMappingAttempt {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::ProgressAsVerified => "progress_as_verified",
            Self::ProgressAsCurrent => "progress_as_current",
            Self::ProgressAsLegalState => "progress_as_legal_state",
            Self::MutateLifecycle => "mutate_lifecycle",
            Self::MutateClock => "mutate_clock",
            Self::MutateIdentity => "mutate_identity",
            Self::MutateRelation => "mutate_relation",
            Self::MutateAuthority => "mutate_authority",
        }
    }

    pub fn is_forbidden(self) -> bool {
        !matches!(self, Self::None)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionRequest {
    pub work_unit_id: WorkUnitId,
    pub event: WorkEvent,
    pub expected_checkpoint: Option<CheckpointId>,
    pub legal_mapping: LegalMappingAttempt,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionTrace {
    pub policy_version: String,
    pub work_unit_id: WorkUnitId,
    pub event: WorkEvent,
    pub from_state: WorkState,
    pub to_state: WorkState,
    pub prior_checkpoint: CheckpointId,
    pub new_checkpoint: CheckpointId,
    pub domain_snapshot_before: DomainSnapshotId,
    pub domain_snapshot_after: DomainSnapshotId,
    pub publication_snapshot_before: PublicationSnapshotId,
    pub publication_snapshot_after: PublicationSnapshotId,
    pub domain_unchanged: bool,
    pub publication_unchanged: bool,
    pub legal_mapping_attempt: LegalMappingAttempt,
    pub legal_mapping_applied: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionResult {
    pub outcome: TransitionOutcome,
    pub state: WorkState,
    pub checkpoint: CheckpointId,
    pub domain_snapshot: DomainSnapshotId,
    pub publication_snapshot: PublicationSnapshotId,
    pub domain_unchanged: bool,
    pub publication_unchanged: bool,
    pub legal_mapping_applied: bool,
    pub trace: TransitionTrace,
}

/// Pure transition table for application processing states.
pub fn next_state(current: WorkState, event: WorkEvent) -> Option<WorkState> {
    match (current, event) {
        (WorkState::Requested, WorkEvent::Start) => Some(WorkState::Running),
        (WorkState::Requested, WorkEvent::Cancel) => Some(WorkState::Cancelling),
        (WorkState::Requested, WorkEvent::Fail) => Some(WorkState::Failed),
        (WorkState::Running, WorkEvent::Cancel) => Some(WorkState::Cancelling),
        (WorkState::Running, WorkEvent::Fail) => Some(WorkState::Failed),
        (WorkState::Running, WorkEvent::Commit) => Some(WorkState::Committed),
        (WorkState::Running, WorkEvent::MarkStale) => Some(WorkState::Stale),
        (WorkState::Cancelling, WorkEvent::CancelAck) => Some(WorkState::Cancelled),
        (WorkState::Cancelling, WorkEvent::Fail) => Some(WorkState::Failed),
        (WorkState::Cancelled, WorkEvent::Resume) => Some(WorkState::Running),
        (WorkState::Cancelled, WorkEvent::MarkStale) => Some(WorkState::Stale),
        (WorkState::Failed, WorkEvent::Resume) => Some(WorkState::Running),
        (WorkState::Failed, WorkEvent::MarkStale) => Some(WorkState::Stale),
        (WorkState::Stale, WorkEvent::Resume) => Some(WorkState::Running),
        (WorkState::Stale, WorkEvent::Cancel) => Some(WorkState::Cancelling),
        // Terminal committed: only mark_stale is allowed for observability.
        (WorkState::Committed, WorkEvent::MarkStale) => Some(WorkState::Stale),
        _ => None,
    }
}

/// Fail-closed FSM wrapper for [`WorkState`] backed by `ln-fsm`.
#[derive(Debug, Clone, Copy, Default)]
pub struct WorkStateMachine;

impl ln_fsm::DeterministicFsm for WorkStateMachine {
    type State = WorkState;
    type Event = WorkEvent;
    type RejectionReason = TransitionOutcome;

    fn policy_version(&self) -> &'static str {
        WORK_POLICY_VERSION
    }

    fn is_terminal(&self, _state: &Self::State) -> bool {
        // Committed intentionally allows MarkStale for observability.
        false
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        TransitionOutcome::InvalidTransition
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, ln_fsm::StepError<Self::RejectionReason>> {
        next_state(*state, *event).ok_or(ln_fsm::StepError::InvalidTransition(
            TransitionOutcome::InvalidTransition,
        ))
    }
}

/// Declarative transition-graph contract for [`WorkStateMachine`].
pub const WORK_STATE_GRAPH_SPEC: ln_fsm::graph::GraphSpec = ln_fsm::graph::GraphSpec {
    name: "work_state",
    initial: "requested",
    states: &[
        "requested",
        "running",
        "cancelling",
        "cancelled",
        "failed",
        "committed",
        "stale",
    ],
    terminals: &[],
    transitions: &[
        ln_fsm::graph::EdgeSpec {
            from: "requested",
            event: "start",
            to: "running",
        },
        ln_fsm::graph::EdgeSpec {
            from: "requested",
            event: "cancel",
            to: "cancelling",
        },
        ln_fsm::graph::EdgeSpec {
            from: "requested",
            event: "fail",
            to: "failed",
        },
        ln_fsm::graph::EdgeSpec {
            from: "running",
            event: "cancel",
            to: "cancelling",
        },
        ln_fsm::graph::EdgeSpec {
            from: "running",
            event: "fail",
            to: "failed",
        },
        ln_fsm::graph::EdgeSpec {
            from: "running",
            event: "commit",
            to: "committed",
        },
        ln_fsm::graph::EdgeSpec {
            from: "running",
            event: "mark_stale",
            to: "stale",
        },
        ln_fsm::graph::EdgeSpec {
            from: "cancelling",
            event: "cancel_ack",
            to: "cancelled",
        },
        ln_fsm::graph::EdgeSpec {
            from: "cancelling",
            event: "fail",
            to: "failed",
        },
        ln_fsm::graph::EdgeSpec {
            from: "cancelled",
            event: "resume",
            to: "running",
        },
        ln_fsm::graph::EdgeSpec {
            from: "cancelled",
            event: "mark_stale",
            to: "stale",
        },
        ln_fsm::graph::EdgeSpec {
            from: "failed",
            event: "resume",
            to: "running",
        },
        ln_fsm::graph::EdgeSpec {
            from: "failed",
            event: "mark_stale",
            to: "stale",
        },
        ln_fsm::graph::EdgeSpec {
            from: "stale",
            event: "resume",
            to: "running",
        },
        ln_fsm::graph::EdgeSpec {
            from: "stale",
            event: "cancel",
            to: "cancelling",
        },
        ln_fsm::graph::EdgeSpec {
            from: "committed",
            event: "mark_stale",
            to: "stale",
        },
    ],
    forbidden_direct_edges: &[
        ln_fsm::graph::ForbiddenEdge {
            from: "requested",
            to: "committed",
            rationale: "work must enter running before commit",
        },
        ln_fsm::graph::ForbiddenEdge {
            from: "committed",
            to: "running",
            rationale: "committed work cannot silently resume without mark_stale",
        },
    ],
    allow_guarded_branching: false,
};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_work_unit_id() {
        assert!(WorkUnitId::parse("").is_err());
    }

    #[test]
    fn cancel_resume_path_is_valid() {
        assert_eq!(
            next_state(WorkState::Running, WorkEvent::Cancel),
            Some(WorkState::Cancelling)
        );
        assert_eq!(
            next_state(WorkState::Cancelling, WorkEvent::CancelAck),
            Some(WorkState::Cancelled)
        );
        assert_eq!(
            next_state(WorkState::Cancelled, WorkEvent::Resume),
            Some(WorkState::Running)
        );
    }

    #[test]
    fn commit_cannot_resume_into_running() {
        assert_eq!(next_state(WorkState::Committed, WorkEvent::Resume), None);
    }
}
