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

fn marker_with_path(level: &str, number: &str, path: &str) -> HierarchyMarker {
    HierarchyMarker::try_new_with_path(None, level, number, Some(path), None).expect("marker")
}

fn binding_with_path(level: &str, number: &str, path: &str, component: &str) -> HierarchyBinding {
    HierarchyBinding::try_new_with_path(None, level, number, Some(path), cc(component))
        .expect("binding")
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
    advance_ontology_fsm("O2_decode_prefixes", "O2_calendar_ordinal").expect("declared");
    let err = advance_ontology_fsm("O1", "O6_closed_validated").expect_err("jump");
    assert!(matches!(err, WriteSetError::UnknownFsmTransition));
}

// ─── CC-path keys (D192 / review R8-11) ───────────────────────────────────────

#[test]
fn same_number_different_paths_do_not_collide() {
    // punkt-4 under statya-93 vs punkt-4 under statya-94 must be distinct keys.
    let mut map = HierarchyMap::empty();
    map.register(binding_with_path(
        "punkt",
        "4",
        "statya-93/punkt-4",
        "cc:work:statya-93/punkt-4",
    ))
    .expect("r93");
    map.register(binding_with_path(
        "punkt",
        "4",
        "statya-94/punkt-4",
        "cc:work:statya-94/punkt-4",
    ))
    .expect("r94");
    match map_hierarchy_marker(&map, &marker_with_path("punkt", "4", "statya-93/punkt-4")) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:work:statya-93/punkt-4");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
    match map_hierarchy_marker(&map, &marker_with_path("punkt", "4", "statya-94/punkt-4")) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:work:statya-94/punkt-4");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
}

#[test]
fn deep_path_binding_resolves() {
    let mut map = HierarchyMap::empty();
    map.register(binding_with_path(
        "punkt",
        "4.2",
        "statya-93/punkt-4/punkt-4.2",
        "cc:work:statya-93/punkt-4/punkt-4.2",
    ))
    .expect("deep");
    match map_hierarchy_marker(
        &map,
        &marker_with_path("punkt", "4.2", "statya-93/punkt-4/punkt-4.2"),
    ) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:work:statya-93/punkt-4/punkt-4.2");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
}

#[test]
fn marker_without_path_does_not_match_path_binding() {
    // A flat marker `punkt 4` (effective path "4") must not hit a binding
    // whose effective path is the ladder `statya-93/punkt-4`.
    let mut map = HierarchyMap::empty();
    map.register(binding_with_path(
        "punkt",
        "4",
        "statya-93/punkt-4",
        "cc:work:statya-93/punkt-4",
    ))
    .expect("r");
    let outcome = map_hierarchy_marker(&map, &marker("punkt", "4"));
    assert_eq!(outcome, HierarchyMapOutcome::Unknown);
}

#[test]
fn flat_marker_matches_flat_binding() {
    // Default path = number keeps the flat registry working (D192).
    let mut map = HierarchyMap::empty();
    map.register(HierarchyBinding::try_new(None, "statya", "93", cc("cc:44fz:art-93")).expect("b"))
        .expect("reg");
    match map_hierarchy_marker(&map, &marker("statya", "93")) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:44fz:art-93");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
}

#[test]
fn same_path_two_components_is_conflict() {
    // Collision on the (level, path) key → typed conflict, no silent overwrite.
    let mut map = HierarchyMap::empty();
    map.register(binding_with_path(
        "punkt",
        "4",
        "statya-93/punkt-4",
        "cc:work:statya-93/punkt-4",
    ))
    .expect("r1");
    let err = map
        .register(binding_with_path(
            "punkt",
            "4",
            "statya-93/punkt-4",
            "cc:work:statya-93/punkt-4-other",
        ))
        .expect_err("conflict");
    assert!(matches!(err, WriteSetError::HierarchyMapConflict));
}

#[test]
fn empty_path_is_rejected() {
    let err = HierarchyMarker::try_new_with_path(None, "punkt", "4", Some("  "), None)
        .expect_err("empty path");
    assert!(matches!(err, WriteSetError::MissingIdentity));
    let err = HierarchyBinding::try_new_with_path(
        None,
        "punkt",
        "4",
        Some("  "),
        cc("cc:work:statya-93/punkt-4"),
    )
    .expect_err("empty binding path");
    assert!(matches!(err, WriteSetError::MissingIdentity));
}

#[test]
fn marker_key_path_defaults_to_number() {
    let flat = HierarchyMarker::try_new(None, "punkt", "4", None).expect("flat");
    assert_eq!(flat.key_path(), "4");
    let ladder = marker_with_path("punkt", "4", "statya-93/punkt-4");
    assert_eq!(ladder.key_path(), "statya-93/punkt-4");
}
