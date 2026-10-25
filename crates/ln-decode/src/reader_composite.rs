//! Composite coordinates over a reader projection's *reading order*.
//!
//! This module is the composite-coordinate half of
//! `prd/architecture/intermediate-source-reading-order-contract.md`: an output
//! range in a primary view is localized as an **ordered list of units**, where
//! each unit is either a sub-span of a source fragment or a derived control.
//! It resolves against the independently re-derived [`ReadingOrderIndex`]
//! (T02) and the frozen substrate records, never against the projection's
//! declared segment order, and it never re-parses XML.
//!
//! Provenance is read-only: each unit copies the segment's `element_ref` and
//! `source_pos` verbatim and derived units never invent a fragment or span. A
//! construction that crosses several fragments or a derived separator is
//! therefore addressed by several units, not by a fabricated single fragment.
//!
//! Non-claims: no raw decoded legal text logging, no XML byte coordinates, no
//! R1000 closure and no legal-completeness claim. `[bounded]` to one pinned
//! fixture. The module is serialization-agnostic: it imports no `serde`/JSON.

use std::collections::HashMap;
use std::fmt;

use crate::reader_contract::{
    ContractError, ContractErrorKind, ElementRef, FragmentRef, ReaderDerivedKind,
    ReaderFragmentSpan, ReaderRecordIndex, check_fragment_span,
};
use crate::reader_projection::{
    ProjectedSegment, ReaderProjection, SegmentId, SegmentOrigin, ViewId,
};
use crate::reader_reading_order::{ReadingOrderErrorKind, ReadingOrderIndex};
use crate::source_package::{Record, TextSlot};

// ------------------------------------------------------------------- errors #

/// Failure class of a composite-coordinate resolution.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompositeErrorKind {
    /// The requested view id has no projected view.
    UnknownView,
    /// The requested view is a navigation view (or has no primary reading
    /// order), so it carries no localizable units.
    NotPrimaryView,
    /// The requested range is empty or inverted, or selects no unit.
    EmptyOrInverted,
    /// The range end lies past the view output.
    OutOfBounds,
    /// A sub-span bound is not on a UTF-8 code point boundary.
    NotCharBoundary,
    /// The projection or reading order is internally inconsistent for this
    /// address (missing fragment, missing slot, unknown segment).
    SpanInvalid,
}

impl CompositeErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            CompositeErrorKind::UnknownView => "unknown_view",
            CompositeErrorKind::NotPrimaryView => "not_primary_view",
            CompositeErrorKind::EmptyOrInverted => "empty_or_inverted",
            CompositeErrorKind::OutOfBounds => "out_of_bounds",
            CompositeErrorKind::NotCharBoundary => "not_char_boundary",
            CompositeErrorKind::SpanInvalid => "span_invalid",
        }
    }
}

impl fmt::Display for CompositeErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed composite-coordinate error. Carries no serialization dependency.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompositeError {
    kind: CompositeErrorKind,
    detail: String,
}

impl CompositeError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: CompositeErrorKind, detail: impl Into<String>) -> Self {
        CompositeError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> CompositeErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for CompositeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for CompositeError {}

/// Maps a [`ContractErrorKind`] from `check_fragment_span` onto the composite
/// vocabulary; an unexpected class degrades to `SpanInvalid`, never to success.
fn map_span_error(error: ContractError) -> CompositeError {
    let kind = match error.kind() {
        ContractErrorKind::EmptyOrInverted => CompositeErrorKind::EmptyOrInverted,
        ContractErrorKind::OutOfBounds => CompositeErrorKind::OutOfBounds,
        ContractErrorKind::NotCharBoundary => CompositeErrorKind::NotCharBoundary,
        _ => CompositeErrorKind::SpanInvalid,
    };
    CompositeError::new(kind, error.detail().to_string())
}

// -------------------------------------------------------------------- types #

/// A half-open output range `[output_start, output_end)` over one primary view.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompositeAddress {
    /// The addressed primary view.
    pub view: ViewId,
    /// Inclusive byte offset into the view output.
    pub output_start: usize,
    /// Exclusive byte offset into the view output.
    pub output_end: usize,
}

/// One localized unit of a composite range: a source sub-span or a derived
/// control. The derived variant structurally cannot carry a fragment or span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CompositeUnit {
    /// A sub-span of a source fragment, copied with its provenance.
    Source {
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
    /// A documented derived control (tab / line break / page break).
    Derived {
        /// The owning projected segment.
        segment: SegmentId,
        /// The derived control kind.
        kind: ReaderDerivedKind,
        /// The anchoring element id (provenance, copied verbatim).
        element_ref: ElementRef,
        /// The substrate source position (provenance, copied verbatim).
        source_pos: usize,
    },
}

/// A resolved composite range: the addressed interval plus its ordered units.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CompositeRange {
    /// The addressed primary view.
    pub view: ViewId,
    /// Inclusive byte offset into the view output.
    pub output_start: usize,
    /// Exclusive byte offset into the view output.
    pub output_end: usize,
    /// The ordered units covering the interval, in reading order.
    pub units: Vec<CompositeUnit>,
}

impl CompositeRange {
    /// The address this range was resolved from (round-trips).
    pub fn to_address(&self) -> CompositeAddress {
        CompositeAddress {
            view: self.view.clone(),
            output_start: self.output_start,
            output_end: self.output_end,
        }
    }
}

// -------------------------------------------------------------- resolution #

/// Resolves a composite address against an already-built reading-order index.
///
/// Validation is fail-closed and ordered: the view must exist and be primary,
/// the interval must be non-empty, and its end must lie within the view output
/// before any per-segment span arithmetic is attempted. Every intersecting
/// segment contributes one unit, sub-spanned to the overlap and re-validated on
/// decoded code point boundaries; a derived unit never fabricates a fragment or
/// span. An interval that selects no unit is refused as `EmptyOrInverted`.
pub fn resolve_composite(
    projection: &ReaderProjection,
    order: &ReadingOrderIndex,
    records: &[Record],
    address: &CompositeAddress,
) -> Result<CompositeRange, CompositeError> {
    // 1. The view must be projected.
    let view = projection.view(&address.view).ok_or_else(|| {
        CompositeError::new(
            CompositeErrorKind::UnknownView,
            format!("view {} is not projected", address.view),
        )
    })?;

    // 2. Only primary (text-owning) views localize units.
    if !view.kind.is_primary() {
        return Err(CompositeError::new(
            CompositeErrorKind::NotPrimaryView,
            format!(
                "view {} is {} which is not a primary reading-order view",
                address.view,
                view.kind.as_str()
            ),
        ));
    }

    // 3. A composite range is a non-empty half-open interval.
    if address.output_start >= address.output_end {
        return Err(CompositeError::new(
            CompositeErrorKind::EmptyOrInverted,
            format!(
                "address [{}, {}) in view {} is empty or inverted",
                address.output_start, address.output_end, address.view
            ),
        ));
    }

    // 4. The reading order is the authority for segmentation, never the
    //    projection's declared refs.
    let segment_ids = order.reading_order(&address.view).map_err(|error| {
        let kind = match error.kind() {
            ReadingOrderErrorKind::NotPrimaryView => CompositeErrorKind::NotPrimaryView,
            _ => CompositeErrorKind::SpanInvalid,
        };
        CompositeError::new(kind, error.detail().to_string())
    })?;

    let segments_by_id: HashMap<&str, &ProjectedSegment> = projection
        .segments
        .iter()
        .map(|segment| (segment.id.as_str(), segment))
        .collect();

    // 5. The view output length is the end of the last segment in reading order.
    let view_len = match segment_ids.last() {
        Some(last) => match segments_by_id.get(last.as_str()) {
            Some(segment) => segment.output_end,
            None => {
                return Err(CompositeError::new(
                    CompositeErrorKind::SpanInvalid,
                    format!("view {} names unknown segment {last}", address.view),
                ));
            }
        },
        None => 0,
    };
    if address.output_end > view_len {
        return Err(CompositeError::new(
            CompositeErrorKind::OutOfBounds,
            format!(
                "address end {} exceeds view {} output length {}",
                address.output_end, address.view, view_len
            ),
        ));
    }

    // 6. One substrate index for the whole resolution.
    let index = ReaderRecordIndex::new(records).map_err(|error| {
        CompositeError::new(CompositeErrorKind::SpanInvalid, error.detail().to_string())
    })?;

    // 7. Walk the reading order, emitting one unit per intersecting segment.
    let mut units: Vec<CompositeUnit> = Vec::new();
    for id in segment_ids {
        let segment = segments_by_id.get(id.as_str()).ok_or_else(|| {
            CompositeError::new(
                CompositeErrorKind::SpanInvalid,
                format!("reading order names unknown segment {id}"),
            )
        })?;
        let lo = address.output_start.max(segment.output_start);
        let hi = address.output_end.min(segment.output_end);
        if lo >= hi {
            continue;
        }
        match segment.origin {
            SegmentOrigin::SourceFragment => {
                let fragment = segment.fragment_ref.clone().ok_or_else(|| {
                    CompositeError::new(
                        CompositeErrorKind::SpanInvalid,
                        format!("source segment {} has no fragment", segment.id),
                    )
                })?;
                let slot = segment.slot.ok_or_else(|| {
                    CompositeError::new(
                        CompositeErrorKind::SpanInvalid,
                        format!("source segment {} has no slot", segment.id),
                    )
                })?;
                let value = index.text(fragment.as_str()).ok_or_else(|| {
                    CompositeError::new(
                        CompositeErrorKind::SpanInvalid,
                        format!("fragment {fragment} is missing from the substrate"),
                    )
                })?;
                let span = ReaderFragmentSpan::new(
                    fragment.clone(),
                    lo - segment.output_start,
                    hi - segment.output_start,
                );
                check_fragment_span(&value.value, &span).map_err(map_span_error)?;
                units.push(CompositeUnit::Source {
                    segment: segment.id.clone(),
                    fragment_ref: fragment,
                    slot,
                    span,
                    element_ref: segment.element_ref.clone(),
                    source_pos: segment.source_pos,
                });
            }
            SegmentOrigin::Derived(kind) => {
                // A derived control carries no fragment/span by construction.
                units.push(CompositeUnit::Derived {
                    segment: segment.id.clone(),
                    kind,
                    element_ref: segment.element_ref.clone(),
                    source_pos: segment.source_pos,
                });
            }
        }
    }

    // 8. An interval that covers no unit is a typed refusal, never an empty Ok.
    if units.is_empty() {
        return Err(CompositeError::new(
            CompositeErrorKind::EmptyOrInverted,
            format!(
                "address [{}, {}) in view {} selects no unit",
                address.output_start, address.output_end, address.view
            ),
        ));
    }

    Ok(CompositeRange {
        view: address.view.clone(),
        output_start: address.output_start,
        output_end: address.output_end,
        units,
    })
}
