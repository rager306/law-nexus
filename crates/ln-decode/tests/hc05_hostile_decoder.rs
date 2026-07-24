use ln_decode::{
    adapters::{InMemoryDiagnosticSink, MaliciousSyntheticDecoder},
    application::DecodeAndAnchor,
    domain::{DecodeCategory, DecodeRequest, FamilyFormat, PayloadRef},
};

const CANARY: &[u8] = b"CANARY::SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK";

fn request() -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:P-hostile").expect("valid"),
        FamilyFormat::parse("family:synthetic").expect("valid"),
        CANARY,
    )
}

#[test]
fn malicious_verified_merge_relation_and_raw_context_are_rejected() {
    let mut use_case =
        DecodeAndAnchor::new(MaliciousSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    assert!(result.candidates.is_empty());
    assert!(result
        .rejected_categories
        .contains(&DecodeCategory::VerifiedAssertion));
    assert!(result
        .rejected_categories
        .contains(&DecodeCategory::MergedIdentity));
    assert!(result
        .rejected_categories
        .contains(&DecodeCategory::UnregisteredRelation));
    assert!(result
        .rejected_categories
        .contains(&DecodeCategory::RawFailureContext));
    assert!(result.verified_assertion_absent);
    assert!(result.merged_identity_absent);
    assert!(result.unregistered_relation_absent);
    assert!(result.raw_payload_absent);
}

#[test]
fn malicious_canary_never_appears_in_diagnostics_or_debug() {
    let mut use_case =
        DecodeAndAnchor::new(MaliciousSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    let debug = format!("{result:?}");
    assert!(!debug.contains("CANARY::"));
    assert!(!debug.contains("SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK"));
    for event in &result.diagnostics {
        assert!(!format!("{event:?}").contains("CANARY::"));
        assert!(!event.fingerprint.is_empty());
        assert!(!event.category.contains("CANARY"));
    }
}

#[test]
fn malicious_path_still_emits_positive_control() {
    let mut use_case =
        DecodeAndAnchor::new(MaliciousSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.positive_control && d.category == "decode-positive-control"));
    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.category == "decode-rejected-non-structural"));
}
