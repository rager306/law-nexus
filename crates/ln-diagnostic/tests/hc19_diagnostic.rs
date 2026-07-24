use ln_diagnostic::adapters::{HostileCanarySink, InMemoryDiagnosticSink};
use ln_diagnostic::application::EmitSafeDiagnostics;
use ln_diagnostic::domain::{
    DiagnosticEntry, DiagnosticId, DiagnosticOutcome, SinkId, DIAGNOSTIC_POLICY_VERSION,
};

fn entry(sink: &str, content: &str) -> DiagnosticEntry {
    DiagnosticEntry {
        diagnostic_id: DiagnosticId::parse("diag:1").unwrap(),
        sink: SinkId::parse(sink).unwrap(),
        content: content.to_owned(),
        contains_secret: false,
        contains_raw_legal_text: false,
        contains_injection: false,
    }
}

#[test]
fn safe_content_emitted_to_allowed_sink() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let result = svc.emit(entry("sink:log", "operation completed"));
    assert_eq!(result.outcome, DiagnosticOutcome::Emitted);
    assert!(result.emitted_content.is_some());
}

#[test]
fn secret_content_blocked() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let mut e = entry("sink:log", "processing data");
    e.contains_secret = true;
    let result = svc.emit(e);
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
    assert!(result.emitted_content.is_none());
}

#[test]
fn raw_legal_text_blocked() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let mut e = entry("sink:log", "processing");
    e.contains_raw_legal_text = true;
    let result = svc.emit(e);
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
}

#[test]
fn forbidden_marker_in_content_blocked() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let result = svc.emit(entry("sink:log", "user api_key=abc123"));
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
}

#[test]
fn injection_attempt_blocked() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let mut e = entry("sink:log", "data");
    e.contains_injection = true;
    let result = svc.emit(e);
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
}

#[test]
fn disallowed_sink_blocked() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new());
    let result = svc.emit(entry("sink:unknown", "safe content"));
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
}

#[test]
fn hostile_canary_sink_still_blocks_secrets() {
    let mut svc = EmitSafeDiagnostics::new(HostileCanarySink::new());
    let mut e = entry("sink:any", "data");
    e.contains_secret = true;
    let result = svc.emit(e);
    assert_eq!(result.outcome, DiagnosticOutcome::Blocked);
}

#[test]
fn policy_version_stable() {
    let mut svc = EmitSafeDiagnostics::new(InMemoryDiagnosticSink::new().allow("sink:log"));
    let result = svc.emit(entry("sink:log", "ok"));
    assert_eq!(result.policy_version, DIAGNOSTIC_POLICY_VERSION);
}
