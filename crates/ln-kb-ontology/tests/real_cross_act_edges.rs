//! First real cross-act edge from C1 corpus: 138-ФЗ amends 44-ФЗ articles 31, 43.
//! Uses YAML registry to mint Expression IDs and resolve CC bindings.

use ln_kb_ontology::domain::try_cross_act_edge;
use ln_kb_ontology::registry::load_expression_id_for_path;
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
