//! S_fold: edition_ast_at = membership fold + presence fold + filter.
//! Proves the edition AST is smaller than the composition AST when a
//! component is absent from the Expression.

use ln_identity::domain::ExpressionId;
use ln_kb_ontology::domain::{
    admit_membership_proposals, commit_admitted_to_log, edition_ast_at, fold_expression_presence,
    ComponentInExpressionEvent, ComponentInExpressionLog, MembershipProposal,
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

fn expr() -> ExpressionId {
    ExpressionId::parse("expr:402-fz:2025-12-15").expect("expr")
}

fn provenance() -> AmendingActId {
    AmendingActId::parse("amendingact:c2-oracle-edition").expect("prov")
}

fn include_event(component: &str, day: i64) -> ComponentInExpressionEvent {
    ComponentInExpressionEvent::try_new(
        "include",
        expr(),
        cc(component),
        day,
        "amendingact:c2-oracle-edition",
    )
    .expect("include event")
}

#[test]
fn edition_ast_excludes_absent_components() {
    let admit = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-2"),
    ]);
    let mut mlog = VersionedMembershipLog::empty();
    let day = 80000i64;
    commit_admitted_to_log(&admit, &mut mlog, day, &provenance()).expect("commit");

    // Presence: statya-1 included, statya-2 NOT included
    let mut plog = ComponentInExpressionLog::empty();
    plog.append(include_event("cc:glava-1", day)).expect("p1");
    plog.append(include_event("cc:statya-1", day)).expect("p2");
    // cc:statya-2 deliberately absent from this Expression

    let edition = edition_ast_at(&mlog, &plog, &expr(), day).expect("edition fold");

    // Root: glava-1 (present)
    assert_eq!(edition.roots().len(), 1);
    let root = &edition.roots()[0];
    assert_eq!(root.component().as_str(), "cc:glava-1");
    // Only statya-1 child, not statya-2
    assert_eq!(root.children().len(), 1);
    assert_eq!(root.children()[0].component().as_str(), "cc:statya-1");
}

#[test]
fn edition_ast_equals_composition_when_all_present() {
    let admit = admit_membership_proposals(&[
        proposal("cc:glava-1", "cc:statya-1"),
        proposal("cc:glava-1", "cc:statya-2"),
    ]);
    let mut mlog = VersionedMembershipLog::empty();
    let day = 80000i64;
    commit_admitted_to_log(&admit, &mut mlog, day, &provenance()).expect("commit");

    // Presence: ALL components included
    let mut plog = ComponentInExpressionLog::empty();
    plog.append(include_event("cc:glava-1", day)).expect("p1");
    plog.append(include_event("cc:statya-1", day)).expect("p2");
    plog.append(include_event("cc:statya-2", day)).expect("p3");

    let composition = ln_temporal::domain::fold_membership_at(&mlog, day).expect("composition");
    let presence = fold_expression_presence(&plog, &expr(), day).expect("presence");
    let edition = edition_ast_at(&mlog, &plog, &expr(), day).expect("edition fold");

    // Same number of roots and total nodes when nothing is filtered
    assert_eq!(edition.roots().len(), composition.roots().len());
    let edition_nodes: usize = edition.roots().iter().map(count_nodes).sum();
    let comp_nodes: usize = composition.roots().iter().map(count_nodes).sum();
    assert_eq!(edition_nodes, comp_nodes);
    assert!(presence.components().len() >= 3);
}

#[test]
fn edition_ast_at_earlier_day_hides_future() {
    let admit = admit_membership_proposals(&[proposal("cc:glava-1", "cc:statya-1")]);
    let mut mlog = VersionedMembershipLog::empty();
    let day = 80000i64;
    commit_admitted_to_log(&admit, &mut mlog, day, &provenance()).expect("commit");

    let mut plog = ComponentInExpressionLog::empty();
    plog.append(include_event("cc:glava-1", day)).expect("p1");
    plog.append(include_event("cc:statya-1", day)).expect("p2");

    let earlier = edition_ast_at(&mlog, &plog, &expr(), day - 1).expect("earlier fold");
    assert!(
        earlier.roots().is_empty(),
        "future events must be invisible at day-1"
    );
}

fn count_nodes(node: &ln_temporal::domain::StructuralAstNode) -> usize {
    1 + node.children().iter().map(count_nodes).sum::<usize>()
}
