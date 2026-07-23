use ln_projection::adapters::HonestExecutor;
use ln_projection::application::RebuildDisposableProjection;
use ln_projection::domain::{
    BaselineId, CompletenessLabel, CurrencyLabel, CutoffId, NodeId, RebuildOutcome, RebuildRequest,
    RequestId, RuleVersion, ScopeId, PROJECTION_POLICY_VERSION,
};

fn req(gaps: &[&str]) -> RebuildRequest {
    RebuildRequest {
        request_id: RequestId::parse("req:R1").expect("id"),
        baseline: BaselineId::parse("baseline:B1").expect("id"),
        scope: ScopeId::parse("scope:S1").expect("id"),
        cutoff: CutoffId::parse("cutoff:C1").expect("id"),
        rules: RuleVersion::parse("rules:v1").expect("id"),
        known_gaps: gaps
            .iter()
            .map(|g| NodeId::parse(g).expect("id"))
            .collect(),
    }
}

fn rebuild(outcome: RebuildOutcome, gaps: &[&str]) -> ln_projection::domain::RebuildResult {
    let residual = gaps
        .iter()
        .map(|g| NodeId::parse(g).expect("id"))
        .collect();
    let svc = RebuildDisposableProjection::new(HonestExecutor {
        outcome,
        residual_gaps: residual,
        extra_stale: vec![NodeId::parse("node:stale1").expect("id")],
    });
    svc.rebuild(req(gaps))
}

#[test]
fn partial_rebuild_is_non_authoritative_with_ceiling() {
    let result = rebuild(RebuildOutcome::Partial, &["node:gap1"]);
    assert_eq!(result.outcome, RebuildOutcome::Partial);
    assert!(!result.ceiling.authoritative);
    assert_eq!(result.ceiling.completeness, CompletenessLabel::Incomplete);
    assert_eq!(result.ceiling.currency, CurrencyLabel::NotCurrent);
    assert!(result.publication_authority.is_none());
    assert!(!result.publication_authority_changed);
    assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap1"));
    assert!(result.ceiling.stale.iter().any(|g| g.as_str() == "node:stale1"));
    assert_eq!(result.ceiling.baseline.as_str(), "baseline:B1");
    assert_eq!(result.ceiling.scope.as_str(), "scope:S1");
    assert_eq!(result.ceiling.cutoff.as_str(), "cutoff:C1");
    assert_eq!(result.ceiling.rules.as_str(), "rules:v1");
    assert_eq!(result.trace.policy_version, PROJECTION_POLICY_VERSION);
}

#[test]
fn stale_input_cancelled_and_failed_preserve_non_authority() {
    for outcome in [
        RebuildOutcome::StaleInput,
        RebuildOutcome::Cancelled,
        RebuildOutcome::Failed,
    ] {
        let result = rebuild(outcome, &["node:gapX"]);
        assert_eq!(result.outcome, outcome);
        assert!(!result.ceiling.authoritative);
        assert!(result.publication_authority.is_none());
        assert!(!result.publication_authority_changed);
        assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gapX"));
    }
}

#[test]
fn rebuilt_disposable_success_still_non_authoritative() {
    let result = rebuild(RebuildOutcome::RebuiltDisposable, &[]);
    assert_eq!(result.outcome, RebuildOutcome::RebuiltDisposable);
    assert!(!result.ceiling.authoritative);
    assert_eq!(result.ceiling.completeness, CompletenessLabel::Incomplete);
    assert_eq!(result.ceiling.currency, CurrencyLabel::NotCurrent);
    assert!(result.publication_authority.is_none());
    assert!(!result.publication_authority_changed);
    assert!(!result.demoted);
}

#[test]
fn known_gaps_are_never_dropped_on_honest_path() {
    let result = rebuild(RebuildOutcome::Partial, &["node:g1", "node:g2"]);
    assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:g1"));
    assert!(result.ceiling.gaps.iter().any(|g| g.as_str() == "node:g2"));
}
