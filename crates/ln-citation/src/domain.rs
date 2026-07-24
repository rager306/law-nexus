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

id_type!(CitationId, "citation id");
id_type!(SourceRef, "source ref");
id_type!(AnchorId, "anchor id");

pub const CITATION_POLICY_VERSION: &str = "hc18:resolve-citation:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceAuthority {
    Official,
    Mirror,
    Unverified,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CitationOutcome {
    Resolved,
    Missing,
    Invalid,
    MirrorRelabelRejected,
    AnchorInventionRejected,
}

impl CitationOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Resolved => "resolved",
            Self::Missing => "missing",
            Self::Invalid => "invalid",
            Self::MirrorRelabelRejected => "mirror-relabel-rejected",
            Self::AnchorInventionRejected => "anchor-invention-rejected",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CitationRequest {
    pub citation_id: CitationId,
    pub source_ref: SourceRef,
    pub requested_authority: SourceAuthority,
    pub anchor_invention_attempt: bool,
    pub mirror_relabel_attempt: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CitationResult {
    pub outcome: CitationOutcome,
    pub citation_id: CitationId,
    pub resolved_anchor: Option<AnchorId>,
    pub authoritative: bool,
    pub policy_version: String,
}
