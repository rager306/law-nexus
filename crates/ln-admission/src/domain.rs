use std::error::Error;
use std::fmt;

const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}

impl fmt::Display for IdError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid {}: {}", self.kind, self.reason)
    }
}

impl Error for IdError {}

fn parse_id(kind: &'static str, value: &str, max_len: usize) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > max_len {
        return Err(IdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.'))
    {
        return Err(IdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! id_type {
    ($name:ident, $kind:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);
        impl $name {
            pub fn parse(value: &str) -> Result<Self, IdError> {
                parse_id($kind, value, MAX_ID_LEN).map(Self)
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(RequestId, "request id");
id_type!(BoundId, "bound id");
id_type!(WorkClassId, "work class id");

/// Admission policy version for HC-13 traces.
pub const ADMISSION_POLICY_VERSION: &str = "hc13:decide-admission:v1";

/// Default retry amplification threshold for synthetic policy (not product capacity).
pub const RETRY_AMPLIFICATION_THRESHOLD: u32 = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionDecision {
    Admitted,
    Paused,
    Rejected,
}

impl AdmissionDecision {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Admitted => "admitted",
            Self::Paused => "paused",
            Self::Rejected => "rejected",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AdmissionReason {
    MeasuredBound,
    BoundUnknown,
    Saturated,
    RetryAmplification,
    VendorCapacityRejected,
    CompletenessClaimRejected,
    LegalDelayClaimRejected,
}

impl AdmissionReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::MeasuredBound => "measured-bound",
            Self::BoundUnknown => "bound-unknown",
            Self::Saturated => "saturated",
            Self::RetryAmplification => "retry-amplification",
            Self::VendorCapacityRejected => "vendor-capacity-rejected",
            Self::CompletenessClaimRejected => "completeness-claim-rejected",
            Self::LegalDelayClaimRejected => "legal-delay-claim-rejected",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CapacityState {
    Unknown,
    /// Local measured bound identity present; still not a product E1-E3 claim.
    BoundedLocal,
}

impl CapacityState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Unknown => "unknown",
            Self::BoundedLocal => "bounded-local",
        }
    }

    pub fn is_unknown(self) -> bool {
        matches!(self, Self::Unknown)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BoundObservationKind {
    Unknown,
    Saturated,
    Measured,
}

/// Forbidden meanings that must never be inferred from admission.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ForbiddenInference {
    None,
    LegalDelay,
    Completeness,
    VendorThroughput,
    VendorLatency,
    VendorStoragePrecision,
}

impl ForbiddenInference {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::LegalDelay => "legal-delay",
            Self::Completeness => "completeness",
            Self::VendorThroughput => "vendor-throughput",
            Self::VendorLatency => "vendor-latency",
            Self::VendorStoragePrecision => "vendor-storage-precision",
        }
    }

    pub fn is_forbidden(self) -> bool {
        !matches!(self, Self::None)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionRequest {
    pub request_id: RequestId,
    pub work_class: WorkClassId,
    pub retry_count: u32,
    pub forbidden_inference: ForbiddenInference,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BoundObservation {
    pub kind: BoundObservationKind,
    pub bound_id: Option<BoundId>,
    /// Adapter may report vendor numbers; application must ignore as capacity.
    pub vendor_throughput_claim: Option<u64>,
    pub vendor_latency_claim: Option<u64>,
    pub vendor_storage_claim: Option<u64>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionTrace {
    pub policy_version: String,
    pub request_id: RequestId,
    pub decision: AdmissionDecision,
    pub reason: AdmissionReason,
    pub capacity: CapacityState,
    pub bound_id: Option<BoundId>,
    pub retry_count: u32,
    pub forbidden_inference: ForbiddenInference,
    pub forbidden_inference_applied: bool,
    pub vendor_number_used: bool,
    pub legal_delay_inferred: bool,
    pub completeness_inferred: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmissionResult {
    pub decision: AdmissionDecision,
    pub reason: AdmissionReason,
    pub capacity: CapacityState,
    pub bound_id: Option<BoundId>,
    pub vendor_number_used: bool,
    pub legal_delay_inferred: bool,
    pub completeness_inferred: bool,
    pub trace: AdmissionTrace,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_request_id() {
        assert!(RequestId::parse("").is_err());
    }

    #[test]
    fn capacity_unknown_by_default_marker() {
        assert!(CapacityState::Unknown.is_unknown());
        assert!(!CapacityState::BoundedLocal.is_unknown());
    }
}
