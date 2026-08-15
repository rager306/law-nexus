//! Legislative replay foundation: diff_marker_sets compares two editions'
//! hierarchy markers to find structural changes (added/removed articles).
//! This is the basis for extracting AmendmentEvents from consecutive editions.

use ln_kb_ontology::domain::{diff_marker_sets, HierarchyMarker};

fn marker(level: &str, number: &str) -> HierarchyMarker {
    HierarchyMarker::try_new(None, level, number, None).expect("marker")
}

#[test]
fn diff_finds_added_article() {
    let before = vec![
        marker("glava", "1"),
        marker("statya", "1"),
        marker("statya", "2"),
    ];
    let after = vec![
        marker("glava", "1"),
        marker("statya", "1"),
        marker("statya", "2"),
        marker("statya", "3"), // new in edition 2
    ];
    let diff = diff_marker_sets(&before, &after);
    assert_eq!(diff.added.len(), 1);
    assert_eq!(diff.added[0].level(), "statya");
    assert_eq!(diff.added[0].number(), "3");
    assert!(diff.removed.is_empty());
}

#[test]
fn diff_finds_removed_article() {
    let before = vec![
        marker("glava", "1"),
        marker("statya", "1"),
        marker("statya", "2"), // removed in edition 2
    ];
    let after = vec![marker("glava", "1"), marker("statya", "1")];
    let diff = diff_marker_sets(&before, &after);
    assert!(diff.added.is_empty());
    assert_eq!(diff.removed.len(), 1);
    assert_eq!(diff.removed[0].number(), "2");
}

#[test]
fn diff_no_changes_returns_empty() {
    let before = vec![marker("statya", "1"), marker("statya", "2")];
    let after = vec![marker("statya", "2"), marker("statya", "1")]; // order swapped
    let diff = diff_marker_sets(&before, &after);
    assert!(diff.added.is_empty());
    assert!(diff.removed.is_empty());
}

#[test]
fn diff_finds_multiple_changes() {
    let before = vec![
        marker("glava", "1"),
        marker("statya", "1"),
        marker("statya", "2"), // will be removed
        marker("statya", "3"),
    ];
    let after = vec![
        marker("glava", "1"),
        marker("statya", "1"),
        marker("statya", "3"),
        marker("statya", "4"), // new
        marker("statya", "5"), // new
    ];
    let diff = diff_marker_sets(&before, &after);
    assert_eq!(diff.added.len(), 2);
    assert_eq!(diff.removed.len(), 1);
    let added_nums: Vec<&str> = diff.added.iter().map(|m| m.number()).collect();
    assert!(added_nums.contains(&"4"));
    assert!(added_nums.contains(&"5"));
}

#[test]
fn diff_empty_before_all_added() {
    let before: Vec<HierarchyMarker> = vec![];
    let after = vec![marker("statya", "1"), marker("statya", "2")];
    let diff = diff_marker_sets(&before, &after);
    assert_eq!(diff.added.len(), 2);
    assert!(diff.removed.is_empty());
}

// ─── AmendmentEventDraft bridge (M169 S03 T01) ─────────────────────────────

use ln_kb_ontology::domain::{drafts_from_marker_diff, AmendmentDraftOp};

fn draft_marker(level: &str, number: &str) -> HierarchyMarker {
    HierarchyMarker::try_new(None, level, number, None).expect("marker")
}

#[test]
fn added_marker_becomes_attach_draft_with_oracle_evidence_class() {
    let before = vec![draft_marker("glava", "1"), draft_marker("statya", "1")];
    let after = vec![
        draft_marker("glava", "1"),
        draft_marker("statya", "1"),
        draft_marker("statya", "2"),
    ];
    let drafts = drafts_from_marker_diff(
        &before,
        &after,
        "expr:ru:federal:zakon:2013-04-05:44-fz:2014-01-01",
    )
    .expect("drafts");
    assert_eq!(drafts.len(), 1);
    assert_eq!(drafts[0].op, AmendmentDraftOp::Attach);
    assert_eq!(drafts[0].level, "statya");
    assert_eq!(drafts[0].number, "2");
    assert_eq!(drafts[0].facet, "structural");
    assert_eq!(drafts[0].evidence_class, "hypothesized_from_oracle_diff");
    assert!(drafts[0].provenance.contains("44-fz"));
}

#[test]
fn removed_marker_becomes_detach_draft() {
    let before = vec![draft_marker("statya", "1"), draft_marker("statya", "2")];
    let after = vec![draft_marker("statya", "1")];
    let drafts = drafts_from_marker_diff(&before, &after, "expr:test:1").expect("drafts");
    assert_eq!(drafts.len(), 1);
    assert_eq!(drafts[0].op, AmendmentDraftOp::Detach);
    assert_eq!(drafts[0].number, "2");
}

#[test]
fn empty_provenance_fails_closed() {
    let before = vec![draft_marker("statya", "1")];
    let after = vec![draft_marker("statya", "1"), draft_marker("statya", "2")];
    let err = drafts_from_marker_diff(&before, &after, "").expect_err("empty provenance");
    assert!(err.to_string().contains("provenance"));
}

#[test]
fn identical_sets_produce_no_drafts() {
    let before = vec![draft_marker("statya", "1")];
    let after = vec![draft_marker("statya", "1")];
    let drafts = drafts_from_marker_diff(&before, &after, "expr:test:1").expect("drafts");
    assert!(drafts.is_empty());
}
