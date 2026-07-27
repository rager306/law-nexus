use crate::{
    deontic::DeonticLexemeKind,
    domain::{HierarchyLevel, SourceFormatId, TextSpan},
    references::ReferenceMentionKind,
    temporal::TemporalPhraseKind,
};

/// Validation error for golden manifest construction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GoldenError {
    EmptySourcePath,
    EmptySourceHash,
    ZeroByteCount,
    EmptyFingerprint,
    EmptyAnnotations,
    DuplicateAnnotation { block_index: usize },
    InvalidReferenceNumber { number: String },
}

impl std::fmt::Display for GoldenError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::EmptySourcePath => write!(formatter, "empty source path"),
            Self::EmptySourceHash => write!(formatter, "empty source hash"),
            Self::ZeroByteCount => write!(formatter, "zero byte count"),
            Self::EmptyFingerprint => write!(formatter, "empty runtime fingerprint"),
            Self::EmptyAnnotations => write!(formatter, "empty annotations"),
            Self::DuplicateAnnotation { block_index } => {
                write!(formatter, "duplicate annotation at block {block_index}")
            }
            Self::InvalidReferenceNumber { number } => {
                write!(formatter, "invalid reference number: {number}")
            }
        }
    }
}

impl std::error::Error for GoldenError {}

/// Structural annotation layer.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GoldenLayer {
    Hierarchy,
    Reference,
    Temporal,
    Deontic,
}

/// One expected structural annotation in decoded block text.
///
/// All variants carry only decoded `TextSpan` offsets and typed kind/level
/// values. No raw legal text, resolved target identity, five-clock fact,
/// `NormStatement`, citation authority or legal effect is present.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GoldenAnnotation {
    Hierarchy {
        block_index: usize,
        level: HierarchyLevel,
        span: TextSpan,
    },
    Reference {
        block_index: usize,
        kind: ReferenceMentionKind,
        number: String,
        span: TextSpan,
    },
    Temporal {
        block_index: usize,
        kind: TemporalPhraseKind,
        span: TextSpan,
    },
    Deontic {
        block_index: usize,
        kind: DeonticLexemeKind,
        span: TextSpan,
        negated: bool,
    },
}

impl GoldenAnnotation {
    pub fn layer(&self) -> GoldenLayer {
        match self {
            Self::Hierarchy { .. } => GoldenLayer::Hierarchy,
            Self::Reference { .. } => GoldenLayer::Reference,
            Self::Temporal { .. } => GoldenLayer::Temporal,
            Self::Deontic { .. } => GoldenLayer::Deontic,
        }
    }

    pub fn block_index(&self) -> usize {
        match self {
            Self::Hierarchy { block_index, .. }
            | Self::Reference { block_index, .. }
            | Self::Temporal { block_index, .. }
            | Self::Deontic { block_index, .. } => *block_index,
        }
    }

    pub fn span(&self) -> TextSpan {
        match self {
            Self::Hierarchy { span, .. }
            | Self::Reference { span, .. }
            | Self::Temporal { span, .. }
            | Self::Deontic { span, .. } => *span,
        }
    }

    fn duplicate_key(&self) -> (GoldenLayer, usize, TextSpan) {
        (self.layer(), self.block_index(), self.span())
    }
}

fn is_valid_reference_number(number: &str) -> bool {
    let bytes = number.as_bytes();
    if bytes.is_empty() || !bytes[0].is_ascii_digit() {
        return false;
    }
    let mut end = 0;
    while end < bytes.len() && bytes[end].is_ascii_digit() {
        end += 1;
    }
    loop {
        if end >= bytes.len() || bytes[end] != b'.' {
            break;
        }
        if end + 1 >= bytes.len() || !bytes[end + 1].is_ascii_digit() {
            return false;
        }
        end += 1;
        while end < bytes.len() && bytes[end].is_ascii_digit() {
            end += 1;
        }
    }
    end == bytes.len()
}

/// Source identity for a golden fixture.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GoldenSource {
    path: String,
    sha256: String,
    byte_count: usize,
    runtime_fingerprint: String,
}

impl GoldenSource {
    pub fn try_new(
        path: &str,
        sha256: &str,
        byte_count: usize,
        runtime_fingerprint: &str,
    ) -> Result<Self, GoldenError> {
        if path.trim().is_empty() {
            return Err(GoldenError::EmptySourcePath);
        }
        if sha256.trim().is_empty() {
            return Err(GoldenError::EmptySourceHash);
        }
        if byte_count == 0 {
            return Err(GoldenError::ZeroByteCount);
        }
        if runtime_fingerprint.trim().is_empty() {
            return Err(GoldenError::EmptyFingerprint);
        }
        Ok(Self {
            path: path.to_owned(),
            sha256: sha256.to_owned(),
            byte_count,
            runtime_fingerprint: runtime_fingerprint.to_owned(),
        })
    }

    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn sha256(&self) -> &str {
        &self.sha256
    }

    pub fn byte_count(&self) -> usize {
        self.byte_count
    }

    pub fn runtime_fingerprint(&self) -> &str {
        &self.runtime_fingerprint
    }
}

/// A validated golden fixture with structural annotations only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GoldenFixture {
    source: GoldenSource,
    provider: SourceFormatId,
    annotations: Vec<GoldenAnnotation>,
    non_claims: Vec<String>,
}

impl GoldenFixture {
    pub fn try_new(
        source: GoldenSource,
        provider: SourceFormatId,
        annotations: Vec<GoldenAnnotation>,
        non_claims: Vec<String>,
    ) -> Result<Self, GoldenError> {
        if annotations.is_empty() {
            return Err(GoldenError::EmptyAnnotations);
        }
        let mut seen = std::collections::HashSet::new();
        for annotation in &annotations {
            if let Some(number) = match annotation {
                GoldenAnnotation::Reference { number, .. } => Some(number.as_str()),
                _ => None,
            } {
                if !is_valid_reference_number(number) {
                    return Err(GoldenError::InvalidReferenceNumber {
                        number: number.to_owned(),
                    });
                }
            }
            if !seen.insert(annotation.duplicate_key()) {
                return Err(GoldenError::DuplicateAnnotation {
                    block_index: annotation.block_index(),
                });
            }
        }
        Ok(Self {
            source,
            provider,
            annotations,
            non_claims,
        })
    }

    pub fn source(&self) -> &GoldenSource {
        &self.source
    }

    pub fn provider(&self) -> SourceFormatId {
        self.provider
    }

    pub fn annotations(&self) -> &[GoldenAnnotation] {
        &self.annotations
    }

    pub fn non_claims(&self) -> &[String] {
        &self.non_claims
    }
}
