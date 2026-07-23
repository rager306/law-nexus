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

id_type!(PayloadRef, "payload ref");
id_type!(FamilyFormat, "family format");
id_type!(CandidateId, "candidate id");
id_type!(AnchorId, "anchor id");
id_type!(DiagnosticId, "diagnostic id");

/// Categories a decoder may claim. Only structural is accepted by policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DecodeCategory {
    StructuralCandidate,
    /// Gate-owned; rejected by DecodeAndAnchor.
    VerifiedAssertion,
    /// Identity merge is C12-owned; rejected.
    MergedIdentity,
    /// Relation minting is C13-owned; rejected.
    UnregisteredRelation,
    /// Raw failure context / payload leak; rejected.
    RawFailureContext,
}

impl DecodeCategory {
    pub fn is_structural(self) -> bool {
        matches!(self, Self::StructuralCandidate)
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::StructuralCandidate => "structural-candidate",
            Self::VerifiedAssertion => "verified-assertion",
            Self::MergedIdentity => "merged-identity",
            Self::UnregisteredRelation => "unregistered-relation",
            Self::RawFailureContext => "raw-failure-context",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceAnchor {
    pub anchor_id: AnchorId,
    pub start_offset: usize,
    pub end_offset: usize,
    pub fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralCandidate {
    pub candidate_id: CandidateId,
    pub category: DecodeCategory,
    pub anchor: EvidenceAnchor,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodeRequest {
    pub payload_ref: PayloadRef,
    pub family_format: FamilyFormat,
    pub bytes: Vec<u8>,
}

impl DecodeRequest {
    pub fn new(payload_ref: PayloadRef, family_format: FamilyFormat, bytes: &[u8]) -> Self {
        Self {
            payload_ref,
            family_format,
            bytes: bytes.to_vec(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecoderEmission {
    pub category: DecodeCategory,
    pub candidate_id: Option<CandidateId>,
    pub anchor: Option<EvidenceAnchor>,
    /// Optional raw context. Application must never accept this into diagnostics.
    pub raw_context: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SafeDiagnostic {
    pub diagnostic_id: DiagnosticId,
    pub category: String,
    pub positive_control: bool,
    pub byte_count: usize,
    pub fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodeResult {
    pub payload_ref: PayloadRef,
    pub candidates: Vec<StructuralCandidate>,
    pub rejected_categories: Vec<DecodeCategory>,
    pub diagnostics: Vec<SafeDiagnostic>,
    pub verified_assertion_absent: bool,
    pub merged_identity_absent: bool,
    pub unregistered_relation_absent: bool,
    pub raw_payload_absent: bool,
}

pub fn fingerprint_bytes(bytes: &[u8]) -> String {
    // FNV-1a diagnostic fingerprint only; not integrity or authority digest.
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("fnv1a64:{hash:016x}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_payload_ref() {
        assert!(PayloadRef::parse("").is_err());
    }

    #[test]
    fn structural_category_is_only_accepted_kind() {
        assert!(DecodeCategory::StructuralCandidate.is_structural());
        assert!(!DecodeCategory::VerifiedAssertion.is_structural());
        assert!(!DecodeCategory::MergedIdentity.is_structural());
        assert!(!DecodeCategory::UnregisteredRelation.is_structural());
        assert!(!DecodeCategory::RawFailureContext.is_structural());
    }
}
