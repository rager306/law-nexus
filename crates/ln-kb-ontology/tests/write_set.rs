//! Pure write-set projection: domain → typed graph ops, no I/O (KBO O2→O4).

use ln_identity::domain::mint_work;
use ln_kb_ontology::domain::{
    project_expression, project_force_event, project_join, project_membership,
    project_structural_ast, project_work, reject_forbidden_kind, GraphEdgeKind, GraphNodeKind,
    WriteSetError,
};
use ln_temporal::domain::{
    fold_membership_at, join_force_with_membership, AmendingActId, ComponentConceptId,
    ForceStatusEvent, ForceStatusTimeline, MembershipChangeKind, MembershipEdge, MembershipGraph,
    NormativeState, VersionedMembershipEvent, VersionedMembershipLog,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

#[test]
fn project_work_emits_work_node_not_force() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("work");
    let set = project_work(&work).expect("project");
    assert!(set.nodes.iter().any(|n| n.kind == GraphNodeKind::Work));
    assert!(!set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ForceStatusEvent));
    assert!(!set.claims_applicability);
    assert!(set
        .non_claims
        .iter()
        .any(|c| c.contains("not") || c.contains("I/O")));
}

#[test]
fn project_expression_links_to_work() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("work");
    let expr = ln_identity::domain::mint_expression(&work, "2014-01-01").expect("expr");
    let set = project_expression(&expr).expect("project");
    assert!(set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::Expression));
    assert!(set
        .edges
        .iter()
        .any(|e| e.kind == GraphEdgeKind::ExpressionOf));
}

#[test]
fn project_membership_does_not_emit_in_force() {
    let edge = MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e");
    let set = project_membership(&edge).expect("project");
    assert!(set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ComponentConcept));
    assert!(set
        .edges
        .iter()
        .any(|e| e.kind == GraphEdgeKind::MembershipParent));
    assert!(!set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ForceStatusEvent));
}

#[test]
fn project_force_event_requires_transition_and_provenance() {
    let event =
        ForceStatusEvent::try_new(cc("cc:art-1"), NormativeState::InForce, 10, act("act:p"))
            .expect("ev");
    let set = project_force_event(&event).expect("project");
    assert!(set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ForceStatusEvent));
    assert!(set
        .edges
        .iter()
        .any(|e| e.kind == GraphEdgeKind::ForceStatusOf));
    assert!(set
        .edges
        .iter()
        .any(|e| e.kind == GraphEdgeKind::ProvAmendingAct));
    assert!(!set.claims_applicability);
}

#[test]
fn project_join_unknown_force_does_not_invent_in_force_node() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let timeline = ForceStatusTimeline::empty();
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:art-1"), 10).expect("j");
    let set = project_join(&joined).expect("project");
    assert!(set.structural_known);
    assert!(!set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ForceStatusEvent));
    assert_eq!(joined.force.status, NormativeState::Unknown);
}

#[test]
fn forbidden_kinds_are_rejected() {
    for kind in [
        "ApplicableDecision",
        "PracticeRulingAsForce",
        "RiskScoreAsStatus",
        "ProfileCodeAsClock",
        "NormRuleAsAuthority",
        "NormativeBlob",
    ] {
        let err = reject_forbidden_kind(kind).expect_err(kind);
        assert!(matches!(err, WriteSetError::ForbiddenKind(_)));
    }
}

#[test]
fn write_set_never_claims_store_io() {
    let work = mint_work("federal", "2013-04-05", "44-fz").expect("work");
    let set = project_work(&work).expect("project");
    assert!(!set.performs_io);
    assert!(set
        .non_claims
        .iter()
        .any(|c| c.contains("I/O") || c.contains("RuVector") || c.contains("store")));
}

#[test]
fn project_folded_ast_emits_membership_not_force() {
    let mut log = VersionedMembershipLog::empty();
    log.append(
        VersionedMembershipEvent::try_new(
            MembershipChangeKind::Attach,
            cc("cc:ch-3"),
            cc("cc:art-93"),
            1,
            act("act:p"),
        )
        .expect("ev"),
    )
    .expect("append");
    let ast = fold_membership_at(&log, 1).expect("fold");
    let set = project_structural_ast(&ast).expect("project");
    assert!(set.structural_known);
    assert!(set
        .edges
        .iter()
        .any(|e| e.kind == GraphEdgeKind::MembershipParent));
    assert!(!set
        .nodes
        .iter()
        .any(|n| n.kind == GraphNodeKind::ForceStatusEvent));
    assert!(!set.performs_io);
}
