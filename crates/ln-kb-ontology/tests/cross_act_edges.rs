//! Cross-act edge port: typed edges between ASTs of different normative acts.
//! Validates kind against YAML cross_act_edge_kinds vocabulary.

use ln_kb_ontology::domain::{try_cross_act_edge, CrossActEdgeError};
use ln_temporal::domain::ComponentConceptId;

/// G0 vocabulary (D216): refers_to superset + reference binding vocabulary
/// are YAML data; this file pins their contract without minting Rust types.
const ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn prov() -> &'static str {
    "amendingact:c2-oracle-edition"
}

#[test]
fn valid_amends_edge() {
    let edge = try_cross_act_edge(
        "amends",
        &cc("cc:504-fz:art-1"),
        &cc("cc:44-fz:art-93"),
        prov(),
    )
    .expect("amends");
    assert_eq!(edge.kind, "amends");
    assert_eq!(edge.from_cc.as_str(), "cc:504-fz:art-1");
    assert_eq!(edge.to_cc.as_str(), "cc:44-fz:art-93");
}

#[test]
fn valid_implements_edge() {
    let edge = try_cross_act_edge(
        "implements",
        &cc("cc:pp-926:art-1"),
        &cc("cc:44-fz:art-112"),
        prov(),
    )
    .expect("implements");
    assert_eq!(edge.kind, "implements");
}

#[test]
fn unknown_edge_kind_rejected() {
    let result = try_cross_act_edge("supersedes", &cc("cc:a"), &cc("cc:b"), prov());
    assert!(matches!(result, Err(CrossActEdgeError::UnknownKind(_))));
}

#[test]
fn self_edge_rejected() {
    let result = try_cross_act_edge("amends", &cc("cc:same"), &cc("cc:same"), prov());
    assert!(matches!(result, Err(CrossActEdgeError::SelfEdge)));
}

#[test]
fn empty_provenance_rejected() {
    let result = try_cross_act_edge("cites", &cc("cc:a"), &cc("cc:b"), "");
    assert!(matches!(result, Err(CrossActEdgeError::MissingProvenance)));
}

#[test]
fn cites_edge_created() {
    let edge = try_cross_act_edge("cites", &cc("cc:44-fz:art-1"), &cc("cc:bk:art-72"), prov())
        .expect("cites");
    assert_eq!(edge.kind, "cites");
}

#[test]
fn valid_refers_to_edge_created() {
    // G0 (D216, review-25 §A.8 / ADR-0019 note): refers_to is the edge-family
    // superset over cites; the port must accept it straight from YAML data —
    // no Rust enum and no parser classification change is implied.
    let edge = try_cross_act_edge(
        "refers_to",
        &cc("cc:131-fz:art-5"),
        &cc("cc:44-fz:art-15"),
        prov(),
    )
    .expect("refers_to");
    assert_eq!(edge.kind, "refers_to");
}

#[test]
fn refers_to_listed_after_cites_in_yaml_vocabulary() {
    // Demo contract: within cross_act_edge_kinds, cites stays a strict subset
    // family and refers_to is listed after it; the design-only reference
    // binding vocabulary carries an honest unclassified default and non-claims.
    let section_start = ONTOLOGY_YAML
        .find("cross_act_edge_kinds:")
        .expect("cross_act_edge_kinds section present");
    let section = &ONTOLOGY_YAML[section_start..];
    let cites = section.find("- cites").expect("cites row");
    let refers_to = section.find("- refers_to").expect("refers_to row");
    assert!(cites < refers_to, "refers_to must be listed after cites");
    assert!(ONTOLOGY_YAML.contains("reference_binding_vocabulary:"));
    assert!(ONTOLOGY_YAML.contains("- unclassified"));
    assert!(ONTOLOGY_YAML.contains("no Rust types, no classification wiring"));
}

#[test]
fn semantics_mode_token_is_not_an_edge_kind() {
    // ReferenceSemantics modes live in reference_binding_vocabulary only;
    // they must not leak into the cross_act_edge_kinds port surface.
    let result = try_cross_act_edge("identity_ambulatory", &cc("cc:a"), &cc("cc:b"), prov());
    assert!(matches!(result, Err(CrossActEdgeError::UnknownKind(_))));
}
