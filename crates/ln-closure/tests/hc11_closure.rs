use ln_closure::adapters::FixedDependencyEvidence;
use ln_closure::application::ComputeDependencyClosure;
use ln_closure::domain::{
    ClosureRequest, ClosureStatus, CompletenessClaim, NodeId, PublicationEligibility, RequestId,
    RuleVersion, CLOSURE_POLICY_VERSION,
};

fn n(id: &str) -> NodeId {
    NodeId::parse(id).expect("id")
}

fn rv(id: &str) -> RuleVersion {
    RuleVersion::parse(id).expect("id")
}

fn rid(id: &str) -> RequestId {
    RequestId::parse(id).expect("id")
}

fn base_graph() -> FixedDependencyEvidence {
    // A -> B -> C (all known, empty leaf)
    FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:B")])
        .with_node(n("node:B"), vec![n("node:C")])
        .with_node(n("node:C"), vec![])
}

#[test]
fn fully_evidenced_bounded_set_is_complete_and_publication_eligible() {
    let svc = ComputeDependencyClosure::new(base_graph());
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:ok"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::Complete);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Eligible
    );
    assert!(result.missing.is_empty());
    assert!(!result.completeness_claim_applied);
    assert!(!result.progress_used_as_completeness);
    assert!(!result.queue_depth_used_as_completeness);
    assert_eq!(result.trace.policy_version, CLOSURE_POLICY_VERSION);
    assert!(result.affected.iter().any(|x| x.as_str() == "node:A"));
    assert!(result.affected.iter().any(|x| x.as_str() == "node:C"));
}

#[test]
fn missing_dependency_is_incomplete_and_blocks_publication() {
    let evidence = FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:MISSING")]);
    // node:MISSING has no evidence record.
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:missing"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::Incomplete);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Blocked
    );
    assert!(result.missing.iter().any(|x| x.as_str() == "node:MISSING"));
}

#[test]
fn unknown_node_blocks_as_unknown() {
    let evidence = FixedDependencyEvidence::new(rv("rules:v1"));
    // changed node has no deps entry → unknown.
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:unknown"),
        changed: vec![n("node:GHOST")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::Unknown);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Blocked
    );
}

#[test]
fn unbounded_fanout_blocks_publication() {
    // Build a chain longer than MAX_BOUNDED_FANOUT.
    let mut evidence = FixedDependencyEvidence::new(rv("rules:v1"));
    for i in 0..12 {
        let cur = n(&format!("node:N{i}"));
        let next = n(&format!("node:N{}", i + 1));
        evidence = evidence.with_node(cur, vec![next]);
    }
    evidence = evidence.with_node(n("node:N12"), vec![]);
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:unbounded"),
        changed: vec![n("node:N0")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::Unbounded);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Blocked
    );
}

#[test]
fn rule_version_mismatch_blocks_publication() {
    let svc = ComputeDependencyClosure::new(base_graph());
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:skew"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v2"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::RuleVersionMismatch);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Blocked
    );
}

#[test]
fn progress_as_complete_claim_is_rejected() {
    let evidence = base_graph().with_progress(999, 0);
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:progress"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::ProgressAsComplete,
        request_incremental_publication: true,
    });
    assert_eq!(result.status, ClosureStatus::Incomplete);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Blocked
    );
    assert!(!result.completeness_claim_applied);
    assert!(!result.progress_used_as_completeness);
    assert_eq!(
        result.trace.completeness_claim,
        CompletenessClaim::ProgressAsComplete
    );
}
