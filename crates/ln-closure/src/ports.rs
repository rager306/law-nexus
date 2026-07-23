use crate::domain::{NodeId, RuleVersion};

/// Read-only dependency evidence for a changed set.
/// Adapters supply edges and metadata; application owns completeness policy.
pub trait DependencyEvidencePort {
    fn rule_version(&self) -> RuleVersion;
    /// Known direct dependencies of a node. Missing node → None (unknown).
    fn dependencies_of(&self, node: &NodeId) -> Option<Vec<NodeId>>;
    /// Nodes known to exist in the evidence graph.
    fn known(&self, node: &NodeId) -> bool;
    /// Optional progress/queue signals. Application must never use these as
    /// completeness evidence.
    fn progress_count(&self) -> usize {
        0
    }
    fn queue_depth(&self) -> usize {
        0
    }
}
