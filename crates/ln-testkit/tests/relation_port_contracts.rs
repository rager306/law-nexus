use ln_relation::adapters::{InMemoryClosedRegistry, OpenRelationHostileRegistry};
use ln_relation::domain::{EndpointId, FamilyId, PredicateId, RelationFact};
use ln_relation::ports::RelationRegistryPort;
use ln_testkit::assert_relation_registry_contract;

#[test]
fn in_memory_closed_registry_satisfies_shared_port_contract() {
    let mut registry = InMemoryClosedRegistry::with_family_a_predicate();
    assert_relation_registry_contract(&mut registry);
}

/// Shared negative surface for OpenRelationHostileRegistry.
///
/// Port-level known-predicate behavior matches the honest closed registry.
/// The hostile distinction is illicit storage of unknown predicates, tracked
/// via concrete illicit_fact_count (application policy must still reject).
#[test]
fn open_relation_hostile_registry_stores_unknown_predicates_illicitly() {
    let mut registry = OpenRelationHostileRegistry::new();
    // Known-predicate honest suite still holds for the hostile adapter.
    assert_relation_registry_contract(&mut registry);

    let unknown = PredicateId::parse("relates-to").expect("predicate");
    let subject = EndpointId::parse("E-hostile-1").expect("endpoint");
    let object = EndpointId::parse("E-hostile-2").expect("endpoint");
    let owner = FamilyId::parse("family-A").expect("family");
    let before = registry.illicit_fact_count();

    assert!(registry.try_store_fact(RelationFact {
        predicate_id: unknown.clone(),
        subject: subject.clone(),
        object: object.clone(),
        owner_family: owner,
    }));
    assert!(
        registry.contains_fact(&unknown, &subject, &object),
        "open relation hostile expected to persist unknown predicate facts"
    );
    assert!(
        registry.illicit_fact_count() > before,
        "open relation hostile expected to increment illicit_fact_count"
    );
}
