use ln_inventory::{
    adapters::{DigestBackedItemIdentity, InMemoryVisibilityView},
    application::InventoryImmutableIntake,
    domain::{
        DropReference, InventoryDisposition, InventoryItemId, InventoryRequest, InventoryRequestId,
        InventoryVisibility, ObservationAttempt,
    },
    ports::{InventoryStorePort, ItemIdentityPort},
};

/// Hostile store that tries to destroy prior observation history.
#[derive(Default)]
struct OverwritingInventoryStore {
    last: Option<(String, ObservationAttempt)>,
}

impl InventoryStorePort for OverwritingInventoryStore {
    fn append_attempt(
        &mut self,
        item_id: &InventoryItemId,
        attempt: ObservationAttempt,
    ) -> Vec<ObservationAttempt> {
        self.last = Some((item_id.as_str().to_owned(), attempt.clone()));
        // Hostile behavior: pretend only the latest attempt exists.
        vec![attempt]
    }

    fn attempts_for(&self, item_id: &InventoryItemId) -> Vec<ObservationAttempt> {
        match &self.last {
            Some((id, attempt)) if id == item_id.as_str() => vec![attempt.clone()],
            _ => Vec::new(),
        }
    }
}

#[test]
fn hostile_overwrite_store_cannot_erase_prior_attempts() {
    let bytes = b"SYNTHETIC-IMMUTABLE-DROP-D1";
    let mut use_case =
        InventoryImmutableIntake::new(OverwritingInventoryStore::default(), InMemoryVisibilityView);

    let request = InventoryRequest::new(
        InventoryRequestId::parse("INV-H1").expect("valid"),
        DropReference::parse("D1").expect("valid"),
        bytes,
    );
    let first = use_case.inventory(request.clone());
    let second = use_case.inventory(request);

    assert_eq!(first.input_digest, second.input_digest);
    assert_eq!(second.observation_attempts.len(), 2);
    assert_eq!(
        second.observation_attempts[0].attempt_id.as_str(),
        "attempt:1"
    );
    assert_eq!(
        second.observation_attempts[1].attempt_id.as_str(),
        "attempt:2"
    );
    assert_eq!(second.visibility, InventoryVisibility::InventoryReview);
    assert_eq!(second.disposition, InventoryDisposition::Pending);
    assert!(second.curated_label.is_none());
    assert!(second.current_label.is_none());
    assert!(second.promotion_id.is_none());
    assert!(second.publication_id.is_none());
}

#[test]
fn same_drop_and_digest_keeps_one_logical_item_identity() {
    let bytes = b"SYNTHETIC-IMMUTABLE-DROP-D1";
    let identity = DigestBackedItemIdentity;
    let first = InventoryRequest::new(
        InventoryRequestId::parse("INV-A").expect("valid"),
        DropReference::parse("D1").expect("valid"),
        bytes,
    );
    let second = InventoryRequest::new(
        InventoryRequestId::parse("INV-B").expect("valid"),
        DropReference::parse("D1").expect("valid"),
        bytes,
    );
    assert_eq!(
        identity.resolve_item_id(&first),
        identity.resolve_item_id(&second)
    );
    assert_eq!(first.input_digest(), second.input_digest());
}

#[test]
fn public_result_cannot_carry_curated_current_or_authority_labels() {
    let bytes = b"SYNTHETIC-IMMUTABLE-DROP-D1";
    let mut use_case = InventoryImmutableIntake::new(
        ln_inventory::adapters::InMemoryInventoryStore::default(),
        InMemoryVisibilityView,
    );
    let result = use_case.inventory(InventoryRequest::new(
        InventoryRequestId::parse("INV-SAFE").expect("valid"),
        DropReference::parse("D1").expect("valid"),
        bytes,
    ));
    assert!(result.curated_label.is_none());
    assert!(result.current_label.is_none());
    assert!(result.promotion_id.is_none());
    assert!(result.publication_id.is_none());
    assert_eq!(result.visibility, InventoryVisibility::InventoryReview);
    assert_ne!(
        format!("{:?}", result.visibility),
        "Curated",
        "visibility vocabulary must not look curated"
    );
}
