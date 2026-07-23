use ln_dispose::{
    adapters::{InMemoryDispositionStore, InMemoryPromotionGate},
    application::DisposeReview,
    domain::{
        DispositionReason, DispositionState, InventoryItemId, PromotionAttemptId, PromotionOutcome,
        PromotionRequestId, ReviewEvidenceId,
    },
};

#[test]
fn promotion_attempt_from_missing_item_is_rejected() {
    let mut use_case = DisposeReview::new(
        InMemoryDispositionStore::default(),
        InMemoryPromotionGate::default(),
    );
    let item = InventoryItemId::parse("I-MISSING").expect("valid");
    let result = use_case.attempt_promotion(
        item,
        PromotionRequestId::parse("P1").expect("valid"),
        PromotionAttemptId::parse("A1").expect("valid"),
    );
    assert_eq!(result.outcome, PromotionOutcome::Rejected);
    assert_eq!(result.reason, DispositionReason::Incomplete);
    assert!(result.commit_id.is_none());
}

#[test]
fn accepted_state_can_produce_promotion_commit() {
    let store = InMemoryDispositionStore::default();
    let gate = InMemoryPromotionGate::default();
    let mut use_case = DisposeReview::new(store, gate);

    let item = InventoryItemId::parse("I1").expect("valid");
    use_case.set_pending(
        item.clone(),
        vec![ReviewEvidenceId::parse("E1").expect("valid")],
    );

    // Simulate accepted disposition by directly setting it
    use_case.store_set_accepted(item.clone());

    let result = use_case.attempt_promotion(
        item,
        PromotionRequestId::parse("P1").expect("valid"),
        PromotionAttemptId::parse("A1").expect("valid"),
    );
    assert_eq!(result.outcome, PromotionOutcome::Committed);
    assert!(result.commit_id.is_some());
}

#[test]
fn pending_stays_pending_after_rejected_promotion() {
    let store = InMemoryDispositionStore::default();
    let gate = InMemoryPromotionGate::default();
    let mut use_case = DisposeReview::new(store, gate);

    let item = InventoryItemId::parse("I1").expect("valid");
    use_case.set_pending(
        item.clone(),
        vec![ReviewEvidenceId::parse("E1").expect("valid")],
    );

    let _ = use_case.attempt_promotion(
        item.clone(),
        PromotionRequestId::parse("P1").expect("valid"),
        PromotionAttemptId::parse("A1").expect("valid"),
    );

    let d = use_case.disposition(&item);
    assert_eq!(d.state, DispositionState::Pending);
    assert!(d.accepted_commit_id.is_none());
}
