//! S_verify: oracle diff. Compare folded AST against expected CCs from oracle.
//! drift = missing (expected but not in AST) + phantom (in AST but not expected).

use ln_kb_ontology::domain::{
    admit_membership_proposals, commit_admitted_to_log, oracle_diff, MembershipProposal,
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

fn provenance() -> AmendingActId {
    AmendingActId::parse("amendingact:c2-oracle-edition").expect("prov")
}

fn build_ast(edges: &[(&str, &str)], day: i64) -> ln_temporal::domain::StructuralAst {
    let proposals: Vec<MembershipProposal> = edges.iter().map(|(p, c)| proposal(p, c)).collect();
    let admit = admit_membership_proposals(&proposals);
    let mut log = VersionedMembershipLog::empty();
    commit_admitted_to_log(&admit, &mut log, day, &provenance()).expect("commit");
    ln_temporal::domain::fold_membership_at(&log, day).expect("fold")
}

#[test]
fn zero_drift_when_ast_matches_expected() {
    let ast = build_ast(
        &[("cc:glava-1", "cc:statya-1"), ("cc:glava-1", "cc:statya-2")],
        80_000,
    );
    let expected = vec![cc("cc:glava-1"), cc("cc:statya-1"), cc("cc:statya-2")];
    let report = oracle_diff(&ast, &expected);
    assert_eq!(report.expected, 3);
    assert_eq!(report.actual, 3);
    assert_eq!(report.missing, 0);
    assert_eq!(report.phantom, 0);
    assert_eq!(report.drift, 0);
}

#[test]
fn phantom_when_ast_has_more_than_expected() {
    let ast = build_ast(
        &[("cc:glava-1", "cc:statya-1"), ("cc:glava-1", "cc:statya-2")],
        80_000,
    );
    let expected = vec![cc("cc:glava-1"), cc("cc:statya-1")]; // statya-2 not expected
    let report = oracle_diff(&ast, &expected);
    assert_eq!(report.phantom, 1);
    assert_eq!(report.missing, 0);
    assert_eq!(report.drift, 1);
}

#[test]
fn missing_when_expected_not_in_ast() {
    let ast = build_ast(&[("cc:glava-1", "cc:statya-1")], 80_000);
    let expected = vec![
        cc("cc:glava-1"),
        cc("cc:statya-1"),
        cc("cc:statya-2"), // expected but not in AST
    ];
    let report = oracle_diff(&ast, &expected);
    assert_eq!(report.missing, 1);
    assert_eq!(report.phantom, 0);
    assert_eq!(report.drift, 1);
}

#[test]
fn empty_ast_against_empty_expected_is_zero_drift() {
    let ast = build_ast(&[], 80_000);
    let expected: Vec<ComponentConceptId> = vec![];
    let report = oracle_diff(&ast, &expected);
    assert_eq!(report.drift, 0);
}
