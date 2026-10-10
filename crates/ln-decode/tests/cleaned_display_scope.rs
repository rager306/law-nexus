//! S03 T05 (R29-F06): cross-cutting controls proving that retained source
//! content (field codes, revisions, unknown/foreign elements, inert payload)
//! stays present, typed, addressable and unsuppressed on the cleaned wire.
//!
//! These are wire-level controls: the emitted artifact is read back through
//! `read_cleaned_wire` and re-checked with the independent
//! `cleaned_verifier::verify_cleaned_wire`. The reader-level oracles are not
//! duplicated here:
//! - `reader_projection_diverse.rs::fields_revisions_keep_typed_references_and_revision_semantics`
//! - `reader_projection_diverse.rs::navigation_demo_combines_all_shapes`
//! - `cleaned_projection_wire.rs::full_text_is_carried_inline_exactly_once`
//!
//! The positive tamper (`display_scope`) control lives in T04; this suite is
//! positive-only. `[bounded]` to the two self-authored non-legal synthetic
//! fixtures named here (`fields-revisions.xml`, `navigation-demo.xml`): not
//! corpus coverage, not source authenticity and not a legal-completeness claim.
//! R1000 stays active. Raw decoded legal text is never logged.

use std::collections::{HashMap, HashSet};

use ln_decode::cleaned_verifier::verify_cleaned_wire;
use ln_decode::cleaned_wire::{
    CleanedProjection, KIND_POLICIES, KIND_REFERENCE, POLICY_DISPLAY_SCOPE, WireCompletion,
    WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_contract::{ReaderReferenceType, ReaderSemantic};
use ln_decode::reader_projection::{ReaderProjection, SegmentOrigin, build_projection};
use ln_decode::source_package::{Limits, Package, Record, capture};

const FIELDS_REVISIONS: &str = include_str!("fixtures/reader/diverse/fields-revisions.xml");
const NAVIGATION_DEMO: &str = include_str!("fixtures/reader/diverse/navigation-demo.xml");

// ---------------------------------------------------------------- helpers #

fn project(xml: &str) -> (Package, ReaderProjection) {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let projection =
        build_projection(package.records()).expect("fixture must project in the reader");
    (package, projection)
}

fn exported(package: &Package, projection: &ReaderProjection) -> String {
    export_cleaned_projection(
        package,
        projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("a verified package and its projection must export")
}

/// Finds the single artifact line whose `kind` token matches `kind`.
fn line_of_kind<'a>(document: &'a str, kind: &str) -> &'a str {
    let needle = format!("\"kind\":\"{kind}\"");
    document
        .split_terminator('\n')
        .find(|line| line.contains(&needle))
        .unwrap_or_else(|| panic!("document must contain a {kind} line"))
}

/// Local raw-line extractor for a top-level string value. The writer emits one
/// compact ascending-key JSON object per line; the closed policies tokens carry
/// no escapes, so an exact `"key":"value"` slice is unambiguous. Deliberately
/// local: the module under test shares none of it.
fn string_value(line: &str, key: &str) -> Option<String> {
    let needle = format!("\"{key}\":\"");
    let start = line.find(&needle)? + needle.len();
    let rest = &line[start..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}

/// Local raw-line extractor for a top-level unsigned value.
fn unsigned_value(line: &str, key: &str) -> Option<u64> {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle)? + needle.len();
    let rest = &line[start..];
    let end = rest
        .find(|character: char| !character.is_ascii_digit())
        .unwrap_or(rest.len());
    if end == 0 {
        return None;
    }
    rest[..end].parse().ok()
}

/// (a) No suppression and no duplication: every substrate `TextRecord` is
/// attributed to exactly one source segment.
/// (e) Reversibility: every source segment is addressable by
/// `fragment_ref` + `slot` + `span` (+ `element_ref`), every reference by
/// `element_ref` + `source_pos`.
fn assert_retained_addressable_and_unsuppressed(package: &Package, readback: &CleanedProjection) {
    let substrate: HashMap<&str, &str> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Text(text) => Some((text.id.as_str(), text.value.as_str())),
            Record::Element(_) => None,
        })
        .collect();

    let mut attributed: HashMap<String, usize> = HashMap::new();
    for segment in &readback.projection.segments {
        match segment.origin {
            SegmentOrigin::SourceFragment => {
                let fragment = segment.fragment_ref.as_ref().unwrap_or_else(|| {
                    panic!(
                        "source segment {} must carry a fragment_ref",
                        segment.id.as_str()
                    )
                });
                assert!(
                    segment.slot.is_some(),
                    "source segment {} must carry a slot",
                    segment.id.as_str()
                );
                assert!(
                    segment.span.is_some(),
                    "source segment {} must carry a span",
                    segment.id.as_str()
                );
                assert!(
                    !segment.element_ref.as_str().is_empty(),
                    "source segment {} must carry an element_ref",
                    segment.id.as_str()
                );
                *attributed.entry(fragment.as_str().to_string()).or_insert(0) += 1;
            }
            SegmentOrigin::Derived(_) => {
                assert!(
                    segment.fragment_ref.is_none(),
                    "derived segment {} must not carry a fragment_ref",
                    segment.id.as_str()
                );
                assert!(
                    segment.slot.is_none(),
                    "derived segment {} must not carry a slot",
                    segment.id.as_str()
                );
                assert!(
                    segment.span.is_none(),
                    "derived segment {} must not carry a span",
                    segment.id.as_str()
                );
            }
        }
    }

    for id in substrate.keys() {
        assert_eq!(
            attributed.get(*id).copied(),
            Some(1),
            "substrate fragment {id} must be attributed exactly once (no suppression)"
        );
    }
    assert_eq!(
        attributed.len(),
        substrate.len(),
        "no fragment outside the substrate may be attributed"
    );
    assert!(
        attributed.values().all(|count| *count == 1),
        "no fragment may be attributed twice"
    );

    for reference in &readback.projection.references {
        assert!(
            !reference.element_ref.as_str().is_empty(),
            "reference {} must carry an element_ref",
            reference.id.as_str()
        );
    }
}

fn expect_verified(document: &str, package: &Package, label: &str) {
    verify_cleaned_wire(document, package).unwrap_or_else(|findings| {
        panic!("{label}: independent verifier must accept the artifact: {findings:?}")
    });
}

// ---------------------------------------------------------------- controls #

/// (b) The raw policies line declares the retained display scope and the whole
/// artifact still passes the independent verifier.
#[test]
fn policies_declare_retained_display_scope_and_verify() {
    for (label, xml) in [
        ("fields-revisions.xml", FIELDS_REVISIONS),
        ("navigation-demo.xml", NAVIGATION_DEMO),
    ] {
        let (package, projection) = project(xml);
        let document = exported(&package, &projection);

        assert_eq!(
            POLICY_DISPLAY_SCOPE, "source_content_retained_no_suppression",
            "the closed display-scope token must name no suppression"
        );
        let policies = line_of_kind(&document, KIND_POLICIES);
        assert_eq!(
            string_value(policies, "display_scope").as_deref(),
            Some(POLICY_DISPLAY_SCOPE),
            "{label}: policies must declare the retained display scope"
        );

        let readback = read_cleaned_wire(&document).expect("canonical artifact must read back");
        assert_retained_addressable_and_unsuppressed(&package, &readback);

        expect_verified(&document, &package, label);
    }
}

/// (c) Field codes and the revision pair keep their typed semantics and stay
/// contextual across the cleaned wire. Reader-level counterpart:
/// `reader_projection_diverse.rs::fields_revisions_keep_typed_references_and_revision_semantics`.
#[test]
fn fields_revisions_keep_typed_semantics_on_cleaned_wire() {
    let (package, projection) = project(FIELDS_REVISIONS);
    let document = exported(&package, &projection);
    let readback = read_cleaned_wire(&document).expect("canonical artifact must read back");

    let semantics: HashSet<ReaderSemantic> = readback
        .projection
        .segments
        .iter()
        .map(|segment| segment.semantic)
        .collect();
    for expected in [
        ReaderSemantic::FieldCode,
        ReaderSemantic::RevisionInsertion,
        ReaderSemantic::RevisionDeletion,
    ] {
        assert!(
            semantics.contains(&expected),
            "retained content must keep the {} semantic",
            expected.as_str()
        );
    }

    for segment in &readback.projection.segments {
        if matches!(
            segment.semantic,
            ReaderSemantic::FieldCode
                | ReaderSemantic::RevisionInsertion
                | ReaderSemantic::RevisionDeletion
        ) {
            assert!(
                segment.contextual,
                "{}: retained contextual content must stay contextual",
                segment.id.as_str()
            );
        }
    }

    assert_retained_addressable_and_unsuppressed(&package, &readback);
    expect_verified(&document, &package, "fields-revisions.xml");
}

/// (d) Unknown and foreign elements stay typed, addressable references on the
/// cleaned wire (never promoted to a view or suppressed). Reader-level
/// counterpart: `reader_projection_diverse.rs::navigation_demo_combines_all_shapes`.
#[test]
fn navigation_demo_retains_unknown_and_foreign_references_addressably() {
    let (package, projection) = project(NAVIGATION_DEMO);
    let document = exported(&package, &projection);
    let readback = read_cleaned_wire(&document).expect("canonical artifact must read back");

    let retained: Vec<_> = readback
        .projection
        .references
        .iter()
        .filter(|reference| {
            matches!(
                reference.reference_type,
                ReaderReferenceType::UnknownWordmlElement | ReaderReferenceType::ForeignElement
            )
        })
        .collect();
    assert!(
        !retained.is_empty(),
        "the demo must retain unknown/foreign references, not suppress them"
    );

    let kinds: HashSet<&str> = retained
        .iter()
        .map(|reference| reference.reference_type.as_str())
        .collect();
    assert_eq!(
        kinds,
        HashSet::from(["unknown_wordml_element", "foreign_element"]),
        "unknown/foreign references keep their closed types"
    );

    // Addressability is observable on the raw reference lines: a non-empty
    // `element_ref` and a numeric `source_pos` are always emitted.
    let reference_lines: Vec<&str> = document
        .split_terminator('\n')
        .filter(|line| line.contains(&format!("\"kind\":\"{KIND_REFERENCE}\"")))
        .collect();
    assert!(
        !reference_lines.is_empty(),
        "the demo must emit at least one reference line"
    );
    for line in &reference_lines {
        assert!(
            string_value(line, "element_ref").is_some_and(|value| !value.is_empty()),
            "a reference line must carry a non-empty element_ref"
        );
        assert!(
            unsigned_value(line, "source_pos").is_some(),
            "a reference line must carry a source_pos"
        );
    }

    assert_retained_addressable_and_unsuppressed(&package, &readback);
    expect_verified(&document, &package, "navigation-demo.xml");
}
