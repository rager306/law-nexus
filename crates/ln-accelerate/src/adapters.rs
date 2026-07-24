use std::collections::HashMap;

use crate::domain::AccelerationRequest;
use crate::domain::ProvisionalId;
use crate::ports::AccelerationLedgerPort;

#[derive(Debug, Default)]
pub struct InMemoryAccelerationLedger {
    provisionals: HashMap<String, AccelerationRequest>,
}

impl InMemoryAccelerationLedger {
    pub fn new() -> Self {
        Self::default()
    }
}

impl AccelerationLedgerPort for InMemoryAccelerationLedger {
    fn has_provisional(&self, id: &ProvisionalId) -> bool {
        self.provisionals.contains_key(id.as_str())
    }
    fn provisional_count(&self) -> usize {
        self.provisionals.len()
    }
    fn put(&mut self, request: &AccelerationRequest) {
        self.provisionals
            .insert(request.provisional_id.as_str().to_owned(), request.clone());
    }
    fn authoritative_count(&self) -> usize {
        0
    }
    fn label_for(&self, id: &ProvisionalId) -> Option<String> {
        self.provisionals
            .get(id.as_str())
            .map(|r| r.label.as_str().to_owned())
    }
}

/// Hostile: tries to mutate labels and claim authority.
#[derive(Debug, Default)]
pub struct HostileLabelMutatorLedger {
    inner: InMemoryAccelerationLedger,
}

impl HostileLabelMutatorLedger {
    pub fn new() -> Self {
        Self::default()
    }
}

impl AccelerationLedgerPort for HostileLabelMutatorLedger {
    fn has_provisional(&self, id: &ProvisionalId) -> bool {
        self.inner.has_provisional(id)
    }
    fn provisional_count(&self) -> usize {
        self.inner.provisional_count()
    }
    fn put(&mut self, request: &AccelerationRequest) {
        self.inner.put(request);
    }
    fn authoritative_count(&self) -> usize {
        99
    }
    fn label_for(&self, id: &ProvisionalId) -> Option<String> {
        self.inner
            .label_for(id)
            .map(|_| "authoritative:mutated".to_owned())
    }
}
