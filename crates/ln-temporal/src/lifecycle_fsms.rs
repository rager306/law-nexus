//! Fields-carrying deterministic FSMs for `PendingEffect` (E.2.3) and
//! `AssertionLifecycle` (E.2.7), backed by `ln-fsm` (ADR-0032 / ADR-0017).
//!
//! Lifecycle: `[proposed]`. State-specific evidence payloads live strictly
//! inside enum variants so invalid combinations (e.g. `Validated` without a
//! `receipt_id` or `AuthoritativeInternal` without adjudication) are
//! unrepresentable at compile time.

use ln_fsm::graph::{EdgeSpec, ForbiddenEdge, GraphSpec};
use ln_fsm::{DeterministicFsm, StepError};

// ── 1. PendingEffect FSM (prd/architecture/pending-effects-contract.yaml) ───

/// Fields-carrying state of a scheduled pending effect (E.2.3).
///
/// Matches the closed 4-state set: `scheduled`, `cancelled`, `applied`, `unknown`.
/// There is deliberately no `modified` state: `ModifyPendingEffect` is a
/// `Scheduled -> Scheduled` transition recording provenance.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PendingEffectState {
    Scheduled {
        pending_id: String,
        expected_base_version: String,
        modifications: Vec<String>,
    },
    Applied {
        pending_id: String,
        applied_at_day: i64,
    },
    Cancelled {
        pending_id: String,
        cancelled_by_op: String,
    },
    Unknown {
        pending_id: String,
        reason: &'static str,
    },
}

impl PendingEffectState {
    pub const fn tag(&self) -> &'static str {
        match self {
            Self::Scheduled { .. } => "scheduled",
            Self::Applied { .. } => "applied",
            Self::Cancelled { .. } => "cancelled",
            Self::Unknown { .. } => "unknown",
        }
    }
}

/// Triggers driving [`PendingEffectFsm`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PendingEffectEvent {
    ModifyPendingEffect { modification_op_id: String },
    CancelPendingEffect { cancel_op_id: String },
    SelectorSatisfied { legal_as_of_day: i64 },
    MarkUnknown { reason: &'static str },
}

impl PendingEffectEvent {
    pub const fn tag(&self) -> &'static str {
        match self {
            Self::ModifyPendingEffect { .. } => "ModifyPendingEffect",
            Self::CancelPendingEffect { .. } => "CancelPendingEffect",
            Self::SelectorSatisfied { .. } => "selector_satisfied",
            Self::MarkUnknown { .. } => "mark_unknown",
        }
    }
}

/// Typed refusal for [`PendingEffectFsm`] (`MC-RES` / `pending-effects-contract.yaml`:
/// modifying/cancelling an applied or cancelled pending effect or supplying
/// empty provenance is `PreconditionMismatch`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PendingEffectRefusal {
    PreconditionMismatch,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct PendingEffectFsm;

impl DeterministicFsm for PendingEffectFsm {
    type State = PendingEffectState;
    type Event = PendingEffectEvent;
    type RejectionReason = PendingEffectRefusal;

    fn policy_version(&self) -> &'static str {
        "adr0017:pending-effect-fsm:v1"
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(
            state,
            PendingEffectState::Applied { .. }
                | PendingEffectState::Cancelled { .. }
                | PendingEffectState::Unknown { .. }
        )
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        PendingEffectRefusal::PreconditionMismatch
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, event) {
            (
                PendingEffectState::Scheduled {
                    pending_id,
                    expected_base_version,
                    modifications,
                },
                PendingEffectEvent::ModifyPendingEffect { modification_op_id },
            ) => {
                if modification_op_id.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        PendingEffectRefusal::PreconditionMismatch,
                    ));
                }
                let mut next_mods = modifications.clone();
                next_mods.push(modification_op_id.clone());
                Ok(PendingEffectState::Scheduled {
                    pending_id: pending_id.clone(),
                    expected_base_version: expected_base_version.clone(),
                    modifications: next_mods,
                })
            }
            (
                PendingEffectState::Scheduled { pending_id, .. },
                PendingEffectEvent::CancelPendingEffect { cancel_op_id },
            ) => {
                if cancel_op_id.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        PendingEffectRefusal::PreconditionMismatch,
                    ));
                }
                Ok(PendingEffectState::Cancelled {
                    pending_id: pending_id.clone(),
                    cancelled_by_op: cancel_op_id.clone(),
                })
            }
            (
                PendingEffectState::Scheduled { pending_id, .. },
                PendingEffectEvent::SelectorSatisfied { legal_as_of_day },
            ) => Ok(PendingEffectState::Applied {
                pending_id: pending_id.clone(),
                applied_at_day: *legal_as_of_day,
            }),
            (
                PendingEffectState::Scheduled { pending_id, .. },
                PendingEffectEvent::MarkUnknown { reason },
            ) => {
                if reason.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        PendingEffectRefusal::PreconditionMismatch,
                    ));
                }
                Ok(PendingEffectState::Unknown {
                    pending_id: pending_id.clone(),
                    reason,
                })
            }
            _ => Err(StepError::InvalidTransition(
                PendingEffectRefusal::PreconditionMismatch,
            )),
        }
    }
}

pub const PENDING_EFFECT_GRAPH_SPEC: GraphSpec = GraphSpec {
    name: "pending_effect",
    initial: "scheduled",
    states: &["scheduled", "applied", "cancelled", "unknown"],
    terminals: &["applied", "cancelled", "unknown"],
    transitions: &[
        EdgeSpec {
            from: "scheduled",
            event: "ModifyPendingEffect",
            to: "scheduled",
        },
        EdgeSpec {
            from: "scheduled",
            event: "CancelPendingEffect",
            to: "cancelled",
        },
        EdgeSpec {
            from: "scheduled",
            event: "selector_satisfied",
            to: "applied",
        },
        EdgeSpec {
            from: "scheduled",
            event: "mark_unknown",
            to: "unknown",
        },
    ],
    forbidden_direct_edges: &[
        ForbiddenEdge {
            from: "applied",
            to: "cancelled",
            rationale: "applied effect cannot be cancelled; use supersession/repeal",
        },
        ForbiddenEdge {
            from: "cancelled",
            to: "applied",
            rationale: "cancelled pending effect can never be resurrected",
        },
    ],
    allow_guarded_branching: false,
};

// ── 2. AssertionLifecycle FSM (prd/architecture/assertion-lifecycle-contract.yaml) ─

/// Fields-carrying projection-status state of a `LegalEventAssertion` (E.2.7).
///
/// Closed 5-set: `Proposed`, `Validated`, `AuthoritativeInternal`, `Rejected`, `Superseded`.
/// Per `prd/architecture/assertion-lifecycle-contract.yaml`:
/// - `Reject` exists **only** from `Proposed` (never from `Validated` or `AuthoritativeInternal`);
/// - `AuthoritativeInternal` is reachable **only** from `Validated` (never directly from `Proposed`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AssertionLifecycleState {
    Proposed {
        assertion_id: String,
    },
    Validated {
        assertion_id: String,
        validation_receipt_id: String,
    },
    AuthoritativeInternal {
        assertion_id: String,
        validation_receipt_id: String,
        disposition_event_id: String,
    },
    Rejected {
        assertion_id: String,
        rationale: String,
    },
    Superseded {
        assertion_id: String,
        superseded_by_assertion_id: String,
    },
}

impl AssertionLifecycleState {
    pub const fn tag(&self) -> &'static str {
        match self {
            Self::Proposed { .. } => "Proposed",
            Self::Validated { .. } => "Validated",
            Self::AuthoritativeInternal { .. } => "AuthoritativeInternal",
            Self::Rejected { .. } => "Rejected",
            Self::Superseded { .. } => "Superseded",
        }
    }

    /// True iff this status is eligible to enter projection folds (`Validated`
    /// or `AuthoritativeInternal` per E.2.7 `fold_statuses`).
    pub const fn enters_fold(&self) -> bool {
        matches!(
            self,
            Self::Validated { .. } | Self::AuthoritativeInternal { .. }
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AssertionLifecycleEvent {
    AttachValidationReceipt { receipt_id: String },
    AcceptForProjection { disposition_event_id: String },
    Reject { rationale: String },
    SupersedeAppend { replacement_assertion_id: String },
}

impl AssertionLifecycleEvent {
    pub const fn tag(&self) -> &'static str {
        match self {
            Self::AttachValidationReceipt { .. } => "AttachValidationReceipt",
            Self::AcceptForProjection { .. } => "AcceptForProjection",
            Self::Reject { .. } => "Reject",
            Self::SupersedeAppend { .. } => "SupersedeAppend",
        }
    }
}

/// Closed 3-token typed non-successes from `prd/architecture/assertion-lifecycle-contract.yaml`:
/// - `SkipLifecycle`: skipping a promotion rung (e.g. `Proposed -> AuthoritativeInternal`)
///   or missing required receipt/disposition evidence;
/// - `DirectAuthoritativeMint`: reserved for parser/adapter attempts to mint
///   `AuthoritativeInternal` directly from `none`;
/// - `InPlaceRewrite`: attempting to mutate/reject a committed or terminal row.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AssertionLifecycleRefusal {
    SkipLifecycle,
    DirectAuthoritativeMint,
    InPlaceRewrite,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct AssertionLifecycleFsm;

impl DeterministicFsm for AssertionLifecycleFsm {
    type State = AssertionLifecycleState;
    type Event = AssertionLifecycleEvent;
    type RejectionReason = AssertionLifecycleRefusal;

    fn policy_version(&self) -> &'static str {
        "adr0017:assertion-lifecycle-fsm:v1"
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(
            state,
            AssertionLifecycleState::Rejected { .. } | AssertionLifecycleState::Superseded { .. }
        )
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        AssertionLifecycleRefusal::InPlaceRewrite
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, event) {
            (
                AssertionLifecycleState::Proposed { assertion_id },
                AssertionLifecycleEvent::AttachValidationReceipt { receipt_id },
            ) => {
                if receipt_id.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        AssertionLifecycleRefusal::SkipLifecycle,
                    ));
                }
                Ok(AssertionLifecycleState::Validated {
                    assertion_id: assertion_id.clone(),
                    validation_receipt_id: receipt_id.clone(),
                })
            }
            (
                AssertionLifecycleState::Proposed { .. },
                AssertionLifecycleEvent::AcceptForProjection { .. },
            ) => Err(StepError::GuardRejected(
                AssertionLifecycleRefusal::SkipLifecycle,
            )),
            (
                AssertionLifecycleState::Proposed { assertion_id },
                AssertionLifecycleEvent::Reject { rationale },
            ) => {
                if rationale.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        AssertionLifecycleRefusal::SkipLifecycle,
                    ));
                }
                Ok(AssertionLifecycleState::Rejected {
                    assertion_id: assertion_id.clone(),
                    rationale: rationale.clone(),
                })
            }
            (
                AssertionLifecycleState::Proposed { .. },
                AssertionLifecycleEvent::SupersedeAppend { .. },
            ) => Err(StepError::InvalidTransition(
                AssertionLifecycleRefusal::SkipLifecycle,
            )),
            (
                AssertionLifecycleState::Validated {
                    assertion_id,
                    validation_receipt_id,
                },
                AssertionLifecycleEvent::AcceptForProjection {
                    disposition_event_id,
                },
            ) => {
                if disposition_event_id.trim().is_empty() {
                    return Err(StepError::GuardRejected(
                        AssertionLifecycleRefusal::SkipLifecycle,
                    ));
                }
                Ok(AssertionLifecycleState::AuthoritativeInternal {
                    assertion_id: assertion_id.clone(),
                    validation_receipt_id: validation_receipt_id.clone(),
                    disposition_event_id: disposition_event_id.clone(),
                })
            }
            (
                AssertionLifecycleState::Validated { assertion_id, .. },
                AssertionLifecycleEvent::SupersedeAppend {
                    replacement_assertion_id,
                },
            )
            | (
                AssertionLifecycleState::AuthoritativeInternal { assertion_id, .. },
                AssertionLifecycleEvent::SupersedeAppend {
                    replacement_assertion_id,
                },
            ) => {
                if replacement_assertion_id.trim().is_empty()
                    || replacement_assertion_id == assertion_id
                {
                    return Err(StepError::GuardRejected(
                        AssertionLifecycleRefusal::InPlaceRewrite,
                    ));
                }
                Ok(AssertionLifecycleState::Superseded {
                    assertion_id: assertion_id.clone(),
                    superseded_by_assertion_id: replacement_assertion_id.clone(),
                })
            }
            // Reject or re-validate on committed Validated/AuthoritativeInternal
            // is an in-place rewrite attempt (per E.2.7: reject exists only from Proposed).
            (
                AssertionLifecycleState::Validated { .. }
                | AssertionLifecycleState::AuthoritativeInternal { .. },
                _,
            ) => Err(StepError::InvalidTransition(
                AssertionLifecycleRefusal::InPlaceRewrite,
            )),
            _ => Err(StepError::InvalidTransition(
                AssertionLifecycleRefusal::InPlaceRewrite,
            )),
        }
    }
}

pub const ASSERTION_LIFECYCLE_GRAPH_SPEC: GraphSpec = GraphSpec {
    name: "assertion_lifecycle",
    initial: "Proposed",
    states: &[
        "Proposed",
        "Validated",
        "AuthoritativeInternal",
        "Rejected",
        "Superseded",
    ],
    terminals: &["Rejected", "Superseded"],
    transitions: &[
        EdgeSpec {
            from: "Proposed",
            event: "AttachValidationReceipt",
            to: "Validated",
        },
        EdgeSpec {
            from: "Proposed",
            event: "Reject",
            to: "Rejected",
        },
        EdgeSpec {
            from: "Validated",
            event: "AcceptForProjection",
            to: "AuthoritativeInternal",
        },
        EdgeSpec {
            from: "Validated",
            event: "SupersedeAppend",
            to: "Superseded",
        },
        EdgeSpec {
            from: "AuthoritativeInternal",
            event: "SupersedeAppend",
            to: "Superseded",
        },
    ],
    forbidden_direct_edges: &[
        ForbiddenEdge {
            from: "Proposed",
            to: "AuthoritativeInternal",
            rationale: "direct authoritative mint skipping Validated rung is forbidden (E.2.7)",
        },
        ForbiddenEdge {
            from: "Validated",
            to: "Rejected",
            rationale: "reject exists only from Proposed; Validated must use SupersedeAppend (E.2.7)",
        },
        ForbiddenEdge {
            from: "AuthoritativeInternal",
            to: "Rejected",
            rationale: "AuthoritativeInternal cannot be rejected in place (E.2.7)",
        },
        ForbiddenEdge {
            from: "AuthoritativeInternal",
            to: "Validated",
            rationale: "demotion of AuthoritativeInternal is forbidden (E.2.7)",
        },
        ForbiddenEdge {
            from: "Validated",
            to: "Proposed",
            rationale: "demotion of Validated is forbidden (E.2.7)",
        },
    ],
    allow_guarded_branching: false,
};
