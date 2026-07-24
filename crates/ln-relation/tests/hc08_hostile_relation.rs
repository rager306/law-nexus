use ln_relation::{
    adapters::OpenRelationHostileRegistry,
    application::ValidateRelation,
    domain::{EndpointId, EvidenceRef, FamilyId, PredicateId, RelationOutcome, RelationProposal},
};

fn use_case() -> ValidateRelation<OpenRelationHostileRegistry> {
    ValidateRelation::new(OpenRelationHostileRegistry::new())
}

#[test]
fn hostile_store_does_not_receive_unknown_predicate_writes() {
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
}

#[test]
fn hostile_store_does_not_receive_wrong_owner_writes() {
    let mut gate = use_case();
    let result = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("valid"),
        subject: EndpointId::parse("E1").expect("valid"),
        object: EndpointId::parse("E2").expect("valid"),
        proposed_owner: FamilyId::parse("family-B").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("valid")],
    });
    assert_eq!(result.outcome, RelationOutcome::WrongOwner);
    assert!(!result.stored_as_fact);
    assert!(!result.exposed_as_query_fact);
    assert_eq!(gate.accepted_fact_count(), 0);
    assert!(!gate.query_has_fact(
        &PredicateId::parse("amends").expect("valid"),
        &EndpointId::parse("E1").expect("valid"),
        &EndpointId::parse("E2").expect("valid"),
    ));
}

#[test]
fn application_query_exposes_only_accepted_facts_against_hostile_store() {
    let mut gate = use_case();
    // Rejections first.
    let _ = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("relates-to").expect("valid"),
        subject: EndpointId::parse("E9").expect("valid"),
        object: EndpointId::parse("E9b").expect("valid"),
        proposed_owner: FamilyId::parse("family-A").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EVX").expect("valid")],
    });
    let _ = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("valid"),
        subject: EndpointId::parse("E8").expect("valid"),
        object: EndpointId::parse("E8b").expect("valid"),
        proposed_owner: FamilyId::parse("family-B").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EVY").expect("valid")],
    });
    // Then one accepted fact.
    let accepted = gate.validate(RelationProposal {
        predicate_id: PredicateId::parse("amends").expect("valid"),
        subject: EndpointId::parse("E1").expect("valid"),
        object: EndpointId::parse("E2").expect("valid"),
        proposed_owner: FamilyId::parse("family-A").expect("valid"),
        evidence_refs: vec![EvidenceRef::parse("EV1").expect("valid")],
    });
    assert_eq!(accepted.outcome, RelationOutcome::Accepted);
    assert!(accepted.exposed_as_query_fact);
    assert_eq!(gate.accepted_fact_count(), 1);
    assert!(gate.query_has_fact(
        &PredicateId::parse("amends").expect("valid"),
        &EndpointId::parse("E1").expect("valid"),
        &EndpointId::parse("E2").expect("valid"),
    ));
    // Rejected proposals remain absent from application query surface.
    assert!(!gate.query_has_fact(
        &PredicateId::parse("relates-to").expect("valid"),
        &EndpointId::parse("E9").expect("valid"),
        &EndpointId::parse("E9b").expect("valid"),
    ));
    assert!(!gate.query_has_fact(
        &PredicateId::parse("amends").expect("valid"),
        &EndpointId::parse("E8").expect("valid"),
        &EndpointId::parse("E8b").expect("valid"),
    ));
}
