use std::collections::HashSet;

use crate::domain::SinkId;
use crate::ports::DiagnosticSinkPort;

#[derive(Debug, Default)]
pub struct InMemoryDiagnosticSink {
    allowed: HashSet<String>,
    emitted: Vec<(String, String)>,
}

impl InMemoryDiagnosticSink {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn allow(mut self, sink: &str) -> Self {
        self.allowed.insert(sink.to_owned());
        self
    }
    pub fn emitted_count(&self) -> usize {
        self.emitted.len()
    }
}

impl DiagnosticSinkPort for InMemoryDiagnosticSink {
    fn is_allowed(&self, sink: &SinkId) -> bool {
        self.allowed.contains(sink.as_str())
    }
    fn emit(&mut self, sink: &SinkId, content: &str) {
        self.emitted
            .push((sink.as_str().to_owned(), content.to_owned()));
    }
}

/// Hostile: allows all sinks, ignores forbidden content.
#[derive(Debug, Default)]
pub struct HostileCanarySink {
    inner: InMemoryDiagnosticSink,
}

impl HostileCanarySink {
    pub fn new() -> Self {
        Self::default()
    }
}

impl DiagnosticSinkPort for HostileCanarySink {
    fn is_allowed(&self, sink: &SinkId) -> bool {
        true
    }
    fn emit(&mut self, sink: &SinkId, content: &str) {
        self.inner.emit(sink, content);
    }
}
