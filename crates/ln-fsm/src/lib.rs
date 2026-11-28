//! Zero-dependency, fail-closed deterministic finite-state-machine primitives.
//!
//! `ln-fsm` is a domain-neutral support crate (not a KOF-DA capability owner
//! under ADR-0011). Capability crates retain full ownership of their domain
//! state/event enums and legal semantics; `ln-fsm` provides:
//!
//! - [`DeterministicFsm`] with fail-closed [`TransitionReceipt`] /
//!   [`TransitionRejection`] and structured [`TransitionTrace`] (INV-10: never
//!   substitutes silent `None` for a typed refusal);
//! - [`graph::validate_graph`] to verify reachability, terminal isolation,
//!   dead-end absence, determinism, and forbidden direct edges on declarative
//!   transition tables;
//! - [`graph::to_mermaid_state_diagram`] to render `stateDiagram-v2` directly
//!   from code;
//! - [`model_check::run_deterministic_model_check`] for offline, zero-dep
//!   seeded sequence exploration with counterexample shrinking.

pub mod graph;
pub mod model_check;

use std::fmt;

/// Category of a fail-closed FSM rejection (INV-10).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum RejectionKind {
    /// Transition attempted from a terminal state (always refused).
    TerminalState,
    /// `(state, event)` pair is not an admissible transition.
    InvalidTransition,
    /// A domain guard rejected an otherwise admissible transition.
    GuardRejected,
}

impl RejectionKind {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::TerminalState => "terminal-state",
            Self::InvalidTransition => "invalid-transition",
            Self::GuardRejected => "guard-rejected",
        }
    }
}

/// Structured audit record emitted for every attempted FSM transition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionTrace<S, E> {
    pub policy_version: &'static str,
    pub from: S,
    pub event: E,
    pub to: Option<S>,
    pub accepted: bool,
}

/// Receipt returned when a deterministic transition succeeds.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionReceipt<S, E> {
    pub next: S,
    pub trace: TransitionTrace<S, E>,
}

/// Typed refusal returned when a transition is rejected fail-closed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionRejection<S, E, R> {
    pub state: S,
    pub event: E,
    pub kind: RejectionKind,
    pub reason: R,
    pub trace: TransitionTrace<S, E>,
}

/// Typed outcome returned by [`DeterministicFsm::apply`].
pub type ApplyResult<S, E, R> = Result<TransitionReceipt<S, E>, TransitionRejection<S, E, R>>;

/// Error returned by [`DeterministicFsm::step`] for non-terminal states.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum StepError<R> {
    InvalidTransition(R),
    GuardRejected(R),
}

/// Result of replaying a sequence of events through [`DeterministicFsm::replay`].
#[must_use]
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplayOutcome<S, E, R> {
    pub final_state: S,
    pub traces: Vec<TransitionTrace<S, E>>,
    pub rejected_at: Option<(usize, TransitionRejection<S, E, R>)>,
}

/// Pure, fail-closed deterministic finite state machine contract.
///
/// Supports both flat tag enums and fields-carrying state enums (`State: Clone + Eq`).
pub trait DeterministicFsm {
    type State: Clone + Eq + fmt::Debug;
    type Event: Clone + Eq + fmt::Debug;
    type RejectionReason: Clone + Eq + fmt::Debug;

    /// Version identifier embedded into every emitted [`TransitionTrace`].
    fn policy_version(&self) -> &'static str;

    /// Returns `true` when `state` is terminal and must never accept further transitions.
    fn is_terminal(&self, state: &Self::State) -> bool;

    /// Reason emitted when an event targets a terminal state.
    fn terminal_rejection_reason(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Self::RejectionReason;

    /// Pure transition step for a non-terminal state.
    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>>;

    /// Apply one event fail-closed, enforcing terminal-state immutability and
    /// emitting a [`TransitionTrace`].
    fn apply(
        &self,
        state: Self::State,
        event: Self::Event,
    ) -> ApplyResult<Self::State, Self::Event, Self::RejectionReason> {
        let policy_version = self.policy_version();
        if self.is_terminal(&state) {
            let reason = self.terminal_rejection_reason(&state, &event);
            let trace = TransitionTrace {
                policy_version,
                from: state.clone(),
                event: event.clone(),
                to: None,
                accepted: false,
            };
            return Err(TransitionRejection {
                state,
                event,
                kind: RejectionKind::TerminalState,
                reason,
                trace,
            });
        }

        match self.step(&state, &event) {
            Ok(next) => {
                let trace = TransitionTrace {
                    policy_version,
                    from: state,
                    event,
                    to: Some(next.clone()),
                    accepted: true,
                };
                Ok(TransitionReceipt { next, trace })
            }
            Err(step_err) => {
                let (kind, reason) = match step_err {
                    StepError::InvalidTransition(r) => (RejectionKind::InvalidTransition, r),
                    StepError::GuardRejected(r) => (RejectionKind::GuardRejected, r),
                };
                let trace = TransitionTrace {
                    policy_version,
                    from: state.clone(),
                    event: event.clone(),
                    to: None,
                    accepted: false,
                };
                Err(TransitionRejection {
                    state,
                    event,
                    kind,
                    reason,
                    trace,
                })
            }
        }
    }

    /// Deterministically replay a sequence of events, halting on the first
    /// rejection while preserving the exact prior state and full trace prefix.
    fn replay<I>(
        &self,
        initial: Self::State,
        events: I,
    ) -> ReplayOutcome<Self::State, Self::Event, Self::RejectionReason>
    where
        I: IntoIterator<Item = Self::Event>,
    {
        let mut current = initial;
        let mut traces = Vec::new();
        for (index, event) in events.into_iter().enumerate() {
            match self.apply(current, event) {
                Ok(receipt) => {
                    current = receipt.next;
                    traces.push(receipt.trace);
                }
                Err(rejection) => {
                    let final_state = rejection.state.clone();
                    traces.push(rejection.trace.clone());
                    return ReplayOutcome {
                        final_state,
                        traces,
                        rejected_at: Some((index, rejection)),
                    };
                }
            }
        }
        ReplayOutcome {
            final_state: current,
            traces,
            rejected_at: None,
        }
    }
}
