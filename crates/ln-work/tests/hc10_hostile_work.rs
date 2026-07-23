use ln_work::adapters::HostileMutatingEvidence;
use ln_work::application::TransitionWorkState;
use ln_work::domain::{
    DomainSnapshotId, LegalMappingAttempt, PublicationSnapshotId, TransitionOutcome,
    TransitionRequest, WorkEvent, WorkState, WorkUnitId,
};
use ln_work::ports::HostileLegalSideChannel;

fn unit() -> WorkUnitId {
    WorkUnitId::parse("work:W1").expect("id")
}

fn hostile_svc() -> (
    TransitionWorkState<HostileMutatingEvidence>,
    HostileMutatingEvidence,
) {
    let evidence = HostileMutatingEvidence::new(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("id"),
        PublicationSnapshotId::parse("publication:P1").expect("id"),
    );
    // Clone-like second handle via re-construct is not available; keep one service.
    // Side-channel claims go through the evidence inside the service, so we also
    // keep a parallel instance for claim counters after transitions via re-open pattern.
    let evidence_for_claims = HostileMutatingEvidence::new(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("id"),
        PublicationSnapshotId::parse("publication:P1").expect("id"),
    );
    let mut svc = TransitionWorkState::new(evidence);
    let _ = svc.open(unit());
    let _ = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Start,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    (svc, evidence_for_claims)
}

#[test]
fn hostile_adapter_cannot_rewrite_frozen_domain_on_cancel_resume() {
    let (mut svc, _) = hostile_svc();
    let domain_before = svc.domain_snapshot_of(&unit()).expect("domain");
    assert_eq!(domain_before.as_str(), "domain:D1");

    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(cancel.outcome, TransitionOutcome::Transitioned);
    assert_eq!(cancel.state, WorkState::Cancelling);
    assert!(cancel.domain_unchanged);
    assert_eq!(cancel.domain_snapshot.as_str(), "domain:D1");

    let ack = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::CancelAck,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(ack.outcome, TransitionOutcome::Transitioned);
    assert_eq!(ack.state, WorkState::Cancelled);
    assert_eq!(ack.domain_snapshot.as_str(), "domain:D1");

    let resume = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Resume,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(resume.outcome, TransitionOutcome::Transitioned);
    assert_eq!(resume.state, WorkState::Running);
    assert!(resume.domain_unchanged);
    assert!(resume.publication_unchanged);
    assert_eq!(resume.domain_snapshot.as_str(), "domain:D1");
    assert_eq!(
        svc.domain_snapshot_of(&unit()).expect("domain").as_str(),
        "domain:D1"
    );
}

#[test]
fn all_forbidden_legal_mappings_are_rejected_without_state_change() {
    let (mut svc, _) = hostile_svc();
    let domain_before = svc.domain_snapshot_of(&unit()).expect("domain");
    let forbidden = [
        LegalMappingAttempt::ProgressAsVerified,
        LegalMappingAttempt::ProgressAsCurrent,
        LegalMappingAttempt::ProgressAsLegalState,
        LegalMappingAttempt::MutateLifecycle,
        LegalMappingAttempt::MutateClock,
        LegalMappingAttempt::MutateIdentity,
        LegalMappingAttempt::MutateRelation,
        LegalMappingAttempt::MutateAuthority,
    ];
    for attempt in forbidden {
        let r = svc.transition(TransitionRequest {
            work_unit_id: unit(),
            event: WorkEvent::Cancel,
            expected_checkpoint: None,
            legal_mapping: attempt,
        });
        assert_eq!(
            r.outcome,
            TransitionOutcome::LegalMutationRejected,
            "attempt {:?}",
            attempt
        );
        assert_eq!(r.state, WorkState::Running);
        assert!(!r.legal_mapping_applied);
        assert!(r.domain_unchanged);
        assert_eq!(r.domain_snapshot, domain_before);
        assert_eq!(r.trace.legal_mapping_attempt, attempt);
    }
    // After all rejections, cancel without mapping still works.
    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(cancel.outcome, TransitionOutcome::Transitioned);
    assert_eq!(cancel.state, WorkState::Cancelling);
    assert_eq!(cancel.domain_snapshot, domain_before);
}

#[test]
fn side_channel_legal_mutation_claims_do_not_apply_to_application_state() {
    let evidence = HostileMutatingEvidence::new(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("id"),
        PublicationSnapshotId::parse("publication:P1").expect("id"),
    );
    evidence.claim_mutation();
    evidence.claim_mutation();
    assert_eq!(evidence.claimed_legal_mutations(), 2);

    let mut svc = TransitionWorkState::new(evidence);
    let _ = svc.open(unit());
    let _ = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Start,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    let r = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::MutateAuthority,
    });
    assert_eq!(r.outcome, TransitionOutcome::LegalMutationRejected);
    assert!(!r.legal_mapping_applied);
    assert_eq!(r.domain_snapshot.as_str(), "domain:D1");
    assert_eq!(r.publication_snapshot.as_str(), "publication:P1");
    assert_eq!(svc.state_of(&unit()), Some(WorkState::Running));
}
