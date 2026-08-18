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

fn marker_with_path(level: &str, number: &str, path: &str) -> HierarchyMarker {
    HierarchyMarker::try_new_with_path(None, level, number, Some(path), None).expect("marker")
}

fn bind(map: &mut HierarchyMap, level: &str, number: &str, id: &str) {
    map.register(HierarchyBinding::try_new(None, level, number, cc(id)).expect("bind"))
        .expect("reg");
}

fn bind_with_path(map: &mut HierarchyMap, level: &str, number: &str, path: &str, id: &str) {
    map.register(
        HierarchyBinding::try_new_with_path(None, level, number, Some(path), cc(id)).expect("bind"),
    )
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

// R087/R8-13: recursive rank = (role order, depth). Path-bearing punkt
// markers form a ladder, so 4 -> 4.1 -> 4.1.2 nests instead of collapsing
// to flat siblings.

#[test]
fn path_punkt_nests_4_to_41_to_412() {
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "93", "cc:statya-93");
    bind_with_path(&mut map, "punkt", "4", "statya-93/punkt-4", "cc:punkt-4");
    bind_with_path(
        &mut map,
        "punkt",
        "4.1",
        "statya-93/punkt-4/punkt-4.1",
        "cc:punkt-4.1",
    );
    bind_with_path(
        &mut map,
        "punkt",
        "4.1.2",
        "statya-93/punkt-4/punkt-4.1/punkt-4.1.2",
        "cc:punkt-4.1.2",
    );
    let report = propose_membership_from_markers(
        &map,
        &[
            marker("statya", "93"),
            marker_with_path("punkt", "4", "statya-93/punkt-4"),
            marker_with_path("punkt", "4.1", "statya-93/punkt-4/punkt-4.1"),
            marker_with_path("punkt", "4.1.2", "statya-93/punkt-4/punkt-4.1/punkt-4.1.2"),
        ],
    )
    .expect("propose");
    assert_eq!(report.proposals.len(), 3);
    assert_eq!(report.proposals[0].parent.as_str(), "cc:statya-93");
    assert_eq!(report.proposals[0].child.as_str(), "cc:punkt-4");
    assert_eq!(report.proposals[1].parent.as_str(), "cc:punkt-4");
    assert_eq!(report.proposals[1].child.as_str(), "cc:punkt-4.1");
    assert_eq!(report.proposals[2].parent.as_str(), "cc:punkt-4.1");
    assert_eq!(report.proposals[2].child.as_str(), "cc:punkt-4.1.2");
    assert_eq!(report.quarantined, 0);
    assert_eq!(report.forest_roots, 1);
}

#[test]
fn flat_punkt_markers_stay_siblings_under_statya() {
    // D192 regression: without paths the flat registry keeps 4 / 4.1 / 4.1.2
    // as siblings under the enclosing statya.
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "93", "cc:statya-93");
    bind(&mut map, "punkt", "4", "cc:punkt-4");
    bind(&mut map, "punkt", "4.1", "cc:punkt-4.1");
    bind(&mut map, "punkt", "4.1.2", "cc:punkt-4.1.2");
    let report = propose_membership_from_markers(
        &map,
        &[
            marker("statya", "93"),
            marker("punkt", "4"),
            marker("punkt", "4.1"),
            marker("punkt", "4.1.2"),
        ],
    )
    .expect("propose");
    assert_eq!(report.proposals.len(), 3);
    assert_eq!(report.proposals[0].parent.as_str(), "cc:statya-93");
    assert_eq!(report.proposals[1].parent.as_str(), "cc:statya-93");
    assert_eq!(report.proposals[2].parent.as_str(), "cc:statya-93");
    assert_eq!(report.quarantined, 0);
    assert_eq!(report.forest_roots, 1);
}

#[test]
fn nested_punkt_then_flat_sibling_returns_to_statya() {
    // A flat same-role marker after a nested path ladder pops back to the
    // enclosing statya: flat depth 1 is a top-level punkt.
    let mut map = HierarchyMap::empty();
    bind(&mut map, "statya", "93", "cc:statya-93");
    bind_with_path(&mut map, "punkt", "4", "statya-93/punkt-4", "cc:punkt-4");
    bind_with_path(
        &mut map,
        "punkt",
        "4.1",
        "statya-93/punkt-4/punkt-4.1",
        "cc:punkt-4.1",
    );
    bind(&mut map, "punkt", "5", "cc:punkt-5");
    let report = propose_membership_from_markers(
        &map,
        &[
            marker("statya", "93"),
            marker_with_path("punkt", "4", "statya-93/punkt-4"),
            marker_with_path("punkt", "4.1", "statya-93/punkt-4/punkt-4.1"),
            marker("punkt", "5"),
        ],
    )
    .expect("propose");
    assert_eq!(report.proposals.len(), 3);
    assert_eq!(report.proposals[0].child.as_str(), "cc:punkt-4");
    assert_eq!(report.proposals[0].parent.as_str(), "cc:statya-93");
    assert_eq!(report.proposals[1].child.as_str(), "cc:punkt-4.1");
    assert_eq!(report.proposals[1].parent.as_str(), "cc:punkt-4");
    assert_eq!(report.proposals[2].child.as_str(), "cc:punkt-5");
    assert_eq!(report.proposals[2].parent.as_str(), "cc:statya-93");
}

#[test]
fn marker_depth_counts_non_empty_path_segments() {
    // Empty segments must not inflate the recursive rank depth; flat markers
    // default to depth 1.
    let flat = HierarchyMarker::try_new(None, "punkt", "4", None).expect("marker");
    assert_eq!(flat.depth(), 1);
    let nested = marker_with_path("punkt", "4.1", "statya-93/punkt-4/punkt-4.1");
    assert_eq!(nested.depth(), 3);
    let ragged = marker_with_path("punkt", "4", "statya-93//punkt-4/");
    assert_eq!(ragged.depth(), 2);
}
