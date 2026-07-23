use std::collections::HashMap;
use std::sync::atomic::{AtomicUsize, Ordering};

use crate::domain::{DomainSnapshotId, PublicationSnapshotId, WorkUnitId};
use crate::ports::{DomainEvidencePort, HostileLegalSideChannel};

#[derive(Debug, Clone)]
pub struct SnapshotPair {
    pub domain: DomainSnapshotId,
    pub publication: PublicationSnapshotId,
}

/// Honest fixed snapshots for a work unit. Domain/publication ids never change
/// because of processing transitions.
#[derive(Debug, Default)]
pub struct FixedDomainEvidence {
    snapshots: HashMap<String, SnapshotPair>,
}

impl FixedDomainEvidence {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn with_unit(
        work_unit: WorkUnitId,
        domain: DomainSnapshotId,
        publication: PublicationSnapshotId,
    ) -> Self {
        let mut snapshots = HashMap::new();
        snapshots.insert(
            work_unit.as_str().to_owned(),
            SnapshotPair {
                domain,
                publication,
            },
        );
        Self { snapshots }
    }
}

impl DomainEvidencePort for FixedDomainEvidence {
    fn domain_snapshot(&self, work_unit: &WorkUnitId) -> DomainSnapshotId {
        self.snapshots
            .get(work_unit.as_str())
            .map(|s| s.domain.clone())
            .unwrap_or_else(|| {
                DomainSnapshotId::parse("domain:missing").expect("static id")
            })
    }

    fn publication_snapshot(&self, work_unit: &WorkUnitId) -> PublicationSnapshotId {
        self.snapshots
            .get(work_unit.as_str())
            .map(|s| s.publication.clone())
            .unwrap_or_else(|| {
                PublicationSnapshotId::parse("publication:missing").expect("static id")
            })
    }
}

/// Hostile evidence that pretends domain/publication ids change after every read
/// and claims legal mutations. Application must freeze initial ids and ignore claims.
#[derive(Debug)]
pub struct HostileMutatingEvidence {
    work_unit: String,
    base_domain: DomainSnapshotId,
    base_publication: PublicationSnapshotId,
    read_count: AtomicUsize,
    claimed_mutations: AtomicUsize,
}

impl HostileMutatingEvidence {
    pub fn new(
        work_unit: WorkUnitId,
        domain: DomainSnapshotId,
        publication: PublicationSnapshotId,
    ) -> Self {
        Self {
            work_unit: work_unit.as_str().to_owned(),
            base_domain: domain,
            base_publication: publication,
            read_count: AtomicUsize::new(0),
            claimed_mutations: AtomicUsize::new(0),
        }
    }

    pub fn claim_mutation(&self) {
        self.claimed_mutations.fetch_add(1, Ordering::SeqCst);
    }
}

impl DomainEvidencePort for HostileMutatingEvidence {
    fn domain_snapshot(&self, work_unit: &WorkUnitId) -> DomainSnapshotId {
        if work_unit.as_str() != self.work_unit {
            return DomainSnapshotId::parse("domain:other").expect("static id");
        }
        let n = self.read_count.fetch_add(1, Ordering::SeqCst);
        // After first read, hostile adapter invents a new id string.
        if n == 0 {
            self.base_domain.clone()
        } else {
            DomainSnapshotId::parse(&format!("{}:mutated:{}", self.base_domain.as_str(), n))
                .expect("static id")
        }
    }

    fn publication_snapshot(&self, work_unit: &WorkUnitId) -> PublicationSnapshotId {
        if work_unit.as_str() != self.work_unit {
            return PublicationSnapshotId::parse("publication:other").expect("static id");
        }
        // Keep publication "stable" relative to domain hostility so tests can
        // distinguish frozen application ids from adapter mutation attempts.
        self.base_publication.clone()
    }
}

impl HostileLegalSideChannel for HostileMutatingEvidence {
    fn claimed_legal_mutations(&self) -> usize {
        self.claimed_mutations.load(Ordering::SeqCst)
    }
}
