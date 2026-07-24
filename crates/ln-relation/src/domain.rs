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

id_type!(PredicateId, "predicate id");
id_type!(EndpointId, "endpoint id");
id_type!(FamilyId, "family id");
id_type!(RegistryVersion, "registry version");
id_type!(EvidenceRef, "evidence ref");
id_type!(InputChainDigest, "input chain digest");

pub const C13_GATE_VERSION: &str = "c13:v1";
pub const DEFAULT_REGISTRY_VERSION: &str = "R1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RelationOutcome {
    Accepted,
    UnknownPredicate,
    WrongOwner,
    InsufficientEvidence,
}

impl RelationOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::UnknownPredicate => "unknown-predicate",
            Self::WrongOwner => "wrong-owner",
            Self::InsufficientEvidence => "insufficient-evidence",
        }
    }

    pub fn is_rejection(self) -> bool {
        !matches!(self, Self::Accepted)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegisteredPredicate {
    pub predicate_id: PredicateId,
    pub owner_family: FamilyId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RelationProposal {
    pub predicate_id: PredicateId,
    pub subject: EndpointId,
    pub object: EndpointId,
    pub proposed_owner: FamilyId,
    pub evidence_refs: Vec<EvidenceRef>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RelationFact {
    pub predicate_id: PredicateId,
    pub subject: EndpointId,
    pub object: EndpointId,
    pub owner_family: FamilyId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RelationValidation {
    pub c13_version: String,
    pub registry_version: RegistryVersion,
    pub outcome: RelationOutcome,
    pub predicate_id: PredicateId,
    pub subject: EndpointId,
    pub object: EndpointId,
    pub proposed_owner: FamilyId,
    pub registry_unchanged: bool,
    pub stored_as_fact: bool,
    pub exposed_as_query_fact: bool,
    pub input_chain_digest: InputChainDigest,
}

pub fn digest_proposal(proposal: &RelationProposal) -> InputChainDigest {
    let mut material = format!(
        "{}|{}|{}|{}",
        proposal.predicate_id.as_str(),
        proposal.subject.as_str(),
        proposal.object.as_str(),
        proposal.proposed_owner.as_str()
    );
    for item in &proposal.evidence_refs {
        material.push('|');
        material.push_str(item.as_str());
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
    fn rejects_empty_predicate_id() {
        assert!(PredicateId::parse("").is_err());
    }

    #[test]
    fn outcome_vocabulary_is_closed() {
        assert_eq!(
            RelationOutcome::UnknownPredicate.as_str(),
            "unknown-predicate"
        );
        assert_eq!(RelationOutcome::WrongOwner.as_str(), "wrong-owner");
    }
}
