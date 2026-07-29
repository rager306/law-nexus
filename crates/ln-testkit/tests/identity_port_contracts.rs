use ln_identity::adapters::{ErasingMergerHostileStore, InMemoryIdentityStore};
use ln_identity::domain::IdentityId;
use ln_testkit::{
    assert_erasing_merger_hostile_fails_honest_identity_contract, assert_identity_store_contract,
};

#[test]
fn in_memory_identity_store_satisfies_shared_port_contract() {
    let mut store = InMemoryIdentityStore::default();
    assert_identity_store_contract(&mut store);
}

#[test]
fn erasing_merger_hostile_fails_honest_identity_contract() {
    let right = IdentityId::parse("ID-contract-B").expect("identity id");
    let mut store = ErasingMergerHostileStore::targeting_right(&right);
    assert_erasing_merger_hostile_fails_honest_identity_contract(&mut store, &right);

    let result = std::panic::catch_unwind(|| {
        let right = IdentityId::parse("ID-contract-B").expect("identity id");
        let mut hostile = ErasingMergerHostileStore::targeting_right(&right);
        assert_identity_store_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "erasing merger hostile must fail the honest identity contract"
    );
}
