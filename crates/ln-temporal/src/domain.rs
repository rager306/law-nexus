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

id_type!(AnchorId, "anchor id");
id_type!(RequestId, "request id");

pub const D118_POLICY_VERSION: &str = "d118:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ClockKind {
    FactualEvent,
    Proceeding,
    LegalActEffect,
    SourcePublication,
    SystemObservation,
}

impl ClockKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::FactualEvent => "factual_event",
            Self::Proceeding => "proceeding",
            Self::LegalActEffect => "legal_act_effect",
            Self::SourcePublication => "source_publication",
            Self::SystemObservation => "system_observation",
        }
    }

    pub fn all() -> [ClockKind; 5] {
        [
            Self::FactualEvent,
            Self::Proceeding,
            Self::LegalActEffect,
            Self::SourcePublication,
            Self::SystemObservation,
        ]
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SubstituteKind {
    OtherClock(ClockKind),
    WallClock,
    EditionOrder,
    LifecycleType,
}

impl SubstituteKind {
    pub fn as_str(self) -> String {
        match self {
            Self::OtherClock(clock) => format!("other_clock:{}", clock.as_str()),
            Self::WallClock => "wall_clock".to_owned(),
            Self::EditionOrder => "edition_order".to_owned(),
            Self::LifecycleType => "lifecycle_type".to_owned(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResolutionOutcome {
    Resolved,
    MissingAnchor,
    SubstituteRejected,
    Unknown,
    Conflict,
}

impl ResolutionOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Resolved => "resolved",
            Self::MissingAnchor => "missing-anchor",
            Self::SubstituteRejected => "substitute-rejected",
            Self::Unknown => "unknown",
            Self::Conflict => "conflict",
        }
    }

    pub fn is_fail_closed(self) -> bool {
        !matches!(self, Self::Resolved)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClockAnchor {
    pub clock: ClockKind,
    pub anchor_id: AnchorId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolutionRequest {
    pub request_id: RequestId,
    pub governing_clock: ClockKind,
    /// Attempted non-governing sources offered by caller/adapter.
    pub attempted_substitutes: Vec<SubstituteKind>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecisionTrace {
    pub policy_version: String,
    pub governing_clock: ClockKind,
    pub governing_anchor: Option<AnchorId>,
    pub considered_substitutes: Vec<String>,
    pub rejected_substitutes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolutionResult {
    pub outcome: ResolutionOutcome,
    pub governing_clock: ClockKind,
    pub resolved_anchor: Option<AnchorId>,
    pub substitution_used: bool,
    pub trace: DecisionTrace,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn five_clocks_are_distinct() {
        assert_eq!(ClockKind::all().len(), 5);
        assert_eq!(ClockKind::FactualEvent.as_str(), "factual_event");
        assert_eq!(ClockKind::SystemObservation.as_str(), "system_observation");
    }

    #[test]
    fn resolved_is_not_fail_closed() {
        assert!(!ResolutionOutcome::Resolved.is_fail_closed());
        assert!(ResolutionOutcome::SubstituteRejected.is_fail_closed());
    }
}
