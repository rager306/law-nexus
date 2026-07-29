use ln_decode::adapters::{
    HonestSyntheticDecoder, InMemoryDiagnosticSink, MaliciousSyntheticDecoder,
    WordMLStreamingDecoder,
};
use ln_testkit::{
    assert_decode_diagnostic_port_contract, assert_decoder_port_contract,
    assert_decoder_port_contract_with_fixture, assert_malicious_decoder_fails_honest_contract,
};

fn wordml_structural_fixture() -> &'static [u8] {
    br#"<?xml version="1.0"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
<w:body>
<w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Title text</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>Article 1.</w:t></w:r></w:p>
</w:body>
</w:wordDocument>"#
}

#[test]
fn honest_synthetic_decoder_satisfies_shared_port_contract() {
    assert_decoder_port_contract(&HonestSyntheticDecoder);
}

#[test]
fn wordml_streaming_decoder_satisfies_shared_port_contract() {
    assert_decoder_port_contract_with_fixture(
        &WordMLStreamingDecoder,
        "family:consultant-wordml",
        wordml_structural_fixture(),
    );
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
