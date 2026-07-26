use std::collections::HashSet;

use crate::domain::EvidenceId;
use crate::ports::QueryStatePort;

#[derive(Debug, Default)]
pub struct InMemoryQueryState {
    evidence: HashSet<String>,
}

impl InMemoryQueryState {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with_evidence(mut self, id: &str) -> Self {
        self.evidence.insert(id.to_owned());
        self
    }
}

impl QueryStatePort for InMemoryQueryState {
    fn has_evidence(&self, id: &EvidenceId) -> bool {
        self.evidence.contains(id.as_str())
    }
    fn evidence_ids(&self) -> Vec<EvidenceId> {
        self.evidence
            .iter()
            .filter_map(|s| EvidenceId::parse(s).ok())
            .collect()
    }
}

/// Hostile: claims all evidence exists (gap invention).
#[derive(Debug, Default)]
pub struct HostileGapInventorState {
    real: InMemoryQueryState,
}

impl HostileGapInventorState {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn with_evidence(mut self, id: &str) -> Self {
        self.real = self.real.with_evidence(id);
        self
    }
}

impl QueryStatePort for HostileGapInventorState {
    fn has_evidence(&self, _id: &EvidenceId) -> bool {
        true
    }
    fn evidence_ids(&self) -> Vec<EvidenceId> {
        self.real.evidence_ids()
    }
}
