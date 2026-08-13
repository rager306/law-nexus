//! Scoped YAML bindings. Unmatched paths stay empty.

use ln_kb_ontology::domain::{map_hierarchy_marker, HierarchyMapOutcome, HierarchyMarker};
use ln_kb_ontology::registry::{
    bindings_matching_path, embedded_binding_count_for_path, load_hierarchy_map_for_path,
    parse_hierarchy_registry, EMBEDDED_HIERARCHY_REGISTRY_YAML,
};

#[test]
fn unmatched_path_loads_empty_map() {
    let map = load_hierarchy_map_for_path("law-source/consultant/unknown-scan.xml").expect("load");
    assert_eq!(
        embedded_binding_count_for_path("unknown-scan.xml").expect("count"),
        0
    );
    let marker = HierarchyMarker::try_new(None, "statya", "1", None).expect("marker");
    assert_eq!(
        map_hierarchy_marker(&map, &marker),
        HierarchyMapOutcome::Unknown
    );
}

#[test]
fn fz435_needle_binds_statya_one() {
    let parsed = parse_hierarchy_registry(EMBEDDED_HIERARCHY_REGISTRY_YAML).expect("parse");
    let matched = bindings_matching_path(
        &parsed,
        "federalnyi-zakon-ot-22-12-2020-n-435-fz-red-ot-25-12-2023.xml",
    );
    assert!(!matched.is_empty());
    assert!(matched.iter().all(|row| row.level == "statya"));
    assert_eq!(
        embedded_binding_count_for_path("n-435-fz").expect("count"),
        matched.len()
    );
}

#[test]
fn fz402_needle_binds_glava_and_statya() {
    let parsed = parse_hierarchy_registry(EMBEDDED_HIERARCHY_REGISTRY_YAML).expect("parse");
    let matched = bindings_matching_path(
        &parsed,
        "federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025.xml",
    );
    assert!(matched
        .iter()
        .any(|row| row.level == "glava" && row.number == "1"));
    assert!(matched
        .iter()
        .any(|row| row.level == "statya" && row.number == "25.1"));
    let map = load_hierarchy_map_for_path(
        "law-source/consultant/federalnyi-zakon-ot-06-12-2011-n-402-fz.xml",
    )
    .expect("load");
    let glava = HierarchyMarker::try_new(None, "glava", "1", None).expect("glava");
    let dotted = HierarchyMarker::try_new(None, "statya", "25.1", None).expect("dotted");
    assert!(matches!(
        map_hierarchy_marker(&map, &glava),
        HierarchyMapOutcome::Bound { .. }
    ));
    assert!(matches!(
        map_hierarchy_marker(&map, &dotted),
        HierarchyMapOutcome::Bound { .. }
    ));
    assert_eq!(
        embedded_binding_count_for_path("n-402-fz").expect("count"),
        matched.len()
    );
}

#[test]
fn missing_fields_fail_closed() {
    let err = parse_hierarchy_registry(
        "schema_version: x\nbindings:\n  - {path_needle: n-435-fz, level: statya}\n",
    )
    .expect_err("missing cc");
    assert!(err.to_string().contains("missing"));
}
