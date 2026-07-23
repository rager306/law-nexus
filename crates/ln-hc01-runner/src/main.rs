use std::env;
use std::process::ExitCode;

use ln_observe::adapters::{InMemoryDiagnosticSink, InMemoryWorkState, InterruptibleSourceAdapter};
use ln_observe::application::ObserveSource;
use ln_observe::domain::{ObservationRequest, ObservationRequestId, SourceChannelId, WorkPhase};

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

fn run(scenario: &str) -> Option<String> {
    let source = adapter_for(scenario)?;
    let mut use_case = ObserveSource::new(
        source,
        InMemoryWorkState::default(),
        InMemoryDiagnosticSink::default(),
    );
    let result = use_case.execute(ObservationRequest::new(
        ObservationRequestId::parse("O1").expect("static request ID is valid"),
        SourceChannelId::parse("S1").expect("static source ID is valid"),
    ));
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

    Some(format!(
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
    ))
}

fn main() -> ExitCode {
    let args = env::args().skip(1).collect::<Vec<_>>();
    let [scenario] = args.as_slice() else {
        eprintln!("hc01_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };
    let Some(receipt) = run(scenario) else {
        eprintln!("hc01_runner_error:unknown_scenario");
        return ExitCode::from(2);
    };
    println!("{receipt}");
    ExitCode::SUCCESS
}
