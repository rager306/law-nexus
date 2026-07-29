use ln_publish::adapters::InMemoryPublicationLedger;
use ln_testkit::assert_publication_ledger_contract;

#[test]
fn in_memory_publication_ledger_satisfies_shared_port_contract() {
    let mut ledger = InMemoryPublicationLedger::new();
    assert_publication_ledger_contract(&mut ledger);
}
