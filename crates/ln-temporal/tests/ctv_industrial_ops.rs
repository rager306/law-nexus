//! Fail-closed CTV structural membership + industrial ops spine (RC11-F08 / TSG-003/013).
//!
//! Structural only: not full CTV temporal resolution, not legal amendment correctness.

use ln_temporal::domain::{
    ctv_ops_non_claims, plan_industrial_op, whole_act_structural_compile, AmendingActId,
    ComponentConceptId, CtvIndustrialOpKind, CtvOpsError, IndustrialOpId, IndustrialOpRequest,
    MembershipEdge, MembershipGraph,
};

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

fn op(id: &str) -> IndustrialOpId {
    IndustrialOpId::parse(id).expect("op")
}

#[test]
fn industrial_op_kinds_are_closed_set_of_four() {
    assert_eq!(CtvIndustrialOpKind::all().len(), 4);
    assert_eq!(CtvIndustrialOpKind::Split.as_str(), "split");
    assert_eq!(CtvIndustrialOpKind::Merge.as_str(), "merge");
}

#[test]
fn membership_rejects_self_parent_and_cycles() {
    let err = MembershipEdge::try_new(cc("cc:a"), cc("cc:a")).expect_err("self");
    assert!(matches!(err, CtvOpsError::SelfMembership));

    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:a"), cc("cc:b")).expect("ab"))
        .expect("insert ab");
    let reverse = MembershipEdge::try_new(cc("cc:b"), cc("cc:a")).expect("ba");
    let err = graph.insert(reverse).expect_err("cycle");
    assert!(matches!(err, CtvOpsError::MembershipCycle));
}

#[test]
fn membership_single_parent_rule() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:parent1"), cc("cc:child")).expect("e1"))
        .expect("ok");
    let err = graph
        .insert(MembershipEdge::try_new(cc("cc:parent2"), cc("cc:child")).expect("e2"))
        .expect_err("multi");
    assert!(matches!(err, CtvOpsError::MultipleParents));
}

#[test]
fn plan_split_requires_two_targets_and_provenance() {
    let graph = MembershipGraph::empty();
    let bad_arity = IndustrialOpRequest {
        op_id: op("op:split1"),
        kind: CtvIndustrialOpKind::Split,
        subjects: vec![cc("cc:art-93")],
        targets: vec![cc("cc:art-93-1")],
        provenance: act("act:fz-188"),
    };
    assert!(matches!(
        plan_industrial_op(&graph, &bad_arity),
        Err(CtvOpsError::InvalidArity)
    ));

    let ok = IndustrialOpRequest {
        op_id: op("op:split2"),
        kind: CtvIndustrialOpKind::Split,
        subjects: vec![cc("cc:art-93")],
        targets: vec![cc("cc:art-93-1"), cc("cc:art-93-2")],
        provenance: act("act:fz-188"),
    };
    let plan = plan_industrial_op(&graph, &ok).expect("plan");
    assert_eq!(plan.kind, CtvIndustrialOpKind::Split);
    assert!(!plan.notes.is_empty());
    assert!(plan.notes.iter().any(|n| n.contains("not full CTV")));
}

#[test]
fn plan_merge_requires_two_subjects() {
    let graph = MembershipGraph::empty();
    let bad = IndustrialOpRequest {
        op_id: op("op:merge1"),
        kind: CtvIndustrialOpKind::Merge,
        subjects: vec![cc("cc:a")],
        targets: vec![cc("cc:merged")],
        provenance: act("act:x"),
    };
    assert!(matches!(
        plan_industrial_op(&graph, &bad),
        Err(CtvOpsError::InvalidArity)
    ));

    let ok = IndustrialOpRequest {
        op_id: op("op:merge2"),
        kind: CtvIndustrialOpKind::Merge,
        subjects: vec![cc("cc:a"), cc("cc:b")],
        targets: vec![cc("cc:merged")],
        provenance: act("act:x"),
    };
    plan_industrial_op(&graph, &ok).expect("merge plan");
}

#[test]
fn plan_renumber_rejects_target_collision() {
    let graph = MembershipGraph::empty();
    let bad = IndustrialOpRequest {
        op_id: op("op:ren1"),
        kind: CtvIndustrialOpKind::Renumber,
        subjects: vec![cc("cc:art-10")],
        targets: vec![cc("cc:art-10")],
        provenance: act("act:y"),
    };
    assert!(matches!(
        plan_industrial_op(&graph, &bad),
        Err(CtvOpsError::TargetCollision)
    ));
}

#[test]
fn plan_move_is_structural_only() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch1"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let req = IndustrialOpRequest {
        op_id: op("op:move1"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:art-1")],
        targets: vec![cc("cc:ch2")],
        provenance: act("act:z"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("move");
    assert_eq!(plan.kind, CtvIndustrialOpKind::Move);
    // Graph not mutated by plan — structural plan only.
    assert_eq!(
        graph.parent_of(&cc("cc:art-1")).map(|p| p.as_str()),
        Some("cc:ch1")
    );
}

#[test]
fn whole_act_compile_fail_closed_on_missing_component() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:act"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let required = [cc("cc:act"), cc("cc:art-1"), cc("cc:art-2")];
    let err = whole_act_structural_compile(&graph, &required).expect_err("incomplete");
    assert!(matches!(err, CtvOpsError::WholeActIncomplete));

    graph
        .insert(MembershipEdge::try_new(cc("cc:act"), cc("cc:art-2")).expect("e2"))
        .expect("ins2");
    whole_act_structural_compile(&graph, &required).expect("complete");
}

#[test]
fn non_claims_are_mandatory() {
    let claims = ctv_ops_non_claims();
    assert!(claims.iter().any(|c| c.contains("not full CTV")));
    assert!(claims.iter().any(|c| c.contains("fail-closed")));
}
