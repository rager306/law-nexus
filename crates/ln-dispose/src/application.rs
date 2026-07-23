use crate::domain::{
    Disposition, DispositionReason, DispositionState, InventoryItemId, PromotionAttemptId,
    PromotionOutcome, PromotionRequestId, PromotionResult, ReviewEvidenceId,
};
use crate::ports::{DispositionStorePort, PromotionGatePort};

pub struct DisposeReview<S, G> {
    store: S,
    gate: G,
}

impl<S, G> DisposeReview<S, G>
where
    S: DispositionStorePort,
    G: PromotionGatePort,
{
    pub fn new(store: S, gate: G) -> Self {
        Self { store, gate }
    }

    pub fn set_pending(
        &mut self,
        item_id: InventoryItemId,
        evidence_ids: Vec<ReviewEvidenceId>,
    ) -> Disposition {
        let d = Disposition {
            item_id,
            state: DispositionState::Pending,
            reason: DispositionReason::Incomplete,
            evidence_ids,
            accepted_commit_id: None,
            promotion_identity: None,
        };
        self.store.set_disposition(d.clone());
        d
    }

    pub fn set_quarantined(
        &mut self,
        item_id: InventoryItemId,
        evidence_ids: Vec<ReviewEvidenceId>,
    ) -> Disposition {
        let d = Disposition {
            item_id,
            state: DispositionState::Quarantined,
            reason: DispositionReason::Conflict,
            evidence_ids,
            accepted_commit_id: None,
            promotion_identity: None,
        };
        self.store.set_disposition(d.clone());
        d
    }

    pub fn attempt_promotion(
        &mut self,
        item_id: InventoryItemId,
        _request_id: PromotionRequestId,
        _attempt_id: PromotionAttemptId,
    ) -> PromotionResult {
        let disposition = self.store.get_disposition(&item_id);
        let accepted = disposition
            .as_ref()
            .map(|d| d.state.is_accepted())
            .unwrap_or(false);

        let result = self.gate.attempt_promotion(&item_id, accepted);

        // For non-accepted states: override reason to match disposition if available.
        if result.outcome == PromotionOutcome::Rejected {
            let reason = disposition
                .as_ref()
                .map(|d| d.reason)
                .unwrap_or(DispositionReason::Incomplete);
            return PromotionResult {
                outcome: result.outcome,
                reason,
                commit_id: None,
                promotion_identity: None,
            };
        }
        result
    }

    pub fn disposition(&self, item_id: &InventoryItemId) -> Disposition {
        self.store.get_disposition(item_id).unwrap_or(Disposition {
            item_id: item_id.clone(),
            state: DispositionState::Pending,
            reason: DispositionReason::Incomplete,
            evidence_ids: Vec::new(),
            accepted_commit_id: None,
            promotion_identity: None,
        })
    }

    /// Test-only helper: set disposition to Accepted for positive control.
    pub fn store_set_accepted(&mut self, item_id: InventoryItemId) {
        self.store.set_disposition(Disposition {
            item_id,
            state: DispositionState::Accepted,
            reason: DispositionReason::Accepted,
            evidence_ids: Vec::new(),
            accepted_commit_id: None,
            promotion_identity: None,
        });
    }
}
