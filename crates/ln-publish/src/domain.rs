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

id_type!(H1UnitId, "h1 unit id");
id_type!(OperationId, "operation id");
id_type!(InputDigest, "input digest");
id_type!(ScopeId, "scope id");
id_type!(CutoffId, "cutoff id");
id_type!(RuleVersion, "rule version");
id_type!(WriterId, "writer id");

/// Publication policy version for HC-15 traces.
pub const PUBLICATION_POLICY_VERSION: &str = "hc15:publish-authoritative-h1:v1";

/// Authority is granted only on the publication surface (D120), never by
/// promotion/intake/partial paths.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AuthoritySurface {
    Publication,
}

impl AuthoritySurface {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Publication => "publication",
        }
    }
}

/// Sealed publication authority. Only a complete first publish mints this.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PublicationAuthority {
    _sealed: (),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompletenessEvidence {
    Complete,
    Partial,
    Missing,
}

impl CompletenessEvidence {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Complete => "complete",
            Self::Partial => "partial",
            Self::Missing => "missing",
        }
    }

    pub fn is_complete(self) -> bool {
        matches!(self, Self::Complete)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PublicationOutcome {
    Published,
    Duplicate,
    Incomplete,
    Conflict,
    Cancelled,
    Failed,
    CompetingWriterRejected,
}

impl PublicationOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Published => "published",
            Self::Duplicate => "duplicate",
            Self::Incomplete => "incomplete",
            Self::Conflict => "conflict",
            Self::Cancelled => "cancelled",
            Self::Failed => "failed",
            Self::CompetingWriterRejected => "competing-writer-rejected",
        }
    }

    pub fn is_authoritative(self) -> bool {
        matches!(self, Self::Published | Self::Duplicate)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublishRequest {
    pub operation_id: OperationId,
    pub writer_id: WriterId,
    pub scope_id: ScopeId,
    pub cutoff_id: CutoffId,
    pub rule_version: RuleVersion,
    pub input_digest: InputDigest,
    pub completeness: CompletenessEvidence,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicationRecord {
    pub operation_id: OperationId,
    pub writer_id: WriterId,
    pub scope_id: ScopeId,
    pub cutoff_id: CutoffId,
    pub rule_version: RuleVersion,
    pub input_digest: InputDigest,
    pub h1_unit_id: H1UnitId,
    pub completeness: CompletenessEvidence,
    pub authoritative: bool,
    pub publication_authority: Option<PublicationAuthority>,
    pub authority_surface: AuthoritySurface,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PublicationResult {
    pub outcome: PublicationOutcome,
    pub operation_id: OperationId,
    pub writer_id: WriterId,
    pub scope_id: ScopeId,
    pub h1_unit_id: Option<H1UnitId>,
    pub input_digest: Option<InputDigest>,
    pub authoritative: bool,
    pub publication_authority: Option<PublicationAuthority>,
    pub authority_surface: AuthoritySurface,
    pub policy_version: String,
}

impl PublicationResult {
    pub fn has_publication_authority(&self) -> bool {
        self.publication_authority.is_some()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_operation_id() {
        assert!(OperationId::parse("").is_err());
    }

    #[test]
    fn accepts_stable_h1_unit_id() {
        assert_eq!(H1UnitId::parse("h1:1").unwrap().as_str(), "h1:1");
    }

    #[test]
    fn only_published_and_duplicate_are_authoritative_outcomes() {
        assert!(PublicationOutcome::Published.is_authoritative());
        assert!(PublicationOutcome::Duplicate.is_authoritative());
        assert!(!PublicationOutcome::Incomplete.is_authoritative());
        assert!(!PublicationOutcome::CompetingWriterRejected.is_authoritative());
        assert!(!PublicationOutcome::Conflict.is_authoritative());
        assert!(!PublicationOutcome::Cancelled.is_authoritative());
        assert!(!PublicationOutcome::Failed.is_authoritative());
    }

    #[test]
    fn authority_surface_is_publication_only() {
        assert_eq!(AuthoritySurface::Publication.as_str(), "publication");
    }
}
