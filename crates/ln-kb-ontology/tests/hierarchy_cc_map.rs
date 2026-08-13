//! HierarchyMarker → ComponentConcept lift (KBO-R024 / review R3-02).
//!
//! Decode nodes are candidates. Number+level alone never mint a CC.
//! Missing map → Unknown. Duplicate key → Conflict.

use ln_kb_ontology::domain::{
    advance_ontology_fsm, map_hierarchy_marker, HierarchyBinding, HierarchyMap,
    HierarchyMapOutcome, HierarchyMarker, WriteSetError,
};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn marker(level: &str, number: &str) -> HierarchyMarker {
    HierarchyMarker::try_new(None, level, number, None).expect("marker")
}

#[test]
fn unmapped_marker_is_unknown_not_invented_cc() {
    let map = HierarchyMap::empty();
    let outcome = map_hierarchy_marker(&map, &marker("statya", "93"));
    assert_eq!(outcome, HierarchyMapOutcome::Unknown);
}

#[test]
fn registered_binding_resolves_to_component() {
    let mut map = HierarchyMap::empty();
    map.register(HierarchyBinding::try_new(None, "statya", "93", cc("cc:44fz:art-93")).expect("b"))
        .expect("reg");
    let outcome = map_hierarchy_marker(&map, &marker("statya", "93"));
    match outcome {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:44fz:art-93");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
}

#[test]
fn number_alone_does_not_cross_levels() {
    let mut map = HierarchyMap::empty();
    map.register(HierarchyBinding::try_new(None, "statya", "93", cc("cc:44fz:art-93")).expect("b"))
        .expect("reg");
    let outcome = map_hierarchy_marker(&map, &marker("glava", "93"));
    assert_eq!(outcome, HierarchyMapOutcome::Unknown);
}

#[test]
fn same_key_two_components_is_conflict_on_register() {
    let mut map = HierarchyMap::empty();
    map.register(
        HierarchyBinding::try_new(None, "statya", "93", cc("cc:44fz:art-93")).expect("b1"),
    )
    .expect("r1");
    let err = map
        .register(
            HierarchyBinding::try_new(None, "statya", "93", cc("cc:other:art-93")).expect("b2"),
        )
        .expect_err("conflict");
    assert!(matches!(err, WriteSetError::HierarchyMapConflict));
}

#[test]
fn same_number_different_works_do_not_collide() {
    let mut map = HierarchyMap::empty();
    map.register(
        HierarchyBinding::try_new(
            Some("work:ru:federal:zakon:2013-04-05:44-fz"),
            "statya",
            "93",
            cc("cc:44fz:art-93"),
        )
        .expect("b1"),
    )
    .expect("r1");
    map.register(
        HierarchyBinding::try_new(
            Some("work:ru:federal:zakon:2011-07-18:223-fz"),
            "statya",
            "93",
            cc("cc:223fz:art-93"),
        )
        .expect("b2"),
    )
    .expect("r2");
    let m44 = HierarchyMarker::try_new(
        Some("work:ru:federal:zakon:2013-04-05:44-fz"),
        "statya",
        "93",
        None,
    )
    .expect("m44");
    match map_hierarchy_marker(&map, &m44) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:44fz:art-93");
        }
        other => panic!("{other:?}"),
    }
}

#[test]
fn empty_number_is_rejected() {
    let err = HierarchyMarker::try_new(None, "statya", "  ", None).expect_err("empty");
    assert!(matches!(err, WriteSetError::MissingIdentity));
}

#[test]
fn lift_does_not_claim_force_or_expression_presence() {
    let mut map = HierarchyMap::empty();
    map.register(HierarchyBinding::try_new(None, "statya", "93", cc("cc:44fz:art-93")).expect("b"))
        .expect("reg");
    let outcome = map_hierarchy_marker(&map, &marker("statya", "93"));
    let claims = outcome.non_claims();
    assert!(claims
        .iter()
        .any(|c| c.contains("Force") || c.contains("InForce")));
    assert!(claims
        .iter()
        .any(|c| c.contains("Expression") || c.contains("presence")));
    assert!(claims.iter().any(|c| c.contains("Unknown")));
}

#[test]
fn unknown_yaml_level_is_rejected() {
    let err = HierarchyMarker::try_new(None, "not-a-level", "93", None).expect_err("level");
    assert!(matches!(err, WriteSetError::UnknownHierarchyLevel));
}

#[test]
fn fsm_only_allows_yaml_declared_edges() {
    advance_ontology_fsm("O2_catalog_coverage", "O2_composition_lift").expect("declared");
    let err = advance_ontology_fsm("O1", "O6_closed_validated").expect_err("jump");
    assert!(matches!(err, WriteSetError::UnknownFsmTransition));
}
