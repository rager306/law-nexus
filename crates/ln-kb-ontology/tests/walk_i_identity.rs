//! WALK-I: ComponentConcept identity grows from first appearance in a Work chain.
//!
//! Not C0, not 118-step XML, not force, not CTV text, not Applicable.
//! The YAML 0118 registry is not the CC universe.

use ln_kb_ontology::domain::{
    grow_identity, map_hierarchy_marker, HierarchyMap, HierarchyMapOutcome, HierarchyMarker,
    IdentitySnapshot, WriteSetError,
};

const WORK: &str = "work:ru:federal:zakon:2013-04-05:44-fz";
const MINT: &[&str] = &["glava", "statya"];

fn marker(level: &str, number: &str) -> HierarchyMarker {
    HierarchyMarker::try_new(Some(WORK), level, number, None).expect("marker")
}

fn marker_path(level: &str, number: &str, path: &str) -> HierarchyMarker {
    HierarchyMarker::try_new_with_path(Some(WORK), level, number, Some(path), None).expect("marker")
}

#[test]
fn first_appearance_mints_and_second_snapshot_reuses() {
    let seed = IdentitySnapshot {
        markers: vec![marker("statya", "53"), marker("statya", "1")],
    };
    let later = IdentitySnapshot {
        markers: vec![marker("statya", "1")],
    };
    let report = grow_identity(HierarchyMap::empty(), &[seed, later], MINT).expect("grow");
    assert_eq!(report.minted, 2);
    assert_eq!(report.reused, 1);
    assert_eq!(report.skipped, 0);
    match map_hierarchy_marker(&report.map, &marker("statya", "53")) {
        HierarchyMapOutcome::Bound { component } => {
            assert!(component.as_str().starts_with("cc:walk:"));
            assert!(component.as_str().contains("statya-53"));
        }
        other => panic!("seed-only article must stay Bound after later snapshot: {other:?}"),
    }
    match map_hierarchy_marker(&report.map, &marker("statya", "1")) {
        HierarchyMapOutcome::Bound { .. } => {}
        other => panic!("reused article missing: {other:?}"),
    }
}

#[test]
fn new_key_on_later_snapshot_mints_separately() {
    let seed = IdentitySnapshot {
        markers: vec![marker("statya", "1")],
    };
    let later = IdentitySnapshot {
        markers: vec![marker("statya", "1"), marker("statya", "114")],
    };
    let report = grow_identity(HierarchyMap::empty(), &[seed, later], MINT).expect("grow");
    assert_eq!(report.minted, 2);
    assert_eq!(report.reused, 1);
    assert!(matches!(
        map_hierarchy_marker(&report.map, &marker("statya", "114")),
        HierarchyMapOutcome::Bound { .. }
    ));
}

#[test]
fn missing_work_id_fails_closed() {
    let orphan = HierarchyMarker::try_new(None, "statya", "1", None).expect("orphan");
    let err = grow_identity(
        HierarchyMap::empty(),
        &[IdentitySnapshot {
            markers: vec![orphan],
        }],
        MINT,
    )
    .expect_err("no work");
    assert!(matches!(err, WriteSetError::MissingIdentity));
}

#[test]
fn level_outside_mint_levels_is_skipped() {
    let report = grow_identity(
        HierarchyMap::empty(),
        &[IdentitySnapshot {
            markers: vec![marker("statya", "1"), marker("punkt", "4")],
        }],
        MINT,
    )
    .expect("grow");
    assert_eq!(report.minted, 1);
    assert_eq!(report.skipped, 1);
    assert_eq!(
        map_hierarchy_marker(&report.map, &marker("punkt", "4")),
        HierarchyMapOutcome::Unknown
    );
}

#[test]
fn same_number_different_path_does_not_reuse() {
    let report = grow_identity(
        HierarchyMap::empty(),
        &[IdentitySnapshot {
            markers: vec![
                marker("statya", "93"),
                marker_path("punkt", "4", "statya-93/punkt-4"),
            ],
        }],
        &["statya", "punkt"],
    )
    .expect("grow");
    assert_eq!(report.minted, 2);
    let a = match map_hierarchy_marker(&report.map, &marker("statya", "93")) {
        HierarchyMapOutcome::Bound { component } => component,
        other => panic!("{other:?}"),
    };
    let b = match map_hierarchy_marker(&report.map, &marker_path("punkt", "4", "statya-93/punkt-4"))
    {
        HierarchyMapOutcome::Bound { component } => component,
        other => panic!("{other:?}"),
    };
    assert_ne!(a.as_str(), b.as_str());
    assert!(!b.as_str().contains('/'), "CC id must not contain slash");
}

#[test]
fn report_does_not_claim_c0_force_or_applicable() {
    let report = grow_identity(
        HierarchyMap::empty(),
        &[IdentitySnapshot {
            markers: vec![marker("statya", "1")],
        }],
        MINT,
    )
    .expect("grow");
    let joined = report.non_claims().join(" ");
    assert!(joined.contains("C0") || joined.contains("not proven C0"));
    assert!(joined.contains("118") || joined.contains("not a 118"));
    assert!(joined.to_lowercase().contains("force") || joined.contains("InForce"));
    assert!(joined.contains("Applicable"));
}
