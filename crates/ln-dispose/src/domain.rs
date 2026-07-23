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

id_type!(InventoryItemId, "inventory item id");
id_type!(ReviewEvidenceId, "review evidence id");
id_type!(PromotionRequestId, "promotion request id");
id_type!(PromotionAttemptId, "promotion attempt id");
id_type!(CommitId, "commit id");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DispositionState {
    Pending,
    Quarantined,
    Accepted,
    Rejected,
}

impl DispositionState {
    pub fn is_accepted(self) -> bool {
        matches!(self, Self::Accepted)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DispositionReason {
    Incomplete,
    Conflict,
    Unauthorized,
    Accepted,
    RejectedReasonCoded,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Disposition {
    pub item_id: InventoryItemId,
    pub state: DispositionState,
    pub reason: DispositionReason,
    pub evidence_ids: Vec<ReviewEvidenceId>,
    pub accepted_commit_id: Option<CommitId>,
    pub promotion_identity: Option<PromotionIdentity>,
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PromotionIdentity {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PromotionOutcome {
    Rejected,
    Committed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionResult {
    pub outcome: PromotionOutcome,
    pub reason: DispositionReason,
    pub commit_id: Option<CommitId>,
    pub promotion_identity: Option<PromotionIdentity>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_reject_unsafe_values() {
        assert!(InventoryItemId::parse("").is_err());
        assert!(ReviewEvidenceId::parse("bad id").is_err());
        assert!(PromotionRequestId::parse("a/b").is_err());
    }
}
