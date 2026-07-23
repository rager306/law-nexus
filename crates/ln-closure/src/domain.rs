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

id_type!(NodeId, "node id");
id_type!(RuleVersion, "rule version");
id_type!(RequestId, "request id");

/// Inward dependency policy version for HC-11 traces.
pub const CLOSURE_POLICY_VERSION: &str = "hc11:dependency-closure:v1";

/// Hard fan-out bound for synthetic completeness. Not a product capacity value.
pub const MAX_BOUNDED_FANOUT: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ClosureStatus {
    Complete,
    Incomplete,
    Unknown,
    Unbounded,
    RuleVersionMismatch,
}

impl ClosureStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Complete => "complete",
            Self::Incomplete => "incomplete",
            Self::Unknown => "unknown",
            Self::Unbounded => "unbounded",
            Self::RuleVersionMismatch => "rule-version-mismatch",
        }
    }

    pub fn is_complete(self) -> bool {
        matches!(self, Self::Complete)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicationEligibility {
    Eligible,
    Blocked,
}

impl PublicationEligibility {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Eligible => "eligible",
            Self::Blocked => "blocked",
        }
    }

    pub fn is_blocked(self) -> bool {
        matches!(self, Self::Blocked)
    }
}

/// Attempts to invent completeness from non-evidence signals.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompletenessClaim {
    None,
    ProgressAsComplete,
    QueueDepthAsComplete,
    InventedAffectedSet,
}

impl CompletenessClaim {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::ProgressAsComplete => "progress_as_complete",
            Self::QueueDepthAsComplete => "queue_depth_as_complete",
            Self::InventedAffectedSet => "invented_affected_set",
        }
    }

    pub fn is_forbidden(self) -> bool {
        !matches!(self, Self::None)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClosureRequest {
    pub request_id: RequestId,
    pub changed: Vec<NodeId>,
    pub expected_rule_version: RuleVersion,
    pub completeness_claim: CompletenessClaim,
    /// Requested incremental authoritative publication after closure.
    pub request_incremental_publication: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClosureTrace {
    pub policy_version: String,
    pub request_id: RequestId,
    pub status: ClosureStatus,
    pub publication_eligibility: PublicationEligibility,
    pub changed: Vec<NodeId>,
    pub affected: Vec<NodeId>,
    pub missing: Vec<NodeId>,
    pub stale: Vec<NodeId>,
    pub observed_rule_version: Option<RuleVersion>,
    pub expected_rule_version: RuleVersion,
    pub completeness_claim: CompletenessClaim,
    pub completeness_claim_applied: bool,
    pub progress_used_as_completeness: bool,
    pub queue_depth_used_as_completeness: bool,
    pub fanout: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClosureResult {
    pub status: ClosureStatus,
    pub publication_eligibility: PublicationEligibility,
    pub changed: Vec<NodeId>,
    pub affected: Vec<NodeId>,
    pub missing: Vec<NodeId>,
    pub stale: Vec<NodeId>,
    pub completeness_claim_applied: bool,
    pub progress_used_as_completeness: bool,
    pub queue_depth_used_as_completeness: bool,
    pub trace: ClosureTrace,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_node_id() {
        assert!(NodeId::parse("").is_err());
    }

    #[test]
    fn complete_is_only_complete_status() {
        assert!(ClosureStatus::Complete.is_complete());
        assert!(!ClosureStatus::Incomplete.is_complete());
        assert!(!ClosureStatus::Unknown.is_complete());
        assert!(!ClosureStatus::Unbounded.is_complete());
        assert!(!ClosureStatus::RuleVersionMismatch.is_complete());
    }
}
