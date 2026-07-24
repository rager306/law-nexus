use std::collections::HashMap;

use crate::domain::{
    AuthoritySurface, CompletenessEvidence, H1UnitId, OperationId, PublicationAuthority,
    PublicationOutcome, PublicationRecord, PublicationResult, PublishRequest, ScopeId, WriterId,
    PUBLICATION_POLICY_VERSION,
};
use crate::ports::PublicationLedgerPort;

/// Application-owned sole Publication Authority for HC-15.
/// Owns exclusive writer assignment, completeness gate, and unit ledger.
/// External PublicationLedgerPort is best-effort only and cannot force a
/// second authoritative unit or grant authority on partial candidates.
pub struct PublishAuthoritativeH1<L> {
    ledger: L,
    /// Authoritative units by operation identity (idempotent publish).
    by_operation: HashMap<String, PublicationRecord>,
    /// Sole authoritative unit per scope.
    by_scope: HashMap<String, PublicationRecord>,
    /// Exclusive writer lock per scope once an authoritative unit exists.
    writer_for_scope: HashMap<String, WriterId>,
    next_unit_seq: u64,
}

impl<L> PublishAuthoritativeH1<L>
where
    L: PublicationLedgerPort,
{
    pub fn new(ledger: L) -> Self {
        Self {
            ledger,
            by_operation: HashMap::new(),
            by_scope: HashMap::new(),
            writer_for_scope: HashMap::new(),
            next_unit_seq: 0,
        }
    }

    pub fn authoritative_count(&self) -> usize {
        self.by_scope.len()
    }

    pub fn has_authoritative_for_scope(&self, scope_id: &ScopeId) -> bool {
        self.by_scope.contains_key(scope_id.as_str())
    }

    pub fn unit_for_scope(&self, scope_id: &ScopeId) -> Option<H1UnitId> {
        self.by_scope
            .get(scope_id.as_str())
            .map(|r| r.h1_unit_id.clone())
    }

    pub fn writer_for_scope(&self, scope_id: &ScopeId) -> Option<WriterId> {
        self.writer_for_scope.get(scope_id.as_str()).cloned()
    }

    pub fn publish(&mut self, request: PublishRequest) -> PublicationResult {
        // Completeness gate: partial/missing never become authoritative.
        if !request.completeness.is_complete() {
            return self.finish(request, PublicationOutcome::Incomplete, None, false, None);
        }

        // Identical operation retry: same effect or typed Duplicate.
        if let Some(existing) = self
            .by_operation
            .get(request.operation_id.as_str())
            .cloned()
        {
            return self.handle_existing_operation(request, existing);
        }

        // Scope already holds an authoritative unit.
        if let Some(existing) = self.by_scope.get(request.scope_id.as_str()).cloned() {
            // Competing writer for the same scope is rejected without mutation.
            if existing.writer_id != request.writer_id {
                return self.finish(
                    request,
                    PublicationOutcome::CompetingWriterRejected,
                    Some(existing.h1_unit_id),
                    false,
                    None,
                );
            }

            // Same writer, different operation identity against existing unit.
            if existing.input_digest != request.input_digest
                || existing.cutoff_id != request.cutoff_id
                || existing.rule_version != request.rule_version
            {
                return self.finish(
                    request,
                    PublicationOutcome::Conflict,
                    Some(existing.h1_unit_id),
                    false,
                    None,
                );
            }

            // Same writer + same digest/scope/cutoff/rules: treat as duplicate
            // of the existing unit (operation may differ but effect is same).
            return self.finish(
                request,
                PublicationOutcome::Duplicate,
                Some(existing.h1_unit_id),
                true,
                existing.publication_authority,
            );
        }

        // Optional: if a writer lock exists without a unit (should not happen),
        // still enforce exclusive writer.
        if let Some(owner) = self.writer_for_scope.get(request.scope_id.as_str()) {
            if owner != &request.writer_id {
                return self.finish(
                    request,
                    PublicationOutcome::CompetingWriterRejected,
                    None,
                    false,
                    None,
                );
            }
        }

        // First complete publish for this scope: mint sole unit + authority.
        self.next_unit_seq += 1;
        let h1_unit_id =
            H1UnitId::parse(&format!("h1:{}", self.next_unit_seq)).expect("static h1 unit id");
        let record = PublicationRecord {
            operation_id: request.operation_id.clone(),
            writer_id: request.writer_id.clone(),
            scope_id: request.scope_id.clone(),
            cutoff_id: request.cutoff_id.clone(),
            rule_version: request.rule_version.clone(),
            input_digest: request.input_digest.clone(),
            h1_unit_id: h1_unit_id.clone(),
            completeness: CompletenessEvidence::Complete,
            authoritative: true,
            publication_authority: Some(PublicationAuthority::default()),
            authority_surface: AuthoritySurface::Publication,
        };

        self.by_operation
            .insert(request.operation_id.as_str().to_owned(), record.clone());
        self.by_scope
            .insert(request.scope_id.as_str().to_owned(), record.clone());
        self.writer_for_scope.insert(
            request.scope_id.as_str().to_owned(),
            request.writer_id.clone(),
        );

        // Best-effort external ledger. Policy does not depend on ledger honesty.
        self.ledger.put(record);

        self.finish(
            request,
            PublicationOutcome::Published,
            Some(h1_unit_id),
            true,
            Some(PublicationAuthority::default()),
        )
    }

    pub fn cancel(&mut self, operation_id: OperationId, writer_id: WriterId) -> PublicationResult {
        if let Some(existing) = self.by_operation.get(operation_id.as_str()).cloned() {
            // Cannot cancel an already authoritative unit; unit remains.
            return PublicationResult {
                outcome: PublicationOutcome::Duplicate,
                operation_id,
                writer_id,
                scope_id: existing.scope_id,
                h1_unit_id: Some(existing.h1_unit_id),
                input_digest: Some(existing.input_digest),
                authoritative: true,
                publication_authority: existing.publication_authority,
                authority_surface: AuthoritySurface::Publication,
                policy_version: PUBLICATION_POLICY_VERSION.to_owned(),
            };
        }

        PublicationResult {
            outcome: PublicationOutcome::Cancelled,
            operation_id,
            writer_id,
            scope_id: ScopeId::parse("scope:none").expect("static id"),
            h1_unit_id: None,
            input_digest: None,
            authoritative: false,
            publication_authority: None,
            authority_surface: AuthoritySurface::Publication,
            policy_version: PUBLICATION_POLICY_VERSION.to_owned(),
        }
    }

    pub fn fail(&mut self, request: PublishRequest) -> PublicationResult {
        // Explicit failure path: never grants authority and never mutates units.
        self.finish(request, PublicationOutcome::Failed, None, false, None)
    }

    fn handle_existing_operation(
        &self,
        request: PublishRequest,
        existing: PublicationRecord,
    ) -> PublicationResult {
        if existing.writer_id != request.writer_id {
            return self.finish(
                request,
                PublicationOutcome::CompetingWriterRejected,
                Some(existing.h1_unit_id),
                false,
                None,
            );
        }
        if existing.scope_id != request.scope_id
            || existing.input_digest != request.input_digest
            || existing.cutoff_id != request.cutoff_id
            || existing.rule_version != request.rule_version
        {
            return self.finish(
                request,
                PublicationOutcome::Conflict,
                Some(existing.h1_unit_id),
                false,
                None,
            );
        }
        self.finish(
            request,
            PublicationOutcome::Duplicate,
            Some(existing.h1_unit_id),
            true,
            existing.publication_authority,
        )
    }

    fn finish(
        &self,
        request: PublishRequest,
        outcome: PublicationOutcome,
        h1_unit_id: Option<H1UnitId>,
        authoritative: bool,
        publication_authority: Option<PublicationAuthority>,
    ) -> PublicationResult {
        // Authority is only present for complete authoritative outcomes.
        let (authoritative, publication_authority) = if authoritative
            && matches!(
                outcome,
                PublicationOutcome::Published | PublicationOutcome::Duplicate
            ) {
            (true, publication_authority)
        } else {
            (false, None)
        };

        PublicationResult {
            outcome,
            operation_id: request.operation_id,
            writer_id: request.writer_id,
            scope_id: request.scope_id,
            h1_unit_id,
            input_digest: if authoritative {
                Some(request.input_digest)
            } else if matches!(
                outcome,
                PublicationOutcome::Conflict | PublicationOutcome::CompetingWriterRejected
            ) {
                None
            } else {
                Some(request.input_digest)
            },
            authoritative,
            publication_authority,
            authority_surface: AuthoritySurface::Publication,
            policy_version: PUBLICATION_POLICY_VERSION.to_owned(),
        }
    }
}
