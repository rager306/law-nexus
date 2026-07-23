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

id_type!(IdentityId, "identity id");
id_type!(ContributionId, "contribution id");
id_type!(FamilyId, "family id");
id_type!(C12Version, "c12 version");
id_type!(InputChainDigest, "input chain digest");

pub const C12_GATE_VERSION: &str = "c12:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvidenceSide {
    Left,
    Right,
    Bilateral,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceContribution {
    pub contribution_id: ContributionId,
    pub family_id: FamilyId,
    pub side: EvidenceSide,
    /// Human-readable ceiling label only; not a ranking authority.
    pub evidence_ceiling: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityOutcome {
    Same,
    Different,
    Candidate,
    Ambiguous,
    Conflict,
    NotResolvable,
}

impl IdentityOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Same => "same",
            Self::Different => "different",
            Self::Candidate => "candidate",
            Self::Ambiguous => "ambiguous",
            Self::Conflict => "conflict",
            Self::NotResolvable => "not-resolvable",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityReason {
    OneSidedEvidence,
    SimilarityOnly,
    MissingEvidence,
    BilateralSameEvidence,
    BilateralDifferentEvidence,
    ConflictingEvidence,
}

impl IdentityReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::OneSidedEvidence => "one-sided-evidence",
            Self::SimilarityOnly => "similarity-only",
            Self::MissingEvidence => "missing-evidence",
            Self::BilateralSameEvidence => "bilateral-same-evidence",
            Self::BilateralDifferentEvidence => "bilateral-different-evidence",
            Self::ConflictingEvidence => "conflicting-evidence",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityRecord {
    pub identity_id: IdentityId,
    pub label: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssertRequest {
    pub left_id: IdentityId,
    pub right_id: IdentityId,
    pub contributions: Vec<EvidenceContribution>,
    /// Caller claims `same` (e.g. from adapter/similarity). Policy decides.
    pub claim_same: bool,
    /// Optional similarity score used only as ranking within a ceiling.
    /// Cannot authorize same/merge by itself.
    pub similarity_score: Option<u8>,
    pub method: String,
    pub scope: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityAssertion {
    pub c12_version: C12Version,
    pub outcome: IdentityOutcome,
    pub reason: IdentityReason,
    pub left_id: IdentityId,
    pub right_id: IdentityId,
    pub left_survives: bool,
    pub right_survives: bool,
    pub merge_performed: bool,
    pub no_merge_observation: bool,
    pub contribution_ids: Vec<ContributionId>,
    pub input_chain_digest: InputChainDigest,
    pub method: String,
    pub scope: String,
    pub evidence_ceiling_visible: bool,
}

pub fn digest_pair(
    left_id: &IdentityId,
    right_id: &IdentityId,
    contributions: &[EvidenceContribution],
) -> InputChainDigest {
    let mut material = format!("{}|{}", left_id.as_str(), right_id.as_str());
    for item in contributions {
        material.push('|');
        material.push_str(item.contribution_id.as_str());
        material.push(':');
        material.push_str(item.family_id.as_str());
    }
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
    fn rejects_empty_identity_id() {
        assert!(IdentityId::parse("").is_err());
    }

    #[test]
    fn outcome_vocabulary_is_closed() {
        assert_eq!(IdentityOutcome::Same.as_str(), "same");
        assert_eq!(IdentityOutcome::NotResolvable.as_str(), "not-resolvable");
    }
}
