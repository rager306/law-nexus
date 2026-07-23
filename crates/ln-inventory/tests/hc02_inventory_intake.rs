use ln_inventory::{
    adapters::{InMemoryInventoryStore, InMemoryVisibilityView},
    application::InventoryImmutableIntake,
    domain::{
        DropReference, InventoryDisposition, InventoryRequest, InventoryRequestId,
        InventoryVisibility, ObservationAttemptId,
    },
};

#[test]
fn re_inventory_of_same_drop_remains_immutable_staging() {
    let bytes = b"SYNTHETIC-IMMUTABLE-DROP-D1";
    let store = InMemoryInventoryStore::default();
    let visibility = InMemoryVisibilityView::default();
    let mut use_case = InventoryImmutableIntake::new(store, visibility);

    let request = InventoryRequest::new(
        InventoryRequestId::parse("INV-1").expect("valid request id"),
        DropReference::parse("D1").expect("valid drop id"),
        bytes,
    );

    let first = use_case.inventory(request.clone());
    let second = use_case.inventory(request);

    assert_eq!(first.input_digest, second.input_digest);
    assert_eq!(first.disposition, InventoryDisposition::Pending);
    assert_eq!(second.disposition, InventoryDisposition::Pending);
    assert_eq!(first.visibility, InventoryVisibility::InventoryReview);
    assert_eq!(second.visibility, InventoryVisibility::InventoryReview);
    assert_eq!(first.observation_attempts.len(), 1);
    assert_eq!(second.observation_attempts.len(), 2);
    assert_eq!(
        first.observation_attempts[0].attempt_id,
        ObservationAttemptId::parse("attempt:1").expect("valid attempt id")
    );
    assert_eq!(
        second.observation_attempts[1].attempt_id,
        ObservationAttemptId::parse("attempt:2").expect("valid attempt id")
    );
    assert!(first.curated_label.is_none());
    assert!(second.curated_label.is_none());
    assert!(first.current_label.is_none());
    assert!(second.current_label.is_none());
    assert!(first.promotion_id.is_none());
    assert!(second.promotion_id.is_none());
    assert!(first.publication_id.is_none());
    assert!(second.publication_id.is_none());
    assert!(!format!("{second:?}").contains("SYNTHETIC-IMMUTABLE-DROP-D1"));
}
