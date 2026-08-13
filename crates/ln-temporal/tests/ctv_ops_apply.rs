//! Bounded-runtime apply of structural industrial ops (TSG-003/013 S3).
//!
//! Mutates membership graph and appends structural events only.
//! Not temporal CTV resolution, not legal amendment correctness.

use ln_temporal::domain::{
    apply_industrial_op, plan_industrial_op, AmendingActId, ComponentConceptId,
    CtvIndustrialOpKind, CtvOpsError, IndustrialOpId, IndustrialOpRequest, MembershipEdge,
    MembershipGraph, StructuralEventLog,
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
fn apply_move_mutates_parent_and_appends_event() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch1"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:move1"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:art-1")],
        targets: vec![cc("cc:ch2")],
        provenance: act("act:z"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("apply");
    assert_eq!(
        graph.parent_of(&cc("cc:art-1")).map(|p| p.as_str()),
        Some("cc:ch2")
    );
    assert_eq!(log.events().len(), 1);
    assert_eq!(log.events()[0].kind, CtvIndustrialOpKind::Move);
    assert_eq!(log.events()[0].op_id.as_str(), "op:move1");
}

#[test]
fn apply_requires_matching_plan() {
    let mut graph = MembershipGraph::empty();
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:move2"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:art-1")],
        targets: vec![cc("cc:ch2")],
        provenance: act("act:z"),
    };
    let other = IndustrialOpRequest {
        op_id: op("op:other"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:art-1")],
        targets: vec![cc("cc:ch2")],
        provenance: act("act:z"),
    };
    let plan = plan_industrial_op(&graph, &other).expect("plan");
    let err = apply_industrial_op(&mut graph, &mut log, &req, &plan).expect_err("mismatch");
    assert!(matches!(err, CtvOpsError::PlanMismatch));
    assert!(log.events().is_empty());
}

#[test]
fn apply_rejects_duplicate_op_id_in_log() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch1"), cc("cc:art-1")).expect("e"))
        .expect("ins");
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:dup"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:art-1")],
        targets: vec![cc("cc:ch2")],
        provenance: act("act:z"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("first");
    let err = apply_industrial_op(&mut graph, &mut log, &req, &plan).expect_err("dup");
    assert!(matches!(err, CtvOpsError::DuplicateOpId));
}

#[test]
fn apply_split_under_parent_replaces_subject_children() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-93")).expect("e"))
        .expect("ins");
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:split"),
        kind: CtvIndustrialOpKind::Split,
        subjects: vec![cc("cc:art-93")],
        targets: vec![cc("cc:art-93-1"), cc("cc:art-93-2")],
        provenance: act("act:fz"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("apply");
    assert!(graph.parent_of(&cc("cc:art-93")).is_none());
    assert_eq!(
        graph.parent_of(&cc("cc:art-93-1")).map(|p| p.as_str()),
        Some("cc:ch")
    );
    assert_eq!(
        graph.parent_of(&cc("cc:art-93-2")).map(|p| p.as_str()),
        Some("cc:ch")
    );
}

#[test]
fn apply_merge_collapses_siblings_to_target() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:a")).expect("e1"))
        .expect("i1");
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:b")).expect("e2"))
        .expect("i2");
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:merge"),
        kind: CtvIndustrialOpKind::Merge,
        subjects: vec![cc("cc:a"), cc("cc:b")],
        targets: vec![cc("cc:merged")],
        provenance: act("act:x"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("apply");
    assert!(graph.parent_of(&cc("cc:a")).is_none());
    assert!(graph.parent_of(&cc("cc:b")).is_none());
    assert_eq!(
        graph.parent_of(&cc("cc:merged")).map(|p| p.as_str()),
        Some("cc:ch")
    );
}

#[test]
fn apply_renumber_rewrites_component_ids_in_edges() {
    let mut graph = MembershipGraph::empty();
    graph
        .insert(MembershipEdge::try_new(cc("cc:ch"), cc("cc:art-10")).expect("e"))
        .expect("ins");
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:ren"),
        kind: CtvIndustrialOpKind::Renumber,
        subjects: vec![cc("cc:art-10")],
        targets: vec![cc("cc:art-11")],
        provenance: act("act:y"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("apply");
    assert!(graph.parent_of(&cc("cc:art-10")).is_none());
    assert_eq!(
        graph.parent_of(&cc("cc:art-11")).map(|p| p.as_str()),
        Some("cc:ch")
    );
}

#[test]
fn apply_does_not_claim_temporal_ctv_resolution() {
    let mut graph = MembershipGraph::empty();
    let mut log = StructuralEventLog::empty();
    let req = IndustrialOpRequest {
        op_id: op("op:move-free"),
        kind: CtvIndustrialOpKind::Move,
        subjects: vec![cc("cc:free")],
        targets: vec![cc("cc:parent")],
        provenance: act("act:z"),
    };
    let plan = plan_industrial_op(&graph, &req).expect("plan");
    let receipt = apply_industrial_op(&mut graph, &mut log, &req, &plan).expect("apply");
    assert!(receipt
        .non_claims
        .iter()
        .any(|c| c.contains("not full CTV") || c.contains("Structural")));
}
