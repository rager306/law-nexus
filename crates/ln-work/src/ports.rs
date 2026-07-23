use crate::domain::{DomainSnapshotId, PublicationSnapshotId, WorkUnitId};

/// Read-only view of domain and publication identity for a work unit.
/// Adapters must not become owners of legal truth; application freezes ids.
pub trait DomainEvidencePort {
    fn domain_snapshot(&self, work_unit: &WorkUnitId) -> DomainSnapshotId;
    fn publication_snapshot(&self, work_unit: &WorkUnitId) -> PublicationSnapshotId;
}

/// Optional side-channel that hostile adapters may use to claim legal mutation.
/// Application policy never consults this for authority and never writes legal state.
pub trait HostileLegalSideChannel {
    fn claimed_legal_mutations(&self) -> usize;
}
