use ln_projection::adapters::HostileAuthoritativeExecutor;
use ln_projection::application::RebuildDisposableProjection;
use ln_projection::domain::{
    BaselineId, CompletenessLabel, CurrencyLabel, CutoffId, NodeId, RebuildOutcome, RebuildRequest,
    RequestId, RuleVersion, ScopeId,
};

fn req_with_gaps() -> RebuildRequest {
    RebuildRequest {
        request_id: RequestId::parse("req:hostile").expect("id"),
        baseline: BaselineId::parse("baseline:B1").expect("id"),
        scope: ScopeId::parse("scope:S1").expect("id"),
        cutoff: CutoffId::parse("cutoff:C1").expect("id"),
        rules: RuleVersion::parse("rules:v1").expect("id"),
        known_gaps: vec![
            NodeId::parse("node:gap1").expect("id"),
            NodeId::parse("node:gap2").expect("id"),
        ],
    }
}

#[test]
fn hostile_authoritative_success_is_demoted_to_failed_non_authority() {
    let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::RebuiltDisposable,
    });
    let result = svc.rebuild(req_with_gaps());
    assert_eq!(result.outcome, RebuildOutcome::Failed);
    assert!(result.demoted);
    assert!(!result.ceiling.authoritative);
    assert_eq!(result.ceiling.completeness, CompletenessLabel::Incomplete);
    assert_eq!(result.ceiling.currency, CurrencyLabel::NotCurrent);
    assert!(result.publication_authority.is_none());
    assert!(!result.publication_authority_changed);
    assert!(result.trace.executor_claimed_complete);
    assert!(result.trace.executor_claimed_current);
    assert!(result.trace.executor_claimed_authoritative);
    assert!(result.trace.executor_invented_fact);
    assert!(result.trace.executor_hid_gaps);
}

#[test]
fn hostile_cannot_hide_known_gaps() {
    let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::Partial,
    });
    let result = svc.rebuild(req_with_gaps());
    assert!(!result.ceiling.authoritative);
    assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap1"));
    assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap2"));
    // Residual was emptied by hostile hide; known gaps still present.
    assert_eq!(result.ceiling.gaps.len(), 2);
}

#[test]
fn hostile_partial_stale_cancel_still_non_authoritative() {
    for outcome in [
        RebuildOutcome::Partial,
        RebuildOutcome::StaleInput,
        RebuildOutcome::Cancelled,
        RebuildOutcome::Failed,
    ] {
        let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
            base_outcome: outcome,
        });
        let result = svc.rebuild(req_with_gaps());
        assert_eq!(result.outcome, outcome, "{outcome:?}");
        assert!(result.demoted);
        assert!(!result.ceiling.authoritative);
        assert!(result.publication_authority.is_none());
        assert!(!result.publication_authority_changed);
    }
}

#[test]
fn hostile_publication_authority_grant_never_applies() {
    let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::RebuiltDisposable,
    });
    let result = svc.rebuild(req_with_gaps());
    assert!(result.publication_authority.is_none());
    assert!(!result.publication_authority_changed);
    assert_eq!(result.ceiling.baseline.as_str(), "baseline:B1");
    assert_eq!(result.ceiling.scope.as_str(), "scope:S1");
    assert_eq!(result.ceiling.cutoff.as_str(), "cutoff:C1");
    assert_eq!(result.ceiling.rules.as_str(), "rules:v1");
}
