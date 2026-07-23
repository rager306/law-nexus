use crate::domain::{Disposition, InventoryItemId, PromotionResult};

pub trait DispositionStorePort {
    fn set_disposition(&mut self, disposition: Disposition);
    fn get_disposition(&self, item_id: &InventoryItemId) -> Option<Disposition>;
}

pub trait PromotionGatePort {
    fn attempt_promotion(
        &mut self,
        item_id: &InventoryItemId,
        disposition_is_accepted: bool,
    ) -> PromotionResult;
}
