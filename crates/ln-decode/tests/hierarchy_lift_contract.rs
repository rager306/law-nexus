//! T02 contract battery for the ladder-bound hierarchy lift.
//!
//! Handwritten oracle: this battery shares no private code with the module
//! under test. It builds decoded [`ParsedBlock`] streams, runs the public
//! extractor ([`extract_hierarchy_candidates`]) and then drives the lift on
//! the *embedded* `document_groups` catalog, asserting the fail-closed
//! ladder placement, the `Unknown` accounting and the `text_only`
//! non-normative barrier.
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic blocks in
//! this file and to the shipped ontology catalog; never corpus coverage, never
//! source authenticity, never a legal-completeness claim. R1000 stays active.
//! Raw decoded legal text is never logged by the battery.

use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use ln_decode::hierarchy::{HierarchyCandidateReport, extract_hierarchy_candidates};
use ln_decode::hierarchy_lift::{
    HIERARCHY_LIFT_NON_CLAIMS, HierarchyLiftReport, LiftDisposition, LiftUnknownReason,
    detect_and_lift, lift_hierarchy_over_group,
};
use ln_decode::structural_profile::{
    DetectionFactor, GroupDetection, StructuralProfile, UnknownReason,
};

// ------------------------------------------------------------ preparation #

fn profile() -> StructuralProfile {
    StructuralProfile::embedded().expect("embedded ontology catalog must load")
}

fn block(text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        ParagraphStyle::BodyText,
        SourceLocation::new(
            SourceStreamId::parse("test:m224-s05-hierarchy-lift").expect("static stream id"),
            SourceSpan::try_new(0, text.len()).expect("non-empty block text"),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid synthetic block")
}

/// Decode a synthetic marker stream: blocks + first-wins candidates.
fn decode(texts: &[&str]) -> (Vec<ParsedBlock>, HierarchyCandidateReport) {
    let blocks: Vec<ParsedBlock> = texts.iter().map(|text| block(text)).collect();
    let candidates = extract_hierarchy_candidates(&blocks);
    (blocks, candidates)
}

/// One `statya` unit, one numbered `punkt` subunit and one `razdel` container,
/// in document order. `razdel` is deliberately absent from the federal_law
/// ladder (R8-08) so it must stay Unknown.
const MARKER_STREAM: &[&str] = &[
    "Статья 1. Общие положения",
    "1) Первое требование.",
    "Раздел 2. Особенная часть",
];

fn unknown_reasons(report: &HierarchyLiftReport) -> Vec<LiftUnknownReason> {
    report
        .placements
        .iter()
        .filter_map(|placement| match placement {
            LiftDisposition::Unknown { reason } => Some(*reason),
            _ => None,
        })
        .collect()
}

// ------------------------------------------------------------- appliances #

#[test]
fn federal_law_binds_statya_and_punkt_to_unit_and_subunit() {
    let profile = profile();
    let (blocks, candidates) = decode(&["Статья 1. Общие положения", "1) Первое требование."]);
    assert_eq!(candidates.unique_count(), 2, "one statya + one punkt");

    let report = detect_and_lift(
        &profile,
        Some("exports/npa/federalnyi-zakon_44-fz.xml"),
        None,
        None,
        &blocks,
        &candidates,
    );

    assert!(
        matches!(
            &report.detection,
            GroupDetection::Bound { group, factor: DetectionFactor::NeedleAndProbe }
                if group == "federal_law@v1"
        ),
        "federal law must bind with both factors: {:?}",
        report.detection
    );
    assert_eq!(report.group, "federal_law@v1");
    assert_eq!(report.markers_total, 2);
    assert_eq!(report.bound, 2, "statya + punkt both land on the ladder");
    assert_eq!(report.unknown, 0);
    assert!(!report.non_normative);
    assert_eq!(report.per_role.get("unit"), Some(&1));
    assert_eq!(report.per_role.get("subunit"), Some(&1));
    assert!(report.unmapped_tokens.is_empty());
    assert_eq!(
        report.placements,
        vec![
            LiftDisposition::Bound {
                token: "statya".to_owned(),
                role: "unit".to_owned(),
            },
            LiftDisposition::Bound {
                token: "punkt".to_owned(),
                role: "subunit".to_owned(),
            },
        ]
    );
}

#[test]
fn undeclared_razdel_stays_unknown_and_is_counted_unmapped() {
    let profile = profile();
    let (_, candidates) = decode(MARKER_STREAM);
    assert_eq!(candidates.unique_count(), 3);

    let report = lift_hierarchy_over_group(&profile, "federal_law@v1", &candidates);

    // Fail-closed: razdel has no ladder entry in federal_law (R8-08) and is
    // NOT silently defaulted to a statya-level placement.
    assert_eq!(report.markers_total, 3);
    assert_eq!(report.bound, 2);
    assert_eq!(report.unknown, 1);
    assert!(
        report.unmapped_tokens.get("razdel").copied().unwrap_or(0) > 0,
        "razdel must be an unmapped token: {:?}",
        report.unmapped_tokens
    );
    assert_eq!(
        unknown_reasons(&report),
        vec![LiftUnknownReason::TokenNotInLadder]
    );
}

#[test]
fn text_only_court_practice_is_non_normative_with_zero_placements() {
    let profile = profile();
    let (blocks, candidates) = decode(MARKER_STREAM);

    let report = detect_and_lift(
        &profile,
        Some("exports/courts/court_123.xml"),
        None,
        None,
        &blocks,
        &candidates,
    );

    assert!(
        matches!(
            &report.detection,
            GroupDetection::Bound { group, factor: DetectionFactor::Needle }
                if group == "court_practice"
        ),
        "text-only binds by needle only: {:?}",
        report.detection
    );
    assert!(
        report.non_normative,
        "text_only profile is the non-normative barrier"
    );
    assert_eq!(report.markers_total, 3);
    assert_eq!(report.bound, 0, "no normative placement for text-only");
    assert_eq!(report.unknown, 0);
    assert!(report.per_role.is_empty());
    assert!(report.unmapped_tokens.is_empty());
    assert!(
        report
            .placements
            .iter()
            .all(|placement| matches!(placement, LiftDisposition::NonNormative)),
        "every marker is non-normative: {:?}",
        report.placements
    );
}

#[test]
fn text_only_barrier_is_load_bearing() {
    // Negative self-check for the S04 barrier: court_practice is text_only with
    // an EMPTY ladder. If the `if group.text_only` branch were removed, the
    // report would fall through to the ladder, set non_normative=false and
    // count every candidate Unknown{TokenNotInLadder}. This test therefore
    // fails on barrier removal even though the ladder is empty.
    let profile = profile();
    let (_, candidates) = decode(&["Статья 1. X", "1) Y"]);
    let report = lift_hierarchy_over_group(&profile, "court_practice", &candidates);
    assert!(report.non_normative, "barrier must hold");
    assert_eq!(
        report.unknown, 0,
        "text_only never attempts a normative placement"
    );
    assert!(report.unmapped_tokens.is_empty());
}

#[test]
fn undetectable_group_fails_closed_as_group_unknown() {
    let profile = profile();
    let (blocks, candidates) = decode(&["Статья 1. Общие положения"]);
    let report = detect_and_lift(&profile, None, None, None, &blocks, &candidates);

    assert!(
        matches!(
            report.detection,
            GroupDetection::Unknown {
                reason: UnknownReason::NoMetadata
            }
        ),
        "no metadata is Unknown: {:?}",
        report.detection
    );
    assert_eq!(report.group, "");
    assert_eq!(report.bound, 0);
    assert_eq!(report.unknown, report.markers_total);
    assert_eq!(report.markers_total, 1);
    assert_eq!(
        unknown_reasons(&report),
        vec![LiftUnknownReason::GroupUnknown; report.markers_total]
    );
}

#[test]
fn metadata_but_no_structure_fails_closed_as_group_conflict() {
    // Metadata names federal_law, but the block carries no statya marker, so
    // the structural probe finds nothing: ProbeConflict -> GroupConflict.
    let profile = profile();
    let (blocks, candidates) = decode(&["Обычный абзац без маркера."]);
    assert_eq!(candidates.unique_count(), 0, "no marker extracts");
    let report = detect_and_lift(
        &profile,
        Some("exports/npa/federalnyi-zakon_44-fz.xml"),
        None,
        None,
        &blocks,
        &candidates,
    );

    assert!(
        matches!(
            report.detection,
            GroupDetection::Unknown {
                reason: UnknownReason::ProbeConflict { .. }
            }
        ),
        "metadata without structure is a conflict: {:?}",
        report.detection
    );
    assert_eq!(report.group, "federal_law@v1");
    assert_eq!(
        report.markers_total, 0,
        "empty candidates are not a fake success"
    );
    assert_eq!(report.bound, 0);
    assert_eq!(report.unknown, 0);
}

#[test]
fn missing_group_profile_is_fail_closed() {
    let profile = profile();
    let (_, candidates) = decode(&["Статья 1. Общие положения"]);
    let report = lift_hierarchy_over_group(&profile, "does-not-exist@v1", &candidates);

    assert_eq!(report.group, "does-not-exist@v1");
    assert!(matches!(report.detection, GroupDetection::Unknown { .. }));
    assert_eq!(report.bound, 0);
    assert_eq!(report.unknown, report.markers_total);
    assert_eq!(
        unknown_reasons(&report),
        vec![LiftUnknownReason::NoGroupProfile; report.markers_total]
    );
}

#[test]
fn empty_candidate_stream_is_zero_markers_not_fake_success() {
    let profile = profile();
    let candidates = extract_hierarchy_candidates(&[]);
    assert_eq!(candidates.unique_count(), 0);

    let report = lift_hierarchy_over_group(&profile, "federal_law@v1", &candidates);
    assert_eq!(report.markers_total, 0);
    assert_eq!(report.bound, 0);
    assert_eq!(report.unknown, 0);
    assert!(!report.non_normative);
    assert!(report.placements.is_empty());
    assert!(report.unmapped_tokens.is_empty());

    let report = detect_and_lift(&profile, None, None, None, &[], &candidates);
    assert_eq!(report.markers_total, 0);
    assert_eq!(report.unknown, 0);
    assert!(report.placements.is_empty());
}

#[test]
fn lift_non_claims_are_declared() {
    assert!(
        HIERARCHY_LIFT_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("ComponentConcept"))
    );
    assert!(
        HIERARCHY_LIFT_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("fail-closed"))
    );
    let profile = profile();
    let candidates = extract_hierarchy_candidates(&[]);
    let report = lift_hierarchy_over_group(&profile, "federal_law@v1", &candidates);
    assert_eq!(report.non_claims, HIERARCHY_LIFT_NON_CLAIMS.to_vec());
}
