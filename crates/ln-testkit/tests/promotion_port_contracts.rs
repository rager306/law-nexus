//! Shared PromotionStorePort contracts (ADR-0015 / M146).

use ln_promote::adapters::InMemoryPromotionStore;
use ln_testkit::assert_promotion_store_contract;

#[test]
fn in_memory_promotion_store_satisfies_shared_port_contract() {
    let mut store = InMemoryPromotionStore::default();
    assert_promotion_store_contract(&mut store);
}
