use crate::domain::{CommitId, InputDigest, PromotionOpId, PromotionRecord};

pub trait PromotionStorePort {
    fn get(&self, op_id: &PromotionOpId) -> Option<PromotionRecord>;
    fn put(&mut self, record: PromotionRecord);
    fn next_commit_id(&mut self) -> CommitId;
    /// Count of committed curated effects. Used to prove cancel left no effect
    /// and retries did not create a second commit.
    fn committed_count(&self) -> usize;
    /// Returns true if a commit with the given identity is visible as curated.
    fn has_curated_commit(&self, commit_id: &CommitId) -> bool;
    /// Returns true if any curated effect exists for the operation.
    fn has_curated_effect_for(&self, op_id: &PromotionOpId) -> bool;
    /// Optional: expose committed digest for identity checks.
    fn commit_digest_for(&self, commit_id: &CommitId) -> Option<InputDigest>;
}
