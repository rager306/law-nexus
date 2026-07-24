use std::collections::HashMap;

use crate::domain::{
    CheckpointDigest, CheckpointId, CheckpointRecord, EffectId, OperationId, RuleVersion,
};
use crate::ports::{CheckpointPort, EffectLedgerPort};

#[derive(Debug, Default, Clone)]
pub struct InMemoryCheckpointStore {
    records: HashMap<String, CheckpointRecord>,
}

impl InMemoryCheckpointStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(mut self, record: CheckpointRecord) -> Self {
        self.records
            .insert(record.checkpoint_id.as_str().to_owned(), record);
        self
    }
}

impl CheckpointPort for InMemoryCheckpointStore {
    fn load(&self, checkpoint_id: &CheckpointId) -> Option<CheckpointRecord> {
        self.records.get(checkpoint_id.as_str()).cloned()
    }
}

#[derive(Debug, Default, Clone)]
pub struct InMemoryEffectLedger {
    /// key: operation_id + effect_id
    applied: HashMap<String, CheckpointDigest>,
}

impl InMemoryEffectLedger {
    pub fn new() -> Self {
        Self::default()
    }

    fn key(operation_id: &OperationId, effect_id: &EffectId) -> String {
        format!("{}|{}", operation_id.as_str(), effect_id.as_str())
    }
}

impl EffectLedgerPort for InMemoryEffectLedger {
    fn applied_count(&self) -> usize {
        self.applied.len()
    }

    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool {
        self.applied
            .contains_key(&Self::key(operation_id, effect_id))
    }

    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest> {
        self.applied
            .get(&Self::key(operation_id, effect_id))
            .cloned()
    }

    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool {
        let key = Self::key(operation_id, effect_id);
        if self.applied.contains_key(&key) {
            return false;
        }
        self.applied.insert(key, digest.clone());
        true
    }
}

/// Hostile ledger that claims apply always succeeds and inflates counts,
/// attempting to force duplicate external effects.
#[derive(Debug, Default)]
pub struct HostileDuplicateEffectLedger {
    inner: InMemoryEffectLedger,
    forced_applies: usize,
}

impl HostileDuplicateEffectLedger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn forced_applies(&self) -> usize {
        self.forced_applies
    }
}

impl EffectLedgerPort for HostileDuplicateEffectLedger {
    fn applied_count(&self) -> usize {
        // Inflate count to confuse callers that trust the adapter.
        self.inner.applied_count() + self.forced_applies
    }

    fn has_applied(&self, operation_id: &OperationId, effect_id: &EffectId) -> bool {
        // Lie: always claim not applied so application must still suppress via
        // its own check path — application freezes has_applied from a single
        // call and uses try_apply return for authority.
        let _ = (operation_id, effect_id);
        false
    }

    fn prior_digest(
        &self,
        operation_id: &OperationId,
        effect_id: &EffectId,
    ) -> Option<CheckpointDigest> {
        self.inner.prior_digest(operation_id, effect_id)
    }

    fn try_apply(
        &mut self,
        operation_id: &OperationId,
        effect_id: &EffectId,
        digest: &CheckpointDigest,
    ) -> bool {
        // Always report success and force-insert again under a salted key path
        // via forced counter — application must not re-apply when it already
        // recorded the identity in its own freeze of has_applied.
        let first = self.inner.try_apply(operation_id, effect_id, digest);
        if !first {
            self.forced_applies += 1;
            // Pretend success even on duplicate.
            return true;
        }
        true
    }
}

pub fn sample_checkpoint(
    checkpoint_id: &str,
    digest: &str,
    rules: &str,
    operation: &str,
    effect: &str,
    history: &str,
) -> CheckpointRecord {
    CheckpointRecord {
        checkpoint_id: CheckpointId::parse(checkpoint_id).expect("static id"),
        digest: CheckpointDigest::parse(digest).expect("static id"),
        rule_version: RuleVersion::parse(rules).expect("static id"),
        operation_id: OperationId::parse(operation).expect("static id"),
        effect_id: EffectId::parse(effect).expect("static id"),
        history_digest: CheckpointDigest::parse(history).expect("static id"),
    }
}
