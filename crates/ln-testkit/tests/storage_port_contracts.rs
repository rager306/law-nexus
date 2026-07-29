//! Shared storage port contracts exercised against InMemory adapters (ADR-0015).

use ln_storage::adapters::in_memory::{InMemoryGraphStore, InMemoryVectorStore};
use ln_testkit::{assert_graph_store_contract, assert_vector_store_contract};

#[test]
fn in_memory_vector_store_satisfies_shared_port_contract() {
    let mut store = InMemoryVectorStore::new();
    assert_vector_store_contract(&mut store);
}

#[test]
fn in_memory_graph_store_satisfies_shared_port_contract() {
    let mut store = InMemoryGraphStore::new();
    assert_graph_store_contract(&mut store);
}
