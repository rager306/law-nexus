use ln_diagnostic::adapters::{HostileCanarySink, InMemoryDiagnosticSink};
use ln_testkit::{
    assert_diagnostic_sink_port_contract,
    assert_hostile_canary_fails_honest_diagnostic_sink_contract,
};

#[test]
fn in_memory_diagnostic_sink_satisfies_shared_port_contract() {
    let mut sink = InMemoryDiagnosticSink::new().allow("sink:contract-allowed");
    assert_diagnostic_sink_port_contract(&mut sink);
}

#[test]
fn hostile_canary_sink_fails_honest_diagnostic_sink_contract() {
    let sink = HostileCanarySink::new();
    assert_hostile_canary_fails_honest_diagnostic_sink_contract(&sink);

    let result = std::panic::catch_unwind(|| {
        let mut hostile = HostileCanarySink::new();
        assert_diagnostic_sink_port_contract(&mut hostile);
    });
    assert!(
        result.is_err(),
        "hostile canary sink must fail the honest diagnostic sink contract"
    );
}
