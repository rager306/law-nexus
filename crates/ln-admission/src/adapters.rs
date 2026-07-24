use crate::domain::{BoundId, BoundObservation, BoundObservationKind};
use crate::ports::BoundObservationPort;

#[derive(Debug, Clone)]
pub struct HonestBoundObservation {
    pub observation: BoundObservation,
}

impl BoundObservationPort for HonestBoundObservation {
    fn observe(&self) -> BoundObservation {
        self.observation.clone()
    }
}

impl HonestBoundObservation {
    pub fn unknown() -> Self {
        Self {
            observation: BoundObservation {
                kind: BoundObservationKind::Unknown,
                bound_id: None,
                vendor_throughput_claim: None,
                vendor_latency_claim: None,
                vendor_storage_claim: None,
            },
        }
    }

    pub fn saturated() -> Self {
        Self {
            observation: BoundObservation {
                kind: BoundObservationKind::Saturated,
                bound_id: None,
                vendor_throughput_claim: None,
                vendor_latency_claim: None,
                vendor_storage_claim: None,
            },
        }
    }

    pub fn measured(bound_id: BoundId) -> Self {
        Self {
            observation: BoundObservation {
                kind: BoundObservationKind::Measured,
                bound_id: Some(bound_id),
                vendor_throughput_claim: None,
                vendor_latency_claim: None,
                vendor_storage_claim: None,
            },
        }
    }
}

/// Hostile adapter that invents vendor throughput/latency/storage numbers and
/// may claim measured while only offering vendor provenance.
#[derive(Debug, Clone)]
pub struct HostileVendorCapacity {
    pub pretend_measured: bool,
    pub bound_id: Option<BoundId>,
}

impl BoundObservationPort for HostileVendorCapacity {
    fn observe(&self) -> BoundObservation {
        BoundObservation {
            kind: if self.pretend_measured {
                BoundObservationKind::Measured
            } else {
                BoundObservationKind::Unknown
            },
            bound_id: self.bound_id.clone(),
            vendor_throughput_claim: Some(100_000),
            vendor_latency_claim: Some(12),
            vendor_storage_claim: Some(1_000_000_000),
        }
    }
}
