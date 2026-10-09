//! Closed output vocabulary for the fail-closed retrieval output ID validator.
//!
//! This module freezes the contract published in
//! `prd/retrieval/rust_retrieval_output_validator_contract.md`
//! (`retrieval-output-validator/rust-v1`): typed, serde-free identifier
//! newtypes, the output envelope shape, the closed diagnostic taxonomy, and the
//! bounded diagnostic/outcome value types.
//!
//! The identifier newtypes are validator-envelope proof-local tokens, not
//! production domain entities. In particular `SourceBlockId` here does not
//! promote the `prd/temporal-legal-model.md` §3 `SourceBlock` row, which stays
//! `deferred-undefined`. The module adds no crate dependency and performs no
//! I/O.

use std::collections::{HashMap, HashSet};
use std::error::Error;
use std::fmt;

use crate::domain::QueryId;

/// Version string of the Rust retrieval output validator contract.
pub const VALIDATOR_CONTRACT_VERSION: &str = "retrieval-output-validator/rust-v1";

/// Maximum byte length accepted for any bounded identifier or diagnostic token.
const MAX_TOKEN_LEN: usize = 128;

// --- errors ---------------------------------------------------------------

/// Fail-closed error returned when a bounded token cannot be parsed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutputIdError {
    kind: &'static str,
    reason: &'static str,
}

impl OutputIdError {
    /// The kind of token that failed to parse.
    pub fn kind(&self) -> &'static str {
        self.kind
    }

    /// The bounded, closed failure reason (`empty`, `too long`, ...).
    pub fn reason(&self) -> &'static str {
        self.reason
    }
}

impl fmt::Display for OutputIdError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "invalid {}: {}", self.kind, self.reason)
    }
}

impl Error for OutputIdError {}

// --- bounded tokens -------------------------------------------------------

fn parse_id_value(kind: &'static str, value: &str) -> Result<String, OutputIdError> {
    if value.is_empty() {
        return Err(OutputIdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > MAX_TOKEN_LEN {
        return Err(OutputIdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.'))
    {
        return Err(OutputIdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

fn parse_diagnostic_token(kind: &'static str, value: &str) -> Result<String, OutputIdError> {
    if value.is_empty() {
        return Err(OutputIdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > MAX_TOKEN_LEN {
        return Err(OutputIdError {
            kind,
            reason: "too long",
        });
    }
    if !value.bytes().all(|b| {
        b.is_ascii_alphanumeric()
            || matches!(
                b,
                b'-' | b'_' | b':' | b'.' | b'/' | b'[' | b']' | b'<' | b'>'
            )
    }) {
        return Err(OutputIdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! output_id_type {
    ($name:ident, $kind:literal, $prefix:expr) => {
        #[doc = concat!("Envelope identifier token (`", $kind, "`).")]
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);

        impl $name {
            /// Expected namespace prefix for this token, or `None` when the
            /// token carries no namespace (for example a date selector).
            pub const NAMESPACE_PREFIX: Option<&'static str> = $prefix;

            /// Fail-closed parse: rejects empty, over-long, or unsupported input.
            pub fn parse(value: &str) -> Result<Self, OutputIdError> {
                parse_id_value($kind, value).map(Self)
            }

            /// The raw identifier string.
            pub fn as_str(&self) -> &str {
                &self.0
            }

            /// True when the token carries its expected namespace prefix, or
            /// when it carries no namespace at all.
            pub fn has_expected_namespace(&self) -> bool {
                match Self::NAMESPACE_PREFIX {
                    Some(prefix) => self.0.starts_with(prefix),
                    None => true,
                }
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(&self.0)
            }
        }
    };
}

output_id_type!(RetrievalOutputId, "retrieval output id", Some("RET-"));
output_id_type!(CitationKey, "citation key", Some("CIT-"));
output_id_type!(EvidenceSpanId, "evidence span id", Some("EV-"));
output_id_type!(SourceBlockId, "source block id", Some("SB-"));
output_id_type!(SourceDocumentId, "source document id", Some("SD-"));
output_id_type!(LegalUnitId, "legal unit id", Some("LU-"));
output_id_type!(ActEditionId, "act edition id", Some("ED-"));
output_id_type!(AnswerClaimId, "answer claim id", Some("AC-"));
output_id_type!(LegalActId, "legal act id", Some("LA-"));
output_id_type!(OutputScopeId, "output scope id", Some("SCOPE-"));
output_id_type!(RetrievalRunId, "retrieval run id", Some("RUN-"));
output_id_type!(SourceCorpusId, "source corpus id", Some("CORPUS-"));
output_id_type!(ScopeAsOfDate, "scope as-of date", None);

/// Contract version token, e.g. `retrieval-output-validator/rust-v1`.
///
/// Unlike graph identifiers this token carries the contract path separator `/`,
/// so it uses the bounded diagnostic alphabet rather than the strict graph-ID
/// alphabet.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ValidatorContractVersion(String);

impl ValidatorContractVersion {
    /// Fail-closed parse of a bounded contract-version token.
    pub fn parse(value: &str) -> Result<Self, OutputIdError> {
        parse_diagnostic_token("validator contract version", value).map(Self)
    }

    /// The raw contract-version string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for ValidatorContractVersion {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// A bounded, log-safe diagnostic token: an identifier reference or a dotted
/// field path such as `citations[0].evidence_span_id`.
///
/// The restricted alphabet excludes whitespace, quotes and non-ASCII bytes, so
/// raw legal text, prompts, and provider payloads cannot be smuggled through a
/// diagnostic field.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BoundedToken(String);

impl BoundedToken {
    /// Fail-closed parse of a bounded diagnostic token.
    pub fn parse(value: &str) -> Result<Self, OutputIdError> {
        parse_diagnostic_token("diagnostic token", value).map(Self)
    }

    /// The sentinel used when a bounded value is unavailable.
    pub fn missing() -> Self {
        Self("<missing>".to_owned())
    }

    /// The raw token string.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for BoundedToken {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

// --- wire shape -----------------------------------------------------------

/// Left-open field shape that keeps missing, explicit null, wrong shape, and a
/// present value distinct so fail-closed rules stay exact.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FieldShape<T> {
    /// Field is present with a value.
    Value(T),
    /// Field is present but explicitly null.
    ExplicitNull,
    /// Field is absent from the envelope.
    Missing,
    /// Field is present with an invalid shape for its contract type.
    WrongShape,
}

impl<T> FieldShape<T> {
    /// The contained value when present.
    pub fn value(&self) -> Option<&T> {
        match self {
            Self::Value(value) => Some(value),
            Self::ExplicitNull | Self::Missing | Self::WrongShape => None,
        }
    }

    /// True when the field is absent.
    pub fn is_missing(&self) -> bool {
        matches!(self, Self::Missing)
    }

    /// True when the field is present but null.
    pub fn is_explicit_null(&self) -> bool {
        matches!(self, Self::ExplicitNull)
    }

    /// True when the field has an invalid shape.
    pub fn is_wrong_shape(&self) -> bool {
        matches!(self, Self::WrongShape)
    }

    /// True when the field is absent or null (never repaired).
    pub fn is_absent_or_null(&self) -> bool {
        matches!(self, Self::Missing | Self::ExplicitNull)
    }
}

// --- closed output enums --------------------------------------------------

/// Closed retrieval output kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OutputKind {
    RetrievalCandidate,
    AnswerClaim,
    ScopedNoAnswer,
}

impl OutputKind {
    /// Every valid output kind, in contract order.
    pub const ALL: [Self; 3] = [
        Self::RetrievalCandidate,
        Self::AnswerClaim,
        Self::ScopedNoAnswer,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::RetrievalCandidate => "retrieval_candidate",
            Self::AnswerClaim => "answer_claim",
            Self::ScopedNoAnswer => "scoped_no_answer",
        }
    }
}

/// Closed validator verdict.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OutputVerdict {
    Accepted,
    AcceptedScopedNoAnswer,
    Rejected,
}

impl OutputVerdict {
    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Accepted => "accepted",
            Self::AcceptedScopedNoAnswer => "accepted_scoped_no_answer",
            Self::Rejected => "rejected",
        }
    }
}

/// Closed diagnostic severity.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DiagnosticSeverity {
    Error,
    Warning,
    Info,
}

impl DiagnosticSeverity {
    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Error => "error",
            Self::Warning => "warning",
            Self::Info => "info",
        }
    }
}

/// Closed diagnostic taxonomy. Exactly sixteen codes.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum OutputDiagnosticCode {
    MalformedOutputShape,
    MissingRequiredField,
    UnknownIdNamespace,
    UnresolvedCitationKey,
    AmbiguousCitationKey,
    UnresolvedEvidenceSpan,
    OrphanedSourcePath,
    OrphanedLegalUnitPath,
    IdPathMismatch,
    SupersededEvidence,
    WrongEdition,
    AnswerClaimWithoutEvidence,
    CitationWithoutEvidence,
    UnsafeNoAnswerShape,
    ForbiddenPayloadField,
    ScopedNoAnswer,
}

impl OutputDiagnosticCode {
    /// Every diagnostic code, in contract order.
    pub const ALL: [Self; 16] = [
        Self::MalformedOutputShape,
        Self::MissingRequiredField,
        Self::UnknownIdNamespace,
        Self::UnresolvedCitationKey,
        Self::AmbiguousCitationKey,
        Self::UnresolvedEvidenceSpan,
        Self::OrphanedSourcePath,
        Self::OrphanedLegalUnitPath,
        Self::IdPathMismatch,
        Self::SupersededEvidence,
        Self::WrongEdition,
        Self::AnswerClaimWithoutEvidence,
        Self::CitationWithoutEvidence,
        Self::UnsafeNoAnswerShape,
        Self::ForbiddenPayloadField,
        Self::ScopedNoAnswer,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::MalformedOutputShape => "malformed_output_shape",
            Self::MissingRequiredField => "missing_required_field",
            Self::UnknownIdNamespace => "unknown_id_namespace",
            Self::UnresolvedCitationKey => "unresolved_citation_key",
            Self::AmbiguousCitationKey => "ambiguous_citation_key",
            Self::UnresolvedEvidenceSpan => "unresolved_evidence_span",
            Self::OrphanedSourcePath => "orphaned_source_path",
            Self::OrphanedLegalUnitPath => "orphaned_legal_unit_path",
            Self::IdPathMismatch => "id_path_mismatch",
            Self::SupersededEvidence => "superseded_evidence",
            Self::WrongEdition => "wrong_edition",
            Self::AnswerClaimWithoutEvidence => "answer_claim_without_evidence",
            Self::CitationWithoutEvidence => "citation_without_evidence",
            Self::UnsafeNoAnswerShape => "unsafe_no_answer_shape",
            Self::ForbiddenPayloadField => "forbidden_payload_field",
            Self::ScopedNoAnswer => "scoped_no_answer",
        }
    }

    /// Severity derived from the code.
    pub fn severity(self) -> DiagnosticSeverity {
        match self {
            Self::ScopedNoAnswer => DiagnosticSeverity::Info,
            _ => DiagnosticSeverity::Error,
        }
    }

    /// Verdict derived from the code.
    pub fn verdict(self) -> OutputVerdict {
        match self {
            Self::ScopedNoAnswer => OutputVerdict::AcceptedScopedNoAnswer,
            _ => OutputVerdict::Rejected,
        }
    }
}

/// Closed answer-claim kind.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ClaimKind {
    NormReference,
    Status,
    Deadline,
    Condition,
}

impl ClaimKind {
    /// Every valid claim kind, in contract order.
    pub const ALL: [Self; 4] = [
        Self::NormReference,
        Self::Status,
        Self::Deadline,
        Self::Condition,
    ];

    /// Stable wire string.
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NormReference => "norm_reference",
            Self::Status => "status",
            Self::Deadline => "deadline",
            Self::Condition => "condition",
        }
    }
}

// --- diagnostics ----------------------------------------------------------

/// A bounded diagnostic record. Severity and verdict are derived from the code
/// at construction so they cannot disagree with it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutputDiagnostic {
    code: OutputDiagnosticCode,
    severity: DiagnosticSeverity,
    verdict: OutputVerdict,
    field_path: BoundedToken,
    retrieval_output_id: BoundedToken,
    scope_id: BoundedToken,
    safe_id_value: Option<BoundedToken>,
    expected_id: Option<BoundedToken>,
    resolved_id: Option<BoundedToken>,
}

impl OutputDiagnostic {
    /// Create a diagnostic for `code` at `field_path`; severity and verdict are
    /// derived from the code.
    pub fn new(code: OutputDiagnosticCode, field_path: BoundedToken) -> Self {
        Self {
            code,
            severity: code.severity(),
            verdict: code.verdict(),
            field_path,
            retrieval_output_id: BoundedToken::missing(),
            scope_id: BoundedToken::missing(),
            safe_id_value: None,
            expected_id: None,
            resolved_id: None,
        }
    }

    /// Attach the bounded retrieval output ID.
    pub fn with_retrieval_output_id(mut self, value: BoundedToken) -> Self {
        self.retrieval_output_id = value;
        self
    }

    /// Attach the bounded scope ID.
    pub fn with_scope_id(mut self, value: BoundedToken) -> Self {
        self.scope_id = value;
        self
    }

    /// Attach a bounded offending value (never raw payload).
    pub fn with_safe_id_value(mut self, value: BoundedToken) -> Self {
        self.safe_id_value = Some(value);
        self
    }

    /// Attach a bounded expected value.
    pub fn with_expected_id(mut self, value: BoundedToken) -> Self {
        self.expected_id = Some(value);
        self
    }

    /// Attach a bounded resolved value.
    pub fn with_resolved_id(mut self, value: BoundedToken) -> Self {
        self.resolved_id = Some(value);
        self
    }

    /// The diagnostic code.
    pub fn code(&self) -> OutputDiagnosticCode {
        self.code
    }

    /// Severity derived from the code.
    pub fn severity(&self) -> DiagnosticSeverity {
        self.severity
    }

    /// Verdict derived from the code.
    pub fn verdict(&self) -> OutputVerdict {
        self.verdict
    }

    /// The bounded field path the diagnostic points at.
    pub fn field_path(&self) -> &BoundedToken {
        &self.field_path
    }

    /// The bounded retrieval output ID or the `<missing>` sentinel.
    pub fn retrieval_output_id(&self) -> &BoundedToken {
        &self.retrieval_output_id
    }

    /// The bounded scope ID or the `<missing>` sentinel.
    pub fn scope_id(&self) -> &BoundedToken {
        &self.scope_id
    }

    /// The bounded offending value, when one was recorded.
    pub fn safe_id_value(&self) -> Option<&BoundedToken> {
        self.safe_id_value.as_ref()
    }

    /// The bounded expected value, when one was recorded.
    pub fn expected_id(&self) -> Option<&BoundedToken> {
        self.expected_id.as_ref()
    }

    /// The bounded resolved value, when one was recorded.
    pub fn resolved_id(&self) -> Option<&BoundedToken> {
        self.resolved_id.as_ref()
    }
}

// --- outcome --------------------------------------------------------------

/// A validation outcome. Invariants: `rejected` carries at least one error
/// diagnostic; `accepted`/`accepted_scoped_no_answer` carry none.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ValidationOutcome {
    verdict: OutputVerdict,
    diagnostics: Vec<OutputDiagnostic>,
}

/// Error returned when an outcome would violate the outcome invariants.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutcomeInvariantViolation {
    verdict: OutputVerdict,
    reason: &'static str,
}

impl OutcomeInvariantViolation {
    /// The verdict that violated the invariant.
    pub fn verdict(&self) -> OutputVerdict {
        self.verdict
    }

    /// The bounded reason.
    pub fn reason(&self) -> &'static str {
        self.reason
    }
}

impl fmt::Display for OutcomeInvariantViolation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "invalid {} outcome: {}",
            self.verdict.as_str(),
            self.reason
        )
    }
}

impl Error for OutcomeInvariantViolation {}

impl ValidationOutcome {
    /// Build a checked outcome, rejecting an invalid verdict/diagnostic pairing.
    pub fn checked(
        verdict: OutputVerdict,
        diagnostics: Vec<OutputDiagnostic>,
    ) -> Result<Self, OutcomeInvariantViolation> {
        let has_error = diagnostics
            .iter()
            .any(|d| d.severity() == DiagnosticSeverity::Error);
        match verdict {
            OutputVerdict::Rejected if !has_error => {
                return Err(OutcomeInvariantViolation {
                    verdict,
                    reason: "rejected outcome requires an error diagnostic",
                });
            }
            OutputVerdict::Accepted | OutputVerdict::AcceptedScopedNoAnswer if has_error => {
                return Err(OutcomeInvariantViolation {
                    verdict,
                    reason: "accepted outcome must not carry error diagnostics",
                });
            }
            OutputVerdict::Rejected
            | OutputVerdict::Accepted
            | OutputVerdict::AcceptedScopedNoAnswer => {}
        }
        Ok(Self {
            verdict,
            diagnostics,
        })
    }

    /// The outcome verdict.
    pub fn verdict(&self) -> OutputVerdict {
        self.verdict
    }

    /// The bounded diagnostics, in deterministic order.
    pub fn diagnostics(&self) -> &[OutputDiagnostic] {
        &self.diagnostics
    }

    /// True when any diagnostic has error severity.
    pub fn has_error_diagnostics(&self) -> bool {
        self.diagnostics
            .iter()
            .any(|d| d.severity() == DiagnosticSeverity::Error)
    }

    /// The primary code: the first error diagnostic, else the first diagnostic.
    pub fn primary_code(&self) -> Option<OutputDiagnosticCode> {
        self.diagnostics
            .iter()
            .find(|d| d.severity() == DiagnosticSeverity::Error)
            .or_else(|| self.diagnostics.first())
            .map(OutputDiagnostic::code)
    }
}

// --- scope ----------------------------------------------------------------

/// Closed set of required scope fields.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ScopeField {
    ScopeId,
    QueryId,
    RetrievalRunId,
    AsOfDate,
    SourceCorpusId,
    ValidatorContractVersion,
}

impl ScopeField {
    /// Every required scope field, in contract order.
    pub const ALL: [Self; 6] = [
        Self::ScopeId,
        Self::QueryId,
        Self::RetrievalRunId,
        Self::AsOfDate,
        Self::SourceCorpusId,
        Self::ValidatorContractVersion,
    ];

    /// The bounded JSON-pointer/dotted path of the field.
    pub fn field_path(self) -> &'static str {
        match self {
            Self::ScopeId => "scope.scope_id",
            Self::QueryId => "scope.query_id",
            Self::RetrievalRunId => "scope.retrieval_run_id",
            Self::AsOfDate => "scope.as_of_date",
            Self::SourceCorpusId => "scope.source_corpus_id",
            Self::ValidatorContractVersion => "scope.validator_contract_version",
        }
    }
}

/// The left-open wire form of scope metadata.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ObservedScope {
    pub scope_id: FieldShape<OutputScopeId>,
    pub query_id: FieldShape<QueryId>,
    pub retrieval_run_id: FieldShape<RetrievalRunId>,
    pub as_of_date: FieldShape<ScopeAsOfDate>,
    pub source_corpus_id: FieldShape<SourceCorpusId>,
    pub validator_contract_version: FieldShape<ValidatorContractVersion>,
}

impl ObservedScope {
    /// Resolve a complete scope, rejecting any missing, null, or wrong-shaped
    /// field without repairing it.
    pub fn resolve(self) -> Result<OutputScope, ScopeResolutionError> {
        Ok(OutputScope {
            scope_id: required(self.scope_id, ScopeField::ScopeId)?,
            query_id: required(self.query_id, ScopeField::QueryId)?,
            retrieval_run_id: required(self.retrieval_run_id, ScopeField::RetrievalRunId)?,
            as_of_date: required(self.as_of_date, ScopeField::AsOfDate)?,
            source_corpus_id: required(self.source_corpus_id, ScopeField::SourceCorpusId)?,
            validator_contract_version: required(
                self.validator_contract_version,
                ScopeField::ValidatorContractVersion,
            )?,
        })
    }
}

fn required<T>(shape: FieldShape<T>, field: ScopeField) -> Result<T, ScopeResolutionError> {
    match shape {
        FieldShape::Value(value) => Ok(value),
        _ => Err(ScopeResolutionError { field }),
    }
}

/// Error returned when a scope field cannot be resolved.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeResolutionError {
    field: ScopeField,
}

impl ScopeResolutionError {
    /// The field that failed to resolve.
    pub fn field(&self) -> ScopeField {
        self.field
    }

    /// The bounded field path that failed to resolve.
    pub fn field_path(&self) -> &'static str {
        self.field.field_path()
    }
}

impl fmt::Display for ScopeResolutionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "unresolved scope field {}", self.field.field_path())
    }
}

impl Error for ScopeResolutionError {}

/// A complete, validated scope. The constructor requires all six fields.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OutputScope {
    pub scope_id: OutputScopeId,
    pub query_id: QueryId,
    pub retrieval_run_id: RetrievalRunId,
    pub as_of_date: ScopeAsOfDate,
    pub source_corpus_id: SourceCorpusId,
    pub validator_contract_version: ValidatorContractVersion,
}

impl OutputScope {
    /// Build a complete scope from all six required fields.
    pub fn new(
        scope_id: OutputScopeId,
        query_id: QueryId,
        retrieval_run_id: RetrievalRunId,
        as_of_date: ScopeAsOfDate,
        source_corpus_id: SourceCorpusId,
        validator_contract_version: ValidatorContractVersion,
    ) -> Self {
        Self {
            scope_id,
            query_id,
            retrieval_run_id,
            as_of_date,
            source_corpus_id,
            validator_contract_version,
        }
    }

    /// The scope identifier.
    pub fn scope_id(&self) -> &OutputScopeId {
        &self.scope_id
    }
}

/// Left-open shape of the envelope `scope` member.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScopeShape {
    Complete(OutputScope),
    IncompleteField(ScopeField),
    WrongShape,
    Missing,
    ExplicitNull,
}

// --- envelope -------------------------------------------------------------

/// One citation/evidence binding. Each required field keeps missing and explicit
/// null distinct via [`FieldShape`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CitationBinding {
    pub retrieval_output_id: FieldShape<RetrievalOutputId>,
    pub citation_key: FieldShape<CitationKey>,
    pub evidence_span_id: FieldShape<EvidenceSpanId>,
    pub source_block_id: FieldShape<SourceBlockId>,
    pub source_document_id: FieldShape<SourceDocumentId>,
    pub legal_unit_id: FieldShape<LegalUnitId>,
    pub act_edition_id: FieldShape<ActEditionId>,
    pub answer_claim_id: FieldShape<AnswerClaimId>,
}

/// One answer claim referencing supporting citation keys.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnswerClaim {
    pub answer_claim_id: FieldShape<AnswerClaimId>,
    pub retrieval_output_id: FieldShape<RetrievalOutputId>,
    pub claim_kind: FieldShape<ClaimKind>,
    pub scope_id: FieldShape<OutputScopeId>,
    pub supported_citation_keys: FieldShape<Vec<CitationKey>>,
}

/// The retrieval/answer output envelope submitted to the validator.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RetrievalOutputEnvelope {
    pub retrieval_output_id: FieldShape<RetrievalOutputId>,
    pub output_kind: FieldShape<OutputKind>,
    pub scope: ScopeShape,
    pub citations: FieldShape<Vec<CitationBinding>>,
    pub answer_claims: FieldShape<Vec<AnswerClaim>>,
    /// Observed additional wire field names, used for forbidden-payload checks.
    pub extra_field_names: Vec<BoundedToken>,
}

// --- forbidden payload denylist ------------------------------------------

/// Closed denylist of wire field names whose presence is forbidden because the
/// value would carry a non-bounded payload class.
pub const FORBIDDEN_PAYLOAD_FIELD_NAMES: [&str; 12] = [
    "raw_legal_text",
    "raw_source_excerpt",
    "prompt",
    "user_prompt",
    "provider_payload",
    "provider_body",
    "vector",
    "embedding",
    "falkordb_row",
    "runtime_row",
    "secret",
    "credential",
];

/// True when a wire field name matches the closed forbidden-payload denylist.
///
/// Matching is deterministic and case-insensitive, and treats `-` as `_` so a
/// hostile spelling cannot bypass the denylist.
pub fn is_forbidden_payload_field(name: &str) -> bool {
    fn normalize(c: char) -> char {
        if c == '-' {
            '_'
        } else {
            c.to_ascii_lowercase()
        }
    }
    FORBIDDEN_PAYLOAD_FIELD_NAMES.iter().any(|candidate| {
        candidate
            .chars()
            .map(normalize)
            .eq(name.chars().map(normalize))
    })
}

// --- resolution port ------------------------------------------------------

/// How a `citation_key` resolves within a scope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CitationKeyResolution {
    /// The key resolves to exactly one evidence span.
    Unique(EvidenceSpanId),
    /// The key resolves to more than one evidence span.
    Ambiguous,
    /// The key is absent from the resolution graph.
    Unresolved,
}

/// Closed evidence-span lifecycle status in the proof fixture graph.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum EvidenceSpanStatus {
    /// Active, non-superseded evidence.
    Active,
    /// Superseded evidence that must reject for the active scope.
    Superseded,
    /// Deliberately orphaned evidence used for path-failure cases.
    Orphaned,
}

/// A resolved evidence span record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceSpanRecord {
    pub source_block_id: SourceBlockId,
    pub source_document_id: SourceDocumentId,
    pub legal_unit_id: LegalUnitId,
    pub act_edition_id: ActEditionId,
    pub status: EvidenceSpanStatus,
}

/// A resolved source block record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBlockRecord {
    pub source_document_id: SourceDocumentId,
}

/// A resolved source document record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceDocumentRecord {
    pub source_corpus_id: SourceCorpusId,
}

/// A resolved legal unit record.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegalUnitRecord {
    pub act_edition_id: ActEditionId,
    pub legal_act_id: LegalActId,
}

/// A resolved act edition record with its validity window.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ActEditionRecord {
    pub legal_act_id: LegalActId,
    pub valid_from: String,
    pub valid_to: Option<String>,
}

/// Read-only resolution port the validator depends on.
///
/// Implementations resolve envelope IDs to typed graph records. They must not
/// repair, infer, or best-effort match IDs; an unresolved lookup returns `None`
/// and the validator fails closed.
pub trait OutputIdResolutionPort {
    /// Resolve a citation key within a scope.
    fn resolve_citation_key(
        &self,
        scope_id: &OutputScopeId,
        citation_key: &CitationKey,
    ) -> CitationKeyResolution;

    /// Resolve an evidence span to its graph record.
    fn resolve_evidence_span(
        &self,
        evidence_span_id: &EvidenceSpanId,
    ) -> Option<EvidenceSpanRecord>;

    /// Traverse a source block to its declared source document.
    fn resolve_source_block(&self, source_block_id: &SourceBlockId) -> Option<SourceBlockRecord>;

    /// Resolve a declared source document.
    fn resolve_source_document(
        &self,
        source_document_id: &SourceDocumentId,
    ) -> Option<SourceDocumentRecord>;

    /// Resolve a declared legal unit.
    fn resolve_legal_unit(&self, legal_unit_id: &LegalUnitId) -> Option<LegalUnitRecord>;

    /// Resolve a declared act edition.
    fn resolve_act_edition(&self, act_edition_id: &ActEditionId) -> Option<ActEditionRecord>;

    /// The edition valid for a legal unit at a scope as-of date.
    fn resolve_valid_edition(
        &self,
        legal_unit_id: &LegalUnitId,
        as_of_date: &ScopeAsOfDate,
    ) -> Option<ActEditionId>;

    /// Whether an evidence span is superseded for a scope as-of date.
    fn is_superseded(&self, evidence_span_id: &EvidenceSpanId, as_of_date: &ScopeAsOfDate) -> bool;
}

// --- in-memory fixture resolver ------------------------------------------

/// Serde-free in-memory resolution adapter holding the M012 proof fixture
/// topology. It is synthetic proof-local data, not a production schema.
#[derive(Debug, Clone, Default)]
pub struct FixtureGraphResolver {
    citation_bindings: HashMap<(OutputScopeId, CitationKey), Vec<EvidenceSpanId>>,
    evidence_spans: HashMap<EvidenceSpanId, EvidenceSpanRecord>,
    source_blocks: HashMap<SourceBlockId, SourceBlockRecord>,
    source_documents: HashMap<SourceDocumentId, SourceDocumentRecord>,
    legal_units: HashMap<LegalUnitId, LegalUnitRecord>,
    act_editions: HashMap<ActEditionId, ActEditionRecord>,
}

impl FixtureGraphResolver {
    /// Build the resolver populated with the M012 fixture topology.
    pub fn m012() -> Self {
        let mut resolver = Self::default();

        // Source documents (proof-local anchors; no raw text or provider body).
        resolver.add_source_document("SD-M012-44FZ-CONSULTANT", "CORPUS-M012-FIXTURE");
        resolver.add_source_document("SD-M012-44FZ-GARANT", "CORPUS-M012-FIXTURE");

        // Source blocks; the orphan block points at an undeclared document.
        resolver.add_source_block("SB-M012-001", "SD-M012-44FZ-CONSULTANT");
        resolver.add_source_block("SB-M012-002", "SD-M012-44FZ-GARANT");
        resolver.add_source_block("SB-M012-ORPHAN", "SD-M012-MISSING-DOCUMENT");

        // Act editions for the synthetic 44-FZ anchor.
        resolver.add_act_edition(
            "ED-M012-44FZ-2024-01-01",
            "LA-M012-44FZ",
            "2024-01-01",
            None,
        );
        resolver.add_act_edition(
            "ED-M012-44FZ-2023-01-01",
            "LA-M012-44FZ",
            "2023-01-01",
            Some("2023-12-31"),
        );

        // Legal units; the OLD unit belongs to the superseded 2023 edition.
        resolver.add_legal_unit(
            "LU-M012-44FZ-ART-001",
            "LA-M012-44FZ",
            "ED-M012-44FZ-2024-01-01",
        );
        resolver.add_legal_unit(
            "LU-M012-44FZ-ART-001-OLD",
            "LA-M012-44FZ",
            "ED-M012-44FZ-2023-01-01",
        );

        // Evidence spans, including superseded and deliberately orphaned rows.
        resolver.add_evidence_span(
            "EV-M012-001",
            "SB-M012-001",
            "SD-M012-44FZ-CONSULTANT",
            "LU-M012-44FZ-ART-001",
            "ED-M012-44FZ-2024-01-01",
            EvidenceSpanStatus::Active,
        );
        resolver.add_evidence_span(
            "EV-M012-002",
            "SB-M012-002",
            "SD-M012-44FZ-GARANT",
            "LU-M012-44FZ-ART-001",
            "ED-M012-44FZ-2024-01-01",
            EvidenceSpanStatus::Active,
        );
        resolver.add_evidence_span(
            "EV-M012-SUPERSEDED",
            "SB-M012-001",
            "SD-M012-44FZ-CONSULTANT",
            "LU-M012-44FZ-ART-001-OLD",
            "ED-M012-44FZ-2023-01-01",
            EvidenceSpanStatus::Superseded,
        );
        resolver.add_evidence_span(
            "EV-M012-ORPHAN-SOURCE",
            "SB-M012-ORPHAN",
            "SD-M012-MISSING-DOCUMENT",
            "LU-M012-44FZ-ART-001",
            "ED-M012-44FZ-2024-01-01",
            EvidenceSpanStatus::Orphaned,
        );
        resolver.add_evidence_span(
            "EV-M012-ORPHAN-LEGAL",
            "SB-M012-002",
            "SD-M012-44FZ-GARANT",
            "LU-M012-MISSING-UNIT",
            "ED-M012-44FZ-2024-01-01",
            EvidenceSpanStatus::Orphaned,
        );

        // Citation bindings; CIT-M012-AMBIG resolves to two evidence spans.
        resolver.add_citation_binding("SCOPE-M012-44FZ-2024-001", "CIT-M012-001", "EV-M012-001");
        resolver.add_citation_binding("SCOPE-M012-44FZ-2024-001", "CIT-M012-002", "EV-M012-002");
        resolver.add_citation_binding("SCOPE-M012-44FZ-2024-001", "CIT-M012-AMBIG", "EV-M012-001");
        resolver.add_citation_binding("SCOPE-M012-44FZ-2024-001", "CIT-M012-AMBIG", "EV-M012-002");
        resolver.add_citation_binding(
            "SCOPE-M012-44FZ-2024-001",
            "CIT-M012-SUPERSEDED",
            "EV-M012-SUPERSEDED",
        );
        resolver.add_citation_binding(
            "SCOPE-M012-44FZ-2024-001",
            "CIT-M012-ORPHAN-SOURCE",
            "EV-M012-ORPHAN-SOURCE",
        );
        resolver.add_citation_binding(
            "SCOPE-M012-44FZ-2024-001",
            "CIT-M012-ORPHAN-LEGAL",
            "EV-M012-ORPHAN-LEGAL",
        );

        resolver
    }

    fn add_source_document(&mut self, id: &str, corpus_id: &str) {
        self.source_documents.insert(
            SourceDocumentId::parse(id).expect("fixture source document id"),
            SourceDocumentRecord {
                source_corpus_id: SourceCorpusId::parse(corpus_id).expect("fixture corpus id"),
            },
        );
    }

    fn add_source_block(&mut self, id: &str, document_id: &str) {
        self.source_blocks.insert(
            SourceBlockId::parse(id).expect("fixture source block id"),
            SourceBlockRecord {
                source_document_id: SourceDocumentId::parse(document_id)
                    .expect("fixture source document id"),
            },
        );
    }

    fn add_act_edition(
        &mut self,
        id: &str,
        legal_act_id: &str,
        valid_from: &str,
        valid_to: Option<&str>,
    ) {
        self.act_editions.insert(
            ActEditionId::parse(id).expect("fixture act edition id"),
            ActEditionRecord {
                legal_act_id: LegalActId::parse(legal_act_id).expect("fixture legal act id"),
                valid_from: valid_from.to_owned(),
                valid_to: valid_to.map(str::to_owned),
            },
        );
    }

    fn add_legal_unit(&mut self, id: &str, legal_act_id: &str, act_edition_id: &str) {
        self.legal_units.insert(
            LegalUnitId::parse(id).expect("fixture legal unit id"),
            LegalUnitRecord {
                act_edition_id: ActEditionId::parse(act_edition_id)
                    .expect("fixture act edition id"),
                legal_act_id: LegalActId::parse(legal_act_id).expect("fixture legal act id"),
            },
        );
    }

    fn add_evidence_span(
        &mut self,
        id: &str,
        source_block_id: &str,
        source_document_id: &str,
        legal_unit_id: &str,
        act_edition_id: &str,
        status: EvidenceSpanStatus,
    ) {
        self.evidence_spans.insert(
            EvidenceSpanId::parse(id).expect("fixture evidence span id"),
            EvidenceSpanRecord {
                source_block_id: SourceBlockId::parse(source_block_id)
                    .expect("fixture source block id"),
                source_document_id: SourceDocumentId::parse(source_document_id)
                    .expect("fixture source document id"),
                legal_unit_id: LegalUnitId::parse(legal_unit_id).expect("fixture legal unit id"),
                act_edition_id: ActEditionId::parse(act_edition_id)
                    .expect("fixture act edition id"),
                status,
            },
        );
    }

    fn add_citation_binding(&mut self, scope_id: &str, citation_key: &str, evidence_span_id: &str) {
        self.citation_bindings
            .entry((
                OutputScopeId::parse(scope_id).expect("fixture scope id"),
                CitationKey::parse(citation_key).expect("fixture citation key"),
            ))
            .or_default()
            .push(EvidenceSpanId::parse(evidence_span_id).expect("fixture evidence span id"));
    }
}

impl OutputIdResolutionPort for FixtureGraphResolver {
    fn resolve_citation_key(
        &self,
        scope_id: &OutputScopeId,
        citation_key: &CitationKey,
    ) -> CitationKeyResolution {
        match self
            .citation_bindings
            .get(&(scope_id.clone(), citation_key.clone()))
            .map(Vec::as_slice)
        {
            Some([only]) => CitationKeyResolution::Unique(only.clone()),
            Some(_) => CitationKeyResolution::Ambiguous,
            None => CitationKeyResolution::Unresolved,
        }
    }

    fn resolve_evidence_span(
        &self,
        evidence_span_id: &EvidenceSpanId,
    ) -> Option<EvidenceSpanRecord> {
        self.evidence_spans.get(evidence_span_id).cloned()
    }

    fn resolve_source_block(&self, source_block_id: &SourceBlockId) -> Option<SourceBlockRecord> {
        self.source_blocks.get(source_block_id).cloned()
    }

    fn resolve_source_document(
        &self,
        source_document_id: &SourceDocumentId,
    ) -> Option<SourceDocumentRecord> {
        self.source_documents.get(source_document_id).cloned()
    }

    fn resolve_legal_unit(&self, legal_unit_id: &LegalUnitId) -> Option<LegalUnitRecord> {
        self.legal_units.get(legal_unit_id).cloned()
    }

    fn resolve_act_edition(&self, act_edition_id: &ActEditionId) -> Option<ActEditionRecord> {
        self.act_editions.get(act_edition_id).cloned()
    }

    fn resolve_valid_edition(
        &self,
        legal_unit_id: &LegalUnitId,
        as_of_date: &ScopeAsOfDate,
    ) -> Option<ActEditionId> {
        let unit = self.legal_units.get(legal_unit_id)?;
        let edition = self.act_editions.get(&unit.act_edition_id)?;
        if date_in_validity_window(as_of_date.as_str(), edition) {
            Some(unit.act_edition_id.clone())
        } else {
            None
        }
    }

    fn is_superseded(
        &self,
        evidence_span_id: &EvidenceSpanId,
        _as_of_date: &ScopeAsOfDate,
    ) -> bool {
        self.evidence_spans
            .get(evidence_span_id)
            .map(|record| record.status == EvidenceSpanStatus::Superseded)
            .unwrap_or(false)
    }
}

/// True when `as_of` falls inside a record's inclusive validity window. ISO-8601
/// date strings compare lexicographically, so no date dependency is required.
fn date_in_validity_window(as_of: &str, edition: &ActEditionRecord) -> bool {
    as_of >= edition.valid_from.as_str()
        && edition
            .valid_to
            .as_deref()
            .is_none_or(|valid_to| as_of <= valid_to)
}

// --- validator ------------------------------------------------------------

/// Bounded diagnostic context derived from the envelope, never from payloads.
struct DiagnosticContext {
    retrieval_output_id: BoundedToken,
    scope_id: BoundedToken,
}

impl DiagnosticContext {
    fn from_envelope(envelope: &RetrievalOutputEnvelope) -> Self {
        let retrieval_output_id = envelope
            .retrieval_output_id
            .value()
            .map(|value| bounded_token(value.as_str()))
            .unwrap_or_else(BoundedToken::missing);
        let scope_id = match &envelope.scope {
            ScopeShape::Complete(scope) => bounded_token(scope.scope_id.as_str()),
            _ => BoundedToken::missing(),
        };
        Self {
            retrieval_output_id,
            scope_id,
        }
    }
}

fn bounded_token(value: &str) -> BoundedToken {
    BoundedToken::parse(value).unwrap_or_else(|_| BoundedToken::missing())
}

fn diagnostic(
    ctx: &DiagnosticContext,
    code: OutputDiagnosticCode,
    field_path: &str,
) -> OutputDiagnostic {
    OutputDiagnostic::new(code, bounded_token(field_path))
        .with_retrieval_output_id(ctx.retrieval_output_id.clone())
        .with_scope_id(ctx.scope_id.clone())
}

fn reject(diagnostic: OutputDiagnostic) -> ValidationOutcome {
    ValidationOutcome::checked(OutputVerdict::Rejected, vec![diagnostic])
        .expect("rejected outcome carries an error diagnostic")
}

fn accept() -> ValidationOutcome {
    ValidationOutcome::checked(OutputVerdict::Accepted, Vec::new())
        .expect("accepted outcome carries no error diagnostics")
}

fn accept_scoped_no_answer(diagnostic: OutputDiagnostic) -> ValidationOutcome {
    ValidationOutcome::checked(OutputVerdict::AcceptedScopedNoAnswer, vec![diagnostic])
        .expect("scoped no-answer carries an info diagnostic")
}

fn value_or_empty<T>(shape: &FieldShape<Vec<T>>) -> &[T] {
    match shape {
        FieldShape::Value(values) => values.as_slice(),
        FieldShape::ExplicitNull | FieldShape::Missing | FieldShape::WrongShape => &[],
    }
}

/// Validate a retrieval/answer output envelope against a resolution port.
///
/// The validator borrows the envelope and never mutates it (no-repair
/// invariant). Rules run in the fixed contract order; the first failing rule
/// produces exactly one primary diagnostic, so identical input yields an
/// identical outcome.
pub fn validate_retrieval_output<P>(
    envelope: &RetrievalOutputEnvelope,
    resolver: &P,
) -> ValidationOutcome
where
    P: OutputIdResolutionPort + ?Sized,
{
    let ctx = DiagnosticContext::from_envelope(envelope);

    // Rule 1: envelope shape.
    if let Some(diagnostic) = check_shape(envelope, &ctx) {
        return reject(diagnostic);
    }
    // Rule 2: missing required fields.
    if let Some(diagnostic) = check_missing_required(envelope, &ctx) {
        return reject(diagnostic);
    }
    // Rule 3: forbidden payload field names.
    if let Some(diagnostic) = check_forbidden_payload(envelope, &ctx) {
        return reject(diagnostic);
    }
    // Rule 4: unknown ID namespace.
    if let Some(diagnostic) = check_namespaces(envelope, &ctx) {
        return reject(diagnostic);
    }

    let citations = value_or_empty(&envelope.citations);

    // Rules 5-10: per-citation resolution, traversal, and temporal validity.
    for (index, citation) in citations.iter().enumerate() {
        if let Some(diagnostic) = check_citation(index, citation, envelope, &ctx, resolver) {
            return reject(diagnostic);
        }
    }

    // Rule 11: answer claims.
    if let Some(diagnostic) = check_answer_claims(envelope, citations, &ctx) {
        return reject(diagnostic);
    }
    // Rule 12: citation without evidence.
    if let Some(diagnostic) = check_citation_without_evidence(citations, &ctx) {
        return reject(diagnostic);
    }

    // Rules 13-14: no-answer shape and acceptance.
    if matches!(
        envelope.output_kind.value(),
        Some(OutputKind::ScopedNoAnswer)
    ) {
        let has_claims =
            matches!(&envelope.answer_claims, FieldShape::Value(claims) if !claims.is_empty());
        if !citations.is_empty() || has_claims {
            return reject(diagnostic(
                &ctx,
                OutputDiagnosticCode::UnsafeNoAnswerShape,
                "citations",
            ));
        }
        return accept_scoped_no_answer(diagnostic(
            &ctx,
            OutputDiagnosticCode::ScopedNoAnswer,
            "citations",
        ));
    }

    accept()
}

fn check_shape(
    envelope: &RetrievalOutputEnvelope,
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    let checks = [
        (
            envelope.retrieval_output_id.is_wrong_shape(),
            "retrieval_output_id",
        ),
        (envelope.output_kind.is_wrong_shape(), "output_kind"),
        (matches!(envelope.scope, ScopeShape::WrongShape), "scope"),
        (envelope.citations.is_wrong_shape(), "citations"),
        (envelope.answer_claims.is_wrong_shape(), "answer_claims"),
    ];
    for (wrong, path) in checks {
        if wrong {
            return Some(diagnostic(
                ctx,
                OutputDiagnosticCode::MalformedOutputShape,
                path,
            ));
        }
    }
    None
}

fn check_missing_required(
    envelope: &RetrievalOutputEnvelope,
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    if envelope.retrieval_output_id.is_absent_or_null() {
        return Some(diagnostic(
            ctx,
            OutputDiagnosticCode::MissingRequiredField,
            "retrieval_output_id",
        ));
    }
    if envelope.output_kind.is_absent_or_null() {
        return Some(diagnostic(
            ctx,
            OutputDiagnosticCode::MissingRequiredField,
            "output_kind",
        ));
    }
    match &envelope.scope {
        ScopeShape::Missing | ScopeShape::ExplicitNull => {
            return Some(diagnostic(
                ctx,
                OutputDiagnosticCode::MissingRequiredField,
                "scope",
            ));
        }
        ScopeShape::IncompleteField(field) => {
            return Some(diagnostic(
                ctx,
                OutputDiagnosticCode::MissingRequiredField,
                field.field_path(),
            ));
        }
        ScopeShape::Complete(_) | ScopeShape::WrongShape => {}
    }
    if envelope.citations.is_absent_or_null() {
        return Some(diagnostic(
            ctx,
            OutputDiagnosticCode::MissingRequiredField,
            "citations",
        ));
    }
    if let FieldShape::Value(citations) = &envelope.citations {
        for (index, citation) in citations.iter().enumerate() {
            let checks = [
                (
                    citation.retrieval_output_id.is_absent_or_null(),
                    "retrieval_output_id",
                ),
                (citation.citation_key.is_absent_or_null(), "citation_key"),
                (citation.evidence_span_id.is_missing(), "evidence_span_id"),
                (
                    citation.source_block_id.is_absent_or_null(),
                    "source_block_id",
                ),
                (
                    citation.source_document_id.is_absent_or_null(),
                    "source_document_id",
                ),
                (citation.legal_unit_id.is_absent_or_null(), "legal_unit_id"),
                (
                    citation.act_edition_id.is_absent_or_null(),
                    "act_edition_id",
                ),
            ];
            for (missing, name) in checks {
                if missing {
                    return Some(diagnostic(
                        ctx,
                        OutputDiagnosticCode::MissingRequiredField,
                        &format!("citations[{index}].{name}"),
                    ));
                }
            }
        }
    }
    if let FieldShape::Value(claims) = &envelope.answer_claims {
        for (index, claim) in claims.iter().enumerate() {
            let checks = [
                (claim.answer_claim_id.is_absent_or_null(), "answer_claim_id"),
                (
                    claim.retrieval_output_id.is_absent_or_null(),
                    "retrieval_output_id",
                ),
                (claim.claim_kind.is_absent_or_null(), "claim_kind"),
                (claim.scope_id.is_absent_or_null(), "scope_id"),
                (
                    claim.supported_citation_keys.is_missing(),
                    "supported_citation_keys",
                ),
            ];
            for (missing, name) in checks {
                if missing {
                    return Some(diagnostic(
                        ctx,
                        OutputDiagnosticCode::MissingRequiredField,
                        &format!("answer_claims[{index}].{name}"),
                    ));
                }
            }
        }
    }
    None
}

fn check_forbidden_payload(
    envelope: &RetrievalOutputEnvelope,
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    for name in &envelope.extra_field_names {
        if is_forbidden_payload_field(name.as_str()) {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::ForbiddenPayloadField,
                    name.as_str(),
                )
                .with_safe_id_value(name.clone()),
            );
        }
    }
    None
}

fn check_namespace(
    ctx: &DiagnosticContext,
    field_path: &str,
    token: &str,
    expected: Option<&'static str>,
) -> Option<OutputDiagnostic> {
    let expected = expected?;
    if token.starts_with(expected) {
        return None;
    }
    Some(
        diagnostic(ctx, OutputDiagnosticCode::UnknownIdNamespace, field_path)
            .with_safe_id_value(bounded_token(token)),
    )
}

macro_rules! check_namespace_shape {
    ($ctx:expr, $path:expr, $shape:expr, $ty:ty) => {
        if let Some(value) = $shape.value() {
            if let Some(diagnostic) =
                check_namespace($ctx, $path, value.as_str(), <$ty>::NAMESPACE_PREFIX)
            {
                return Some(diagnostic);
            }
        }
    };
}

fn check_namespaces(
    envelope: &RetrievalOutputEnvelope,
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    check_namespace_shape!(
        ctx,
        "retrieval_output_id",
        envelope.retrieval_output_id,
        RetrievalOutputId
    );
    if let ScopeShape::Complete(scope) = &envelope.scope {
        if let Some(diagnostic) = check_namespace(
            ctx,
            "scope.scope_id",
            scope.scope_id.as_str(),
            OutputScopeId::NAMESPACE_PREFIX,
        ) {
            return Some(diagnostic);
        }
        if let Some(diagnostic) = check_namespace(
            ctx,
            "scope.retrieval_run_id",
            scope.retrieval_run_id.as_str(),
            RetrievalRunId::NAMESPACE_PREFIX,
        ) {
            return Some(diagnostic);
        }
        if let Some(diagnostic) = check_namespace(
            ctx,
            "scope.source_corpus_id",
            scope.source_corpus_id.as_str(),
            SourceCorpusId::NAMESPACE_PREFIX,
        ) {
            return Some(diagnostic);
        }
    }
    if let FieldShape::Value(citations) = &envelope.citations {
        for (index, citation) in citations.iter().enumerate() {
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].citation_key"),
                citation.citation_key,
                CitationKey
            );
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].evidence_span_id"),
                citation.evidence_span_id,
                EvidenceSpanId
            );
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].source_block_id"),
                citation.source_block_id,
                SourceBlockId
            );
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].source_document_id"),
                citation.source_document_id,
                SourceDocumentId
            );
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].legal_unit_id"),
                citation.legal_unit_id,
                LegalUnitId
            );
            check_namespace_shape!(
                ctx,
                &format!("citations[{index}].act_edition_id"),
                citation.act_edition_id,
                ActEditionId
            );
        }
    }
    if let FieldShape::Value(claims) = &envelope.answer_claims {
        for (index, claim) in claims.iter().enumerate() {
            check_namespace_shape!(
                ctx,
                &format!("answer_claims[{index}].answer_claim_id"),
                claim.answer_claim_id,
                AnswerClaimId
            );
        }
    }
    None
}

fn check_citation<P>(
    index: usize,
    citation: &CitationBinding,
    envelope: &RetrievalOutputEnvelope,
    ctx: &DiagnosticContext,
    resolver: &P,
) -> Option<OutputDiagnostic>
where
    P: OutputIdResolutionPort + ?Sized,
{
    let scope = match &envelope.scope {
        ScopeShape::Complete(scope) => scope,
        _ => return None,
    };

    // Rule 5: citation key resolution.
    if let Some(citation_key) = citation.citation_key.value() {
        match resolver.resolve_citation_key(&scope.scope_id, citation_key) {
            CitationKeyResolution::Unresolved => {
                return Some(
                    diagnostic(
                        ctx,
                        OutputDiagnosticCode::UnresolvedCitationKey,
                        &format!("citations[{index}].citation_key"),
                    )
                    .with_safe_id_value(bounded_token(citation_key.as_str())),
                );
            }
            CitationKeyResolution::Ambiguous => {
                return Some(
                    diagnostic(
                        ctx,
                        OutputDiagnosticCode::AmbiguousCitationKey,
                        &format!("citations[{index}].citation_key"),
                    )
                    .with_safe_id_value(bounded_token(citation_key.as_str())),
                );
            }
            CitationKeyResolution::Unique(_) => {}
        }
    }

    // Rule 6: evidence span resolution. Missing is handled by rule 2 and an
    // explicit null is deferred to rule 12.
    let evidence_span_id = citation.evidence_span_id.value()?;
    let record = match resolver.resolve_evidence_span(evidence_span_id) {
        Some(record) => record,
        None => {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::UnresolvedEvidenceSpan,
                    &format!("citations[{index}].evidence_span_id"),
                )
                .with_safe_id_value(bounded_token(evidence_span_id.as_str())),
            );
        }
    };

    // Rule 7: superseded evidence is rejected before the edition check.
    if resolver.is_superseded(evidence_span_id, &scope.as_of_date) {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::SupersededEvidence,
                &format!("citations[{index}].evidence_span_id"),
            )
            .with_safe_id_value(bounded_token(evidence_span_id.as_str())),
        );
    }

    // Rule 8: source path traversal and explicit-ID comparison.
    if let (Some(explicit), Some(parent)) = (
        citation.retrieval_output_id.value(),
        envelope.retrieval_output_id.value(),
    ) {
        if explicit != parent {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::IdPathMismatch,
                    &format!("citations[{index}].retrieval_output_id"),
                )
                .with_expected_id(bounded_token(parent.as_str()))
                .with_resolved_id(bounded_token(explicit.as_str())),
            );
        }
    }
    if citation.source_block_id.value() != Some(&record.source_block_id) {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::IdPathMismatch,
                &format!("citations[{index}].source_block_id"),
            )
            .with_expected_id(bounded_token(record.source_block_id.as_str()))
            .with_resolved_id(
                citation
                    .source_block_id
                    .value()
                    .map(|value| bounded_token(value.as_str()))
                    .unwrap_or_else(BoundedToken::missing),
            ),
        );
    }
    let reached_document = match resolver.resolve_source_block(&record.source_block_id) {
        Some(block) => block.source_document_id,
        None => {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::OrphanedSourcePath,
                    &format!("citations[{index}].source_block_id"),
                )
                .with_safe_id_value(bounded_token(record.source_block_id.as_str())),
            );
        }
    };
    if resolver
        .resolve_source_document(&reached_document)
        .is_none()
    {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::OrphanedSourcePath,
                &format!("citations[{index}].source_document_id"),
            )
            .with_safe_id_value(bounded_token(record.source_block_id.as_str()))
            .with_resolved_id(bounded_token(reached_document.as_str())),
        );
    }
    if record.source_document_id != reached_document {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::IdPathMismatch,
                &format!("citations[{index}].source_document_id"),
            )
            .with_expected_id(bounded_token(reached_document.as_str()))
            .with_resolved_id(bounded_token(record.source_document_id.as_str())),
        );
    }
    if citation.source_document_id.value() != Some(&reached_document) {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::IdPathMismatch,
                &format!("citations[{index}].source_document_id"),
            )
            .with_expected_id(bounded_token(reached_document.as_str()))
            .with_resolved_id(
                citation
                    .source_document_id
                    .value()
                    .map(|value| bounded_token(value.as_str()))
                    .unwrap_or_else(BoundedToken::missing),
            ),
        );
    }

    // Rule 9: legal path traversal.
    if citation.legal_unit_id.value() != Some(&record.legal_unit_id) {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::IdPathMismatch,
                &format!("citations[{index}].legal_unit_id"),
            )
            .with_expected_id(bounded_token(record.legal_unit_id.as_str()))
            .with_resolved_id(
                citation
                    .legal_unit_id
                    .value()
                    .map(|value| bounded_token(value.as_str()))
                    .unwrap_or_else(BoundedToken::missing),
            ),
        );
    }
    let legal_unit = match resolver.resolve_legal_unit(&record.legal_unit_id) {
        Some(legal_unit) => legal_unit,
        None => {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::OrphanedLegalUnitPath,
                    &format!("citations[{index}].legal_unit_id"),
                )
                .with_safe_id_value(bounded_token(record.legal_unit_id.as_str())),
            );
        }
    };

    // Rule 10: edition validity for the scoped date.
    let valid_edition =
        match resolver.resolve_valid_edition(&record.legal_unit_id, &scope.as_of_date) {
            Some(edition) => edition,
            None => {
                return Some(
                    diagnostic(
                        ctx,
                        OutputDiagnosticCode::WrongEdition,
                        &format!("citations[{index}].act_edition_id"),
                    )
                    .with_safe_id_value(bounded_token(record.act_edition_id.as_str())),
                );
            }
        };
    if citation.act_edition_id.value() != Some(&valid_edition) {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::WrongEdition,
                &format!("citations[{index}].act_edition_id"),
            )
            .with_safe_id_value(
                citation
                    .act_edition_id
                    .value()
                    .map(|value| bounded_token(value.as_str()))
                    .unwrap_or_else(BoundedToken::missing),
            )
            .with_expected_id(bounded_token(valid_edition.as_str())),
        );
    }
    if record.act_edition_id != valid_edition {
        return Some(
            diagnostic(
                ctx,
                OutputDiagnosticCode::WrongEdition,
                &format!("citations[{index}].act_edition_id"),
            )
            .with_safe_id_value(bounded_token(record.act_edition_id.as_str()))
            .with_expected_id(bounded_token(valid_edition.as_str())),
        );
    }
    match resolver.resolve_act_edition(&valid_edition) {
        Some(edition) => {
            if edition.legal_act_id != legal_unit.legal_act_id {
                return Some(
                    diagnostic(
                        ctx,
                        OutputDiagnosticCode::IdPathMismatch,
                        &format!("citations[{index}].act_edition_id"),
                    )
                    .with_expected_id(bounded_token(legal_unit.legal_act_id.as_str()))
                    .with_resolved_id(bounded_token(edition.legal_act_id.as_str())),
                );
            }
        }
        None => {
            return Some(
                diagnostic(
                    ctx,
                    OutputDiagnosticCode::OrphanedLegalUnitPath,
                    &format!("citations[{index}].act_edition_id"),
                )
                .with_safe_id_value(bounded_token(valid_edition.as_str())),
            );
        }
    }

    None
}

fn check_answer_claims(
    envelope: &RetrievalOutputEnvelope,
    citations: &[CitationBinding],
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    let claims = match &envelope.answer_claims {
        FieldShape::Value(claims) if !claims.is_empty() => claims.as_slice(),
        _ => return None,
    };
    let mut available_keys: HashSet<&str> = HashSet::new();
    for citation in citations {
        if let Some(key) = citation.citation_key.value() {
            available_keys.insert(key.as_str());
        }
    }
    for (index, claim) in claims.iter().enumerate() {
        let field_path = format!("answer_claims[{index}].supported_citation_keys");
        let supported = match claim.supported_citation_keys.value() {
            Some(supported) => supported,
            None => {
                return Some(diagnostic(
                    ctx,
                    OutputDiagnosticCode::AnswerClaimWithoutEvidence,
                    &field_path,
                ));
            }
        };
        if supported.is_empty()
            || supported
                .iter()
                .any(|key| !available_keys.contains(key.as_str()))
        {
            return Some(diagnostic(
                ctx,
                OutputDiagnosticCode::AnswerClaimWithoutEvidence,
                &field_path,
            ));
        }
    }
    None
}

fn check_citation_without_evidence(
    citations: &[CitationBinding],
    ctx: &DiagnosticContext,
) -> Option<OutputDiagnostic> {
    for (index, citation) in citations.iter().enumerate() {
        if citation.evidence_span_id.is_explicit_null() {
            return Some(diagnostic(
                ctx,
                OutputDiagnosticCode::CitationWithoutEvidence,
                &format!("citations[{index}].evidence_span_id"),
            ));
        }
    }
    None
}
