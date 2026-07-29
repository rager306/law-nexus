use ln_query::adapters::{HostileGapInventorState, InMemoryQueryState};
use ln_testkit::{
    assert_hostile_gap_inventor_fails_honest_query_contract, assert_query_state_contract,
};

#[test]
fn in_memory_query_state_satisfies_shared_port_contract() {
    let state = InMemoryQueryState::new().with_evidence("ev:contract-known");
    assert_query_state_contract(&state);
}

#[test]
fn hostile_gap_inventor_fails_honest_query_contract() {
    let state = HostileGapInventorState::new().with_evidence("ev:contract-known");
    assert_hostile_gap_inventor_fails_honest_query_contract(&state);

    // And the honest suite must not accept the hostile adapter.
    let result = std::panic::catch_unwind(|| {
        assert_query_state_contract(&state);
    });
    assert!(
        result.is_err(),
        "hostile gap inventor must fail the honest query contract"
    );
}
