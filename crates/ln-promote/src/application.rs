use crate::domain::{
    AcceptedSetId, InputDigest, PromotionAttemptState, PromotionOpId, PromotionOutcome,
    PromotionRecord, PromotionResult,
};
use crate::ports::PromotionStorePort;

pub struct CommitCuratedPromotion<S> {
    store: S,
}

impl<S> CommitCuratedPromotion<S>
where
    S: PromotionStorePort,
{
    pub fn new(store: S) -> Self {
        Self { store }
    }

    pub fn begin(
        &mut self,
        op_id: PromotionOpId,
        accepted_set_id: AcceptedSetId,
        input_digest: InputDigest,
    ) -> PromotionResult {
        if let Some(existing) = self.store.get(&op_id) {
            return self.handle_existing(existing, &accepted_set_id, &input_digest);
        }

        let record = PromotionRecord {
            op_id: op_id.clone(),
            accepted_set_id,
            input_digest,
            state: PromotionAttemptState::InProgress,
            commit_id: None,
            commit_digest: None,
            publication_authority: None,
        };
        self.store.put(record);
        PromotionResult {
            outcome: PromotionOutcome::Incomplete,
            op_id,
            commit_id: None,
            commit_digest: None,
            publication_authority: None,
        }
    }

    pub fn cancel(&mut self, op_id: PromotionOpId) -> PromotionResult {
        match self.store.get(&op_id) {
            None => PromotionResult {
                outcome: PromotionOutcome::Incomplete,
                op_id,
                commit_id: None,
                commit_digest: None,
                publication_authority: None,
            },
            Some(existing) if existing.state == PromotionAttemptState::Committed => {
                PromotionResult {
                    outcome: PromotionOutcome::AlreadyCommitted,
                    op_id,
                    commit_id: existing.commit_id,
                    commit_digest: existing.commit_digest,
                    publication_authority: None,
                }
            }
            Some(mut existing) => {
                existing.state = PromotionAttemptState::Cancelled;
                existing.commit_id = None;
                existing.commit_digest = None;
                existing.publication_authority = None;
                let op = existing.op_id.clone();
                self.store.put(existing);
                PromotionResult {
                    outcome: PromotionOutcome::Cancelled,
                    op_id: op,
                    commit_id: None,
                    commit_digest: None,
                    publication_authority: None,
                }
            }
        }
    }

    pub fn commit(
        &mut self,
        op_id: PromotionOpId,
        accepted_set_id: AcceptedSetId,
        input_digest: InputDigest,
    ) -> PromotionResult {
        if let Some(existing) = self.store.get(&op_id) {
            match existing.state {
                PromotionAttemptState::Committed => {
                    return self.handle_existing(existing, &accepted_set_id, &input_digest);
                }
                PromotionAttemptState::Cancelled | PromotionAttemptState::InProgress => {
                    // Fall through: cancelled may be retried with same identity;
                    // in-progress may complete. Mismatch still rejects.
                    if existing.accepted_set_id != accepted_set_id
                        || existing.input_digest != input_digest
                    {
                        return PromotionResult {
                            outcome: PromotionOutcome::RejectedMismatch,
                            op_id,
                            commit_id: None,
                            commit_digest: None,
                            publication_authority: None,
                        };
                    }
                }
            }
        }

        // Fresh or cancelled/in-progress matching identity → one commit.
        if let Some(existing) = self.store.get(&op_id) {
            if existing.state == PromotionAttemptState::Committed {
                return self.handle_existing(existing, &accepted_set_id, &input_digest);
            }
        }

        let commit_id = self.store.next_commit_id();
        let record = PromotionRecord {
            op_id: op_id.clone(),
            accepted_set_id,
            input_digest: input_digest.clone(),
            state: PromotionAttemptState::Committed,
            commit_id: Some(commit_id.clone()),
            commit_digest: Some(input_digest.clone()),
            publication_authority: None,
        };
        self.store.put(record);
        PromotionResult {
            outcome: PromotionOutcome::Committed,
            op_id,
            commit_id: Some(commit_id),
            commit_digest: Some(input_digest),
            publication_authority: None,
        }
    }

    pub fn committed_count(&self) -> usize {
        self.store.committed_count()
    }

    pub fn has_curated_effect_for(&self, op_id: &PromotionOpId) -> bool {
        self.store.has_curated_effect_for(op_id)
    }

    fn handle_existing(
        &self,
        existing: PromotionRecord,
        accepted_set_id: &AcceptedSetId,
        input_digest: &InputDigest,
    ) -> PromotionResult {
        if existing.accepted_set_id != *accepted_set_id || existing.input_digest != *input_digest {
            return PromotionResult {
                outcome: PromotionOutcome::RejectedMismatch,
                op_id: existing.op_id,
                commit_id: None,
                commit_digest: None,
                publication_authority: None,
            };
        }
        if existing.state == PromotionAttemptState::Committed {
            return PromotionResult {
                outcome: PromotionOutcome::AlreadyCommitted,
                op_id: existing.op_id,
                commit_id: existing.commit_id,
                commit_digest: existing.commit_digest,
                publication_authority: None,
            };
        }
        // Existing non-committed with matching identity: caller should use commit().
        PromotionResult {
            outcome: PromotionOutcome::Incomplete,
            op_id: existing.op_id,
            commit_id: None,
            commit_digest: None,
            publication_authority: None,
        }
    }
}
