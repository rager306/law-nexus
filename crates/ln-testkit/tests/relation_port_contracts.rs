use ln_relation::adapters::InMemoryClosedRegistry;
use ln_testkit::assert_relation_registry_contract;

#[test]
fn in_memory_closed_registry_satisfies_shared_port_contract() {
    let mut registry = InMemoryClosedRegistry::with_family_a_predicate();
    assert_relation_registry_contract(&mut registry);
}
