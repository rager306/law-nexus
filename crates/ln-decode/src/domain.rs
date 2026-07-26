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

id_type!(PayloadRef, "payload ref");
id_type!(FamilyFormat, "family format");
id_type!(CandidateId, "candidate id");
id_type!(AnchorId, "anchor id");
id_type!(DiagnosticId, "diagnostic id");

/// Categories a decoder may claim. Only structural is accepted by policy.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DecodeCategory {
    StructuralCandidate,
    /// Gate-owned; rejected by DecodeAndAnchor.
    VerifiedAssertion,
    /// Identity merge is C12-owned; rejected.
    MergedIdentity,
    /// Relation minting is C13-owned; rejected.
    UnregisteredRelation,
    /// Raw failure context / payload leak; rejected.
    RawFailureContext,
}

impl DecodeCategory {
    pub fn is_structural(self) -> bool {
        matches!(self, Self::StructuralCandidate)
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Self::StructuralCandidate => "structural-candidate",
            Self::VerifiedAssertion => "verified-assertion",
            Self::MergedIdentity => "merged-identity",
            Self::UnregisteredRelation => "unregistered-relation",
            Self::RawFailureContext => "raw-failure-context",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceAnchor {
    pub anchor_id: AnchorId,
    pub start_offset: usize,
    pub end_offset: usize,
    pub fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralCandidate {
    pub candidate_id: CandidateId,
    pub category: DecodeCategory,
    pub anchor: EvidenceAnchor,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodeRequest {
    pub payload_ref: PayloadRef,
    pub family_format: FamilyFormat,
    pub bytes: Vec<u8>,
}

impl DecodeRequest {
    pub fn new(payload_ref: PayloadRef, family_format: FamilyFormat, bytes: &[u8]) -> Self {
        Self {
            payload_ref,
            family_format,
            bytes: bytes.to_vec(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecoderEmission {
    pub category: DecodeCategory,
    pub candidate_id: Option<CandidateId>,
    pub anchor: Option<EvidenceAnchor>,
    /// Optional raw context. Application must never accept this into diagnostics.
    pub raw_context: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SafeDiagnostic {
    pub diagnostic_id: DiagnosticId,
    pub category: String,
    pub positive_control: bool,
    pub byte_count: usize,
    pub fingerprint: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodeResult {
    pub payload_ref: PayloadRef,
    pub candidates: Vec<StructuralCandidate>,
    pub rejected_categories: Vec<DecodeCategory>,
    pub diagnostics: Vec<SafeDiagnostic>,
    pub verified_assertion_absent: bool,
    pub merged_identity_absent: bool,
    pub unregistered_relation_absent: bool,
    pub raw_payload_absent: bool,
}

/// Stable validation failures for provider-neutral parser domain values.
///
/// Error variants intentionally contain no source text.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParserDomainError {
    InvalidSourceSpan { start: usize, end: usize },
    InvalidTextSpan { start: usize, end: usize },
    EmptyBlockText,
    EmptyProviderStyleId,
    EmptyHierarchyNumber,
    EmptyHierarchyTitle,
    EmptyHierarchyText,
}

impl fmt::Display for ParserDomainError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidSourceSpan { start, end } => {
                write!(formatter, "invalid source span: start={start}, end={end}")
            }
            Self::InvalidTextSpan { start, end } => {
                write!(
                    formatter,
                    "invalid decoded text span: start={start}, end={end}"
                )
            }
            Self::EmptyBlockText => formatter.write_str("parsed block text is empty"),
            Self::EmptyProviderStyleId => formatter.write_str("provider style id is empty"),
            Self::EmptyHierarchyNumber => formatter.write_str("hierarchy number is empty"),
            Self::EmptyHierarchyTitle => formatter.write_str("hierarchy title is empty"),
            Self::EmptyHierarchyText => formatter.write_str("hierarchy text is empty"),
        }
    }
}

impl Error for ParserDomainError {}

/// Non-empty half-open byte range in the original source artifact.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct SourceSpan {
    start: usize,
    end: usize,
}

impl SourceSpan {
    pub fn try_new(start: usize, end: usize) -> Result<Self, ParserDomainError> {
        if start >= end {
            return Err(ParserDomainError::InvalidSourceSpan { start, end });
        }
        Ok(Self { start, end })
    }

    pub fn start(self) -> usize {
        self.start
    }

    pub fn end(self) -> usize {
        self.end
    }

    pub fn len(self) -> usize {
        self.end - self.start
    }

    pub fn is_empty(self) -> bool {
        false
    }
}

/// Non-empty half-open byte range in decoded block text.
///
/// This coordinate system is intentionally distinct from `SourceSpan`, which
/// refers to the original XML/ODT artifact. Adapters own any mapping between
/// the two.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct TextSpan {
    start: usize,
    end: usize,
}

impl TextSpan {
    pub fn try_new(start: usize, end: usize) -> Result<Self, ParserDomainError> {
        if start >= end {
            return Err(ParserDomainError::InvalidTextSpan { start, end });
        }
        Ok(Self { start, end })
    }

    pub fn start(self) -> usize {
        self.start
    }

    pub fn end(self) -> usize {
        self.end
    }

    pub fn len(self) -> usize {
        self.end - self.start
    }

    pub fn is_empty(self) -> bool {
        false
    }
}

/// Source format identity carried by shared parser records.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SourceFormatId {
    ConsultantWordMl,
    GarantOdt,
}

/// Provider-specific styles map into this shared classification in adapters.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ParagraphStyle {
    Title,
    BodyText,
    Heading,
    JurTerm,
    ProviderComment,
    TableCell,
    Unknown,
}

/// A validated paragraph emitted by any source-format adapter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParsedBlock {
    text: String,
    provider_style_id: Option<String>,
    style: ParagraphStyle,
    source_span: SourceSpan,
    source_format: SourceFormatId,
}

impl ParsedBlock {
    pub fn try_new(
        text: String,
        provider_style_id: Option<String>,
        style: ParagraphStyle,
        source_span: SourceSpan,
        source_format: SourceFormatId,
    ) -> Result<Self, ParserDomainError> {
        if text.trim().is_empty() {
            return Err(ParserDomainError::EmptyBlockText);
        }
        if provider_style_id
            .as_deref()
            .is_some_and(|value| value.trim().is_empty())
        {
            return Err(ParserDomainError::EmptyProviderStyleId);
        }
        Ok(Self {
            text,
            provider_style_id,
            style,
            source_span,
            source_format,
        })
    }

    pub fn text(&self) -> &str {
        &self.text
    }

    pub fn provider_style_id(&self) -> Option<&str> {
        self.provider_style_id.as_deref()
    }

    pub fn style(&self) -> ParagraphStyle {
        self.style
    }

    pub fn source_span(&self) -> SourceSpan {
        self.source_span
    }

    pub fn source_format(&self) -> SourceFormatId {
        self.source_format
    }
}

/// Format-independent hierarchy levels for Russian legal acts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum HierarchyLevel {
    Razdel,
    Glava,
    Paragraph,
    Statya,
    Chast,
    Punkt,
    Podpunkt,
}

/// A validated hierarchy marker and its exact source span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyNode {
    level: HierarchyLevel,
    number: String,
    title: Option<String>,
    text: String,
    source_span: SourceSpan,
}

impl HierarchyNode {
    pub fn try_new(
        level: HierarchyLevel,
        number: String,
        title: Option<String>,
        text: String,
        source_span: SourceSpan,
    ) -> Result<Self, ParserDomainError> {
        if number.trim().is_empty() {
            return Err(ParserDomainError::EmptyHierarchyNumber);
        }
        if title
            .as_deref()
            .is_some_and(|value| value.trim().is_empty())
        {
            return Err(ParserDomainError::EmptyHierarchyTitle);
        }
        if text.trim().is_empty() {
            return Err(ParserDomainError::EmptyHierarchyText);
        }
        Ok(Self {
            level,
            number,
            title,
            text,
            source_span,
        })
    }

    pub fn level(&self) -> HierarchyLevel {
        self.level
    }

    pub fn number(&self) -> &str {
        &self.number
    }

    pub fn title(&self) -> Option<&str> {
        self.title.as_deref()
    }

    pub fn text(&self) -> &str {
        &self.text
    }

    pub fn source_span(&self) -> SourceSpan {
        self.source_span
    }
}

pub fn fingerprint_bytes(bytes: &[u8]) -> String {
    // FNV-1a diagnostic fingerprint only; not integrity or authority digest.
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    format!("fnv1a64:{hash:016x}")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_payload_ref() {
        assert!(PayloadRef::parse("").is_err());
    }

    #[test]
    fn structural_category_is_only_accepted_kind() {
        assert!(DecodeCategory::StructuralCandidate.is_structural());
        assert!(!DecodeCategory::VerifiedAssertion.is_structural());
        assert!(!DecodeCategory::MergedIdentity.is_structural());
        assert!(!DecodeCategory::UnregisteredRelation.is_structural());
        assert!(!DecodeCategory::RawFailureContext.is_structural());
    }
}
