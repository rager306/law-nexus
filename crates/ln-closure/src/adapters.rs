use std::collections::HashMap;

use crate::domain::{NodeId, RuleVersion};
use crate::ports::DependencyEvidencePort;

#[derive(Debug, Clone)]
pub struct FixedDependencyEvidence {
    rule_version: RuleVersion,
    /// node -> Some(deps) known; absence of key means unknown node.
    deps: HashMap<String, Vec<NodeId>>,
    progress_count: usize,
    queue_depth: usize,
}

impl FixedDependencyEvidence {
    pub fn new(rule_version: RuleVersion) -> Self {
        Self {
            rule_version,
            deps: HashMap::new(),
            progress_count: 0,
            queue_depth: 0,
        }
    }

    pub fn with_node(mut self, node: NodeId, deps: Vec<NodeId>) -> Self {
        self.deps.insert(node.as_str().to_owned(), deps);
        self
    }

    pub fn with_progress(mut self, progress: usize, queue: usize) -> Self {
        self.progress_count = progress;
        self.queue_depth = queue;
        self
    }
}

impl DependencyEvidencePort for FixedDependencyEvidence {
    fn rule_version(&self) -> RuleVersion {
        self.rule_version.clone()
    }

    fn dependencies_of(&self, node: &NodeId) -> Option<Vec<NodeId>> {
        self.deps.get(node.as_str()).cloned()
    }

    fn known(&self, node: &NodeId) -> bool {
        self.deps.contains_key(node.as_str())
    }

    fn progress_count(&self) -> usize {
        self.progress_count
    }

    fn queue_depth(&self) -> usize {
        self.queue_depth
    }
}

/// Hostile adapter that always reports high progress/queue and invents
/// complete dependency lists for unknown nodes. Application must ignore.
#[derive(Debug, Clone)]
pub struct HostileProgressCompleteness {
    inner: FixedDependencyEvidence,
}

impl HostileProgressCompleteness {
    pub fn wrapping(inner: FixedDependencyEvidence) -> Self {
        Self { inner }
    }
}

impl DependencyEvidencePort for HostileProgressCompleteness {
    fn rule_version(&self) -> RuleVersion {
        self.inner.rule_version()
    }

    fn dependencies_of(&self, node: &NodeId) -> Option<Vec<NodeId>> {
        // If unknown, invent empty deps as if complete.
        Some(
            self.inner
                .dependencies_of(node)
                .unwrap_or_else(|| Vec::new()),
        )
    }

    fn known(&self, node: &NodeId) -> bool {
        // Pretend every node is known.
        let _ = node;
        true
    }

    fn progress_count(&self) -> usize {
        10_000
    }

    fn queue_depth(&self) -> usize {
        0
    }
}
