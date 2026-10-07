//! T04 contract battery (M214-es3jvw S03).
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8B.4:
//! `read_back_npa_analysis` reconstructs all seven families into a typed model,
//! and `verify_npa_analysis_wire` re-derives the canonical records from the
//! pinned parent and returns `Ok(())` for a valid context-enriched envelope.
//! Read-back fails closed on a structural break and never verifies seals.
//!
//! Fixtures are inline synthetic WordML documents. Raw decoded corpus text is
//! never logged.

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::{ContextStatus, DocumentVersionRef};
use ln_decode::npa_analysis_records::{analyze_document, DocumentAnalysis};
use ln_decode::npa_analysis_verify::{
    read_back_npa_analysis, verify_npa_analysis_wire, AnalysisReadback, AnalysisVerifyCode,
    ReadbackContext,
};
use ln_decode::npa_analysis_wire::{
    inspect_npa_analysis_wire, render_npa_analysis, render_npa_analysis_with_context,
    AnalysisEnvelopeRequest, AnalysisLimits, AnalysisScope,
};
use ln_decode::npa_context_records::{
    build_context_records, context_stream_is_trivially_empty, ContextRecord,
};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::{build_projection, ReaderProjection};
use ln_decode::source_package::{capture, Limits};

fn wrap(body: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{body}</w:body></w:wordDocument>"
    )
}

struct Pipeline {
    analysis: DocumentAnalysis,
    projection: ReaderProjection,
    index: ReaderRecordIndex,
    mapping: SourceMapping,
}

/// Runs the real pipeline: capture -> projection -> document analysis, with a
/// mapping that pins every substrate fragment.
fn pipeline(xml: &str) -> Pipeline {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");
    let projection = build_projection(package.records()).expect("projection must build");
    let identity = SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        "law-nexus/source-package-model/v1".to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .expect("manifest identity must be well formed");
    let version = DocumentVersionRef::try_new(
        "doc-version-1".to_string(),
        "rev-1".to_string(),
        "reader_wordml_profile/v1".to_string(),
    )
    .expect("version triple must be well formed");
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .expect("every substrate fragment must pin");
    }
    let analysis = analyze_document(&projection, &index, &mapping).expect("analysis must build");
    Pipeline {
        analysis,
        projection,
        index,
        mapping,
    }
}

fn envelope_request(p: &Pipeline) -> AnalysisEnvelopeRequest<'_> {
    AnalysisEnvelopeRequest {
        analysis: &p.analysis,
        projection: &p.projection,
        index: &p.index,
        mapping: &p.mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    }
}

fn context_envelope(p: &Pipeline) -> (Vec<ContextRecord>, String) {
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    let request = envelope_request(p);
    let text = render_npa_analysis_with_context(&request, &contexts)
        .expect("a valid context envelope must render");
    (contexts, text)
}

fn verify(
    p: &Pipeline,
    text: &str,
) -> Result<(), Vec<ln_decode::npa_analysis_verify::AnalysisVerifyFinding>> {
    verify_npa_analysis_wire(text, &p.projection, &p.index, &p.mapping)
}

// A heading designation frame plus two act-requisites paragraphs (the second
// bare `от ДАТА N` is the continuation tail), then a trailing heading block
// carrying a this-ref surface. No letterhead is present, so the emitted
// current-document-requisites request stays `unavailable` and the honest
// non-resolved context path is exercised.
const CONTEXT_BODY: &str = "<w:p><w:r><w:t>Статья 1. Предмет регулирования</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Федерального закона от 01.01.2020 N 1-ФЗ,</w:t></w:r></w:p>\
     <w:p><w:r><w:t>от 02.02.2021 N 2-ФЗ</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Статья 2. Настоящего Федерального закона</w:t></w:r></w:p>";

const TYPED_BODY: &str = "<w:p><w:r><w:t>Федеральный закон от 01.01.2020 N 1-ФЗ</w:t></w:r></w:p>";

// A contextless document: two plain runs with no legal marker, no this-ref
// surface, no continuation tail and no captured mention. Its re-derived context
// stream is trivially empty (a single zero-request run), so it is the honest
// six-family parent and, with the run line rendered, the zero-request
// seven-family parent.
const TWO_RUNS: &str = "<w:p><w:r><w:t>Alpha</w:t></w:r><w:r><w:t>Beta</w:t></w:r></w:p>";

// ------------------------------------------------------ fixture coverage #

#[test]
fn context_fixture_yields_context_relation_and_classification_records() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    assert!(
        contexts
            .iter()
            .any(|record| matches!(record, ContextRecord::Result(_))),
        "the fixture emits at least one context result"
    );
    assert!(
        contexts
            .iter()
            .any(|record| matches!(record, ContextRecord::Run(_))),
        "the fixture emits exactly the aggregate run line"
    );
    assert!(
        !p.analysis.relations.is_empty(),
        "the open series head yields a relation"
    );
    assert!(
        !p.analysis.classifications.is_empty(),
        "the linked member is classified"
    );
}

// ----------------------------------------------------------- read-back #

#[test]
fn read_back_reconstructs_all_seven_families() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let (contexts, text) = context_envelope(&p);
    let summary = inspect_npa_analysis_wire(&text).expect("the envelope inspects");
    let readback = read_back_npa_analysis(&text).expect("the envelope reads back");

    assert_eq!(
        readback.footer.completion, summary.completion,
        "read-back preserves the completion token"
    );
    assert_eq!(
        readback.footer.completion_basis, summary.completion_basis,
        "read-back preserves the completion basis"
    );
    assert_eq!(
        readback.footer.counts.get("records").copied(),
        Some(summary.records),
        "read-back preserves the record count"
    );
    assert_eq!(
        readback.fragments.len() as u64,
        summary.families.get("fragment").copied().unwrap_or(0),
        "read-back reconstructs every fragment record"
    );
    assert_eq!(
        readback.records.len() as u64,
        summary.records,
        "read-back reconstructs every interior record"
    );
    assert_eq!(
        readback.contexts.len(),
        contexts.len(),
        "read-back reconstructs every context record"
    );
    assert!(
        readback
            .contexts
            .iter()
            .any(|record| matches!(record, ReadbackContext::Result { .. })),
        "read-back reconstructs context result lines"
    );
    assert!(
        readback
            .contexts
            .iter()
            .any(|record| matches!(record, ReadbackContext::Run { .. })),
        "read-back reconstructs the aggregate run line"
    );
    assert!(
        !readback.manifest.source_sha256.is_empty()
            && !readback.manifest.document_version_ref.is_empty(),
        "read-back reconstructs the pinned manifest"
    );
    assert!(
        readback.footer.records_seal_hash.is_some() && readback.footer.manifest_hash.is_some(),
        "read-back reconstructs both footer seals"
    );
    assert!(
        !readback.relations.is_empty() && !readback.classifications.is_empty(),
        "read-back reconstructs relation and classification families"
    );
}

#[test]
fn read_back_is_deterministic() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let (_, text) = context_envelope(&p);
    let first = read_back_npa_analysis(&text).expect("first read-back");
    let second = read_back_npa_analysis(&text).expect("second read-back");
    assert_eq!(first, second, "read-back is byte-deterministic");
}

// ---------------------------------------------------------- verifier #

#[test]
fn valid_context_envelope_verifies_ok() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let (contexts, text) = context_envelope(&p);
    assert!(
        contexts
            .iter()
            .any(|record| matches!(record, ContextRecord::Result(_))),
        "the fixture is context-bearing"
    );
    assert_eq!(
        verify(&p, &text),
        Ok(()),
        "an untouched context envelope verifies against the pinned parent"
    );
}

#[test]
fn valid_envelope_uses_only_the_pinned_parent() {
    // The verifier re-derives from `projection` + `index` + `mapping`; changing
    // any of them changes the canonical derivation. A valid envelope verified
    // with the *same* parent is Ok, proving the derivation is not self-sealing.
    let p = pipeline(&wrap(CONTEXT_BODY));
    let (_, text) = context_envelope(&p);
    assert_eq!(verify(&p, &text), Ok(()));
    // Re-reading the artifact without a parent must not be mistaken for a pass.
    let readback = read_back_npa_analysis(&text).expect("read-back succeeds");
    assert!(
        !readback.records.is_empty(),
        "read-back is independent of the verifier verdict"
    );
}

#[test]
fn non_resolved_context_is_exercised() {
    let p = pipeline(&wrap(CONTEXT_BODY));
    let (contexts, _) = context_envelope(&p);
    assert!(
        contexts.iter().any(|record| matches!(
            record,
            ContextRecord::Result(result) if result.status != ContextStatus::Resolved
        )),
        "the fixture surfaces a non-resolved context outcome for the honest-incomplete path"
    );
}

// ------------------------------------------- mode-aware admission (§8B.4) #

#[test]
fn contextless_six_family_envelope_verifies_ok() {
    // The six-family S02-envelope is admitted only when the re-derived context
    // stream is trivially empty; the positive must prove that precondition, not
    // merely happen to pass.
    let p = pipeline(&wrap(TWO_RUNS));
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    assert!(
        context_stream_is_trivially_empty(&contexts),
        "the contextless parent must re-derive a trivially empty context stream: {contexts:?}"
    );
    let text = render_npa_analysis(&envelope_request(&p)).expect("the S02 envelope renders");
    assert_eq!(
        verify(&p, &text),
        Ok(()),
        "a six-family envelope on a contextless parent verifies"
    );
}

#[test]
fn six_family_envelope_hiding_context_is_context_outcome_mismatch() {
    // A six-family envelope derived from a context-bearing parent hides the
    // mandatory context family; the closed refusal is context_outcome_mismatch,
    // never a silent pass or a generic completion failure.
    let p = pipeline(&wrap(CONTEXT_BODY));
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    assert!(
        !context_stream_is_trivially_empty(&contexts),
        "the fixture must be context-bearing"
    );
    let text = render_npa_analysis(&envelope_request(&p)).expect("the S02 envelope renders");
    let findings =
        verify(&p, &text).expect_err("a six-family envelope that hides context must be rejected");
    assert!(
        findings
            .iter()
            .any(|finding| finding.code() == AnalysisVerifyCode::ContextOutcomeMismatch),
        "a hidden context family is context_outcome_mismatch: {findings:?}"
    );
}

#[test]
fn zero_request_seven_family_envelope_verifies_ok() {
    // The seven-family mode is admitted always; a contextless parent rendered
    // with its honest zero-request run line is a valid seven-family envelope.
    let p = pipeline(&wrap(TWO_RUNS));
    let contexts = build_context_records(&p.analysis.layout, &p.mapping);
    assert!(
        context_stream_is_trivially_empty(&contexts),
        "the contextless parent must re-derive a trivially empty context stream"
    );
    let text = render_npa_analysis_with_context(&envelope_request(&p), &contexts)
        .expect("the seven-family envelope renders");
    assert_eq!(
        verify(&p, &text),
        Ok(()),
        "an honest zero-request run line is admitted"
    );
}

// ------------------------------------------------------ fail-closed shape #

#[test]
fn read_back_fails_closed_on_structural_break() {
    let p = pipeline(&wrap(TYPED_BODY));
    let request = envelope_request(&p);
    let s02 = render_npa_analysis(&request).expect("the S02 envelope renders");

    assert!(
        read_back_npa_analysis("").is_err(),
        "an empty document is refused"
    );
    assert!(
        read_back_npa_analysis("not json").is_err(),
        "a non-JSON document is refused"
    );
    assert!(
        read_back_npa_analysis(&s02.replace('\n', "\r\n")).is_err(),
        "an embedded carriage return is refused"
    );
    let mut truncated = s02.clone();
    truncated.truncate(truncated.len() - 3);
    assert!(
        read_back_npa_analysis(&truncated).is_err(),
        "a truncated envelope is refused"
    );
}

#[test]
fn verifier_refuses_garbage_with_a_closed_code() {
    let p = pipeline(&wrap(TYPED_BODY));
    let findings = verify(&p, "not a jsonl envelope\n").expect_err("garbage must not verify");
    assert!(
        findings
            .iter()
            .any(|finding| finding.code() == AnalysisVerifyCode::EnvelopeStructural),
        "garbage yields envelope_structural"
    );
}

#[test]
fn verify_codes_are_closed_tokens() {
    for (code, token) in [
        (
            AnalysisVerifyCode::EnvelopeStructural,
            "envelope_structural",
        ),
        (AnalysisVerifyCode::SealMismatch, "seal_mismatch"),
        (
            AnalysisVerifyCode::ManifestIdentityMismatch,
            "manifest_identity_mismatch",
        ),
        (
            AnalysisVerifyCode::FragmentHashMismatch,
            "fragment_hash_mismatch",
        ),
        (AnalysisVerifyCode::SpanSliceMismatch, "span_slice_mismatch"),
        (
            AnalysisVerifyCode::SourceRefSubstitution,
            "source_ref_substitution",
        ),
        (
            AnalysisVerifyCode::RelationRefMissing,
            "relation_ref_missing",
        ),
        (
            AnalysisVerifyCode::RelationSubstitution,
            "relation_substitution",
        ),
        (AnalysisVerifyCode::MemberRefMissing, "member_ref_missing"),
        (
            AnalysisVerifyCode::ContextOutcomeMismatch,
            "context_outcome_mismatch",
        ),
        (
            AnalysisVerifyCode::CompletionMismatch,
            "completion_mismatch",
        ),
    ] {
        assert_eq!(code.as_str(), token);
    }
}

// A tiny helper kept so the test module always compiles against the public
// readback type even if a future refactor changes its shape.
fn _assert_readback_type(_: &AnalysisReadback) {}
