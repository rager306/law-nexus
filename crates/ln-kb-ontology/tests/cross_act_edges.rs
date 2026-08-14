//! Cross-act edge port: typed edges between ASTs of different normative acts.
//! Validates kind against YAML cross_act_edge_kinds vocabulary.

use ln_kb_ontology::domain::{try_cross_act_edge, CrossActEdgeError};
use ln_temporal::domain::ComponentConceptId;

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
