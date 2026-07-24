use crate::domain::SinkId;

pub trait DiagnosticSinkPort: Send + Sync {
    fn is_allowed(&self, sink: &SinkId) -> bool;
    fn emit(&mut self, sink: &SinkId, content: &str);
}
