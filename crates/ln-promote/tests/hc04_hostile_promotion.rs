use ln_promote::{
    adapters::InMemoryPromotionStore,
    application::CommitCuratedPromotion,
    domain::{
        AcceptedSetId, CommitId, InputDigest, PromotionAttemptState, PromotionOpId,
        PromotionOutcome, PromotionRecord,
    },
    ports::PromotionStorePort,
};

/// Hostile store that tries to mint a second curated commit on every put and
/// reports inflated committed cardinality.
#[derive(Default)]
struct DoubleCommitHostileStore {
    records: std::collections::HashMap<String, PromotionRecord>,
    fake_commits: usize,
    next_seq: u64,
}

impl PromotionStorePort for DoubleCommitHostileStore {
    fn get(&self, op_id: &PromotionOpId) -> Option<PromotionRecord> {
        self.records.get(op_id.as_str()).cloned()
    }

    fn put(&mut self, mut record: PromotionRecord) {
        // Hostile: force every write into a committed record with a new id.
        self.next_seq += 1;
        let hostile_id = CommitId::parse(&format!("hostile:{}", self.next_seq)).expect("static id");
        record.state = PromotionAttemptState::Committed;
        record.commit_id = Some(hostile_id);
        record.commit_digest = Some(record.input_digest.clone());
        self.fake_commits += 1;
        self.records
            .insert(record.op_id.as_str().to_owned(), record);
    }

    fn next_commit_id(&mut self) -> CommitId {
        self.next_seq += 1;
        CommitId::parse(&format!("hostile:{}", self.next_seq)).expect("static id")
    }

    fn committed_count(&self) -> usize {
        // Hostile: claim many commits exist.
        self.fake_commits.max(99)
    }

    fn has_curated_commit(&self, _commit_id: &CommitId) -> bool {
        true
    }

    fn has_curated_effect_for(&self, _op_id: &PromotionOpId) -> bool {
        true
    }

    fn commit_digest_for(&self, _commit_id: &CommitId) -> Option<InputDigest> {
        InputDigest::parse("HOSTILE-MUTATED").ok()
    }
}

/// Hostile store that mutates the first commit digest on read-back.
#[derive(Default)]
struct MutatingDigestHostileStore {
    inner: InMemoryPromotionStore,
}

impl PromotionStorePort for MutatingDigestHostileStore {
    fn get(&self, op_id: &PromotionOpId) -> Option<PromotionRecord> {
        self.inner.get(op_id).map(|mut record| {
            if record.state == PromotionAttemptState::Committed {
                record.commit_digest = InputDigest::parse("MUTATED-DIGEST").ok();
            }
            record
        })
    }

    fn put(&mut self, record: PromotionRecord) {
        self.inner.put(record);
    }

    fn next_commit_id(&mut self) -> CommitId {
        self.inner.next_commit_id()
    }

    fn committed_count(&self) -> usize {
        self.inner.committed_count()
    }

    fn has_curated_commit(&self, commit_id: &CommitId) -> bool {
        self.inner.has_curated_commit(commit_id)
    }

    fn has_curated_effect_for(&self, op_id: &PromotionOpId) -> bool {
        self.inner.has_curated_effect_for(op_id)
    }

    fn commit_digest_for(&self, _commit_id: &CommitId) -> Option<InputDigest> {
        InputDigest::parse("MUTATED-DIGEST").ok()
    }
}

fn ids() -> (PromotionOpId, AcceptedSetId, InputDigest) {
    (
        PromotionOpId::parse("P1").expect("op"),
        AcceptedSetId::parse("I1").expect("set"),
        InputDigest::parse("D1").expect("digest"),
    )
}

#[test]
fn hostile_double_commit_store_cannot_create_second_effect() {
    let mut use_case = CommitCuratedPromotion::new(DoubleCommitHostileStore::default());
    let (op, set, digest) = ids();

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    let first_id = first.commit_id.clone();
    let first_digest = first.commit_digest.clone();

    let retry = use_case.commit(op.clone(), set, digest);
    assert_eq!(retry.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(retry.commit_id, first_id);
    assert_eq!(retry.commit_digest, first_digest);
    // Application-owned cardinality, not hostile store count.
    assert_eq!(use_case.committed_count(), 1);
    assert!(use_case.has_curated_effect_for(&op));
    assert!(!retry.has_publication_authority());
}

#[test]
fn hostile_mutating_digest_store_cannot_change_first_result() {
    let mut use_case = CommitCuratedPromotion::new(MutatingDigestHostileStore::default());
    let (op, set, digest) = ids();

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    assert_eq!(first.commit_digest.as_ref().map(|d| d.as_str()), Some("D1"));

    let retry = use_case.commit(op, set, digest);
    assert_eq!(retry.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(retry.commit_id, first.commit_id);
    assert_eq!(retry.commit_digest.as_ref().map(|d| d.as_str()), Some("D1"));
    assert_eq!(use_case.committed_count(), 1);
}

#[test]
fn cancel_then_retry_against_hostile_store_still_one_commit() {
    let mut use_case = CommitCuratedPromotion::new(DoubleCommitHostileStore::default());
    let (op, set, digest) = ids();

    let _ = use_case.begin(op.clone(), set.clone(), digest.clone());
    let cancelled = use_case.cancel(op.clone());
    assert_eq!(cancelled.outcome, PromotionOutcome::Cancelled);
    assert!(cancelled.commit_id.is_none());
    assert_eq!(use_case.committed_count(), 0);
    assert!(!use_case.has_curated_effect_for(&op));

    let first = use_case.commit(op.clone(), set.clone(), digest.clone());
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    let retry = use_case.commit(op, set, digest);
    assert_eq!(retry.outcome, PromotionOutcome::AlreadyCommitted);
    assert_eq!(retry.commit_id, first.commit_id);
    assert_eq!(use_case.committed_count(), 1);
}

#[test]
fn mismatch_still_rejected_with_hostile_store() {
    let mut use_case = CommitCuratedPromotion::new(DoubleCommitHostileStore::default());
    let (op, set, digest) = ids();
    let other = InputDigest::parse("D2").expect("digest");

    let first = use_case.commit(op.clone(), set.clone(), digest);
    assert_eq!(first.outcome, PromotionOutcome::Committed);
    let mismatch = use_case.commit(op, set, other);
    assert_eq!(mismatch.outcome, PromotionOutcome::RejectedMismatch);
    assert!(mismatch.commit_id.is_none());
    assert_eq!(use_case.committed_count(), 1);
}
