use std::error::Error;
use std::fmt;

const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}
impl fmt::Display for IdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "invalid {}: {}", self.kind, self.reason)
    }
}
impl Error for IdError {}

fn parse_id(kind: &'static str, value: &str) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > MAX_ID_LEN {
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
                parse_id($kind, value).map(Self)
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(QueryId, "query id");
id_type!(EvidenceId, "evidence id");
id_type!(ScopeId, "scope id");

pub const QUERY_POLICY_VERSION: &str = "hc17:evidence-bounded-query:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum QueryOutcome {
    Answered,
    NoAnswer,
    Partial,
    InventedRejected,
}

impl QueryOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Answered => "answered",
            Self::NoAnswer => "no-answer",
            Self::Partial => "partial",
            Self::InventedRejected => "invented-rejected",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueryRequest {
    pub query_id: QueryId,
    pub scope_id: ScopeId,
    pub requested_evidence: Vec<EvidenceId>,
    pub invention_attempt: bool,
    pub fabrication_attempt: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QueryResult {
    pub outcome: QueryOutcome,
    pub query_id: QueryId,
    pub returned_evidence: Vec<EvidenceId>,
    pub authoritative: bool,
    pub policy_version: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn outcomes_classification() {
        assert!(QueryOutcome::Answered.as_str() == "answered");
        assert!(QueryOutcome::InventedRejected.as_str() == "invented-rejected");
    }
}
