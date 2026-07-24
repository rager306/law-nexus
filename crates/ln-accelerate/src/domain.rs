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

id_type!(ProvisionalId, "provisional id");
id_type!(ScopeId, "scope id");
id_type!(LabelId, "label id");
id_type!(WriterId, "writer id");

pub const ACCELERATION_POLICY_VERSION: &str = "hc16:provisional-acceleration:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AccelerationOutcome {
    Accelerated,
    Superseded,
    DirectPromotionRejected,
    LabelMutationRejected,
    Expired,
    Cancelled,
}

impl AccelerationOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Accelerated => "accelerated",
            Self::Superseded => "superseded",
            Self::DirectPromotionRejected => "direct-promotion-rejected",
            Self::LabelMutationRejected => "label-mutation-rejected",
            Self::Expired => "expired",
            Self::Cancelled => "cancelled",
        }
    }
    pub fn is_provisional(self) -> bool {
        matches!(self, Self::Accelerated | Self::Superseded)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProvisionalTier {
    Accelerated,
    Normal,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccelerationRequest {
    pub provisional_id: ProvisionalId,
    pub scope_id: ScopeId,
    pub writer_id: WriterId,
    pub label: LabelId,
    pub tier: ProvisionalTier,
    pub direct_promotion_attempt: bool,
    pub label_mutation_attempt: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AccelerationResult {
    pub outcome: AccelerationOutcome,
    pub provisional_id: ProvisionalId,
    pub authoritative: bool,
    pub policy_version: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn provisional_outcomes_are_non_authoritative() {
        assert!(AccelerationOutcome::Accelerated.is_provisional());
        assert!(AccelerationOutcome::Superseded.is_provisional());
        assert!(!AccelerationOutcome::DirectPromotionRejected.is_provisional());
        assert!(!AccelerationOutcome::LabelMutationRejected.is_provisional());
    }
}
