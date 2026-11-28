use std::collections::HashMap;

use ln_fsm::{DeterministicFsm, TransitionRejection};

use crate::domain::{
    Disposition, DispositionEvent, DispositionFsm, DispositionReason, DispositionState,
    DispositionTransitionRefusal, InventoryItemId, PromotionAttemptId, PromotionOutcome,
    PromotionRequestId, PromotionResult, ReviewEvidenceId,
};
use crate::ports::{DispositionStorePort, PromotionGatePort};

/// HC-03 application-owned disposition service.
///
/// Store and gate adapters may be hostile or lossy; authoritative disposition
/// state and terminal immutability are enforced in-process via [`DispositionFsm`].
pub struct DisposeReview<S, G> {
    store: S,
    gate: G,
    dispositions: HashMap<String, Disposition>,
}

impl<S, G> DisposeReview<S, G>
where
    S: DispositionStorePort,
    G: PromotionGatePort,
{
    pub fn new(store: S, gate: G) -> Self {
        Self {
            store,
            gate,
            dispositions: HashMap::new(),
        }
    }

    pub fn set_pending(
        &mut self,
        item_id: InventoryItemId,
        evidence_ids: Vec<ReviewEvidenceId>,
    ) -> Disposition {
        if let Some(current) = self.dispositions.get(item_id.as_str())
            && DispositionFsm.is_terminal(&current.state)
        {
            return current.clone();
        }
        let d = Disposition {
            item_id: item_id.clone(),
            state: DispositionState::Pending,
            reason: DispositionReason::Incomplete,
            evidence_ids,
            accepted_commit_id: None,
            promotion_identity: None,
        };
        self.dispositions
            .insert(item_id.as_str().to_owned(), d.clone());
        // Best-effort persistence only; policy does not trust store honesty.
        self.store.set_disposition(d.clone());
        d
    }

    pub fn set_quarantined(
        &mut self,
        item_id: InventoryItemId,
        evidence_ids: Vec<ReviewEvidenceId>,
    ) -> Disposition {
        if let Some(current) = self.dispositions.get(item_id.as_str())
            && DispositionFsm.is_terminal(&current.state)
        {
            return current.clone();
        }
        let d = Disposition {
            item_id: item_id.clone(),
            state: DispositionState::Quarantined,
            reason: DispositionReason::Conflict,
            evidence_ids,
            accepted_commit_id: None,
            promotion_identity: None,
        };
        self.dispositions
            .insert(item_id.as_str().to_owned(), d.clone());
        self.store.set_disposition(d.clone());
        d
    }

    pub fn attempt_promotion(
        &mut self,
        item_id: InventoryItemId,
        _request_id: PromotionRequestId,
        _attempt_id: PromotionAttemptId,
    ) -> PromotionResult {
        let disposition = self.dispositions.get(item_id.as_str()).cloned();
        let accepted = disposition
            .as_ref()
            .map(|d| d.state.is_accepted())
            .unwrap_or(false);

        let result = self.gate.attempt_promotion(&item_id, accepted);

        // Fail closed whenever authoritative disposition is not Accepted, even
        // if a hostile PromotionGatePort tries to return Committed.
        if !accepted || result.outcome == PromotionOutcome::Rejected {
            let reason = disposition
                .as_ref()
                .map(|d| d.reason)
                .unwrap_or(DispositionReason::Incomplete);
            return PromotionResult {
                outcome: PromotionOutcome::Rejected,
                reason,
                commit_id: None,
                promotion_identity: None,
            };
        }
        result
    }

    pub fn disposition(&self, item_id: &InventoryItemId) -> Disposition {
        self.dispositions
            .get(item_id.as_str())
            .cloned()
            .unwrap_or(Disposition {
                item_id: item_id.clone(),
                state: DispositionState::Pending,
                reason: DispositionReason::Incomplete,
                evidence_ids: Vec::new(),
                accepted_commit_id: None,
                promotion_identity: None,
            })
    }

    /// Apply a typed HC-03 disposition lifecycle event fail-closed via [`DispositionFsm`].
    pub fn transition_disposition(
        &mut self,
        item_id: InventoryItemId,
        event: DispositionEvent,
        evidence_ids: Vec<ReviewEvidenceId>,
    ) -> Result<
        Disposition,
        TransitionRejection<DispositionState, DispositionEvent, DispositionTransitionRefusal>,
    > {
        let current = self.disposition(&item_id);
        let receipt = DispositionFsm.apply(current.state, event)?;
        let reason = match receipt.next {
            DispositionState::Pending => DispositionReason::Incomplete,
            DispositionState::Quarantined => DispositionReason::Conflict,
            DispositionState::Accepted => DispositionReason::Accepted,
            DispositionState::Rejected => DispositionReason::RejectedReasonCoded,
        };
        let updated = Disposition {
            item_id: item_id.clone(),
            state: receipt.next,
            reason,
            evidence_ids,
            accepted_commit_id: None,
            promotion_identity: None,
        };
        self.dispositions
            .insert(item_id.as_str().to_owned(), updated.clone());
        self.store.set_disposition(updated.clone());
        Ok(updated)
    }

    /// Test-only helper: route Accepted positive-control seeding through [`DispositionFsm`].
    pub fn store_set_accepted(&mut self, item_id: InventoryItemId) {
        let _ = self.transition_disposition(item_id, DispositionEvent::Accept, Vec::new());
    }
}
