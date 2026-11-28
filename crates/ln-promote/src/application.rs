use std::collections::HashMap;

use ln_fsm::DeterministicFsm;

use crate::domain::{
    AcceptedSetId, CommitId, InputDigest, PromotionAttemptEvent, PromotionAttemptFsm,
    PromotionAttemptState, PromotionOpId, PromotionOutcome, PromotionRecord, PromotionResult,
    PromotionTransitionRefusal,
};
use crate::ports::PromotionStorePort;

/// Application-owned promotion policy. Store adapters may be hostile or lossy;
/// commit cardinality and identity stability are enforced here.
pub struct CommitCuratedPromotion<S> {
    store: S,
    /// Authoritative in-process ledger for committed operations.
    committed: HashMap<String, PromotionRecord>,
    /// Authoritative in-process ledger for non-committed attempts (in progress / cancelled).
    open: HashMap<String, PromotionRecord>,
    next_seq: u64,
}

impl<S> CommitCuratedPromotion<S>
where
    S: PromotionStorePort,
{
    pub fn new(store: S) -> Self {
        Self {
            store,
            committed: HashMap::new(),
            open: HashMap::new(),
            next_seq: 0,
        }
    }

    pub fn begin(
        &mut self,
        op_id: PromotionOpId,
        accepted_set_id: AcceptedSetId,
        input_digest: InputDigest,
    ) -> PromotionResult {
        if let Some(existing) = self.lookup(&op_id) {
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
        self.open.insert(op_id.as_str().to_owned(), record.clone());
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
        if let Some(existing) = self.committed.get(op_id.as_str()).cloned() {
            return PromotionResult {
                outcome: PromotionOutcome::AlreadyCommitted,
                op_id,
                commit_id: existing.commit_id,
                commit_digest: existing.commit_digest,
                publication_authority: None,
            };
        }

        match self.open.remove(op_id.as_str()) {
            None => PromotionResult {
                outcome: PromotionOutcome::Incomplete,
                op_id,
                commit_id: None,
                commit_digest: None,
                publication_authority: None,
            },
            Some(mut existing) => {
                // Match PromotionAttemptFsm exhaustively so only AlreadyCancelled is
                // idempotent and AlreadyCommitted fails closed without wiping state.
                match PromotionAttemptFsm.apply(existing.state, PromotionAttemptEvent::Cancel) {
                    Ok(receipt) => {
                        existing.state = receipt.next;
                        existing.commit_id = None;
                        existing.commit_digest = None;
                        existing.publication_authority = None;
                        let op = existing.op_id.clone();
                        self.open.insert(op.as_str().to_owned(), existing.clone());
                        self.store.put(existing);
                        PromotionResult {
                            outcome: PromotionOutcome::Cancelled,
                            op_id: op,
                            commit_id: None,
                            commit_digest: None,
                            publication_authority: None,
                        }
                    }
                    Err(rej) => match rej.reason {
                        PromotionTransitionRefusal::AlreadyCancelled => {
                            let op = existing.op_id.clone();
                            self.open.insert(op.as_str().to_owned(), existing);
                            PromotionResult {
                                outcome: PromotionOutcome::Cancelled,
                                op_id: op,
                                commit_id: None,
                                commit_digest: None,
                                publication_authority: None,
                            }
                        }
                        PromotionTransitionRefusal::AlreadyCommitted => {
                            let op = existing.op_id.clone();
                            let commit_id = existing.commit_id.clone();
                            let commit_digest = existing.commit_digest.clone();
                            self.committed.insert(op.as_str().to_owned(), existing);
                            PromotionResult {
                                outcome: PromotionOutcome::AlreadyCommitted,
                                op_id: op,
                                commit_id,
                                commit_digest,
                                publication_authority: None,
                            }
                        }
                    },
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
        let next_state = if let Some(existing) = self.lookup(&op_id) {
            if existing.accepted_set_id != accepted_set_id || existing.input_digest != input_digest
            {
                return PromotionResult {
                    outcome: PromotionOutcome::RejectedMismatch,
                    op_id,
                    commit_id: None,
                    commit_digest: None,
                    publication_authority: None,
                };
            }
            match PromotionAttemptFsm.apply(existing.state, PromotionAttemptEvent::Commit) {
                Ok(receipt) => receipt.next,
                Err(rej) => match rej.reason {
                    PromotionTransitionRefusal::AlreadyCommitted => {
                        return PromotionResult {
                            outcome: PromotionOutcome::AlreadyCommitted,
                            op_id: existing.op_id,
                            commit_id: existing.commit_id,
                            commit_digest: existing.commit_digest,
                            publication_authority: None,
                        };
                    }
                    PromotionTransitionRefusal::AlreadyCancelled => {
                        return PromotionResult {
                            outcome: PromotionOutcome::Cancelled,
                            op_id: existing.op_id,
                            commit_id: None,
                            commit_digest: None,
                            publication_authority: None,
                        };
                    }
                },
            }
        } else {
            PromotionAttemptFsm
                .apply(
                    PromotionAttemptState::InProgress,
                    PromotionAttemptEvent::Commit,
                )
                .expect("InProgress + Commit is always valid")
                .next
        };

        // Mint commit identity in the application, not the store.
        self.next_seq += 1;
        let commit_id =
            CommitId::parse(&format!("commit:{}", self.next_seq)).expect("static commit id");
        let record = PromotionRecord {
            op_id: op_id.clone(),
            accepted_set_id,
            input_digest: input_digest.clone(),
            state: next_state,
            commit_id: Some(commit_id.clone()),
            commit_digest: Some(input_digest.clone()),
            publication_authority: None,
        };
        self.open.remove(op_id.as_str());
        self.committed
            .insert(op_id.as_str().to_owned(), record.clone());
        // Best-effort persistence. Policy does not depend on store honesty.
        let _ = self.store.next_commit_id();
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
        self.committed.len()
    }

    pub fn has_curated_effect_for(&self, op_id: &PromotionOpId) -> bool {
        self.committed.contains_key(op_id.as_str())
    }

    fn lookup(&self, op_id: &PromotionOpId) -> Option<PromotionRecord> {
        self.committed
            .get(op_id.as_str())
            .or_else(|| self.open.get(op_id.as_str()))
            .cloned()
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
        PromotionResult {
            outcome: PromotionOutcome::Incomplete,
            op_id: existing.op_id,
            commit_id: None,
            commit_digest: None,
            publication_authority: None,
        }
    }
}
