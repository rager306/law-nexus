use std::collections::HashMap;

use crate::adapters::{next_attempt_id, DigestBackedItemIdentity};
#[cfg(test)]
use crate::domain::InventoryItemId;
use crate::domain::{
    InventoryDisposition, InventoryRequest, InventoryResult, InventoryVisibility,
    ObservationAttempt,
};
use crate::ports::{InventoryStorePort, ItemIdentityPort, VisibilityPort};

pub struct InventoryImmutableIntake<S, V, I = DigestBackedItemIdentity> {
    store: S,
    visibility: V,
    identity: I,
    /// Application-owned append-only history. Store adapters may be hostile or
    /// lossy; inventory policy still preserves prior observation attempts.
    history: HashMap<String, Vec<ObservationAttempt>>,
}

impl<S, V> InventoryImmutableIntake<S, V, DigestBackedItemIdentity>
where
    S: InventoryStorePort,
    V: VisibilityPort,
{
    pub fn new(store: S, visibility: V) -> Self {
        Self {
            store,
            visibility,
            identity: DigestBackedItemIdentity,
            history: HashMap::new(),
        }
    }
}

impl<S, V, I> InventoryImmutableIntake<S, V, I>
where
    S: InventoryStorePort,
    V: VisibilityPort,
    I: ItemIdentityPort,
{
    pub fn inventory(&mut self, request: InventoryRequest) -> InventoryResult {
        let item_id = self.identity.resolve_item_id(&request);
        let key = item_id.as_str().to_owned();
        let existing = self.history.get(&key).cloned().unwrap_or_default();
        let attempt = ObservationAttempt {
            attempt_id: next_attempt_id(existing.len()),
            request_id: request.request_id.clone(),
            drop_reference: request.drop_reference.clone(),
            input_digest: request.input_digest().to_owned(),
        };
        // Best-effort persistence. Policy history does not depend on store honesty.
        let _ = self.store.append_attempt(&item_id, attempt.clone());
        let mut observation_attempts = existing;
        observation_attempts.push(attempt);
        self.history.insert(key, observation_attempts.clone());
        let _ = self.visibility.inventory_review_visible(&item_id);

        InventoryResult {
            item_id,
            input_digest: request.input_digest().to_owned(),
            disposition: InventoryDisposition::Pending,
            visibility: InventoryVisibility::InventoryReview,
            observation_attempts,
            curated_label: None,
            current_label: None,
            promotion_id: None,
            publication_id: None,
        }
    }

    #[cfg(test)]
    pub fn history_len(&self, item_id: &InventoryItemId) -> usize {
        self.history
            .get(item_id.as_str())
            .map(Vec::len)
            .unwrap_or(0)
    }
}
