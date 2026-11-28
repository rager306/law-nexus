use std::cell::Cell;

use ln_fsm::graph::{
    EdgeSpec, ForbiddenEdge, GraphDefect, GraphSpec, to_mermaid_state_diagram, validate_graph,
};
use ln_fsm::model_check::{ModelCheckConfig, ModelCheckReport, run_deterministic_model_check};
use ln_fsm::{
    ApplyResult, DeterministicFsm, RejectionKind, StepError, TransitionRejection, TransitionTrace,
};

/// Fields-carrying state machine verifying that payload lives strictly inside
/// each variant (2026 Rust FSM best practice).
#[derive(Debug, Clone, PartialEq, Eq)]
enum DraftLifecycle {
    Proposed {
        candidate_id: u32,
    },
    Validated {
        candidate_id: u32,
        receipt_id: u32,
    },
    Authoritative {
        candidate_id: u32,
        receipt_id: u32,
    },
    Rejected {
        candidate_id: u32,
        reason: &'static str,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum DraftEvent {
    Validate { receipt_id: u32 },
    AcceptForProjection,
    Reject(&'static str),
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum DraftRefusal {
    Terminal,
    SkipLifecycle,
    InvalidTransition,
}

struct DraftFsm;

impl DeterministicFsm for DraftFsm {
    type State = DraftLifecycle;
    type Event = DraftEvent;
    type RejectionReason = DraftRefusal;

    fn policy_version(&self) -> &'static str {
        "ln-fsm:test-draft:v1"
    }

    fn is_terminal(&self, state: &Self::State) -> bool {
        matches!(
            state,
            DraftLifecycle::Authoritative { .. } | DraftLifecycle::Rejected { .. }
        )
    }

    fn terminal_rejection_reason(
        &self,
        _state: &Self::State,
        _event: &Self::Event,
    ) -> Self::RejectionReason {
        DraftRefusal::Terminal
    }

    fn step(
        &self,
        state: &Self::State,
        event: &Self::Event,
    ) -> Result<Self::State, StepError<Self::RejectionReason>> {
        match (state, event) {
            (DraftLifecycle::Proposed { candidate_id }, DraftEvent::Validate { receipt_id }) => {
                Ok(DraftLifecycle::Validated {
                    candidate_id: *candidate_id,
                    receipt_id: *receipt_id,
                })
            }
            (DraftLifecycle::Proposed { .. }, DraftEvent::AcceptForProjection) => {
                Err(StepError::GuardRejected(DraftRefusal::SkipLifecycle))
            }
            (DraftLifecycle::Proposed { candidate_id }, DraftEvent::Reject(reason)) => {
                Ok(DraftLifecycle::Rejected {
                    candidate_id: *candidate_id,
                    reason,
                })
            }
            (
                DraftLifecycle::Validated {
                    candidate_id,
                    receipt_id,
                },
                DraftEvent::AcceptForProjection,
            ) => Ok(DraftLifecycle::Authoritative {
                candidate_id: *candidate_id,
                receipt_id: *receipt_id,
            }),
            (DraftLifecycle::Validated { candidate_id, .. }, DraftEvent::Reject(reason)) => {
                Ok(DraftLifecycle::Rejected {
                    candidate_id: *candidate_id,
                    reason,
                })
            }
            _ => Err(StepError::InvalidTransition(
                DraftRefusal::InvalidTransition,
            )),
        }
    }
}

const VALID_SPEC: GraphSpec = GraphSpec {
    name: "draft_lifecycle",
    initial: "Proposed",
    states: &["Proposed", "Validated", "Authoritative", "Rejected"],
    terminals: &["Authoritative", "Rejected"],
    transitions: &[
        EdgeSpec {
            from: "Proposed",
            event: "Validate",
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
            to: "Authoritative",
        },
        EdgeSpec {
            from: "Validated",
            event: "Reject",
            to: "Rejected",
        },
    ],
    forbidden_direct_edges: &[ForbiddenEdge {
        from: "Proposed",
        to: "Authoritative",
        rationale: "direct authoritative mint without validation is forbidden",
    }],
    allow_guarded_branching: false,
};

#[test]
fn rejection_kind_as_str_covers_all_variants() {
    assert_eq!(RejectionKind::TerminalState.as_str(), "terminal-state");
    assert_eq!(
        RejectionKind::InvalidTransition.as_str(),
        "invalid-transition"
    );
    assert_eq!(RejectionKind::GuardRejected.as_str(), "guard-rejected");
}

#[test]
fn graph_validator_passes_well_formed_spec_and_emits_mermaid() {
    let report = validate_graph(&VALID_SPEC).expect("valid spec must pass");
    assert_eq!(report.state_count, 4);
    assert_eq!(report.terminal_count, 2);
    assert_eq!(report.edge_count, 4);
    assert_eq!(report.reachable_count, 4);

    let mermaid = to_mermaid_state_diagram(&VALID_SPEC);
    assert!(mermaid.starts_with("stateDiagram-v2\n"));
    assert!(mermaid.contains("[*] --> Proposed"));
    assert!(mermaid.contains("Validated --> Authoritative: AcceptForProjection"));
    assert!(mermaid.contains("Authoritative --> [*]"));
}

#[test]
fn graph_validator_catches_every_structural_defect_kind() {
    // 1. Empty states
    const EMPTY: GraphSpec = GraphSpec {
        name: "empty",
        initial: "A",
        states: &[],
        terminals: &[],
        transitions: &[],
        forbidden_direct_edges: &[],
        allow_guarded_branching: false,
    };
    assert_eq!(validate_graph(&EMPTY), Err(vec![GraphDefect::EmptyStates]));

    // 2. Duplicate state, unknown initial, unknown/duplicate terminal, unknown
    //    transition endpoints, duplicate edge, non-deterministic edge, unknown
    //    forbidden edge endpoints, self-loop trap.
    const COMPLEX_BROKEN: GraphSpec = GraphSpec {
        name: "complex_broken",
        initial: "GhostInitial",
        states: &["A", "A", "B", "Trap", "Done"],
        terminals: &["Done", "Done", "GhostTerm"],
        transitions: &[
            EdgeSpec {
                from: "A",
                event: "go",
                to: "B",
            },
            EdgeSpec {
                from: "A",
                event: "go",
                to: "B",
            },
            EdgeSpec {
                from: "A",
                event: "go",
                to: "Done",
            },
            EdgeSpec {
                from: "Trap",
                event: "spin",
                to: "Trap",
            },
            EdgeSpec {
                from: "GhostFrom",
                event: "bad",
                to: "GhostTo",
            },
        ],
        forbidden_direct_edges: &[ForbiddenEdge {
            from: "GhostForbiddenFrom",
            to: "GhostForbiddenTo",
            rationale: "stale rule",
        }],
        allow_guarded_branching: false,
    };
    let defects = validate_graph(&COMPLEX_BROKEN).expect_err("complex broken spec must fail");
    assert!(defects.contains(&GraphDefect::DuplicateState("A")));
    assert!(defects.contains(&GraphDefect::UnknownInitialState("GhostInitial")));
    assert!(defects.contains(&GraphDefect::UnknownTerminalState("GhostTerm")));
    assert!(defects.contains(&GraphDefect::DuplicateTerminalState("Done")));
    assert!(defects.contains(&GraphDefect::DuplicateEdge {
        from: "A",
        event: "go",
        to: "B",
    }));
    assert!(defects.contains(&GraphDefect::NonDeterministicEdge {
        from: "A",
        event: "go",
        first_to: "B",
        second_to: "Done",
    }));
    assert!(defects.contains(&GraphDefect::UnknownTransitionEndpoint {
        from: "GhostFrom",
        event: "bad",
        to: "GhostTo",
        unknown: "GhostFrom",
    }));
    assert!(defects.contains(&GraphDefect::UnknownTransitionEndpoint {
        from: "GhostFrom",
        event: "bad",
        to: "GhostTo",
        unknown: "GhostTo",
    }));
    assert!(
        defects.contains(&GraphDefect::UnknownForbiddenEdgeEndpoint {
            from: "GhostForbiddenFrom",
            to: "GhostForbiddenTo",
            unknown: "GhostForbiddenFrom",
        })
    );
    assert!(
        defects.contains(&GraphDefect::UnknownForbiddenEdgeEndpoint {
            from: "GhostForbiddenFrom",
            to: "GhostForbiddenTo",
            unknown: "GhostForbiddenTo",
        })
    );
    assert!(defects.contains(&GraphDefect::NonTerminalSelfLoopTrap("Trap")));

    // 3. Initial state is terminal + outgoing from terminal + forbidden jump +
    //    unreachable + dead end.
    const BROKEN_TERMINAL: GraphSpec = GraphSpec {
        name: "broken_terminal",
        initial: "Authoritative",
        states: &["Proposed", "Validated", "Authoritative", "Orphan"],
        terminals: &["Authoritative"],
        transitions: &[
            EdgeSpec {
                from: "Proposed",
                event: "DirectJump",
                to: "Authoritative",
            },
            EdgeSpec {
                from: "Proposed",
                event: "Validate",
                to: "Validated",
            },
            EdgeSpec {
                from: "Authoritative",
                event: "Leak",
                to: "Proposed",
            },
        ],
        forbidden_direct_edges: &[ForbiddenEdge {
            from: "Proposed",
            to: "Authoritative",
            rationale: "no skip-lifecycle",
        }],
        allow_guarded_branching: false,
    };
    let defects = validate_graph(&BROKEN_TERMINAL).expect_err("broken terminal spec must fail");
    assert!(defects.contains(&GraphDefect::InitialStateIsTerminal("Authoritative")));
    assert!(defects.contains(&GraphDefect::ForbiddenDirectEdgePresent {
        from: "Proposed",
        to: "Authoritative",
        event: "DirectJump",
        rationale: "no skip-lifecycle",
    }));
    assert!(defects.contains(&GraphDefect::OutgoingFromTerminal {
        from: "Authoritative",
        event: "Leak",
        to: "Proposed",
    }));
    assert!(defects.contains(&GraphDefect::UnreachableState("Orphan")));
    assert!(defects.contains(&GraphDefect::NonTerminalDeadEnd("Validated")));

    // 4. Guarded branching allowed when explicitly opted in.
    const GUARDED: GraphSpec = GraphSpec {
        name: "guarded",
        initial: "Start",
        states: &["Start", "Ok", "Err"],
        terminals: &["Ok", "Err"],
        transitions: &[
            EdgeSpec {
                from: "Start",
                event: "Eval",
                to: "Ok",
            },
            EdgeSpec {
                from: "Start",
                event: "Eval",
                to: "Err",
            },
        ],
        forbidden_direct_edges: &[],
        allow_guarded_branching: true,
    };
    let report = validate_graph(&GUARDED).expect("guarded branching must pass when enabled");
    assert_eq!(report.edge_count, 2);
}

#[test]
fn apply_short_circuits_terminal_before_step_and_records_exact_traces() {
    struct PanickingTerminalStep;
    impl DeterministicFsm for PanickingTerminalStep {
        type State = bool;
        type Event = u8;
        type RejectionReason = &'static str;

        fn policy_version(&self) -> &'static str {
            "test:terminal-shortcircuit:v1"
        }
        fn is_terminal(&self, state: &Self::State) -> bool {
            *state
        }
        fn terminal_rejection_reason(&self, _state: &bool, _event: &u8) -> &'static str {
            "already-terminal"
        }
        fn step(&self, state: &bool, _event: &u8) -> Result<bool, StepError<&'static str>> {
            assert!(
                !*state,
                "apply() must short-circuit terminal states before step()"
            );
            Ok(true)
        }
    }

    let machine = PanickingTerminalStep;
    let rej = machine
        .apply(true, 1)
        .expect_err("terminal state must be rejected before step()");
    assert_eq!(rej.kind, RejectionKind::TerminalState);
    assert_eq!(rej.reason, "already-terminal");
    assert_eq!(rej.trace.policy_version, "test:terminal-shortcircuit:v1");
    assert!(rej.trace.from);
    assert_eq!(rej.trace.to, None);
    assert!(!rej.trace.accepted);

    let fsm = DraftFsm;
    // Direct InvalidTransition check (Validate on Validated is invalid).
    let invalid = fsm
        .apply(
            DraftLifecycle::Validated {
                candidate_id: 7,
                receipt_id: 42,
            },
            DraftEvent::Validate { receipt_id: 99 },
        )
        .expect_err("re-validating must be InvalidTransition");
    assert_eq!(invalid.kind, RejectionKind::InvalidTransition);
    assert_eq!(invalid.reason, DraftRefusal::InvalidTransition);
    assert_eq!(invalid.trace.policy_version, "ln-fsm:test-draft:v1");
    assert_eq!(invalid.trace.to, None);
    assert!(!invalid.trace.accepted);

    // GuardRejected check (skip lifecycle).
    let skip = fsm
        .apply(
            DraftLifecycle::Proposed { candidate_id: 7 },
            DraftEvent::AcceptForProjection,
        )
        .expect_err("skip lifecycle must fail closed");
    assert_eq!(skip.kind, RejectionKind::GuardRejected);
    assert_eq!(skip.reason, DraftRefusal::SkipLifecycle);
    assert!(!skip.trace.accepted);
}

#[test]
fn replay_halts_mid_sequence_and_handles_empty_and_all_accepted_paths() {
    let fsm = DraftFsm;

    // 1. Empty sequence.
    let empty = fsm.replay(DraftLifecycle::Proposed { candidate_id: 1 }, []);
    assert_eq!(
        empty.final_state,
        DraftLifecycle::Proposed { candidate_id: 1 }
    );
    assert!(empty.traces.is_empty());
    assert!(empty.rejected_at.is_none());

    // 2. All-accepted sequence.
    let accepted = fsm.replay(
        DraftLifecycle::Proposed { candidate_id: 7 },
        [
            DraftEvent::Validate { receipt_id: 42 },
            DraftEvent::AcceptForProjection,
        ],
    );
    assert_eq!(
        accepted.final_state,
        DraftLifecycle::Authoritative {
            candidate_id: 7,
            receipt_id: 42,
        }
    );
    assert!(accepted.rejected_at.is_none());
    assert_eq!(accepted.traces.len(), 2);
    assert!(accepted.traces.iter().all(|t| t.accepted && t.to.is_some()));

    // 3. Mid-sequence rejection MUST halt before executing trailing valid event.
    let mid_halt = fsm.replay(
        DraftLifecycle::Proposed { candidate_id: 7 },
        [
            DraftEvent::AcceptForProjection,
            DraftEvent::Validate { receipt_id: 42 },
        ],
    );
    assert_eq!(
        mid_halt.final_state,
        DraftLifecycle::Proposed { candidate_id: 7 }
    );
    assert_eq!(mid_halt.traces.len(), 1);
    assert!(!mid_halt.traces[0].accepted);
    let (idx, rej) = mid_halt.rejected_at.expect("must reject at index 0");
    assert_eq!(idx, 0);
    assert_eq!(rej.kind, RejectionKind::GuardRejected);

    // 4. Rejection after reaching terminal halts before trailing event.
    let after_terminal = fsm.replay(
        DraftLifecycle::Proposed { candidate_id: 7 },
        [
            DraftEvent::Validate { receipt_id: 42 },
            DraftEvent::AcceptForProjection,
            DraftEvent::Reject("late"),
            DraftEvent::Validate { receipt_id: 99 },
        ],
    );
    assert_eq!(
        after_terminal.final_state,
        DraftLifecycle::Authoritative {
            candidate_id: 7,
            receipt_id: 42,
        }
    );
    assert_eq!(after_terminal.traces.len(), 3);
    assert!(after_terminal.traces[0].accepted);
    assert!(after_terminal.traces[1].accepted);
    assert!(!after_terminal.traces[2].accepted);
    let (idx, rej) = after_terminal.rejected_at.expect("must reject at index 2");
    assert_eq!(idx, 2);
    assert_eq!(rej.kind, RejectionKind::TerminalState);
}

#[test]
fn model_checker_covers_degenerate_configs_shrinking_and_built_in_safety_detectors() {
    let fsm = DraftFsm;
    let alphabet = [
        DraftEvent::Validate { receipt_id: 1 },
        DraftEvent::AcceptForProjection,
        DraftEvent::Reject("bad"),
    ];

    // Degenerate configs return zeroed report without panicking.
    let zero = ModelCheckReport {
        sequences_run: 0,
        steps_executed: 0,
        accepted_steps: 0,
        rejected_steps: 0,
    };
    assert_eq!(
        run_deterministic_model_check(
            &fsm,
            DraftLifecycle::Proposed { candidate_id: 1 },
            &[],
            ModelCheckConfig::default(),
            |_, _, _| Ok(()),
        ),
        Ok(zero)
    );
    assert_eq!(
        run_deterministic_model_check(
            &fsm,
            DraftLifecycle::Proposed { candidate_id: 1 },
            &alphabet,
            ModelCheckConfig {
                seed: 1,
                sequences: 0,
                max_len: 8,
            },
            |_, _, _| Ok(()),
        ),
        Ok(zero)
    );
    assert_eq!(
        run_deterministic_model_check(
            &fsm,
            DraftLifecycle::Proposed { candidate_id: 1 },
            &alphabet,
            ModelCheckConfig {
                seed: 1,
                sequences: 8,
                max_len: 0,
            },
            |_, _, _| Ok(()),
        ),
        Ok(zero)
    );

    // 1-element alphabet and max_len=1 exercise gen_range(upper <= 1).
    let single = run_deterministic_model_check(
        &fsm,
        DraftLifecycle::Proposed { candidate_id: 1 },
        &[DraftEvent::Validate { receipt_id: 1 }],
        ModelCheckConfig {
            seed: 7,
            sequences: 4,
            max_len: 1,
        },
        |_, _, _| Ok(()),
    )
    .expect("single-element config must pass");
    assert_eq!(single.sequences_run, 4);
    assert_eq!(single.steps_executed, 4);

    // Determinism + shrinking check.
    let cfg = ModelCheckConfig {
        seed: 42,
        sequences: 128,
        max_len: 16,
    };
    let ban_auth = |_prev: &DraftLifecycle,
                    _event: &DraftEvent,
                    outcome: Result<
        &ln_fsm::TransitionReceipt<DraftLifecycle, DraftEvent>,
        &TransitionRejection<DraftLifecycle, DraftEvent, DraftRefusal>,
    >| {
        if let Ok(receipt) = outcome
            && matches!(receipt.next, DraftLifecycle::Authoritative { .. })
        {
            return Err("synthetic ban on Authoritative".to_owned());
        }
        Ok(())
    };
    let fail_a = run_deterministic_model_check(
        &fsm,
        DraftLifecycle::Proposed { candidate_id: 1 },
        &alphabet,
        cfg,
        ban_auth,
    )
    .expect_err("synthetic invariant must fail");
    let fail_b = run_deterministic_model_check(
        &fsm,
        DraftLifecycle::Proposed { candidate_id: 1 },
        &alphabet,
        cfg,
        ban_auth,
    )
    .expect_err("same seed must reproduce failure");
    assert_eq!(fail_a, fail_b);
    assert_eq!(fail_a.reason, "synthetic ban on Authoritative");
    assert_eq!(
        fail_a.minimal_events,
        vec![
            DraftEvent::Validate { receipt_id: 1 },
            DraftEvent::AcceptForProjection,
        ]
    );
    assert_eq!(
        fail_a.failing_state,
        DraftLifecycle::Validated {
            candidate_id: 1,
            receipt_id: 1,
        }
    );
    assert_eq!(fail_a.failing_event, DraftEvent::AcceptForProjection);

    // Built-in detector 1: INV-01 non-deterministic step MUST return Err (not panic in shrink!).
    struct FlakyFsm(Cell<u8>);
    impl DeterministicFsm for FlakyFsm {
        type State = u8;
        type Event = u8;
        type RejectionReason = &'static str;
        fn policy_version(&self) -> &'static str {
            "flaky:v1"
        }
        fn is_terminal(&self, _state: &u8) -> bool {
            false
        }
        fn terminal_rejection_reason(&self, _state: &u8, _event: &u8) -> &'static str {
            "term"
        }
        fn step(&self, state: &u8, _event: &u8) -> Result<u8, StepError<&'static str>> {
            let n = self.0.get();
            self.0.set(n.wrapping_add(1));
            Ok(state.wrapping_add(n % 2))
        }
    }
    let flaky_fail = run_deterministic_model_check(
        &FlakyFsm(Cell::new(0)),
        0u8,
        &[1u8],
        ModelCheckConfig {
            seed: 1,
            sequences: 4,
            max_len: 4,
        },
        |_, _, _| Ok(()),
    )
    .expect_err("flaky FSM must be caught without panicking");
    assert!(flaky_fail.reason.contains("INV-01"));

    // Built-in detector 2: INV-10 rejection returning mutated state.
    struct MutatingRejectFsm;
    impl DeterministicFsm for MutatingRejectFsm {
        type State = u8;
        type Event = u8;
        type RejectionReason = &'static str;
        fn policy_version(&self) -> &'static str {
            "mut-rej:v1"
        }
        fn is_terminal(&self, _state: &u8) -> bool {
            false
        }
        fn terminal_rejection_reason(&self, _state: &u8, _event: &u8) -> &'static str {
            "term"
        }
        fn step(&self, _state: &u8, _event: &u8) -> Result<u8, StepError<&'static str>> {
            Err(StepError::InvalidTransition("no"))
        }
        fn apply(&self, state: u8, event: u8) -> ApplyResult<u8, u8, &'static str> {
            Err(TransitionRejection {
                state: state.wrapping_add(1),
                event,
                kind: RejectionKind::InvalidTransition,
                reason: "mutated",
                trace: TransitionTrace {
                    policy_version: self.policy_version(),
                    from: state,
                    event,
                    to: None,
                    accepted: false,
                },
            })
        }
    }
    let inv10_fail = run_deterministic_model_check(
        &MutatingRejectFsm,
        0u8,
        &[1u8],
        ModelCheckConfig {
            seed: 1,
            sequences: 2,
            max_len: 2,
        },
        |_, _, _| Ok(()),
    )
    .expect_err("mutated state on rejection must trigger INV-10");
    assert!(inv10_fail.reason.contains("INV-10"));

    // Built-in detector 3: non-terminal state falsely returning RejectionKind::TerminalState.
    struct BadTerminalKindFsm;
    impl DeterministicFsm for BadTerminalKindFsm {
        type State = u8;
        type Event = u8;
        type RejectionReason = &'static str;
        fn policy_version(&self) -> &'static str {
            "bad-term:v1"
        }
        fn is_terminal(&self, _state: &u8) -> bool {
            false
        }
        fn terminal_rejection_reason(&self, _state: &u8, _event: &u8) -> &'static str {
            "term"
        }
        fn step(&self, _state: &u8, _event: &u8) -> Result<u8, StepError<&'static str>> {
            Err(StepError::InvalidTransition("no"))
        }
        fn apply(&self, state: u8, event: u8) -> ApplyResult<u8, u8, &'static str> {
            Err(TransitionRejection {
                state,
                event,
                kind: RejectionKind::TerminalState,
                reason: "wrong-kind",
                trace: TransitionTrace {
                    policy_version: self.policy_version(),
                    from: state,
                    event,
                    to: None,
                    accepted: false,
                },
            })
        }
    }
    let term_fail = run_deterministic_model_check(
        &BadTerminalKindFsm,
        0u8,
        &[1u8],
        ModelCheckConfig {
            seed: 1,
            sequences: 2,
            max_len: 2,
        },
        |_, _, _| Ok(()),
    )
    .expect_err("non-terminal returning TerminalState must be caught");
    assert!(term_fail.reason.contains("terminal-state violation"));
}
