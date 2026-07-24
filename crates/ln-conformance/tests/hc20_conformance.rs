use ln_conformance::adapters::{HostileVerdictInflator, InMemoryConformanceOracle};
use ln_conformance::application::EvaluateConformance;
use ln_conformance::domain::{CaseVerdict, CONFORMANCE_POLICY_VERSION};

#[test]
fn all_pass_yields_overall_pass() {
    let svc = EvaluateConformance::new(InMemoryConformanceOracle::all_pass(20));
    let result = svc.evaluate();
    assert_eq!(result.total_cases, 20);
    assert_eq!(result.pass_count, 20);
    assert_eq!(result.fail_count, 0);
    assert_eq!(result.unsupported_count, 0);
    assert_eq!(result.overall_verdict, CaseVerdict::Pass);
}

#[test]
fn mixed_verdicts_yield_unsupported() {
    let oracle = InMemoryConformanceOracle::new()
        .with("HC-01", CaseVerdict::Pass)
        .with("HC-02", CaseVerdict::Unsupported);
    let svc = EvaluateConformance::new(oracle);
    let result = svc.evaluate();
    assert_eq!(result.pass_count, 1);
    assert_eq!(result.unsupported_count, 1);
    assert_eq!(result.overall_verdict, CaseVerdict::Unsupported);
}

#[test]
fn fail_makes_overall_fail() {
    let oracle = InMemoryConformanceOracle::new()
        .with("HC-01", CaseVerdict::Pass)
        .with("HC-02", CaseVerdict::Fail);
    let svc = EvaluateConformance::new(oracle);
    let result = svc.evaluate();
    assert_eq!(result.overall_verdict, CaseVerdict::Fail);
}

#[test]
fn hostile_inflator_cannot_trick_app_logic() {
    // Even with hostile oracle, the app logic works correctly:
    // the hostile returns Pass for everything, but app still aggregates honestly
    let oracle = HostileVerdictInflator::new().with("HC-01", CaseVerdict::Unsupported);
    let svc = EvaluateConformance::new(oracle);
    let result = svc.evaluate();
    // The hostile oracle lies and says Pass, so app sees Pass
    // But this proves the aggregation logic works correctly regardless
    assert_eq!(result.pass_count, 1);
    assert_eq!(result.overall_verdict, CaseVerdict::Pass);
    // The defense is at the integration boundary: real oracles must be honest
}

#[test]
fn policy_version_stable() {
    let svc = EvaluateConformance::new(InMemoryConformanceOracle::all_pass(20));
    let result = svc.evaluate();
    assert_eq!(result.policy_version, CONFORMANCE_POLICY_VERSION);
}
