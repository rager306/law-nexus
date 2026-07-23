use ln_dispose::{
    adapters::{InMemoryDispositionStore, InMemoryPromotionGate},
    application::DisposeReview,
    domain::{
        DispositionReason, DispositionState, InventoryItemId, PromotionAttemptId, PromotionOutcome,
        PromotionRequestId, ReviewEvidenceId,
    },
};

#[test]
fn pending_disposition_rejects_promotion_without_curated_commit() {
    let store = InMemoryDispositionStore::default();
    let gate = InMemoryPromotionGate::default();
    let mut use_case = DisposeReview::new(store, gate);

    let item = InventoryItemId::parse("I1").expect("valid item id");
    let evidence = vec![ReviewEvidenceId::parse("E1").expect("valid evidence id")];

    let disposition = use_case.set_pending(item.clone(), evidence.clone());

    assert_eq!(disposition.state, DispositionState::Pending);
    assert!(disposition.accepted_commit_id.is_none());
    assert!(disposition.promotion_identity.is_none());

    let promotion = use_case.attempt_promotion(
        item.clone(),
        PromotionRequestId::parse("P1").expect("valid request id"),
        PromotionAttemptId::parse("A1").expect("valid attempt id"),
    );

    assert_eq!(promotion.outcome, PromotionOutcome::Rejected);
    assert_eq!(promotion.reason, DispositionReason::Incomplete);
    assert!(promotion.commit_id.is_none());
    assert!(promotion.promotion_identity.is_none());

    let final_disposition = use_case.disposition(&item);
    assert_eq!(final_disposition.state, DispositionState::Pending);
    assert!(final_disposition.accepted_commit_id.is_none());
}

#[test]
fn quarantined_disposition_also_rejects_promotion() {
    let store = InMemoryDispositionStore::default();
    let gate = InMemoryPromotionGate::default();
    let mut use_case = DisposeReview::new(store, gate);

    let item = InventoryItemId::parse("I1").expect("valid item id");
    let evidence = vec![ReviewEvidenceId::parse("E1").expect("valid evidence id")];

    let disposition = use_case.set_quarantined(item.clone(), evidence);

    assert_eq!(disposition.state, DispositionState::Quarantined);

    let promotion = use_case.attempt_promotion(
        item.clone(),
        PromotionRequestId::parse("P1").expect("valid request id"),
        PromotionAttemptId::parse("A2").expect("valid attempt id"),
    );

    assert_eq!(promotion.outcome, PromotionOutcome::Rejected);
    assert_eq!(promotion.reason, DispositionReason::Conflict);
    assert!(promotion.commit_id.is_none());
    assert!(promotion.promotion_identity.is_none());

    let final_disposition = use_case.disposition(&item);
    assert_eq!(final_disposition.state, DispositionState::Quarantined);
    assert!(final_disposition.accepted_commit_id.is_none());
}
