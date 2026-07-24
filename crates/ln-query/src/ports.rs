use crate::domain::EvidenceId;

pub trait QueryStatePort: Send + Sync {
    fn has_evidence(&self, id: &EvidenceId) -> bool;
    fn evidence_ids(&self) -> Vec<EvidenceId>;
}
