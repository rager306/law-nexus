use std::env;
use std::process::ExitCode;

use ln_projection::adapters::{HonestExecutor, HostileAuthoritativeExecutor};
use ln_projection::application::RebuildDisposableProjection;
use ln_projection::domain::{
    BaselineId, CompletenessLabel, CurrencyLabel, CutoffId, NodeId, RebuildOutcome, RebuildRequest,
    RequestId, RuleVersion, ScopeId, PROJECTION_POLICY_VERSION,
};

struct ScenarioResult {
    outcome: RebuildOutcome,
    authoritative: bool,
    publication_authority_present: bool,
    publication_authority_changed: bool,
    gaps_preserved: bool,
    demoted: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn req(id: &str, gaps: &[&str]) -> RebuildRequest {
    RebuildRequest {
        request_id: RequestId::parse(id).expect("static id"),
        baseline: BaselineId::parse("baseline:B1").expect("static id"),
        scope: ScopeId::parse("scope:S1").expect("static id"),
        cutoff: CutoffId::parse("cutoff:C1").expect("static id"),
        rules: RuleVersion::parse("rules:v1").expect("static id"),
        known_gaps: gaps
            .iter()
            .map(|g| NodeId::parse(g).expect("static id"))
            .collect(),
    }
}

fn non_auth_pass(result: &ln_projection::domain::RebuildResult, expected: RebuildOutcome) -> bool {
    result.outcome == expected
        && !result.ceiling.authoritative
        && result.ceiling.completeness == CompletenessLabel::Incomplete
        && result.ceiling.currency == CurrencyLabel::NotCurrent
        && result.publication_authority.is_none()
        && !result.publication_authority_changed
        && result.trace.policy_version == PROJECTION_POLICY_VERSION
        && result.ceiling.baseline.as_str() == "baseline:B1"
        && result.ceiling.scope.as_str() == "scope:S1"
        && result.ceiling.cutoff.as_str() == "cutoff:C1"
        && result.ceiling.rules.as_str() == "rules:v1"
}

fn run_partial_non_authoritative() -> ScenarioResult {
    let svc = RebuildDisposableProjection::new(HonestExecutor {
        outcome: RebuildOutcome::Partial,
        residual_gaps: vec![NodeId::parse("node:gap1").expect("static id")],
        extra_stale: vec![NodeId::parse("node:stale1").expect("static id")],
    });
    let result = svc.rebuild(req("req:partial", &["node:gap1"]));
    let gaps_preserved = result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap1");
    let pass = non_auth_pass(&result, RebuildOutcome::Partial) && gaps_preserved && !result.demoted;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.ceiling.authoritative,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        gaps_preserved,
        demoted: result.demoted,
        policy_version_ok: result.trace.policy_version == PROJECTION_POLICY_VERSION,
        pass,
    }
}

fn run_stale_cancelled_failed_matrix() -> ScenarioResult {
    let mut all_pass = true;
    let mut last = RebuildOutcome::Failed;
    for outcome in [
        RebuildOutcome::StaleInput,
        RebuildOutcome::Cancelled,
        RebuildOutcome::Failed,
    ] {
        let svc = RebuildDisposableProjection::new(HonestExecutor {
            outcome,
            residual_gaps: vec![NodeId::parse("node:gapX").expect("static id")],
            extra_stale: Vec::new(),
        });
        let result = svc.rebuild(req("req:matrix", &["node:gapX"]));
        all_pass &= non_auth_pass(&result, outcome)
            && result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gapX");
        last = result.outcome;
    }
    ScenarioResult {
        outcome: last,
        authoritative: false,
        publication_authority_present: false,
        publication_authority_changed: false,
        gaps_preserved: all_pass,
        demoted: false,
        policy_version_ok: true,
        pass: all_pass,
    }
}

fn run_rebuilt_disposable_non_authoritative() -> ScenarioResult {
    let svc = RebuildDisposableProjection::new(HonestExecutor {
        outcome: RebuildOutcome::RebuiltDisposable,
        residual_gaps: Vec::new(),
        extra_stale: Vec::new(),
    });
    let result = svc.rebuild(req("req:ok", &[]));
    let pass = non_auth_pass(&result, RebuildOutcome::RebuiltDisposable) && !result.demoted;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.ceiling.authoritative,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        gaps_preserved: true,
        demoted: result.demoted,
        policy_version_ok: result.trace.policy_version == PROJECTION_POLICY_VERSION,
        pass,
    }
}

fn run_hostile_demotion() -> ScenarioResult {
    let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::RebuiltDisposable,
    });
    let result = svc.rebuild(req("req:hostile", &["node:gap1", "node:gap2"]));
    let gaps_preserved = result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap1")
        && result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap2");
    let pass = result.outcome == RebuildOutcome::Failed
        && result.demoted
        && !result.ceiling.authoritative
        && result.publication_authority.is_none()
        && !result.publication_authority_changed
        && gaps_preserved
        && result.trace.executor_claimed_authoritative
        && result.trace.policy_version == PROJECTION_POLICY_VERSION;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.ceiling.authoritative,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        gaps_preserved,
        demoted: result.demoted,
        policy_version_ok: result.trace.policy_version == PROJECTION_POLICY_VERSION,
        pass,
    }
}

fn run_hostile_cannot_hide_gaps() -> ScenarioResult {
    let svc = RebuildDisposableProjection::new(HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::Partial,
    });
    let result = svc.rebuild(req("req:hide", &["node:gap1", "node:gap2"]));
    let gaps_preserved = result.ceiling.gaps.len() == 2
        && result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap1")
        && result.ceiling.gaps.iter().any(|g| g.as_str() == "node:gap2");
    let pass = result.outcome == RebuildOutcome::Partial
        && result.demoted
        && !result.ceiling.authoritative
        && result.publication_authority.is_none()
        && gaps_preserved;
    ScenarioResult {
        outcome: result.outcome,
        authoritative: result.ceiling.authoritative,
        publication_authority_present: result.publication_authority.is_some(),
        publication_authority_changed: result.publication_authority_changed,
        gaps_preserved,
        demoted: result.demoted,
        policy_version_ok: result.trace.policy_version == PROJECTION_POLICY_VERSION,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc12-receipt/v1\",\"case_id\":\"HC-12\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"authoritative\":{},\"publication_authority_present\":{},\"publication_authority_changed\":{},\"gaps_preserved\":{},\"demoted\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"projection_store_selected\":false}}",
        scenario,
        result.outcome.as_str(),
        result.authoritative,
        result.publication_authority_present,
        result.publication_authority_changed,
        result.gaps_preserved,
        result.demoted,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let partial = run_partial_non_authoritative();
    let matrix = run_stale_cancelled_failed_matrix();
    let rebuilt = run_rebuilt_disposable_non_authoritative();
    let hostile = run_hostile_demotion();
    let hide = run_hostile_cannot_hide_gaps();
    let pass = partial.pass && matrix.pass && rebuilt.pass && hostile.pass && hide.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc12-verdict/v1\",\"evidence_id\":\"S10-HC-12-RT\",\"case_id\":\"HC-12\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"partial_non_authoritative\":{},\"stale_cancelled_failed_matrix\":{},\"rebuilt_disposable_non_authoritative\":{},\"hostile_demotion\":{},\"hostile_cannot_hide_gaps\":{},\"publication_authority_never_granted\":{},\"remaining_unsupported_cases\":8,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"projection_store_selected\":false}}",
        partial.pass,
        matrix.pass,
        rebuilt.pass,
        hostile.pass,
        hide.pass,
        !partial.publication_authority_present
            && !matrix.publication_authority_present
            && !rebuilt.publication_authority_present
            && !hostile.publication_authority_present
            && !hide.publication_authority_present
            && !partial.publication_authority_changed
            && !matrix.publication_authority_changed
            && !rebuilt.publication_authority_changed
            && !hostile.publication_authority_changed
            && !hide.publication_authority_changed,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc12_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "partial-non-authoritative" => run_partial_non_authoritative(),
        "stale-cancelled-failed-matrix" => run_stale_cancelled_failed_matrix(),
        "rebuilt-disposable-non-authoritative" => run_rebuilt_disposable_non_authoritative(),
        "hostile-demotion" => run_hostile_demotion(),
        "hostile-cannot-hide-gaps" => run_hostile_cannot_hide_gaps(),
        _ => {
            eprintln!("hc12_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
