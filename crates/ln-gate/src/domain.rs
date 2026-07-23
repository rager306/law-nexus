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

id_type!(CandidateId, "candidate id");
id_type!(EvidenceRef, "evidence ref");
id_type!(GateVersion, "gate version");
id_type!(InputChainDigest, "input chain digest");

pub const C10_GATE_VERSION: &str = "c10:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LifecycleType {
    ExtractedCandidate,
    VerifiedAssertion,
}

impl LifecycleType {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ExtractedCandidate => "extracted-candidate",
            Self::VerifiedAssertion => "verified-assertion",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateOutcome {
    InsufficientEvidence,
    InvalidTransition,
    AcceptedNewOutcome,
}

impl GateOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::InsufficientEvidence => "insufficient-evidence",
            Self::InvalidTransition => "invalid-transition",
            Self::AcceptedNewOutcome => "accepted-new-outcome",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GateReason {
    ConfidenceOnly,
    InPlaceMutation,
    MissingEvidenceChain,
    EvidenceChainSatisfied,
}

impl GateReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ConfidenceOnly => "confidence-only",
            Self::InPlaceMutation => "in-place-mutation",
            Self::MissingEvidenceChain => "missing-evidence-chain",
            Self::EvidenceChainSatisfied => "evidence-chain-satisfied",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CandidateRecord {
    pub candidate_id: CandidateId,
    pub lifecycle_type: LifecycleType,
    pub evidence_refs: Vec<EvidenceRef>,
    pub predecessor: Option<CandidateId>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateRequest {
    pub candidate_id: CandidateId,
    pub requested_type: LifecycleType,
    pub confidence: u8,
    pub evidence_refs: Vec<EvidenceRef>,
    /// When true, caller asks to mutate the same identity in place.
    pub in_place: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GateResult {
    pub gate_version: GateVersion,
    pub outcome: GateOutcome,
    pub reason: GateReason,
    pub original_id: CandidateId,
    pub original_type: LifecycleType,
    pub resulting_id: CandidateId,
    pub resulting_type: LifecycleType,
    pub predecessor: Option<CandidateId>,
    pub input_chain_digest: InputChainDigest,
    pub confidence_used_as_authority: bool,
}

pub fn digest_chain(candidate_id: &CandidateId, evidence_refs: &[EvidenceRef]) -> InputChainDigest {
    let mut material = candidate_id.as_str().to_owned();
    for item in evidence_refs {
        material.push('|');
        material.push_str(item.as_str());
    }
    // FNV-1a diagnostic digest only; not cryptographic authority.
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in material.as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    InputChainDigest::parse(&format!("fnv1a64:{hash:016x}")).expect("static digest")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_candidate_id() {
        assert!(CandidateId::parse("").is_err());
    }

    #[test]
    fn digest_is_deterministic() {
        let id = CandidateId::parse("C1").unwrap();
        let ev = vec![EvidenceRef::parse("E1").unwrap()];
        assert_eq!(digest_chain(&id, &ev), digest_chain(&id, &ev));
    }
}
