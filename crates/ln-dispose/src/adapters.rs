use std::collections::HashMap;

use crate::domain::{
    CommitId, Disposition, DispositionReason, InventoryItemId, PromotionIdentity, PromotionOutcome,
    PromotionResult,
};
use crate::ports::{DispositionStorePort, PromotionGatePort};

#[derive(Debug, Default)]
pub struct InMemoryDispositionStore {
    items: HashMap<String, Disposition>,
}

impl DispositionStorePort for InMemoryDispositionStore {
    fn set_disposition(&mut self, disposition: Disposition) {
        self.items
            .insert(disposition.item_id.as_str().to_owned(), disposition);
    }

    fn get_disposition(&self, item_id: &InventoryItemId) -> Option<Disposition> {
        self.items.get(item_id.as_str()).cloned()
    }
}

#[derive(Debug, Default)]
pub struct InMemoryPromotionGate;

impl PromotionGatePort for InMemoryPromotionGate {
    fn attempt_promotion(
        &mut self,
        _item_id: &InventoryItemId,
        disposition_is_accepted: bool,
    ) -> PromotionResult {
        if disposition_is_accepted {
            PromotionResult {
                outcome: PromotionOutcome::Committed,
                reason: DispositionReason::Accepted,
                commit_id: Some(CommitId::parse("commit:synthetic-1").expect("static commit id")),
                promotion_identity: Some(PromotionIdentity::default()),
            }
        } else {
            PromotionResult {
                outcome: PromotionOutcome::Rejected,
                reason: DispositionReason::Incomplete,
                commit_id: None,
                promotion_identity: None,
            }
        }
    }
}
