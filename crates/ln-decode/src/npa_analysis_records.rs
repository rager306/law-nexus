//! M214-es3jvw S02 T02: analysis blocks and typed records with source refs.
//!
//! Executable core of `prd/architecture/npa-analysis-jsonl-contract.md` §8A: a
//! reader primary view becomes an analysis **block** whose text is the full
//! ordered concatenation of its source-fragment segments and derived separator
//! literals, and a local analyzer coordinate (`npa_anchor::LocalSpan`) is
//! localized to exactly one pinned fragment. Every outcome carries either a
//! resolved fragment-qualified span or a closed typed refusal — never a panic,
//! never a dropped result.
//!
//! Scope is blocks plus the typed, **linked** and **classification** record
//! streams: the JSONL envelope is a later task of the same slice. No second
//! coordinate system is minted; resolution goes through
//! `analysis_source_mapping::SourceMapping` and the analyzer modules stay
//! untouched (`npa_link` / `npa_classify` are read-only producers).

use std::collections::HashMap;
use std::fmt;

use crate::analysis_source_mapping::{MappingRefusal, MappingRefusalKind, SourceMapping};
use crate::npa_anchor::{check_span, AnchorDiagnostic, LocalSpan, RejectReason, SpanError};
use crate::npa_classify::{
    self, ClassificationDiagnostic, ClassifiedMember, Competence, GraphClass, IdentityKey,
    LegalClass,
};
use crate::npa_link::{
    self, LinkDerivation, LinkDiagnostic, LinkedDocument, LinkedMember, LinkedMemberKind,
    LinkedRelation, LinkedRelationKind,
};
use crate::npa_typed::{self, TypeDerivation};
use crate::reader_contract::{
    FragmentRef, ReaderDerivedKind, ReaderFragmentSpan, ReaderRecordIndex,
};
use crate::reader_projection::{
    ProjectedSegment, ReaderProjection, SegmentId, SegmentOrigin, ViewId,
};

/// Producer rule token for the typed stage (`diagnostic.rule`).
pub const TYPED_RULE: &str = "npa_typed::scan_typed_diagnosed";

// ---------------------------------------------------------------- refusals #

/// Closed S02-local refusal vocabulary (§8A.3). The seam's
/// [`MappingRefusalKind`] is surfaced verbatim beside these tokens.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AnalysisRefusalKind {
    /// The span is not contained in a single fragment segment.
    CrossFragment,
    /// The span crosses a derived separator boundary inside one block. The
    /// separator is never rebased onto a fragment span.
    DerivedSeparator,
    /// The span leaves the block text.
    OutOfBounds,
    /// The block index is absent from the layout.
    UnmappedBlock,
    /// The span is empty, inverted or splits a UTF-8 code point.
    InvalidSpan,
    /// A rendering or record-count limit was reached.
    LimitReached,
}

impl AnalysisRefusalKind {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            AnalysisRefusalKind::CrossFragment => "cross_fragment",
            AnalysisRefusalKind::DerivedSeparator => "derived_separator",
            AnalysisRefusalKind::OutOfBounds => "out_of_bounds",
            AnalysisRefusalKind::UnmappedBlock => "unmapped_block",
            AnalysisRefusalKind::InvalidSpan => "invalid_span",
            AnalysisRefusalKind::LimitReached => "limit_reached",
        }
    }
}

impl fmt::Display for AnalysisRefusalKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A record refusal: either an S02-local kind or a seam mapping refusal.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AnalysisRefusal {
    /// An S02-local localization refusal.
    Local(AnalysisRefusalKind),
    /// A refusal bubbled from `analysis_source_mapping`.
    Mapping(MappingRefusal),
}

impl AnalysisRefusal {
    /// Builds a local refusal.
    pub const fn local(kind: AnalysisRefusalKind) -> Self {
        AnalysisRefusal::Local(kind)
    }

    /// The closed wire token (local or seam token).
    pub fn token(&self) -> &'static str {
        match self {
            AnalysisRefusal::Local(kind) => kind.as_str(),
            AnalysisRefusal::Mapping(refusal) => refusal.kind().as_str(),
        }
    }

    /// Diagnostic detail (never parsed).
    pub fn detail(&self) -> String {
        match self {
            AnalysisRefusal::Local(kind) => kind.as_str().to_string(),
            AnalysisRefusal::Mapping(refusal) => refusal.detail().to_string(),
        }
    }
}

impl fmt::Display for AnalysisRefusal {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AnalysisRefusal::Local(kind) => write!(f, "{kind}"),
            AnalysisRefusal::Mapping(refusal) => write!(f, "{refusal}"),
        }
    }
}

impl std::error::Error for AnalysisRefusal {}

fn structural(detail: impl Into<String>) -> AnalysisRefusal {
    AnalysisRefusal::Mapping(MappingRefusal::new(
        MappingRefusalKind::EnvelopeStructural,
        detail,
    ))
}

fn unknown_fragment(detail: impl Into<String>) -> AnalysisRefusal {
    AnalysisRefusal::Mapping(MappingRefusal::new(
        MappingRefusalKind::UnknownFragment,
        detail,
    ))
}

// ------------------------------------------------------------- source refs #

/// A resolved source coordinate: one fragment plus its half-open UTF-8 byte
/// range. Only [`resolve_span`] mints one, so the range is valid by
/// construction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SourceBoundSpan {
    /// The fragment the coordinate indexes.
    pub fragment: FragmentRef,
    /// Half-open start byte in the fragment.
    pub start: usize,
    /// Half-open end byte in the fragment.
    pub end: usize,
}

impl SourceBoundSpan {
    /// Builds a resolved coordinate.
    pub fn new(fragment: FragmentRef, start: usize, end: usize) -> Self {
        SourceBoundSpan {
            fragment,
            start,
            end,
        }
    }

    /// The seam fragment-qualified span.
    pub fn as_fragment_span(&self) -> ReaderFragmentSpan {
        ReaderFragmentSpan::new(self.fragment.clone(), self.start, self.end)
    }
}

/// A record's source reference: a resolved span or a closed refusal token.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SourceRef {
    /// The span resolved to one pinned fragment.
    Bound(SourceBoundSpan),
    /// The span could not be localized or resolved.
    Refused(AnalysisRefusal),
}

impl SourceRef {
    /// The bound span, when resolution succeeded.
    pub fn as_bound(&self) -> Option<&SourceBoundSpan> {
        match self {
            SourceRef::Bound(span) => Some(span),
            SourceRef::Refused(_) => None,
        }
    }

    /// True when the reference resolved.
    pub fn is_bound(&self) -> bool {
        matches!(self, SourceRef::Bound(_))
    }

    /// The refusal token, when resolution failed.
    pub fn refusal_token(&self) -> Option<&'static str> {
        match self {
            SourceRef::Bound(_) => None,
            SourceRef::Refused(refusal) => Some(refusal.token()),
        }
    }

    /// The refusal, when resolution failed.
    pub fn refusal(&self) -> Option<&AnalysisRefusal> {
        match self {
            SourceRef::Bound(_) => None,
            SourceRef::Refused(refusal) => Some(refusal),
        }
    }
}

impl From<Result<SourceBoundSpan, AnalysisRefusal>> for SourceRef {
    fn from(result: Result<SourceBoundSpan, AnalysisRefusal>) -> Self {
        match result {
            Ok(span) => SourceRef::Bound(span),
            Err(refusal) => SourceRef::Refused(refusal),
        }
    }
}

// ------------------------------------------------------------- block layout #

/// One source-fragment segment of a block: the fragment id plus its half-open
/// offsets in the concatenated block text and in the fragment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BlockSegment {
    /// The pinned fragment this segment names.
    pub fragment: FragmentRef,
    /// Half-open start offset in the block text.
    pub block_start: usize,
    /// Half-open end offset in the block text.
    pub block_end: usize,
    /// Half-open start offset in the fragment.
    pub fragment_start: usize,
    /// Half-open end offset in the fragment.
    pub fragment_end: usize,
}

/// One derived separator boundary inside a block: the reader control kind plus
/// its half-open offsets in the concatenated block text. A derived boundary
/// carries no fragment and no source span; it is never rebased onto a fragment.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DerivedBoundary {
    /// The reader control that generated this separator.
    pub kind: ReaderDerivedKind,
    /// Half-open start offset in the block text.
    pub block_start: usize,
    /// Half-open end offset in the block text.
    pub block_end: usize,
}

/// One analysis block: a non-empty reader primary view (§8A.3).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AnalysisBlock {
    /// Sequential index over the non-empty primary views.
    pub index: usize,
    /// The reader view that produced this block.
    pub view: ViewId,
    /// Full ordered concatenation of the block's source-fragment segments and
    /// derived separator literals (`TAB` / `LF`).
    pub text: String,
    /// The ordered source-fragment segments with block offsets computed over the
    /// full [`AnalysisBlock::text`].
    pub segments: Vec<BlockSegment>,
    /// The ordered derived separators, as typed boundaries without a fragment or
    /// source span.
    pub boundaries: Vec<DerivedBoundary>,
}

/// Ordered analysis blocks built from a reader projection (§8A.3).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct AnalysisBlockLayout {
    /// The non-empty primary blocks in document order.
    pub blocks: Vec<AnalysisBlock>,
}

impl AnalysisBlockLayout {
    /// Number of non-empty analysis blocks.
    pub fn block_count(&self) -> usize {
        self.blocks.len()
    }

    /// The block at `index`.
    pub fn block(&self, index: usize) -> Option<&AnalysisBlock> {
        self.blocks.get(index)
    }

    /// The block texts, in document order, for the analyzer input.
    pub fn block_texts(&self) -> Vec<String> {
        self.blocks.iter().map(|block| block.text.clone()).collect()
    }

    /// Localizes a local analyzer span to exactly one fragment (§8A.3). Refusal
    /// order is `unmapped_block` -> `invalid_span` / `out_of_bounds` ->
    /// `derived_separator` (the span crosses a derived boundary) ->
    /// `cross_fragment`. Every refusal is closed — never rebased, never dropped.
    pub fn localize(&self, span: LocalSpan) -> Result<SourceBoundSpan, AnalysisRefusal> {
        let block = self
            .blocks
            .get(span.block)
            .ok_or_else(|| AnalysisRefusal::local(AnalysisRefusalKind::UnmappedBlock))?;
        if let Err(error) = check_span(&block.text, span) {
            let kind = match error {
                SpanError::EmptyOrInverted => AnalysisRefusalKind::InvalidSpan,
                SpanError::OutOfBounds => AnalysisRefusalKind::OutOfBounds,
                SpanError::NotCharBoundary => AnalysisRefusalKind::InvalidSpan,
            };
            return Err(AnalysisRefusal::local(kind));
        }
        if block
            .boundaries
            .iter()
            .any(|boundary| span.start < boundary.block_end && boundary.block_start < span.end)
        {
            return Err(AnalysisRefusal::local(
                AnalysisRefusalKind::DerivedSeparator,
            ));
        }
        let segment = block
            .segments
            .iter()
            .find(|segment| segment.block_start <= span.start && span.end <= segment.block_end)
            .ok_or_else(|| AnalysisRefusal::local(AnalysisRefusalKind::CrossFragment))?;
        let start = segment.fragment_start + (span.start - segment.block_start);
        let end = segment.fragment_start + (span.end - segment.block_start);
        Ok(SourceBoundSpan::new(segment.fragment.clone(), start, end))
    }
}

/// Builds the ordered analysis blocks from a reader projection and its
/// substrate index (§8A.3). Primary views are taken in document order; each
/// block text is the full ordered concatenation of its source-fragment segments
/// and derived separator literals (`TAB` / `LF`) read from `ReaderRecordIndex`.
/// Derived separators are recorded as typed [`DerivedBoundary`] values without a
/// fragment or source span. A block is emitted only when at least one source
/// fragment contributed non-empty text, so a derived-only view is not a block
/// and empty blocks are skipped.
pub fn build_analysis_block_layout(
    projection: &ReaderProjection,
    index: &ReaderRecordIndex,
) -> Result<AnalysisBlockLayout, AnalysisRefusal> {
    let segment_by_id: HashMap<&SegmentId, &ProjectedSegment> = projection
        .segments
        .iter()
        .map(|segment| (&segment.id, segment))
        .collect();
    let mut blocks: Vec<AnalysisBlock> = Vec::new();
    for view in &projection.views {
        if !view.kind.is_primary() {
            continue;
        }
        let mut text = String::new();
        let mut segments: Vec<BlockSegment> = Vec::new();
        let mut boundaries: Vec<DerivedBoundary> = Vec::new();
        let mut has_source_text = false;
        for segment_id in &view.segment_refs {
            let segment = segment_by_id.get(segment_id).copied().ok_or_else(|| {
                structural(format!(
                    "view {} references missing segment {}",
                    view.id, segment_id
                ))
            })?;
            match segment.origin {
                SegmentOrigin::SourceFragment => {
                    let fragment = segment.fragment_ref.clone().ok_or_else(|| {
                        structural(format!("segment {segment_id} has no source fragment"))
                    })?;
                    let value = index
                        .text(fragment.as_str())
                        .map(|record| record.value.as_str())
                        .ok_or_else(|| {
                            unknown_fragment(format!(
                                "fragment {fragment} is missing from the substrate index"
                            ))
                        })?;
                    let block_start = text.len();
                    text.push_str(value);
                    let block_end = text.len();
                    if !value.is_empty() {
                        has_source_text = true;
                    }
                    let fragment_start = segment.span.as_ref().map_or(0, |span| span.start);
                    let fragment_end = segment.span.as_ref().map_or(value.len(), |span| span.end);
                    segments.push(BlockSegment {
                        fragment,
                        block_start,
                        block_end,
                        fragment_start,
                        fragment_end,
                    });
                }
                SegmentOrigin::Derived(kind) => {
                    let literal = segment.text.as_deref().unwrap_or(kind.literal());
                    let block_start = text.len();
                    text.push_str(literal);
                    let block_end = text.len();
                    boundaries.push(DerivedBoundary {
                        kind,
                        block_start,
                        block_end,
                    });
                }
            }
        }
        if !has_source_text {
            continue;
        }
        let block_index = blocks.len();
        blocks.push(AnalysisBlock {
            index: block_index,
            view: view.id.clone(),
            text,
            segments,
            boundaries,
        });
    }
    Ok(AnalysisBlockLayout { blocks })
}

/// Localizes then resolves a local analyzer span through the pinned parent
/// (§8A.3, T02 step 4). The resolved fragment slice must reproduce the block
/// slice; a mismatch is a structural refusal, never a silent success.
pub fn resolve_span(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    span: LocalSpan,
) -> Result<SourceBoundSpan, AnalysisRefusal> {
    let bound = layout.localize(span)?;
    let resolved = mapping
        .resolve_fragment_span(&bound.as_fragment_span())
        .map_err(AnalysisRefusal::Mapping)?;
    let slice = mapping.slice(&resolved).map_err(AnalysisRefusal::Mapping)?;
    let block = layout
        .block(span.block)
        .ok_or_else(|| AnalysisRefusal::local(AnalysisRefusalKind::UnmappedBlock))?;
    if slice != &block.text[span.start..span.end] {
        return Err(structural(
            "resolved fragment slice differs from the analysis block text",
        ));
    }
    Ok(bound)
}

// ---------------------------------------------------------------- records #

/// One competing `npa_typed::TypeHypothesis` with its localized source span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedAlternativeRecord {
    /// The hypothesis surface form.
    pub canon: String,
    /// The hypothesis source span.
    pub span: SourceRef,
}

/// A typed member record (`npa_typed::TypedMember`: family `member`,
/// `stage=typed`). Provenance (`derivation`, `unresolved`, `type_evidence`,
/// `alternatives`) is preserved for every member.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedMemberRecord {
    /// Position in the producer stream; the family-local `ref` is `mt:<index>`.
    pub typed_index: usize,
    /// Normalized date.
    pub date: String,
    /// Number as written.
    pub number: String,
    /// Resolved TYPE surface, empty when unresolved.
    pub type_name: String,
    /// Approving act, empty when absent.
    pub approved_by: String,
    /// How the TYPE was obtained.
    pub derivation: TypeDerivation,
    /// True when no TYPE hypothesis survived.
    pub unresolved: bool,
    /// The member's own anchor span.
    pub span: SourceRef,
    /// Winning TYPE head span, when one exists.
    pub type_evidence: Option<SourceRef>,
    /// Losing surviving hypotheses, in producer order.
    pub alternatives: Vec<TypedAlternativeRecord>,
}

/// Diagnostic stage discriminator (§8A.7).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DiagnosticStage {
    /// Anchor/typing stage.
    Anchor,
    /// Linking stage.
    Link,
    /// Classification stage.
    Classification,
}

impl DiagnosticStage {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            DiagnosticStage::Anchor => "anchor",
            DiagnosticStage::Link => "link",
            DiagnosticStage::Classification => "classification",
        }
    }
}

/// Closed diagnostic `kind` vocabulary across the three stages (§8A.8).
/// S02-T02 emits the anchor kinds; the link and classification kinds are
/// declared here so the closed vocabulary is stable before those stages land.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DiagnosticKind {
    /// Anchor span is not a valid local UTF-8 range.
    InvalidSpan,
    /// Anchor was rejected by a guard.
    RejectedAnchor,
    /// The same `(date, number)` occurred at another span.
    DuplicateOccurrence,
    /// An open coordination had no eligible cross-block head.
    OpenSeriesWithoutHead,
    /// A head existed but was farther than the series hop bound.
    IncompatibleSeriesHead,
    /// A cross-block TYPE was not inherited.
    TypeNotInherited,
    /// A corporate head-family carry was refused.
    HeadFamilyCarryRefused,
    /// A short reference had no declaration in this document.
    AliasWithoutDeclaration,
    /// A this-reference had no usable document head.
    HeadUnavailable,
    /// A classification member span is invalid.
    SpanInvalid,
    /// A classification member carries no TYPE surface.
    TypeMissing,
    /// A classification member TYPE is off the closed dictionary.
    UnknownKind,
}

impl DiagnosticKind {
    /// Closed wire token.
    pub const fn as_str(self) -> &'static str {
        match self {
            DiagnosticKind::InvalidSpan => "invalid_span",
            DiagnosticKind::RejectedAnchor => "rejected_anchor",
            DiagnosticKind::DuplicateOccurrence => "duplicate_occurrence",
            DiagnosticKind::OpenSeriesWithoutHead => "open_series_without_head",
            DiagnosticKind::IncompatibleSeriesHead => "incompatible_series_head",
            DiagnosticKind::TypeNotInherited => "type_not_inherited",
            DiagnosticKind::HeadFamilyCarryRefused => "head_family_carry_refused",
            DiagnosticKind::AliasWithoutDeclaration => "alias_without_declaration",
            DiagnosticKind::HeadUnavailable => "head_unavailable",
            DiagnosticKind::SpanInvalid => "span_invalid",
            DiagnosticKind::TypeMissing => "type_missing",
            DiagnosticKind::UnknownKind => "unknown_kind",
        }
    }
}

/// A cross-reference to another record: family plus the family-local id.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecordRef {
    /// Referenced family token.
    pub family: String,
    /// Referenced family-local id (wire field `ref`).
    pub reference: String,
}

/// A diagnostic record (family `diagnostic`). A diagnostic never carries
/// provenance-free data: it either has its own span or a non-empty `refs`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiagnosticRecord {
    /// Position in the diagnostic stream; the local `ref` is `d:<index>`.
    pub index: usize,
    /// The stage that produced the diagnostic.
    pub stage: DiagnosticStage,
    /// The closed diagnostic kind.
    pub kind: DiagnosticKind,
    /// Records this diagnostic concerns.
    pub refs: Vec<RecordRef>,
    /// The diagnostic's own span, when it has one.
    pub span: Option<SourceRef>,
    /// The producer rule token.
    pub rule: String,
    /// Anchor reject reason, when the diagnostic carries one.
    pub reject_reason: Option<RejectReason>,
    /// The analysis block the diagnostic concerns, when known.
    pub block: Option<usize>,
}

/// The typed record stream and its anchor diagnostics.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TypedAnalysis {
    /// The analysis block layout the stream was built over.
    pub layout: AnalysisBlockLayout,
    /// Typed member records.
    pub members: Vec<TypedMemberRecord>,
    /// Anchor diagnostic records.
    pub diagnostics: Vec<DiagnosticRecord>,
}

fn typed_member_record(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    typed_index: usize,
    member: &npa_typed::TypedMember,
) -> TypedMemberRecord {
    TypedMemberRecord {
        typed_index,
        date: member.date.clone(),
        number: member.number.clone(),
        type_name: member.type_name.clone(),
        approved_by: member.approved_by.clone(),
        derivation: member.derivation,
        unresolved: member.unresolved,
        span: SourceRef::from(resolve_span(layout, mapping, member.span)),
        type_evidence: member
            .type_evidence
            .map(|evidence| SourceRef::from(resolve_span(layout, mapping, evidence))),
        alternatives: member
            .alternatives
            .iter()
            .map(|hypothesis| TypedAlternativeRecord {
                canon: hypothesis.canon.clone(),
                span: SourceRef::from(resolve_span(layout, mapping, hypothesis.evidence)),
            })
            .collect(),
    }
}

fn block_fragment_refs(layout: &AnalysisBlockLayout, block: usize) -> Vec<RecordRef> {
    match layout.block(block) {
        Some(block) => block
            .segments
            .iter()
            .map(|segment| RecordRef {
                family: "fragment".to_string(),
                reference: segment.fragment.as_str().to_string(),
            })
            .collect(),
        None => Vec::new(),
    }
}

fn anchor_diagnostic_record(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    index: usize,
    diagnostic: &AnchorDiagnostic,
    typed: &[TypedMemberRecord],
) -> DiagnosticRecord {
    match diagnostic {
        AnchorDiagnostic::InvalidSpan {
            block, start, end, ..
        } => {
            let span = LocalSpan {
                block: *block,
                start: *start,
                end: *end,
            };
            DiagnosticRecord {
                index,
                stage: DiagnosticStage::Anchor,
                kind: DiagnosticKind::InvalidSpan,
                refs: block_fragment_refs(layout, *block),
                span: Some(SourceRef::from(resolve_span(layout, mapping, span))),
                rule: TYPED_RULE.to_string(),
                reject_reason: None,
                block: Some(*block),
            }
        }
        AnchorDiagnostic::RejectedAnchor {
            block,
            start,
            end,
            reason,
        } => {
            let span = LocalSpan {
                block: *block,
                start: *start,
                end: *end,
            };
            DiagnosticRecord {
                index,
                stage: DiagnosticStage::Anchor,
                kind: DiagnosticKind::RejectedAnchor,
                refs: block_fragment_refs(layout, *block),
                span: Some(SourceRef::from(resolve_span(layout, mapping, span))),
                rule: TYPED_RULE.to_string(),
                reject_reason: Some(*reason),
                block: Some(*block),
            }
        }
        AnchorDiagnostic::DuplicateOccurrence {
            date, number, next, ..
        } => {
            let mut refs: Vec<RecordRef> = typed
                .iter()
                .filter(|record| record.date == *date && record.number == *number)
                .map(|record| RecordRef {
                    family: "member".to_string(),
                    reference: format!("mt:{}", record.typed_index),
                })
                .collect();
            refs.extend(block_fragment_refs(layout, next.block));
            DiagnosticRecord {
                index,
                stage: DiagnosticStage::Anchor,
                kind: DiagnosticKind::DuplicateOccurrence,
                refs,
                span: Some(SourceRef::from(resolve_span(layout, mapping, *next))),
                rule: TYPED_RULE.to_string(),
                reject_reason: None,
                block: Some(next.block),
            }
        }
    }
}

/// Builds the typed record stream and its anchor diagnostics over the analysis
/// blocks. Every member and every diagnostic becomes a record; a span that
/// cannot be localized carries its closed refusal token instead of a span.
pub fn build_typed_records(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> (Vec<TypedMemberRecord>, Vec<DiagnosticRecord>) {
    let texts = layout.block_texts();
    let (typed, anchor_diagnostics) = npa_typed::scan_typed_diagnosed(&texts);
    let members: Vec<TypedMemberRecord> = typed
        .iter()
        .enumerate()
        .map(|(index, member)| typed_member_record(layout, mapping, index, member))
        .collect();
    let diagnostics: Vec<DiagnosticRecord> = anchor_diagnostics
        .iter()
        .enumerate()
        .map(|(index, diagnostic)| {
            anchor_diagnostic_record(layout, mapping, index, diagnostic, &members)
        })
        .collect();
    (members, diagnostics)
}

/// Convenience pipeline: projection + index + mapping -> blocks + typed records.
pub fn analyze_typed(
    projection: &ReaderProjection,
    index: &ReaderRecordIndex,
    mapping: &SourceMapping,
) -> Result<TypedAnalysis, AnalysisRefusal> {
    let layout = build_analysis_block_layout(projection, index)?;
    let (members, diagnostics) = build_typed_records(&layout, mapping);
    Ok(TypedAnalysis {
        layout,
        members,
        diagnostics,
    })
}

// ------------------------------------------------- linking / classification #

/// Producer rule token for the linking stage (`diagnostic.rule`).
pub const LINK_RULE: &str = "npa_link::build_linked_document";

/// Producer rule token for the classification stage (`diagnostic.rule`).
pub const CLASSIFY_RULE: &str = "npa_classify::classify_members";

/// A linked member record (family `member`, closed `stage=linked`). Typed
/// provenance (`unresolved`/`alternatives`/`type_evidence`) is carried beside
/// it by [`TypedMemberRecord`]; linking clones `npa_link::LinkedMember` and
/// never mutates it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkedMemberRecord {
    /// `npa_link::LinkedMember.id`; the wire `ref` is `ml:<member_id>`.
    pub member_id: usize,
    /// How the member entered the linked model.
    pub kind: LinkedMemberKind,
    /// Provenance of the linked fields.
    pub derivation: LinkDerivation,
    /// Declared scoped alias, when present.
    pub alias: Option<String>,
    /// Quoted approving act, when present.
    pub approved_by: Option<String>,
    /// The member's own anchor.
    pub evidence: SourceRef,
    /// Every span that backs the member, in discovery order.
    pub provenance: Vec<SourceRef>,
}

/// A derived relation record (family `relation`). Evidence is a list of
/// separate anchors — never one cross-block span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RelationRecord {
    /// Position in the relation stream; the wire `ref` is `r:<index>`.
    pub index: usize,
    /// The relation kind.
    pub kind: LinkedRelationKind,
    /// Source member id.
    pub from_id: usize,
    /// Target member id.
    pub to_id: usize,
    /// The relation's source anchors, in order.
    pub evidence: Vec<SourceRef>,
    /// The producer's rule/explanation text.
    pub why: String,
}

/// A classification record (family `classification`); the wire `ref` is
/// `c:<member_id>`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClassificationRecord {
    /// The classified linked member id.
    pub member_id: usize,
    /// Axis A graph class.
    pub graph: GraphClass,
    /// Axis B legal class.
    pub legal_class: LegalClass,
    /// Axis C competence.
    pub competence: Competence,
    /// ADR-0016 identity selector.
    pub identity_key: IdentityKey,
    /// The member's own anchor.
    pub evidence: SourceRef,
    /// The producer's rule/explanation text.
    pub why: String,
}

/// Linked and classified records plus their stage diagnostics.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LinkedAnalysis {
    /// Linked member records.
    pub members: Vec<LinkedMemberRecord>,
    /// Relation records.
    pub relations: Vec<RelationRecord>,
    /// Classification records.
    pub classifications: Vec<ClassificationRecord>,
    /// Link and classification diagnostics, indexed from zero within the
    /// linked analysis stream (anchor diagnostics belong to the typed stream).
    pub diagnostics: Vec<DiagnosticRecord>,
}

/// Full document-scoped analysis: typed, linked, relation and classification
/// records over one block layout, with a single globally indexed diagnostic
/// stream (anchor, then link, then classification — each in producer order).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentAnalysis {
    /// The analysis block layout every record indexes into.
    pub layout: AnalysisBlockLayout,
    /// Typed member records (`stage=typed`).
    pub typed: Vec<TypedMemberRecord>,
    /// Linked member records (`stage=linked`).
    pub linked: Vec<LinkedMemberRecord>,
    /// Relation records.
    pub relations: Vec<RelationRecord>,
    /// Classification records.
    pub classifications: Vec<ClassificationRecord>,
    /// Anchor, link and classification diagnostics with unique `index`.
    pub diagnostics: Vec<DiagnosticRecord>,
}

/// The document-level provenance anchor for a payload-free diagnostic. The
/// analyzer diagnostics (`LinkDiagnostic`, `ClassificationDiagnostic`) carry no
/// span and no member/relation id, so this module cannot recover a specific
/// affected record without re-deriving analyzer internals. The honest,
/// non-invented provenance is the document record (emitted once by the
/// envelope task): the diagnostic concerns this document's pass.
fn document_refs() -> Vec<RecordRef> {
    vec![RecordRef {
        family: "document".to_string(),
        reference: "doc".to_string(),
    }]
}

fn link_diagnostic_kind(diagnostic: LinkDiagnostic) -> DiagnosticKind {
    match diagnostic {
        LinkDiagnostic::OpenSeriesWithoutHead => DiagnosticKind::OpenSeriesWithoutHead,
        LinkDiagnostic::IncompatibleSeriesHead => DiagnosticKind::IncompatibleSeriesHead,
        LinkDiagnostic::TypeNotInherited => DiagnosticKind::TypeNotInherited,
        LinkDiagnostic::HeadFamilyCarryRefused => DiagnosticKind::HeadFamilyCarryRefused,
        LinkDiagnostic::AliasWithoutDeclaration => DiagnosticKind::AliasWithoutDeclaration,
        LinkDiagnostic::HeadUnavailable => DiagnosticKind::HeadUnavailable,
    }
}

fn link_diagnostic_record(index: usize, diagnostic: LinkDiagnostic) -> DiagnosticRecord {
    DiagnosticRecord {
        index,
        stage: DiagnosticStage::Link,
        kind: link_diagnostic_kind(diagnostic),
        refs: document_refs(),
        span: None,
        rule: LINK_RULE.to_string(),
        reject_reason: None,
        block: None,
    }
}

fn classification_diagnostic_kind(diagnostic: ClassificationDiagnostic) -> DiagnosticKind {
    match diagnostic {
        ClassificationDiagnostic::SpanInvalid => DiagnosticKind::SpanInvalid,
        ClassificationDiagnostic::TypeMissing => DiagnosticKind::TypeMissing,
        ClassificationDiagnostic::UnknownKind => DiagnosticKind::UnknownKind,
    }
}

fn classification_diagnostic_record(
    index: usize,
    diagnostic: ClassificationDiagnostic,
) -> DiagnosticRecord {
    DiagnosticRecord {
        index,
        stage: DiagnosticStage::Classification,
        kind: classification_diagnostic_kind(diagnostic),
        refs: document_refs(),
        span: None,
        rule: CLASSIFY_RULE.to_string(),
        reject_reason: None,
        block: None,
    }
}

fn source_refs(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    spans: &[LocalSpan],
) -> Vec<SourceRef> {
    spans
        .iter()
        .map(|span| SourceRef::from(resolve_span(layout, mapping, *span)))
        .collect()
}

fn linked_member_record(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    member: &LinkedMember,
) -> LinkedMemberRecord {
    LinkedMemberRecord {
        member_id: member.id,
        kind: member.kind,
        derivation: member.derivation,
        alias: member.alias.clone(),
        approved_by: member.approved_by.clone(),
        evidence: SourceRef::from(resolve_span(layout, mapping, member.evidence)),
        provenance: source_refs(layout, mapping, &member.provenance),
    }
}

fn relation_record(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    index: usize,
    relation: &LinkedRelation,
) -> RelationRecord {
    RelationRecord {
        index,
        kind: relation.kind,
        from_id: relation.from_id,
        to_id: relation.to_id,
        evidence: source_refs(layout, mapping, &relation.evidence),
        why: relation.why.to_string(),
    }
}

fn classification_record(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
    member: &ClassifiedMember,
) -> ClassificationRecord {
    ClassificationRecord {
        member_id: member.member_id,
        graph: member.graph,
        legal_class: member.legal_class,
        competence: member.competence,
        identity_key: member.identity_key,
        evidence: SourceRef::from(resolve_span(layout, mapping, member.evidence)),
        why: member.why.clone(),
    }
}

/// Builds linked members, relations and classifications over the analysis
/// blocks by running the real `npa_link` then `npa_classify` pipelines on the
/// block texts. Every span resolves through the T02 layout: a span that
/// straddles two fragments becomes a closed refusal record, never a rebase and
/// never a drop. The input layout, the derived `LinkedDocument` and the
/// producer streams are read-only.
///
/// A payload-free analyzer diagnostic is emitted as a `diagnostic` record with
/// `span: null` and the document provenance anchor (see [`document_refs`]); it
/// is never dropped.
pub fn build_linked_analysis(
    layout: &AnalysisBlockLayout,
    mapping: &SourceMapping,
) -> LinkedAnalysis {
    let texts = layout.block_texts();
    let linked: LinkedDocument = npa_link::build_linked_document(&texts);

    let members: Vec<LinkedMemberRecord> = linked
        .members
        .iter()
        .map(|member| linked_member_record(layout, mapping, member))
        .collect();
    let relations: Vec<RelationRecord> = linked
        .relations
        .iter()
        .enumerate()
        .map(|(index, relation)| relation_record(layout, mapping, index, relation))
        .collect();

    let (classified, classification_diagnostics) = npa_classify::classify_members(&linked, &texts);
    let classifications: Vec<ClassificationRecord> = classified
        .iter()
        .map(|member| classification_record(layout, mapping, member))
        .collect();

    let mut diagnostics: Vec<DiagnosticRecord> = linked
        .diagnostics
        .iter()
        .enumerate()
        .map(|(index, diagnostic)| link_diagnostic_record(index, *diagnostic))
        .collect();
    for diagnostic in &classification_diagnostics {
        diagnostics.push(classification_diagnostic_record(
            diagnostics.len(),
            *diagnostic,
        ));
    }

    LinkedAnalysis {
        members,
        relations,
        classifications,
        diagnostics,
    }
}

/// Convenience pipeline: projection + index + mapping -> the full document
/// analysis (blocks, typed, linked, relation, classification, diagnostics).
/// Diagnostics are renumbered into one stream: anchor, then link, then
/// classification, so `index` is unique across the whole analysis.
pub fn analyze_document(
    projection: &ReaderProjection,
    index: &ReaderRecordIndex,
    mapping: &SourceMapping,
) -> Result<DocumentAnalysis, AnalysisRefusal> {
    let layout = build_analysis_block_layout(projection, index)?;
    let (typed, typed_diagnostics) = build_typed_records(&layout, mapping);
    let linked = build_linked_analysis(&layout, mapping);

    let mut diagnostics: Vec<DiagnosticRecord> = Vec::new();
    for mut diagnostic in typed_diagnostics {
        diagnostic.index = diagnostics.len();
        diagnostics.push(diagnostic);
    }
    for mut diagnostic in linked.diagnostics {
        diagnostic.index = diagnostics.len();
        diagnostics.push(diagnostic);
    }

    Ok(DocumentAnalysis {
        layout,
        typed,
        linked: linked.members,
        relations: linked.relations,
        classifications: linked.classifications,
        diagnostics,
    })
}
