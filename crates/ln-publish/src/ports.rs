use crate::domain::{H1UnitId, OperationId, PublicationRecord, ScopeId, WriterId};

/// Best-effort publication ledger. Application-owned maps are authoritative for
/// exclusive writer, unit identity, and completeness gating. Adapters may be
/// hostile or lossy and must not mint a second authoritative unit.
pub trait PublicationLedgerPort {
    fn get_by_operation(&self, operation_id: &OperationId) -> Option<PublicationRecord>;
    fn get_authoritative_for_scope(&self, scope_id: &ScopeId) -> Option<PublicationRecord>;
    fn writer_for_scope(&self, scope_id: &ScopeId) -> Option<WriterId>;
    fn put(&mut self, record: PublicationRecord);
    /// Count of authoritative units reported by the adapter (may lie).
    fn authoritative_count(&self) -> usize;
    fn has_unit(&self, unit_id: &H1UnitId) -> bool;
}
