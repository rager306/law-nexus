//! First real cross-act edge from C1 corpus: 138-ФЗ amends 44-ФЗ articles 31, 43.
//! Uses YAML registry to mint Expression IDs and resolve CC bindings.

use ln_kb_ontology::domain::{
    map_hierarchy_marker, try_cross_act_edge, HierarchyMapOutcome, HierarchyMarker,
};
use ln_kb_ontology::registry::{load_expression_id_for_path, load_hierarchy_map_for_path};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

#[test]
fn real_amends_edge_138fz_to_44fz_article_31() {
    // 138-ФЗ (C1 amending act) amends article 31 of 44-ФЗ
    let prov_138 = load_expression_id_for_path("n-138-fz").expect("138 expression");
    let prov_44 = load_expression_id_for_path("n-44-fz").expect("44 expression");

    let edge = try_cross_act_edge(
        "amends",
        &cc("cc:138-fz:statya-1"),
        &cc("cc:44-fz:statya-31"),
        &prov_138,
    )
    .expect("real amends edge");

    assert_eq!(edge.kind, "amends");
    assert_eq!(edge.from_cc.as_str(), "cc:138-fz:statya-1");
    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:statya-31");
    assert!(prov_138.contains("138-fz"));
    assert!(prov_44.contains("44-fz"));
}

#[test]
fn real_amends_edge_138fz_to_44fz_article_43() {
    let prov = load_expression_id_for_path("n-138-fz").expect("138 expression");

    let edge = try_cross_act_edge(
        "amends",
        &cc("cc:138-fz:statya-1"),
        &cc("cc:44-fz:statya-43"),
        &prov,
    )
    .expect("real amends edge 43");

    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:statya-43");
}

#[test]
fn real_amends_edge_333fz_to_44fz_article_95() {
    // 333-ФЗ (C1) amends article 95 of 44-ФЗ
    let prov_333 = load_expression_id_for_path("federalnyi-zakon-ot-31-07-2025-n-333-fz")
        .or_else(|| load_expression_id_for_path("333-fz"))
        .unwrap_or_else(|| "amendingact:c1-333-fz".to_owned());

    let edge = try_cross_act_edge(
        "amends",
        &cc("cc:333-fz:statya-1"),
        &cc("cc:44-fz:statya-95"),
        &prov_333,
    )
    .expect("real amends edge 95");

    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:statya-95");
}

#[test]
fn real_44fz_expression_id_minted() {
    let expr = load_expression_id_for_path("n-44-fz").expect("44 expression");
    assert!(expr.contains("44-fz"), "must contain act number: {expr}");
    assert!(
        expr.contains("2013-04-05"),
        "must contain enactment date: {expr}"
    );
}

#[test]
fn real_138fz_expression_id_minted() {
    let expr = load_expression_id_for_path("n-138-fz").expect("138 expression");
    assert!(expr.contains("138-fz"), "must contain act number: {expr}");
    assert!(
        expr.contains("2025-06-07"),
        "must contain enactment date: {expr}"
    );
}

// ─── 484-FZ amends 44-FZ statya 93: composed C1 constructor proof (M186 S02) ──

/// 484-FZ (enactment 2024-12-26) mints its own expression id from the
/// embedded works table — real needle, no synthetic `amendingact:` fallback.
#[test]
fn real_484fz_expression_id_minted() {
    let expr = load_expression_id_for_path("law_2024-12-26_484-fz").expect("484 expression");
    assert_eq!(expr, "expr:ru:federal:zakon:2024-12-26:484-fz:2024-12-26");
}

/// First constructor proof for 484-FZ → 44-FZ statya 93. The C1 constructor
/// is the composition of three existing APIs (D292): expression minting from
/// the works table, hierarchy-map lift of the target component, and the
/// cross-act edge port. No new error variant, no YAML binding for
/// `cc:484-fz:statya-1` (from_cc parses directly), no XML parsing.
#[test]
fn real_amends_edge_484fz_to_44fz_article_93() {
    let expr = load_expression_id_for_path("law_2024-12-26_484-fz").expect("484 expression");
    let map = load_hierarchy_map_for_path("law_2013-04-05_44-fz").expect("44 map");
    // work_id stays None: 44-FZ registry bindings are work-less, and a
    // concrete work id would break same_key; number is the flat key_path.
    let marker = HierarchyMarker::try_new(None, "statya", "93", None).expect("marker");
    let bound_cc = match map_hierarchy_marker(&map, &marker) {
        HierarchyMapOutcome::Bound { component } => component,
        other => panic!("expected Bound for 44-fz statya 93, got {other:?}"),
    };
    let edge = try_cross_act_edge("amends", &cc("cc:484-fz:statya-1"), &bound_cc, &expr)
        .expect("real 484 amends");

    assert_eq!(edge.kind, "amends");
    assert_eq!(edge.from_cc.as_str(), "cc:484-fz:statya-1");
    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:statya-93");
    assert!(edge.provenance().as_str().contains("484-fz"));
    assert!(edge.provenance().as_str().contains("2024-12-26"));
}

/// Wrong enactment day fails closed at minting: the works table pins
/// 2024-12-26, so a 2024-12-27 filename resolves to None. The edge port
/// would parse a fabricated `expr:…2024-12-27…` provenance — that port
/// acceptance is exactly the trap this negative refuses to walk into.
#[test]
fn wrong_enactment_day_484_does_not_mint_edge_provenance() {
    assert!(load_expression_id_for_path(
        "consru_export/exports/npa/law_2024-12-27_484-fz_rev-unknown_x.xml"
    )
    .is_none());
}

/// Parse is not resolve: `ComponentConceptId::parse("cc:44-fz:statya-999")`
/// succeeds on its own, but the 44-FZ hierarchy map has no such binding, so
/// the lift must answer Unknown — never an invented CC, never an edge.
#[test]
fn unbound_44fz_statya_999_is_unknown_not_invented_cc() {
    let map = load_hierarchy_map_for_path("law_2013-04-05_44-fz").expect("44 map");
    let marker = HierarchyMarker::try_new(None, "statya", "999", None).expect("marker");
    assert_eq!(
        map_hierarchy_marker(&map, &marker),
        HierarchyMapOutcome::Unknown
    );
}

/// Pitfall guard for the positive path: the fixture needle `n-44-fz` binds
/// only 31/43/95, so statya 93 must come from the corpus map
/// `law_2013-04-05_44-fz`; loading the toy map would leave the lift Unknown.
#[test]
fn n_44_fz_map_does_not_bind_statya_93() {
    let map = load_hierarchy_map_for_path("n-44-fz").expect("fixture 44 map");
    let marker = HierarchyMarker::try_new(None, "statya", "93", None).expect("marker");
    assert_eq!(
        map_hierarchy_marker(&map, &marker),
        HierarchyMapOutcome::Unknown
    );
}
