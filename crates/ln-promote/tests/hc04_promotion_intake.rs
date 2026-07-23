use ln_promote::{
    adapters::InMemoryPromotionStore,
    application::CommitCuratedPromotion,
    domain::{AcceptedSetId, InputDigest, PromotionOpId, PromotionOutcome},
};

fn ids() -> (PromotionOpId, AcceptedSetId, InputDigest) {
    (
        PromotionOpId::parse("P1").expect("op"),
        AcceptedSetId::parse("I1").expect("set"),
        InputDigest::parse("D1").expect("digest"),
    )
}

#[test]
fn cancel_mid_attempt_leaves_no_curated_effect() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();

    let begun = use_case.begin(op.clone(), set.clone(), digest.clone());
    assert_eq!(begun.outcome, PromotionOutcome::Incomplete);
    assert!(begun.commit_id.is_none());
    assert!(!begun.has_publication_authority());

    let cancelled = use_case.cancel(op.clone());
    assert_eq!(cancelled.outcome, PromotionOutcome::Cancelled);
    assert!(cancelled.commit_id.is_none());
    assert!(cancelled.commit_digest.is_none());
    assert!(!cancelled.has_publication_authority());
    assert_eq!(use_case.committed_count(), 0);
    assert!(!use_case.has_curated_effect_for(&op));
}

#[test]
fn identical_retry_after_cancel_yields_one_commit() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();

    let _ = use_case.begin(op.clone(), set.clone(), digest.clone());
    let _ = use_case.cancel(op.clone());

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    assert!(first.commit_id.is_some());
    assert_eq!(first.commit_digest.as_ref().map(|d| d.as_str()), Some("D1"));
    assert!(!first.has_publication_authority());
    assert_eq!(use_case.committed_count(), 1);

    let retry = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(retry.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(retry.commit_id, first.commit_id);
    assert_eq!(retry.commit_digest, first.commit_digest);
    assert!(!retry.has_publication_authority());
    assert_eq!(use_case.committed_count(), 1);
}

#[test]
fn identical_commit_without_prior_cancel_is_idempotent() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    let second = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(second.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(second.commit_id, first.commit_id);
    assert_eq!(use_case.committed_count(), 1);
}

#[test]
fn mismatched_digest_reuse_is_rejected() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();
    let other = InputDigest::parse("D2").expect("digest");

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    let first_id = first.commit_id.clone();

    let mismatch = use_case.commit(op.clone(), set.clone(), other);
    assert_eq!(mismatch.outcome, PromotionOutcome::RejectedMismatch);
    assert!(mismatch.commit_id.is_none());
    assert!(!mismatch.has_publication_authority());
    assert_eq!(use_case.committed_count(), 1);
    assert_eq!(
        use_case
            .commit(op.clone(), set, digest)
            .commit_id,
        first_id
    );
}

#[test]
fn mismatched_set_identity_reuse_is_rejected() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();
    let other_set = AcceptedSetId::parse("I2").expect("set");

    let _ = use_case.commit(op.clone(), set, digest.clone());
    let mismatch = use_case.commit(op, other_set, digest);
    assert_eq!(mismatch.outcome, PromotionOutcome::RejectedMismatch);
    assert_eq!(use_case.committed_count(), 1);
}

#[test]
fn success_never_grants_publication_authority() {
    let store = InMemoryPromotionStore::default();
    let mut use_case = CommitCuratedPromotion::new(store);
    let (op, set, digest) = ids();

    let result = use_case.commit(op, set, digest);
    assert_eq!(result.outcome, PromotionOutcome::Committed);
    assert!(!result.has_publication_authority());
    assert!(result.publication_authority.is_none());
}
