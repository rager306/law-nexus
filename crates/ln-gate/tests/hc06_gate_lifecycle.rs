use ln_gate::{
    adapters::InMemoryCandidateStore,
    application::GateLifecycle,
    domain::{
        CandidateId, EvidenceRef, GateOutcome, GateReason, GateRequest, LifecycleType,
        C10_GATE_VERSION,
    },
};

fn seed() -> (GateLifecycle<InMemoryCandidateStore>, CandidateId) {
    let mut gate = GateLifecycle::new(InMemoryCandidateStore::default());
    let id = CandidateId::parse("C1").expect("valid");
    gate.seed_extracted(id.clone(), Vec::new());
    (gate, id)
}

#[test]
fn confidence_only_request_is_rejected_and_type_unchanged() {
    let (mut gate, id) = seed();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 99,
        evidence_refs: Vec::new(),
        in_place: false,
    });

    assert_eq!(result.outcome, GateOutcome::InsufficientEvidence);
    assert_eq!(result.reason, GateReason::ConfidenceOnly);
    assert_eq!(result.original_type, LifecycleType::ExtractedCandidate);
    assert_eq!(result.resulting_type, LifecycleType::ExtractedCandidate);
    assert_eq!(result.resulting_id, id);
    assert!(result.confidence_used_as_authority);
    assert_eq!(result.gate_version.as_str(), C10_GATE_VERSION);
    assert!(result.predecessor.is_none());

    let stored = gate.get(&id).expect("still stored");
    assert_eq!(stored.lifecycle_type, LifecycleType::ExtractedCandidate);
}

#[test]
fn in_place_type_change_is_invalid_transition() {
    let (mut gate, id) = seed();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 10,
        evidence_refs: vec![EvidenceRef::parse("E1").expect("valid")],
        in_place: true,
    });

    assert_eq!(result.outcome, GateOutcome::InvalidTransition);
    assert_eq!(result.reason, GateReason::InPlaceMutation);
    assert_eq!(result.resulting_id, id);
    assert_eq!(result.resulting_type, LifecycleType::ExtractedCandidate);

    let stored = gate.get(&id).expect("still stored");
    assert_eq!(stored.lifecycle_type, LifecycleType::ExtractedCandidate);
}

#[test]
fn accepted_path_mints_new_immutable_outcome_with_predecessor() {
    let (mut gate, id) = seed();
    let result = gate.request_transition(GateRequest {
        candidate_id: id.clone(),
        requested_type: LifecycleType::VerifiedAssertion,
        confidence: 10,
        evidence_refs: vec![
            EvidenceRef::parse("E1").expect("valid"),
            EvidenceRef::parse("E2").expect("valid"),
        ],
        in_place: false,
    });

    assert_eq!(result.outcome, GateOutcome::AcceptedNewOutcome);
    assert_eq!(result.reason, GateReason::EvidenceChainSatisfied);
    assert_ne!(result.resulting_id, id);
    assert_eq!(result.resulting_type, LifecycleType::VerifiedAssertion);
    assert_eq!(result.predecessor.as_ref(), Some(&id));
    assert!(!result.confidence_used_as_authority);
    assert!(result.input_chain_digest.as_str().starts_with("fnv1a64:"));

    // Original identity/type remains unchanged.
    let original = gate.get(&id).expect("original remains");
    assert_eq!(original.lifecycle_type, LifecycleType::ExtractedCandidate);
    assert!(original.predecessor.is_none());

    let minted = gate.get(&result.resulting_id).expect("new outcome stored");
    assert_eq!(minted.lifecycle_type, LifecycleType::VerifiedAssertion);
    assert_eq!(minted.predecessor.as_ref(), Some(&id));
}
