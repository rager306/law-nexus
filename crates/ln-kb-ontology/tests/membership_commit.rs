//! S_commit → S_fold: admitted drafts become log events, fold produces AST.
//! Provenance is synthetic for C2 editions until S_identify mints Expression IDs.

use ln_kb_ontology::domain::{
    admit_membership_proposals, commit_admitted_to_log, MembershipProposal,
};
use ln_temporal::domain::{
    AmendingActId, ComponentConceptId, MembershipChangeKind, VersionedMembershipLog,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn proposal(parent: &str, child: &str) -> MembershipProposal {
    MembershipProposal {
        parent: cc(parent),
        child: cc(child),
    }
}

fn provenance() -> AmendingActId {
    AmendingActId::parse("amendingact:c2-oracle:402-fz:2025-12-15").expect("prov")
}

#[test]
fn commit_admitted_appends_attach_events() {
    let admit = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-2"),
    ]);
    assert_eq!(admit.admitted.len(), 2);

    let mut log = VersionedMembershipLog::empty();
    let day = 80000i64;
    let committed = commit_admitted_to_log(&admit, &mut log, day, &provenance()).expect("commit");
    assert_eq!(committed, 2);
    assert_eq!(log.events().len(), 2);
    assert_eq!(log.events()[0].kind(), MembershipChangeKind::Attach);
    assert_eq!(log.events()[0].parent().as_str(), "cc:glava-1");
    assert_eq!(log.events()[0].child().as_str(), "cc:statya-1");
    assert_eq!(log.events()[0].effect_day(), day);
}

#[test]
fn commit_skips_quarantined_proposals() {
    let admit = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-5"),
        proposal("cc:glava-2", "cc:statya-5"), // two-parent conflict
    ]);
    assert_eq!(admit.admitted.len(), 1);
    assert_eq!(admit.quarantined.len(), 1);

    let mut log = VersionedMembershipLog::empty();
    let committed = commit_admitted_to_log(&admit, &mut log, 80000, &provenance()).expect("commit");
    assert_eq!(committed, 1);
    assert_eq!(log.events().len(), 1);
}

#[test]
fn fold_committed_log_produces_ast_tree() {
    let admit = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-2"),
        proposal("cc:glava-2", "cc:statya-5"),
    ]);
    let mut log = VersionedMembershipLog::empty();
    let day = 80000i64;
    commit_admitted_to_log(&admit, &mut log, day, &provenance()).expect("commit");

    let ast = ln_temporal::domain::fold_membership_at(&log, day).expect("fold");
    assert_eq!(ast.roots().len(), 2); // glava-1 and glava-2 are roots
    let glava1 = ast
        .roots()
        .iter()
        .find(|r| r.component().as_str() == "cc:glava-1")
        .expect("glava-1 root");
    assert_eq!(glava1.children().len(), 2);
}

#[test]
fn fold_at_earlier_day_hides_future_events() {
    let admit = admit_membership_proposals(&[proposal("cc:glava-1", "cc:statya-1")]);
    let mut log = VersionedMembershipLog::empty();
    let day = 80000i64;
    commit_admitted_to_log(&admit, &mut log, day, &provenance()).expect("commit");

    let ast = ln_temporal::domain::fold_membership_at(&log, day - 1).expect("fold earlier");
    assert!(ast.roots().is_empty(), "future events must be invisible");
}

#[test]
fn commit_non_claims_forbid_resolve_ctv() {
    let admit = admit_membership_proposals(&[proposal("cc:a", "cc:b")]);
    let mut log = VersionedMembershipLog::empty();
    commit_admitted_to_log(&admit, &mut log, 1, &provenance()).expect("commit");
    assert!(log.events().len() == 1);
}
