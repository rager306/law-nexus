use ln_gate::adapters::{InMemoryCandidateStore, InPlaceMutatingHostileStore};
use ln_testkit::{
    assert_candidate_store_contract,
    assert_inplace_mutating_hostile_fails_honest_candidate_contract,
};

#[test]
fn in_memory_candidate_store_satisfies_shared_port_contract() {
    let mut store = InMemoryCandidateStore::default();
    assert_candidate_store_contract(&mut store);
}

#[test]
fn inplace_mutating_hostile_fails_honest_candidate_contract() {
    let mut store = InPlaceMutatingHostileStore::default();
    assert_inplace_mutating_hostile_fails_honest_candidate_contract(&mut store);

    let result = std::panic::catch_unwind(|| {
        let mut hostile = InPlaceMutatingHostileStore::default();
        assert_candidate_store_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "inplace mutating hostile must fail the honest candidate contract"
    );
}
