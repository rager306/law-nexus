use crate::domain::{CandidateId, CandidateRecord};

pub trait CandidateStorePort {
    fn get(&self, candidate_id: &CandidateId) -> Option<CandidateRecord>;
    fn put(&mut self, record: CandidateRecord);
}
