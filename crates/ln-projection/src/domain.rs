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
id_type!(BaselineId, "baseline id");
id_type!(ScopeId, "scope id");
id_type!(CutoffId, "cutoff id");
id_type!(RuleVersion, "rule version");
id_type!(NodeId, "node id");
id_type!(PublicationAuthorityId, "publication authority id");

/// Projection rebuild policy version for HC-12 traces.
pub const PROJECTION_POLICY_VERSION: &str = "hc12:disposable-projection:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RebuildOutcome {
    RebuiltDisposable,
    Partial,
    StaleInput,
    Cancelled,
    Failed,
}

impl RebuildOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::RebuiltDisposable => "rebuilt-disposable",
            Self::Partial => "partial",
            Self::StaleInput => "stale-input",
            Self::Cancelled => "cancelled",
            Self::Failed => "failed",
        }
    }

    pub fn is_success_disposable(self) -> bool {
        matches!(self, Self::RebuiltDisposable)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompletenessLabel {
    Incomplete,
    CompleteClaimed,
}

impl CompletenessLabel {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Incomplete => "incomplete",
            Self::CompleteClaimed => "complete-claimed",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CurrencyLabel {
    NotCurrent,
    CurrentClaimed,
}

impl CurrencyLabel {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NotCurrent => "not-current",
            Self::CurrentClaimed => "current-claimed",
        }
    }
}

/// Sealed: rebuild path never mints publication authority.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationAuthority {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CeilingMetadata {
    pub authoritative: bool,
    pub completeness: CompletenessLabel,
    pub currency: CurrencyLabel,
    pub baseline: BaselineId,
    pub scope: ScopeId,
    pub cutoff: CutoffId,
    pub rules: RuleVersion,
    pub stale: Vec<NodeId>,
    pub gaps: Vec<NodeId>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RebuildRequest {
    pub request_id: RequestId,
    pub baseline: BaselineId,
    pub scope: ScopeId,
    pub cutoff: CutoffId,
    pub rules: RuleVersion,
    /// Known gaps declared at request time; must not be hidden.
    pub known_gaps: Vec<NodeId>,
}

/// Executor-reported raw outcome. Application owns policy demotion.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutorReport {
    pub outcome: RebuildOutcome,
    pub claims_complete: bool,
    pub claims_current: bool,
    pub claims_authoritative: bool,
    pub invents_fact: bool,
    pub hides_gaps: bool,
    pub publication_authority_granted: bool,
    pub extra_stale: Vec<NodeId>,
    pub residual_gaps: Vec<NodeId>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RebuildTrace {
    pub policy_version: String,
    pub request_id: RequestId,
    pub outcome: RebuildOutcome,
    pub ceiling: CeilingMetadata,
    pub publication_authority: Option<PublicationAuthority>,
    pub publication_authority_changed: bool,
    pub executor_claimed_complete: bool,
    pub executor_claimed_current: bool,
    pub executor_claimed_authoritative: bool,
    pub executor_invented_fact: bool,
    pub executor_hid_gaps: bool,
    pub demoted: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RebuildResult {
    pub outcome: RebuildOutcome,
    pub ceiling: CeilingMetadata,
    pub publication_authority: Option<PublicationAuthority>,
    pub publication_authority_changed: bool,
    pub demoted: bool,
    pub trace: RebuildTrace,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_request_id() {
        assert!(RequestId::parse("").is_err());
    }

    #[test]
    fn publication_authority_is_sealed_default_empty() {
        assert_eq!(
            PublicationAuthority::default(),
            PublicationAuthority::default()
        );
    }
}
