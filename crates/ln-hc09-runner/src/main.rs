use std::env;
use std::process::ExitCode;

use ln_temporal::adapters::InMemoryClockEvidence;
use ln_temporal::application::ResolveFiveClockState;
use ln_temporal::domain::{
    ClockKind, RequestId, ResolutionOutcome, ResolutionRequest, SubstituteKind, D118_POLICY_VERSION,
};

struct ScenarioResult {
    outcome: ResolutionOutcome,
    governing_clock: ClockKind,
    substitution_used: bool,
    rejected_count: usize,
    wall_clock_rejected: bool,
    policy_version_ok: bool,
    pass: bool,
}

fn forbidden_substitutes(missing: ClockKind) -> Vec<SubstituteKind> {
    let mut out = vec![
        SubstituteKind::WallClock,
        SubstituteKind::EditionOrder,
        SubstituteKind::LifecycleType,
    ];
    for clock in ClockKind::all() {
        if clock != missing {
            out.push(SubstituteKind::OtherClock(clock));
        }
    }
    out
}

fn run_matrix_all_clocks_reject_substitution() -> ScenarioResult {
    let mut all_pass = true;
    let mut total_rejected = 0usize;
    let mut wall_ok = true;
    for governing in ClockKind::all() {
        let evidence = InMemoryClockEvidence::with_all_except(governing);
        let resolver = ResolveFiveClockState::new(evidence);
        let substitutes = forbidden_substitutes(governing);
        let result = resolver.resolve(ResolutionRequest {
            request_id: RequestId::parse(&format!("req:{}", governing.as_str()))
                .expect("static id"),
            governing_clock: governing,
            attempted_substitutes: substitutes.clone(),
        });
        let pass = result.outcome == ResolutionOutcome::SubstituteRejected
            && !result.substitution_used
            && result.resolved_anchor.is_none()
            && result.trace.rejected_substitutes.len() == substitutes.len()
            && result.trace.policy_version == D118_POLICY_VERSION
            && result
                .trace
                .rejected_substitutes
                .iter()
                .any(|s| s == "wall_clock");
        all_pass &= pass;
        total_rejected += result.trace.rejected_substitutes.len();
        wall_ok &= result
            .trace
            .rejected_substitutes
            .iter()
            .any(|s| s == "wall_clock");
    }
    ScenarioResult {
        outcome: if all_pass {
            ResolutionOutcome::SubstituteRejected
        } else {
            ResolutionOutcome::Resolved
        },
        governing_clock: ClockKind::FactualEvent,
        substitution_used: false,
        rejected_count: total_rejected,
        wall_clock_rejected: wall_ok,
        policy_version_ok: true,
        pass: all_pass,
    }
}

fn run_missing_anchor_without_substitutes() -> ScenarioResult {
    let evidence = InMemoryClockEvidence::with_all_except(ClockKind::LegalActEffect);
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("req:no-sub").expect("static id"),
        governing_clock: ClockKind::LegalActEffect,
        attempted_substitutes: Vec::new(),
    });
    let pass = result.outcome == ResolutionOutcome::MissingAnchor
        && !result.substitution_used
        && result.trace.rejected_substitutes.is_empty()
        && result.trace.policy_version == D118_POLICY_VERSION;
    ScenarioResult {
        outcome: result.outcome,
        governing_clock: result.governing_clock,
        substitution_used: result.substitution_used,
        rejected_count: result.trace.rejected_substitutes.len(),
        wall_clock_rejected: true,
        policy_version_ok: result.trace.policy_version == D118_POLICY_VERSION,
        pass,
    }
}

fn run_present_anchor_resolves() -> ScenarioResult {
    let evidence = InMemoryClockEvidence::with_only(
        ClockKind::FactualEvent,
        ln_temporal::domain::AnchorId::parse("anchor:factual_event").expect("static id"),
    );
    let resolver = ResolveFiveClockState::new(evidence);
    let result = resolver.resolve(ResolutionRequest {
        request_id: RequestId::parse("req:ok").expect("static id"),
        governing_clock: ClockKind::FactualEvent,
        attempted_substitutes: vec![SubstituteKind::WallClock, SubstituteKind::EditionOrder],
    });
    let pass = result.outcome == ResolutionOutcome::Resolved
        && !result.substitution_used
        && result.resolved_anchor.is_some()
        && result.trace.rejected_substitutes.is_empty()
        && result.trace.policy_version == D118_POLICY_VERSION;
    ScenarioResult {
        outcome: result.outcome,
        governing_clock: result.governing_clock,
        substitution_used: result.substitution_used,
        rejected_count: result.trace.rejected_substitutes.len(),
        wall_clock_rejected: true,
        policy_version_ok: result.trace.policy_version == D118_POLICY_VERSION,
        pass,
    }
}

fn render_receipt(scenario: &str, result: &ScenarioResult) -> String {
    format!(
        "{{\"schema\":\"law-nexus-hc09-receipt/v1\",\"case_id\":\"HC-09\",\"scenario\":\"{}\",\"outcome\":\"{}\",\"governing_clock\":\"{}\",\"substitution_used\":{},\"rejected_count\":{},\"wall_clock_rejected\":{},\"policy_version_ok\":{},\"pass\":{},\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"applicable_law_claimed\":false}}",
        scenario,
        result.outcome.as_str(),
        result.governing_clock.as_str(),
        result.substitution_used,
        result.rejected_count,
        result.wall_clock_rejected,
        result.policy_version_ok,
        result.pass,
    )
}

fn render_verdict() -> String {
    let matrix = run_matrix_all_clocks_reject_substitution();
    let missing = run_missing_anchor_without_substitutes();
    let present = run_present_anchor_resolves();
    let pass = matrix.pass && missing.pass && present.pass;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc09-verdict/v1\",\"evidence_id\":\"S10-HC-09-RT\",\"case_id\":\"HC-09\",\"verdict\":\"{verdict}\",\"scenario_count\":3,\"matrix_all_clocks_reject_substitution\":{},\"missing_anchor_without_substitutes\":{},\"present_anchor_resolves\":{},\"wall_clock_never_authorizes\":{},\"substitution_never_used\":{},\"remaining_unsupported_cases\":11,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false,\"applicable_law_claimed\":false}}",
        matrix.pass,
        missing.pass,
        present.pass,
        matrix.wall_clock_rejected && missing.pass && present.pass,
        !matrix.substitution_used && !missing.substitution_used && !present.substitution_used,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    let [scenario] = args.as_slice() else {
        eprintln!("hc09_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };

    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }

    let result = match scenario.as_str() {
        "matrix-all-clocks-reject-substitution" => run_matrix_all_clocks_reject_substitution(),
        "missing-anchor-without-substitutes" => run_missing_anchor_without_substitutes(),
        "present-anchor-resolves" => run_present_anchor_resolves(),
        _ => {
            eprintln!("hc09_runner_error:unknown_scenario");
            return ExitCode::from(2);
        }
    };

    println!("{}", render_receipt(scenario, &result));
    ExitCode::SUCCESS
}
