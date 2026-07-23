use ln_work::adapters::FixedDomainEvidence;
use ln_work::application::TransitionWorkState;
use ln_work::domain::{
    CheckpointId, DomainSnapshotId, LegalMappingAttempt, PublicationSnapshotId, TransitionOutcome,
    TransitionRequest, WorkEvent, WorkState, WorkUnitId, WORK_POLICY_VERSION,
};

fn unit() -> WorkUnitId {
    WorkUnitId::parse("work:W1").expect("id")
}

fn honest() -> TransitionWorkState<FixedDomainEvidence> {
    let evidence = FixedDomainEvidence::with_unit(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("id"),
        PublicationSnapshotId::parse("publication:P1").expect("id"),
    );
    let mut svc = TransitionWorkState::new(evidence);
    let _ = svc.open(unit());
    svc
}

fn start_running(svc: &mut TransitionWorkState<FixedDomainEvidence>) {
    let r = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Start,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(r.outcome, TransitionOutcome::Transitioned);
    assert_eq!(r.state, WorkState::Running);
}

#[test]
fn cancel_then_resume_keeps_domain_and_publication_unchanged() {
    let mut svc = honest();
    start_running(&mut svc);
    let domain_before = svc.domain_snapshot_of(&unit()).expect("domain");
    let pub_before = svc.publication_snapshot_of(&unit()).expect("pub");

    let cancel = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(cancel.outcome, TransitionOutcome::Transitioned);
    assert_eq!(cancel.state, WorkState::Cancelling);
    assert!(cancel.domain_unchanged);
    assert!(cancel.publication_unchanged);
    assert!(!cancel.legal_mapping_applied);
    assert_eq!(cancel.trace.policy_version, WORK_POLICY_VERSION);

    let ack = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::CancelAck,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(ack.outcome, TransitionOutcome::Transitioned);
    assert_eq!(ack.state, WorkState::Cancelled);

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
    assert_eq!(resume.domain_snapshot, domain_before);
    assert_eq!(resume.publication_snapshot, pub_before);
    assert_eq!(
        svc.domain_snapshot_of(&unit()).expect("domain"),
        domain_before
    );
    assert_eq!(
        svc.publication_snapshot_of(&unit()).expect("pub"),
        pub_before
    );
    // Checkpoint advanced; domain/publication identities did not.
    assert_ne!(
        resume.trace.prior_checkpoint.as_str(),
        resume.trace.new_checkpoint.as_str()
    );
}

#[test]
fn stale_checkpoint_is_typed_and_does_not_mutate_domain() {
    let mut svc = honest();
    start_running(&mut svc);
    let domain_before = svc.domain_snapshot_of(&unit()).expect("domain");
    let current_cp = svc
        .transition(TransitionRequest {
            work_unit_id: unit(),
            event: WorkEvent::Cancel,
            expected_checkpoint: None,
            legal_mapping: LegalMappingAttempt::None,
        })
        .checkpoint;

    let stale = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::CancelAck,
        expected_checkpoint: Some(CheckpointId::parse("cp:stale-wrong").expect("id")),
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(stale.outcome, TransitionOutcome::StaleCheckpoint);
    assert_eq!(stale.state, WorkState::Cancelling);
    assert!(stale.domain_unchanged);
    assert!(stale.publication_unchanged);
    assert_eq!(stale.domain_snapshot, domain_before);
    // State did not advance past cancelling.
    assert_eq!(svc.state_of(&unit()), Some(WorkState::Cancelling));
    // Matching checkpoint still works.
    let ack = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::CancelAck,
        expected_checkpoint: Some(current_cp),
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(ack.outcome, TransitionOutcome::Transitioned);
    assert_eq!(ack.state, WorkState::Cancelled);
}

#[test]
fn invalid_transition_is_typed_without_legal_side_effects() {
    let mut svc = honest();
    // Resume from Requested is invalid.
    let bad = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Resume,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::None,
    });
    assert_eq!(bad.outcome, TransitionOutcome::InvalidTransition);
    assert_eq!(bad.state, WorkState::Requested);
    assert!(bad.domain_unchanged);
    assert!(!bad.legal_mapping_applied);
}

#[test]
fn progress_as_legal_state_is_rejected() {
    let mut svc = honest();
    start_running(&mut svc);
    let domain_before = svc.domain_snapshot_of(&unit()).expect("domain");
    let rejected = svc.transition(TransitionRequest {
        work_unit_id: unit(),
        event: WorkEvent::Cancel,
        expected_checkpoint: None,
        legal_mapping: LegalMappingAttempt::ProgressAsLegalState,
    });
    assert_eq!(rejected.outcome, TransitionOutcome::LegalMutationRejected);
    assert_eq!(rejected.state, WorkState::Running);
    assert!(!rejected.legal_mapping_applied);
    assert_eq!(rejected.domain_snapshot, domain_before);
    assert_eq!(
        rejected.trace.legal_mapping_attempt,
        LegalMappingAttempt::ProgressAsLegalState
    );
}
