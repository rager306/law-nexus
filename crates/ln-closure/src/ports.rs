use crate::domain::{NodeId, RuleVersion};

/// Read-only dependency evidence for a changed set.
/// Adapters supply edges and metadata; application owns completeness policy
/// and freezes a registered-node snapshot at compute start.
pub trait DependencyEvidencePort {
    fn rule_version(&self) -> RuleVersion;
    /// Nodes with registered evidence records. Application freezes this set.
    fn registered_nodes(&self) -> Vec<NodeId>;
    /// Known direct dependencies of a registered node. Missing node → None.
    fn dependencies_of(&self, node: &NodeId) -> Option<Vec<NodeId>>;
    /// Optional progress/queue signals. Application must never use these as
    /// completeness evidence.
    fn progress_count(&self) -> usize {
        0
    }
    fn queue_depth(&self) -> usize {
        0
    }
}
