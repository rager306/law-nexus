use ln_gate::{
    adapters::InPlaceMutatingHostileStore,
    application::GateLifecycle,
    domain::{CandidateId, EvidenceRef, GateOutcome, GateReason, GateRequest, LifecycleType},
};

fn seed_hostile() -> (GateLifecycle<InPlaceMutatingHostileStore>, CandidateId) {
    let mut gate = GateLifecycle::new(InPlaceMutatingHostileStore::default());
    let id = CandidateId::parse("C1").expect("valid");
    gate.seed_extracted(id.clone(), Vec::new());
    (gate, id)
}

#[test]
fn hostile_store_cannot_rewrite_original_type_on_seed() {
    let (gate, id) = seed_hostile();
    let stored = gate.get(&id).expect("seeded");
    assert_eq!(stored.lifecycle_type, LifecycleType::ExtractedCandidate);
}

#[test]
fn hostile_store_cannot_force_verified_via_confidence_only() {
    let (mut gate, id) = seed_hostile();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 99,
        evidence_refs: Vec::new(),
        in_place: false,
    });
    assert_eq!(result.outcome, GateOutcome::InsufficientEvidence);
    assert_eq!(result.reason, GateReason::ConfidenceOnly);
    assert_eq!(result.resulting_type, LifecycleType::ExtractedCandidate);
    assert_eq!(
        gate.get(&id).expect("original").lifecycle_type,
        LifecycleType::ExtractedCandidate
    );
}

#[test]
fn hostile_store_cannot_force_in_place_mutation() {
    let (mut gate, id) = seed_hostile();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 50,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("valid")],
        in_place: true,
    });
    assert_eq!(result.outcome, GateOutcome::InvalidTransition);
    assert_eq!(result.reason, GateReason::InPlaceMutation);
    assert_eq!(
        gate.get(&id).expect("original").lifecycle_type,
        LifecycleType::ExtractedCandidate
    );
}

#[test]
fn accepted_path_still_mints_new_identity_against_hostile_store() {
    let (mut gate, id) = seed_hostile();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 10,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("valid")],
        in_place: false,
    });
    assert_eq!(result.outcome, GateOutcome::AcceptedNewOutcome);
    assert_ne!(result.resulting_id, id);
    assert_eq!(
        gate.get(&id).expect("original").lifecycle_type,
        LifecycleType::ExtractedCandidate
    );
    assert_eq!(
        gate.get(&result.resulting_id)
            .expect("minted")
            .lifecycle_type,
        LifecycleType::VerifiedAssertion
    );
}
