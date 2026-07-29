use ln_decode::adapters::{
    HonestSyntheticDecoder, InMemoryDiagnosticSink, MaliciousSyntheticDecoder,
};
use ln_testkit::{
    assert_decode_diagnostic_port_contract, assert_decoder_port_contract,
    assert_malicious_decoder_fails_honest_contract,
};

#[test]
fn honest_synthetic_decoder_satisfies_shared_port_contract() {
    assert_decoder_port_contract(&HonestSyntheticDecoder);
}

#[test]
fn malicious_synthetic_decoder_fails_honest_decoder_contract() {
    assert_malicious_decoder_fails_honest_contract(&MaliciousSyntheticDecoder);

    let result = std::panic::catch_unwind(|| {
        assert_decoder_port_contract(&MaliciousSyntheticDecoder);
    });
    assert!(
        result.is_err(),
        "malicious decoder must fail the honest decoder contract"
    );
}

#[test]
fn decode_in_memory_diagnostic_sink_satisfies_shared_port_contract() {
    let mut sink = InMemoryDiagnosticSink::new();
    assert_decode_diagnostic_port_contract(&mut sink);
}
