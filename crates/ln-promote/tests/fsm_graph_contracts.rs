use std::cell::Cell;

use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};
use ln_promote::adapters::InMemoryPromotionStore;
use ln_promote::application::CommitCuratedPromotion;
use ln_promote::domain::{
    AcceptedSetId, InputDigest, PROMOTION_ATTEMPT_GRAPH_SPEC, PROMOTION_ATTEMPT_POLICY_VERSION,
    PromotionAttemptEvent, PromotionAttemptFsm, PromotionAttemptState, PromotionOpId,
    PromotionOutcome, PromotionTransitionRefusal,
};

const ALL_STATES: [PromotionAttemptState; 3] = [
    PromotionAttemptState::InProgress,
    PromotionAttemptState::Cancelled,
    PromotionAttemptState::Committed,
];

const ALL_EVENTS: [PromotionAttemptEvent; 2] =
    [PromotionAttemptEvent::Cancel, PromotionAttemptEvent::Commit];

fn assert_exhaustive(state: PromotionAttemptState, event: PromotionAttemptEvent) {
    match state {
        PromotionAttemptState::InProgress
        | PromotionAttemptState::Cancelled
        | PromotionAttemptState::Committed => {}
    }
    match event {
        PromotionAttemptEvent::Cancel | PromotionAttemptEvent::Commit => {}
    }
}

#[test]
fn promotion_attempt_graph_spec_is_valid_bijective_and_model_checked() {
    let report = validate_graph(&PROMOTION_ATTEMPT_GRAPH_SPEC)
        .expect("promotion attempt graph must validate");
    assert_eq!(report.state_count, ALL_STATES.len());
    assert_eq!(report.reachable_count, ALL_STATES.len());
    assert_eq!(report.terminal_count, 1);

    let fsm = PromotionAttemptFsm;
    let mut observed_edges = 0usize;
    for state in ALL_STATES {
        assert_eq!(
            fsm.is_terminal(&state),
            PROMOTION_ATTEMPT_GRAPH_SPEC
                .terminals
                .contains(&state.as_str())
        );
        for event in ALL_EVENTS {
            assert_exhaustive(state, event);
            let declared = PROMOTION_ATTEMPT_GRAPH_SPEC
                .transitions
                .iter()
                .find(|e| e.from == state.as_str() && e.event == event.as_str());
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(
                        receipt.trace.policy_version,
                        PROMOTION_ATTEMPT_POLICY_VERSION
                    );
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    let expected_kind = if fsm.is_terminal(&state) {
                        RejectionKind::TerminalState
                    } else {
                        RejectionKind::InvalidTransition
                    };
                    assert_eq!(rej.kind, expected_kind);
                    assert_eq!(rej.trace.policy_version, PROMOTION_ATTEMPT_POLICY_VERSION);
                    assert!(rej.trace.to.is_none());
                    assert!(!rej.trace.accepted);
                    if state == PromotionAttemptState::Committed {
                        assert_eq!(rej.reason, PromotionTransitionRefusal::AlreadyCommitted);
                    } else {
                        assert_eq!(rej.reason, PromotionTransitionRefusal::AlreadyCancelled);
                    }
                }
                (Ok(receipt), None) => {
                    panic!(
                        "runtime accepted undeclared edge ({:?}, {:?}) -> {:?}",
                        state, event, receipt.next
                    );
                }
                (Err(rej), Some(edge)) => {
                    panic!(
                        "runtime rejected declared edge ({:?}, {:?}) -> {} with {:?}",
                        state, event, edge.to, rej.kind
                    );
                }
            }
        }
    }
    assert_eq!(
        observed_edges,
        PROMOTION_ATTEMPT_GRAPH_SPEC.transitions.len()
    );

    let mermaid = to_mermaid_state_diagram(&PROMOTION_ATTEMPT_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> in-progress"));
    assert!(mermaid.contains("committed --> [*]"));

    let committed_reached = Cell::new(0usize);
    let mc = run_deterministic_model_check(
        &fsm,
        PromotionAttemptState::InProgress,
        &ALL_EVENTS,
        ModelCheckConfig::default(),
        |prev, event, outcome| {
            if let Ok(receipt) = outcome {
                if receipt.next == PromotionAttemptState::InProgress {
                    return Err("attempt must never transition back to InProgress".to_owned());
                }
                if receipt.next == PromotionAttemptState::Committed {
                    if *event != PromotionAttemptEvent::Commit {
                        return Err("only Commit event may reach Committed".to_owned());
                    }
                    committed_reached.set(committed_reached.get() + 1);
                }
                if receipt.next == PromotionAttemptState::Cancelled
                    && (*prev != PromotionAttemptState::InProgress
                        || *event != PromotionAttemptEvent::Cancel)
                {
                    return Err("Cancelled reachable only via InProgress + Cancel".to_owned());
                }
            }
            Ok(())
        },
    )
    .expect("promotion attempt model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0);
    assert!(mc.rejected_steps > 0);
    assert!(committed_reached.get() > 0);
}

#[test]
fn commit_curated_promotion_handles_repeated_cancel_unknown_cancel_and_cancel_after_commit() {
    let mut use_case = CommitCuratedPromotion::new(InMemoryPromotionStore::default());
    let op = PromotionOpId::parse("P-FSM-1").expect("op");
    let set = AcceptedSetId::parse("S-1").expect("set");
    let digest = InputDigest::parse("D-1").expect("digest");

    // Cancel on unknown op returns Incomplete without creating a commit.
    let unknown = use_case.cancel(PromotionOpId::parse("P-UNKNOWN").expect("op"));
    assert_eq!(unknown.outcome, PromotionOutcome::Incomplete);
    assert!(unknown.commit_id.is_none());

    // Repeated cancel (`begin -> cancel -> cancel`) stays idempotent and permits identical retry commit.
    assert_eq!(
        use_case
            .begin(op.clone(), set.clone(), digest.clone())
            .outcome,
        PromotionOutcome::Incomplete
    );
    let c1 = use_case.cancel(op.clone());
    assert_eq!(c1.outcome, PromotionOutcome::Cancelled);
    let c2 = use_case.cancel(op.clone());
    assert_eq!(c2.outcome, PromotionOutcome::Cancelled);
    assert_eq!(use_case.committed_count(), 0);

    let committed = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(committed.outcome, PromotionOutcome::Committed);
    assert!(!committed.has_publication_authority());
    assert_eq!(use_case.committed_count(), 1);

    // Cancel after commit fails closed as AlreadyCommitted preserving original commit_id & digest.
    let cancel_after = use_case.cancel(op.clone());
    assert_eq!(cancel_after.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(cancel_after.commit_id, committed.commit_id);
    assert_eq!(cancel_after.commit_digest, committed.commit_digest);
    assert!(!cancel_after.has_publication_authority());
    assert!(use_case.has_curated_effect_for(&op));
    assert_eq!(use_case.committed_count(), 1);

    // Begin after commit with identical vs mismatched digest.
    assert_eq!(
        use_case.begin(op.clone(), set.clone(), digest).outcome,
        PromotionOutcome::AlreadyCommitted
    );
    assert_eq!(
        use_case
            .begin(op, set, InputDigest::parse("D-OTHER").expect("digest"))
            .outcome,
        PromotionOutcome::RejectedMismatch
    );
}
