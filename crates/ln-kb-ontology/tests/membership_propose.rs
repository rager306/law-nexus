//! Stack propose is a draft. Empty registry quarantines; no log write.

use ln_kb_ontology::domain::{
    propose_membership_from_markers, HierarchyBinding, HierarchyMap, HierarchyMarker,
};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn marker(level: &str, number: &str) -> HierarchyMarker {
    HierarchyMarker::try_new(None, level, number, None).expect("marker")
}

fn bind(map: &mut HierarchyMap, level: &str, number: &str, id: &str) {
    map.register(HierarchyBinding::try_new(None, level, number, cc(id)).expect("bind"))
        .expect("reg");
}

#[test]
fn glava_then_statya_proposes_one_attach() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "glava", "1", "cc:glava-1");
    bind(&mut map, "statya", "1", "cc:statya-1");
    let report =
        propose_membership_from_markers(&map, &[marker("glava", "1"), marker("statya", "1")])
            .expect("propose");
    assert_eq!(report.proposals.len(), 1);
    assert_eq!(report.proposals[0].parent.as_str(), "cc:glava-1");
    assert_eq!(report.proposals[0].child.as_str(), "cc:statya-1");
    assert_eq!(report.quarantined, 0);
    assert_eq!(report.forest_roots, 1);
    assert!(report
        .non_claims()
        .iter()
        .any(|line| line.contains("do not append VersionedMembershipLog")));
}

#[test]
fn sibling_statya_share_the_same_glava() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "glava", "1", "cc:glava-1");
    bind(&mut map, "statya", "1", "cc:statya-1");
    bind(&mut map, "statya", "2", "cc:statya-2");
    let report = propose_membership_from_markers(
        &map,
        &[
            marker("glava", "1"),
            marker("statya", "1"),
            marker("statya", "2"),
        ],
    )
    .expect("propose");
    assert_eq!(report.proposals.len(), 2);
    assert_eq!(report.proposals[0].parent.as_str(), "cc:glava-1");
    assert_eq!(report.proposals[1].parent.as_str(), "cc:glava-1");
    assert_eq!(report.proposals[1].child.as_str(), "cc:statya-2");
    assert_eq!(report.forest_roots, 1);
}

#[test]
fn empty_registry_quarantines_and_proposes_nothing() {
    let report = propose_membership_from_markers(
        &HierarchyMap::empty(),
        &[marker("glava", "1"), marker("statya", "1")],
    )
    .expect("propose");
    assert!(report.proposals.is_empty());
    assert_eq!(report.quarantined, 2);
    assert_eq!(report.forest_roots, 0);
}

#[test]
fn unknown_marker_does_not_break_the_stack() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "glava", "1", "cc:glava-1");
    bind(&mut map, "statya", "2", "cc:statya-2");
    let report = propose_membership_from_markers(
        &map,
        &[
            marker("glava", "1"),
            marker("statya", "99"),
            marker("statya", "2"),
        ],
    )
    .expect("propose");
    assert_eq!(report.quarantined, 1);
    assert_eq!(report.proposals.len(), 1);
    assert_eq!(report.proposals[0].child.as_str(), "cc:statya-2");
    assert_eq!(report.proposals[0].parent.as_str(), "cc:glava-1");
}
