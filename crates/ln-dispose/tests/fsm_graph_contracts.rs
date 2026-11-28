use ln_dispose::adapters::{InMemoryDispositionStore, InMemoryPromotionGate};
use ln_dispose::application::DisposeReview;
use ln_dispose::domain::{
    CommitId, DISPOSITION_GRAPH_SPEC, DISPOSITION_POLICY_VERSION, Disposition, DispositionEvent,
    DispositionFsm, DispositionReason, DispositionState, DispositionTransitionRefusal,
    InventoryItemId, PromotionAttemptId, PromotionIdentity, PromotionOutcome, PromotionRequestId,
    PromotionResult, ReviewEvidenceId,
};
use ln_dispose::ports::{DispositionStorePort, PromotionGatePort};
use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};

const ALL_STATES: [DispositionState; 4] = [
    DispositionState::Pending,
    DispositionState::Quarantined,
    DispositionState::Accepted,
    DispositionState::Rejected,
];

const ALL_EVENTS: [DispositionEvent; 4] = [
    DispositionEvent::Quarantine,
    DispositionEvent::ReopenPending,
    DispositionEvent::Accept,
    DispositionEvent::Reject,
];

fn assert_exhaustive(state: DispositionState, event: DispositionEvent) {
    match state {
        DispositionState::Pending
        | DispositionState::Quarantined
        | DispositionState::Accepted
        | DispositionState::Rejected => {}
    }
    match event {
        DispositionEvent::Quarantine
        | DispositionEvent::ReopenPending
        | DispositionEvent::Accept
        | DispositionEvent::Reject => {}
    }
}

/// Hostile/lossy store that drops writes and tries to spoof Accepted on reads.
struct HostileSpoofingStore;
impl DispositionStorePort for HostileSpoofingStore {
    fn set_disposition(&mut self, _disposition: Disposition) {}
    fn get_disposition(&self, item_id: &InventoryItemId) -> Option<Disposition> {
        Some(Disposition {
            item_id: item_id.clone(),
            state: DispositionState::Accepted,
            reason: DispositionReason::Accepted,
            evidence_ids: Vec::new(),
            accepted_commit_id: None,
            promotion_identity: None,
        })
    }
}

/// Hostile gate that ignores `disposition_is_accepted == false` and tries to commit.
struct HostileAlwaysCommitGate;
impl PromotionGatePort for HostileAlwaysCommitGate {
    fn attempt_promotion(
        &mut self,
        item_id: &InventoryItemId,
        _disposition_is_accepted: bool,
    ) -> PromotionResult {
        PromotionResult {
            outcome: PromotionOutcome::Committed,
            reason: DispositionReason::Accepted,
            commit_id: Some(CommitId::parse(&format!("rogue:{}", item_id.as_str())).expect("id")),
            promotion_identity: Some(PromotionIdentity::default()),
        }
    }
}

#[test]
fn disposition_graph_spec_is_valid_bijective_and_model_checked() {
    let report = validate_graph(&DISPOSITION_GRAPH_SPEC).expect("disposition graph must validate");
    assert_eq!(report.state_count, ALL_STATES.len());
    assert_eq!(report.reachable_count, ALL_STATES.len());
    assert_eq!(report.terminal_count, 2);

    let fsm = DispositionFsm;
    let mut observed_edges = 0usize;
    for state in ALL_STATES {
        assert_eq!(
            fsm.is_terminal(&state),
            DISPOSITION_GRAPH_SPEC.terminals.contains(&state.as_str())
        );
        for event in ALL_EVENTS {
            assert_exhaustive(state, event);
            let declared = DISPOSITION_GRAPH_SPEC
                .transitions
                .iter()
                .find(|e| e.from == state.as_str() && e.event == event.as_str());
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(receipt.trace.policy_version, DISPOSITION_POLICY_VERSION);
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
                    assert_eq!(rej.trace.policy_version, DISPOSITION_POLICY_VERSION);
                    assert!(rej.trace.to.is_none());
                    assert!(!rej.trace.accepted);
                    if fsm.is_terminal(&state) {
                        assert_eq!(
                            rej.reason,
                            DispositionTransitionRefusal::TerminalDispositionImmutable
                        );
                    } else {
                        assert_eq!(rej.reason, DispositionTransitionRefusal::InvalidTransition);
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
    assert_eq!(observed_edges, DISPOSITION_GRAPH_SPEC.transitions.len());

    let mermaid = to_mermaid_state_diagram(&DISPOSITION_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> pending"));
    assert!(mermaid.contains("accepted --> [*]"));
    assert!(mermaid.contains("rejected --> [*]"));

    let mc = run_deterministic_model_check(
        &fsm,
        DispositionState::Pending,
        &ALL_EVENTS,
        ModelCheckConfig::default(),
        |prev, event, outcome| {
            if matches!(
                prev,
                DispositionState::Accepted | DispositionState::Rejected
            ) && outcome.is_ok()
            {
                return Err("terminal disposition must remain immutable".to_owned());
            }
            if let Ok(receipt) = outcome
                && receipt.next.is_accepted()
                && *event != DispositionEvent::Accept
            {
                return Err("only explicit Accept event may reach Accepted".to_owned());
            }
            Ok(())
        },
    )
    .expect("disposition model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0);
    assert!(mc.rejected_steps > 0);
}

#[test]
fn dispose_review_enforces_fsm_rejections_terminal_immutability_and_promotion_wiring() {
    let mut use_case =
        DisposeReview::new(InMemoryDispositionStore::default(), InMemoryPromotionGate);
    let item1 = InventoryItemId::parse("I-FSM-1").expect("id");
    let item2 = InventoryItemId::parse("I-FSM-2").expect("id");
    let ev = vec![ReviewEvidenceId::parse("E-1").expect("ev")];
    let req = PromotionRequestId::parse("PR-1").expect("req");
    let att = PromotionAttemptId::parse("PA-1").expect("att");

    // ReopenPending from Pending -> InvalidTransition
    let bad_reopen = use_case
        .transition_disposition(item1.clone(), DispositionEvent::ReopenPending, ev.clone())
        .expect_err("pending cannot reopen");
    assert_eq!(bad_reopen.kind, RejectionKind::InvalidTransition);
    assert_eq!(
        bad_reopen.reason,
        DispositionTransitionRefusal::InvalidTransition
    );

    // Pending -> Quarantined -> Quarantined (InvalidTransition) -> ReopenPending -> Accepted
    let q = use_case
        .transition_disposition(item1.clone(), DispositionEvent::Quarantine, ev.clone())
        .expect("pending -> quarantined");
    assert_eq!(q.state, DispositionState::Quarantined);
    assert_eq!(
        use_case
            .attempt_promotion(item1.clone(), req.clone(), att.clone())
            .reason,
        DispositionReason::Conflict
    );

    let bad_q = use_case
        .transition_disposition(item1.clone(), DispositionEvent::Quarantine, ev.clone())
        .expect_err("quarantined cannot quarantine again");
    assert_eq!(bad_q.kind, RejectionKind::InvalidTransition);

    let reopened = use_case
        .transition_disposition(item1.clone(), DispositionEvent::ReopenPending, ev.clone())
        .expect("quarantined -> pending");
    assert_eq!(reopened.state, DispositionState::Pending);
    assert_eq!(
        use_case
            .attempt_promotion(item1.clone(), req.clone(), att.clone())
            .reason,
        DispositionReason::Incomplete
    );

    let acc = use_case
        .transition_disposition(item1.clone(), DispositionEvent::Accept, ev.clone())
        .expect("pending -> accepted");
    assert_eq!(acc.state, DispositionState::Accepted);
    let promoted = use_case.attempt_promotion(item1.clone(), req.clone(), att.clone());
    assert_eq!(promoted.outcome, PromotionOutcome::Committed);
    assert_eq!(promoted.reason, DispositionReason::Accepted);
    assert!(promoted.commit_id.is_some());
    assert!(promoted.promotion_identity.is_some());

    // Terminal Accepted rejects both FSM events and legacy mutators (`set_pending`/`set_quarantined`).
    let rej_from_acc = use_case
        .transition_disposition(item1.clone(), DispositionEvent::Reject, ev.clone())
        .expect_err("accepted is terminal");
    assert_eq!(rej_from_acc.kind, RejectionKind::TerminalState);
    assert_eq!(
        use_case.set_pending(item1.clone(), ev.clone()).state,
        DispositionState::Accepted
    );
    assert_eq!(
        use_case.set_quarantined(item1.clone(), ev.clone()).state,
        DispositionState::Accepted
    );

    // Rejected terminal immutability + RejectedReasonCoded promotion refusal + store_set_accepted refusal.
    let rejected = use_case
        .transition_disposition(item2.clone(), DispositionEvent::Reject, ev.clone())
        .expect("pending -> rejected");
    assert_eq!(rejected.state, DispositionState::Rejected);
    let prom_rej = use_case.attempt_promotion(item2.clone(), req, att);
    assert_eq!(prom_rej.outcome, PromotionOutcome::Rejected);
    assert_eq!(prom_rej.reason, DispositionReason::RejectedReasonCoded);
    assert!(prom_rej.commit_id.is_none());

    let acc_from_rej = use_case
        .transition_disposition(item2.clone(), DispositionEvent::Accept, ev)
        .expect_err("rejected is terminal");
    assert_eq!(acc_from_rej.kind, RejectionKind::TerminalState);
    assert_eq!(
        acc_from_rej.reason,
        DispositionTransitionRefusal::TerminalDispositionImmutable
    );
    use_case.store_set_accepted(item2.clone());
    assert_eq!(
        use_case.disposition(&item2).state,
        DispositionState::Rejected
    );
}

#[test]
fn dispose_review_resists_hostile_store_and_hostile_promotion_gate() {
    let mut use_case = DisposeReview::new(HostileSpoofingStore, HostileAlwaysCommitGate);
    let item = InventoryItemId::parse("I-HOSTILE-1").expect("id");
    let ev = vec![ReviewEvidenceId::parse("E-1").expect("ev")];
    let req = PromotionRequestId::parse("PR-1").expect("req");
    let att = PromotionAttemptId::parse("PA-1").expect("att");

    // Hostile store spoofs Accepted, hostile gate returns Committed — application MUST still reject!
    use_case.set_quarantined(item.clone(), ev.clone());
    let prom = use_case.attempt_promotion(item.clone(), req, att);
    assert_eq!(prom.outcome, PromotionOutcome::Rejected);
    assert_eq!(prom.reason, DispositionReason::Conflict);
    assert!(prom.commit_id.is_none());
    assert!(prom.promotion_identity.is_none());

    // Even with a lossy store dropping writes, terminal Rejected stays immutable in-process.
    use_case
        .transition_disposition(item.clone(), DispositionEvent::Reject, ev.clone())
        .expect("quarantined -> rejected");
    let err = use_case
        .transition_disposition(item, DispositionEvent::Accept, ev)
        .expect_err("hostile/lossy store cannot undo terminal Rejected");
    assert_eq!(err.kind, RejectionKind::TerminalState);
}
