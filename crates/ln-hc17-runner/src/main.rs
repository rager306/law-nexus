use std::env;
use std::process::ExitCode;

use ln_query::adapters::{HostileGapInventorState, InMemoryQueryState};
use ln_query::application::ExecuteEvidenceBoundedQuery;
use ln_query::domain::{EvidenceId, QueryId, QueryOutcome, QueryRequest, ScopeId};

fn req(evidence: &[&str], invention: bool) -> QueryRequest {
    QueryRequest {
        query_id: QueryId::parse("q:1").unwrap(),
        scope_id: ScopeId::parse("scope:S1").unwrap(),
        requested_evidence: evidence
            .iter()
            .map(|s| EvidenceId::parse(s).unwrap())
            .collect(),
        invention_attempt: invention,
        fabrication_attempt: false,
    }
}

fn render_verdict() -> String {
    let svc = ExecuteEvidenceBoundedQuery::new(
        InMemoryQueryState::new()
            .with_evidence("ev:1")
            .with_evidence("ev:2"),
    );
    let answered = svc.query(req(&["ev:1", "ev:2"], false));
    let missing = svc.query(req(&["ev:missing"], false));
    let partial = svc.query(req(&["ev:1", "ev:missing"], false));
    let invented = svc.query(req(&["ev:1"], true));
    let hostile = ExecuteEvidenceBoundedQuery::new(HostileGapInventorState::new());
    let hostile_invented = hostile.query(req(&["ev:anything"], true));

    let pass = answered.outcome == QueryOutcome::Answered
        && missing.outcome == QueryOutcome::NoAnswer
        && partial.outcome == QueryOutcome::Partial
        && invented.outcome == QueryOutcome::InventedRejected
        && hostile_invented.outcome == QueryOutcome::InventedRejected;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc17-verdict/v1\",\"evidence_id\":\"S10-HC-17-RT\",\"case_id\":\"HC-17\",\"verdict\":\"{verdict}\",\"scenario_count\":5,\"answered\":{},\"no_answer\":{},\"partial\":{},\"invention_rejected\":{},\"hostile_invention_rejected\":{},\"remaining_unsupported_cases\":3,\"lifecycle\":\"[bounded]\"}}",
        answered.outcome == QueryOutcome::Answered,
        missing.outcome == QueryOutcome::NoAnswer,
        partial.outcome == QueryOutcome::Partial,
        invented.outcome == QueryOutcome::InventedRejected,
        hostile_invented.outcome == QueryOutcome::InventedRejected,
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
            eprintln!("hc17_runner_error:unknown_scenario");
            ExitCode::from(2)
        }
    }
}
