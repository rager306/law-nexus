use std::env;
use std::process::ExitCode;

use ln_diagnostic::adapters::{HostileCanarySink, InMemoryDiagnosticSink};
use ln_diagnostic::application::EmitSafeDiagnostics;
use ln_diagnostic::domain::{DiagnosticEntry, DiagnosticId, DiagnosticOutcome, SinkId};

fn entry(content: &str) -> DiagnosticEntry {
    DiagnosticEntry {
        diagnostic_id: DiagnosticId::parse("diag:1").unwrap(),
        sink: SinkId::parse("sink:log").unwrap(),
        content: content.to_owned(),
        contains_secret: false,
        contains_raw_legal_text: false,
        contains_injection: false,
    }
}

fn render_verdict() -> String {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let safe = svc.emit(entry("operation completed"));
    let mut secret_entry = entry("data");
    secret_entry.contains_secret = true;
    let secret = svc.emit(secret_entry);
    let mut raw = entry("processing");
    raw.contains_raw_legal_text = true;
    let raw_result = svc.emit(raw);
    let marker = svc.emit(entry("user api_key=secret123"));
    let mut inject = entry("data");
    inject.contains_injection = true;
    let injection = svc.emit(inject);
    let mut hostile = EmitSafeDiagnostics::new(HostileCanarySink::new());
    let mut hostile_entry = entry("data");
    hostile_entry.contains_secret = true;
    let hostile_result = hostile.emit(hostile_entry);

    let pass = safe.outcome == DiagnosticOutcome::Emitted
        && secret.outcome == DiagnosticOutcome::Blocked
        && raw_result.outcome == DiagnosticOutcome::Blocked
        && marker.outcome == DiagnosticOutcome::Blocked
        && injection.outcome == DiagnosticOutcome::Blocked
        && hostile_result.outcome == DiagnosticOutcome::Blocked;
    let verdict = if pass { "PASS" } else { "FAIL" };
    format!(
        "{{\"schema\":\"law-nexus-hc19-verdict/v1\",\"evidence_id\":\"S10-HC-19-RT\",\"case_id\":\"HC-19\",\"verdict\":\"{verdict}\",\"scenario_count\":6,\"safe_emitted\":{},\"secret_blocked\":{},\"raw_legal_blocked\":{},\"forbidden_marker_blocked\":{},\"injection_blocked\":{},\"hostile_sink_blocked\":{},\"remaining_unsupported_cases\":1,\"lifecycle\":\"[bounded]\"}}",
        safe.outcome == DiagnosticOutcome::Emitted,
        secret.outcome == DiagnosticOutcome::Blocked,
        raw_result.outcome == DiagnosticOutcome::Blocked,
        marker.outcome == DiagnosticOutcome::Blocked,
        injection.outcome == DiagnosticOutcome::Blocked,
        hostile_result.outcome == DiagnosticOutcome::Blocked,
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
            eprintln!("hc19_runner_error:unknown_scenario");
            ExitCode::from(2)
        }
    }
}
