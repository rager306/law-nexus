use std::collections::HashMap;

use crate::domain::{H1UnitId, OperationId, PublicationRecord, ScopeId, WriterId};
use crate::ports::PublicationLedgerPort;

/// Honest in-memory publication ledger for HC-15 pure seam tests.
#[derive(Debug, Default, Clone)]
pub struct InMemoryPublicationLedger {
    by_operation: HashMap<String, PublicationRecord>,
    by_scope: HashMap<String, PublicationRecord>,
    writer_for_scope: HashMap<String, WriterId>,
    units: HashMap<String, PublicationRecord>,
}

impl InMemoryPublicationLedger {
    pub fn new() -> Self {
        Self::default()
    }
}

impl PublicationLedgerPort for InMemoryPublicationLedger {
    fn get_by_operation(&self, operation_id: &OperationId) -> Option<PublicationRecord> {
        self.by_operation.get(operation_id.as_str()).cloned()
    }

    fn get_authoritative_for_scope(&self, scope_id: &ScopeId) -> Option<PublicationRecord> {
        self.by_scope
            .get(scope_id.as_str())
            .filter(|r| r.authoritative)
            .cloned()
    }

    fn writer_for_scope(&self, scope_id: &ScopeId) -> Option<WriterId> {
        self.writer_for_scope.get(scope_id.as_str()).cloned()
    }

    fn put(&mut self, record: PublicationRecord) {
        self.by_operation
            .insert(record.operation_id.as_str().to_owned(), record.clone());
        if record.authoritative {
            self.by_scope
                .insert(record.scope_id.as_str().to_owned(), record.clone());
            self.writer_for_scope.insert(
                record.scope_id.as_str().to_owned(),
                record.writer_id.clone(),
            );
        }
        self.units
            .insert(record.h1_unit_id.as_str().to_owned(), record);
    }

    fn authoritative_count(&self) -> usize {
        self.by_scope.values().filter(|r| r.authoritative).count()
    }

    fn has_unit(&self, unit_id: &H1UnitId) -> bool {
        self.units.contains_key(unit_id.as_str())
    }
}

/// Hostile ledger that attempts to mint a second writer/unit on every put.
/// Application-owned exclusivity must ignore this and keep one unit.
#[derive(Debug, Default)]
pub struct HostileDualWriterLedger {
    inner: InMemoryPublicationLedger,
    forced_second_writer_attempts: usize,
}

impl HostileDualWriterLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn forced_second_writer_attempts(&self) -> usize {
        self.forced_second_writer_attempts
    }
}

impl PublicationLedgerPort for HostileDualWriterLedger {
    fn get_by_operation(&self, operation_id: &OperationId) -> Option<PublicationRecord> {
        self.inner.get_by_operation(operation_id)
    }

    fn get_authoritative_for_scope(&self, scope_id: &ScopeId) -> Option<PublicationRecord> {
        self.inner.get_authoritative_for_scope(scope_id)
    }

    fn writer_for_scope(&self, scope_id: &ScopeId) -> Option<WriterId> {
        // Lie: claim no writer so a naive caller might admit a second writer.
        let _ = scope_id;
        None
    }

    fn put(&mut self, mut record: PublicationRecord) {
        // Record the honest first write, then force a second hostile unit.
        self.inner.put(record.clone());
        self.forced_second_writer_attempts += 1;

        let hostile_writer = WriterId::parse("writer:hostile-second").expect("static id");
        let hostile_unit = H1UnitId::parse(&format!(
            "h1:hostile:{}",
            self.forced_second_writer_attempts
        ))
        .expect("static id");
        record.writer_id = hostile_writer;
        record.h1_unit_id = hostile_unit;
        record.authoritative = true;
        record.publication_authority = Some(crate::domain::PublicationAuthority::default());
        // Second put under a synthetic operation key to inflate counts.
        let hostile_op = OperationId::parse(&format!(
            "op:hostile:{}",
            self.forced_second_writer_attempts
        ))
        .expect("static id");
        record.operation_id = hostile_op;
        self.inner.put(record);
    }

    fn authoritative_count(&self) -> usize {
        // Inflate: claim many authoritative units.
        self.inner.authoritative_count().saturating_mul(2).max(99)
    }

    fn has_unit(&self, unit_id: &H1UnitId) -> bool {
        self.inner.has_unit(unit_id)
    }
}
