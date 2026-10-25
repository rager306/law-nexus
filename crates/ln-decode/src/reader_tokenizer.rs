//! S07 tokenizer consumer over the saved cleaned wire JSONL (M223 / S07 / T02).
//!
//! Executable core of
//! `prd/architecture/intermediate-source-consumer-acceptance-contract.md`
//! (`reader_tokenizer`). The module turns the **saved cleaned wire JSONL** plus
//! the already-decoded substrate into an ordered, lossless token stream over
//! each primary view's clean text channel. Every token carries composite
//! provenance and is bound to one verified [`DocumentIdentity`].
//!
//! # Consumers without XML re-parse
//!
//! The consumer reads only materialized layers: the read-back
//! [`CleanedProjection`] (view/segment anchors, output offsets) and the
//! already-captured [`Package`] substrate (decoded fragment values, read
//! through [`ReaderRecordIndex`]). It **never** opens the source XML: there is
//! no `quick_xml`, no `capture`, and no byte re-parse anywhere on the read
//! path. The reading order is re-derived from the substrate by the frozen
//! [`ReadingOrderIndex`] and never from the projection's declared refs.
//!
//! # Composite provenance
//!
//! A token carries exactly one of three provenance forms:
//!
//! * `source_fragment` — a token wholly inside one source-fragment unit carries
//!   `fragment_ref` + `slot` + `span` + `element_ref` + `source_pos`. The span
//!   is the unit's decoded span offset by the token's local offset inside the
//!   unit: `token_span.start = span.start + local_start`.
//! * `derived_control` — a token that is exactly one documented derived control
//!   carries `derived_kind` + `element_ref` + `source_pos` + `rule_profile` and
//!   **no** `fragment_ref` and **no** `span`. A derived control never receives a
//!   fabricated fragment or span.
//! * `composite_range` — a token that crosses a unit boundary (several source
//!   fragments, a fragment and a derived separator, or several derived
//!   controls) is an ordered list of source sub-spans and derived controls over
//!   the owning primary view, never a single fictitious fragment slice.
//!
//! # Pinned token rule `reader_tokenizer/v1`
//!
//! Within a primary view the clean text channel is split into **maximal runs of
//! whitespace and maximal runs of non-whitespace** (the [`TokenClass`] rule).
//! Each run is then localized against the reading-order unit map: a run inside
//! one unit is a `source_fragment` / `derived_control` token; a run covering two
//! or more units is a `composite_range` token. The stream is lossless — the
//! concatenation of the token texts equals the view's clean output — so no byte
//! of the clean channel is dropped or duplicated.
//!
//! Machine-readable consumer model (T06 parses this block; keep one entry per
//! line):
//!
//! ```text
//! <!-- consumer-model:reader_tokenizer:begin -->
//! provenance:source_fragment fields:document_identity,element_ref,slot,fragment_ref,span,source_pos
//! provenance:derived_control fields:document_identity,element_ref,source_pos,derived_kind,rule_profile
//! provenance:composite_range units:source_subspan,derived_control
//! derived_kind:tab
//! derived_kind:line_break
//! derived_kind:page_break
//! <!-- consumer-model:reader_tokenizer:end -->
//! ```
//!
//! # Non-claims
//!
//! This is a bounded structural consumer. It asserts document structure and
//! identity, **not** legal authority, legal completeness, or normative citation
//! resolution; its `kind` labels are working labels. It is not authenticity
//! (a pin is integrity evidence), not normalization (the text channel is read
//! verbatim), not physical pagination (a `page_break` stays a derived control),
//! and not an R1000 closure artifact (R1000 stays `active/unclosed`). It is
//! serialization-free: no `serde`, no JSON writer. Decoded legal text is never
//! logged or interpolated into diagnostics; only ids, closed codes and counters
//! appear in errors.

use std::collections::HashMap;
use std::fmt;

use crate::analysis_source_mapping::{MappingRefusal, SourceIdentity};
use crate::cleaned_wire::{CLEANED_PROJECTION_SCHEMA, CleanedProjection, read_cleaned_wire};
use crate::document_context::DocumentVersionRef;
use crate::reader_composite::{CompositeAddress, CompositeError, CompositeUnit, resolve_composite};
use crate::reader_contract::{
    ContractError, ElementRef, FragmentRef, ReaderDerivedKind, ReaderFragmentSpan,
    ReaderRecordIndex, ReaderSemantic, check_fragment_span,
};
use crate::reader_projection::{
    ProjectedSegment, ReaderProjection, SegmentId, SegmentOrigin, ViewId,
};
use crate::reader_reading_order::{ReadingOrderError, ReadingOrderIndex};
use crate::source_package::{Package, Record, TextSlot};

// ------------------------------------------------------------- constants #

/// Pinned tokenizer profile id.
pub const READER_TOKENIZER_PROFILE: &str = "reader_tokenizer/v1";

/// Pinned derivation rule that produced a derived control's literal. The rule
/// lives in the frozen reader projection (`reader-projection-contract.md`); the
/// tokenizer copies the rule id, it never re-derives the literal.
pub const READER_TOKENIZER_DERIVED_RULE: &str = "reader-projection/derived-literal/v1";

/// The three documented derived-control kinds, in pinned order.
pub const READER_TOKENIZER_DERIVED_KINDS: [ReaderDerivedKind; 3] = [
    ReaderDerivedKind::Tab,
    ReaderDerivedKind::LineBreak,
    ReaderDerivedKind::PageBreak,
];

// ----------------------------------------------------------------- errors #

/// Closed tokenizer error vocabulary. Every failure is a typed refusal, never a
/// partial or clamped stream.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenizerErrorKind {
    /// The cleaned wire artifact could not be read back.
    ArtifactUnreadable,
    /// The document identity could not be constructed from the wire pins.
    IdentityInvalid,
    /// A primary view named by the projection has no reading-order entry.
    UnknownView,
    /// A navigation (structure-only) view was requested as a token surface.
    NotPrimaryView,
    /// The reading order could not be re-derived from the substrate.
    OrderUnavailable,
    /// A reading-order segment id has no projected segment.
    MissingSegment,
    /// A source segment names a fragment that is absent from the substrate.
    MissingFragment,
    /// A source segment carries no text slot, or a derived segment carries no
    /// derived kind.
    MissingProvenance,
    /// A segment's declared output offsets do not tile the view output.
    OutputGap,
    /// A computed sub-span failed `check_fragment_span`.
    SpanInvalid,
    /// A composite address was refused by `resolve_composite`.
    AddressRefused,
}

impl TokenizerErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            TokenizerErrorKind::ArtifactUnreadable => "artifact_unreadable",
            TokenizerErrorKind::IdentityInvalid => "identity_invalid",
            TokenizerErrorKind::UnknownView => "unknown_view",
            TokenizerErrorKind::NotPrimaryView => "not_primary_view",
            TokenizerErrorKind::OrderUnavailable => "order_unavailable",
            TokenizerErrorKind::MissingSegment => "missing_segment",
            TokenizerErrorKind::MissingFragment => "missing_fragment",
            TokenizerErrorKind::MissingProvenance => "missing_provenance",
            TokenizerErrorKind::OutputGap => "output_gap",
            TokenizerErrorKind::SpanInvalid => "span_invalid",
            TokenizerErrorKind::AddressRefused => "address_refused",
        }
    }
}

impl fmt::Display for TokenizerErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed tokenizer error. Carries no serialization dependency and never embeds
/// decoded legal text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TokenizerError {
    kind: TokenizerErrorKind,
    detail: String,
}

impl TokenizerError {
    /// Builds an error from a class and a diagnostic detail.
    pub fn new(kind: TokenizerErrorKind, detail: impl Into<String>) -> Self {
        TokenizerError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> TokenizerErrorKind {
        self.kind
    }

    /// Diagnostic detail (never parsed; ids and closed codes only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for TokenizerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for TokenizerError {}

// ------------------------------------------------------------- identity #

/// The verified document identity every token is bound to: the composite
/// `SourceIdentity ⊕ DocumentVersionRef` (acceptance contract §6 / this
/// contract §3). Fragment ids (`tN`, `eN`) and member ids are local to one
/// document and are never used as an identity on their own.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct DocumentIdentity {
    /// Pinned parent evidence identity (sha / bytes / schema / seals).
    pub source: SourceIdentity,
    /// Pinned document-version triple.
    pub version: DocumentVersionRef,
}

impl DocumentIdentity {
    /// Builds a document identity from its two halves.
    pub fn new(source: SourceIdentity, version: DocumentVersionRef) -> Self {
        DocumentIdentity { source, version }
    }

    /// Builds the identity from a read-back cleaned wire (the source pin and the
    /// parent seals) plus the caller-supplied document-version triple.
    ///
    /// The `source_sha256` / seals are copied verbatim from the wire — never
    /// recomputed — and are integrity evidence, not authenticity.
    pub fn from_cleaned(
        cleaned: &CleanedProjection,
        version: DocumentVersionRef,
    ) -> Result<Self, TokenizerError> {
        let source = SourceIdentity::try_new(
            cleaned.source.sha256.clone(),
            cleaned.source.bytes,
            CLEANED_PROJECTION_SCHEMA.to_string(),
            cleaned.parent.records_seal_hash.clone(),
            cleaned.parent.manifest_hash.clone(),
        )
        .map_err(|error: MappingRefusal| {
            TokenizerError::new(TokenizerErrorKind::IdentityInvalid, error.kind().as_str())
        })?;
        Ok(DocumentIdentity { source, version })
    }
}

// ---------------------------------------------------------------- tokens #

/// The three provenance forms a token may carry (consumer-model block).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ProvenanceForm {
    /// A token inside one source-fragment unit.
    SourceFragment,
    /// A token that is exactly one documented derived control.
    DerivedControl,
    /// A token crossing a unit boundary: an ordered range of units.
    CompositeRange,
}

impl ProvenanceForm {
    /// Closed string form.
    pub const fn as_str(self) -> &'static str {
        match self {
            ProvenanceForm::SourceFragment => "source_fragment",
            ProvenanceForm::DerivedControl => "derived_control",
            ProvenanceForm::CompositeRange => "composite_range",
        }
    }
}

/// The pinned whitespace split of the clean text channel (`reader_tokenizer/v1`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TokenClass {
    /// A maximal run of non-whitespace characters.
    Word,
    /// A maximal run of whitespace characters.
    Whitespace,
}

impl TokenClass {
    /// Closed string form.
    pub const fn as_str(self) -> &'static str {
        match self {
            TokenClass::Word => "word",
            TokenClass::Whitespace => "whitespace",
        }
    }
}

/// One ordered unit of a [`ReaderToken::Composite`] range: a source sub-span or
/// a derived control. The derived variant structurally cannot carry a fragment
/// or a span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TokenUnit {
    /// A sub-span of a source fragment, copied with its provenance.
    SourceSubspan {
        /// The owning projected segment.
        segment: SegmentId,
        /// The source fragment the span indexes.
        fragment_ref: FragmentRef,
        /// The source text/tail slot.
        slot: TextSlot,
        /// The validated sub-span within the referenced fragment.
        span: ReaderFragmentSpan,
        /// The anchoring element id (provenance, copied verbatim).
        element_ref: ElementRef,
        /// The substrate source position (provenance, copied verbatim).
        source_pos: usize,
    },
    /// A documented derived control, with no fragment and no span.
    DerivedControl {
        /// The owning projected segment.
        segment: SegmentId,
        /// The derived control kind.
        derived_kind: ReaderDerivedKind,
        /// The anchoring element id (provenance, copied verbatim).
        element_ref: ElementRef,
        /// The substrate source position (provenance, copied verbatim).
        source_pos: usize,
    },
}

/// One token in the ordered stream. The `document_identity` field binds the
/// token to one verified document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReaderToken {
    /// A token wholly inside one source-fragment unit.
    Source {
        /// The owning document identity.
        document_identity: DocumentIdentity,
        /// The owning primary view.
        view: ViewId,
        /// The owning projected segment.
        segment: SegmentId,
        /// The whitespace class of the run.
        class: TokenClass,
        /// The unit's semantic label (a working label, copied verbatim).
        semantic: ReaderSemantic,
        /// The source fragment the span indexes.
        fragment_ref: FragmentRef,
        /// The source text/tail slot.
        slot: TextSlot,
        /// The token's decoded span inside the fragment.
        span: ReaderFragmentSpan,
        /// The anchoring element id (provenance, copied verbatim).
        element_ref: ElementRef,
        /// The substrate source position (provenance, copied verbatim).
        source_pos: usize,
    },
    /// A token that is exactly one documented derived control. It carries no
    /// `fragment_ref` and no `span` by construction.
    DerivedControl {
        /// The owning document identity.
        document_identity: DocumentIdentity,
        /// The owning primary view.
        view: ViewId,
        /// The owning projected segment.
        segment: SegmentId,
        /// The derived control kind.
        derived_kind: ReaderDerivedKind,
        /// The anchoring element id (provenance, copied verbatim).
        element_ref: ElementRef,
        /// The substrate source position (provenance, copied verbatim).
        source_pos: usize,
        /// The versioned derivation rule that produced the literal.
        rule_profile: &'static str,
        /// The generated literal (a documented control, not a page model).
        literal: &'static str,
    },
    /// A token crossing a unit boundary: an ordered range of units over the
    /// owning primary view.
    Composite {
        /// The owning document identity.
        document_identity: DocumentIdentity,
        /// The owning primary view.
        view: ViewId,
        /// Inclusive byte offset into the view output.
        output_start: usize,
        /// Exclusive byte offset into the view output.
        output_end: usize,
        /// The ordered units covering the range, in reading order.
        units: Vec<TokenUnit>,
    },
}

impl ReaderToken {
    /// The token's provenance form.
    pub const fn form(&self) -> ProvenanceForm {
        match self {
            ReaderToken::Source { .. } => ProvenanceForm::SourceFragment,
            ReaderToken::DerivedControl { .. } => ProvenanceForm::DerivedControl,
            ReaderToken::Composite { .. } => ProvenanceForm::CompositeRange,
        }
    }

    /// The owning document identity.
    pub const fn document_identity(&self) -> &DocumentIdentity {
        match self {
            ReaderToken::Source {
                document_identity, ..
            }
            | ReaderToken::DerivedControl {
                document_identity, ..
            }
            | ReaderToken::Composite {
                document_identity, ..
            } => document_identity,
        }
    }

    /// The owning primary view.
    pub const fn view(&self) -> &ViewId {
        match self {
            ReaderToken::Source { view, .. }
            | ReaderToken::DerivedControl { view, .. }
            | ReaderToken::Composite { view, .. } => view,
        }
    }
}

/// An ordered token stream for one document.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TokenStream {
    /// The verified document identity every token is bound to.
    pub document_identity: DocumentIdentity,
    /// The ordered tokens across every primary view, in projection view order.
    pub tokens: Vec<ReaderToken>,
}

impl TokenStream {
    /// Number of tokens of the given provenance form.
    pub fn count(&self, form: ProvenanceForm) -> usize {
        self.tokens
            .iter()
            .filter(|token| token.form() == form)
            .count()
    }

    /// Number of source-fragment tokens.
    pub fn source_count(&self) -> usize {
        self.count(ProvenanceForm::SourceFragment)
    }

    /// Number of derived-control tokens.
    pub fn derived_count(&self) -> usize {
        self.count(ProvenanceForm::DerivedControl)
    }

    /// Number of composite-range tokens.
    pub fn composite_count(&self) -> usize {
        self.count(ProvenanceForm::CompositeRange)
    }
}

// ------------------------------------------------------------- read path #

/// Localizes one primary view's clean text channel into tokens and appends them
/// to `out`, in reading order.
///
/// `segments_by_id` is the document-wide segment lookup, built **once** by
/// [`tokenize_projection`] and shared by every view: rebuilding it per view made
/// the stage O(views × segments) and dominated multi-paragraph documents, where
/// every paragraph is its own primary view.
fn tokenize_view(
    order: &ReadingOrderIndex,
    segments_by_id: &HashMap<&str, &ProjectedSegment>,
    index: &ReaderRecordIndex,
    view: &ViewId,
    identity: &DocumentIdentity,
    out: &mut Vec<ReaderToken>,
) -> Result<(), TokenizerError> {
    let ordered = order
        .reading_order(view)
        .map_err(|error: ReadingOrderError| {
            let kind = match error.kind().as_str() {
                "not_primary_view" => TokenizerErrorKind::NotPrimaryView,
                _ => TokenizerErrorKind::UnknownView,
            };
            TokenizerError::new(kind, format!("view {}: {}", view, error.detail()))
        })?;

    // 1. The reading order is the authority for segmentation, never the
    //    projection's declared refs.
    let mut units: Vec<&ProjectedSegment> = Vec::with_capacity(ordered.len());
    for id in ordered {
        let segment = segments_by_id.get(id.as_str()).ok_or_else(|| {
            TokenizerError::new(
                TokenizerErrorKind::MissingSegment,
                format!("reading order names unknown segment {id}"),
            )
        })?;
        units.push(segment);
    }

    // 2. Rebuild the view output from the units and check that the declared
    //    output offsets tile it exactly. A gap is a typed refusal.
    let mut output = String::new();
    for segment in &units {
        let start = segment.output_start;
        if start != output.len() {
            return Err(TokenizerError::new(
                TokenizerErrorKind::OutputGap,
                format!(
                    "segment {} starts at {} but the view output is {} bytes",
                    segment.id,
                    start,
                    output.len()
                ),
            ));
        }
        match segment.origin {
            SegmentOrigin::SourceFragment => {
                let fragment = segment.fragment_ref.clone().ok_or_else(|| {
                    TokenizerError::new(
                        TokenizerErrorKind::MissingProvenance,
                        format!("source segment {} has no fragment", segment.id),
                    )
                })?;
                let span = segment.span.clone().ok_or_else(|| {
                    TokenizerError::new(
                        TokenizerErrorKind::MissingProvenance,
                        format!("source segment {} has no span", segment.id),
                    )
                })?;
                let value = index.text(fragment.as_str()).ok_or_else(|| {
                    TokenizerError::new(
                        TokenizerErrorKind::MissingFragment,
                        format!("fragment {fragment} is missing from the substrate"),
                    )
                })?;
                check_fragment_span(&value.value, &span).map_err(map_contract_error)?;
                output.push_str(&value.value[span.start..span.end]);
            }
            SegmentOrigin::Derived(kind) => output.push_str(kind.literal()),
        }
    }
    if output.len() != units.last().map_or(0, |segment| segment.output_end) {
        return Err(TokenizerError::new(
            TokenizerErrorKind::OutputGap,
            format!(
                "view {} output length does not match its declared end",
                view
            ),
        ));
    }

    // 3. Split the output into maximal whitespace / non-whitespace runs.
    let mut runs: Vec<(usize, usize, bool)> = Vec::new();
    for (offset, ch) in output.char_indices() {
        let whitespace = ch.is_whitespace();
        match runs.last_mut() {
            Some(last) if last.2 == whitespace => last.1 = offset + ch.len_utf8(),
            _ => runs.push((offset, offset + ch.len_utf8(), whitespace)),
        }
    }

    // 4. Localize each run against the unit map. The units tile the view
    //    output contiguously and both `runs` and `units` are in ascending
    //    output order, so a single forward cursor finds each run's overlapping
    //    units in O(runs + units) — never a per-run rescan of every unit.
    let mut cursor = 0usize;
    for (run_start, run_end, whitespace) in runs {
        while cursor < units.len() && units[cursor].output_end <= run_start {
            cursor += 1;
        }
        let mut end = cursor;
        while end < units.len() && units[end].output_start < run_end {
            end += 1;
        }
        let overlapping: &[&ProjectedSegment] = &units[cursor..end];
        match overlapping {
            [] => {
                return Err(TokenizerError::new(
                    TokenizerErrorKind::SpanInvalid,
                    format!("run [{run_start}, {run_end}) in view {view} selects no unit"),
                ));
            }
            [segment] => match segment.origin {
                SegmentOrigin::SourceFragment => {
                    out.push(source_token(
                        index, identity, view, segment, run_start, run_end, whitespace,
                    )?);
                }
                SegmentOrigin::Derived(kind) => {
                    out.push(ReaderToken::DerivedControl {
                        document_identity: identity.clone(),
                        view: view.clone(),
                        segment: segment.id.clone(),
                        derived_kind: kind,
                        element_ref: segment.element_ref.clone(),
                        source_pos: segment.source_pos,
                        rule_profile: READER_TOKENIZER_DERIVED_RULE,
                        literal: kind.literal(),
                    });
                }
            },
            _ => {
                // A run crossing a unit boundary is a composite range. The
                // overlapping units are exactly the contiguous slice
                // `units[cursor..end]` (the units tile the view output), so the
                // range is built directly from them — never a per-run rebuild of
                // the substrate index and a full reading-order walk, which made
                // a composite-heavy document quadratic. The unit construction
                // copies `reader_composite::resolve_composite` verbatim.
                let mut composite_units: Vec<CompositeUnit> = Vec::with_capacity(overlapping.len());
                for segment in overlapping {
                    let lo = run_start.max(segment.output_start);
                    let hi = run_end.min(segment.output_end);
                    if lo >= hi {
                        continue;
                    }
                    match segment.origin {
                        SegmentOrigin::SourceFragment => {
                            let fragment = segment.fragment_ref.clone().ok_or_else(|| {
                                TokenizerError::new(
                                    TokenizerErrorKind::MissingProvenance,
                                    format!("source segment {} has no fragment", segment.id),
                                )
                            })?;
                            let slot = segment.slot.ok_or_else(|| {
                                TokenizerError::new(
                                    TokenizerErrorKind::MissingProvenance,
                                    format!("source segment {} has no slot", segment.id),
                                )
                            })?;
                            let value = index.text(fragment.as_str()).ok_or_else(|| {
                                TokenizerError::new(
                                    TokenizerErrorKind::MissingFragment,
                                    format!("fragment {fragment} is missing from the substrate"),
                                )
                            })?;
                            let span = ReaderFragmentSpan::new(
                                fragment.clone(),
                                lo - segment.output_start,
                                hi - segment.output_start,
                            );
                            check_fragment_span(&value.value, &span).map_err(
                                |error: ContractError| {
                                    TokenizerError::new(
                                        TokenizerErrorKind::AddressRefused,
                                        error.kind().as_str(),
                                    )
                                },
                            )?;
                            composite_units.push(CompositeUnit::Source {
                                segment: segment.id.clone(),
                                fragment_ref: fragment,
                                slot,
                                span,
                                element_ref: segment.element_ref.clone(),
                                source_pos: segment.source_pos,
                            });
                        }
                        SegmentOrigin::Derived(kind) => {
                            composite_units.push(CompositeUnit::Derived {
                                segment: segment.id.clone(),
                                kind,
                                element_ref: segment.element_ref.clone(),
                                source_pos: segment.source_pos,
                            });
                        }
                    }
                }
                if composite_units.is_empty() {
                    return Err(TokenizerError::new(
                        TokenizerErrorKind::AddressRefused,
                        format!("run [{run_start}, {run_end}) in view {view} selects no unit"),
                    ));
                }
                out.push(ReaderToken::Composite {
                    document_identity: identity.clone(),
                    view: view.clone(),
                    output_start: run_start,
                    output_end: run_end,
                    units: composite_units.into_iter().map(token_unit).collect(),
                });
            }
        }
    }
    Ok(())
}

/// Builds a source-fragment token for a run inside one source unit, applying
/// the pinned span-offset rule (`span.start + local offset`).
fn source_token(
    index: &ReaderRecordIndex,
    identity: &DocumentIdentity,
    view: &ViewId,
    segment: &ProjectedSegment,
    run_start: usize,
    run_end: usize,
    whitespace: bool,
) -> Result<ReaderToken, TokenizerError> {
    let fragment_ref = segment.fragment_ref.clone().ok_or_else(|| {
        TokenizerError::new(
            TokenizerErrorKind::MissingProvenance,
            format!("source segment {} has no fragment", segment.id),
        )
    })?;
    let slot = segment.slot.ok_or_else(|| {
        TokenizerError::new(
            TokenizerErrorKind::MissingProvenance,
            format!("source segment {} has no slot", segment.id),
        )
    })?;
    let unit_span = segment.span.clone().ok_or_else(|| {
        TokenizerError::new(
            TokenizerErrorKind::MissingProvenance,
            format!("source segment {} has no span", segment.id),
        )
    })?;
    let value = index.text(fragment_ref.as_str()).ok_or_else(|| {
        TokenizerError::new(
            TokenizerErrorKind::MissingFragment,
            format!("fragment {fragment_ref} is missing from the substrate"),
        )
    })?;
    let local_start = run_start - segment.output_start;
    let local_end = run_end - segment.output_start;
    let span = ReaderFragmentSpan::new(
        fragment_ref.clone(),
        unit_span.start + local_start,
        unit_span.start + local_end,
    );
    check_fragment_span(&value.value, &span).map_err(map_contract_error)?;
    Ok(ReaderToken::Source {
        document_identity: identity.clone(),
        view: view.clone(),
        segment: segment.id.clone(),
        class: if whitespace {
            TokenClass::Whitespace
        } else {
            TokenClass::Word
        },
        semantic: segment.semantic,
        fragment_ref,
        slot,
        span,
        element_ref: segment.element_ref.clone(),
        source_pos: segment.source_pos,
    })
}

/// Converts a composite unit into a token unit.
fn token_unit(unit: CompositeUnit) -> TokenUnit {
    match unit {
        CompositeUnit::Source {
            segment,
            fragment_ref,
            slot,
            span,
            element_ref,
            source_pos,
        } => TokenUnit::SourceSubspan {
            segment,
            fragment_ref,
            slot,
            span,
            element_ref,
            source_pos,
        },
        CompositeUnit::Derived {
            segment,
            kind,
            element_ref,
            source_pos,
        } => TokenUnit::DerivedControl {
            segment,
            derived_kind: kind,
            element_ref,
            source_pos,
        },
    }
}

fn map_contract_error(error: ContractError) -> TokenizerError {
    TokenizerError::new(TokenizerErrorKind::SpanInvalid, error.kind().as_str())
}

fn map_composite_error(error: CompositeError) -> TokenizerError {
    TokenizerError::new(TokenizerErrorKind::AddressRefused, error.kind().as_str())
}

// --------------------------------------------------------------- public #

/// Tokenizes one document directly from the frozen reader projection, the
/// re-derived reading order and the substrate records (the "direct build").
///
/// Navigation views are skipped: they are structure-only and never own a
/// segment. XML is never opened.
pub fn tokenize_projection(
    projection: &ReaderProjection,
    order: &ReadingOrderIndex,
    records: &[Record],
    identity: &DocumentIdentity,
) -> Result<TokenStream, TokenizerError> {
    let index = ReaderRecordIndex::new(records).map_err(|error: ContractError| {
        TokenizerError::new(TokenizerErrorKind::OrderUnavailable, error.kind().as_str())
    })?;
    // One document-wide segment lookup, shared by every view. Rebuilding it
    // inside `tokenize_view` was O(views × segments): a multi-paragraph document
    // owns one primary view per paragraph, so the rebuild alone was quadratic in
    // the document's paragraph count.
    let segments_by_id: HashMap<&str, &ProjectedSegment> = projection
        .segments
        .iter()
        .map(|segment| (segment.id.as_str(), segment))
        .collect();
    let mut tokens = Vec::new();
    for view in &projection.views {
        if !view.kind.is_primary() {
            continue;
        }
        tokenize_view(
            order,
            &segments_by_id,
            &index,
            &view.id,
            identity,
            &mut tokens,
        )?;
    }
    Ok(TokenStream {
        document_identity: identity.clone(),
        tokens,
    })
}

/// Tokenizes one document from the read-back cleaned wire plus the
/// already-captured substrate package. The reading order is re-derived from the
/// substrate, never read from the wire's declared refs.
pub fn tokenize(
    cleaned: &CleanedProjection,
    package: &Package,
    identity: &DocumentIdentity,
) -> Result<TokenStream, TokenizerError> {
    let records = package.records();
    let order = ReadingOrderIndex::build(&cleaned.projection, records).map_err(|errors| {
        TokenizerError::new(
            TokenizerErrorKind::OrderUnavailable,
            errors.first().map_or_else(
                || "reading order is unavailable".to_string(),
                |error| error.kind().as_str().to_string(),
            ),
        )
    })?;
    tokenize_projection(&cleaned.projection, &order, records, identity)
}

/// Tokenizes one document from the saved cleaned wire JSONL text plus the
/// already-captured substrate package.
pub fn tokenize_from_wire(
    artifact: &str,
    package: &Package,
    identity: &DocumentIdentity,
) -> Result<TokenStream, TokenizerError> {
    let cleaned = read_cleaned_wire(artifact).map_err(|error| {
        TokenizerError::new(
            TokenizerErrorKind::ArtifactUnreadable,
            error.kind().as_str(),
        )
    })?;
    tokenize(&cleaned, package, identity)
}

/// Tokenizes an explicit output range of one primary view.
///
/// A range covering exactly one unit yields a `source_fragment` /
/// `derived_control` token (the span-offset rule applies to a sub-span of a
/// source unit); a range covering two or more units yields a `composite_range`
/// token. A refused address is a typed error.
pub fn tokenize_address(
    cleaned: &CleanedProjection,
    package: &Package,
    identity: &DocumentIdentity,
    address: &CompositeAddress,
) -> Result<ReaderToken, TokenizerError> {
    let records = package.records();
    let order = ReadingOrderIndex::build(&cleaned.projection, records).map_err(|errors| {
        TokenizerError::new(
            TokenizerErrorKind::OrderUnavailable,
            errors.first().map_or_else(
                || "reading order is unavailable".to_string(),
                |error| error.kind().as_str().to_string(),
            ),
        )
    })?;
    let range = resolve_composite(&cleaned.projection, &order, records, address)
        .map_err(map_composite_error)?;
    if range.units.len() == 1 {
        let index = ReaderRecordIndex::new(records).map_err(|error: ContractError| {
            TokenizerError::new(TokenizerErrorKind::OrderUnavailable, error.kind().as_str())
        })?;
        if let Some(segment) =
            cleaned
                .projection
                .segments
                .iter()
                .find(|segment| match &range.units[0] {
                    CompositeUnit::Source { segment: id, .. }
                    | CompositeUnit::Derived { segment: id, .. } => &segment.id == id,
                })
        {
            return match &range.units[0] {
                CompositeUnit::Source { span, .. } => {
                    let value = index.text(span.fragment.as_str()).ok_or_else(|| {
                        TokenizerError::new(
                            TokenizerErrorKind::MissingFragment,
                            format!("fragment {} is missing from the substrate", span.fragment),
                        )
                    })?;
                    let whitespace = value.value[span.start..span.end]
                        .chars()
                        .all(char::is_whitespace);
                    source_token(
                        &index,
                        identity,
                        &range.view,
                        segment,
                        range.output_start,
                        range.output_end,
                        whitespace,
                    )
                }
                CompositeUnit::Derived { kind, .. } => Ok(ReaderToken::DerivedControl {
                    document_identity: identity.clone(),
                    view: range.view.clone(),
                    segment: segment.id.clone(),
                    derived_kind: *kind,
                    element_ref: segment.element_ref.clone(),
                    source_pos: segment.source_pos,
                    rule_profile: READER_TOKENIZER_DERIVED_RULE,
                    literal: kind.literal(),
                }),
            };
        }
    }
    Ok(ReaderToken::Composite {
        document_identity: identity.clone(),
        view: range.view,
        output_start: range.output_start,
        output_end: range.output_end,
        units: range.units.into_iter().map(token_unit).collect(),
    })
}

// ----------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cleaned_wire::{WireCompletion, WireLimits, render_cleaned_projection};
    use crate::reader_projection::build_projection;
    use crate::source_package::{Limits, capture};

    const CONTROLS: &str = include_str!("../tests/fixtures/reader/diverse/controls.xml");
    const TEXT_ONLY: &str = include_str!("../tests/fixtures/reader/diverse/text-only.xml");

    fn identity() -> DocumentIdentity {
        let version = DocumentVersionRef::try_new(
            "doc-1".to_string(),
            "rev-1".to_string(),
            "reader_wordml_profile/v1".to_string(),
        )
        .expect("version triple must be valid");
        let source = SourceIdentity::try_new(
            "a".repeat(64),
            12,
            CLEANED_PROJECTION_SCHEMA.to_string(),
            None,
            None,
        )
        .expect("source identity must be valid");
        DocumentIdentity::new(source, version)
    }

    fn build(xml: &str) -> (Package, CleanedProjection, TokenStream) {
        let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
        let projection = build_projection(package.records()).expect("projection must build");
        let artifact = render_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("render must succeed");
        let cleaned = read_cleaned_wire(&artifact).expect("read-back must succeed");
        let stream = tokenize(&cleaned, &package, &identity()).expect("tokenize must succeed");
        (package, cleaned, stream)
    }

    #[test]
    fn text_only_fixture_yields_three_source_tokens() {
        let (_package, _cleaned, stream) = build(TEXT_ONLY);
        // "Только текст" -> word, whitespace, word.
        assert_eq!(stream.source_count(), 3);
        assert_eq!(stream.derived_count(), 0);
        assert_eq!(stream.composite_count(), 0);
        assert!(
            stream
                .tokens
                .iter()
                .all(|token| token.form() == ProvenanceForm::SourceFragment)
        );
    }

    #[test]
    fn derived_control_token_has_no_fragment_or_span() {
        let (_package, _cleaned, stream) = build(CONTROLS);
        let derived: Vec<&ReaderToken> = stream
            .tokens
            .iter()
            .filter(|token| token.form() == ProvenanceForm::DerivedControl)
            .collect();
        assert!(
            !derived.is_empty(),
            "controls fixture must yield derived tokens"
        );
        for token in derived {
            match token {
                ReaderToken::DerivedControl { literal, .. } => assert!(!literal.is_empty()),
                other => panic!("expected a derived control token, got {other:?}"),
            }
        }
    }

    #[test]
    fn composite_range_across_two_source_fragments() {
        // mixed-wordml has `<w:ins><w:t>Theta</w:t></w:ins><w:del><w:t>Iota</w:t></w:del>`:
        // two adjacent source fragments with no whitespace between, so the
        // non-whitespace run "ThetaIota" crosses a unit boundary.
        let xml = include_str!("../tests/fixtures/reader/mixed-wordml.xml");
        let (_package, _cleaned, stream) = build(xml);
        let composite = stream
            .tokens
            .iter()
            .find(|token| token.form() == ProvenanceForm::CompositeRange)
            .expect("mixed-wordml must yield a composite token");
        match composite {
            ReaderToken::Composite { units, .. } => {
                assert!(units.len() >= 2, "a composite must cover two or more units");
                assert!(
                    units
                        .iter()
                        .all(|unit| matches!(unit, TokenUnit::SourceSubspan { .. })),
                    "this composite spans several source fragments"
                );
            }
            other => panic!("expected a composite token, got {other:?}"),
        }
    }

    #[test]
    fn single_unit_subspan_applies_the_offset_rule() {
        let (package, cleaned, _stream) = build(CONTROLS);
        // The first primary view's first source unit starts at output offset 0
        // and holds a single byte "A"; its span must be [0, 1) in the fragment.
        let segment = cleaned
            .projection
            .segments
            .iter()
            .find(|segment| {
                segment.origin == SegmentOrigin::SourceFragment && segment.output_start == 0
            })
            .expect("controls fixture must have a leading source segment");
        let unit_span = segment
            .span
            .clone()
            .expect("source segment must carry a span");
        let address = CompositeAddress {
            view: segment.view.clone(),
            output_start: 0,
            output_end: 1,
        };
        let token = tokenize_address(&cleaned, &package, &identity(), &address)
            .expect("address must tokenize");
        match token {
            ReaderToken::Source { span, .. } => {
                assert_eq!(span.start, unit_span.start);
                assert_eq!(span.end, unit_span.start + 1);
            }
            other => panic!("expected a source token, got {other:?}"),
        }
    }

    #[test]
    fn address_spanning_two_units_is_a_composite() {
        let (package, cleaned, _stream) = build(CONTROLS);
        let view = cleaned
            .projection
            .views
            .iter()
            .find(|view| view.kind.is_primary())
            .expect("controls fixture must have a primary view");
        // "A\nB": [0, 3) spans the source "A", the derived "\n" and the source "B".
        let address = CompositeAddress {
            view: view.id.clone(),
            output_start: 0,
            output_end: 3,
        };
        let token = tokenize_address(&cleaned, &package, &identity(), &address)
            .expect("address must tokenize");
        match token {
            ReaderToken::Composite { units, .. } => {
                assert_eq!(units.len(), 3);
                // A fragment, a derived separator and a fragment: the derived
                // unit is present and structurally carries no fragment or span.
                assert!(
                    units
                        .iter()
                        .any(|unit| matches!(unit, TokenUnit::DerivedControl { .. }))
                );
                assert!(
                    units
                        .iter()
                        .any(|unit| matches!(unit, TokenUnit::SourceSubspan { .. }))
                );
            }
            other => panic!("expected a composite token, got {other:?}"),
        }
    }

    #[test]
    fn derived_kinds_are_the_pinned_three() {
        let kinds: Vec<&str> = READER_TOKENIZER_DERIVED_KINDS
            .iter()
            .map(|kind| kind.as_str())
            .collect();
        assert_eq!(kinds, ["tab", "line_break", "page_break"]);
        for kind in READER_TOKENIZER_DERIVED_KINDS {
            assert!(
                !kind.literal().is_empty(),
                "a derived literal must be non-empty"
            );
        }
    }

    #[test]
    fn source_is_serialization_free() {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("src/reader_tokenizer.rs");
        let source = std::fs::read_to_string(path).expect("source must be readable");
        // Scan the module proper, not this test module (whose literals name the
        // forbidden crates).
        let code_end = source.find("#[cfg(test)]").unwrap_or(source.len());
        let code: String = source[..code_end]
            .lines()
            .filter(|line| !line.trim_start().starts_with("//"))
            .collect::<Vec<_>>()
            .join("\n");
        for forbidden in ["serde", "Serialize", "Deserialize"] {
            assert!(
                !code.contains(forbidden),
                "reader_tokenizer must stay serialization-free, found {forbidden}"
            );
        }
    }
}
