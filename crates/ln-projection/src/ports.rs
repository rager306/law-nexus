use crate::domain::{ExecutorReport, RebuildRequest};

/// Outbound rebuild executor. May fail, cancel, or report partial results.
/// Application owns ceiling policy and Publication Authority non-effect.
pub trait RebuildExecutorPort {
    fn execute(&self, request: &RebuildRequest) -> ExecutorReport;
}
