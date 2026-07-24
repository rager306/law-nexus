use crate::domain::{ProvisionalId, ScopeId};

use crate::domain::AccelerationRequest;

pub trait AccelerationLedgerPort: Send + Sync {
    fn has_provisional(&self, id: &ProvisionalId) -> bool;
    fn provisional_count(&self) -> usize;
    fn put(&mut self, request: &AccelerationRequest);
    fn authoritative_count(&self) -> usize;
    fn label_for(&self, id: &ProvisionalId) -> Option<String>;
}
