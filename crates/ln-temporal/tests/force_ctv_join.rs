//! Offline force↔CTV membership join by ComponentConceptId (KBO-R012 / O2).
//!
//! Joins ForceStatusTimeline with MembershipGraph. Never implies Applicable,
//! never treats membership/text presence as InForce.

use ln_temporal::domain::{
    join_force_with_membership, AmendingActId, ComponentConceptId, ForceStatusEvent,
    ForceStatusTimeline, MembershipEdge, MembershipGraph, NormativeState,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

fn force_event(component: &str, status: NormativeState, day: i64) -> ForceStatusEvent {
    ForceStatusEvent::try_new(cc(component), status, day, act("act:p")).expect("ev")
}

#[test]
fn membership_alone_does_not_imply_in_force() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let timeline = ForceStatusTimeline::empty();
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:art-1"), 10).expect("j");
    assert_eq!(joined.force.status, NormativeState::Unknown);
    assert!(joined.structural_known);
    assert_eq!(joined.parent.as_ref().map(|p| p.as_str()), Some("cc:ch"));
    assert!(joined
        .non_claims
        .iter()
        .any(|c| c.contains("membership") || c.contains("does not imply")));
}

#[test]
fn force_resolves_with_structural_context() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(force_event("cc:art-1", NormativeState::InForce, 5))
        .expect("a");
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:art-1"), 10).expect("j");
    assert_eq!(joined.force.status, NormativeState::InForce);
    assert!(joined.structural_known);
    assert_eq!(joined.force.dimension.as_str(), "force_status");
}

#[test]
fn free_component_with_force_is_not_structural() {
    let graph = MembershipGraph::empty();
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(force_event("cc:orphan", NormativeState::Suspended, 1))
        .expect("a");
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:orphan"), 2).expect("j");
    assert_eq!(joined.force.status, NormativeState::Suspended);
    assert!(!joined.structural_known);
    assert!(joined.parent.is_none());
    assert!(joined.children.is_empty());
}

#[test]
fn join_does_not_claim_applicability() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(force_event("cc:art-1", NormativeState::InForce, 1))
        .expect("a");
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:art-1"), 2).expect("j");
    assert!(joined.non_claims.iter().any(|c| c.contains("Applicab")));
    assert!(!joined.claims_applicability);
}

#[test]
fn conflict_force_still_joins_structure() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(force_event("cc:art-1", NormativeState::InForce, 10))
        .expect("a");
    timeline
        .append(force_event("cc:art-1", NormativeState::Repealed, 10))
        .expect("b");
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:art-1"), 10).expect("j");
    assert_eq!(joined.force.status, NormativeState::Unknown);
    assert!(joined.force.conflict);
    assert!(joined.structural_known);
}

#[test]
fn parent_component_is_structural_known() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let timeline = ForceStatusTimeline::empty();
    let joined = join_force_with_membership(&timeline, &graph, &cc("cc:ch"), 1).expect("j");
    assert!(joined.structural_known);
    assert!(joined.children.iter().any(|c| c.as_str() == "cc:art-1"));
    assert_eq!(joined.force.status, NormativeState::Unknown);
}
