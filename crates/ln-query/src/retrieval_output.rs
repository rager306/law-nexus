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
    ($name:ident, $kind:literal) => {
        #[doc = concat!("Envelope identifier token (`", $kind, "`).")]
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);

        impl $name {
            /// Fail-closed parse: rejects empty, over-long, or unsupported input.
            pub fn parse(value: &str) -> Result<Self, OutputIdError> {
                parse_id_value($kind, value).map(Self)
            }

            /// The raw identifier string.
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }

        impl fmt::Display for $name {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                f.write_str(&self.0)
            }
        }
    };
}

output_id_type!(RetrievalOutputId, "retrieval output id");
output_id_type!(CitationKey, "citation key");
output_id_type!(EvidenceSpanId, "evidence span id");
output_id_type!(SourceBlockId, "source block id");
output_id_type!(SourceDocumentId, "source document id");
output_id_type!(LegalUnitId, "legal unit id");
output_id_type!(ActEditionId, "act edition id");
output_id_type!(AnswerClaimId, "answer claim id");
output_id_type!(OutputScopeId, "output scope id");
output_id_type!(RetrievalRunId, "retrieval run id");
output_id_type!(SourceCorpusId, "source corpus id");
output_id_type!(ScopeAsOfDate, "scope as-of date");

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
