//! S03 T03 consumer-contract battery (M221-wbslul §8C.3).
//!
//! Executable core of the bounded consumer seam: the unchanged
//! `npa_context_records::build_context_records` stream is mapped to the closed
//! [`ThisDocumentReferenceOutcome`] and the mapping is fail-closed.
//!
//! The real-pipeline cases reuse the §8C.1/§8C.2 inline synthetic WordML
//! fixtures: an authorized `Приказ` letterhead plus a this-ref surface, a
//! this-ref surface without a letterhead, and no this-ref surface. The
//! conflicting and `resolved`-without-authorizing-claim cases are hand-built
//! `ContextRecord` streams (the producer guard never emits them, so the
//! consumer's fail-closed branch is exercised directly). Raw decoded corpus
//! text is never logged.

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::{
    ContextClaimStatus, ContextRequestKind, ContextStatus, DocumentVersionRef,
};
use ln_decode::local_grammar::DerivationSource;
use ln_decode::npa_analysis_records::{
    build_analysis_block_layout, AnalysisBlockLayout, AnalysisRefusal, AnalysisRefusalKind,
    SourceBoundSpan, SourceRef,
};
use ln_decode::npa_context_consumer::{
    consume_document_this_document_reference, consume_this_document_reference,
    ThisDocumentReferenceOutcome,
};
use ln_decode::npa_context_records::{
    build_context_records, ContextClaimRecord, ContextRecord, ContextResultRecord, ContextRunRecord,
};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{capture, Limits};

fn wrap(body: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"http://schemas.microsoft.com/office/word/2003/wordml\"><w:body>{body}</w:body></w:wordDocument>"
    )
}

/// Runs the real pipeline: capture -> projection -> block layout, with a
/// mapping that pins every substrate fragment.
fn pipeline(xml: &str) -> (AnalysisBlockLayout, SourceMapping, ReaderRecordIndex) {
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
    let layout =
        build_analysis_block_layout(&projection, &index).expect("analysis layout must build");
    (layout, mapping, index)
}

// A recognized inline `Приказ` letterhead (block 0) and a heading block (block
// 1) that carries a non-empty this-ref surface; the requisites request resolves.
const AUTHORIZED_BODY: &str =
    "<w:p><w:r><w:t>Приказ Минэкономразвития России от 02.10.2013 N 567</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Статья 2. Настоящего Федерального закона</w:t></w:r></w:p>";

// A this-ref surface without a letterhead: the request is emitted, unavailable.
const THIS_REF_ONLY_BODY: &str =
    "<w:p><w:r><w:t>Статья 1. Настоящего Федерального закона</w:t></w:r></w:p>";

// No this-ref surface: no requisites request is emitted.
const NO_THIS_REF_BODY: &str =
    "<w:p><w:r><w:t>Федеральный закон от 01.01.2020 N 1-ФЗ</w:t></w:r></w:p>";

// ------------------------------------------------------- hand-built records #

fn bound_ref() -> SourceRef {
    SourceRef::Bound(SourceBoundSpan::new(FragmentRef::from("fragment-1"), 0, 1))
}

fn result_record(
    kind: ContextRequestKind,
    status: ContextStatus,
    claims: Vec<ContextClaimRecord>,
) -> ContextRecord {
    ContextRecord::Result(ContextResultRecord {
        reference: "ctx:0".to_string(),
        request_ref: "req:0".to_string(),
        request_kind: kind,
        view: None,
        status,
        claims,
        derivations: Vec::new(),
        diagnostics: Vec::new(),
        anchors: Vec::new(),
    })
}

fn requisites(status: ContextStatus, claims: Vec<ContextClaimRecord>) -> ContextRecord {
    result_record(
        ContextRequestKind::CurrentDocumentRequisites,
        status,
        claims,
    )
}

fn claim_with_anchor(derivation: DerivationSource, anchor: SourceRef) -> ContextClaimRecord {
    ContextClaimRecord {
        field: "current_document_requisites".to_string(),
        claim_status: ContextClaimStatus::Inherited,
        derivation,
        source_node_ref: "frame-0".to_string(),
        anchor,
    }
}

fn claim(derivation: DerivationSource) -> ContextClaimRecord {
    claim_with_anchor(derivation, bound_ref())
}

fn refused_ref() -> SourceRef {
    SourceRef::Refused(AnalysisRefusal::local(AnalysisRefusalKind::OutOfBounds))
}

fn authorized_claim() -> ContextClaimRecord {
    claim(DerivationSource::AuthorizedCurrentDocumentRequisites)
}

// ------------------------------------------------------ real pipeline cases #

#[test]
fn authorized_letterhead_and_this_ref_yields_authorized() {
    let (layout, mapping, _) = pipeline(&wrap(AUTHORIZED_BODY));
    let (records, outcome) = consume_document_this_document_reference(&layout, &mapping);
    // The consumer never changes the producer stream.
    assert_eq!(records, build_context_records(&layout, &mapping));
    match outcome {
        ThisDocumentReferenceOutcome::Authorized { claim_ref } => {
            assert!(!claim_ref.is_empty(), "claim_ref must be non-empty");
            assert!(
                claim_ref.starts_with("ctx:"),
                "claim_ref is a family-local reference, not decoded text"
            );
        }
        other => panic!("expected Authorized, got {other:?}"),
    }
}

#[test]
fn this_ref_surface_without_letterhead_is_unavailable() {
    let (layout, mapping, _) = pipeline(&wrap(THIS_REF_ONLY_BODY));
    let (_, outcome) = consume_document_this_document_reference(&layout, &mapping);
    assert_eq!(outcome, ThisDocumentReferenceOutcome::Unavailable);
}

#[test]
fn no_this_ref_surface_is_not_requested() {
    let (layout, mapping, _) = pipeline(&wrap(NO_THIS_REF_BODY));
    let (_, outcome) = consume_document_this_document_reference(&layout, &mapping);
    assert_eq!(outcome, ThisDocumentReferenceOutcome::NotRequested);
}

#[test]
fn consumer_is_deterministic_across_repeated_calls() {
    let (layout, mapping, _) = pipeline(&wrap(AUTHORIZED_BODY));
    let first = consume_document_this_document_reference(&layout, &mapping);
    let second = consume_document_this_document_reference(&layout, &mapping);
    assert_eq!(
        first, second,
        "the consumer is a pure function of the stream"
    );
}

// --------------------------------------------- fail-closed hand-built cases #

#[test]
fn partial_and_conflicting_statuses_are_conflicting() {
    for status in [ContextStatus::Partial, ContextStatus::Conflicting] {
        assert_eq!(
            consume_this_document_reference(&[requisites(status, Vec::new())]),
            ThisDocumentReferenceOutcome::Conflicting,
            "{status:?} must be Conflicting"
        );
    }
}

#[test]
fn resolved_without_authorizing_claim_is_conflicting() {
    // A `resolved` requisites result with no claim at all.
    assert_eq!(
        consume_this_document_reference(&[requisites(ContextStatus::Resolved, Vec::new())]),
        ThisDocumentReferenceOutcome::Conflicting
    );
    // A `resolved` result whose only claim is not the authorizing inherited one.
    assert_eq!(
        consume_this_document_reference(&[requisites(
            ContextStatus::Resolved,
            vec![claim(DerivationSource::ExplicitMember)]
        )]),
        ThisDocumentReferenceOutcome::Conflicting
    );
    // The authorizing derivation with the wrong claim status is not a success.
    let mut wrong_status = authorized_claim();
    wrong_status.claim_status = ContextClaimStatus::Explicit;
    assert_eq!(
        consume_this_document_reference(&[requisites(ContextStatus::Resolved, vec![wrong_status])]),
        ThisDocumentReferenceOutcome::Conflicting
    );
}

#[test]
fn authorized_claim_with_refused_anchor_is_conflicting() {
    let refused = claim_with_anchor(
        DerivationSource::AuthorizedCurrentDocumentRequisites,
        refused_ref(),
    );
    assert_eq!(
        consume_this_document_reference(&[requisites(ContextStatus::Resolved, vec![refused])]),
        ThisDocumentReferenceOutcome::Conflicting,
        "a refused source anchor must not be promoted to Authorized"
    );
}

#[test]
fn authorized_claim_with_conflicting_sibling_is_conflicting() {
    let mut sibling = claim(DerivationSource::ExplicitMember);
    sibling.claim_status = ContextClaimStatus::Conflicting;
    assert_eq!(
        consume_this_document_reference(&[requisites(
            ContextStatus::Resolved,
            vec![authorized_claim(), sibling]
        )]),
        ThisDocumentReferenceOutcome::Conflicting,
        "a conflicting sibling claim must block Authorized"
    );
}

// -------------------------------------------------- canonical mapping table #
#[test]
fn canonical_status_mapping_table_is_closed() {
    // Every `ContextStatus` maps to exactly one decision.
    let cases: [(
        ContextStatus,
        Vec<ContextClaimRecord>,
        ThisDocumentReferenceOutcome,
    ); 7] = [
        (
            ContextStatus::Resolved,
            vec![authorized_claim()],
            ThisDocumentReferenceOutcome::Authorized {
                claim_ref: "ctx:0".to_string(),
            },
        ),
        (
            ContextStatus::Resolved,
            Vec::new(),
            ThisDocumentReferenceOutcome::Conflicting,
        ),
        (
            ContextStatus::Partial,
            Vec::new(),
            ThisDocumentReferenceOutcome::Conflicting,
        ),
        (
            ContextStatus::Conflicting,
            Vec::new(),
            ThisDocumentReferenceOutcome::Conflicting,
        ),
        (
            ContextStatus::Unavailable,
            Vec::new(),
            ThisDocumentReferenceOutcome::Unavailable,
        ),
        (
            ContextStatus::Cycle,
            Vec::new(),
            ThisDocumentReferenceOutcome::Unavailable,
        ),
        (
            ContextStatus::Limit,
            Vec::new(),
            ThisDocumentReferenceOutcome::Unavailable,
        ),
    ];
    for (status, claims, expected) in cases {
        assert_eq!(
            consume_this_document_reference(&[requisites(status, claims)]),
            expected,
            "{status:?} maps to the closed outcome"
        );
    }

    // A non-requisites result is never read as a requisites decision.
    let other = result_record(
        ContextRequestKind::OpenSeriesHead,
        ContextStatus::Resolved,
        Vec::new(),
    );
    assert_eq!(
        consume_this_document_reference(&[
            other,
            ContextRecord::Run(ContextRunRecord::empty(vec![]))
        ]),
        ThisDocumentReferenceOutcome::NotRequested
    );
}

#[test]
fn worst_outcome_wins_unavailable_over_authorized_and_conflicting_over_all() {
    // Conflicting > Unavailable > Authorized (fail-closed).
    let unavailable = vec![
        requisites(ContextStatus::Unavailable, Vec::new()),
        requisites(ContextStatus::Resolved, vec![authorized_claim()]),
    ];
    assert_eq!(
        consume_this_document_reference(&unavailable),
        ThisDocumentReferenceOutcome::Unavailable,
        "an unavailable result is not authorized by a sibling resolved result"
    );

    let conflicting = vec![
        requisites(ContextStatus::Resolved, vec![authorized_claim()]),
        requisites(ContextStatus::Partial, Vec::new()),
    ];
    assert_eq!(
        consume_this_document_reference(&conflicting),
        ThisDocumentReferenceOutcome::Conflicting,
        "a partial result outranks an authorizing sibling"
    );

    let unavailable_then_conflicting = vec![
        requisites(ContextStatus::Unavailable, Vec::new()),
        requisites(ContextStatus::Conflicting, Vec::new()),
    ];
    assert_eq!(
        consume_this_document_reference(&unavailable_then_conflicting),
        ThisDocumentReferenceOutcome::Conflicting,
        "conflicting outranks unavailable"
    );
}

#[test]
fn outcome_tokens_are_closed_and_ascii() {
    let outcomes = [
        ThisDocumentReferenceOutcome::Authorized {
            claim_ref: "ctx:0".to_string(),
        },
        ThisDocumentReferenceOutcome::Conflicting,
        ThisDocumentReferenceOutcome::Unavailable,
        ThisDocumentReferenceOutcome::NotRequested,
    ];
    for outcome in outcomes {
        let token = outcome.token();
        assert!(token.is_ascii(), "the outcome token is ascii-only");
        assert!(
            token.bytes().all(|b| b.is_ascii_lowercase() || b == b'_'),
            "the outcome token is a closed token ({token})"
        );
    }
}
