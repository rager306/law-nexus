use ln_relation::{
    adapters::InMemoryClosedRegistry,
    application::ValidateRelation,
    domain::{
        EndpointId, EvidenceRef, FamilyId, PredicateId, RelationOutcome, RelationProposal,
        C13_GATE_VERSION, DEFAULT_REGISTRY_VERSION,
    },
};

fn use_case() -> ValidateRelation<InMemoryClosedRegistry> {
    ValidateRelation::new(InMemoryClosedRegistry::with_family_a_predicate())
}

#[test]
fn unknown_predicate_is_rejected_and_not_stored() {
    let mut gate = use_case();
    let before = gate.registered_count();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("relates-to").expect("valid"),
        subject: EndpointId::parse("E1").expect("valid"),
        object: EndpointId::parse("E2").expect("valid"),
        proposed_owner: FamilyId::parse("family-A").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("valid")],
    });

    assert_eq!(result.outcome, RelationOutcome::UnknownPredicate);
    assert!(result.registry_unchanged);
    assert!(!result.stored_as_fact);
    assert!(!result.exposed_as_query_fact);
    assert_eq!(gate.registered_count(), before);
    assert_eq!(gate.accepted_fact_count(), 0);
    assert!(!gate.query_has_fact(
        &PredicateId::parse("relates-to").expect("valid"),
        &EndpointId::parse("E1").expect("valid"),
        &EndpointId::parse("E2").expect("valid"),
    ));
    assert_eq!(result.c13_version, C13_GATE_VERSION);
    assert_eq!(result.registry_version.as_str(), DEFAULT_REGISTRY_VERSION);
    assert!(result.input_chain_digest.as_str().starts_with("fnv1a64:"));
}

#[test]
fn wrong_owner_predicate_is_rejected_and_not_stored() {
    let mut gate = use_case();
    let before = gate.registered_count();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("valid"),
        subject: EndpointId::parse("E1").expect("valid"),
        object: EndpointId::parse("E2").expect("valid"),
        // family-B tries to emit family-A owned predicate
        proposed_owner: FamilyId::parse("family-B").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("valid")],
    });

    assert_eq!(result.outcome, RelationOutcome::WrongOwner);
    assert!(result.registry_unchanged);
    assert!(!result.stored_as_fact);
    assert!(!result.exposed_as_query_fact);
    assert_eq!(gate.registered_count(), before);
    assert_eq!(gate.accepted_fact_count(), 0);
    assert!(!gate.query_has_fact(
        &PredicateId::parse("amends").expect("valid"),
        &EndpointId::parse("E1").expect("valid"),
        &EndpointId::parse("E2").expect("valid"),
    ));
}

#[test]
fn correct_owner_with_evidence_is_accepted_as_fact() {
    let mut gate = use_case();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("valid"),
        subject: EndpointId::parse("E1").expect("valid"),
        object: EndpointId::parse("E2").expect("valid"),
        proposed_owner: FamilyId::parse("family-A").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("valid")],
    });

    assert_eq!(result.outcome, RelationOutcome::Accepted);
    assert!(result.registry_unchanged);
    assert!(result.stored_as_fact);
    assert!(result.exposed_as_query_fact);
    assert_eq!(gate.accepted_fact_count(), 1);
    assert!(gate.query_has_fact(
        &PredicateId::parse("amends").expect("valid"),
        &EndpointId::parse("E1").expect("valid"),
        &EndpointId::parse("E2").expect("valid"),
    ));
}
