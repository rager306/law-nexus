use ln_inventory::adapters::{InMemoryInventoryStore, InMemoryVisibilityView};
use ln_testkit::{assert_inventory_store_contract, assert_visibility_port_contract};

#[test]
fn in_memory_inventory_store_satisfies_shared_port_contract() {
    let mut store = InMemoryInventoryStore::default();
    assert_inventory_store_contract(&mut store);
}

#[test]
fn in_memory_visibility_view_satisfies_shared_port_contract() {
    assert_visibility_port_contract(&InMemoryVisibilityView);
}
