use ln_temporal::adapters::InMemoryClockEvidence;
use ln_temporal::domain::ClockKind;
use ln_testkit::assert_clock_evidence_port_contract;

#[test]
fn in_memory_clock_evidence_satisfies_shared_port_contract() {
    let evidence = InMemoryClockEvidence::with_all_except(ClockKind::SystemObservation);
    assert_clock_evidence_port_contract(&evidence);
}
