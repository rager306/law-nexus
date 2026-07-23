use ln_decode::{
    adapters::{HonestSyntheticDecoder, InMemoryDiagnosticSink},
    application::DecodeAndAnchor,
    domain::{DecodeCategory, DecodeRequest, FamilyFormat, PayloadRef},
};

const CANARY: &[u8] = b"CANARY::SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK";

fn request() -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:P1").expect("valid"),
        FamilyFormat::parse("family:synthetic").expect("valid"),
        CANARY,
    )
}

#[test]
fn honest_decode_yields_only_structural_candidates_and_anchors() {
    let mut use_case =
        DecodeAndAnchor::new(HonestSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    assert_eq!(result.candidates.len(), 1);
    assert_eq!(
        result.candidates[0].category,
        DecodeCategory::StructuralCandidate
    );
    assert_eq!(result.candidates[0].anchor.start_offset, 0);
    assert!(result.candidates[0].anchor.end_offset > 0);
    assert!(result
        .candidates[0]
        .anchor
        .fingerprint
        .starts_with("fnv1a64:"));
    assert!(result.rejected_categories.is_empty());
    assert!(result.verified_assertion_absent);
    assert!(result.merged_identity_absent);
    assert!(result.unregistered_relation_absent);
    assert!(result.raw_payload_absent);
}

#[test]
fn diagnostics_include_positive_control_and_omit_canary() {
    let mut use_case =
        DecodeAndAnchor::new(HonestSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    assert!(result
        .diagnostics
        .iter()
        .any(|d| d.positive_control && d.category == "decode-positive-control"));
    let debug = format!("{result:?}");
    assert!(!debug.contains("CANARY::"));
    assert!(!debug.contains("SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK"));
    for event in &result.diagnostics {
        assert!(!format!("{event:?}").contains("CANARY::"));
        assert!(!event.fingerprint.is_empty());
    }
}

#[test]
fn accepted_output_never_carries_gate_owned_claims() {
    let mut use_case =
        DecodeAndAnchor::new(HonestSyntheticDecoder, InMemoryDiagnosticSink::default());
    let result = use_case.execute(request());

    for candidate in &result.candidates {
        assert!(candidate.category.is_structural());
        assert_ne!(
            candidate.category,
            DecodeCategory::VerifiedAssertion
        );
        assert_ne!(candidate.category, DecodeCategory::MergedIdentity);
        assert_ne!(
            candidate.category,
            DecodeCategory::UnregisteredRelation
        );
    }
}
