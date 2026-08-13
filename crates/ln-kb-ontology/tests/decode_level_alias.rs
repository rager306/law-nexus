//! Decode-facing level tokens resolve through YAML aliases, not Rust enums.

use ln_kb_ontology::catalog::OntologyCatalog;
use ln_kb_ontology::domain::{
    map_hierarchy_marker, marker_from_decode_token, HierarchyBinding, HierarchyMap,
    HierarchyMapOutcome, WriteSetError,
};
use ln_temporal::domain::ComponentConceptId;

#[test]
fn yaml_alias_maps_decode_token_to_catalog_level() {
    let catalog = OntologyCatalog::embedded().expect("yaml");
    assert_eq!(
        catalog.resolve_decode_level_alias("Statya").as_deref(),
        Some("statya")
    );
    assert!(catalog.is_presence_change_kind("include"));
    assert!(catalog.is_membership_change_kind("detach"));
    assert!(!catalog.is_presence_change_kind("upsert"));
}

#[test]
fn decode_token_lifts_through_alias_then_registry() {
    let mut map = HierarchyMap::empty();
    map.register(
        HierarchyBinding::try_new(
            None,
            "statya",
            "93",
            ComponentConceptId::parse("cc:44fz:art-93").expect("cc"),
        )
        .expect("b"),
    )
    .expect("reg");
    let marker = marker_from_decode_token(None, "Statya", "93", None).expect("alias");
    assert_eq!(marker.level(), "statya");
    match map_hierarchy_marker(&map, &marker) {
        HierarchyMapOutcome::Bound { component } => {
            assert_eq!(component.as_str(), "cc:44fz:art-93");
        }
        other => panic!("{other:?}"),
    }
}

#[test]
fn unknown_decode_token_is_rejected() {
    let err = marker_from_decode_token(None, "Article", "93", None).expect_err("unknown");
    assert!(matches!(err, WriteSetError::UnknownHierarchyLevel));
}

#[test]
fn unmapped_aliased_marker_stays_unknown() {
    let map = HierarchyMap::empty();
    let marker = marker_from_decode_token(None, "Glava", "3", None).expect("alias");
    assert_eq!(
        map_hierarchy_marker(&map, &marker),
        HierarchyMapOutcome::Unknown
    );
}
