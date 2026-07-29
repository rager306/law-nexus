use ln_replay::adapters::{
    HostileDuplicateEffectLedger, InMemoryCheckpointStore, InMemoryEffectLedger,
};
use ln_testkit::{
    assert_checkpoint_port_contract, assert_effect_ledger_port_contract,
    assert_hostile_duplicate_effect_ledger_fails_honest_contract, contract_sample_checkpoint,
};

#[test]
fn in_memory_checkpoint_store_satisfies_shared_port_contract() {
    let store = InMemoryCheckpointStore::new().insert(contract_sample_checkpoint());
    assert_checkpoint_port_contract(&store);
}

#[test]
fn in_memory_effect_ledger_satisfies_shared_port_contract() {
    let mut ledger = InMemoryEffectLedger::new();
    assert_effect_ledger_port_contract(&mut ledger);
}

#[test]
fn hostile_duplicate_effect_ledger_fails_honest_contract() {
    let mut ledger = HostileDuplicateEffectLedger::new();
    assert_hostile_duplicate_effect_ledger_fails_honest_contract(&mut ledger);

    let result = std::panic::catch_unwind(|| {
        let mut hostile = HostileDuplicateEffectLedger::new();
        assert_effect_ledger_port_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "hostile duplicate effect ledger must fail the honest effect ledger contract"
    );
}
