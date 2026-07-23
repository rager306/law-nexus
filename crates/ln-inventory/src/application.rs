use crate::adapters::{next_attempt_id, DigestBackedItemIdentity};
use crate::domain::{
    InventoryDisposition, InventoryRequest, InventoryResult, InventoryVisibility,
    ObservationAttempt,
};
use crate::ports::{InventoryStorePort, ItemIdentityPort, VisibilityPort};

pub struct InventoryImmutableIntake<S, V, I = DigestBackedItemIdentity> {
    store: S,
    visibility: V,
    identity: I,
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
        let existing = self.store.attempts_for(&item_id);
        let attempt = ObservationAttempt {
            attempt_id: next_attempt_id(existing.len()),
            request_id: request.request_id.clone(),
            drop_reference: request.drop_reference.clone(),
            input_digest: request.input_digest().to_owned(),
        };
        let observation_attempts = self.store.append_attempt(&item_id, attempt);
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
}
