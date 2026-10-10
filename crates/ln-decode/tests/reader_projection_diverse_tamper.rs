//! S04 diverse resealed semantic-tamper battery.
//!
//! The single mixed fixture covered by the S03 tamper battery
//! (`reader_projection_tamper.rs`) is not enough: the reader must reject
//! semantic rewrites across the diverse shapes frozen in T01. This battery
//! takes the representative supported fixtures — documented controls, residual
//! and tails, nested notes, fields/revisions and combined navigation — and for
//! each one:
//!
//! 1. asserts the untampered, `reseal()`ed projection verifies `Ok`;
//! 2. applies the semantic tampers that fixture's shape supports;
//! 3. re-`reseal()`s, asserts the content seal moved, and asserts the
//!    independent `reader_verifier` still rejects the rewrite with the expected
//!    `VerifyCode`.
//!
//! The seal is an integrity/version pin only: it never feeds verification, so a
//! moved `content_hash` is asserted alongside every `VerifyCode`. The builder
//! and the seal are never trusted — the baseline is re-verified before mutation.
//!
//! Tamper classes: loss (`MissingFragmentReference`), cross-view ownership
//! reassignment (`FragmentInWrongView`), derived→source promotion
//! (`SegmentSourceMismatch`), source-span stripping (`SegmentSourceMismatch`),
//! in-view order permutation (`SegmentMembershipOrOrderMismatch`) and a
//! resolved reference (`ReferenceResolved`). Only the public API is used.
//!
//! Non-claims: `[bounded]` to the five self-authored non-legal synthetic
//! fixtures named here; this is not corpus coverage, not source authenticity
//! and not a legal-completeness claim. R1000 stays active. Raw decoded legal
//! text is never logged.

use std::collections::HashSet;

use ln_decode::reader_contract::{ReaderFragmentSpan, ReaderSegmentKind};
use ln_decode::reader_gate::{ReaderSourceClass, classify_source, gate_reader};
use ln_decode::reader_projection::{ReaderProjection, SegmentOrigin, build_projection};
use ln_decode::reader_verifier::{VerifyCode, verify_projection};
use ln_decode::source_package::{Limits, Record, TextRecord, capture};

// ---------------------------------------------------------------- fixtures #

struct Fixture {
    file: &'static str,
    xml: &'static str,
    sha256: &'static str,
}

const REPRESENTATIVE: &[Fixture] = &[
    Fixture {
        file: "controls.xml",
        xml: include_str!("fixtures/reader/diverse/controls.xml"),
        sha256: "86440c8cf2f16b88f9da919c77f04e9a2487ed3a0032305dd195aaf48e40988f",
    },
    Fixture {
        file: "residual-and-tails.xml",
        xml: include_str!("fixtures/reader/diverse/residual-and-tails.xml"),
        sha256: "424f7f117255472e320a1d86adb2a63d8985b97b435a262e3d2403c2767a6834",
    },
    Fixture {
        file: "notes-nested.xml",
        xml: include_str!("fixtures/reader/diverse/notes-nested.xml"),
        sha256: "36d874f81bc456583687b6189d21ae2c7f5c3621a0373c6248cbe733e4fa9a75",
    },
    Fixture {
        file: "fields-revisions.xml",
        xml: include_str!("fixtures/reader/diverse/fields-revisions.xml"),
        sha256: "4e6ca62093eefb95fa49471b41de072a8e144ac2a867ffe894c0ce507ff17b0e",
    },
    Fixture {
        file: "navigation-demo.xml",
        xml: include_str!("fixtures/reader/diverse/navigation-demo.xml"),
        sha256: "b12bed26bde92a5516c9e2cbfe25333168cdd32101c3a4790c77357554c0a3f0",
    },
];

fn fixture(name: &str) -> &'static Fixture {
    REPRESENTATIVE
        .iter()
        .find(|fixture| fixture.file == name)
        .unwrap_or_else(|| panic!("fixture {name} is not declared"))
}

// ------------------------------------------------------------------ helpers #

fn capture_fixture(fixture: &Fixture) -> Vec<Record> {
    let package = capture(fixture.xml.as_bytes(), &Limits::default())
        .unwrap_or_else(|error| panic!("{} must capture: {error:?}", fixture.file));
    assert_eq!(
        package.manifest().source.sha256,
        fixture.sha256,
        "{} content changed; re-pin the sha256 and the handwritten oracle",
        fixture.file
    );
    package.records().to_vec()
}

fn text_record<'a>(records: &'a [Record], fragment: &str) -> &'a TextRecord {
    records
        .iter()
        .find_map(|record| match record {
            Record::Text(text) if text.id == fragment => Some(text),
            _ => None,
        })
        .unwrap_or_else(|| panic!("fragment {fragment} must name a substrate text record"))
}

fn seal_hash(projection: &ReaderProjection) -> String {
    projection
        .content_hash()
        .expect("projection must be sealed")
        .to_string()
}

fn expect_finding(
    projection: &ReaderProjection,
    records: &[Record],
    expected: VerifyCode,
    context: &str,
) {
    match verify_projection(projection, records) {
        Ok(()) => panic!("{context}: tamper must be caught after reseal"),
        Err(findings) => assert!(
            findings.iter().any(|finding| finding.code == expected),
            "{context}: expected {expected:?}, got {:?}",
            findings
                .iter()
                .map(|finding| finding.code)
                .collect::<Vec<_>>()
        ),
    }
}

// -------------------------------------------------------------------- tampers #

/// Loss: drop a source segment and every view reference to it. The substrate
/// still owns the fragment, so coverage must report it as missing.
fn drop_first_source_segment(projection: &mut ReaderProjection, _records: &[Record]) {
    let index = projection
        .segments
        .iter()
        .position(|segment| segment.origin == SegmentOrigin::SourceFragment)
        .expect("a source segment");
    let victim = projection.segments[index].id.clone();
    projection.segments.remove(index);
    for view in &mut projection.views {
        view.segment_refs.retain(|id| id != &victim);
    }
}

/// Ownership reassignment: move a source segment to a different view while
/// keeping its fragment. The verifier recomputes the fragment's owner view.
fn reassign_first_source_segment(projection: &mut ReaderProjection, _records: &[Record]) {
    let index = projection
        .segments
        .iter()
        .position(|segment| segment.origin == SegmentOrigin::SourceFragment)
        .expect("a source segment");
    let source_view = projection.segments[index].view.clone();
    let target = projection
        .views
        .iter()
        .find(|view| view.id != source_view)
        .expect("a second view to receive the segment")
        .id
        .clone();
    let victim = projection.segments[index].id.clone();
    for view in &mut projection.views {
        if view.id == source_view {
            view.segment_refs.retain(|id| id != &victim);
        }
    }
    projection.segments[index].view = target.clone();
    for view in &mut projection.views {
        if view.id == target {
            view.segment_refs.push(victim.clone());
        }
    }
}

/// Derived promotion: rewrite a documented control as if it were a source text
/// segment, borrowing a real fragment and a whole-fragment span to fabricate
/// provenance it can never have.
fn promote_first_derived(projection: &mut ReaderProjection, records: &[Record]) {
    let index = projection
        .segments
        .iter()
        .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
        .expect("a derived segment");
    let victim = projection
        .segments
        .iter()
        .find(|segment| segment.origin == SegmentOrigin::SourceFragment)
        .and_then(|segment| segment.fragment_ref.clone())
        .expect("a source fragment to borrow");
    let text = text_record(records, victim.as_str());
    let end = text.value.len();
    let slot = text.slot;
    let segment = &mut projection.segments[index];
    segment.origin = SegmentOrigin::SourceFragment;
    segment.segment_kind = ReaderSegmentKind::Text;
    segment.fragment_ref = Some(victim.clone());
    segment.span = Some(ReaderFragmentSpan::new(victim, 0, end));
    segment.slot = Some(slot);
    segment.text = None;
}

/// Span strip: a source segment that no longer spans its whole validated
/// fragment.
fn strip_first_source_span(projection: &mut ReaderProjection, _records: &[Record]) {
    let segment = projection
        .segments
        .iter_mut()
        .find(|segment| segment.origin == SegmentOrigin::SourceFragment)
        .expect("a source segment");
    segment.span = None;
}

/// Order permutation: swap two segments inside one view while keeping the same
/// membership, so only the document-event order is wrong.
fn permute_first_multi_segment_view(projection: &mut ReaderProjection, _records: &[Record]) {
    let view = projection
        .views
        .iter_mut()
        .find(|view| view.segment_refs.len() >= 2)
        .expect("a view owning at least two segments");
    view.segment_refs.swap(0, 1);
}

/// Resolved reference: a reader reference must never claim resolution in S04.
fn resolve_first_reference(projection: &mut ReaderProjection, _records: &[Record]) {
    let reference = projection
        .references
        .iter_mut()
        .find(|reference| !reference.resolved)
        .expect("an unresolved reference");
    reference.resolved = true;
}

// ------------------------------------------------------------------- battery #

fn run_tamper(
    fixture: &Fixture,
    base: &ReaderProjection,
    records: &[Record],
    label: &str,
    mutate: fn(&mut ReaderProjection, &[Record]),
    expected: VerifyCode,
) {
    let mut projection = base.clone();
    let before = seal_hash(&projection);
    assert!(
        verify_projection(&projection, records).is_ok(),
        "{}: {label} baseline must verify",
        fixture.file
    );
    mutate(&mut projection, records);
    projection.reseal();
    assert_ne!(
        seal_hash(&projection),
        before,
        "{}: {label} must move the content seal",
        fixture.file
    );
    expect_finding(
        &projection,
        records,
        expected,
        &format!("{}: {label}", fixture.file),
    );
}

/// Validates the fixture, verifies the untampered projection, applies every
/// tamper the fixture's shape supports, and returns the applied labels.
fn apply_tampers(fixture: &Fixture) -> Vec<&'static str> {
    let records = capture_fixture(fixture);
    assert_eq!(
        classify_source(&records),
        ReaderSourceClass::SupportedWordml,
        "{} must classify as supported WordML",
        fixture.file
    );
    assert_eq!(
        gate_reader(&records),
        Ok(ReaderSourceClass::SupportedWordml),
        "{} must pass the gate",
        fixture.file
    );
    let mut base = build_projection(&records)
        .unwrap_or_else(|error| panic!("{} must project: {error:?}", fixture.file));
    base.reseal();
    assert!(
        verify_projection(&base, &records).is_ok(),
        "{}: untampered projection must verify",
        fixture.file
    );

    let mut applied = Vec::new();
    run_tamper(
        fixture,
        &base,
        &records,
        "loss",
        drop_first_source_segment,
        VerifyCode::MissingFragmentReference,
    );
    applied.push("loss");
    run_tamper(
        fixture,
        &base,
        &records,
        "ownership reassignment",
        reassign_first_source_segment,
        VerifyCode::FragmentInWrongView,
    );
    applied.push("ownership_reassignment");
    run_tamper(
        fixture,
        &base,
        &records,
        "span strip",
        strip_first_source_span,
        VerifyCode::SegmentSourceMismatch,
    );
    applied.push("span_strip");

    if base
        .segments
        .iter()
        .any(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
    {
        run_tamper(
            fixture,
            &base,
            &records,
            "derived promotion",
            promote_first_derived,
            VerifyCode::SegmentSourceMismatch,
        );
        applied.push("derived_promotion");
    }
    if base.views.iter().any(|view| view.segment_refs.len() >= 2) {
        run_tamper(
            fixture,
            &base,
            &records,
            "order permutation",
            permute_first_multi_segment_view,
            VerifyCode::SegmentMembershipOrOrderMismatch,
        );
        applied.push("order_permutation");
    }
    if base.references.iter().any(|reference| !reference.resolved) {
        run_tamper(
            fixture,
            &base,
            &records,
            "resolved reference",
            resolve_first_reference,
            VerifyCode::ReferenceResolved,
        );
        applied.push("resolved_reference");
    }
    applied
}

// -------------------------------------------------------------------- tests #

#[test]
fn representative_set_is_exactly_the_five_supported_fixtures() {
    assert_eq!(REPRESENTATIVE.len(), 5, "five representative fixtures");
    let names: Vec<&str> = REPRESENTATIVE.iter().map(|fixture| fixture.file).collect();
    assert_eq!(
        names,
        [
            "controls.xml",
            "residual-and-tails.xml",
            "notes-nested.xml",
            "fields-revisions.xml",
            "navigation-demo.xml",
        ]
    );
}

#[test]
fn every_representative_fixture_verifies_untampered() {
    for fixture in REPRESENTATIVE {
        let records = capture_fixture(fixture);
        assert_eq!(
            classify_source(&records),
            ReaderSourceClass::SupportedWordml,
            "{} must classify as supported WordML",
            fixture.file
        );
        assert_eq!(
            gate_reader(&records),
            Ok(ReaderSourceClass::SupportedWordml),
            "{} must pass the gate",
            fixture.file
        );
        let projection = build_projection(&records)
            .unwrap_or_else(|error| panic!("{} must project: {error:?}", fixture.file));
        assert!(
            verify_projection(&projection, &records).is_ok(),
            "{}: untampered projection must verify",
            fixture.file
        );
        let mut sealed = projection.clone();
        sealed.reseal();
        assert!(
            verify_projection(&sealed, &records).is_ok(),
            "{}: resealing must not affect verification",
            fixture.file
        );
    }
}

#[test]
fn diverse_resealed_semantic_tamper_battery_is_caught() {
    let mut covered: HashSet<&'static str> = HashSet::new();
    for fixture in REPRESENTATIVE {
        for label in apply_tampers(fixture) {
            covered.insert(label);
        }
    }
    assert_eq!(
        covered,
        HashSet::from([
            "loss",
            "ownership_reassignment",
            "derived_promotion",
            "span_strip",
            "order_permutation",
            "resolved_reference",
        ]),
        "the battery must exercise all six tamper classes across the representative fixtures"
    );
}

#[test]
fn controls_exercises_derived_and_reference_tampers() {
    let applied: HashSet<&str> = apply_tampers(fixture("controls.xml")).into_iter().collect();
    assert!(
        applied.contains("derived_promotion"),
        "controls.xml carries documented controls"
    );
    assert!(
        applied.contains("order_permutation"),
        "controls.xml owns multi-segment paragraphs"
    );
    assert!(
        applied.contains("resolved_reference"),
        "controls.xml carries a reference"
    );
}

#[test]
fn fields_revisions_exercises_reference_tamper_without_derived() {
    let applied: HashSet<&str> = apply_tampers(fixture("fields-revisions.xml"))
        .into_iter()
        .collect();
    assert!(
        applied.contains("resolved_reference"),
        "fields-revisions.xml carries field references"
    );
    assert!(
        applied.contains("order_permutation"),
        "the revision paragraph owns two segments"
    );
    assert!(
        !applied.contains("derived_promotion"),
        "fields-revisions.xml carries no documented control to promote"
    );
}
