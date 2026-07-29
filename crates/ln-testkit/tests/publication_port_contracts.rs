use ln_publish::adapters::{HostileDualWriterLedger, InMemoryPublicationLedger};
use ln_testkit::{
    assert_hostile_dual_writer_fails_honest_publication_contract,
    assert_publication_ledger_contract,
};

#[test]
fn in_memory_publication_ledger_satisfies_shared_port_contract() {
    let mut ledger = InMemoryPublicationLedger::new();
    assert_publication_ledger_contract(&mut ledger);
}

#[test]
fn hostile_dual_writer_fails_honest_publication_contract() {
    let mut ledger = HostileDualWriterLedger::new();
    assert_hostile_dual_writer_fails_honest_publication_contract(&mut ledger);

    let result = std::panic::catch_unwind(|| {
        let mut hostile = HostileDualWriterLedger::new();
        assert_publication_ledger_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "hostile dual-writer must fail the honest publication ledger contract"
    );
}
