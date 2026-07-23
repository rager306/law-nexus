use std::env;
use std::process::ExitCode;

use ln_observe::adapters::{InMemoryDiagnosticSink, InMemoryWorkState, InterruptibleSourceAdapter};
use ln_observe::application::ObserveSource;
use ln_observe::domain::{
    ObservationRequest, ObservationRequestId, ObserveSourceResult, PartialObservationSummary,
    SourceChannelId, TransportOutcome, WorkPhase,
};

const RAW_CANARY: &[u8] = b"HC01-RAW-PARTIAL-CANARY";

fn adapter_for(scenario: &str) -> Option<InterruptibleSourceAdapter> {
    match scenario {
        "timeout" => Some(InterruptibleSourceAdapter::timeout_after(RAW_CANARY)),
        "cancelled" => Some(InterruptibleSourceAdapter::cancelled_after(RAW_CANARY)),
        "transport-or-tls-failure" => Some(InterruptibleSourceAdapter::transport_failure_after(
            RAW_CANARY,
        )),
        "access-restricted" => Some(InterruptibleSourceAdapter::access_restricted_after(
            RAW_CANARY,
        )),
        _ => None,
    }
}

fn phase_name(phase: WorkPhase) -> &'static str {
    match phase {
        WorkPhase::Started => "started",
        WorkPhase::ObservationFailed => "observation-failed",
        WorkPhase::ObservationCompleted => "observation-completed",
    }
}

fn execute_scenario(scenario: &str) -> Option<ObserveSourceResult> {
    let source = adapter_for(scenario)?;
    let mut use_case = ObserveSource::new(
        source,
        InMemoryWorkState::default(),
        InMemoryDiagnosticSink::default(),
    );
    Some(use_case.execute(ObservationRequest::new(
        ObservationRequestId::parse("O1").expect("static request ID is valid"),
        SourceChannelId::parse("S1").expect("static source ID is valid"),
    )))
}

fn render_receipt(result: &ObserveSourceResult) -> String {
    let diagnostic = result
        .diagnostics
        .first()
        .expect("ObserveSource always emits one diagnostic");
    let phases = result
        .work_trace
        .iter()
        .map(|transition| format!("\"{}\"", phase_name(transition.phase)))
        .collect::<Vec<_>>()
        .join(",");

    format!(
        "{{\"schema\":\"law-nexus-hc01-receipt/v1\",\"case_id\":\"HC-01\",\"request_id\":\"O1\",\"source_channel_id\":\"S1\",\"observation_id\":\"{}\",\"outcome\":\"{}\",\"work_phases\":[{}],\"diagnostic_category\":\"{}\",\"retryable\":{},\"partial_byte_count\":{},\"partial_fingerprint\":\"{}\",\"authority_absent\":true,\"legal_clock_anchor_absent\":{},\"promotion_id_absent\":{},\"publication_id_absent\":{},\"lifecycle\":\"[bounded]\"}}",
        result.observation_id.as_str(),
        result.transport_outcome.diagnostic_category(),
        phases,
        diagnostic.category.as_str(),
        diagnostic.retryable,
        diagnostic.partial_byte_count,
        diagnostic.partial_fingerprint,
        result.legal_clock_anchor.is_none(),
        result.promotion_id.is_none(),
        result.publication_id.is_none(),
    )
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct VerdictChecks {
    typed_outcomes: bool,
    failed_work_transitions: bool,
    safe_diagnostics: bool,
    authority_absent: bool,
    raw_canary_absent: bool,
}

impl VerdictChecks {
    fn pass(self) -> bool {
        self.typed_outcomes
            && self.failed_work_transitions
            && self.safe_diagnostics
            && self.authority_absent
            && self.raw_canary_absent
    }
}

fn evaluate_results(results: &[(TransportOutcome, ObserveSourceResult)]) -> VerdictChecks {
    let expected_fingerprint = PartialObservationSummary::from_bytes(RAW_CANARY)
        .fingerprint()
        .to_owned();
    VerdictChecks {
        typed_outcomes: results
            .iter()
            .all(|(expected, result)| result.transport_outcome == *expected),
        failed_work_transitions: results.iter().all(|(_, result)| {
            result.work_trace.len() == 2
                && result.work_trace[0].phase == WorkPhase::Started
                && result.work_trace[1].phase == WorkPhase::ObservationFailed
        }),
        safe_diagnostics: results.iter().all(|(_, result)| {
            result.diagnostics.len() == 1
                && result.diagnostics[0].partial_byte_count == RAW_CANARY.len()
                && result.diagnostics[0].partial_fingerprint == expected_fingerprint
        }),
        authority_absent: results.iter().all(|(_, result)| {
            result.legal_clock_anchor.is_none()
                && result.promotion_id.is_none()
                && result.publication_id.is_none()
        }),
        raw_canary_absent: results
            .iter()
            .all(|(_, result)| !format!("{result:?}").contains("HC01-RAW-PARTIAL-CANARY")),
    }
}

fn render_verdict() -> String {
    let scenarios = [
        ("timeout", TransportOutcome::Timeout),
        ("cancelled", TransportOutcome::Cancelled),
        (
            "transport-or-tls-failure",
            TransportOutcome::TransportOrTlsFailure,
        ),
        ("access-restricted", TransportOutcome::AccessRestricted),
    ];
    let results = scenarios
        .iter()
        .map(|(scenario, expected)| {
            (
                *expected,
                execute_scenario(scenario).expect("static scenario is valid"),
            )
        })
        .collect::<Vec<_>>();
    let checks = evaluate_results(&results);
    let verdict = if checks.pass() { "PASS" } else { "FAIL" };
    let scenario_count = results.len();

    format!(
        "{{\"schema\":\"law-nexus-hc01-verdict/v1\",\"evidence_id\":\"S10-HC-01-RT\",\"case_id\":\"HC-01\",\"verdict\":\"{verdict}\",\"scenario_count\":{scenario_count},\"typed_outcomes\":{},\"failed_work_transitions\":{},\"safe_diagnostics\":{},\"authority_absent\":{},\"raw_canary_absent\":{},\"remaining_unsupported_cases\":19,\"lifecycle\":\"[bounded]\",\"product_storage_selected\":false}}",
        checks.typed_outcomes,
        checks.failed_work_transitions,
        checks.safe_diagnostics,
        checks.authority_absent,
        checks.raw_canary_absent,
    )
}

fn main() -> ExitCode {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let [scenario] = args.as_slice() else {
        eprintln!("hc01_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };
    if scenario == "verdict" {
        println!("{}", render_verdict());
        return ExitCode::SUCCESS;
    }
    let Some(result) = execute_scenario(scenario) else {
        eprintln!("hc01_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };
    println!("{}", render_receipt(&result));
    ExitCode::SUCCESS
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn collapsed_scenario_mapping_cannot_pass() {
        let timeout = execute_scenario("timeout").expect("static scenario");
        let collapsed = vec![
            (TransportOutcome::Timeout, timeout.clone()),
            (TransportOutcome::Cancelled, timeout.clone()),
            (TransportOutcome::TransportOrTlsFailure, timeout.clone()),
            (TransportOutcome::AccessRestricted, timeout),
        ];

        let checks = evaluate_results(&collapsed);
        assert!(!checks.typed_outcomes);
        assert!(!checks.pass());
    }
}
