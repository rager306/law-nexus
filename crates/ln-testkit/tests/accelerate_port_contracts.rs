use ln_accelerate::adapters::{HostileLabelMutatorLedger, InMemoryAccelerationLedger};
use ln_testkit::{
    assert_acceleration_ledger_contract,
    assert_hostile_label_mutator_fails_honest_acceleration_contract,
};

#[test]
fn in_memory_acceleration_ledger_satisfies_shared_port_contract() {
    let mut ledger = InMemoryAccelerationLedger::new();
    assert_acceleration_ledger_contract(&mut ledger);
}

#[test]
fn hostile_label_mutator_fails_honest_acceleration_contract() {
    let mut ledger = HostileLabelMutatorLedger::new();
    assert_hostile_label_mutator_fails_honest_acceleration_contract(&mut ledger);

    let result = std::panic::catch_unwind(|| {
        let mut hostile = HostileLabelMutatorLedger::new();
        assert_acceleration_ledger_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "hostile label mutator must fail the honest acceleration contract"
    );
}
