use ln_observe::adapters::{InMemoryDiagnosticSink, InMemoryWorkState};
use ln_testkit::{assert_observe_diagnostic_port_contract, assert_work_state_contract};

#[test]
fn in_memory_work_state_satisfies_shared_port_contract() {
    let mut state = InMemoryWorkState::default();
    assert_work_state_contract(&mut state);
}

#[test]
fn observe_in_memory_diagnostic_sink_satisfies_shared_port_contract() {
    let mut sink = InMemoryDiagnosticSink::default();
    assert_observe_diagnostic_port_contract(&mut sink);
}
