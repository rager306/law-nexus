use std::collections::HashMap;

use crate::domain::{CandidateId, CandidateRecord};
use crate::ports::CandidateStorePort;

#[derive(Debug, Default)]
pub struct InMemoryCandidateStore {
    items: HashMap<String, CandidateRecord>,
}

impl CandidateStorePort for InMemoryCandidateStore {
    fn get(&self, candidate_id: &CandidateId) -> Option<CandidateRecord> {
        self.items.get(candidate_id.as_str()).cloned()
    }

    fn put(&mut self, record: CandidateRecord) {
        self.items
            .insert(record.candidate_id.as_str().to_owned(), record);
    }
}

/// Hostile store that tries to rewrite the original candidate type on put.
#[derive(Debug, Default)]
pub struct InPlaceMutatingHostileStore {
    items: HashMap<String, CandidateRecord>,
}

impl CandidateStorePort for InPlaceMutatingHostileStore {
    fn get(&self, candidate_id: &CandidateId) -> Option<CandidateRecord> {
        self.items.get(candidate_id.as_str()).cloned()
    }

    fn put(&mut self, mut record: CandidateRecord) {
        // Hostile: force verified-assertion onto whatever is written.
        record.lifecycle_type = crate::domain::LifecycleType::VerifiedAssertion;
        self.items
            .insert(record.candidate_id.as_str().to_owned(), record);
    }
}
