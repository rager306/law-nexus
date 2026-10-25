//! Bridge the materialized cleaned-wire CST layer into a provider-neutral
//! [`ParsedBlock`] stream.
//!
//! The bridge is the missing seam between the S04 cleaned-projection artifact
//! ([`CleanedProjection`], read back from the materialized JSONL layer by
//! [`crate::cleaned_wire::read_cleaned_wire`]) and the hierarchy extractor
//! ([`crate::hierarchy::extract_hierarchy`] /
//! [`crate::hierarchy::extract_hierarchy_candidates`]), which consumes
//! [`ParsedBlock`] values. It **never re-parses XML/ODT**: the projection is the
//! only input, so a lift built on this bridge reads the materialized layer and
//! not the source artifact.
//!
//! Mapping contract:
//! - One block per **primary** projected view (`paragraph` / `residual`) in
//!   projection (document) order; navigation views (`table` / `row` / `cell` /
//!   `note`) are structure-only and produce no block.
//! - View text is the byte-exact concatenation of its `segment_refs` in
//!   `ordinal` order, taken from [`ProjectedSegment::text`] when present
//!   (derived controls) and from [`CleanedProjection::inline_texts`] otherwise
//!   (source fragments).
//! - A view whose assembled text is empty or whitespace-only is silently
//!   skipped: an empty paragraph carries no block text. It is never an error
//!   and never a fabricated block.
//! - `ParagraphStyle`: `paragraph` → [`ParagraphStyle::BodyText`], `residual`
//!   → [`ParagraphStyle::Unknown`]; `provider_style_id` is always `None`
//!   (the provider style is not carried by the cleaned projection).
//! - [`SourceLocation`] is **projection-local**: the stream id is
//!   `wire:<view id>` and the span is `0..text.len()`. The bridge never
//!   fabricates XML/ODT artifact byte coordinates; the note on
//!   [`crate::hierarchy::extract_hierarchy`] applies unchanged. `source_format`
//!   is passed by the caller because the producer knows the document family —
//!   this module never guesses it.
//!
//! An unknown `view_kind` wire token can never reach this bridge: it is refused
//! fail-closed by [`crate::cleaned_wire::read_cleaned_wire`] /
//! [`ReaderViewKind::from_wire`] before a [`CleanedProjection`] value exists.
//!
//! Non-claims: a bridged block is a structural decode candidate. It is not
//! source authenticity, not a legal-completeness claim, not a normalized text
//! and not a `StructuralAst`/CST record. Segment text is preserved byte-for-byte
//! but is never verified against any external authority here.

use std::collections::HashMap;
use std::fmt;

use crate::cleaned_wire::CleanedProjection;
use crate::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use crate::reader_contract::ReaderViewKind;
use crate::reader_projection::{ProjectedSegment, ProjectedView};

/// Non-claims carried on the bridge surface itself: what a bridged block is
/// **not**. Pinned by the contract suite.
pub const WIRE_BLOCKS_NON_CLAIMS: &[&str] = &[
    "Bridged blocks are not source authenticity: the bridge reads a derived projection, never the artifact bytes.",
    "Bridged blocks are not a legal-completeness claim and never mint hierarchy or ComponentConcept identity.",
    "Bridged block anchors are projection-local (wire:<view id>), never XML/ODT artifact byte coordinates.",
    "Bridged text is byte-preserved but not normalized and not verified against any external authority.",
];

/// Failure class of the cleaned-wire → block bridge.
///
/// Every variant carries identifiers or closed tokens only — never decoded
/// text, so a refusal is safe to log.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WireBlocksError {
    /// A primary view referenced a segment absent from the projection.
    DanglingSegmentRef { view: String, segment: String },
    /// A segment carried no text in either channel (`segment.text` and
    /// `inline_texts` are both absent).
    MissingSegmentText { segment: String },
    /// The projection-local source stream id could not be built from the view
    /// id.
    InvalidSourceStream { view: String },
    /// [`ParsedBlock::try_new`] rejected the assembled block.
    BlockRejected { view: String, detail: String },
}

impl WireBlocksError {
    /// Closed string form used in diagnostics.
    pub const fn as_str(&self) -> &'static str {
        match self {
            WireBlocksError::DanglingSegmentRef { .. } => "dangling_segment_ref",
            WireBlocksError::MissingSegmentText { .. } => "missing_segment_text",
            WireBlocksError::InvalidSourceStream { .. } => "invalid_source_stream",
            WireBlocksError::BlockRejected { .. } => "block_rejected",
        }
    }
}

impl fmt::Display for WireBlocksError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WireBlocksError::DanglingSegmentRef { view, segment } => write!(
                formatter,
                "wire block bridge: view {view} references absent segment {segment}"
            ),
            WireBlocksError::MissingSegmentText { segment } => write!(
                formatter,
                "wire block bridge: segment {segment} carries no text"
            ),
            WireBlocksError::InvalidSourceStream { view } => write!(
                formatter,
                "wire block bridge: view {view} has no valid projection-local source stream"
            ),
            WireBlocksError::BlockRejected { view, detail } => write!(
                formatter,
                "wire block bridge: view {view} was rejected: {detail}"
            ),
        }
    }
}

impl std::error::Error for WireBlocksError {}

/// Rebuild a provider-neutral [`ParsedBlock`] stream from a materialized
/// cleaned projection.
///
/// `source_format` is supplied by the caller (the producer knows the document
/// family); the bridge does not infer it. Empty and whitespace-only views are
/// skipped without error. See the module documentation for the full mapping
/// contract and non-claims.
pub fn blocks_from_cleaned_projection(
    projection: &CleanedProjection,
    source_format: SourceFormatId,
) -> Result<Vec<ParsedBlock>, WireBlocksError> {
    let reader = &projection.projection;

    let inline_by_segment: HashMap<&str, &str> = projection
        .inline_texts
        .iter()
        .map(|inline| (inline.segment_id.as_str(), inline.text.as_str()))
        .collect();

    let mut segments_by_id: HashMap<&str, &ProjectedSegment> =
        HashMap::with_capacity(reader.segments.len());
    for segment in &reader.segments {
        segments_by_id.insert(segment.id.as_str(), segment);
    }

    let mut blocks: Vec<ParsedBlock> = Vec::new();
    for view in &reader.views {
        let style = match view.kind {
            ReaderViewKind::Paragraph => ParagraphStyle::BodyText,
            ReaderViewKind::Residual => ParagraphStyle::Unknown,
            // Navigation views own structure, never text.
            ReaderViewKind::Table
            | ReaderViewKind::Row
            | ReaderViewKind::Cell
            | ReaderViewKind::Note => continue,
        };
        let text = assemble_view_text(view, &segments_by_id, &inline_by_segment)?;
        if text.trim().is_empty() {
            continue;
        }
        let stream =
            SourceStreamId::parse(&format!("wire:{}", view.id.as_str())).map_err(|_| {
                WireBlocksError::InvalidSourceStream {
                    view: view.id.as_str().to_string(),
                }
            })?;
        let span =
            SourceSpan::try_new(0, text.len()).map_err(|_| WireBlocksError::BlockRejected {
                view: view.id.as_str().to_string(),
                detail: "projection-local span invalid".to_string(),
            })?;
        let block = ParsedBlock::try_new(
            text,
            None,
            style,
            SourceLocation::new(stream, span),
            source_format,
        )
        .map_err(|error| WireBlocksError::BlockRejected {
            view: view.id.as_str().to_string(),
            detail: format!("{error:?}"),
        })?;
        blocks.push(block);
    }
    Ok(blocks)
}

/// Concatenate a primary view's segment text in `ordinal` order.
///
/// Uses [`ProjectedSegment::text`] when present (derived controls) and falls
/// back to the wire `inline_texts` channel otherwise (source fragments). Fails
/// closed on a dangling segment reference or a segment that carries no text.
fn assemble_view_text(
    view: &ProjectedView,
    segments_by_id: &HashMap<&str, &ProjectedSegment>,
    inline_by_segment: &HashMap<&str, &str>,
) -> Result<String, WireBlocksError> {
    let mut ordered: Vec<&ProjectedSegment> = Vec::with_capacity(view.segment_refs.len());
    for segment_id in &view.segment_refs {
        let segment = segments_by_id.get(segment_id.as_str()).ok_or_else(|| {
            WireBlocksError::DanglingSegmentRef {
                view: view.id.as_str().to_string(),
                segment: segment_id.as_str().to_string(),
            }
        })?;
        ordered.push(segment);
    }
    ordered.sort_by_key(|segment| segment.ordinal);

    let mut text = String::new();
    for segment in ordered {
        match &segment.text {
            Some(piece) => text.push_str(piece),
            None => {
                let piece = inline_by_segment.get(segment.id.as_str()).ok_or_else(|| {
                    WireBlocksError::MissingSegmentText {
                        segment: segment.id.as_str().to_string(),
                    }
                })?;
                text.push_str(piece);
            }
        }
    }
    Ok(text)
}
