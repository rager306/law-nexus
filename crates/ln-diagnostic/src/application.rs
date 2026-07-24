use crate::domain::{
    DiagnosticEntry, DiagnosticOutcome, DiagnosticResult, DIAGNOSTIC_POLICY_VERSION,
};
use crate::ports::DiagnosticSinkPort;

const FORBIDDEN_MARKERS: &[&str] = &[
    "secret",
    "password",
    "token",
    "api_key",
    "private_key",
    "credential",
];

pub struct EmitSafeDiagnostics<S> {
    sink: S,
}

impl<S> EmitSafeDiagnostics<S>
where
    S: DiagnosticSinkPort,
{
    pub fn new(sink: S) -> Self {
        Self { sink }
    }

    pub fn emit(&mut self, entry: DiagnosticEntry) -> DiagnosticResult {
        if entry.contains_injection {
            return DiagnosticResult {
                outcome: DiagnosticOutcome::Blocked,
                diagnostic_id: entry.diagnostic_id,
                emitted_content: None,
                policy_version: DIAGNOSTIC_POLICY_VERSION.to_owned(),
            };
        }
        if entry.contains_secret || entry.contains_raw_legal_text {
            return DiagnosticResult {
                outcome: DiagnosticOutcome::Blocked,
                diagnostic_id: entry.diagnostic_id,
                emitted_content: None,
                policy_version: DIAGNOSTIC_POLICY_VERSION.to_owned(),
            };
        }
        for marker in FORBIDDEN_MARKERS {
            if entry.content.to_lowercase().contains(marker) {
                return DiagnosticResult {
                    outcome: DiagnosticOutcome::Blocked,
                    diagnostic_id: entry.diagnostic_id,
                    emitted_content: None,
                    policy_version: DIAGNOSTIC_POLICY_VERSION.to_owned(),
                };
            }
        }
        if !self.sink.is_allowed(&entry.sink) {
            return DiagnosticResult {
                outcome: DiagnosticOutcome::Blocked,
                diagnostic_id: entry.diagnostic_id,
                emitted_content: None,
                policy_version: DIAGNOSTIC_POLICY_VERSION.to_owned(),
            };
        }
        self.sink.emit(&entry.sink, &entry.content);
        DiagnosticResult {
            outcome: DiagnosticOutcome::Emitted,
            diagnostic_id: entry.diagnostic_id,
            emitted_content: Some(entry.content),
            policy_version: DIAGNOSTIC_POLICY_VERSION.to_owned(),
        }
    }
}
