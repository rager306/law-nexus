use ln_closure::adapters::{FixedDependencyEvidence, HostileProgressCompleteness};
use ln_closure::application::ComputeDependencyClosure;
use ln_closure::domain::{
    ClosureRequest, ClosureStatus, CompletenessClaim, NodeId, PublicationEligibility, RequestId,
    RuleVersion,
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

fn base() -> FixedDependencyEvidence {
    FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:B")])
        .with_node(n("node:B"), vec![n("node:C")])
        .with_node(n("node:C"), vec![])
}

#[test]
fn hostile_progress_cannot_force_complete_via_claim() {
    let evidence = HostileProgressCompleteness::wrapping(base().with_progress(0, 0));
    let svc = ComputeDependencyClosure::new(evidence);
    for claim in [
        CompletenessClaim::ProgressAsComplete,
        CompletenessClaim::QueueDepthAsComplete,
        CompletenessClaim::InventedAffectedSet,
    ] {
        let result = svc.compute(ClosureRequest {
            request_id: rid("req:claim"),
            changed: vec![n("node:A")],
            expected_rule_version: rv("rules:v1"),
            completeness_claim: claim,
            request_incremental_publication: true,
        });
        assert_eq!(result.status, ClosureStatus::Incomplete, "{claim:?}");
        assert_eq!(
            result.publication_eligibility,
            PublicationEligibility::Blocked
        );
        assert!(!result.completeness_claim_applied);
        assert!(!result.progress_used_as_completeness);
        assert!(!result.queue_depth_used_as_completeness);
        assert_eq!(result.trace.completeness_claim, claim);
    }
}

#[test]
fn hostile_invented_edges_for_unregistered_seed_cannot_force_complete() {
    // Empty registry; hostile invents empty deps for ghost via dependencies_of.
    let evidence =
        HostileProgressCompleteness::wrapping(FixedDependencyEvidence::new(rv("rules:v1")));
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:ghost"),
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
    assert!(!result.progress_used_as_completeness);
}

#[test]
fn hostile_invented_empty_missing_target_still_incomplete() {
    // A registered with dep MISSING not registered; hostile invents empty for MISSING.
    let inner = FixedDependencyEvidence::new(rv("rules:v1"))
        .with_node(n("node:A"), vec![n("node:MISSING")]);
    let evidence = HostileProgressCompleteness::wrapping(inner);
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
fn hostile_high_progress_does_not_become_completeness_on_honest_complete_path() {
    let evidence = HostileProgressCompleteness::wrapping(base());
    let svc = ComputeDependencyClosure::new(evidence);
    let result = svc.compute(ClosureRequest {
        request_id: rid("req:ok"),
        changed: vec![n("node:A")],
        expected_rule_version: rv("rules:v1"),
        completeness_claim: CompletenessClaim::None,
        request_incremental_publication: true,
    });
    // Complete only from frozen registered evidence, not progress.
    assert_eq!(result.status, ClosureStatus::Complete);
    assert_eq!(
        result.publication_eligibility,
        PublicationEligibility::Eligible
    );
    assert!(!result.progress_used_as_completeness);
    assert!(!result.queue_depth_used_as_completeness);
    assert!(!result.completeness_claim_applied);
}
