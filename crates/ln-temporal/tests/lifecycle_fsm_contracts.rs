use std::cell::Cell;

use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};
use ln_temporal::lifecycle_fsms::{
    ASSERTION_LIFECYCLE_GRAPH_SPEC, AssertionLifecycleEvent, AssertionLifecycleFsm,
    AssertionLifecycleRefusal, AssertionLifecycleState, PENDING_EFFECT_GRAPH_SPEC,
    PendingEffectEvent, PendingEffectFsm, PendingEffectRefusal, PendingEffectState,
};

fn assert_exhaustive_pending_state(s: &PendingEffectState) {
    match s {
        PendingEffectState::Scheduled { .. }
        | PendingEffectState::Applied { .. }
        | PendingEffectState::Cancelled { .. }
        | PendingEffectState::Unknown { .. } => {}
    }
}

fn assert_exhaustive_pending_event(e: &PendingEffectEvent) {
    match e {
        PendingEffectEvent::ModifyPendingEffect { .. }
        | PendingEffectEvent::CancelPendingEffect { .. }
        | PendingEffectEvent::SelectorSatisfied { .. }
        | PendingEffectEvent::MarkUnknown { .. } => {}
    }
}

fn assert_exhaustive_assertion_state(s: &AssertionLifecycleState) {
    match s {
        AssertionLifecycleState::Proposed { .. }
        | AssertionLifecycleState::Validated { .. }
        | AssertionLifecycleState::AuthoritativeInternal { .. }
        | AssertionLifecycleState::Rejected { .. }
        | AssertionLifecycleState::Superseded { .. } => {}
    }
}

fn assert_exhaustive_assertion_event(e: &AssertionLifecycleEvent) {
    match e {
        AssertionLifecycleEvent::AttachValidationReceipt { .. }
        | AssertionLifecycleEvent::AcceptForProjection { .. }
        | AssertionLifecycleEvent::Reject { .. }
        | AssertionLifecycleEvent::SupersedeAppend { .. } => {}
    }
}

#[test]
fn pending_effect_fsm_bijection_guards_and_model_check() {
    let report =
        validate_graph(&PENDING_EFFECT_GRAPH_SPEC).expect("pending effect graph must validate");
    assert_eq!(report.state_count, 4);
    assert_eq!(report.terminal_count, 3);
    assert_eq!(report.reachable_count, 4);

    let mermaid = to_mermaid_state_diagram(&PENDING_EFFECT_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> scheduled"));
    assert!(mermaid.contains("scheduled --> applied: selector_satisfied"));
    assert!(mermaid.contains("applied --> [*]"));

    let states = [
        PendingEffectState::Scheduled {
            pending_id: "pend-1".to_owned(),
            expected_base_version: "ctv-0".to_owned(),
            modifications: Vec::new(),
        },
        PendingEffectState::Applied {
            pending_id: "pend-1".to_owned(),
            applied_at_day: 20260101,
        },
        PendingEffectState::Cancelled {
            pending_id: "pend-1".to_owned(),
            cancelled_by_op: "cancel-1".to_owned(),
        },
        PendingEffectState::Unknown {
            pending_id: "pend-1".to_owned(),
            reason: "missing-clock",
        },
    ];
    let events = [
        PendingEffectEvent::ModifyPendingEffect {
            modification_op_id: "mod-1".to_owned(),
        },
        PendingEffectEvent::CancelPendingEffect {
            cancel_op_id: "cancel-1".to_owned(),
        },
        PendingEffectEvent::SelectorSatisfied {
            legal_as_of_day: 20260101,
        },
        PendingEffectEvent::MarkUnknown {
            reason: "missing-clock",
        },
    ];

    let fsm = PendingEffectFsm;
    let mut observed_edges = 0usize;
    for state in &states {
        assert_exhaustive_pending_state(state);
        let declared_terminal = PENDING_EFFECT_GRAPH_SPEC.terminals.contains(&state.tag());
        assert_eq!(fsm.is_terminal(state), declared_terminal);
        for event in &events {
            assert_exhaustive_pending_event(event);
            let declared = PENDING_EFFECT_GRAPH_SPEC
                .transitions
                .iter()
                .find(|edge| edge.from == state.tag() && edge.event == event.tag());
            match (fsm.apply(state.clone(), event.clone()), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.tag(), edge.to);
                    assert_eq!(receipt.trace.policy_version, fsm.policy_version());
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    assert_eq!(rej.trace.policy_version, fsm.policy_version());
                    assert!(!rej.trace.accepted);
                    assert_eq!(rej.reason, PendingEffectRefusal::PreconditionMismatch);
                    if declared_terminal {
                        assert_eq!(rej.kind, RejectionKind::TerminalState);
                    }
                }
                (Ok(r), None) => panic!(
                    "undeclared PendingEffect edge ({}, {}) -> {}",
                    state.tag(),
                    event.tag(),
                    r.next.tag()
                ),
                (Err(rej), Some(edge)) => panic!(
                    "declared PendingEffect edge ({}, {}) -> {} rejected: {:?}",
                    state.tag(),
                    event.tag(),
                    edge.to,
                    rej.kind
                ),
            }
        }
    }
    assert_eq!(observed_edges, PENDING_EFFECT_GRAPH_SPEC.transitions.len());

    // Guard rejections on empty provenance/reason strings.
    let scheduled = states[0].clone();
    for bad_event in [
        PendingEffectEvent::ModifyPendingEffect {
            modification_op_id: "   ".to_owned(),
        },
        PendingEffectEvent::CancelPendingEffect {
            cancel_op_id: "".to_owned(),
        },
        PendingEffectEvent::MarkUnknown { reason: " " },
    ] {
        let rej = fsm
            .apply(scheduled.clone(), bad_event)
            .expect_err("empty guard input must fail closed");
        assert_eq!(rej.kind, RejectionKind::GuardRejected);
        assert_eq!(rej.reason, PendingEffectRefusal::PreconditionMismatch);
    }

    let terminals_seen = Cell::new(0usize);
    let mc = run_deterministic_model_check(
        &fsm,
        scheduled,
        &events,
        ModelCheckConfig::default(),
        |prev, _event, outcome| {
            if let Ok(receipt) = outcome {
                if prev.tag() == "applied" && receipt.next.tag() == "cancelled" {
                    return Err("applied -> cancelled forbidden".to_owned());
                }
                if fsm.is_terminal(&receipt.next) {
                    terminals_seen.set(terminals_seen.get() + 1);
                }
            }
            Ok(())
        },
    )
    .expect("pending effect model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0 && mc.rejected_steps > 0 && terminals_seen.get() > 0);
}

#[test]
fn assertion_lifecycle_fsm_bijection_e27_guards_and_model_check() {
    let report = validate_graph(&ASSERTION_LIFECYCLE_GRAPH_SPEC)
        .expect("assertion lifecycle graph must validate");
    assert_eq!(report.state_count, 5);
    assert_eq!(report.terminal_count, 2);
    assert_eq!(report.reachable_count, 5);

    let mermaid = to_mermaid_state_diagram(&ASSERTION_LIFECYCLE_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> Proposed"));
    assert!(mermaid.contains("Validated --> AuthoritativeInternal: AcceptForProjection"));
    assert!(mermaid.contains("Superseded --> [*]"));

    let states = [
        AssertionLifecycleState::Proposed {
            assertion_id: "assert-1".to_owned(),
        },
        AssertionLifecycleState::Validated {
            assertion_id: "assert-1".to_owned(),
            validation_receipt_id: "rcpt-1".to_owned(),
        },
        AssertionLifecycleState::AuthoritativeInternal {
            assertion_id: "assert-1".to_owned(),
            validation_receipt_id: "rcpt-1".to_owned(),
            disposition_event_id: "disp-1".to_owned(),
        },
        AssertionLifecycleState::Rejected {
            assertion_id: "assert-1".to_owned(),
            rationale: "invalid".to_owned(),
        },
        AssertionLifecycleState::Superseded {
            assertion_id: "assert-1".to_owned(),
            superseded_by_assertion_id: "assert-2".to_owned(),
        },
    ];
    let events = [
        AssertionLifecycleEvent::AttachValidationReceipt {
            receipt_id: "rcpt-1".to_owned(),
        },
        AssertionLifecycleEvent::AcceptForProjection {
            disposition_event_id: "disp-1".to_owned(),
        },
        AssertionLifecycleEvent::Reject {
            rationale: "bad-evidence".to_owned(),
        },
        AssertionLifecycleEvent::SupersedeAppend {
            replacement_assertion_id: "assert-2".to_owned(),
        },
    ];

    let fsm = AssertionLifecycleFsm;
    let mut observed_edges = 0usize;
    for state in &states {
        assert_exhaustive_assertion_state(state);
        let declared_terminal = ASSERTION_LIFECYCLE_GRAPH_SPEC
            .terminals
            .contains(&state.tag());
        assert_eq!(fsm.is_terminal(state), declared_terminal);
        for event in &events {
            assert_exhaustive_assertion_event(event);
            let declared = ASSERTION_LIFECYCLE_GRAPH_SPEC
                .transitions
                .iter()
                .find(|edge| edge.from == state.tag() && edge.event == event.tag());
            match (fsm.apply(state.clone(), event.clone()), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.tag(), edge.to);
                    assert_eq!(receipt.trace.policy_version, fsm.policy_version());
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    assert_eq!(rej.trace.policy_version, fsm.policy_version());
                    assert!(!rej.trace.accepted);
                    if declared_terminal {
                        assert_eq!(rej.kind, RejectionKind::TerminalState);
                        assert_eq!(rej.reason, AssertionLifecycleRefusal::InPlaceRewrite);
                    }
                }
                (Ok(r), None) => panic!(
                    "undeclared AssertionLifecycle edge ({}, {}) -> {}",
                    state.tag(),
                    event.tag(),
                    r.next.tag()
                ),
                (Err(rej), Some(edge)) => panic!(
                    "declared AssertionLifecycle edge ({}, {}) -> {} rejected: {:?}",
                    state.tag(),
                    event.tag(),
                    edge.to,
                    rej.kind
                ),
            }
        }
    }
    assert_eq!(
        observed_edges,
        ASSERTION_LIFECYCLE_GRAPH_SPEC.transitions.len()
    );

    // Specific E.2.7 contract refusals:
    // 1. Proposed -> AuthoritativeInternal is SkipLifecycle.
    let skip = fsm
        .apply(states[0].clone(), events[1].clone())
        .expect_err("Proposed -> AuthoritativeInternal must fail closed");
    assert_eq!(skip.kind, RejectionKind::GuardRejected);
    assert_eq!(skip.reason, AssertionLifecycleRefusal::SkipLifecycle);

    // 2. Validated -> Rejected and AuthoritativeInternal -> Rejected are forbidden (E.2.7).
    let val_rej = fsm
        .apply(states[1].clone(), events[2].clone())
        .expect_err("Validated cannot be rejected (E.2.7)");
    assert_eq!(val_rej.reason, AssertionLifecycleRefusal::InPlaceRewrite);

    let auth_rej = fsm
        .apply(states[2].clone(), events[2].clone())
        .expect_err("AuthoritativeInternal cannot be rejected (E.2.7)");
    assert_eq!(auth_rej.reason, AssertionLifecycleRefusal::InPlaceRewrite);

    // 3. Proposed -> Superseded is SkipLifecycle.
    let prop_sup = fsm
        .apply(states[0].clone(), events[3].clone())
        .expect_err("Proposed cannot be superseded");
    assert_eq!(prop_sup.reason, AssertionLifecycleRefusal::SkipLifecycle);

    // 4. Self-supersession and empty guards fail closed.
    let self_sup = fsm
        .apply(
            states[1].clone(),
            AssertionLifecycleEvent::SupersedeAppend {
                replacement_assertion_id: "assert-1".to_owned(),
            },
        )
        .expect_err("self-supersession must fail closed");
    assert_eq!(self_sup.reason, AssertionLifecycleRefusal::InPlaceRewrite);

    let empty_rat = fsm
        .apply(
            states[0].clone(),
            AssertionLifecycleEvent::Reject {
                rationale: "  ".to_owned(),
            },
        )
        .expect_err("empty rationale must fail closed");
    assert_eq!(empty_rat.reason, AssertionLifecycleRefusal::SkipLifecycle);

    assert!(!states[0].enters_fold());
    assert!(states[1].enters_fold());
    assert!(states[2].enters_fold());
    assert!(!states[3].enters_fold());
    assert!(!states[4].enters_fold());

    let terminals_seen = Cell::new(0usize);
    let mc = run_deterministic_model_check(
        &fsm,
        states[0].clone(),
        &events,
        ModelCheckConfig::default(),
        |prev, _event, outcome| {
            if let Ok(receipt) = outcome {
                if prev.tag() == "Proposed" && receipt.next.tag() == "AuthoritativeInternal" {
                    return Err("direct Proposed -> AuthoritativeInternal forbidden".to_owned());
                }
                if matches!(prev.tag(), "Validated" | "AuthoritativeInternal")
                    && receipt.next.tag() == "Rejected"
                {
                    return Err("Validated/AuthoritativeInternal -> Rejected forbidden".to_owned());
                }
                if fsm.is_terminal(&receipt.next) {
                    terminals_seen.set(terminals_seen.get() + 1);
                }
            }
            Ok(())
        },
    )
    .expect("assertion lifecycle model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0 && mc.rejected_steps > 0 && terminals_seen.get() > 0);
}
