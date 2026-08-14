//! S_heal: drift → heal event or waiver. Never edit the tree.
//! Two paths: (1) waive_drift explicitly accepts non-zero drift;
//! (2) heal_missing adds Attach events for CCs that should be in the tree.

use ln_kb_ontology::domain::{
    admit_membership_proposals, commit_admitted_to_log, heal_missing, oracle_diff, waive_drift,
    MembershipProposal,
};
use ln_temporal::domain::{AmendingActId, ComponentConceptId, VersionedMembershipLog};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn proposal(parent: &str, child: &str) -> MembershipProposal {
    MembershipProposal {
        parent: cc(parent),
        child: cc(child),
    }
}

fn prov() -> AmendingActId {
    AmendingActId::parse("amendingact:c2-oracle-edition").expect("prov")
}

fn build_ast_and_log(
    edges: &[(&str, &str)],
    day: i64,
) -> (VersionedMembershipLog, ln_temporal::domain::StructuralAst) {
    let admit = admit_membership_proposals(
        &edges
            .iter()
            .map(|(p, c)| proposal(p, c))
            .collect::<Vec<_>>(),
    );
    let mut log = VersionedMembershipLog::empty();
    commit_admitted_to_log(&admit, &mut log, day, &prov()).expect("commit");
    let ast = ln_temporal::domain::fold_membership_at(&log, day).expect("fold");
    (log, ast)
}

#[test]
fn waive_drift_records_missing_and_phantom() {
    let (_log, ast) = build_ast_and_log(&[("cc:glava-1", "cc:statya-1")], 80_000);
    let expected = vec![cc("cc:glava-1"), cc("cc:statya-1"), cc("cc:statya-2")];
    let diff = oracle_diff(&ast, &expected);
    assert_eq!(diff.missing, 1); // statya-2

    let waiver = waive_drift(&diff, "forest root without chapter parent");
    assert_eq!(waiver.drift, 1);
    assert_eq!(waiver.missing, 1);
    assert_eq!(waiver.reason, "forest root without chapter parent");
}

#[test]
fn waive_zero_drift_is_still_valid() {
    let (_log, ast) = build_ast_and_log(&[("cc:glava-1", "cc:statya-1")], 80_000);
    let expected = vec![cc("cc:glava-1"), cc("cc:statya-1")];
    let diff = oracle_diff(&ast, &expected);
    assert_eq!(diff.drift, 0);

    let waiver = waive_drift(&diff, "no drift");
    assert_eq!(waiver.drift, 0);
}

#[test]
fn heal_missing_adds_attach_for_missing_cc() {
    let (mut log, ast) = build_ast_and_log(&[("cc:glava-1", "cc:statya-1")], 80_000);
    let events_before = log.events().len();

    // statya-2 is missing: expected but not in AST
    let expected_with_parents = vec![(cc("cc:glava-1"), cc("cc:statya-2"))];
    let report = heal_missing(
        &mut log,
        &ast,
        &expected_with_parents,
        80_000,
        "amendingact:heal",
    );

    assert_eq!(report.healed, 1);
    assert_eq!(log.events().len(), events_before + 1);

    // After healing, re-fold and verify drift decreased
    let healed_ast = ln_temporal::domain::fold_membership_at(&log, 80_000).expect("healed fold");
    let full_expected = vec![cc("cc:glava-1"), cc("cc:statya-1"), cc("cc:statya-2")];
    let diff = oracle_diff(&healed_ast, &full_expected);
    assert_eq!(diff.drift, 0);
}

#[test]
fn heal_missing_skips_already_present_ccs() {
    let (mut log, ast) = build_ast_and_log(&[("cc:glava-1", "cc:statya-1")], 80_000);
    let events_before = log.events().len();

    // statya-1 is already present — should not be re-added
    let expected_with_parents = vec![(cc("cc:glava-1"), cc("cc:statya-1"))];
    let report = heal_missing(
        &mut log,
        &ast,
        &expected_with_parents,
        80_000,
        "amendingact:heal",
    );

    assert_eq!(report.healed, 0);
    assert_eq!(log.events().len(), events_before);
}
