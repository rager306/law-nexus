//! T02 hostile battery (M214-es3jvw S01).
//!
//! Every closed refusal the T01 contract attributes to the source-mapping seam
//! (§7.1) is exercised with a failing input: malformed half-open UTF-8 ranges,
//! unknown/foreign fragments, parent and document-version identity mismatches,
//! token-view substitution, unsupported coordinate kinds, envelope-shape
//! breaks, temporal stop-sign fields and corpus re-carriage (§12 H1–H12).

use ln_decode::analysis_source_mapping::{
    check_coordinate_kind, check_envelope_shape, check_no_corpus_transfer, check_temporal_fields,
    check_token_span, check_token_view, CoordinateKind, EnvelopeLineKind, EnvelopeLineShape,
    MappingRefusal, MappingRefusalKind, SourceIdentity, SourceMapping, TokenView,
    TEMPORAL_FORBIDDEN_FIELDS,
};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_anchor::LocalSpan;
use ln_decode::reader_contract::{FragmentRef, ReaderFragmentSpan};

const FRAGMENT_T7: &str = "см. ст. 5";

fn hex64(fill: u8) -> String {
    (0..64).map(|_| fill as char).collect()
}

fn identity(fill: u8, sealed: bool) -> SourceIdentity {
    SourceIdentity::try_new(
        hex64(fill),
        FRAGMENT_T7.len() as u64,
        "law-nexus/source-package-model/v1".to_string(),
        sealed.then_some(hex64(b'1')),
        sealed.then_some(hex64(b'2')),
    )
    .expect("identity must be well formed")
}

fn version(source_revision: &str) -> DocumentVersionRef {
    DocumentVersionRef::try_new(
        "doc-version-1".to_string(),
        source_revision.to_string(),
        "reader_wordml_profile/v1".to_string(),
    )
    .expect("version triple must be well formed")
}

fn mapping(sealed: bool) -> SourceMapping {
    let document = identity(b'a', sealed);
    let mut mapping = SourceMapping::new(document.clone(), version("rev-1"));
    mapping
        .pin_fragment(FragmentRef::new("t7"), FRAGMENT_T7, &document)
        .expect("t7 belongs to document A");
    mapping
        .map_block(0, FragmentRef::new("t7"))
        .expect("block 0 maps to t7");
    mapping
}

fn kind_of<T>(result: Result<T, MappingRefusal>) -> MappingRefusalKind {
    match result {
        Ok(_) => panic!("input must be refused"),
        Err(refusal) => refusal.kind(),
    }
}

// ---------------------------------------------------------------- H1–H3 #

#[test]
fn h1_inverted_span_is_refused() {
    let span = ReaderFragmentSpan::new(FragmentRef::new("t7"), 7, 6);
    assert_eq!(
        kind_of(mapping(false).resolve_fragment_span(&span)),
        MappingRefusalKind::EmptyOrInverted
    );
}

#[test]
fn h2_span_past_the_fragment_is_refused() {
    let span = ReaderFragmentSpan::new(FragmentRef::new("t7"), 0, 14);
    assert_eq!(
        kind_of(mapping(false).resolve_fragment_span(&span)),
        MappingRefusalKind::OutOfBounds
    );
}

#[test]
fn h3_span_splitting_a_code_point_is_refused() {
    // Byte 7 sits inside the two-byte 'с' that starts at byte 6.
    let span = ReaderFragmentSpan::new(FragmentRef::new("t7"), 7, 8);
    assert_eq!(
        kind_of(mapping(false).resolve_fragment_span(&span)),
        MappingRefusalKind::NotCharBoundary
    );
}

// ---------------------------------------------------------------- H4–H5 #

#[test]
fn h4_fragment_absent_from_the_pinned_parent_is_refused() {
    let span = ReaderFragmentSpan::new(FragmentRef::new("t999"), 0, 3);
    assert_eq!(
        kind_of(mapping(false).resolve_fragment_span(&span)),
        MappingRefusalKind::UnknownFragment
    );
}

#[test]
fn h5_fragment_from_another_document_is_refused() {
    let mut mapping = mapping(false);
    let foreign = identity(b'b', false);
    assert_eq!(
        kind_of(mapping.pin_fragment(FragmentRef::new("t9"), "чужой", &foreign)),
        MappingRefusalKind::CrossDocument
    );
}

// ---------------------------------------------------------------- H6–H9 #

#[test]
fn h6_parent_citation_with_foreign_source_sha_is_refused() {
    let mapping = mapping(false);
    assert_eq!(
        kind_of(mapping.check_parent_citation(&identity(b'b', false))),
        MappingRefusalKind::SourceIdentityMismatch
    );
}

#[test]
fn h7_cross_view_token_substitution_is_refused() {
    assert_eq!(
        kind_of(check_token_view(
            TokenView::CoveringWord,
            TokenView::Alphabetic
        )),
        MappingRefusalKind::TokenViewMismatch
    );
    // A span that is a covering token but not an alphabetic token is refused
    // under the alphabetic view, and vice versa.
    assert_eq!(
        kind_of(check_token_span("ст. 5", TokenView::Alphabetic, 0, 5)),
        MappingRefusalKind::TokenViewMismatch
    );
    assert_eq!(
        kind_of(check_token_span("ст. 5", TokenView::CoveringWord, 0, 4)),
        MappingRefusalKind::TokenViewMismatch
    );
}

#[test]
fn h8_foreign_document_version_triple_is_refused() {
    let mapping = mapping(false);
    assert_eq!(
        kind_of(mapping.check_document_version(&version("rev-2"))),
        MappingRefusalKind::DocumentVersionMismatch
    );
}

#[test]
fn h9_seal_claim_on_an_unsealed_parent_is_refused() {
    let sealed = mapping(true);
    assert_eq!(
        kind_of(sealed.check_parent_citation(&identity(b'a', false))),
        MappingRefusalKind::SourceIdentityMismatch
    );
    // The same sealed envelope accepts the genuinely sealed parent.
    assert_eq!(sealed.check_parent_citation(&identity(b'a', true)), Ok(()));
}

// ------------------------------------------------------------------ H10 #

#[test]
fn h10_envelope_shape_breaks_are_refused() {
    let record = EnvelopeLineShape::new(EnvelopeLineKind::Record, 10);
    let manifest = EnvelopeLineShape::new(EnvelopeLineKind::Manifest, 10);
    let policies = EnvelopeLineShape::new(EnvelopeLineKind::Policies, 10);
    let footer = EnvelopeLineShape::new(EnvelopeLineKind::Footer, 10);

    // Missing footer (trailing record).
    assert_eq!(
        kind_of(check_envelope_shape(&[manifest, policies, record])),
        MappingRefusalKind::EnvelopeStructural
    );
    // Misordered manifest.
    assert_eq!(
        kind_of(check_envelope_shape(&[policies, manifest, footer])),
        MappingRefusalKind::EnvelopeStructural
    );
    // Embedded carriage return.
    assert_eq!(
        kind_of(check_envelope_shape(&[
            manifest,
            policies,
            record.with_cr(),
            footer
        ])),
        MappingRefusalKind::EnvelopeStructural
    );
    // Empty interior line.
    assert_eq!(
        kind_of(check_envelope_shape(&[
            manifest,
            policies,
            EnvelopeLineShape::new(EnvelopeLineKind::Empty, 0),
            footer
        ])),
        MappingRefusalKind::EnvelopeStructural
    );
    // Record after the footer.
    assert_eq!(
        kind_of(check_envelope_shape(&[manifest, policies, footer, record])),
        MappingRefusalKind::EnvelopeStructural
    );
}

// -------------------------------------------------------------- H11–H12 #

#[test]
fn h11_temporal_field_is_refused() {
    assert_eq!(
        kind_of(check_temporal_fields(&["fragment_ref", "edition_date"])),
        MappingRefusalKind::TemporalFieldForbidden
    );
    // The stop-sign list is closed and non-empty.
    assert!(!TEMPORAL_FORBIDDEN_FIELDS.contains(&"fragment_ref"));
    assert!(TEMPORAL_FORBIDDEN_FIELDS.contains(&"effective_from"));
    assert_eq!(check_temporal_fields(&["fragment_ref", "block"]), Ok(()));
}

#[test]
fn h12_inline_corpus_text_is_refused() {
    assert_eq!(
        kind_of(check_no_corpus_transfer(Some(FRAGMENT_T7))),
        MappingRefusalKind::CorpusTransferForbidden
    );
    assert_eq!(check_no_corpus_transfer(None), Ok(()));
}

// --------------------------------------------- unsupported + structural #

#[test]
fn unsupported_coordinate_systems_are_refused() {
    for coordinate in [
        CoordinateKind::XmlArtifactSpan,
        CoordinateKind::CharacterOffset,
        CoordinateKind::LineOffset,
    ] {
        assert_eq!(
            kind_of(check_coordinate_kind(coordinate)),
            MappingRefusalKind::UnsupportedMapping
        );
    }
}

#[test]
fn unmapped_block_is_refused_rather_than_invented() {
    let mapping = mapping(false);
    let span = LocalSpan {
        block: 7,
        start: 0,
        end: 3,
    };
    assert_eq!(
        kind_of(mapping.resolve_local_span(span)),
        MappingRefusalKind::UnsupportedMapping
    );
}

#[test]
fn local_block_span_validation_reuses_the_half_open_rules() {
    let mapping = mapping(false);
    for span in [
        LocalSpan {
            block: 0,
            start: 7,
            end: 6,
        },
        LocalSpan {
            block: 0,
            start: 0,
            end: 14,
        },
        LocalSpan {
            block: 0,
            start: 7,
            end: 8,
        },
    ] {
        assert!(mapping.resolve_local_span(span).is_err());
    }
}

#[test]
fn duplicate_fragment_and_block_remap_are_structural_refusals() {
    let mut mapping = mapping(false);
    let document = identity(b'a', false);
    assert_eq!(
        kind_of(mapping.pin_fragment(FragmentRef::new("t7"), "cm. st. 5", &document)),
        MappingRefusalKind::EnvelopeStructural
    );
    assert_eq!(
        kind_of(mapping.map_block(0, FragmentRef::new("t4"))),
        MappingRefusalKind::EnvelopeStructural
    );
}

#[test]
fn malformed_parent_identity_is_a_structural_refusal() {
    let short = SourceIdentity::try_new(
        "ABC".to_string(),
        FRAGMENT_T7.len() as u64,
        "law-nexus/source-package-model/v1".to_string(),
        None,
        None,
    );
    assert_eq!(kind_of(short), MappingRefusalKind::EnvelopeStructural);
}
