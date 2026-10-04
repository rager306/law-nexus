//! M214-es3jvw S02 T04: document-scoped analysis JSONL envelope and
//! structure-only inspect.
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8A:
//! the T02/T03 record streams become a LF-delimited JSONL envelope
//! (`manifest → policies → records → footer`) with a pinned parent identity,
//! two non-cyclic recomputable seals, a closed completion marker and a
//! count/hash-only text channel. [`inspect_npa_analysis_wire`] is
//! **structure-only**: it reports families, counts, completion and seal
//! presence, never reconstructs a record and never recomputes a seal (that is
//! S03's read-back verifier).
//!
//! Scope is the seven families (§8A.1 + §8B.1): the six S02 families plus the
//! opt-in `context` family (S03 T03, D662). No second coordinate system is
//! minted and no analyzer module is touched: record streams come from
//! [`crate::npa_analysis_records`] and [`crate::npa_context_records`], and the
//! structural predicates are reused from [`crate::analysis_source_mapping`].

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;
use std::fmt::Write as _;

use sha2::{Digest, Sha256};

use crate::analysis_source_mapping::{
    check_envelope_shape, check_no_corpus_transfer, check_temporal_fields, EnvelopeLineKind,
    EnvelopeLineShape, SourceMapping,
};
use crate::document_context::ContextStatus;
use crate::npa_analysis_records::{
    ClassificationRecord, DiagnosticRecord, DocumentAnalysis, LinkedMemberRecord, RelationRecord,
    SourceRef, TypedMemberRecord,
};
use crate::npa_anchor::RejectReason;
use crate::npa_context_records::{
    claim_derivation_token, claim_status_token, derivation_relation_token,
    diagnostic_token as context_diagnostic_token, edge_status_token, request_kind_token,
    status_token, ContextClaimRecord, ContextDerivationRecord, ContextRecord, ContextResultRecord,
    ContextRunRecord, KIND_RESULT, KIND_RUN,
};
use crate::npa_link::{LinkDerivation, LinkedMemberKind, LinkedRelationKind};
use crate::npa_typed::TypeDerivation;
use crate::reader_contract::{FragmentRef, ReaderRecordIndex};
use crate::reader_projection::ReaderProjection;

// ------------------------------------------------------------ constants #

/// Manifest `capability` token.
pub const CAPABILITY: &str = "npa_analysis_jsonl";
/// Manifest `model` token.
pub const MODEL: &str = "law-nexus/npa-analysis-model/v1";
/// Manifest `profile` token.
pub const PROFILE: &str = "npa_analysis_wordml/v1";
/// Manifest `version`.
pub const CONTRACT_VERSION: u64 = 1;
/// Manifest generator name.
pub const GENERATOR_NAME: &str = "ln-decode.npa_analysis_wire";
/// Manifest generator version.
pub const GENERATOR_VERSION: &str = env!("CARGO_PKG_VERSION");

/// Manifest line kind.
pub const KIND_MANIFEST: &str = "npa_analysis_manifest";
/// Policies line kind.
pub const KIND_POLICIES: &str = "npa_analysis_policies";
/// Footer line kind.
pub const KIND_FOOTER: &str = "npa_analysis_footer";

/// Manifest schema tag.
pub const SCHEMA_MANIFEST: &str = "law-nexus/npa-analysis-manifest/v1";
/// Policies schema tag.
pub const SCHEMA_POLICIES: &str = "law-nexus/npa-analysis-policies/v1";
/// Footer schema tag.
pub const SCHEMA_FOOTER: &str = "law-nexus/npa-analysis-footer/v1";
/// Document record schema tag.
pub const SCHEMA_DOCUMENT: &str = "law-nexus/npa-analysis-document/v1";
/// Fragment record schema tag.
pub const SCHEMA_FRAGMENT: &str = "law-nexus/npa-analysis-fragment/v1";
/// Member record schema tag.
pub const SCHEMA_MEMBER: &str = "law-nexus/npa-analysis-member/v1";
/// Relation record schema tag.
pub const SCHEMA_RELATION: &str = "law-nexus/npa-analysis-relation/v1";
/// Classification record schema tag.
pub const SCHEMA_CLASSIFICATION: &str = "law-nexus/npa-analysis-classification/v1";
/// Diagnostic record schema tag.
pub const SCHEMA_DIAGNOSTIC: &str = "law-nexus/npa-analysis-diagnostic/v1";

/// `document` family token.
pub const FAMILY_DOCUMENT: &str = "document";
/// `fragment` family token.
pub const FAMILY_FRAGMENT: &str = "fragment";
/// `member` family token.
pub const FAMILY_MEMBER: &str = "member";
/// `relation` family token.
pub const FAMILY_RELATION: &str = "relation";
/// `classification` family token.
pub const FAMILY_CLASSIFICATION: &str = "classification";
/// `diagnostic` family token.
pub const FAMILY_DIAGNOSTIC: &str = "diagnostic";
/// `context` family token (§8B.1).
pub const FAMILY_CONTEXT: &str = "context";

/// Context record schema tag (§8B.1); reuses the T02 module constant.
pub const SCHEMA_CONTEXT: &str = crate::npa_context_records::SCHEMA_CONTEXT;

/// The seven closed families, in envelope order (§8A.1 + §8B.1). With an empty
/// context slice the seventh token is admitted but never emitted (D662).
pub const FAMILIES: &[&str] = &[
    FAMILY_DOCUMENT,
    FAMILY_FRAGMENT,
    FAMILY_MEMBER,
    FAMILY_RELATION,
    FAMILY_CLASSIFICATION,
    FAMILY_DIAGNOSTIC,
    FAMILY_CONTEXT,
];

/// `completion_basis` token for a `complete` analysis envelope.
pub const BASIS_COMPLETE: &str = "bounded_analysis_complete";
/// `completion_basis` token forced by a refused analytical record.
pub const BASIS_REFUSED_RECORD: &str = "refused_record";
/// `completion_basis` token forced by a non-resolved context result (§8B.3).
pub const BASIS_CONTEXT_INCOMPLETE: &str = "context_incomplete";

/// Top-level record keys that would re-carry decoded corpus text. The
/// contracted v1 envelope is count/hash-only (§8.4, §12 H12).
const INLINE_TEXT_KEYS: &[&str] = &[
    "text",
    "source_utf8",
    "inline_text",
    "decoded_text",
    "segment_text",
];

// ----------------------------------------------------------------- limits #

/// Hard fail-closed writer limits (validate-before-write, §8A.9). The manifest
/// `limits` object copies the effective bounds used by the writer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AnalysisLimits {
    /// Maximum bytes in a single emitted line.
    pub max_line_bytes: u64,
    /// Maximum number of interior record lines.
    pub max_records: u64,
}

impl Default for AnalysisLimits {
    fn default() -> Self {
        AnalysisLimits {
            max_line_bytes: 64 * 1024 * 1024,
            max_records: 4_000_000,
        }
    }
}

/// Caller-declared analysis scope. A narrower scope can never be reported
/// `complete` (§8A.6); it becomes an honest `incomplete` with its own basis.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum AnalysisScope {
    /// The whole bounded analysis is present.
    #[default]
    Bounded,
    /// The caller declared a narrower scope than the whole document.
    CallerScope,
    /// Hold semantics withheld part of the analysis.
    Hold,
    /// A text-only scope withheld part of the structure.
    TextOnly,
    /// The source is outside the bounded provider profile.
    UnsupportedSource,
}

impl AnalysisScope {
    /// The `completion_basis` token for a non-`Bounded` scope, else `None`.
    pub const fn partial_basis(self) -> Option<&'static str> {
        match self {
            AnalysisScope::Bounded => None,
            AnalysisScope::CallerScope => Some("caller_scope"),
            AnalysisScope::Hold => Some("hold"),
            AnalysisScope::TextOnly => Some("text_only"),
            AnalysisScope::UnsupportedSource => Some("unsupported_source"),
        }
    }
}

// --------------------------------------------------------------- refusals #

/// Closed envelope-writer refusals. Every kind names one concrete invariant
/// that failed; it never carries a legal claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AnalysisWireErrorKind {
    /// A line exceeds `max_line_bytes`.
    LineBytesLimit,
    /// The record total exceeds `max_records`.
    RecordsLimit,
    /// The document does not end with exactly one trailing LF.
    MissingTrailingLf,
    /// The document contains a carriage return.
    CarriageReturn,
    /// The document contains an empty interior line (or is empty).
    EmptyLine,
    /// The manifest / policies / footer order is broken.
    EnvelopeStructural,
    /// A line is not one compact JSON object or carries an unknown kind.
    UnknownKind,
    /// A hash-shaped field is neither 64 lowercase hex nor `null`.
    HashShapeInvalid,
    /// The `completion` / `completion_basis` / `incomplete_reasons` invariant
    /// is violated.
    CompletionMarkerInvalid,
    /// A refused analytical record was presented as `complete`.
    RefusedRecordNotPromoted,
    /// A temporal stop-sign field is present (§9).
    TemporalFieldForbidden,
    /// The envelope re-carries decoded corpus text (§8.4).
    CorpusTransferForbidden,
    /// A referenced fragment is absent from the pinned substrate index.
    FragmentMissing,
}

impl AnalysisWireErrorKind {
    /// Closed diagnostic token.
    pub const fn as_str(self) -> &'static str {
        match self {
            AnalysisWireErrorKind::LineBytesLimit => "line_bytes_limit",
            AnalysisWireErrorKind::RecordsLimit => "records_limit",
            AnalysisWireErrorKind::MissingTrailingLf => "missing_trailing_lf",
            AnalysisWireErrorKind::CarriageReturn => "carriage_return",
            AnalysisWireErrorKind::EmptyLine => "empty_line",
            AnalysisWireErrorKind::EnvelopeStructural => "envelope_structural",
            AnalysisWireErrorKind::UnknownKind => "unknown_kind",
            AnalysisWireErrorKind::HashShapeInvalid => "hash_shape_invalid",
            AnalysisWireErrorKind::CompletionMarkerInvalid => "completion_marker_invalid",
            AnalysisWireErrorKind::RefusedRecordNotPromoted => "refused_record_not_promoted",
            AnalysisWireErrorKind::TemporalFieldForbidden => "temporal_field_forbidden",
            AnalysisWireErrorKind::CorpusTransferForbidden => "corpus_transfer_forbidden",
            AnalysisWireErrorKind::FragmentMissing => "fragment_missing",
        }
    }
}

/// A typed envelope refusal: a closed kind plus a human-readable detail.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisWireError {
    kind: AnalysisWireErrorKind,
    detail: String,
}

impl AnalysisWireError {
    /// Builds a refusal.
    pub fn new(kind: AnalysisWireErrorKind, detail: impl Into<String>) -> Self {
        AnalysisWireError {
            kind,
            detail: detail.into(),
        }
    }

    /// The closed refusal kind.
    pub const fn kind(&self) -> AnalysisWireErrorKind {
        self.kind
    }

    /// The human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for AnalysisWireError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "npa_analysis_wire {}: {}",
            self.kind.as_str(),
            self.detail
        )
    }
}

impl std::error::Error for AnalysisWireError {}

fn err(kind: AnalysisWireErrorKind, detail: impl Into<String>) -> AnalysisWireError {
    AnalysisWireError::new(kind, detail)
}

// ------------------------------------------------------------ request #

/// Everything [`render_npa_analysis`] needs: the built document analysis, the
/// reader projection it indexes into, the pinned substrate index, the source
/// mapping (which carries the parent pin and version triple), the writer limits
/// and the caller scope.
pub struct AnalysisEnvelopeRequest<'a> {
    /// The document-scoped record streams (T02/T03).
    pub analysis: &'a DocumentAnalysis,
    /// The reader projection (`projection_content_hash`, primary views).
    pub projection: &'a ReaderProjection,
    /// The substrate index the fragment records hash.
    pub index: &'a ReaderRecordIndex,
    /// The pinned source mapping (parent identity + document version).
    pub mapping: &'a SourceMapping,
    /// The writer limits copied into the manifest.
    pub limits: AnalysisLimits,
    /// The caller-declared scope.
    pub scope: AnalysisScope,
}

// ------------------------------------------------------ JSON primitives #

enum Json {
    Null,
    Bool(bool),
    Num(u64),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(&'static str, Json)>),
}

impl Json {
    fn string(value: impl Into<String>) -> Json {
        Json::Str(value.into())
    }

    fn number(value: u64) -> Json {
        Json::Num(value)
    }

    fn index(value: usize) -> Json {
        Json::Num(value as u64)
    }

    fn bool(value: bool) -> Json {
        Json::Bool(value)
    }

    fn array(items: Vec<Json>) -> Json {
        Json::Arr(items)
    }

    fn object(entries: Vec<(&'static str, Json)>) -> Json {
        Json::Obj(entries)
    }
}

fn opt_string(value: Option<&str>) -> Json {
    value.map(Json::string).unwrap_or(Json::Null)
}

/// Stable `ensure_ascii=False` escaping: quote, backslash, short control
/// escapes and `\u00xx` for the remaining C0 controls; legal UTF-8 passes
/// through verbatim. Mirrors `cleaned_wire`/`reader_projection`.
fn write_json_string(text: &str, out: &mut String) {
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", c as u32);
            }
            c => out.push(c),
        }
    }
    out.push('"');
}

/// Compact canonical renderer: ascending object keys at every level, no
/// whitespace between tokens, no newline inside the rendered value.
fn render_compact(value: &Json, out: &mut String) {
    match value {
        Json::Null => out.push_str("null"),
        Json::Bool(flag) => out.push_str(if *flag { "true" } else { "false" }),
        Json::Num(number) => {
            let _ = write!(out, "{number}");
        }
        Json::Str(text) => write_json_string(text, out),
        Json::Arr(items) => {
            out.push('[');
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                render_compact(item, out);
            }
            out.push(']');
        }
        Json::Obj(entries) => {
            let mut ordered: Vec<&(&'static str, Json)> = entries.iter().collect();
            ordered.sort_by(|left, right| left.0.cmp(right.0));
            out.push('{');
            for (index, (key, value)) in ordered.iter().enumerate() {
                if index > 0 {
                    out.push(',');
                }
                write_json_string(key, out);
                out.push(':');
                render_compact(value, out);
            }
            out.push('}');
        }
    }
}

fn render_line(value: &Json) -> String {
    let mut out = String::new();
    render_compact(value, &mut out);
    out
}

// --------------------------------------------------------- record JSON #

fn span_json(fragment: &str, start: usize, end: usize) -> Json {
    Json::object(vec![
        ("end", Json::index(end)),
        ("fragment", Json::string(fragment)),
        ("start", Json::index(start)),
    ])
}

/// A source reference on the wire: a fragment-qualified half-open span, or a
/// closed refusal token instead of a span (§8A.3).
fn source_ref_json(source_ref: &SourceRef) -> Json {
    match source_ref {
        SourceRef::Bound(span) => span_json(span.fragment.as_str(), span.start, span.end),
        SourceRef::Refused(refusal) => {
            Json::object(vec![("refusal", Json::string(refusal.token()))])
        }
    }
}

fn source_ref_array(refs: &[SourceRef]) -> Json {
    Json::array(refs.iter().map(source_ref_json).collect())
}

fn document_json(request: &AnalysisEnvelopeRequest<'_>) -> Json {
    let envelope = request.mapping.envelope();
    let version = request.mapping.version();
    let primary_views = request
        .projection
        .views
        .iter()
        .filter(|view| view.kind.is_primary())
        .count();
    Json::object(vec![
        ("blocks", Json::index(request.analysis.layout.block_count())),
        ("decoder_profile", Json::string(version.decoder_profile())),
        (
            "document_version_ref",
            Json::string(version.document_version_ref()),
        ),
        ("family", Json::string(FAMILY_DOCUMENT)),
        ("primary_views", Json::index(primary_views)),
        (
            "projection_content_hash",
            opt_string(request.projection.content_hash()),
        ),
        ("ref", Json::string("doc")),
        ("schema", Json::string(SCHEMA_DOCUMENT)),
        ("source_revision", Json::string(version.source_revision())),
        (
            "source_sha256",
            Json::string(envelope.source_sha256.as_str()),
        ),
    ])
}

fn fragment_json(fragment: &FragmentRef, byte_length: usize, content_sha256: &str) -> Json {
    let id = fragment.as_str();
    Json::object(vec![
        ("byte_length", Json::index(byte_length)),
        ("content_sha256", Json::string(content_sha256)),
        ("family", Json::string(FAMILY_FRAGMENT)),
        ("fragment_ref", Json::string(id)),
        ("ref", Json::string(id)),
        ("schema", Json::string(SCHEMA_FRAGMENT)),
    ])
}

fn type_derivation_token(derivation: TypeDerivation) -> &'static str {
    match derivation {
        TypeDerivation::WrittenHere => "written_here",
        TypeDerivation::Unresolved => "unresolved",
    }
}

fn typed_member_json(record: &TypedMemberRecord) -> Json {
    let alternatives = record
        .alternatives
        .iter()
        .map(|alternative| {
            Json::object(vec![
                ("canon", Json::string(alternative.canon.as_str())),
                ("span", source_ref_json(&alternative.span)),
            ])
        })
        .collect();
    Json::object(vec![
        ("alternatives", Json::array(alternatives)),
        ("approved_by", Json::string(record.approved_by.as_str())),
        ("date", Json::string(record.date.as_str())),
        (
            "derivation",
            Json::string(type_derivation_token(record.derivation)),
        ),
        ("family", Json::string(FAMILY_MEMBER)),
        ("number", Json::string(record.number.as_str())),
        ("ref", Json::string(format!("mt:{}", record.typed_index))),
        ("schema", Json::string(SCHEMA_MEMBER)),
        ("span", source_ref_json(&record.span)),
        ("stage", Json::string("typed")),
        (
            "type_evidence",
            record
                .type_evidence
                .as_ref()
                .map(source_ref_json)
                .unwrap_or(Json::Null),
        ),
        ("type_name", Json::string(record.type_name.as_str())),
        ("typed_index", Json::index(record.typed_index)),
        ("unresolved", Json::bool(record.unresolved)),
    ])
}

fn linked_member_kind_token(kind: LinkedMemberKind) -> &'static str {
    match kind {
        LinkedMemberKind::Anchored => "anchored",
        LinkedMemberKind::NamedType => "named_type",
    }
}

fn link_derivation_token(derivation: LinkDerivation) -> &'static str {
    match derivation {
        LinkDerivation::TypedAnchor => "typed_anchor",
        LinkDerivation::DocumentHead => "document_head",
        LinkDerivation::ApprovedByQuote => "approved_by_quote",
        LinkDerivation::ScopedAlias => "scoped_alias",
        LinkDerivation::ThisDocumentRef => "this_document_ref",
        LinkDerivation::SeriesContinuation => "series_continuation",
        LinkDerivation::NamedTypeText => "named_type_text",
        LinkDerivation::Refused => "refused",
    }
}

fn linked_member_json(record: &LinkedMemberRecord) -> Json {
    Json::object(vec![
        ("alias", opt_string(record.alias.as_deref())),
        ("approved_by", opt_string(record.approved_by.as_deref())),
        (
            "derivation",
            Json::string(link_derivation_token(record.derivation)),
        ),
        ("evidence", source_ref_json(&record.evidence)),
        ("family", Json::string(FAMILY_MEMBER)),
        ("kind", Json::string(linked_member_kind_token(record.kind))),
        ("member_id", Json::index(record.member_id)),
        ("provenance", source_ref_array(&record.provenance)),
        ("ref", Json::string(format!("ml:{}", record.member_id))),
        ("schema", Json::string(SCHEMA_MEMBER)),
        ("stage", Json::string("linked")),
    ])
}

fn linked_relation_kind_token(kind: LinkedRelationKind) -> &'static str {
    match kind {
        LinkedRelationKind::ContinuesSeries => "continues_series",
        LinkedRelationKind::ApprovedBy => "approved_by",
        LinkedRelationKind::ScopedAlias => "scoped_alias",
        LinkedRelationKind::ThisDocumentRef => "this_document_ref",
        LinkedRelationKind::HeadFamilyCarry => "head_family_carry",
    }
}

fn relation_json(record: &RelationRecord) -> Json {
    Json::object(vec![
        ("evidence", source_ref_array(&record.evidence)),
        ("family", Json::string(FAMILY_RELATION)),
        ("from", Json::index(record.from_id)),
        (
            "kind",
            Json::string(linked_relation_kind_token(record.kind)),
        ),
        ("ref", Json::string(format!("r:{}", record.index))),
        ("schema", Json::string(SCHEMA_RELATION)),
        ("to", Json::index(record.to_id)),
        ("why", Json::string(record.why.as_str())),
    ])
}

fn classification_json(record: &ClassificationRecord) -> Json {
    Json::object(vec![
        ("competence", Json::string(record.competence.as_str())),
        ("evidence", source_ref_json(&record.evidence)),
        ("family", Json::string(FAMILY_CLASSIFICATION)),
        ("graph", Json::string(record.graph.as_str())),
        ("identity_key", Json::string(record.identity_key.as_str())),
        ("legal_class", Json::string(record.legal_class.as_str())),
        ("member_id", Json::index(record.member_id)),
        ("ref", Json::string(format!("c:{}", record.member_id))),
        ("schema", Json::string(SCHEMA_CLASSIFICATION)),
        ("why", Json::string(record.why.as_str())),
    ])
}

fn reject_reason_token(reason: RejectReason) -> &'static str {
    match reason {
        RejectReason::Inbound => "inbound",
        RejectReason::Minjust => "minjust",
        RejectReason::DateOverlap => "date_overlap",
    }
}

fn diagnostic_json(record: &DiagnosticRecord) -> Json {
    let refs = record
        .refs
        .iter()
        .map(|reference| {
            Json::object(vec![
                ("family", Json::string(reference.family.as_str())),
                ("ref", Json::string(reference.reference.as_str())),
            ])
        })
        .collect();
    Json::object(vec![
        ("block", record.block.map(Json::index).unwrap_or(Json::Null)),
        ("family", Json::string(FAMILY_DIAGNOSTIC)),
        ("kind", Json::string(record.kind.as_str())),
        ("ref", Json::string(format!("d:{}", record.index))),
        ("refs", Json::array(refs)),
        (
            "reject_reason",
            record
                .reject_reason
                .map(|reason| Json::string(reject_reason_token(reason)))
                .unwrap_or(Json::Null),
        ),
        ("rule", Json::string(record.rule.as_str())),
        ("schema", Json::string(SCHEMA_DIAGNOSTIC)),
        (
            "span",
            record
                .span
                .as_ref()
                .map(source_ref_json)
                .unwrap_or(Json::Null),
        ),
        ("stage", Json::string(record.stage.as_str())),
    ])
}

// ------------------------------------------------------- context JSON #

fn context_claim_json(claim: &ContextClaimRecord) -> Json {
    Json::object(vec![
        ("anchor", source_ref_json(&claim.anchor)),
        (
            "claim_status",
            Json::string(claim_status_token(claim.claim_status)),
        ),
        (
            "derivation",
            Json::string(claim_derivation_token(claim.derivation)),
        ),
        ("field", Json::string(claim.field.as_str())),
        (
            "source_node_ref",
            Json::string(claim.source_node_ref.as_str()),
        ),
    ])
}

fn context_derivation_json(edge: &ContextDerivationRecord) -> Json {
    Json::object(vec![
        ("anchor", source_ref_json(&edge.anchor)),
        ("from", Json::string(edge.from.as_str())),
        (
            "relation",
            Json::string(derivation_relation_token(edge.relation)),
        ),
        ("status", Json::string(edge_status_token(edge.status))),
        ("to", Json::string(edge.to.as_str())),
    ])
}

fn context_result_json(record: &ContextResultRecord) -> Json {
    let claims = record.claims.iter().map(context_claim_json).collect();
    let derivations = record
        .derivations
        .iter()
        .map(context_derivation_json)
        .collect();
    let diagnostics = record
        .diagnostics
        .iter()
        .map(|diagnostic| Json::string(context_diagnostic_token(*diagnostic)))
        .collect();
    let anchors = record.anchors.iter().map(source_ref_json).collect();
    Json::object(vec![
        ("anchors", Json::array(anchors)),
        ("claims", Json::array(claims)),
        ("derivations", Json::array(derivations)),
        ("diagnostics", Json::array(diagnostics)),
        ("family", Json::string(FAMILY_CONTEXT)),
        ("kind", Json::string(KIND_RESULT)),
        ("ref", Json::string(record.reference.as_str())),
        (
            "request_kind",
            Json::string(request_kind_token(record.request_kind)),
        ),
        ("request_ref", Json::string(record.request_ref.as_str())),
        ("schema", Json::string(SCHEMA_CONTEXT)),
        ("status", Json::string(status_token(record.status))),
        ("view", opt_string(record.view)),
    ])
}

fn context_run_json(record: &ContextRunRecord) -> Json {
    let status_counts: Vec<(&'static str, Json)> = record
        .status_counts
        .iter()
        .map(|(status, count)| (status_token(*status), Json::index(*count)))
        .collect();
    let diagnostics = record
        .diagnostics
        .iter()
        .map(|diagnostic| Json::string(context_diagnostic_token(*diagnostic)))
        .collect();
    Json::object(vec![
        ("diagnostics", Json::array(diagnostics)),
        ("family", Json::string(FAMILY_CONTEXT)),
        ("kind", Json::string(KIND_RUN)),
        ("limit_reached", Json::bool(record.limit_reached)),
        ("non_resolved", Json::index(record.non_resolved)),
        ("ref", Json::string(record.reference.as_str())),
        ("requests", Json::index(record.requests)),
        ("resolved", Json::index(record.resolved)),
        ("schema", Json::string(SCHEMA_CONTEXT)),
        ("status_counts", Json::object(status_counts)),
    ])
}

fn context_json(record: &ContextRecord) -> Json {
    match record {
        ContextRecord::Result(result) => context_result_json(result),
        ContextRecord::Run(run) => context_run_json(run),
    }
}

// ------------------------------------------------------- envelope lines #

fn manifest_json(request: &AnalysisEnvelopeRequest<'_>) -> Json {
    let envelope = request.mapping.envelope();
    let version = request.mapping.version();
    Json::object(vec![
        ("capability", Json::string(CAPABILITY)),
        ("decoder_profile", Json::string(version.decoder_profile())),
        (
            "document_version_ref",
            Json::string(version.document_version_ref()),
        ),
        (
            "generator",
            Json::object(vec![
                ("name", Json::string(GENERATOR_NAME)),
                ("version", Json::string(GENERATOR_VERSION)),
            ]),
        ),
        ("kind", Json::string(KIND_MANIFEST)),
        (
            "limits",
            Json::object(vec![
                (
                    "max_line_bytes",
                    Json::number(request.limits.max_line_bytes),
                ),
                ("max_records", Json::number(request.limits.max_records)),
            ]),
        ),
        ("model", Json::string(MODEL)),
        ("non_authoritative", Json::bool(true)),
        (
            "parent",
            Json::object(vec![
                (
                    "manifest_hash",
                    opt_string(envelope.manifest_hash.as_deref()),
                ),
                (
                    "records_seal_hash",
                    opt_string(envelope.records_seal_hash.as_deref()),
                ),
                ("schema", Json::string(envelope.parent_schema.as_str())),
            ]),
        ),
        ("profile", Json::string(PROFILE)),
        ("schema", Json::string(SCHEMA_MANIFEST)),
        (
            "source",
            Json::object(vec![
                ("bytes", Json::number(envelope.source_bytes)),
                ("sha256", Json::string(envelope.source_sha256.as_str())),
            ]),
        ),
        ("source_revision", Json::string(version.source_revision())),
        ("version", Json::number(CONTRACT_VERSION)),
    ])
}

fn policies_json() -> Json {
    Json::object(vec![
        (
            "authenticity",
            Json::string("integrity_only_not_authenticity"),
        ),
        ("corpus_transfer", Json::string("no_restricted_corpus")),
        ("counts_scope", Json::string("integrity_not_coverage")),
        ("kind", Json::string(KIND_POLICIES)),
        ("non_authoritative", Json::bool(true)),
        ("promotion", Json::string("none")),
        ("schema", Json::string(SCHEMA_POLICIES)),
        ("semantic_scope", Json::string("not_legal_gold")),
        (
            "temporal_scope",
            Json::string("identity_and_coordinates_only"),
        ),
    ])
}

/// The record/footer counts object (§8A.6). The `contexts` key is present only
/// when at least one context record is emitted (§8B.1 rule 2).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
struct AnalysisCounts {
    documents: u64,
    fragments: u64,
    members: u64,
    relations: u64,
    classifications: u64,
    diagnostics: u64,
    contexts: Option<u64>,
    records: u64,
}

fn counts_json(counts: AnalysisCounts) -> Json {
    let mut entries: Vec<(&'static str, Json)> = vec![
        ("classifications", Json::number(counts.classifications)),
        ("diagnostics", Json::number(counts.diagnostics)),
        ("documents", Json::number(counts.documents)),
        ("fragments", Json::number(counts.fragments)),
        ("members", Json::number(counts.members)),
        ("records", Json::number(counts.records)),
        ("relations", Json::number(counts.relations)),
    ];
    if let Some(contexts) = counts.contexts {
        entries.push(("contexts", Json::number(contexts)));
    }
    Json::object(entries)
}

fn footer_body_json(
    counts: AnalysisCounts,
    completion: &str,
    completion_basis: &str,
    incomplete_reasons: &[&str],
) -> Json {
    Json::object(vec![
        ("completion", Json::string(completion)),
        ("completion_basis", Json::string(completion_basis)),
        ("counts", counts_json(counts)),
        (
            "incomplete_reasons",
            Json::array(
                incomplete_reasons
                    .iter()
                    .map(|reason| Json::string(*reason))
                    .collect(),
            ),
        ),
        ("kind", Json::string(KIND_FOOTER)),
        ("schema", Json::string(SCHEMA_FOOTER)),
    ])
}

fn footer_json(
    counts: AnalysisCounts,
    completion: &str,
    completion_basis: &str,
    incomplete_reasons: &[&str],
    records_seal_hash: &str,
    manifest_hash: &str,
) -> Json {
    Json::object(vec![
        ("completion", Json::string(completion)),
        ("completion_basis", Json::string(completion_basis)),
        ("counts", counts_json(counts)),
        (
            "incomplete_reasons",
            Json::array(
                incomplete_reasons
                    .iter()
                    .map(|reason| Json::string(*reason))
                    .collect(),
            ),
        ),
        ("kind", Json::string(KIND_FOOTER)),
        ("manifest_hash", Json::string(manifest_hash)),
        ("records_seal_hash", Json::string(records_seal_hash)),
        ("schema", Json::string(SCHEMA_FOOTER)),
    ])
}

// --------------------------------------------------------------- seals #

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

pub(crate) fn sha256_hex(bytes: &[u8]) -> String {
    hex_lower(&Sha256::digest(bytes))
}

/// `records_seal_hash = sha256(bytes(policies_line) || bytes(record_line_0) ||
/// ...)` with no extra separator (§8A.6).
fn records_seal_hash(policies_line: &str, record_lines: &[String]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(policies_line.as_bytes());
    for line in record_lines {
        hasher.update(line.as_bytes());
    }
    hex_lower(&hasher.finalize())
}

/// `manifest_hash = sha256(bytes(manifest_line) || "\n" || records_seal_hash ||
/// "\n" || bytes(footer_body))`, where `footer_body` excludes both seals.
fn manifest_hash(manifest_line: &str, records_seal_hash: &str, footer_body: &str) -> String {
    let mut buffer = String::with_capacity(
        manifest_line.len() + records_seal_hash.len() + footer_body.len() + 2,
    );
    buffer.push_str(manifest_line);
    buffer.push('\n');
    buffer.push_str(records_seal_hash);
    buffer.push('\n');
    buffer.push_str(footer_body);
    sha256_hex(buffer.as_bytes())
}

// ------------------------------------------------------------- render #

fn source_ref_refused(source_ref: &SourceRef) -> bool {
    matches!(source_ref, SourceRef::Refused(_))
}

/// True when any analytical record carries a closed refusal instead of a span.
fn analysis_has_refusal(analysis: &DocumentAnalysis) -> bool {
    analysis.typed.iter().any(|member| {
        source_ref_refused(&member.span)
            || member
                .type_evidence
                .as_ref()
                .is_some_and(source_ref_refused)
            || member
                .alternatives
                .iter()
                .any(|alternative| source_ref_refused(&alternative.span))
    }) || analysis.linked.iter().any(|member| {
        source_ref_refused(&member.evidence) || member.provenance.iter().any(source_ref_refused)
    }) || analysis
        .relations
        .iter()
        .any(|relation| relation.evidence.iter().any(source_ref_refused))
        || analysis
            .classifications
            .iter()
            .any(|record| source_ref_refused(&record.evidence))
        || analysis
            .diagnostics
            .iter()
            .any(|diagnostic| diagnostic.span.as_ref().is_some_and(source_ref_refused))
}

/// True when any context anchor carries a closed refusal instead of a span.
fn context_has_refusal(contexts: &[ContextRecord]) -> bool {
    contexts.iter().any(|record| {
        context_source_refs(record)
            .iter()
            .any(|source_ref| source_ref_refused(source_ref))
    })
}

fn completion_of(
    analysis: &DocumentAnalysis,
    scope: AnalysisScope,
    contexts: &[ContextRecord],
) -> (String, String, Vec<&'static str>) {
    // Precedence (§8B.3 rule 3): a refusal (S02 analytical or context anchor)
    // is never hidden behind a context partial or a scope partial.
    if analysis_has_refusal(analysis) || context_has_refusal(contexts) {
        return (
            "incomplete".to_string(),
            BASIS_REFUSED_RECORD.to_string(),
            vec![BASIS_REFUSED_RECORD],
        );
    }
    // Before the scope partials: a non-resolved context outranks `hold` etc.
    if let Some(reasons) = context_incomplete_reasons(contexts) {
        return (
            "incomplete".to_string(),
            BASIS_CONTEXT_INCOMPLETE.to_string(),
            reasons,
        );
    }
    match scope.partial_basis() {
        Some(basis) => ("incomplete".to_string(), basis.to_string(), vec![basis]),
        None => (
            "complete".to_string(),
            BASIS_COMPLETE.to_string(),
            Vec::new(),
        ),
    }
}

/// The context source refs carried by one record (anchors, claim anchors and
/// derivation anchors), in deterministic producer order.
fn context_source_refs(record: &ContextRecord) -> Vec<&SourceRef> {
    match record {
        ContextRecord::Result(result) => {
            let mut refs: Vec<&SourceRef> = result.anchors.iter().collect();
            refs.extend(result.claims.iter().map(|claim| &claim.anchor));
            refs.extend(result.derivations.iter().map(|edge| &edge.anchor));
            refs
        }
        ContextRecord::Run(_) => Vec::new(),
    }
}

/// The closed `incomplete_reasons` forced by non-resolved context results, or
/// `None` when every emitted result is `resolved` (§8B.3 rule 1).
fn context_incomplete_reasons(contexts: &[ContextRecord]) -> Option<Vec<&'static str>> {
    let mut statuses: BTreeSet<ContextStatus> = BTreeSet::new();
    for record in contexts {
        if let ContextRecord::Result(result) = record {
            if result.status != ContextStatus::Resolved {
                statuses.insert(result.status);
            }
        }
    }
    if statuses.is_empty() {
        return None;
    }
    let mut reasons: Vec<&'static str> = vec![BASIS_CONTEXT_INCOMPLETE];
    for status in statuses {
        let reason = match status {
            ContextStatus::Partial => "context_partial",
            ContextStatus::Conflicting => "context_conflicting",
            ContextStatus::Unavailable => "context_unavailable",
            ContextStatus::Cycle => "context_cycle",
            ContextStatus::Limit => "context_limit",
            ContextStatus::Resolved => continue,
        };
        reasons.push(reason);
    }
    Some(reasons)
}

/// Appends one fragment id to the ordered unique set of first appearances.
fn push_fragment(
    seen: &mut BTreeSet<String>,
    fragments: &mut Vec<FragmentRef>,
    fragment: &FragmentRef,
) {
    if seen.insert(fragment.as_str().to_string()) {
        fragments.push(fragment.clone());
    }
}

/// Ordered unique fragments referenced by the analysis blocks (document order
/// of first appearance) plus any context anchor fragments. With an empty
/// context slice this is byte-for-byte the S02 fragment set.
fn referenced_fragments(
    analysis: &DocumentAnalysis,
    contexts: &[ContextRecord],
) -> Vec<FragmentRef> {
    let mut seen: BTreeSet<String> = BTreeSet::new();
    let mut fragments: Vec<FragmentRef> = Vec::new();
    for block in &analysis.layout.blocks {
        for segment in &block.segments {
            push_fragment(&mut seen, &mut fragments, &segment.fragment);
        }
    }
    for record in contexts {
        for source_ref in context_source_refs(record) {
            if let SourceRef::Bound(span) = source_ref {
                push_fragment(&mut seen, &mut fragments, &span.fragment);
            }
        }
    }
    fragments
}

/// Renders the document-scoped analysis envelope (§8A) with **no** context
/// records: the byte-identical S02 six-family envelope (D662). Delegates to
/// [`render_npa_analysis_with_context`] with an empty slice.
pub fn render_npa_analysis(
    request: &AnalysisEnvelopeRequest<'_>,
) -> Result<String, AnalysisWireError> {
    render_npa_analysis_with_context(request, &[])
}

/// Renders the document-scoped analysis envelope (§8A) plus the opt-in seventh
/// `context` family (§8B.1). Every line is validated against `request.limits`
/// **before** any bytes are returned; a line over `max_line_bytes` or a record
/// count over `max_records` is a closed limit refusal with no partial envelope.
/// A refused analytical record or context anchor forces an honest
/// `incomplete`/`refused_record` footer; otherwise a non-resolved context
/// result forces `incomplete`/`context_incomplete` (§8B.3). With an empty
/// `contexts` slice the output is byte-identical to the S02 envelope.
pub fn render_npa_analysis_with_context(
    request: &AnalysisEnvelopeRequest<'_>,
    contexts: &[ContextRecord],
) -> Result<String, AnalysisWireError> {
    let analysis = request.analysis;

    // Fragment records: count/hash-only, no inline decoded text (§8.4, §8.7).
    let fragments = referenced_fragments(analysis, contexts);
    let mut fragment_records: Vec<Json> = Vec::with_capacity(fragments.len());
    for fragment in &fragments {
        let record = request.index.text(fragment.as_str()).ok_or_else(|| {
            err(
                AnalysisWireErrorKind::FragmentMissing,
                format!("fragment {fragment} is missing from the substrate index"),
            )
        })?;
        fragment_records.push(fragment_json(
            fragment,
            record.value.len(),
            &sha256_hex(record.value.as_bytes()),
        ));
    }

    let context_count = contexts.len() as u64;
    let counts = AnalysisCounts {
        documents: 1,
        fragments: fragment_records.len() as u64,
        members: (analysis.typed.len() + analysis.linked.len()) as u64,
        relations: analysis.relations.len() as u64,
        classifications: analysis.classifications.len() as u64,
        diagnostics: analysis.diagnostics.len() as u64,
        contexts: (context_count > 0).then_some(context_count),
        records: 0,
    };
    let counts = AnalysisCounts {
        records: counts.documents
            + counts.fragments
            + counts.members
            + counts.relations
            + counts.classifications
            + counts.diagnostics
            + counts.contexts.unwrap_or(0),
        ..counts
    };

    let (completion, completion_basis, incomplete_reasons) =
        completion_of(analysis, request.scope, contexts);

    let mut record_lines: Vec<String> = Vec::new();
    record_lines.push(render_line(&document_json(request)));
    for fragment in &fragment_records {
        record_lines.push(render_line(fragment));
    }
    for record in &analysis.typed {
        record_lines.push(render_line(&typed_member_json(record)));
    }
    for record in &analysis.linked {
        record_lines.push(render_line(&linked_member_json(record)));
    }
    for record in &analysis.relations {
        record_lines.push(render_line(&relation_json(record)));
    }
    for record in &analysis.classifications {
        record_lines.push(render_line(&classification_json(record)));
    }
    for record in &analysis.diagnostics {
        record_lines.push(render_line(&diagnostic_json(record)));
    }
    for record in contexts {
        record_lines.push(render_line(&context_json(record)));
    }

    if record_lines.len() as u64 > request.limits.max_records {
        return Err(err(
            AnalysisWireErrorKind::RecordsLimit,
            format!(
                "analysis emitted {} records, over max_records {}",
                record_lines.len(),
                request.limits.max_records
            ),
        ));
    }

    let manifest_line = render_line(&manifest_json(request));
    let policies_line = render_line(&policies_json());
    let records_seal = records_seal_hash(&policies_line, &record_lines);
    let footer_body = render_line(&footer_body_json(
        counts,
        &completion,
        &completion_basis,
        &incomplete_reasons,
    ));
    let manifest_seal = manifest_hash(&manifest_line, &records_seal, &footer_body);
    let footer_line = render_line(&footer_json(
        counts,
        &completion,
        &completion_basis,
        &incomplete_reasons,
        &records_seal,
        &manifest_seal,
    ));

    let mut emitted: Vec<&str> = Vec::with_capacity(record_lines.len() + 3);
    emitted.push(manifest_line.as_str());
    emitted.push(policies_line.as_str());
    emitted.extend(record_lines.iter().map(String::as_str));
    emitted.push(footer_line.as_str());
    for line in &emitted {
        if line.len() as u64 > request.limits.max_line_bytes {
            return Err(err(
                AnalysisWireErrorKind::LineBytesLimit,
                format!(
                    "emitted line of {} bytes is over max_line_bytes {}",
                    line.len(),
                    request.limits.max_line_bytes
                ),
            ));
        }
    }

    let mut out = String::new();
    for line in &emitted {
        out.push_str(line);
        out.push('\n');
    }
    Ok(out)
}

/// Renders the envelope and self-checks the rendered structure with
/// [`inspect_npa_analysis_wire`]. This is a structural self-check, **not** a
/// read-back verifier: records are not reconstructed and seals are not
/// recomputed (S03 owns that).
pub fn export_npa_analysis(
    request: &AnalysisEnvelopeRequest<'_>,
) -> Result<String, AnalysisWireError> {
    let text = render_npa_analysis(request)?;
    inspect_npa_analysis_wire(&text)?;
    Ok(text)
}

// -------------------------------------------------------- structural inspect #

/// Structure-only summary of an analysis envelope (§8A.9). No record is
/// reconstructed and no seal is recomputed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisEnvelopeSummary {
    /// Record count per family token (all admitted families; the seventh
    /// `context` family appears only when context records are emitted).
    pub families: BTreeMap<String, u64>,
    /// Total interior record lines.
    pub records: u64,
    /// Closed `completion` token.
    pub completion: String,
    /// Closed `completion_basis` token.
    pub completion_basis: String,
    /// Ordered closed `incomplete_reasons` tokens (empty for `complete`).
    pub incomplete_reasons: Vec<String>,
    /// Footer `records_seal_hash` (shape-checked, never recomputed here).
    pub records_seal_hash: Option<String>,
    /// Footer `manifest_hash` (shape-checked, never recomputed here).
    pub manifest_hash: Option<String>,
}

/// Top-level members of one compact JSON object, as `(key, raw_value)` slices.
/// A small strict extractor: no JSON dependency is imported.
///
/// `pub(crate)` so the S03 read-back/verifier reuses the same strict parser
/// instead of minting a second one.
pub(crate) struct JsonFields<'a> {
    entries: Vec<(&'a str, &'a str)>,
}

fn is_json_ws(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r')
}

fn skip_ws(bytes: &[u8], index: &mut usize) {
    while *index < bytes.len() && is_json_ws(bytes[*index]) {
        *index += 1;
    }
}

/// Advances `index` past exactly one JSON value starting at `*index`.
fn scan_value(raw: &str, index: &mut usize) -> Result<(), AnalysisWireError> {
    let bytes = raw.as_bytes();
    if *index >= bytes.len() {
        return Err(err(
            AnalysisWireErrorKind::UnknownKind,
            "missing JSON value",
        ));
    }
    match bytes[*index] {
        b'"' => {
            *index += 1;
            while *index < bytes.len() {
                match bytes[*index] {
                    b'\\' => *index += 2,
                    b'"' => {
                        *index += 1;
                        return Ok(());
                    }
                    _ => *index += 1,
                }
            }
            Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "unterminated JSON string",
            ))
        }
        b'{' | b'[' => {
            let mut depth = 0usize;
            while *index < bytes.len() {
                match bytes[*index] {
                    b'"' => {
                        *index += 1;
                        while *index < bytes.len() {
                            match bytes[*index] {
                                b'\\' => *index += 2,
                                b'"' => {
                                    *index += 1;
                                    break;
                                }
                                _ => *index += 1,
                            }
                        }
                    }
                    b'{' | b'[' => {
                        depth += 1;
                        *index += 1;
                    }
                    b'}' | b']' => {
                        depth = depth.saturating_sub(1);
                        *index += 1;
                        if depth == 0 {
                            return Ok(());
                        }
                    }
                    _ => *index += 1,
                }
            }
            Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "unterminated JSON container",
            ))
        }
        _ => {
            while *index < bytes.len() {
                let byte = bytes[*index];
                if byte == b',' || byte == b'}' || byte == b']' || is_json_ws(byte) {
                    break;
                }
                *index += 1;
            }
            Ok(())
        }
    }
}

impl<'a> JsonFields<'a> {
    /// Parses one compact JSON object into its top-level members. Duplicate
    /// keys, unquoted keys, unterminated values and trailing bytes are refused.
    pub(crate) fn parse(raw: &'a str) -> Result<JsonFields<'a>, AnalysisWireError> {
        let bytes = raw.as_bytes();
        let mut index = 0usize;
        skip_ws(bytes, &mut index);
        if index >= bytes.len() || bytes[index] != b'{' {
            return Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "line is not a JSON object",
            ));
        }
        index += 1;
        let mut entries: Vec<(&'a str, &'a str)> = Vec::new();
        loop {
            skip_ws(bytes, &mut index);
            if index >= bytes.len() {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    "unterminated JSON object",
                ));
            }
            if bytes[index] == b'}' {
                index += 1;
                break;
            }
            if bytes[index] != b'"' {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    "object key is not a JSON string",
                ));
            }
            let key_start = index + 1;
            index += 1;
            let mut key_end = None;
            while index < bytes.len() {
                match bytes[index] {
                    b'\\' => index += 2,
                    b'"' => {
                        key_end = Some(index);
                        index += 1;
                        break;
                    }
                    _ => index += 1,
                }
            }
            let key_end = key_end.ok_or_else(|| {
                err(
                    AnalysisWireErrorKind::UnknownKind,
                    "unterminated object key",
                )
            })?;
            let key = &raw[key_start..key_end];
            skip_ws(bytes, &mut index);
            if index >= bytes.len() || bytes[index] != b':' {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    "object member has no colon",
                ));
            }
            index += 1;
            skip_ws(bytes, &mut index);
            let value_start = index;
            scan_value(raw, &mut index)?;
            let value = &raw[value_start..index];
            if entries.iter().any(|(existing, _)| *existing == key) {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    format!("duplicate object key {key}"),
                ));
            }
            entries.push((key, value));
            skip_ws(bytes, &mut index);
            if index >= bytes.len() {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    "unterminated JSON object",
                ));
            }
            match bytes[index] {
                b',' => index += 1,
                b'}' => {
                    index += 1;
                    break;
                }
                _ => {
                    return Err(err(
                        AnalysisWireErrorKind::UnknownKind,
                        "malformed object separator",
                    ));
                }
            }
        }
        skip_ws(bytes, &mut index);
        if index != bytes.len() {
            return Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "trailing bytes after the JSON object",
            ));
        }
        Ok(JsonFields { entries })
    }

    pub(crate) fn get(&self, key: &str) -> Option<&'a str> {
        self.entries
            .iter()
            .find(|(existing, _)| *existing == key)
            .map(|(_, value)| *value)
    }

    pub(crate) fn keys(&self) -> Vec<&'a str> {
        self.entries.iter().map(|(key, _)| *key).collect()
    }
}

/// Decodes one JSON string literal into its Rust text. Unsupported escapes are
/// refused (`None`). Mirrors the writer's `ensure_ascii=False` set.
fn unescape_json_string(raw: &str) -> Option<String> {
    let inner = raw.strip_prefix('"')?.strip_suffix('"')?;
    let mut out = String::with_capacity(inner.len());
    let mut chars = inner.chars();
    while let Some(ch) = chars.next() {
        if ch != '\\' {
            out.push(ch);
            continue;
        }
        match chars.next()? {
            '"' => out.push('"'),
            '\\' => out.push('\\'),
            '/' => out.push('/'),
            'b' => out.push('\u{8}'),
            'f' => out.push('\u{c}'),
            'n' => out.push('\n'),
            'r' => out.push('\r'),
            't' => out.push('\t'),
            'u' => {
                let mut code = 0u32;
                for _ in 0..4 {
                    let digit = chars.next()?.to_digit(16)?;
                    code = code * 16 + digit;
                }
                out.push(char::from_u32(code)?);
            }
            _ => return None,
        }
    }
    Some(out)
}

pub(crate) fn string_field(fields: &JsonFields<'_>, key: &str) -> Option<String> {
    let raw = fields.get(key)?;
    if !raw.starts_with('"') || !raw.ends_with('"') {
        return None;
    }
    unescape_json_string(raw)
}

pub(crate) fn u64_field(fields: &JsonFields<'_>, key: &str) -> Option<u64> {
    fields.get(key)?.trim().parse::<u64>().ok()
}

/// Reads a strict JSON boolean (`true` | `false`). Any other token is `None`.
pub(crate) fn bool_field(fields: &JsonFields<'_>, key: &str) -> Option<bool> {
    match fields.get(key)?.trim() {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

pub(crate) fn string_array_field(fields: &JsonFields<'_>, key: &str) -> Option<Vec<String>> {
    let raw = fields.get(key)?.trim();
    let inner = raw.strip_prefix('[')?.strip_suffix(']')?;
    let bytes = inner.as_bytes();
    let mut items = Vec::new();
    let mut index = 0usize;
    loop {
        skip_ws(bytes, &mut index);
        if index >= bytes.len() {
            break;
        }
        if bytes[index] != b'"' {
            return None;
        }
        let start = index;
        index += 1;
        while index < bytes.len() {
            match bytes[index] {
                b'\\' => index += 2,
                b'"' => {
                    index += 1;
                    break;
                }
                _ => index += 1,
            }
        }
        items.push(unescape_json_string(&inner[start..index])?);
        skip_ws(bytes, &mut index);
        if index < bytes.len() && bytes[index] == b',' {
            index += 1;
        }
    }
    Some(items)
}

pub(crate) fn is_hex64(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

pub(crate) fn opt_hex_field(
    fields: &JsonFields<'_>,
    key: &str,
) -> Result<Option<String>, AnalysisWireError> {
    let raw = fields.get(key).ok_or_else(|| {
        err(
            AnalysisWireErrorKind::HashShapeInvalid,
            format!("{key} is missing"),
        )
    })?;
    let trimmed = raw.trim();
    if trimmed == "null" {
        return Ok(None);
    }
    let value = string_field(fields, key).ok_or_else(|| {
        err(
            AnalysisWireErrorKind::HashShapeInvalid,
            format!("{key} is not a JSON string"),
        )
    })?;
    if !is_hex64(&value) {
        return Err(err(
            AnalysisWireErrorKind::HashShapeInvalid,
            format!("{key} is not 64 lowercase hex"),
        ));
    }
    Ok(Some(value))
}

/// Splits a rendered envelope into its LF-terminated lines, refusing an empty
/// document, a missing trailing LF, a carriage return and an empty line.
pub(crate) fn split_lines(text: &str) -> Result<Vec<&str>, AnalysisWireError> {
    if text.is_empty() {
        return Err(err(AnalysisWireErrorKind::EmptyLine, "empty envelope"));
    }
    if !text.ends_with('\n') {
        return Err(err(
            AnalysisWireErrorKind::MissingTrailingLf,
            "envelope must end with exactly one trailing LF",
        ));
    }
    if text.contains('\r') {
        return Err(err(
            AnalysisWireErrorKind::CarriageReturn,
            "envelope must not contain a carriage return",
        ));
    }
    let body = &text[..text.len() - 1];
    let lines: Vec<&str> = body.split('\n').collect();
    for (index, line) in lines.iter().enumerate() {
        if line.is_empty() {
            return Err(err(
                AnalysisWireErrorKind::EmptyLine,
                format!("envelope line {index} is empty"),
            ));
        }
    }
    Ok(lines)
}

/// Splits a compact JSON array into its top-level element slices. Element
/// order is preserved; nested containers and string escapes are respected.
pub(crate) fn split_json_array_items(raw: &str) -> Result<Vec<&str>, AnalysisWireError> {
    let bytes = raw.as_bytes();
    let mut index = 0usize;
    skip_ws(bytes, &mut index);
    if index >= bytes.len() || bytes[index] != b'[' {
        return Err(err(
            AnalysisWireErrorKind::UnknownKind,
            "value is not a JSON array",
        ));
    }
    index += 1;
    let mut items: Vec<&str> = Vec::new();
    loop {
        skip_ws(bytes, &mut index);
        if index >= bytes.len() {
            return Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "unterminated JSON array",
            ));
        }
        if bytes[index] == b']' {
            index += 1;
            break;
        }
        let start = index;
        scan_value(raw, &mut index)?;
        items.push(&raw[start..index]);
        skip_ws(bytes, &mut index);
        if index >= bytes.len() {
            return Err(err(
                AnalysisWireErrorKind::UnknownKind,
                "unterminated JSON array",
            ));
        }
        match bytes[index] {
            b',' => index += 1,
            b']' => {
                index += 1;
                break;
            }
            _ => {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    "malformed JSON array separator",
                ))
            }
        }
    }
    skip_ws(bytes, &mut index);
    if index != bytes.len() {
        return Err(err(
            AnalysisWireErrorKind::UnknownKind,
            "trailing bytes after the JSON array",
        ));
    }
    Ok(items)
}

/// Maps one parsed line to its `(token, line kind)` pair. A line carries either
/// a `kind` (manifest/policies/footer) or a `family` (record).
pub(crate) fn line_token(
    fields: &JsonFields<'_>,
) -> Result<(String, EnvelopeLineKind), AnalysisWireError> {
    // Records are discriminated by `family` and may also carry their own
    // domain `kind` (linked member kind, diagnostic kind); manifest/policies/
    // footer carry only `kind`. `family` must therefore be checked first.
    if fields.get("family").is_some() {
        let family = string_field(fields, "family")
            .ok_or_else(|| err(AnalysisWireErrorKind::UnknownKind, "family is not a string"))?;
        if !FAMILIES.contains(&family.as_str()) {
            return Err(err(
                AnalysisWireErrorKind::UnknownKind,
                format!("unknown record family {family:?}"),
            ));
        }
        // A context line carries only the `result` | `run` discriminator; an
        // unknown kind is a structural refusal, never dropped (§8B.1 rule 4).
        if family == FAMILY_CONTEXT {
            let kind = string_field(fields, "kind").ok_or_else(|| {
                err(
                    AnalysisWireErrorKind::UnknownKind,
                    "context line has no string kind",
                )
            })?;
            if kind != KIND_RESULT && kind != KIND_RUN {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    format!("unknown context kind {kind:?}"),
                ));
            }
        }
        return Ok((family, EnvelopeLineKind::Record));
    }
    if fields.get("kind").is_some() {
        let token = string_field(fields, "kind")
            .ok_or_else(|| err(AnalysisWireErrorKind::UnknownKind, "kind is not a string"))?;
        let kind = match token.as_str() {
            KIND_MANIFEST => EnvelopeLineKind::Manifest,
            KIND_POLICIES => EnvelopeLineKind::Policies,
            KIND_FOOTER => EnvelopeLineKind::Footer,
            _ => {
                return Err(err(
                    AnalysisWireErrorKind::UnknownKind,
                    format!("unknown line kind {token:?}"),
                ))
            }
        };
        return Ok((token, kind));
    }
    Err(err(
        AnalysisWireErrorKind::UnknownKind,
        "line has neither a family nor a kind",
    ))
}

/// Structure-only inspection of a rendered analysis envelope (§8A.9). It
/// reports families, counts, completion, incomplete reasons and seal presence.
/// It refuses a structural break, a temporal stop-sign field, an inline corpus
/// text channel, a declared-limit violation and a refused record presented as
/// `complete`. It never reconstructs a record and never recomputes a seal.
pub fn inspect_npa_analysis_wire(text: &str) -> Result<AnalysisEnvelopeSummary, AnalysisWireError> {
    let lines = split_lines(text)?;
    let parsed: Vec<JsonFields<'_>> = lines
        .iter()
        .map(|line| JsonFields::parse(line))
        .collect::<Result<_, _>>()?;

    let mut tokens: Vec<String> = Vec::with_capacity(parsed.len());
    let mut shapes: Vec<EnvelopeLineShape> = Vec::with_capacity(parsed.len());
    for (index, fields) in parsed.iter().enumerate() {
        let (token, kind) = line_token(fields)?;
        shapes.push(EnvelopeLineShape {
            kind,
            raw_len: lines[index].len(),
            has_cr: false,
        });
        tokens.push(token);
    }
    check_envelope_shape(&shapes)
        .map_err(|refusal| err(AnalysisWireErrorKind::EnvelopeStructural, refusal.detail()))?;

    let last = lines.len() - 1;

    // Temporal stop-sign and inline corpus text are structurally forbidden
    // (§9, §8.4; the seam predicates are reused).
    let mut families: BTreeMap<String, u64> = BTreeMap::new();
    for fields in parsed.iter().take(last).skip(2) {
        let keys: Vec<&str> = fields.keys();
        check_temporal_fields(&keys).map_err(|refusal| {
            err(
                AnalysisWireErrorKind::TemporalFieldForbidden,
                refusal.detail(),
            )
        })?;
        for key in INLINE_TEXT_KEYS {
            if let Some(raw) = fields.get(key) {
                check_no_corpus_transfer(Some(raw)).map_err(|refusal| {
                    err(
                        AnalysisWireErrorKind::CorpusTransferForbidden,
                        refusal.detail(),
                    )
                })?;
            }
        }
        if let Some(family) = string_field(fields, "family") {
            *families.entry(family).or_insert(0) += 1;
        }
    }
    let records = (last - 2) as u64;

    let footer = &parsed[last];
    let completion = string_field(footer, "completion").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::CompletionMarkerInvalid,
            "footer completion is not a string",
        )
    })?;
    let completion_basis = string_field(footer, "completion_basis").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::CompletionMarkerInvalid,
            "footer completion_basis is not a string",
        )
    })?;
    let incomplete_reasons = string_array_field(footer, "incomplete_reasons").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::CompletionMarkerInvalid,
            "footer incomplete_reasons is not a string array",
        )
    })?;

    // A refused analytical record is never presented as complete (§8A.6, H16).
    let refused = lines[2..last]
        .iter()
        .any(|line| line.contains("\"refusal\":"));
    if refused && (completion != "incomplete" || completion_basis != BASIS_REFUSED_RECORD) {
        return Err(err(
            AnalysisWireErrorKind::RefusedRecordNotPromoted,
            "a refused analytical record must force completion=incomplete with basis refused_record",
        ));
    }

    match completion.as_str() {
        "complete" => {
            if completion_basis != BASIS_COMPLETE || !incomplete_reasons.is_empty() {
                return Err(err(
                    AnalysisWireErrorKind::CompletionMarkerInvalid,
                    "a complete envelope needs the bounded-analysis basis and no reasons",
                ));
            }
        }
        "incomplete" => {
            if incomplete_reasons.is_empty()
                || !incomplete_reasons
                    .iter()
                    .any(|reason| reason == &completion_basis)
            {
                return Err(err(
                    AnalysisWireErrorKind::CompletionMarkerInvalid,
                    "an incomplete envelope needs a non-empty reason set containing its basis",
                ));
            }
        }
        other => {
            return Err(err(
                AnalysisWireErrorKind::CompletionMarkerInvalid,
                format!("unknown completion token {other:?}"),
            ))
        }
    }

    let records_seal_hash = opt_hex_field(footer, "records_seal_hash")?;
    let manifest_hash = opt_hex_field(footer, "manifest_hash")?;

    // Declared limits are honored by the structure; a violation is a closed
    // limit refusal (§8A.9).
    let manifest = &parsed[0];
    let limits_raw = manifest.get("limits").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::EnvelopeStructural,
            "manifest is missing limits",
        )
    })?;
    let limits = JsonFields::parse(limits_raw)?;
    let max_line_bytes = u64_field(&limits, "max_line_bytes").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::EnvelopeStructural,
            "manifest limits.max_line_bytes is not an unsigned integer",
        )
    })?;
    let max_records = u64_field(&limits, "max_records").ok_or_else(|| {
        err(
            AnalysisWireErrorKind::EnvelopeStructural,
            "manifest limits.max_records is not an unsigned integer",
        )
    })?;
    for line in &lines {
        if line.len() as u64 > max_line_bytes {
            return Err(err(
                AnalysisWireErrorKind::LineBytesLimit,
                "envelope line exceeds the declared max_line_bytes",
            ));
        }
    }
    if records > max_records {
        return Err(err(
            AnalysisWireErrorKind::RecordsLimit,
            "envelope record count exceeds the declared max_records",
        ));
    }

    Ok(AnalysisEnvelopeSummary {
        families,
        records,
        completion,
        completion_basis,
        incomplete_reasons,
        records_seal_hash,
        manifest_hash,
    })
}

/// The two non-cyclic seals recomputed from a rendered envelope.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisSealPair {
    /// Recomputable `records_seal_hash` (policies line + record lines).
    pub records_seal_hash: String,
    /// Recomputable `manifest_hash` (manifest + records seal + footer body).
    pub manifest_hash: String,
}

/// Rebuilds the canonical `footer_body` string (the footer line without its two
/// seal fields). The rendered envelope already stores canonical compact values,
/// so the raw member slices can be rejoined in sorted key order.
fn footer_body_from_line(footer_line: &str) -> Result<String, AnalysisWireError> {
    let fields = JsonFields::parse(footer_line)?;
    let mut entries: Vec<(&str, &str)> = fields
        .entries
        .iter()
        .copied()
        .filter(|(key, _)| *key != "records_seal_hash" && *key != "manifest_hash")
        .collect();
    entries.sort_by(|left, right| left.0.cmp(right.0));
    let mut out = String::from("{");
    for (index, (key, value)) in entries.iter().enumerate() {
        if index > 0 {
            out.push(',');
        }
        write_json_string(key, &mut out);
        out.push(':');
        out.push_str(value);
    }
    out.push('}');
    Ok(out)
}

/// Recomputes both envelope seals from the rendered lines. This is a
/// **structure-level** recomputation (line positions only): it never
/// reconstructs a record and is not the S03 read-back verifier. It exists so
/// the S02 acceptance battery can assert the non-cyclic seal discipline.
pub fn recompute_analysis_seals(text: &str) -> Result<AnalysisSealPair, AnalysisWireError> {
    let lines = split_lines(text)?;
    if lines.len() < 3 {
        return Err(err(
            AnalysisWireErrorKind::EnvelopeStructural,
            "envelope needs at least a manifest, policies and footer line",
        ));
    }
    let last = lines.len() - 1;
    let record_lines: Vec<String> = lines[2..last].iter().map(|line| line.to_string()).collect();
    let records_seal = records_seal_hash(lines[1], &record_lines);
    let footer_body = footer_body_from_line(lines[last])?;
    let manifest_seal = manifest_hash(lines[0], &records_seal, &footer_body);
    Ok(AnalysisSealPair {
        records_seal_hash: records_seal,
        manifest_hash: manifest_seal,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn family_tokens_are_the_closed_seven() {
        assert_eq!(FAMILIES.len(), 7);
        assert!(FAMILIES.contains(&FAMILY_DOCUMENT));
        assert!(FAMILIES.contains(&FAMILY_FRAGMENT));
        assert!(FAMILIES.contains(&FAMILY_MEMBER));
        assert!(FAMILIES.contains(&FAMILY_RELATION));
        assert!(FAMILIES.contains(&FAMILY_CLASSIFICATION));
        assert!(FAMILIES.contains(&FAMILY_DIAGNOSTIC));
        assert!(FAMILIES.contains(&FAMILY_CONTEXT));
        assert_eq!(SCHEMA_CONTEXT, "law-nexus/npa-analysis-context/v1");
    }

    #[test]
    fn wire_error_kinds_are_closed_tokens() {
        assert_eq!(
            AnalysisWireErrorKind::RecordsLimit.as_str(),
            "records_limit"
        );
        assert_eq!(
            AnalysisWireErrorKind::TemporalFieldForbidden.as_str(),
            "temporal_field_forbidden"
        );
        assert_eq!(
            AnalysisWireErrorKind::CorpusTransferForbidden.as_str(),
            "corpus_transfer_forbidden"
        );
        assert_eq!(
            AnalysisWireErrorKind::RefusedRecordNotPromoted.as_str(),
            "refused_record_not_promoted"
        );
    }
}
