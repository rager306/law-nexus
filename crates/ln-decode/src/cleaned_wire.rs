//! S01 cleaned-projection wire writer over the frozen `source_package` and the
//! reader projection.
//!
//! This module implements the writer half of
//! `prd/architecture/cleaned-projection-contract.md` (family
//! `law-nexus/cleaned-projection/v1`, profile `cleaned_projection_wordml/v1`).
//! It turns a verified decoded package plus its reader projection into one
//! LF-delimited JSONL document with the envelope
//! `manifest → policies → records → footer`, an explicit inline decoded-text
//! channel on every `segment`, a closed completion marker, and two non-cyclic
//! integrity seals.
//!
//! The module carries no serialization dependency: it does not import a JSON
//! library and hand-rolls the canonical compact writer, mirroring the
//! `reader_projection` discipline (D328/D602/D633). Canonicalization is
//! deterministic — ascending keys, no inter-token whitespace, no embedded
//! newline — so two renders on equal input are byte-identical.
//!
//! Non-claims: this is a bounded wire envelope over an already-verified decoded
//! source and its reader projection. It is not an R1000 closure artifact, not a
//! CST/AST or temporal `StructuralAst`, not a read-back, and it asserts no
//! normative, legal-completeness, source-authenticity or corpus-coverage claim.
//! The seals are integrity evidence only. Counts and hashes are integrity, not
//! coverage. R1000 stays active.

use std::collections::HashMap;
use std::fmt::{self, Write};

use sha2::{Digest, Sha256};

use crate::reader_contract::{
    ElementRef, FragmentRef, ReaderDerivedKind, ReaderFragmentSpan, ReaderReferenceType,
    ReaderSegmentKind, ReaderSemantic, ReaderViewKind,
};
use crate::reader_projection::{
    ProjectedReference, ProjectedSegment, ProjectedView, ReaderProjection, ReferenceId, SegmentId,
    SegmentOrigin, ViewFlags, ViewId,
};
use crate::source_package::{Package, Record, TextRecord, TextSlot};

// -------------------------------------------------------------- constants #

/// Contract family / schema tag.
pub const CLEANED_PROJECTION_SCHEMA: &str = "law-nexus/cleaned-projection/v1";
/// Contract version pinned by this slice.
pub const CONTRACT_VERSION: u64 = 1;
/// Model name.
pub const MODEL: &str = "law-nexus/cleaned-projection-model/v1";
/// Pinned provider profile.
pub const PROFILE: &str = "cleaned_projection_wordml/v1";
/// Capability name.
pub const CAPABILITY: &str = "cleaned_projection_jsonl";
/// Manifest line discriminator.
pub const KIND_MANIFEST: &str = "cleaned_projection_manifest";
/// Policies line discriminator.
pub const KIND_POLICIES: &str = "cleaned_projection_policies";
/// View record discriminator.
pub const KIND_VIEW: &str = "cleaned_projection_view";
/// Segment record discriminator.
pub const KIND_SEGMENT: &str = "cleaned_projection_segment";
/// Reference record discriminator.
pub const KIND_REFERENCE: &str = "cleaned_projection_reference";
/// Footer line discriminator.
pub const KIND_FOOTER: &str = "cleaned_projection_footer";
/// Manifest schema tag.
pub const MANIFEST_SCHEMA: &str = "law-nexus/cleaned-projection-manifest/v1";
/// Policies schema tag.
pub const POLICIES_SCHEMA: &str = "law-nexus/cleaned-projection-policies/v1";
/// View record schema tag.
pub const VIEW_SCHEMA: &str = "law-nexus/cleaned-projection-view/v1";
/// Segment record schema tag.
pub const SEGMENT_SCHEMA: &str = "law-nexus/cleaned-projection-segment/v1";
/// Reference record schema tag.
pub const REFERENCE_SCHEMA: &str = "law-nexus/cleaned-projection-reference/v1";
/// Footer schema tag.
pub const FOOTER_SCHEMA: &str = "law-nexus/cleaned-projection-footer/v1";

/// Stable producing-tool id written into `manifest.generator.name`.
pub const GENERATOR_NAME: &str = "ln-decode.cleaned_wire";
/// Producing-tool version written into `manifest.generator.version`.
pub const GENERATOR_VERSION: &str = env!("CARGO_PKG_VERSION");

/// `completion_basis` token for a `complete` projection.
pub const BASIS_COMPLETE: &str = "bounded_projection_complete";

/// Policies line `cleaning_mode` value (closed contract vocabulary).
pub const POLICY_CLEANING_MODE: &str = "display_only_reversible";
/// Policies line `text_retention` value (closed contract vocabulary).
pub const POLICY_TEXT_RETENTION: &str = "full_decoded_text_retained_inline";
/// Policies line `hold_text_only` value (closed contract vocabulary).
pub const POLICY_HOLD_TEXT_ONLY: &str = "no_decoded_text_loss_permitted";
/// Policies line `counts_scope` value (closed contract vocabulary).
pub const POLICY_COUNTS_SCOPE: &str = "integrity_not_coverage";
/// Policies line `unknown_context` value (closed contract vocabulary).
pub const POLICY_UNKNOWN_CONTEXT: &str = "retained_and_addressable";
/// Policies line `normalization` value (closed contract vocabulary).
pub const POLICY_NORMALIZATION: &str = "raw_decoded_text_no_char_normalization";
/// Policies line `authenticity` value (closed contract vocabulary).
pub const POLICY_AUTHENTICITY: &str = "integrity_only_not_authenticity";

// ------------------------------------------------------------ closed types #

/// Hard fail-closed writer limits (validate-before-write). All values are
/// `u64`; the manifest copies the effective bounds used by the writer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct WireLimits {
    /// Maximum bytes in a single emitted line.
    pub max_line_bytes: u64,
    /// Maximum total `view` + `segment` + `reference` records.
    pub max_records: u64,
    /// Maximum summed inline `text_bytes` over all segments.
    pub max_text_bytes: u64,
}

impl Default for WireLimits {
    fn default() -> Self {
        WireLimits {
            max_line_bytes: 64 * 1024 * 1024,
            max_records: 4_000_000,
            max_text_bytes: 512 * 1024 * 1024,
        }
    }
}

/// Closed incompleteness reason vocabulary. A reason states why an honest
/// partial export is not `complete`; it never carries a legal claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum IncompleteReason {
    /// Hold semantics withheld part of the projection.
    Hold,
    /// A text-only scope withheld part of the structure.
    TextOnly,
    /// A declared writer limit was reached.
    LimitReached,
    /// The source is outside the bounded provider profile.
    UnsupportedSource,
    /// The caller declared a narrower scope than the whole projection.
    CallerScope,
}

impl IncompleteReason {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            IncompleteReason::Hold => "hold",
            IncompleteReason::TextOnly => "text_only",
            IncompleteReason::LimitReached => "limit_reached",
            IncompleteReason::UnsupportedSource => "unsupported_source",
            IncompleteReason::CallerScope => "caller_scope",
        }
    }
}

/// Closed completion marker. `Complete` requires the whole projection to be
/// attributed without text loss; `Incomplete` carries a basis and a non-empty
/// reason set that contains the basis.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WireCompletion {
    /// The whole bounded projection is present, with no decoded-text loss.
    Complete,
    /// An honest partial export, with a primary basis and its reason set.
    Incomplete {
        /// Primary basis; must appear in `reasons`.
        basis: IncompleteReason,
        /// Closed reason tokens; non-empty and containing `basis`.
        reasons: Vec<IncompleteReason>,
    },
}

impl WireCompletion {
    /// Closed `completion` token.
    pub const fn as_str(&self) -> &'static str {
        match self {
            WireCompletion::Complete => "complete",
            WireCompletion::Incomplete { .. } => "incomplete",
        }
    }

    /// Closed `completion_basis` token.
    pub const fn basis_str(&self) -> &'static str {
        match self {
            WireCompletion::Complete => BASIS_COMPLETE,
            WireCompletion::Incomplete { basis, .. } => basis.as_str(),
        }
    }

    /// Ordered `incomplete_reasons` tokens (empty for `Complete`).
    pub fn reason_strs(&self) -> Vec<&'static str> {
        match self {
            WireCompletion::Complete => Vec::new(),
            WireCompletion::Incomplete { reasons, .. } => {
                reasons.iter().map(|reason| reason.as_str()).collect()
            }
        }
    }
}

/// Closed writer refusal vocabulary. Each kind names one concrete invariant
/// that failed; it never carries a legal claim. Structural truncation codes
/// (`MissingTrailingLf`, `CarriageReturn`, ...) are reserved for the S01
/// structure-only inspection added in T03.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum WireErrorKind {
    /// The substrate manifest identity does not match the frozen contract.
    SchemaMismatch,
    /// The substrate manifest version is unsupported.
    VersionMismatch,
    /// A line exceeds `max_line_bytes`.
    LineBytesLimit,
    /// The record total exceeds `max_records`.
    RecordsLimit,
    /// The summed inline `text_bytes` exceeds `max_text_bytes`.
    TextBytesLimit,
    /// A `complete` projection dropped or duplicated a substrate text record.
    TextLoss,
    /// A source segment names a fragment the substrate does not carry.
    FragmentMissing,
    /// A segment's provenance disagrees with its origin (owner, slot, span,
    /// kind, or a missing derived literal).
    ProvenanceMismatch,
    /// The `completion` / `completion_basis` / `incomplete_reasons` invariant
    /// is violated.
    CompletionMarkerInvalid,
    /// The document does not end with exactly one trailing LF.
    MissingTrailingLf,
    /// The document contains a carriage return.
    CarriageReturn,
    /// The document contains an empty interior line (or is empty).
    EmptyLine,
    /// The first line is not a manifest.
    MissingManifest,
    /// A manifest appears where it must not (misordered or duplicated).
    MisorderedManifest,
    /// The second line is not a policies line.
    MissingPolicies,
    /// A policies line appears where it must not (misordered or duplicated).
    MisorderedPolicies,
    /// The last line is not a footer.
    MissingFooter,
    /// A footer appears where it must not (misordered or duplicated).
    MisorderedFooter,
    /// A record line appears after the footer.
    TrailingRecordAfterFooter,
    /// A line is not one compact JSON object or carries an unknown `kind`.
    UnknownKind,
    /// A hash-shaped field is neither 64 lowercase hex nor an allowed `null`.
    HashShapeInvalid,
    /// A manifest/policies line is missing a required contract field or carries
    /// a value outside the closed contract vocabulary (independent of seals).
    ContractFieldInvalid,
    /// A recomputed seal disagrees with the seal recorded in the footer.
    HashMismatch,
    /// The body record groups are not in the order `views → segments → references`.
    RecordGroupOrder,
    /// A record line's required field is absent, ill-typed, or the record is
    /// otherwise not reconstructible.
    RecordFieldInvalid,
    /// Writing the rendered artifact to the caller's writer failed.
    WriteFailed,
}

impl WireErrorKind {
    /// Closed diagnostic token.
    pub const fn as_str(self) -> &'static str {
        match self {
            WireErrorKind::SchemaMismatch => "schema_mismatch",
            WireErrorKind::VersionMismatch => "version_mismatch",
            WireErrorKind::LineBytesLimit => "line_bytes_limit",
            WireErrorKind::RecordsLimit => "records_limit",
            WireErrorKind::TextBytesLimit => "text_bytes_limit",
            WireErrorKind::TextLoss => "text_loss",
            WireErrorKind::FragmentMissing => "fragment_missing",
            WireErrorKind::ProvenanceMismatch => "provenance_mismatch",
            WireErrorKind::CompletionMarkerInvalid => "completion_marker_invalid",
            WireErrorKind::MissingTrailingLf => "missing_trailing_lf",
            WireErrorKind::CarriageReturn => "carriage_return",
            WireErrorKind::EmptyLine => "empty_line",
            WireErrorKind::MissingManifest => "missing_manifest",
            WireErrorKind::MisorderedManifest => "misordered_manifest",
            WireErrorKind::MissingPolicies => "missing_policies",
            WireErrorKind::MisorderedPolicies => "misordered_policies",
            WireErrorKind::MissingFooter => "missing_footer",
            WireErrorKind::MisorderedFooter => "misordered_footer",
            WireErrorKind::TrailingRecordAfterFooter => "trailing_record_after_footer",
            WireErrorKind::UnknownKind => "unknown_kind",
            WireErrorKind::HashShapeInvalid => "hash_shape_invalid",
            WireErrorKind::ContractFieldInvalid => "contract_field_invalid",
            WireErrorKind::HashMismatch => "hash_mismatch",
            WireErrorKind::RecordGroupOrder => "record_group_order",
            WireErrorKind::RecordFieldInvalid => "record_field_invalid",
            WireErrorKind::WriteFailed => "write_failed",
        }
    }
}

/// A typed writer refusal: a closed kind plus a human-readable detail. It is
/// never an authenticity or legal claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireError {
    kind: WireErrorKind,
    detail: String,
}

impl WireError {
    /// Builds a refusal.
    pub fn new(kind: WireErrorKind, detail: impl Into<String>) -> Self {
        WireError {
            kind,
            detail: detail.into(),
        }
    }

    /// The closed refusal kind.
    pub fn kind(&self) -> WireErrorKind {
        self.kind
    }

    /// The human-readable detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for WireError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "cleaned_wire {}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for WireError {}

// -------------------------------------------------------- read-back model #

/// Substrate source identity pinned by the manifest (`manifest.source`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourcePin {
    /// Lowercase-hex sha256 of the frozen source bytes.
    pub sha256: String,
    /// Byte length of the frozen source.
    pub bytes: u64,
}

/// Parent seals pinned by the manifest (`manifest.parent`). `None` pins an
/// unsealed parent; the pair is integrity evidence only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParentSealPin {
    /// `records_seal_hash` of the frozen parent package, when present.
    pub records_seal_hash: Option<String>,
    /// `manifest_hash` of the frozen parent package, when present.
    pub manifest_hash: Option<String>,
}

/// One reconstructed inline decoded-text entry. `chars` / `text_bytes` are the
/// counts **declared on the segment line** (`text_chars` / `text_bytes`), not
/// recomputed here; the independent text-channel check lives in
/// `cleaned_verifier`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SegmentText {
    /// Segment id this text belongs to.
    pub segment_id: String,
    /// Source fragment id for a source segment; `None` for a derived segment.
    pub fragment_ref: Option<String>,
    /// Full decoded text (source fragment value, or the derived literal).
    pub text: String,
    /// Declared `text_chars`.
    pub chars: u64,
    /// Declared `text_bytes`.
    pub text_bytes: u64,
}

/// A typed read-back of a cleaned-projection artifact.
///
/// The embedded `projection` is **verify-shaped**: source-fragment segments
/// carry `text: None` (as `reader_verifier::verify_source_segment` requires) and
/// derived segments carry their generated literal. The full wire text is kept in
/// `inline_texts`, so downstream verification can compare the two channels
/// independently. Seals are recomputed on read and must match the footer; that
/// is an accidental-corruption check, never an authenticity claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanedProjection {
    /// Declared contract version.
    pub contract_version: u64,
    /// Pinned substrate source identity.
    pub source: SourcePin,
    /// Pinned parent seals.
    pub parent: ParentSealPin,
    /// Verify-shaped reader projection.
    pub projection: ReaderProjection,
    /// Full inline text for every segment, in record order.
    pub inline_texts: Vec<SegmentText>,
    /// Closed completion marker.
    pub completion: WireCompletion,
    /// Footer counts as declared (integrity, not coverage).
    pub counts: CleanedCounts,
    /// Footer `records_seal_hash`, recomputed and confirmed.
    pub records_seal_hash: String,
    /// Footer `manifest_hash`, recomputed and confirmed.
    pub manifest_hash: String,
}

// ------------------------------------------------- canonical JSON (compact) #

/// Minimal canonical JSON value tree. Deliberately local: D633 keeps the writer
/// inside the module instead of widening the frozen substrate wire contracts.
enum Json {
    Null,
    Bool(bool),
    Number(JsonNumber),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(&'static str, Json)>),
}

enum JsonNumber {
    Usize(usize),
    U64(u64),
}

impl Json {
    fn string(value: impl Into<String>) -> Json {
        Json::Str(value.into())
    }

    fn unsigned(value: usize) -> Json {
        Json::Number(JsonNumber::Usize(value))
    }

    fn u64(value: u64) -> Json {
        Json::Number(JsonNumber::U64(value))
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

/// Stable `ensure_ascii=False` escaping: quote, backslash, the short control
/// escapes and `\u00xx` for the remaining C0 controls; legal UTF-8 passes
/// through verbatim. Mirrors `reader_projection::write_json_string`.
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
        Json::Number(JsonNumber::Usize(number)) => {
            let _ = write!(out, "{number}");
        }
        Json::Number(JsonNumber::U64(number)) => {
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

// -------------------------------------------------------------- record JSON #

fn span_json(fragment: &str, start: usize, end: usize) -> Json {
    Json::object(vec![
        ("end", Json::unsigned(end)),
        ("fragment", Json::string(fragment)),
        ("start", Json::unsigned(start)),
    ])
}

fn manifest_json(package: &Package, limits: &WireLimits) -> Json {
    let manifest = package.manifest();
    let footer = package.footer();
    Json::object(vec![
        ("capability", Json::string(CAPABILITY)),
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
                ("max_line_bytes", Json::u64(limits.max_line_bytes)),
                ("max_records", Json::u64(limits.max_records)),
                ("max_text_bytes", Json::u64(limits.max_text_bytes)),
            ]),
        ),
        ("model", Json::string(MODEL)),
        ("non_authoritative", Json::Bool(true)),
        (
            "parent",
            Json::object(vec![
                ("manifest_hash", opt_string(footer.manifest_hash.as_deref())),
                (
                    "records_seal_hash",
                    opt_string(footer.records_seal_hash.as_deref()),
                ),
            ]),
        ),
        ("profile", Json::string(PROFILE)),
        ("schema", Json::string(MANIFEST_SCHEMA)),
        (
            "source",
            Json::object(vec![
                ("bytes", Json::u64(manifest.source.bytes)),
                ("sha256", Json::string(manifest.source.sha256.as_str())),
            ]),
        ),
        ("version", Json::u64(CONTRACT_VERSION)),
    ])
}

fn policies_json() -> Json {
    Json::object(vec![
        ("authenticity", Json::string(POLICY_AUTHENTICITY)),
        ("cleaning_mode", Json::string(POLICY_CLEANING_MODE)),
        ("counts_scope", Json::string(POLICY_COUNTS_SCOPE)),
        ("hold_text_only", Json::string(POLICY_HOLD_TEXT_ONLY)),
        ("kind", Json::string(KIND_POLICIES)),
        ("non_authoritative", Json::Bool(true)),
        ("normalization", Json::string(POLICY_NORMALIZATION)),
        ("schema", Json::string(POLICIES_SCHEMA)),
        ("text_retention", Json::string(POLICY_TEXT_RETENTION)),
        ("unknown_context", Json::string(POLICY_UNKNOWN_CONTEXT)),
        ("version", Json::u64(CONTRACT_VERSION)),
    ])
}

fn view_json(view: &crate::reader_projection::ProjectedView) -> Json {
    Json::object(vec![
        (
            "children",
            Json::array(
                view.children
                    .iter()
                    .map(|id| Json::string(id.as_str()))
                    .collect(),
            ),
        ),
        ("element_ref", Json::string(view.element_ref.as_str())),
        (
            "flags",
            Json::object(vec![("empty", Json::Bool(view.flags.empty))]),
        ),
        ("id", Json::string(view.id.as_str())),
        ("kind", Json::string(KIND_VIEW)),
        (
            "parent_view",
            opt_string(view.parent_view.as_ref().map(|id| id.as_str())),
        ),
        (
            "reference_refs",
            Json::array(
                view.reference_refs
                    .iter()
                    .map(|id| Json::string(id.as_str()))
                    .collect(),
            ),
        ),
        ("schema", Json::string(VIEW_SCHEMA)),
        (
            "segment_refs",
            Json::array(
                view.segment_refs
                    .iter()
                    .map(|id| Json::string(id.as_str()))
                    .collect(),
            ),
        ),
        ("view_kind", Json::string(view.kind.as_str())),
    ])
}

fn segment_json(segment: &ProjectedSegment, text: &str) -> Json {
    let source = matches!(segment.origin, SegmentOrigin::SourceFragment);
    let fragment = if source {
        segment
            .fragment_ref
            .as_ref()
            .map(|fragment| Json::string(fragment.as_str()))
            .unwrap_or(Json::Null)
    } else {
        Json::Null
    };
    let slot = if source {
        segment
            .slot
            .map(|slot| Json::string(slot.as_str()))
            .unwrap_or(Json::Null)
    } else {
        Json::Null
    };
    let span = if source {
        segment
            .span
            .as_ref()
            .map(|span| span_json(span.fragment.as_str(), span.start, span.end))
            .unwrap_or(Json::Null)
    } else {
        Json::Null
    };
    Json::object(vec![
        ("chars", Json::unsigned(text.chars().count())),
        ("contextual", Json::Bool(segment.contextual)),
        ("element_ref", Json::string(segment.element_ref.as_str())),
        ("fragment_ref", fragment),
        ("id", Json::string(segment.id.as_str())),
        ("kind", Json::string(KIND_SEGMENT)),
        ("ordinal", Json::unsigned(segment.ordinal)),
        ("origin", Json::string(segment.origin.as_str())),
        ("output_end", Json::unsigned(segment.output_end)),
        ("output_start", Json::unsigned(segment.output_start)),
        ("schema", Json::string(SEGMENT_SCHEMA)),
        ("segment_kind", Json::string(segment.segment_kind.as_str())),
        ("semantic", Json::string(segment.semantic.as_str())),
        ("slot", slot),
        ("source_pos", Json::unsigned(segment.source_pos)),
        ("span", span),
        ("text", Json::string(text)),
        ("text_bytes", Json::u64(text.len() as u64)),
        ("text_chars", Json::u64(text.chars().count() as u64)),
        ("view", Json::string(segment.view.as_str())),
    ])
}

fn reference_json(reference: &crate::reader_projection::ProjectedReference) -> Json {
    Json::object(vec![
        ("element_ref", Json::string(reference.element_ref.as_str())),
        ("id", Json::string(reference.id.as_str())),
        ("kind", Json::string(KIND_REFERENCE)),
        ("ordinal", Json::unsigned(reference.ordinal)),
        (
            "reference_type",
            Json::string(reference.reference_type.as_str()),
        ),
        ("resolved", Json::Bool(reference.resolved)),
        ("schema", Json::string(REFERENCE_SCHEMA)),
        ("source_pos", Json::unsigned(reference.source_pos)),
        ("view", Json::string(reference.view.as_str())),
    ])
}

/// Reconstituted footer counts. They are integrity counters, not a coverage
/// claim: a matching `records_seal_hash` or counts set never proves the
/// projection covers the source.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanedCounts {
    /// View records.
    pub views: u64,
    /// Segment records.
    pub segments: u64,
    /// Reference records.
    pub references: u64,
    /// Source-fragment segments.
    pub source_segments: u64,
    /// Derived segments.
    pub derived_segments: u64,
    /// Declared summed `text_chars`.
    pub text_chars: u64,
    /// Declared summed `text_bytes`.
    pub text_bytes: u64,
    /// `views + segments + references`.
    pub records: u64,
}

impl CleanedCounts {
    fn json(&self) -> Json {
        Json::object(vec![
            ("derived_segments", Json::u64(self.derived_segments)),
            ("records", Json::u64(self.records)),
            ("references", Json::u64(self.references)),
            ("segments", Json::u64(self.segments)),
            ("source_segments", Json::u64(self.source_segments)),
            ("text_bytes", Json::u64(self.text_bytes)),
            ("text_chars", Json::u64(self.text_chars)),
            ("views", Json::u64(self.views)),
        ])
    }
}

fn footer_json(
    completion: &WireCompletion,
    counts: &CleanedCounts,
    records_seal_hash: Option<&str>,
    manifest_hash: Option<&str>,
) -> Json {
    Json::object(vec![
        ("completion", Json::string(completion.as_str())),
        ("completion_basis", Json::string(completion.basis_str())),
        ("counts", counts.json()),
        (
            "incomplete_reasons",
            Json::array(
                completion
                    .reason_strs()
                    .iter()
                    .map(|reason| Json::string(*reason))
                    .collect(),
            ),
        ),
        ("kind", Json::string(KIND_FOOTER)),
        ("manifest_hash", opt_string(manifest_hash)),
        ("non_authoritative", Json::Bool(true)),
        ("records_seal_hash", opt_string(records_seal_hash)),
        ("schema", Json::string(FOOTER_SCHEMA)),
        ("version", Json::u64(CONTRACT_VERSION)),
    ])
}

// ------------------------------------------------------------------ seals #

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex_lower(&Sha256::digest(bytes))
}

/// `records_seal_hash = sha256(bytes(policies_line) || bytes(record_line_0) ||
/// ... || bytes(record_line_{k-1}))` with no extra separator.
fn records_seal_hash<S: AsRef<str>>(policies_line: &str, record_lines: &[S]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(policies_line.as_bytes());
    for line in record_lines {
        hasher.update(line.as_ref().as_bytes());
    }
    hex_lower(&hasher.finalize())
}

/// `manifest_hash = sha256(bytes(manifest_line) || "\n" || records_seal_hash ||
/// "\n" || bytes(footer_body))`, where `footer_body` nulls both seals.
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

// ------------------------------------------------------------ validation #

fn validate_substrate(package: &Package) -> Result<(), WireError> {
    let manifest = package.manifest();
    let identity_ok = manifest.kind == "source_package_manifest"
        && manifest.schema == crate::source_package::MANIFEST_SCHEMA
        && manifest.model == crate::source_package::MODEL
        && manifest.profile == crate::source_package::PROFILE
        && manifest.capability == crate::source_package::CAPABILITY;
    if !identity_ok {
        return Err(WireError::new(
            WireErrorKind::SchemaMismatch,
            "substrate manifest identity/constants mismatch",
        ));
    }
    if manifest.version != crate::source_package::SCHEMA_VERSION {
        return Err(WireError::new(
            WireErrorKind::VersionMismatch,
            format!("substrate manifest version {}", manifest.version),
        ));
    }
    Ok(())
}

fn validate_completion(completion: &WireCompletion) -> Result<(), WireError> {
    if let WireCompletion::Incomplete { basis, reasons } = completion {
        if reasons.is_empty() {
            return Err(WireError::new(
                WireErrorKind::CompletionMarkerInvalid,
                "incomplete completion carries no incomplete_reasons",
            ));
        }
        if !reasons.contains(basis) {
            return Err(WireError::new(
                WireErrorKind::CompletionMarkerInvalid,
                format!(
                    "incomplete_reasons does not contain completion_basis {}",
                    basis.as_str()
                ),
            ));
        }
    }
    Ok(())
}

/// Resolves the inline text of one segment, enforcing provenance consistency.
fn resolve_text(
    segment: &ProjectedSegment,
    index: &HashMap<&str, &TextRecord>,
) -> Result<String, WireError> {
    match segment.origin {
        SegmentOrigin::SourceFragment => {
            if segment.segment_kind != ReaderSegmentKind::Text {
                return Err(WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!(
                        "source segment {} has segment_kind {}",
                        segment.id.as_str(),
                        segment.segment_kind.as_str()
                    ),
                ));
            }
            let fragment = segment.fragment_ref.as_ref().ok_or_else(|| {
                WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!("source segment {} has no fragment_ref", segment.id.as_str()),
                )
            })?;
            let record = index.get(fragment.as_str()).ok_or_else(|| {
                WireError::new(
                    WireErrorKind::FragmentMissing,
                    format!("fragment {} is not in the substrate", fragment.as_str()),
                )
            })?;
            if record.owner != segment.element_ref.as_str() {
                return Err(WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!(
                        "fragment {} owner {} does not match segment element {}",
                        fragment.as_str(),
                        record.owner,
                        segment.element_ref.as_str()
                    ),
                ));
            }
            if Some(record.slot) != segment.slot {
                return Err(WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!(
                        "fragment {} slot does not match segment slot on {}",
                        fragment.as_str(),
                        segment.id.as_str()
                    ),
                ));
            }
            Ok(record.value.clone())
        }
        SegmentOrigin::Derived(_) => {
            if segment.segment_kind != ReaderSegmentKind::Derived
                || segment.fragment_ref.is_some()
                || segment.slot.is_some()
                || segment.span.is_some()
            {
                return Err(WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!(
                        "derived segment {} carries source provenance",
                        segment.id.as_str()
                    ),
                ));
            }
            segment.text.clone().ok_or_else(|| {
                WireError::new(
                    WireErrorKind::ProvenanceMismatch,
                    format!(
                        "derived segment {} has no literal text",
                        segment.id.as_str()
                    ),
                )
            })
        }
    }
}

// ----------------------------------------------------------------- writer #

/// Renders a cleaned structural JSONL projection: exactly one UTF-8
/// LF-terminated document in the fixed order
/// `manifest → policies → views → segments → references → footer`.
///
/// The writer is deterministic (equal input yields byte-identical output),
/// dependency-free, and fail-closed: every declared limit is validated before the
/// document is returned, a `complete` projection must attribute every substrate
/// text record exactly once, and no partial projection is ever emitted on a
/// refusal.
pub fn render_cleaned_projection(
    package: &Package,
    projection: &ReaderProjection,
    completion: &WireCompletion,
    limits: &WireLimits,
) -> Result<String, WireError> {
    validate_substrate(package)?;
    validate_completion(completion)?;

    let index: HashMap<&str, &TextRecord> = package
        .records()
        .iter()
        .filter_map(|record| match record {
            Record::Text(text) => Some((text.id.as_str(), text)),
            Record::Element(_) => None,
        })
        .collect();

    let mut record_lines: Vec<String> = Vec::with_capacity(
        projection.views.len() + projection.segments.len() + projection.references.len(),
    );
    let mut attributed: HashMap<String, u64> = HashMap::new();
    let mut counts = CleanedCounts {
        views: projection.views.len() as u64,
        segments: projection.segments.len() as u64,
        references: projection.references.len() as u64,
        source_segments: 0,
        derived_segments: 0,
        text_chars: 0,
        text_bytes: 0,
        records: (projection.views.len() + projection.segments.len() + projection.references.len())
            as u64,
    };

    for view in &projection.views {
        record_lines.push(render_line(&view_json(view)));
    }
    for segment in &projection.segments {
        let text = resolve_text(segment, &index)?;
        match segment.origin {
            SegmentOrigin::SourceFragment => {
                counts.source_segments += 1;
                if let Some(fragment) = &segment.fragment_ref {
                    *attributed.entry(fragment.as_str().to_string()).or_insert(0) += 1;
                }
            }
            SegmentOrigin::Derived(_) => counts.derived_segments += 1,
        }
        counts.text_chars += text.chars().count() as u64;
        counts.text_bytes += text.len() as u64;
        record_lines.push(render_line(&segment_json(segment, &text)));
    }
    for reference in &projection.references {
        record_lines.push(render_line(&reference_json(reference)));
    }

    // A `complete` projection may not drop or duplicate decoded text.
    if matches!(completion, WireCompletion::Complete) {
        for record in package.records() {
            if let Record::Text(text) = record {
                let seen = attributed.get(text.id.as_str()).copied().unwrap_or(0);
                if seen != 1 {
                    return Err(WireError::new(
                        WireErrorKind::TextLoss,
                        format!(
                            "complete projection attributes text fragment {} {seen} times",
                            text.id
                        ),
                    ));
                }
            }
        }
    }

    // Validate-before-write: no line is emitted on a refusal.
    if counts.records > limits.max_records {
        return Err(WireError::new(
            WireErrorKind::RecordsLimit,
            format!(
                "record total {} exceeds max_records {}",
                counts.records, limits.max_records
            ),
        ));
    }
    if counts.text_bytes > limits.max_text_bytes {
        return Err(WireError::new(
            WireErrorKind::TextBytesLimit,
            format!(
                "text bytes {} exceed max_text_bytes {}",
                counts.text_bytes, limits.max_text_bytes
            ),
        ));
    }

    let manifest_line = render_line(&manifest_json(package, limits));
    let policies_line = render_line(&policies_json());

    let records_seal = records_seal_hash(&policies_line, &record_lines);
    let footer_body = render_line(&footer_json(completion, &counts, None, None));
    let manifest_seal = manifest_hash(&manifest_line, &records_seal, &footer_body);
    let footer_line = render_line(&footer_json(
        completion,
        &counts,
        Some(records_seal.as_str()),
        Some(manifest_seal.as_str()),
    ));

    for line in std::iter::once(&manifest_line)
        .chain(std::iter::once(&policies_line))
        .chain(record_lines.iter())
        .chain(std::iter::once(&footer_line))
    {
        if line.len() as u64 > limits.max_line_bytes {
            return Err(WireError::new(
                WireErrorKind::LineBytesLimit,
                format!(
                    "line of {} bytes exceeds max_line_bytes {}",
                    line.len(),
                    limits.max_line_bytes
                ),
            ));
        }
    }

    let mut out = String::new();
    out.push_str(&manifest_line);
    out.push('\n');
    out.push_str(&policies_line);
    out.push('\n');
    for line in &record_lines {
        out.push_str(line);
        out.push('\n');
    }
    out.push_str(&footer_line);
    out.push('\n');
    Ok(out)
}

/// Named exporter: renders the artifact and self-checks it by reading the
/// envelope back. A round-trip failure is a typed refusal, so an exporter can
/// never publish a document its own reader cannot reconstruct.
///
/// This is an in-memory surface: it performs no filesystem publication and owns
/// no CLI. Callers that need to persist the bytes use
/// [`write_cleaned_projection`].
pub fn export_cleaned_projection(
    package: &Package,
    projection: &ReaderProjection,
    completion: &WireCompletion,
    limits: &WireLimits,
) -> Result<String, WireError> {
    let artifact = render_cleaned_projection(package, projection, completion, limits)?;
    read_cleaned_wire(&artifact).map_err(|error| {
        WireError::new(
            error.kind(),
            format!("exporter self-check failed: {}", error.detail()),
        )
    })?;
    Ok(artifact)
}

/// Writes an already-rendered artifact to a caller-supplied writer. Mirrors
/// `source_package::write_package`; the caller owns filesystem publication.
pub fn write_cleaned_projection<W: std::io::Write>(
    artifact: &str,
    writer: &mut W,
) -> Result<(), WireError> {
    writer.write_all(artifact.as_bytes()).map_err(|error| {
        WireError::new(
            WireErrorKind::WriteFailed,
            format!("writer refused: {error}"),
        )
    })
}

// ---------------------------------------------------- structural inspection #

/// Structure-only summary returned by [`inspect_cleaned_wire`].
///
/// It is deliberately *not* a read-back: no `Record`, view, segment or
/// reference is reconstructed, and the seals are never recomputed here. All
/// counts are integrity counters, not a coverage claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WireEnvelopeSummary {
    /// Declared contract version (always [`CONTRACT_VERSION`]).
    pub contract_version: u64,
    /// Recomputed `view` + `segment` + `reference` record total.
    pub records: u64,
    /// Recomputed view records.
    pub views: u64,
    /// Recomputed segment records.
    pub segments: u64,
    /// Recomputed reference records.
    pub references: u64,
    /// Footer `counts.source_segments` (integrity, not coverage).
    pub source_segments: u64,
    /// Footer `counts.derived_segments` (integrity, not coverage).
    pub derived_segments: u64,
    /// Footer `counts.text_chars` (integrity, not coverage).
    pub text_chars: u64,
    /// Footer `counts.text_bytes` (integrity, not coverage).
    pub text_bytes: u64,
    /// Closed `completion` token: `complete` or `incomplete`.
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
/// A small strict extractor: no JSON dependency is imported (D328/D602/D633).
struct JsonFields<'a> {
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

fn json_value_error(detail: &str) -> WireError {
    WireError::new(WireErrorKind::UnknownKind, detail)
}

/// Maximum JSON nesting depth accepted by [`scan_value`]. The envelope nests at
/// most three levels (manifest → generator/limits → scalars); the bound keeps
/// the recursive validator from overflowing the stack on hostile input (R29-F07
/// is still otherwise open, but this change must not widen it).
const MAX_JSON_DEPTH: usize = 64;

/// Advances `index` past exactly one **strict** JSON value starting at `*index`.
///
/// Unlike the earlier lax scanner this validates the whole value grammar: strings
/// carry well-formed escapes and no raw control bytes, numbers follow the JSON
/// number grammar (no leading zeros, no leading `+`), object keys are unique and
/// separators/trailing commas are exact, with nesting bounded by
/// [`MAX_JSON_DEPTH`]. A malformed value is a typed `UnknownKind` refusal, never a
/// silent skip. This is the F02 admission fix.
fn scan_value(raw: &str, index: &mut usize, depth: usize) -> Result<(), WireError> {
    if depth > MAX_JSON_DEPTH {
        return Err(json_value_error("JSON nesting exceeds the supported depth"));
    }
    skip_ws(raw.as_bytes(), index);
    let bytes = raw.as_bytes();
    let Some(&byte) = bytes.get(*index) else {
        return Err(json_value_error("missing JSON value"));
    };
    match byte {
        b'"' => scan_json_string(raw, index),
        b'{' => scan_json_object(raw, index, depth),
        b'[' => scan_json_array(raw, index, depth),
        b't' => scan_json_literal(raw, index, b"true"),
        b'f' => scan_json_literal(raw, index, b"false"),
        b'n' => scan_json_literal(raw, index, b"null"),
        b'-' | b'0'..=b'9' => scan_json_number(raw, index),
        _ => Err(json_value_error("unrecognized JSON value")),
    }
}

/// Validates one JSON string literal and advances past its closing quote.
fn scan_json_string(raw: &str, index: &mut usize) -> Result<(), WireError> {
    let bytes = raw.as_bytes();
    *index += 1; // opening quote
    while *index < bytes.len() {
        match bytes[*index] {
            b'"' => {
                *index += 1;
                return Ok(());
            }
            b'\\' => {
                *index += 1;
                let escape = *bytes
                    .get(*index)
                    .ok_or_else(|| json_value_error("unterminated JSON escape"))?;
                match escape {
                    b'"' | b'\\' | b'/' | b'b' | b'f' | b'n' | b'r' | b't' => *index += 1,
                    b'u' => {
                        *index += 1;
                        for _ in 0..4 {
                            let digit = *bytes
                                .get(*index)
                                .ok_or_else(|| json_value_error("truncated \\u escape"))?;
                            if !digit.is_ascii_hexdigit() {
                                return Err(json_value_error("invalid \\u escape"));
                            }
                            *index += 1;
                        }
                    }
                    _ => return Err(json_value_error("invalid JSON string escape")),
                }
            }
            byte if byte < 0x20 => {
                return Err(json_value_error(
                    "unescaped control character in JSON string",
                ))
            }
            _ => *index += 1,
        }
    }
    Err(json_value_error("unterminated JSON string"))
}

/// Validates one of the three JSON literals and advances past it.
fn scan_json_literal(raw: &str, index: &mut usize, literal: &[u8]) -> Result<(), WireError> {
    let bytes = raw.as_bytes();
    let end = *index + literal.len();
    if end > bytes.len() || &bytes[*index..end] != literal {
        return Err(json_value_error("invalid JSON literal"));
    }
    *index = end;
    Ok(())
}

/// Validates a JSON number against the RFC 8259 grammar and advances past it.
fn scan_json_number(raw: &str, index: &mut usize) -> Result<(), WireError> {
    let bytes = raw.as_bytes();
    let len = bytes.len();
    if *index < len && bytes[*index] == b'-' {
        *index += 1;
    }
    if *index >= len || !bytes[*index].is_ascii_digit() {
        return Err(json_value_error("invalid JSON number"));
    }
    if bytes[*index] == b'0' {
        *index += 1;
        if *index < len && bytes[*index].is_ascii_digit() {
            return Err(json_value_error("JSON number has a leading zero"));
        }
    } else {
        while *index < len && bytes[*index].is_ascii_digit() {
            *index += 1;
        }
    }
    if *index < len && bytes[*index] == b'.' {
        *index += 1;
        if *index >= len || !bytes[*index].is_ascii_digit() {
            return Err(json_value_error("JSON fraction has no digits"));
        }
        while *index < len && bytes[*index].is_ascii_digit() {
            *index += 1;
        }
    }
    if *index < len && (bytes[*index] == b'e' || bytes[*index] == b'E') {
        *index += 1;
        if *index < len && (bytes[*index] == b'+' || bytes[*index] == b'-') {
            *index += 1;
        }
        if *index >= len || !bytes[*index].is_ascii_digit() {
            return Err(json_value_error("JSON exponent has no digits"));
        }
        while *index < len && bytes[*index].is_ascii_digit() {
            *index += 1;
        }
    }
    Ok(())
}

/// Validates one JSON array (recursive, no trailing comma).
fn scan_json_array(raw: &str, index: &mut usize, depth: usize) -> Result<(), WireError> {
    let bytes = raw.as_bytes();
    *index += 1; // '['
    skip_ws(bytes, index);
    if bytes.get(*index) == Some(&b']') {
        *index += 1;
        return Ok(());
    }
    loop {
        scan_value(raw, index, depth + 1)?;
        skip_ws(bytes, index);
        match bytes.get(*index).copied() {
            Some(b',') => {
                *index += 1;
                skip_ws(bytes, index);
                if bytes.get(*index) == Some(&b']') {
                    return Err(json_value_error("trailing comma in JSON array"));
                }
            }
            Some(b']') => {
                *index += 1;
                return Ok(());
            }
            _ => return Err(json_value_error("malformed JSON array separator")),
        }
    }
}

/// Validates one JSON object (recursive, unique keys, no trailing comma).
fn scan_json_object(raw: &str, index: &mut usize, depth: usize) -> Result<(), WireError> {
    let bytes = raw.as_bytes();
    *index += 1; // '{'
    skip_ws(bytes, index);
    if bytes.get(*index) == Some(&b'}') {
        *index += 1;
        return Ok(());
    }
    let mut keys: Vec<&str> = Vec::new();
    loop {
        skip_ws(bytes, index);
        if bytes.get(*index) != Some(&b'"') {
            return Err(json_value_error("object key is not a JSON string"));
        }
        let key_start = *index + 1;
        scan_json_string(raw, index)?;
        let key = &raw[key_start..*index - 1];
        if keys.contains(&key) {
            return Err(json_value_error("duplicate object key"));
        }
        keys.push(key);
        skip_ws(bytes, index);
        if bytes.get(*index) != Some(&b':') {
            return Err(json_value_error("object member has no colon"));
        }
        *index += 1;
        scan_value(raw, index, depth + 1)?;
        skip_ws(bytes, index);
        match bytes.get(*index).copied() {
            Some(b',') => {
                *index += 1;
                skip_ws(bytes, index);
                if bytes.get(*index) == Some(&b'}') {
                    return Err(json_value_error("trailing comma in JSON object"));
                }
            }
            Some(b'}') => {
                *index += 1;
                return Ok(());
            }
            _ => return Err(json_value_error("malformed JSON object separator")),
        }
    }
}

impl<'a> JsonFields<'a> {
    /// Parses one compact JSON object into its top-level members. Duplicate
    /// keys, unquoted keys, unterminated values and trailing bytes are refused.
    fn parse(raw: &'a str) -> Result<JsonFields<'a>, WireError> {
        let bytes = raw.as_bytes();
        let mut index = 0usize;
        skip_ws(bytes, &mut index);
        if index >= bytes.len() || bytes[index] != b'{' {
            return Err(WireError::new(
                WireErrorKind::UnknownKind,
                "line is not a JSON object",
            ));
        }
        index += 1;
        let mut entries: Vec<(&'a str, &'a str)> = Vec::new();
        loop {
            skip_ws(bytes, &mut index);
            if index >= bytes.len() {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    "unterminated JSON object",
                ));
            }
            if bytes[index] == b'}' {
                index += 1;
                break;
            }
            if bytes[index] != b'"' {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    "object key is not a JSON string",
                ));
            }
            let key_start = index + 1;
            scan_json_string(raw, &mut index)?;
            let key = &raw[key_start..index - 1];
            skip_ws(bytes, &mut index);
            if index >= bytes.len() || bytes[index] != b':' {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    "object member has no colon",
                ));
            }
            index += 1;
            skip_ws(bytes, &mut index);
            let value_start = index;
            scan_value(raw, &mut index, 0)?;
            let value = &raw[value_start..index];
            if entries.iter().any(|(existing, _)| *existing == key) {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    format!("duplicate object key {key}"),
                ));
            }
            entries.push((key, value));
            skip_ws(bytes, &mut index);
            if index >= bytes.len() {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
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
                    return Err(WireError::new(
                        WireErrorKind::UnknownKind,
                        "malformed object separator",
                    ));
                }
            }
        }
        skip_ws(bytes, &mut index);
        if index != bytes.len() {
            return Err(WireError::new(
                WireErrorKind::UnknownKind,
                "trailing bytes after the JSON object",
            ));
        }
        Ok(JsonFields { entries })
    }

    fn get(&self, key: &str) -> Option<&'a str> {
        self.entries
            .iter()
            .find(|(existing, _)| *existing == key)
            .map(|(_, value)| *value)
    }
}

/// Decodes one JSON string literal (`"..."`) into its Rust text. Unsupported
/// escapes are refused (`None`). Mirrors the writer's `ensure_ascii=False` set.
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

fn string_field(fields: &JsonFields<'_>, key: &str) -> Option<String> {
    let raw = fields.get(key)?;
    if !raw.starts_with('"') || !raw.ends_with('"') {
        return None;
    }
    unescape_json_string(raw)
}

fn u64_field(fields: &JsonFields<'_>, key: &str) -> Option<u64> {
    fields.get(key)?.trim().parse::<u64>().ok()
}

fn string_array_field(fields: &JsonFields<'_>, key: &str) -> Option<Vec<String>> {
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

fn is_hex64(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn hex_field(fields: &JsonFields<'_>, key: &str) -> Result<String, WireError> {
    let value = string_field(fields, key).ok_or_else(|| {
        WireError::new(
            WireErrorKind::HashShapeInvalid,
            format!("{key} is not a JSON string"),
        )
    })?;
    if !is_hex64(&value) {
        return Err(WireError::new(
            WireErrorKind::HashShapeInvalid,
            format!("{key} is not 64 lowercase hex"),
        ));
    }
    Ok(value)
}

fn opt_hex_field(fields: &JsonFields<'_>, key: &str) -> Result<Option<String>, WireError> {
    let raw = fields.get(key).ok_or_else(|| {
        WireError::new(WireErrorKind::HashShapeInvalid, format!("{key} is missing"))
    })?;
    let trimmed = raw.trim();
    if trimmed == "null" {
        return Ok(None);
    }
    let value = unescape_json_string(trimmed).ok_or_else(|| {
        WireError::new(
            WireErrorKind::HashShapeInvalid,
            format!("{key} is not a JSON string"),
        )
    })?;
    if !is_hex64(&value) {
        return Err(WireError::new(
            WireErrorKind::HashShapeInvalid,
            format!("{key} is not 64 lowercase hex"),
        ));
    }
    Ok(Some(value))
}

fn reason_from_token(token: &str) -> Option<IncompleteReason> {
    match token {
        "hold" => Some(IncompleteReason::Hold),
        "text_only" => Some(IncompleteReason::TextOnly),
        "limit_reached" => Some(IncompleteReason::LimitReached),
        "unsupported_source" => Some(IncompleteReason::UnsupportedSource),
        "caller_scope" => Some(IncompleteReason::CallerScope),
        _ => None,
    }
}

fn line_kind(fields: &JsonFields<'_>) -> Result<String, WireError> {
    string_field(fields, "kind")
        .ok_or_else(|| WireError::new(WireErrorKind::UnknownKind, "line has no readable kind"))
}

fn is_closed_kind(kind: &str) -> bool {
    kind == KIND_MANIFEST
        || kind == KIND_POLICIES
        || kind == KIND_VIEW
        || kind == KIND_SEGMENT
        || kind == KIND_REFERENCE
        || kind == KIND_FOOTER
}

fn expect_schema(fields: &JsonFields<'_>, expected: &str) -> Result<(), WireError> {
    let schema = string_field(fields, "schema").ok_or_else(|| {
        WireError::new(WireErrorKind::SchemaMismatch, "line has no readable schema")
    })?;
    if schema != expected {
        return Err(WireError::new(
            WireErrorKind::SchemaMismatch,
            format!("expected schema {expected}, found {schema}"),
        ));
    }
    Ok(())
}

fn expect_version(fields: &JsonFields<'_>) -> Result<(), WireError> {
    let raw = fields.get("version").ok_or_else(|| {
        WireError::new(
            WireErrorKind::VersionMismatch,
            "line has no readable version",
        )
    })?;
    // The token must be the canonical decimal for the contract version: `01`,
    // `+1`, `1.0` and `1e0` are all refused even though some are valid JSON
    // numbers. This is the F02 strict-version fix.
    if raw.trim() != CONTRACT_VERSION.to_string() {
        return Err(WireError::new(
            WireErrorKind::VersionMismatch,
            format!("expected version {CONTRACT_VERSION}"),
        ));
    }
    Ok(())
}

fn contract_error(detail: impl Into<String>) -> WireError {
    WireError::new(WireErrorKind::ContractFieldInvalid, detail)
}

fn expect_string_value(
    fields: &JsonFields<'_>,
    key: &str,
    expected: &str,
) -> Result<(), WireError> {
    match string_field(fields, key) {
        Some(actual) if actual == expected => Ok(()),
        _ => Err(contract_error(format!("{key} must be {expected}"))),
    }
}

fn expect_true_value(fields: &JsonFields<'_>, key: &str) -> Result<(), WireError> {
    match bool_field(fields, key) {
        Some(true) => Ok(()),
        _ => Err(contract_error(format!("{key} must be true"))),
    }
}

/// Enforces the §4 manifest required keys and closed contract values
/// independently of the artifact's own seals (F01). Missing keys, ill-typed
/// values, and values outside the closed vocabulary are typed refusals.
fn expect_manifest_contract(manifest: &JsonFields<'_>) -> Result<(), WireError> {
    expect_string_value(manifest, "model", MODEL)?;
    expect_string_value(manifest, "profile", PROFILE)?;
    expect_string_value(manifest, "capability", CAPABILITY)?;
    expect_true_value(manifest, "non_authoritative")?;
    let generator_raw = manifest
        .get("generator")
        .ok_or_else(|| contract_error("manifest has no generator object"))?;
    let generator = JsonFields::parse(generator_raw.trim())
        .map_err(|_| contract_error("manifest generator is not an object"))?;
    if string_field(&generator, "name").is_none() {
        return Err(contract_error("generator.name is missing or not a string"));
    }
    if string_field(&generator, "version").is_none() {
        return Err(contract_error(
            "generator.version is missing or not a string",
        ));
    }
    let limits_raw = manifest
        .get("limits")
        .ok_or_else(|| contract_error("manifest has no limits object"))?;
    let limits = JsonFields::parse(limits_raw.trim())
        .map_err(|_| contract_error("manifest limits is not an object"))?;
    for key in ["max_line_bytes", "max_records", "max_text_bytes"] {
        if u64_field(&limits, key).is_none() {
            return Err(contract_error(format!(
                "manifest limits.{key} is not a u64"
            )));
        }
    }
    Ok(())
}

/// Enforces the §5 policies required keys and closed contract values
/// independently of the artifact's own seals (F01).
fn expect_policies_contract(policies: &JsonFields<'_>) -> Result<(), WireError> {
    expect_string_value(policies, "cleaning_mode", POLICY_CLEANING_MODE)?;
    expect_string_value(policies, "text_retention", POLICY_TEXT_RETENTION)?;
    expect_string_value(policies, "hold_text_only", POLICY_HOLD_TEXT_ONLY)?;
    expect_string_value(policies, "counts_scope", POLICY_COUNTS_SCOPE)?;
    expect_string_value(policies, "unknown_context", POLICY_UNKNOWN_CONTEXT)?;
    expect_string_value(policies, "normalization", POLICY_NORMALIZATION)?;
    expect_string_value(policies, "authenticity", POLICY_AUTHENTICITY)?;
    expect_true_value(policies, "non_authoritative")?;
    Ok(())
}

fn parse_completion(fields: &JsonFields<'_>) -> Result<(String, String, Vec<String>), WireError> {
    let completion = string_field(fields, "completion").ok_or_else(|| {
        WireError::new(
            WireErrorKind::CompletionMarkerInvalid,
            "footer has no completion",
        )
    })?;
    let basis = string_field(fields, "completion_basis").ok_or_else(|| {
        WireError::new(
            WireErrorKind::CompletionMarkerInvalid,
            "footer has no completion_basis",
        )
    })?;
    let reasons = string_array_field(fields, "incomplete_reasons").ok_or_else(|| {
        WireError::new(
            WireErrorKind::CompletionMarkerInvalid,
            "footer has no incomplete_reasons array",
        )
    })?;
    match completion.as_str() {
        "complete" => {
            if basis != BASIS_COMPLETE || !reasons.is_empty() {
                return Err(WireError::new(
                    WireErrorKind::CompletionMarkerInvalid,
                    "complete requires bounded_projection_complete and no reasons",
                ));
            }
        }
        "incomplete" => {
            if reasons.is_empty() {
                return Err(WireError::new(
                    WireErrorKind::CompletionMarkerInvalid,
                    "incomplete requires a non-empty incomplete_reasons set",
                ));
            }
            if reason_from_token(&basis).is_none() {
                return Err(WireError::new(
                    WireErrorKind::CompletionMarkerInvalid,
                    format!("unknown completion_basis {basis}"),
                ));
            }
            for reason in &reasons {
                if reason_from_token(reason).is_none() {
                    return Err(WireError::new(
                        WireErrorKind::CompletionMarkerInvalid,
                        format!("unknown incomplete_reason {reason}"),
                    ));
                }
            }
            if !reasons.iter().any(|reason| reason == &basis) {
                return Err(WireError::new(
                    WireErrorKind::CompletionMarkerInvalid,
                    "incomplete_reasons does not contain completion_basis",
                ));
            }
        }
        _ => {
            return Err(WireError::new(
                WireErrorKind::CompletionMarkerInvalid,
                format!("unknown completion {completion}"),
            ));
        }
    }
    Ok((completion, basis, reasons))
}

struct SummaryCounts {
    source_segments: u64,
    derived_segments: u64,
    text_chars: u64,
    text_bytes: u64,
}

fn counts_field(counts: &JsonFields<'_>, key: &str) -> Result<u64, WireError> {
    u64_field(counts, key).ok_or_else(|| {
        WireError::new(
            WireErrorKind::UnknownKind,
            format!("counts.{key} is not a u64"),
        )
    })
}

fn parse_counts(fields: &JsonFields<'_>) -> Result<SummaryCounts, WireError> {
    let raw = fields
        .get("counts")
        .ok_or_else(|| WireError::new(WireErrorKind::UnknownKind, "footer has no counts object"))?;
    let counts = JsonFields::parse(raw.trim())?;
    Ok(SummaryCounts {
        source_segments: counts_field(&counts, "source_segments")?,
        derived_segments: counts_field(&counts, "derived_segments")?,
        text_chars: counts_field(&counts, "text_chars")?,
        text_bytes: counts_field(&counts, "text_bytes")?,
    })
}

/// Structure-only inspection of a cleaned structural JSONL envelope.
///
/// This is deliberately **not** a read-back: it reconstructs no `Record`, view,
/// segment or reference and it never recomputes the seals. It checks the S01
/// envelope structure only (cleaned-projection contract §10): exactly one
/// trailing LF; no carriage return; no empty interior line; the fixed
/// `manifest → policies → records → footer` order; strict JSON value grammar
/// (RFC 8259 numbers, escapes, separators and unique object keys); closed
/// `kind`/schema/version on every line; the §4 manifest, §5 policies and footer
/// closed contract values (independent of the seals); the completion invariants;
/// and the hash-field shapes. Any violation is a closed typed refusal, never a
/// silent success.
pub fn inspect_cleaned_wire(text: &str) -> Result<WireEnvelopeSummary, WireError> {
    if text.contains('\r') {
        return Err(WireError::new(
            WireErrorKind::CarriageReturn,
            "document contains a carriage return",
        ));
    }
    if !text.ends_with('\n') {
        return Err(WireError::new(
            WireErrorKind::MissingTrailingLf,
            "document does not end with LF",
        ));
    }
    let body = &text[..text.len() - 1];
    if body.is_empty() {
        return Err(WireError::new(WireErrorKind::EmptyLine, "empty document"));
    }
    let lines: Vec<&str> = body.split('\n').collect();
    if lines.iter().any(|line| line.is_empty()) {
        return Err(WireError::new(
            WireErrorKind::EmptyLine,
            "document contains an empty line",
        ));
    }

    let mut parsed: Vec<JsonFields<'_>> = Vec::with_capacity(lines.len());
    let mut kinds: Vec<String> = Vec::with_capacity(lines.len());
    for line in &lines {
        let fields = JsonFields::parse(line)?;
        let kind = line_kind(&fields)?;
        if !is_closed_kind(&kind) {
            return Err(WireError::new(
                WireErrorKind::UnknownKind,
                format!("unknown line kind {kind}"),
            ));
        }
        kinds.push(kind);
        parsed.push(fields);
    }

    // Positional envelope: line 0 manifest, line 1 policies, last footer.
    if kinds[0] == KIND_POLICIES {
        return Err(WireError::new(
            WireErrorKind::MisorderedPolicies,
            "policies precedes the manifest",
        ));
    }
    if kinds[0] != KIND_MANIFEST {
        return Err(WireError::new(
            WireErrorKind::MissingManifest,
            "first line is not a manifest",
        ));
    }
    if kinds.len() < 2 {
        return Err(WireError::new(
            WireErrorKind::MissingPolicies,
            "no policies line",
        ));
    }
    if kinds[1] == KIND_MANIFEST {
        return Err(WireError::new(
            WireErrorKind::MisorderedManifest,
            "manifest appears after the first line",
        ));
    }
    if kinds[1] != KIND_POLICIES {
        return Err(WireError::new(
            WireErrorKind::MissingPolicies,
            "second line is not a policies line",
        ));
    }

    let last_index = kinds.len() - 1;
    let footer_positions: Vec<usize> = kinds
        .iter()
        .enumerate()
        .filter(|(_, kind)| kind.as_str() == KIND_FOOTER)
        .map(|(index, _)| index)
        .collect();
    if footer_positions.is_empty() {
        return Err(WireError::new(
            WireErrorKind::MissingFooter,
            "document has no footer",
        ));
    }
    if footer_positions.len() > 1 {
        return Err(WireError::new(
            WireErrorKind::MisorderedFooter,
            "document has more than one footer",
        ));
    }
    if footer_positions[0] != last_index {
        return Err(WireError::new(
            WireErrorKind::TrailingRecordAfterFooter,
            "records follow the footer",
        ));
    }
    if kinds[2..last_index]
        .iter()
        .any(|kind| kind == KIND_MANIFEST)
    {
        return Err(WireError::new(
            WireErrorKind::MisorderedManifest,
            "a manifest line appears inside the body",
        ));
    }
    if kinds[2..last_index]
        .iter()
        .any(|kind| kind == KIND_POLICIES)
    {
        return Err(WireError::new(
            WireErrorKind::MisorderedPolicies,
            "a policies line appears inside the body",
        ));
    }

    // Manifest line 0.
    let manifest = &parsed[0];
    expect_schema(manifest, MANIFEST_SCHEMA)?;
    expect_version(manifest)?;
    expect_manifest_contract(manifest)?;
    let source_raw = manifest.get("source").ok_or_else(|| {
        WireError::new(
            WireErrorKind::HashShapeInvalid,
            "manifest has no source object",
        )
    })?;
    let source = JsonFields::parse(source_raw.trim())?;
    let _source_sha256 = hex_field(&source, "sha256")?;
    let _source_bytes = u64_field(&source, "bytes")
        .ok_or_else(|| contract_error("manifest source.bytes is not a u64"))?;
    let parent_raw = manifest.get("parent").ok_or_else(|| {
        WireError::new(
            WireErrorKind::HashShapeInvalid,
            "manifest has no parent object",
        )
    })?;
    let parent = JsonFields::parse(parent_raw.trim())?;
    let _parent_records = opt_hex_field(&parent, "records_seal_hash")?;
    let _parent_manifest = opt_hex_field(&parent, "manifest_hash")?;

    // Policies line 1.
    let policies = &parsed[1];
    expect_schema(policies, POLICIES_SCHEMA)?;
    expect_version(policies)?;
    expect_policies_contract(policies)?;

    // Record lines.
    let mut views = 0u64;
    let mut segments = 0u64;
    let mut references = 0u64;
    for index in 2..last_index {
        let fields = &parsed[index];
        match kinds[index].as_str() {
            KIND_VIEW => {
                expect_schema(fields, VIEW_SCHEMA)?;
                views += 1;
            }
            KIND_SEGMENT => {
                expect_schema(fields, SEGMENT_SCHEMA)?;
                segments += 1;
            }
            KIND_REFERENCE => {
                expect_schema(fields, REFERENCE_SCHEMA)?;
                references += 1;
            }
            _ => {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    format!("unexpected record kind {}", kinds[index]),
                ));
            }
        }
    }

    // Footer line.
    let footer = &parsed[last_index];
    expect_schema(footer, FOOTER_SCHEMA)?;
    expect_version(footer)?;
    expect_true_value(footer, "non_authoritative")?;
    let (completion, completion_basis, incomplete_reasons) = parse_completion(footer)?;
    let records_seal_hash = hex_field(footer, "records_seal_hash")?;
    let manifest_hash = hex_field(footer, "manifest_hash")?;
    let counts = parse_counts(footer)?;

    Ok(WireEnvelopeSummary {
        contract_version: CONTRACT_VERSION,
        records: views + segments + references,
        views,
        segments,
        references,
        source_segments: counts.source_segments,
        derived_segments: counts.derived_segments,
        text_chars: counts.text_chars,
        text_bytes: counts.text_bytes,
        completion,
        completion_basis,
        incomplete_reasons,
        records_seal_hash: Some(records_seal_hash),
        manifest_hash: Some(manifest_hash),
    })
}

// ---------------------------------------------------------------- read-back #

fn record_invalid(key: &str, detail: impl fmt::Display) -> WireError {
    WireError::new(
        WireErrorKind::RecordFieldInvalid,
        format!("record field {key}: {detail}"),
    )
}

fn bool_field(fields: &JsonFields<'_>, key: &str) -> Option<bool> {
    match fields.get(key)?.trim() {
        "true" => Some(true),
        "false" => Some(false),
        _ => None,
    }
}

fn record_string(fields: &JsonFields<'_>, key: &str) -> Result<String, WireError> {
    string_field(fields, key).ok_or_else(|| record_invalid(key, "missing or not a JSON string"))
}

fn opt_record_string(fields: &JsonFields<'_>, key: &str) -> Result<Option<String>, WireError> {
    let raw = fields
        .get(key)
        .ok_or_else(|| record_invalid(key, "missing"))?;
    let trimmed = raw.trim();
    if trimmed == "null" {
        return Ok(None);
    }
    unescape_json_string(trimmed)
        .map(Some)
        .ok_or_else(|| record_invalid(key, "not a JSON string or null"))
}

fn record_u64(fields: &JsonFields<'_>, key: &str) -> Result<u64, WireError> {
    u64_field(fields, key).ok_or_else(|| record_invalid(key, "missing or not a u64"))
}

fn record_usize(fields: &JsonFields<'_>, key: &str) -> Result<usize, WireError> {
    let value = record_u64(fields, key)?;
    usize::try_from(value).map_err(|_| record_invalid(key, "does not fit usize"))
}

fn record_bool(fields: &JsonFields<'_>, key: &str) -> Result<bool, WireError> {
    bool_field(fields, key).ok_or_else(|| record_invalid(key, "missing or not a bool"))
}

fn record_string_array(fields: &JsonFields<'_>, key: &str) -> Result<Vec<String>, WireError> {
    string_array_field(fields, key)
        .ok_or_else(|| record_invalid(key, "missing or not a string array"))
}

fn parse_text_slot(token: &str) -> Result<TextSlot, WireError> {
    match token {
        "text" => Ok(TextSlot::Text),
        "tail" => Ok(TextSlot::Tail),
        _ => Err(record_invalid("slot", token)),
    }
}

fn parse_segment_origin(fields: &JsonFields<'_>) -> Result<SegmentOrigin, WireError> {
    let token = record_string(fields, "origin")?;
    if token == "source_fragment" {
        return Ok(SegmentOrigin::SourceFragment);
    }
    if let Some(rest) = token.strip_prefix("derived:") {
        return ReaderDerivedKind::from_wire(rest)
            .map(SegmentOrigin::Derived)
            .map_err(|_| record_invalid("origin", token.as_str()));
    }
    Err(record_invalid("origin", token.as_str()))
}

fn parse_segment_span(fields: &JsonFields<'_>) -> Result<Option<ReaderFragmentSpan>, WireError> {
    let raw = fields
        .get("span")
        .ok_or_else(|| record_invalid("span", "missing"))?;
    let trimmed = raw.trim();
    if trimmed == "null" {
        return Ok(None);
    }
    let inner = JsonFields::parse(trimmed)?;
    let fragment = record_string(&inner, "fragment")?;
    let start = record_usize(&inner, "start")?;
    let end = record_usize(&inner, "end")?;
    Ok(Some(ReaderFragmentSpan::new(
        FragmentRef::new(fragment),
        start,
        end,
    )))
}

fn parse_cleaned_counts(fields: &JsonFields<'_>) -> Result<CleanedCounts, WireError> {
    let raw = fields
        .get("counts")
        .ok_or_else(|| record_invalid("counts", "missing"))?;
    let counts = JsonFields::parse(raw.trim())?;
    Ok(CleanedCounts {
        views: counts_field(&counts, "views")?,
        segments: counts_field(&counts, "segments")?,
        references: counts_field(&counts, "references")?,
        source_segments: counts_field(&counts, "source_segments")?,
        derived_segments: counts_field(&counts, "derived_segments")?,
        text_chars: counts_field(&counts, "text_chars")?,
        text_bytes: counts_field(&counts, "text_bytes")?,
        records: counts_field(&counts, "records")?,
    })
}

fn completion_from_parts(
    completion: &str,
    basis: &str,
    reasons: &[String],
) -> Result<WireCompletion, WireError> {
    match completion {
        "complete" => Ok(WireCompletion::Complete),
        "incomplete" => {
            let basis = reason_from_token(basis)
                .ok_or_else(|| record_invalid("completion_basis", basis))?;
            let mut parsed = Vec::with_capacity(reasons.len());
            for reason in reasons {
                parsed.push(
                    reason_from_token(reason)
                        .ok_or_else(|| record_invalid("incomplete_reasons", reason.as_str()))?,
                );
            }
            Ok(WireCompletion::Incomplete {
                basis,
                reasons: parsed,
            })
        }
        _ => Err(record_invalid("completion", completion)),
    }
}

fn enforce_record_group_order(kinds: &[String]) -> Result<(), WireError> {
    let mut phase = 0u8;
    for kind in kinds {
        match kind.as_str() {
            KIND_VIEW => {
                if phase > 0 {
                    return Err(WireError::new(
                        WireErrorKind::RecordGroupOrder,
                        "view record after a segment or reference record",
                    ));
                }
            }
            KIND_SEGMENT => {
                if phase > 1 {
                    return Err(WireError::new(
                        WireErrorKind::RecordGroupOrder,
                        "segment record after a reference record",
                    ));
                }
                phase = 1;
            }
            KIND_REFERENCE => phase = 2,
            _ => {}
        }
    }
    Ok(())
}

fn reconstruct_view(fields: &JsonFields<'_>) -> Result<ProjectedView, WireError> {
    let id = ViewId::new(record_string(fields, "id")?);
    let view_kind = record_string(fields, "view_kind")?;
    let kind = ReaderViewKind::from_wire(&view_kind)
        .map_err(|_| record_invalid("view_kind", view_kind.as_str()))?;
    let element_ref = ElementRef::new(record_string(fields, "element_ref")?);
    let parent_view = opt_record_string(fields, "parent_view")?.map(ViewId::new);
    let children = record_string_array(fields, "children")?
        .into_iter()
        .map(ViewId::new)
        .collect();
    let segment_refs = record_string_array(fields, "segment_refs")?
        .into_iter()
        .map(SegmentId::new)
        .collect();
    let reference_refs = record_string_array(fields, "reference_refs")?
        .into_iter()
        .map(ReferenceId::new)
        .collect();
    let flags_raw = fields
        .get("flags")
        .ok_or_else(|| record_invalid("flags", "missing"))?;
    let flags_fields = JsonFields::parse(flags_raw.trim())?;
    let flags = ViewFlags::new(record_bool(&flags_fields, "empty")?);
    Ok(ProjectedView {
        id,
        kind,
        element_ref,
        parent_view,
        children,
        segment_refs,
        reference_refs,
        flags,
    })
}

fn reconstruct_segment(
    fields: &JsonFields<'_>,
) -> Result<(ProjectedSegment, SegmentText), WireError> {
    let id = SegmentId::new(record_string(fields, "id")?);
    let view = ViewId::new(record_string(fields, "view")?);
    let ordinal = record_usize(fields, "ordinal")?;
    let segment_kind_token = record_string(fields, "segment_kind")?;
    let segment_kind = ReaderSegmentKind::from_wire(&segment_kind_token)
        .map_err(|_| record_invalid("segment_kind", segment_kind_token.as_str()))?;
    let fragment_ref = opt_record_string(fields, "fragment_ref")?.map(FragmentRef::new);
    let slot = match opt_record_string(fields, "slot")? {
        None => None,
        Some(token) => Some(parse_text_slot(&token)?),
    };
    let span = parse_segment_span(fields)?;
    let output_start = record_usize(fields, "output_start")?;
    let output_end = record_usize(fields, "output_end")?;
    let chars = record_usize(fields, "chars")?;
    let origin = parse_segment_origin(fields)?;
    let semantic_token = record_string(fields, "semantic")?;
    let semantic = ReaderSemantic::from_wire(&semantic_token)
        .map_err(|_| record_invalid("semantic", semantic_token.as_str()))?;
    let contextual = record_bool(fields, "contextual")?;
    let element_ref = ElementRef::new(record_string(fields, "element_ref")?);
    let source_pos = record_usize(fields, "source_pos")?;
    let text = record_string(fields, "text")?;
    let text_chars = record_u64(fields, "text_chars")?;
    let text_bytes = record_u64(fields, "text_bytes")?;

    // A source segment must not carry a rendered literal (`verify_source_segment`
    // rejects `text.is_some()`); the wire text is preserved in `inline_texts`.
    let projection_text = match origin {
        SegmentOrigin::SourceFragment => None,
        SegmentOrigin::Derived(_) => Some(text.clone()),
    };
    let segment = ProjectedSegment {
        id: id.clone(),
        view,
        ordinal,
        segment_kind,
        fragment_ref: fragment_ref.clone(),
        slot,
        span,
        output_start,
        output_end,
        chars,
        origin,
        semantic,
        contextual,
        element_ref,
        source_pos,
        text: projection_text,
    };
    let inline = SegmentText {
        segment_id: id.as_str().to_string(),
        fragment_ref: fragment_ref.map(|fragment| fragment.as_str().to_string()),
        text,
        chars: text_chars,
        text_bytes,
    };
    Ok((segment, inline))
}

fn reconstruct_reference(fields: &JsonFields<'_>) -> Result<ProjectedReference, WireError> {
    let id = ReferenceId::new(record_string(fields, "id")?);
    let view = ViewId::new(record_string(fields, "view")?);
    let ordinal = record_usize(fields, "ordinal")?;
    let reference_type_token = record_string(fields, "reference_type")?;
    let reference_type = ReaderReferenceType::from_wire(&reference_type_token)
        .map_err(|_| record_invalid("reference_type", reference_type_token.as_str()))?;
    let element_ref = ElementRef::new(record_string(fields, "element_ref")?);
    let source_pos = record_usize(fields, "source_pos")?;
    let resolved = record_bool(fields, "resolved")?;
    Ok(ProjectedReference {
        id,
        view,
        ordinal,
        reference_type,
        element_ref,
        source_pos,
        resolved,
    })
}

/// Reads a cleaned structural JSONL artifact back into a typed, verify-shaped
/// [`CleanedProjection`].
///
/// The envelope is first checked with exactly the structural rules of
/// [`inspect_cleaned_wire`] (trailing LF, no CR, no empty line, the fixed
/// `manifest → policies → records → footer` order, strict JSON grammar, closed
/// `kind`/schema/version, and the closed §4/§5 contract values),
/// then every record is reconstructed through the frozen reader vocabulary. The
/// body must keep the `views → segments → references` group order. Both seals are
/// recomputed over the exact line bytes and must match the footer, so an
/// accidentally corrupted document is refused.
///
/// This is a structural read-back, not an authenticity or legal-completeness
/// claim: a re-sealed semantic tamper still parses here and is caught only by
/// the independent `cleaned_verifier` check.
pub fn read_cleaned_wire(text: &str) -> Result<CleanedProjection, WireError> {
    // Same structural and closed-contract envelope check as the S01 inspection.
    let _summary = inspect_cleaned_wire(text)?;

    // `inspect_cleaned_wire` guarantees: no CR, exactly one trailing LF and no
    // empty interior line, so this split is total.
    let body = &text[..text.len() - 1];
    let lines: Vec<&str> = body.split('\n').collect();
    let last_index = lines.len() - 1;
    let mut parsed: Vec<JsonFields<'_>> = Vec::with_capacity(lines.len());
    let mut kinds: Vec<String> = Vec::with_capacity(lines.len());
    for line in &lines {
        let fields = JsonFields::parse(line)?;
        kinds.push(line_kind(&fields)?);
        parsed.push(fields);
    }

    enforce_record_group_order(&kinds[2..last_index])?;

    let manifest = &parsed[0];
    let source_raw = manifest
        .get("source")
        .ok_or_else(|| record_invalid("source", "missing"))?;
    let source_fields = JsonFields::parse(source_raw.trim())?;
    let source = SourcePin {
        sha256: hex_field(&source_fields, "sha256")?,
        bytes: record_u64(&source_fields, "bytes")?,
    };
    let parent_raw = manifest
        .get("parent")
        .ok_or_else(|| record_invalid("parent", "missing"))?;
    let parent_fields = JsonFields::parse(parent_raw.trim())?;
    let parent = ParentSealPin {
        records_seal_hash: opt_hex_field(&parent_fields, "records_seal_hash")?,
        manifest_hash: opt_hex_field(&parent_fields, "manifest_hash")?,
    };

    let footer = &parsed[last_index];
    let (completion_token, basis_token, reasons) = parse_completion(footer)?;
    let completion = completion_from_parts(&completion_token, &basis_token, &reasons)?;
    let counts = parse_cleaned_counts(footer)?;
    let footer_records_seal = hex_field(footer, "records_seal_hash")?;
    let footer_manifest = hex_field(footer, "manifest_hash")?;

    let mut views = Vec::new();
    let mut segments = Vec::new();
    let mut references = Vec::new();
    let mut inline_texts = Vec::new();
    for index in 2..last_index {
        let fields = &parsed[index];
        match kinds[index].as_str() {
            KIND_VIEW => views.push(reconstruct_view(fields)?),
            KIND_SEGMENT => {
                let (segment, inline) = reconstruct_segment(fields)?;
                segments.push(segment);
                inline_texts.push(inline);
            }
            KIND_REFERENCE => references.push(reconstruct_reference(fields)?),
            _ => {
                return Err(WireError::new(
                    WireErrorKind::UnknownKind,
                    format!("unexpected record kind {}", kinds[index]),
                ));
            }
        }
    }

    // Seal recomputation runs after reconstruction so a line that is simply not
    // reconstructible is reported as a record-field refusal rather than masked by
    // the seal mismatch it also causes.
    let record_lines: Vec<&str> = lines[2..last_index].to_vec();
    let recomputed_records_seal = records_seal_hash(lines[1], &record_lines);
    if recomputed_records_seal != footer_records_seal {
        return Err(WireError::new(
            WireErrorKind::HashMismatch,
            "records_seal_hash does not recompute over the file lines",
        ));
    }
    let footer_body = render_line(&footer_json(&completion, &counts, None, None));
    let recomputed_manifest = manifest_hash(lines[0], &footer_records_seal, &footer_body);
    if recomputed_manifest != footer_manifest {
        return Err(WireError::new(
            WireErrorKind::HashMismatch,
            "manifest_hash does not recompute over the manifest and footer",
        ));
    }

    Ok(CleanedProjection {
        contract_version: u64_field(manifest, "version")
            .ok_or_else(|| record_invalid("version", "missing or not a u64"))?,
        source,
        parent,
        projection: ReaderProjection {
            views,
            segments,
            references,
            content_hash: None,
        },
        inline_texts,
        completion,
        counts,
        records_seal_hash: footer_records_seal,
        manifest_hash: footer_manifest,
    })
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reader_projection::{build_projection, canonical_projection_bytes};
    use crate::reader_verifier::verify_projection;
    use crate::source_package::{capture, Limits};

    fn fixture_package() -> Package {
        const XML: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");
        capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture")
    }

    fn fixture_projection(package: &Package) -> ReaderProjection {
        build_projection(package.records()).expect("projection must build")
    }

    fn render(
        package: &Package,
        projection: &ReaderProjection,
        completion: &WireCompletion,
        limits: &WireLimits,
    ) -> Result<String, WireError> {
        render_cleaned_projection(package, projection, completion, limits)
    }

    #[test]
    fn renders_compact_deterministic_envelope() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let limits = WireLimits::default();

        let first = render(&package, &projection, &WireCompletion::Complete, &limits)
            .expect("first render");
        let second = render(&package, &projection, &WireCompletion::Complete, &limits)
            .expect("second render");
        assert_eq!(
            first, second,
            "two renders on equal input must be identical"
        );

        assert!(
            first.ends_with('\n'),
            "document must end with exactly one LF"
        );
        assert!(!first.contains('\r'), "no carriage return is permitted");
        assert_eq!(
            first.matches('\n').count(),
            first.lines().count(),
            "only the terminal LF may be a raw newline"
        );

        let lines: Vec<&str> = first.split_terminator('\n').collect();
        assert!(lines.len() >= 4, "manifest, policies, footer at minimum");
        assert!(
            lines[0].starts_with("{\"capability\":"),
            "ascending keys put capability first: {}",
            lines[0]
        );
        assert!(lines[0].contains("\"kind\":\"cleaned_projection_manifest\""));
        assert!(lines[1].contains("\"kind\":\"cleaned_projection_policies\""));
        assert!(lines[1].starts_with("{\"authenticity\":"));
        let last = lines.last().expect("non-empty document");
        assert!(last.contains("\"kind\":\"cleaned_projection_footer\""));
        assert!(last.starts_with("{\"completion\":"));

        for line in &lines {
            assert!(line.starts_with('{'), "every line is an object: {line}");
            assert!(line.ends_with('}'), "every line is an object: {line}");
        }
        assert!(first.contains("\"completion\":\"complete\""));
        assert!(first.contains("\"incomplete_reasons\":[]"));
        assert!(first.contains("\"text_retention\":\"full_decoded_text_retained_inline\""));
        assert!(first.contains("\"records_seal_hash\":\""));
        assert!(first.contains("\"manifest_hash\":\""));
    }

    #[test]
    fn incomplete_render_carries_closed_reasons() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let completion = WireCompletion::Incomplete {
            basis: IncompleteReason::CallerScope,
            reasons: vec![
                IncompleteReason::CallerScope,
                IncompleteReason::LimitReached,
            ],
        };
        let out = render(&package, &projection, &completion, &WireLimits::default())
            .expect("honest partial export must render");
        assert!(out.contains("\"completion\":\"incomplete\""));
        assert!(out.contains("\"completion_basis\":\"caller_scope\""));
        assert!(out.contains("\"incomplete_reasons\":[\"caller_scope\",\"limit_reached\"]"));

        let readback = read_cleaned_wire(&out).expect("incomplete read-back");
        assert_eq!(readback.completion, completion);
    }

    #[test]
    fn refuses_incomplete_without_reason() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let limits = WireLimits::default();

        let no_reason = WireCompletion::Incomplete {
            basis: IncompleteReason::CallerScope,
            reasons: Vec::new(),
        };
        let error = render(&package, &projection, &no_reason, &limits).expect_err("must refuse");
        assert_eq!(error.kind(), WireErrorKind::CompletionMarkerInvalid);

        let basis_absent = WireCompletion::Incomplete {
            basis: IncompleteReason::CallerScope,
            reasons: vec![IncompleteReason::Hold],
        };
        let error = render(&package, &projection, &basis_absent, &limits).expect_err("must refuse");
        assert_eq!(error.kind(), WireErrorKind::CompletionMarkerInvalid);
    }

    #[test]
    fn refuses_complete_with_text_loss() {
        let package = fixture_package();
        let mut projection = fixture_projection(&package);
        let source_index = projection
            .segments
            .iter()
            .position(|segment| segment.origin == SegmentOrigin::SourceFragment)
            .expect("fixture must carry a source segment");
        projection.segments.remove(source_index);

        let error = render(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect_err("complete-with-loss must refuse");
        assert_eq!(error.kind(), WireErrorKind::TextLoss);
    }

    #[test]
    fn refuses_over_line_and_record_limits() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let completion = WireCompletion::Complete;

        let line_limits = WireLimits {
            max_line_bytes: 1,
            ..WireLimits::default()
        };
        let error =
            render(&package, &projection, &completion, &line_limits).expect_err("must refuse");
        assert_eq!(error.kind(), WireErrorKind::LineBytesLimit);

        let record_limits = WireLimits {
            max_records: 1,
            ..WireLimits::default()
        };
        let error =
            render(&package, &projection, &completion, &record_limits).expect_err("must refuse");
        assert_eq!(error.kind(), WireErrorKind::RecordsLimit);

        let text_limits = WireLimits {
            max_text_bytes: 1,
            ..WireLimits::default()
        };
        let error =
            render(&package, &projection, &completion, &text_limits).expect_err("must refuse");
        assert_eq!(error.kind(), WireErrorKind::TextBytesLimit);
    }

    #[test]
    fn refuses_provenance_mismatch() {
        use crate::reader_contract::ElementRef;

        let package = fixture_package();
        let mut projection = fixture_projection(&package);
        let source = projection
            .segments
            .iter_mut()
            .find(|segment| segment.origin == SegmentOrigin::SourceFragment)
            .expect("fixture must carry a source segment");
        // The fragment still resolves, but its substrate owner no longer matches
        // the segment's declared element: provenance must be refused, not
        // silently repaired.
        source.element_ref = ElementRef::new("e-does-not-exist");

        let error = render(
            &package,
            &projection,
            &WireCompletion::Incomplete {
                basis: IncompleteReason::Hold,
                reasons: vec![IncompleteReason::Hold],
            },
            &WireLimits::default(),
        )
        .expect_err("provenance mismatch must refuse");
        assert_eq!(error.kind(), WireErrorKind::ProvenanceMismatch);
    }

    #[test]
    fn refuses_fragment_missing_and_provenance_mismatch() {
        let package = fixture_package();
        let mut projection = fixture_projection(&package);
        let source = projection
            .segments
            .iter_mut()
            .find(|segment| segment.origin == SegmentOrigin::SourceFragment)
            .expect("fixture must carry a source segment");
        source.fragment_ref = Some(crate::reader_contract::FragmentRef::new("t-missing"));

        let error = render(
            &package,
            &projection,
            &WireCompletion::Incomplete {
                basis: IncompleteReason::Hold,
                reasons: vec![IncompleteReason::Hold],
            },
            &WireLimits::default(),
        )
        .expect_err("missing fragment must refuse");
        assert_eq!(error.kind(), WireErrorKind::FragmentMissing);
    }

    #[test]
    fn limits_carry_reader_view_vocabulary() {
        use crate::reader_contract::{ReaderSemantic, ReaderViewKind};
        // Guard the shared vocabulary imports: the writer must not drift from
        // the frozen reader tokens.
        assert_eq!(ReaderViewKind::Paragraph.as_str(), "paragraph");
        assert_eq!(ReaderSegmentKind::Text.as_str(), "text");
        assert_eq!(ReaderSemantic::Body.as_str(), "body");
    }

    // -------------------------------------------------- read-back tests #

    fn render_complete(package: &Package, projection: &ReaderProjection) -> String {
        render(
            package,
            projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("complete render")
    }

    #[test]
    fn read_back_reconstructs_verify_shaped_projection() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render_complete(&package, &projection);

        let readback = read_cleaned_wire(&artifact).expect("read-back must succeed");
        assert_eq!(readback.contract_version, CONTRACT_VERSION);
        assert_eq!(readback.source.sha256, package.manifest().source.sha256);
        assert_eq!(readback.source.bytes, package.manifest().source.bytes);
        assert_eq!(
            readback.parent.records_seal_hash,
            package.footer().records_seal_hash
        );
        assert_eq!(
            readback.parent.manifest_hash,
            package.footer().manifest_hash
        );
        assert_eq!(readback.completion, WireCompletion::Complete);
        assert_eq!(readback.counts.views, projection.views.len() as u64);
        assert_eq!(readback.counts.segments, projection.segments.len() as u64);
        assert_eq!(
            readback.counts.references,
            projection.references.len() as u64
        );
        assert_eq!(
            readback.counts.records,
            readback.counts.views + readback.counts.segments + readback.counts.references
        );
        assert_eq!(readback.inline_texts.len(), projection.segments.len());
        assert!(verify_projection(&readback.projection, package.records()).is_ok());
        // The read-back projection is byte-identical to the producer projection
        // under the canonical form, proving the transport is lossless.
        assert_eq!(
            canonical_projection_bytes(&readback.projection),
            canonical_projection_bytes(&projection)
        );
        for segment in &readback.projection.segments {
            if segment.origin == SegmentOrigin::SourceFragment {
                assert!(
                    segment.text.is_none(),
                    "source segments must not carry a rendered literal"
                );
            } else {
                assert!(
                    segment.text.is_some(),
                    "derived segments must carry the generated literal"
                );
            }
        }
    }

    fn flip_seal_hex(artifact: &str, key: &str) -> String {
        let marker = format!("\"{key}\":\"");
        let position = artifact.rfind(&marker).expect("seal field present") + marker.len();
        let mut bytes = artifact.as_bytes().to_vec();
        bytes[position] = match bytes[position] {
            b'a' => b'b',
            _ => b'a',
        };
        String::from_utf8(bytes).expect("tampered artifact stays utf-8")
    }

    #[test]
    fn read_back_refuses_seal_mismatch() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render_complete(&package, &projection);

        let bad_records = flip_seal_hex(&artifact, "records_seal_hash");
        assert_eq!(
            read_cleaned_wire(&bad_records)
                .expect_err("records seal mismatch must refuse")
                .kind(),
            WireErrorKind::HashMismatch
        );

        let bad_manifest = flip_seal_hex(&artifact, "manifest_hash");
        assert_eq!(
            read_cleaned_wire(&bad_manifest)
                .expect_err("manifest seal mismatch must refuse")
                .kind(),
            WireErrorKind::HashMismatch
        );
    }

    fn move_first_reference_before_first_segment(artifact: &str) -> String {
        let mut lines: Vec<String> = artifact.lines().map(str::to_string).collect();
        let segment_index = lines
            .iter()
            .position(|line| line.contains("\"kind\":\"cleaned_projection_segment\""))
            .expect("a segment record");
        let reference_index = lines
            .iter()
            .position(|line| line.contains("\"kind\":\"cleaned_projection_reference\""))
            .expect("a reference record");
        assert!(
            reference_index > segment_index,
            "fixture must place a reference after a segment"
        );
        let reference = lines.remove(reference_index);
        lines.insert(segment_index, reference);
        let mut out = lines.join("\n");
        out.push('\n');
        out
    }

    #[test]
    fn read_back_refuses_misordered_record_groups() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render_complete(&package, &projection);
        let tampered = move_first_reference_before_first_segment(&artifact);
        assert_eq!(
            read_cleaned_wire(&tampered)
                .expect_err("misordered groups must refuse")
                .kind(),
            WireErrorKind::RecordGroupOrder
        );
    }

    fn drop_field_from_first_segment(artifact: &str, key: &str) -> String {
        let mut lines: Vec<String> = artifact.lines().map(str::to_string).collect();
        let index = lines
            .iter()
            .position(|line| line.contains("\"kind\":\"cleaned_projection_segment\""))
            .expect("a segment record");
        let line = &lines[index];
        let marker = format!("\"{key}\":");
        let start = line.find(&marker).expect("field present");
        let after = start + marker.len();
        let comma = line[after..]
            .find(',')
            .unwrap_or_else(|| panic!("field {key} must be comma-terminated"));
        let end = after + comma + 1;
        let mut new_line = String::with_capacity(line.len());
        new_line.push_str(&line[..start]);
        new_line.push_str(&line[end..]);
        lines[index] = new_line;
        let mut out = lines.join("\n");
        out.push('\n');
        out
    }

    #[test]
    fn read_back_refuses_missing_record_field() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = render_complete(&package, &projection);
        let tampered = drop_field_from_first_segment(&artifact, "contextual");
        assert_eq!(
            read_cleaned_wire(&tampered)
                .expect_err("missing field must refuse")
                .kind(),
            WireErrorKind::RecordFieldInvalid
        );
    }

    #[test]
    fn export_self_checks_and_writes() {
        let package = fixture_package();
        let projection = fixture_projection(&package);
        let artifact = export_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("export must self-check");
        assert!(read_cleaned_wire(&artifact).is_ok());

        let mut buffer: Vec<u8> = Vec::new();
        write_cleaned_projection(&artifact, &mut buffer).expect("write must succeed");
        assert_eq!(buffer, artifact.as_bytes());
    }
}
