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

#[test]
fn load_expression_id_for_402_fz() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    let expr_id = load_expression_id_for_path(
        "federalnyi-zakon-ot-06-12-2011-n-402-fz-red-ot-15-12-2025.xml",
    )
    .expect("402 expression");
    assert!(
        expr_id.contains("402-fz"),
        "expression must contain act number: {expr_id}"
    );
    assert!(
        expr_id.contains("2011-12-06"),
        "expression must contain enactment date: {expr_id}"
    );
    assert!(
        expr_id.contains("2025-12-15"),
        "expression must contain edition date: {expr_id}"
    );
}

#[test]
fn load_expression_id_unknown_returns_none() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    assert!(load_expression_id_for_path("unknown-act.xml").is_none());
}

/// Real consru_export edition paths (skip when the export is absent).
fn real_editions_dir() -> Option<std::path::PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(&dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz");
    if root
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .exists()
    {
        Some(root)
    } else {
        None
    }
}

#[test]
fn real_edition_seed_mints_initial_expression() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    let Some(dir) = real_editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path = dir
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .to_string_lossy()
        .to_string();
    let expr = load_expression_id_for_path(&path)
        .unwrap_or_else(|| panic!("seed edition must mint, path={path}"));
    assert!(expr.contains("44-fz"), "work act number: {expr}");
    assert!(expr.contains("2013-04-05"), "enactment date: {expr}");
    // initial edition: edition day equals the enactment day
    assert!(
        expr.matches("2013-04-05").count() >= 2,
        "initial edition uses enactment date as edition date: {expr}"
    );
}

#[test]
fn real_edition_0118_mints_dated_expression() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    let Some(dir) = real_editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let path = dir
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml")
        .to_string_lossy()
        .to_string();
    let expr = load_expression_id_for_path(&path)
        .unwrap_or_else(|| panic!("edition-0118 must mint, path={path}"));
    assert!(expr.contains("44-fz"), "same work: {expr}");
    assert!(expr.contains("2013-04-05"), "enactment date: {expr}");
    assert!(
        expr.contains("2025-12-28"),
        "edition date from rev-: {expr}"
    );
}

#[test]
fn real_editions_same_work_different_expressions() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    let Some(dir) = real_editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let seed = dir
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .to_string_lossy()
        .to_string();
    let latest = dir
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml")
        .to_string_lossy()
        .to_string();
    let a = load_expression_id_for_path(&seed).expect("seed");
    let b = load_expression_id_for_path(&latest).expect("latest");
    assert_ne!(a, b, "different editions mint different expressions");
}

#[test]
fn unknown_act_number_in_filename_fails_closed() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    // act 999-fz is not in works: -> no authority -> None (fail-closed)
    assert!(load_expression_id_for_path(
        "consru_export/exports/npa/law_2013-04-05_999-fz/edition-0001_rev-2014-01-01_x.xml"
    )
    .is_none());
}

#[test]
fn enactment_date_mismatch_fails_closed() {
    use ln_kb_ontology::registry::load_expression_id_for_path;
    // works: says 44-fz was enacted 2013-04-05; filename says 2013-04-06
    assert!(load_expression_id_for_path(
        "consru_export/exports/npa/law_2013-04-06_44-fz/edition-0001_rev-2014-01-01_x.xml"
    )
    .is_none());
}

#[test]
fn edition_day_from_filename_per_edition() {
    use ln_kb_ontology::registry::load_edition_day_for_path;
    let Some(dir) = real_editions_dir() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let seed = dir
        .join("edition-0001_rev-initial_from-unknown_19d3c051.xml")
        .to_string_lossy()
        .to_string();
    let latest = dir
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml")
        .to_string_lossy()
        .to_string();
    let seed_day = load_edition_day_for_path(&seed).expect("seed day");
    let latest_day = load_edition_day_for_path(&latest).expect("latest day");
    assert_ne!(seed_day, latest_day, "per-edition effect day must differ");
    assert!(latest_day > seed_day, "edition 118 is later than edition 1");
}
