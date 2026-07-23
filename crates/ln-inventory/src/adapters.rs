use std::collections::HashMap;

use crate::domain::{InventoryItemId, InventoryRequest, ObservationAttempt, ObservationAttemptId};
use crate::ports::{InventoryStorePort, ItemIdentityPort, VisibilityPort};

#[derive(Debug, Default)]
pub struct InMemoryInventoryStore {
    attempts: HashMap<String, Vec<ObservationAttempt>>,
}

impl InventoryStorePort for InMemoryInventoryStore {
    fn append_attempt(
        &mut self,
        item_id: &InventoryItemId,
        attempt: ObservationAttempt,
    ) -> Vec<ObservationAttempt> {
        let entry = self
            .attempts
            .entry(item_id.as_str().to_owned())
            .or_default();
        entry.push(attempt);
        entry.clone()
    }

    fn attempts_for(&self, item_id: &InventoryItemId) -> Vec<ObservationAttempt> {
        self.attempts
            .get(item_id.as_str())
            .cloned()
            .unwrap_or_default()
    }
}

#[derive(Debug, Default)]
pub struct InMemoryVisibilityView;

impl VisibilityPort for InMemoryVisibilityView {
    fn inventory_review_visible(&self, _item_id: &InventoryItemId) -> bool {
        true
    }
}

#[derive(Debug, Default)]
pub struct DigestBackedItemIdentity;

impl ItemIdentityPort for DigestBackedItemIdentity {
    fn resolve_item_id(&self, request: &InventoryRequest) -> InventoryItemId {
        // One logical inventory item per drop+digest. Re-inventory keeps the
        // same identity and appends observation attempts.
        InventoryItemId::parse(&format!(
            "item:{}:{}",
            request.drop_reference.as_str(),
            request.input_digest()
        ))
        .expect("constructed item id fits namespace")
    }
}

pub fn next_attempt_id(existing_attempts: usize) -> ObservationAttemptId {
    ObservationAttemptId::parse(&format!("attempt:{}", existing_attempts + 1))
        .expect("constructed attempt id fits namespace")
}
