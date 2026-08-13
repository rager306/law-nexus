//! Versioned membership fold → StructuralAst projection (TSG-013 / KBO fold).
//!
//! Canonical source is membership events. The AST is a view at effect_day t,
//! not a stored document tree and not CTV text.

use ln_temporal::domain::{
    fold_membership_at, AmendingActId, ComponentConceptId, MembershipChangeKind,
    VersionedMembershipEvent, VersionedMembershipLog,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

fn ev(kind: MembershipChangeKind, parent: &str, child: &str, day: i64) -> VersionedMembershipEvent {
    VersionedMembershipEvent::try_new(kind, cc(parent), cc(child), day, act("act:p")).expect("ev")
}

#[test]
fn empty_log_folds_to_empty_projection() {
    let log = VersionedMembershipLog::empty();
    let ast = fold_membership_at(&log, 10).expect("fold");
    assert!(ast.roots().is_empty());
    assert!(ast.is_projection());
    assert_eq!(ast.as_of_day(), 10);
    assert!(ast
        .non_claims()
        .iter()
        .any(|c| c.contains("projection") || c.contains("not canon")));
}

#[test]
fn attach_builds_parent_child_tree() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 1))
        .expect("a");
    let ast = fold_membership_at(&log, 1).expect("fold");
    assert_eq!(ast.roots().len(), 1);
    assert_eq!(ast.roots()[0].component().as_str(), "cc:ch-3");
    assert_eq!(ast.roots()[0].children().len(), 1);
    assert_eq!(
        ast.roots()[0].children()[0].component().as_str(),
        "cc:art-93"
    );
}

#[test]
fn future_events_are_invisible() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 20))
        .expect("a");
    let ast = fold_membership_at(&log, 10).expect("fold");
    assert!(ast.roots().is_empty());
}

#[test]
fn detach_then_attach_moves_child() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 1))
        .expect("a1");
    log.append(ev(MembershipChangeKind::Detach, "cc:ch-3", "cc:art-93", 5))
        .expect("d");
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-4", "cc:art-93", 5))
        .expect("a2");
    let before = fold_membership_at(&log, 4).expect("t4");
    assert_eq!(before.roots()[0].component().as_str(), "cc:ch-3");
    let after = fold_membership_at(&log, 5).expect("t5");
    assert_eq!(after.roots().len(), 1);
    assert_eq!(after.roots()[0].component().as_str(), "cc:ch-4");
    assert_eq!(
        after.roots()[0].children()[0].component().as_str(),
        "cc:art-93"
    );
}

#[test]
fn same_day_two_parents_is_conflict() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 3))
        .expect("a1");
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-4", "cc:art-93", 3))
        .expect("a2");
    let err = fold_membership_at(&log, 3).expect_err("conflict");
    assert!(matches!(
        err,
        ln_temporal::domain::CtvOpsError::MembershipConflict
    ));
}

#[test]
fn split_replaces_subject_with_targets_in_later_tree() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 1))
        .expect("a");
    log.append(ev(MembershipChangeKind::Detach, "cc:ch-3", "cc:art-93", 8))
        .expect("d");
    log.append(ev(
        MembershipChangeKind::Attach,
        "cc:ch-3",
        "cc:art-93-1",
        8,
    ))
    .expect("t1");
    log.append(ev(
        MembershipChangeKind::Attach,
        "cc:ch-3",
        "cc:art-93-2",
        8,
    ))
    .expect("t2");
    let before = fold_membership_at(&log, 7).expect("before");
    let kids: Vec<&str> = before.roots()[0]
        .children()
        .iter()
        .map(|n| n.component().as_str())
        .collect();
    assert_eq!(kids, vec!["cc:art-93"]);
    let after = fold_membership_at(&log, 8).expect("after");
    let kids: Vec<&str> = after.roots()[0]
        .children()
        .iter()
        .map(|n| n.component().as_str())
        .collect();
    assert_eq!(kids, vec!["cc:art-93-1", "cc:art-93-2"]);
}

#[test]
fn fold_does_not_claim_ctv_text_or_force() {
    let mut log = VersionedMembershipLog::empty();
    log.append(ev(MembershipChangeKind::Attach, "cc:ch-3", "cc:art-93", 1))
        .expect("a");
    let ast = fold_membership_at(&log, 1).expect("fold");
    assert!(ast
        .non_claims()
        .iter()
        .any(|c| c.contains("CTV") || c.contains("text")));
    assert!(ast
        .non_claims()
        .iter()
        .any(|c| c.contains("Force") || c.contains("InForce")));
    assert!(ast.is_projection());
}
