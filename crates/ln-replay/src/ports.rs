use crate::domain::{CheckpointDigest, CheckpointId, CheckpointRecord, EffectId, OperationId};

/// Load checkpoint lineage for replay validation.
pub trait CheckpointPort {
    fn load(&self, checkpoint_id: &CheckpointId) -> Option<CheckpointRecord>;
}

/// Application-owned external effect ledger. Records applied effects by
/// operation/effect identity so replays can suppress duplicates.
pub trait EffectLedgerPort {
    fn applied_count(&self) -> usize;
    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool;
    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest>;
    /// Record a first-time external effect. Returns false if already applied.
    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool;
}
