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

id_type!(PromotionOpId, "promotion operation id");
id_type!(InputDigest, "input digest");
id_type!(CommitId, "commit id");
id_type!(AcceptedSetId, "accepted set id");

/// Sealed publication authority surface. HC-04 must never mint this on D116 success.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationAuthority {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PromotionAttemptState {
    InProgress,
    Cancelled,
    Committed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PromotionOutcome {
    Cancelled,
    Committed,
    AlreadyCommitted,
    RejectedMismatch,
    Incomplete,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionRecord {
    pub op_id: PromotionOpId,
    pub accepted_set_id: AcceptedSetId,
    pub input_digest: InputDigest,
    pub state: PromotionAttemptState,
    pub commit_id: Option<CommitId>,
    pub commit_digest: Option<InputDigest>,
    pub publication_authority: Option<PublicationAuthority>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionResult {
    pub outcome: PromotionOutcome,
    pub op_id: PromotionOpId,
    pub commit_id: Option<CommitId>,
    pub commit_digest: Option<InputDigest>,
    pub publication_authority: Option<PublicationAuthority>,
}

impl PromotionResult {
    pub fn has_publication_authority(&self) -> bool {
        self.publication_authority.is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_op_id() {
        assert!(PromotionOpId::parse("").is_err());
    }

    #[test]
    fn accepts_stable_op_id() {
        assert_eq!(PromotionOpId::parse("P1").unwrap().as_str(), "P1");
    }
}
