use std::collections::HashMap;

use crate::domain::{CommitId, InputDigest, PromotionAttemptState, PromotionOpId, PromotionRecord};
use crate::ports::PromotionStorePort;

#[derive(Debug, Default)]
pub struct InMemoryPromotionStore {
    records: HashMap<String, PromotionRecord>,
    commits: HashMap<String, InputDigest>,
    next_seq: u64,
}

impl PromotionStorePort for InMemoryPromotionStore {
    fn get(&self, op_id: &PromotionOpId) -> Option<PromotionRecord> {
        self.records.get(op_id.as_str()).cloned()
    }

    fn put(&mut self, record: PromotionRecord) {
        if let (Some(commit_id), Some(digest)) = (&record.commit_id, &record.commit_digest) {
            self.commits
                .insert(commit_id.as_str().to_owned(), digest.clone());
        }
        // If cancelled or incomplete, ensure no curated commit remains for this op.
        if record.state != PromotionAttemptState::Committed {
            if let Some(prev) = self.records.get(record.op_id.as_str()) {
                if let Some(old_commit) = &prev.commit_id {
                    // Only remove if this op owned it and is no longer committed.
                    if prev.state == PromotionAttemptState::Committed {
                        self.commits.remove(old_commit.as_str());
                    }
                }
            }
        }
        self.records
            .insert(record.op_id.as_str().to_owned(), record);
    }

    fn next_commit_id(&mut self) -> CommitId {
        self.next_seq += 1;
        CommitId::parse(&format!("commit:{}", self.next_seq)).expect("static commit id")
    }

    fn committed_count(&self) -> usize {
        self.records
            .values()
            .filter(|r| r.state == PromotionAttemptState::Committed)
            .count()
    }

    fn has_curated_commit(&self, commit_id: &CommitId) -> bool {
        self.commits.contains_key(commit_id.as_str())
    }

    fn has_curated_effect_for(&self, op_id: &PromotionOpId) -> bool {
        self.records
            .get(op_id.as_str())
            .map(|r| r.state == PromotionAttemptState::Committed && r.commit_id.is_some())
            .unwrap_or(false)
    }

    fn commit_digest_for(&self, commit_id: &CommitId) -> Option<InputDigest> {
        self.commits.get(commit_id.as_str()).cloned()
    }
}
