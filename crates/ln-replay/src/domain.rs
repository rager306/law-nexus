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
id_type!(CheckpointId, "checkpoint id");
id_type!(CheckpointDigest, "checkpoint digest");
id_type!(EffectId, "effect id");
id_type!(OperationId, "operation id");
id_type!(RuleVersion, "rule version");

/// Replay policy version for HC-14 traces.
pub const REPLAY_POLICY_VERSION: &str = "hc14:checkpoint-replay:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReplayOutcome {
    Applied,
    Suppressed,
    Corrupt,
    IncompatibleRule,
    Incomplete,
    Mismatch,
}

impl ReplayOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Applied => "applied",
            Self::Suppressed => "suppressed",
            Self::Corrupt => "corrupt",
            Self::IncompatibleRule => "incompatible-rule",
            Self::Incomplete => "incomplete",
            Self::Mismatch => "mismatch",
        }
    }

    pub fn is_success(self) -> bool {
        matches!(self, Self::Applied | Self::Suppressed)
    }
}

/// Sealed: replay path never mints or changes publication authority.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationAuthority {
    _sealed: (),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CheckpointRecord {
    pub checkpoint_id: CheckpointId,
    pub digest: CheckpointDigest,
    pub rule_version: RuleVersion,
    pub operation_id: OperationId,
    pub effect_id: EffectId,
    pub history_digest: CheckpointDigest,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplayRequest {
    pub request_id: RequestId,
    pub checkpoint_id: CheckpointId,
    pub expected_digest: CheckpointDigest,
    pub expected_rule_version: RuleVersion,
    pub operation_id: OperationId,
    pub effect_id: EffectId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplayTrace {
    pub policy_version: String,
    pub request_id: RequestId,
    pub outcome: ReplayOutcome,
    pub checkpoint_id: CheckpointId,
    pub expected_digest: CheckpointDigest,
    pub observed_digest: Option<CheckpointDigest>,
    pub expected_rule_version: RuleVersion,
    pub observed_rule_version: Option<RuleVersion>,
    pub operation_id: OperationId,
    pub effect_id: EffectId,
    pub prior_applied_digest: Option<CheckpointDigest>,
    pub applied_count_before: usize,
    pub applied_count_after: usize,
    pub effect_suppressed: bool,
    pub lineage_rewritten: bool,
    pub publication_authority: Option<PublicationAuthority>,
    pub publication_authority_changed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplayResult {
    pub outcome: ReplayOutcome,
    pub applied_count: usize,
    pub effect_suppressed: bool,
    pub lineage_rewritten: bool,
    pub publication_authority: Option<PublicationAuthority>,
    pub publication_authority_changed: bool,
    pub trace: ReplayTrace,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_operation_id() {
        assert!(OperationId::parse("").is_err());
    }

    #[test]
    fn publication_authority_is_sealed_default() {
        assert_eq!(
            PublicationAuthority::default(),
            PublicationAuthority::default()
        );
    }
}
