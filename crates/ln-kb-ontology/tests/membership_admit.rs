//! S_admit: conflict quarantine. Two-parent, cycle, self-parent, duplicate.
//! No log write. Proposals that survive become admitted drafts.

use ln_kb_ontology::domain::{admit_membership_proposals, MembershipProposal, QuarantineReason};
use ln_temporal::domain::ComponentConceptId;

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn proposal(parent: &str, child: &str) -> MembershipProposal {
    MembershipProposal {
        parent: cc(parent),
        child: cc(child),
    }
}

#[test]
fn clean_proposals_all_admitted() {
    let report = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-2"),
        proposal("cc:glava-2", "cc:statya-5"),
    ]);
    assert_eq!(report.admitted.len(), 3);
    assert!(report.quarantined.is_empty());
    assert_eq!(report.forest_roots, 2);
}

#[test]
fn two_parent_conflict_quarantines_second() {
    let report = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-5"),
        proposal("cc:glava-2", "cc:statya-5"),
    ]);
    assert_eq!(report.admitted.len(), 1);
    assert_eq!(report.admitted[0].parent.as_str(), "cc:glava-1");
    assert_eq!(report.quarantined.len(), 1);
    assert!(matches!(
        report.quarantined[0].reason,
        QuarantineReason::TwoParentConflict { .. }
    ));
    if let QuarantineReason::TwoParentConflict { other_parent } = &report.quarantined[0].reason {
        assert_eq!(other_parent.as_str(), "cc:glava-1");
    } else {
        panic!("expected TwoParentConflict");
    }
}

#[test]
fn duplicate_same_parent_kept_once() {
    let report = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-1"),
    ]);
    assert_eq!(report.admitted.len(), 1);
    assert!(report.quarantined.is_empty());
}

#[test]
fn cycle_quarantined() {
    let report = admit_membership_proposals(&[proposal("cc:a", "cc:b"), proposal("cc:b", "cc:a")]);
    assert_eq!(report.admitted.len(), 1);
    assert_eq!(report.quarantined.len(), 1);
    assert!(matches!(
        report.quarantined[0].reason,
        QuarantineReason::Cycle
    ));
}

#[test]
fn self_parent_quarantined() {
    let report = admit_membership_proposals(&[proposal("cc:x", "cc:x")]);
    assert_eq!(report.admitted.len(), 0);
    assert_eq!(report.quarantined.len(), 1);
    assert!(matches!(
        report.quarantined[0].reason,
        QuarantineReason::SelfParent
    ));
}

#[test]
fn admit_non_claims_forbid_log_write() {
    let report = admit_membership_proposals(&[proposal("cc:a", "cc:b")]);
    assert!(report
        .non_claims()
        .iter()
        .any(|line| line.contains("do not append VersionedMembershipLog")));
}
