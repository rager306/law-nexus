use crate::domain::{InventoryItemId, InventoryRequest, ObservationAttempt};

/// Append-only inventory observations. Re-inventory must not destructively
/// rewrite prior attempts.
pub trait InventoryStorePort {
    fn append_attempt(
        &mut self,
        item_id: &InventoryItemId,
        attempt: ObservationAttempt,
    ) -> Vec<ObservationAttempt>;

    fn attempts_for(&self, item_id: &InventoryItemId) -> Vec<ObservationAttempt>;
}

/// Visibility is intentionally limited to inventory/review surfaces.
pub trait VisibilityPort {
    fn inventory_review_visible(&self, item_id: &InventoryItemId) -> bool;
}

pub trait ItemIdentityPort {
    fn resolve_item_id(&self, request: &InventoryRequest) -> InventoryItemId;
}
