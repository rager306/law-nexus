use ln_fsm::graph::{to_mermaid_state_diagram, validate_graph};
use ln_fsm::model_check::{ModelCheckConfig, run_deterministic_model_check};
use ln_fsm::{DeterministicFsm, RejectionKind};
use ln_gate::adapters::InMemoryCandidateStore;
use ln_gate::application::GateLifecycle;
use ln_gate::domain::{
    C10_GATE_VERSION, CandidateId, EvidenceRef, GATE_LIFECYCLE_GRAPH_SPEC, GateLifecycleEvent,
    GateLifecycleFsm, GateOutcome, GateReason, GateRequest, GateTransitionRefusal, LifecycleType,
};

const ALL_STATES: [LifecycleType; 2] = [
    LifecycleType::ExtractedCandidate,
    LifecycleType::VerifiedAssertion,
];

const GRAPH_EVENTS: [GateLifecycleEvent; 2] = [
    GateLifecycleEvent::PromoteToVerified {
        in_place: false,
        has_evidence: true,
        confidence: 10,
    },
    GateLifecycleEvent::DemoteToExtracted,
];

const MODEL_CHECK_EVENTS: [GateLifecycleEvent; 5] = [
    GateLifecycleEvent::PromoteToVerified {
        in_place: false,
        has_evidence: true,
        confidence: 10,
    },
    GateLifecycleEvent::PromoteToVerified {
        in_place: true,
        has_evidence: true,
        confidence: 100,
    },
    GateLifecycleEvent::PromoteToVerified {
        in_place: false,
        has_evidence: false,
        confidence: 90,
    },
    GateLifecycleEvent::PromoteToVerified {
        in_place: false,
        has_evidence: false,
        confidence: 89,
    },
    GateLifecycleEvent::DemoteToExtracted,
];

fn assert_exhaustive(state: LifecycleType, event: GateLifecycleEvent) {
    match state {
        LifecycleType::ExtractedCandidate | LifecycleType::VerifiedAssertion => {}
    }
    match event {
        GateLifecycleEvent::PromoteToVerified {
            in_place: _,
            has_evidence: _,
            confidence: _,
        }
        | GateLifecycleEvent::DemoteToExtracted => {}
    }
}

#[test]
fn gate_lifecycle_graph_spec_is_valid_bijective_guards_and_model_checked() {
    let report =
        validate_graph(&GATE_LIFECYCLE_GRAPH_SPEC).expect("gate lifecycle graph must validate");
    assert_eq!(report.state_count, ALL_STATES.len());
    assert_eq!(report.reachable_count, ALL_STATES.len());
    assert_eq!(report.terminal_count, 1);

    let fsm = GateLifecycleFsm;
    let mut observed_edges = 0usize;
    for state in ALL_STATES {
        assert_eq!(
            fsm.is_terminal(&state),
            GATE_LIFECYCLE_GRAPH_SPEC
                .terminals
                .contains(&state.as_str())
        );
        for event in GRAPH_EVENTS {
            assert_exhaustive(state, event);
            let declared = GATE_LIFECYCLE_GRAPH_SPEC
                .transitions
                .iter()
                .find(|e| e.from == state.as_str() && e.event == event.as_str());
            match (fsm.apply(state, event), declared) {
                (Ok(receipt), Some(edge)) => {
                    assert_eq!(receipt.next.as_str(), edge.to);
                    assert_eq!(receipt.trace.policy_version, C10_GATE_VERSION);
                    assert!(receipt.trace.accepted);
                    observed_edges += 1;
                }
                (Err(rej), None) => {
                    let expected_kind = if fsm.is_terminal(&state) {
                        RejectionKind::TerminalState
                    } else {
                        RejectionKind::InvalidTransition
                    };
                    let expected_reason = if fsm.is_terminal(&state) {
                        GateTransitionRefusal::TerminalLifecycleImmutable
                    } else {
                        GateTransitionRefusal::InvalidLifecycleTransition
                    };
                    assert_eq!(rej.kind, expected_kind);
                    assert_eq!(rej.reason, expected_reason);
                    assert_eq!(rej.trace.policy_version, C10_GATE_VERSION);
                    assert!(rej.trace.to.is_none());
                    assert!(!rej.trace.accepted);
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
    assert_eq!(observed_edges, GATE_LIFECYCLE_GRAPH_SPEC.transitions.len());

    // C10 guard checks including exact `>= 90` / `89` confidence boundary.
    let in_place_rej = fsm
        .apply(
            LifecycleType::ExtractedCandidate,
            GateLifecycleEvent::PromoteToVerified {
                in_place: true,
                has_evidence: true,
                confidence: 100,
            },
        )
        .expect_err("in-place mutation must fail guard");
    assert_eq!(in_place_rej.kind, RejectionKind::GuardRejected);
    assert_eq!(in_place_rej.reason, GateTransitionRefusal::InPlaceMutation);

    let conf_90_rej = fsm
        .apply(
            LifecycleType::ExtractedCandidate,
            GateLifecycleEvent::PromoteToVerified {
                in_place: false,
                has_evidence: false,
                confidence: 90,
            },
        )
        .expect_err("confidence == 90 without evidence must fail as ConfidenceOnly");
    assert_eq!(conf_90_rej.kind, RejectionKind::GuardRejected);
    assert_eq!(conf_90_rej.reason, GateTransitionRefusal::ConfidenceOnly);

    let conf_89_rej = fsm
        .apply(
            LifecycleType::ExtractedCandidate,
            GateLifecycleEvent::PromoteToVerified {
                in_place: false,
                has_evidence: false,
                confidence: 89,
            },
        )
        .expect_err("confidence == 89 without evidence must fail as MissingEvidenceChain");
    assert_eq!(conf_89_rej.kind, RejectionKind::GuardRejected);
    assert_eq!(
        conf_89_rej.reason,
        GateTransitionRefusal::MissingEvidenceChain
    );

    let mermaid = to_mermaid_state_diagram(&GATE_LIFECYCLE_GRAPH_SPEC);
    assert!(mermaid.contains("[*] --> extracted-candidate"));
    assert!(mermaid.contains("verified-assertion --> [*]"));

    let mc = run_deterministic_model_check(
        &fsm,
        LifecycleType::ExtractedCandidate,
        &MODEL_CHECK_EVENTS,
        ModelCheckConfig::default(),
        |prev, event, outcome| {
            if let Ok(receipt) = outcome {
                if *prev == LifecycleType::VerifiedAssertion {
                    return Err("VerifiedAssertion must remain terminal".to_owned());
                }
                let valid = matches!(
                    event,
                    GateLifecycleEvent::PromoteToVerified {
                        in_place: false,
                        has_evidence: true,
                        ..
                    }
                ) && receipt.next == LifecycleType::VerifiedAssertion;
                if !valid {
                    return Err(format!(
                        "C10 violation: unexpected accepted transition {:?} -> {:?}",
                        event, receipt.next
                    ));
                }
            }
            Ok(())
        },
    )
    .expect("gate lifecycle model check must pass");
    assert_eq!(mc.sequences_run, 256);
    assert!(mc.accepted_steps > 0);
    assert!(mc.rejected_steps > 0);
}

#[test]
fn gate_lifecycle_application_rejects_demotion_repromotion_and_low_confidence_missing_evidence() {
    let mut gate = GateLifecycle::new(InMemoryCandidateStore::default());
    let id = CandidateId::parse("C-FSM-1").expect("id");
    gate.seed_extracted(id.clone(), Vec::new());

    // 1. Low-confidence empty evidence (< 90) -> InsufficientEvidence / MissingEvidenceChain.
    let low_conf = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 89,
        evidence_refs: Vec::new(),
        in_place: false,
    });
    assert_eq!(low_conf.outcome, GateOutcome::InsufficientEvidence);
    assert_eq!(low_conf.reason, GateReason::MissingEvidenceChain);
    assert!(!low_conf.confidence_used_as_authority);
    assert_eq!(low_conf.resulting_id, id);

    // 2. Self-transition ExtractedCandidate -> ExtractedCandidate fails closed without minting.
    let self_demote = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::ExtractedCandidate,
        confidence: 10,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("ev")],
        in_place: false,
    });
    assert_eq!(self_demote.outcome, GateOutcome::InvalidTransition);
    assert_eq!(self_demote.reason, GateReason::InvalidLifecycleTransition);
    assert_eq!(self_demote.resulting_id, id);

    // 3. Valid promotion mints immutable VerifiedAssertion (:v1).
    let promoted = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 50,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("ev")],
        in_place: false,
    });
    assert_eq!(promoted.outcome, GateOutcome::AcceptedNewOutcome);
    let verified_id = promoted.resulting_id.clone();

    // 4. Demoting VerifiedAssertion fails closed as TerminalLifecycleImmutable (NOT InPlaceMutation).
    let demote_verified = gate.request_transition(GateRequest {
        candidate_id: verified_id.clone(),
        requested_type: LifecycleType::ExtractedCandidate,
        confidence: 50,
        evidence_refs: vec![EvidenceRef::parse("E2").expect("ev")],
        in_place: false,
    });
    assert_eq!(demote_verified.outcome, GateOutcome::InvalidTransition);
    assert_eq!(
        demote_verified.reason,
        GateReason::TerminalLifecycleImmutable
    );
    assert_eq!(demote_verified.resulting_id, verified_id);
    assert_eq!(
        demote_verified.resulting_type,
        LifecycleType::VerifiedAssertion
    );
    assert_eq!(demote_verified.predecessor.as_ref(), Some(&id));

    // 5. Re-promoting already-VerifiedAssertion fails closed without minting :v2.
    let repromote = gate.request_transition(GateRequest {
        candidate_id: verified_id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 99,
        evidence_refs: vec![EvidenceRef::parse("E3").expect("ev")],
        in_place: false,
    });
    assert_eq!(repromote.outcome, GateOutcome::InvalidTransition);
    assert_eq!(repromote.reason, GateReason::TerminalLifecycleImmutable);
    assert_eq!(repromote.resulting_id, verified_id);
    assert_eq!(
        gate.get(&verified_id).expect("stored").lifecycle_type,
        LifecycleType::VerifiedAssertion
    );
}
