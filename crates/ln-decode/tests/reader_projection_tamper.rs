//! S03 resealed semantic-tamper battery.
//!
//! The untampered projection over the pinned mixed WordML fixture must verify.
//! Then, for each semantic tamper, the projection is mutated, `reseal()`ed and
//! re-verified: the independent `reader_verifier` recomputes the expected
//! semantics from substrate and must still reject the rewrite. The content seal
//! is an integrity pin only and never feeds verification, so a changed
//! `content_hash` is asserted alongside each `VerifyCode`.
//!
//! Tamper cases: loss (dropped segment / dropped view), cross-view ownership
//! reassignment, derived-control promotion, source-span stripping, derived
//! invented span, segment-order permutation and a resolved reference.
//!
//! Non-claims: one pinned mixed fixture (`reader_wordml_profile/v1`),
//! `[bounded]`; diverse fixtures and the gate are S04.

use ln_decode::reader_contract::{
    FragmentRef, ReaderFragmentSpan, ReaderSegmentKind, ReaderViewKind,
};
use ln_decode::reader_projection::{
    ReaderProjection, SegmentId, SegmentOrigin, ViewId, build_projection,
};
use ln_decode::reader_verifier::{VerifyCode, verify_projection};
use ln_decode::source_package::{Limits, Record, capture};

const XML: &str = include_str!("fixtures/reader/mixed-wordml.xml");
const FIXTURE_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

fn fixture_records() -> Vec<Record> {
    let package = capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture");
    assert_eq!(
        package.manifest().source.sha256,
        FIXTURE_SHA256,
        "fixture content changed; re-pin FIXTURE_SHA256"
    );
    package.records().to_vec()
}

/// Builds and seals the untampered projection.
fn sealed_projection(records: &[Record]) -> ReaderProjection {
    let mut projection = build_projection(records).expect("projection must build");
    projection.reseal();
    projection
}

fn seal_hash(projection: &ReaderProjection) -> String {
    projection
        .content_hash()
        .expect("projection must be sealed")
        .to_string()
}

fn segment_index(projection: &ReaderProjection, fragment: &str) -> usize {
    projection
        .segments
        .iter()
        .position(|segment| {
            segment.fragment_ref.as_ref().map(FragmentRef::as_str) == Some(fragment)
        })
        .unwrap_or_else(|| panic!("segment for fragment {fragment} missing"))
}

fn view_id(projection: &ReaderProjection, kind: ReaderViewKind, element_ref: &str) -> ViewId {
    projection
        .views
        .iter()
        .find(|view| view.kind == kind && view.element_ref.as_str() == element_ref)
        .unwrap_or_else(|| panic!("view {kind:?} {element_ref} missing"))
        .id
        .clone()
}

/// The tampered projection must fail verification with `expected`; the caller
/// asserts the seal changed.
fn expect_finding(projection: &ReaderProjection, records: &[Record], expected: VerifyCode) {
    match verify_projection(projection, records) {
        Ok(()) => panic!("tamper {expected:?} must be caught after reseal"),
        Err(findings) => {
            assert!(
                findings.iter().any(|finding| finding.code == expected),
                "expected {expected:?}, got {:?}",
                findings.iter().map(|f| f.code).collect::<Vec<_>>()
            );
        }
    }
}

#[test]
fn untampered_projection_verifies_ok() {
    let records = fixture_records();
    let projection = sealed_projection(&records);
    assert!(verify_projection(&projection, &records).is_ok());
}

#[test]
fn dropped_segment_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let index = segment_index(&projection, "t0");
    let victim = projection.segments[index].id.clone();
    projection.segments.remove(index);
    for view in &mut projection.views {
        view.segment_refs.retain(|id| id != &victim);
    }

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::MissingFragmentReference);
}

#[test]
fn dropped_view_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let victim = view_id(&projection, ReaderViewKind::Paragraph, "e2");
    projection.views.retain(|view| view.id != victim);

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::ViewMissing);
}

#[test]
fn reassigned_fragment_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let index = segment_index(&projection, "t0");
    let victim = projection.segments[index].id.clone();
    let source = view_id(&projection, ReaderViewKind::Paragraph, "e2");
    let target = view_id(&projection, ReaderViewKind::Residual, "e0");

    for view in &mut projection.views {
        if view.id == source {
            view.segment_refs.retain(|id| id != &victim);
        }
    }
    projection.segments[index].view = target.clone();
    for view in &mut projection.views {
        if view.id == target {
            view.segment_refs.push(SegmentId::from(victim.as_str()));
        }
    }

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::FragmentInWrongView);
}

#[test]
fn promoted_derived_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let index = projection
        .segments
        .iter()
        .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
        .expect("fixture carries derived controls");
    {
        let segment = &mut projection.segments[index];
        segment.origin = SegmentOrigin::SourceFragment;
        segment.segment_kind = ReaderSegmentKind::Text;
        segment.text = None;
    }

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::SegmentSourceMismatch);
}

#[test]
fn stripped_source_span_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let index = segment_index(&projection, "t0");
    projection.segments[index].span = None;

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::SegmentSourceMismatch);
}

#[test]
fn derived_invented_span_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let index = projection
        .segments
        .iter()
        .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
        .expect("fixture carries derived controls");
    projection.segments[index].span = Some(ReaderFragmentSpan::new(FragmentRef::new("t0"), 0, 1));

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::DerivedInventedSourceSpan);
}

#[test]
fn permuted_segment_order_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    let view = projection
        .views
        .iter_mut()
        .find(|view| view.kind == ReaderViewKind::Paragraph && view.element_ref.as_str() == "e5")
        .expect("paragraph e5");
    assert!(
        view.segment_refs.len() >= 2,
        "e5 owns [t1, derived:tab, t2]"
    );
    view.segment_refs.swap(0, 1);

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(
        &projection,
        &records,
        VerifyCode::SegmentMembershipOrOrderMismatch,
    );
}

#[test]
fn resolved_reference_after_reseal_is_caught() {
    let records = fixture_records();
    let mut projection = sealed_projection(&records);
    let original = seal_hash(&projection);

    assert!(
        projection
            .references
            .iter()
            .any(|reference| !reference.resolved),
        "fixture carries unresolved references"
    );
    projection.references[0].resolved = true;

    projection.reseal();
    assert_ne!(seal_hash(&projection), original, "seal must move");
    expect_finding(&projection, &records, VerifyCode::ReferenceResolved);
}
