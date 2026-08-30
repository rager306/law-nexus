use crate::domain::{CheckpointDigest, CheckpointId, CheckpointRecord, EffectId, OperationId};

/// Load checkpoint lineage for replay validation.
pub trait CheckpointPort {
    fn load(&self, checkpoint_id: &CheckpointId) -> Option<CheckpointRecord>;
}

/// Application-owned external effect ledger. Records applied effects by
/// operation/effect identity so replays can suppress duplicates. Adapters are
/// either in-memory test doubles (`InMemoryEffectLedger`) or durable
/// append-only JSONL logs (`JsonlEffectLedger`, path from
/// `EFFECT_LEDGER_PATH`, empty-as-unset fail-closed).
pub trait EffectLedgerPort {
    fn applied_count(&self) -> usize;
    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool;
    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest>;
    /// Record a first-time external effect. Returns false if already applied.
    /// Durable adapters also return false when the record cannot be persisted,
    /// so an unrecorded effect is never treated as applied; the typed failure
    /// stays available on the concrete adapter (see
    /// `JsonlEffectLedger::try_apply_checked` / `take_error`).
    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool;
}
