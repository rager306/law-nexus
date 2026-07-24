use std::collections::HashMap;

use crate::domain::{
    CheckpointDigest, EffectId, OperationId, ReplayOutcome, ReplayRequest, ReplayResult,
    ReplayTrace, REPLAY_POLICY_VERSION,
};
use crate::ports::{CheckpointPort, EffectLedgerPort};

/// Application replay policy for Coordinate Checkpoint and Replay (HC-14).
/// Owns suppress-by-operation/effect identity in an application-owned ledger.
/// External EffectLedgerPort is best-effort only and cannot force re-apply.
/// Corrupt digests and incompatible rules fail closed without authority change.
pub struct CoordinateCheckpointAndReplay<C, L> {
    checkpoints: C,
    ledger: L,
    /// Application-owned applied identities: key -> digest.
    applied: HashMap<String, CheckpointDigest>,
}

impl<C, L> CoordinateCheckpointAndReplay<C, L>
where
    C: CheckpointPort,
    L: EffectLedgerPort,
{
    pub fn new(checkpoints: C, ledger: L) -> Self {
        Self {
            checkpoints,
            ledger,
            applied: HashMap::new(),
        }
    }

    pub fn applied_count(&self) -> usize {
        self.applied.len()
    }

    fn key(operation_id: &OperationId, effect_id: &EffectId) -> String {
        format!("{}|{}", operation_id.as_str(), effect_id.as_str())
    }

    pub fn replay(&mut self, request: ReplayRequest) -> ReplayResult {
        let applied_before = self.applied.len();

        let Some(record) = self.checkpoints.load(&request.checkpoint_id) else {
            return self.finish(
                request,
                ReplayOutcome::Incomplete,
                None,
                None,
                None,
                applied_before,
                applied_before,
                false,
                false,
            );
        };

        if record.digest != request.expected_digest {
            return self.finish(
                request,
                ReplayOutcome::Corrupt,
                Some(record.digest.clone()),
                Some(record.rule_version.clone()),
                None,
                applied_before,
                applied_before,
                false,
                false,
            );
        }

        if record.rule_version != request.expected_rule_version {
            return self.finish(
                request,
                ReplayOutcome::IncompatibleRule,
                Some(record.digest.clone()),
                Some(record.rule_version.clone()),
                None,
                applied_before,
                applied_before,
                false,
                false,
            );
        }

        if record.operation_id != request.operation_id || record.effect_id != request.effect_id {
            return self.finish(
                request,
                ReplayOutcome::Mismatch,
                Some(record.digest.clone()),
                Some(record.rule_version.clone()),
                None,
                applied_before,
                applied_before,
                false,
                false,
            );
        }

        let key = Self::key(&request.operation_id, &request.effect_id);
        if let Some(prior) = self.applied.get(&key).cloned() {
            // Suppress: do not re-apply; ignore hostile external ledger.
            let _ = self
                .ledger
                .has_applied(&request.operation_id, &request.effect_id);
            return self.finish(
                request,
                ReplayOutcome::Suppressed,
                Some(record.digest.clone()),
                Some(record.rule_version.clone()),
                Some(prior),
                applied_before,
                applied_before,
                true,
                false,
            );
        }

        // First apply: application ledger is authoritative.
        self.applied.insert(key, record.digest.clone());
        // Best-effort external side channel only.
        let _ = self
            .ledger
            .try_apply(&request.operation_id, &request.effect_id, &record.digest);
        let after = self.applied.len();
        self.finish(
            request,
            ReplayOutcome::Applied,
            Some(record.digest.clone()),
            Some(record.rule_version.clone()),
            None,
            applied_before,
            after,
            false,
            false,
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn finish(
        &self,
        request: ReplayRequest,
        outcome: ReplayOutcome,
        observed_digest: Option<CheckpointDigest>,
        observed_rule_version: Option<crate::domain::RuleVersion>,
        prior_applied_digest: Option<CheckpointDigest>,
        applied_count_before: usize,
        applied_count_after: usize,
        effect_suppressed: bool,
        lineage_rewritten: bool,
    ) -> ReplayResult {
        let publication_authority = None;
        let publication_authority_changed = false;
        let trace = ReplayTrace {
            policy_version: REPLAY_POLICY_VERSION.to_owned(),
            request_id: request.request_id.clone(),
            outcome,
            checkpoint_id: request.checkpoint_id.clone(),
            expected_digest: request.expected_digest.clone(),
            observed_digest,
            expected_rule_version: request.expected_rule_version.clone(),
            observed_rule_version,
            operation_id: request.operation_id.clone(),
            effect_id: request.effect_id.clone(),
            prior_applied_digest,
            applied_count_before,
            applied_count_after,
            effect_suppressed,
            lineage_rewritten,
            publication_authority,
            publication_authority_changed,
        };
        ReplayResult {
            outcome,
            applied_count: applied_count_after,
            effect_suppressed,
            lineage_rewritten,
            publication_authority,
            publication_authority_changed,
            trace,
        }
    }
}
