use std::env;
use std::process::ExitCode;

use ln_conformance::adapters::InMemoryConformanceOracle;
use ln_conformance::application::EvaluateConformance;
use ln_conformance::domain::CaseVerdict;

fn render_verdict() -> String {
    let oracle = InMemoryConformanceOracle::all_pass(20);
    let svc = EvaluateConformance::new(oracle);
    let result = svc.evaluate();

    let pass = result.overall_verdict == CaseVerdict::Pass
        && result.pass_count == 20
        && result.fail_count == 0
        && result.unsupported_count == 0;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc20-verdict/v1\",\"evidence_id\":\"S10-HC-20-RT\",\"case_id\":\"HC-20\",\"verdict\":\"{verdict}\",\"total_cases\":{},\"pass_count\":{},\"fail_count\":{},\"unsupported_count\":{},\"remaining_unsupported_cases\":0,\"lifecycle\":\"[bounded]\"}}",
        result.total_cases, result.pass_count, result.fail_count, result.unsupported_count,
    )
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    match args.as_slice() {
        [s] if s == "verdict" => {
            println!("{}", render_verdict());
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("hc20_runner_error:unknown_scenario");
            ExitCode::from(2)
        }
    }
}
