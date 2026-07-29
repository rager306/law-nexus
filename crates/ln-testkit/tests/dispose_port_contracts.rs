use ln_dispose::adapters::{InMemoryDispositionStore, InMemoryPromotionGate};
use ln_testkit::{assert_disposition_store_contract, assert_promotion_gate_port_contract};

#[test]
fn in_memory_disposition_store_satisfies_shared_port_contract() {
    let mut store = InMemoryDispositionStore::default();
    assert_disposition_store_contract(&mut store);
}

#[test]
fn in_memory_promotion_gate_satisfies_shared_port_contract() {
    let mut gate = InMemoryPromotionGate;
    assert_promotion_gate_port_contract(&mut gate);
}
