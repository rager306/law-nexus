//! Independent reading-order index over an existing reader projection.
//!
//! This module is the reading-order half of
//! `prd/architecture/intermediate-source-reading-order-contract.md`: it
//! re-derives the per-view reading order from the frozen substrate event walk
//! using only the S02 `crate::reader_contract` primitives, then checks that
//! re-derived order against the projection. It never calls
//! `crate::reader_projection::build_projection` and never reads
//! `ReaderProjection::content_hash`, so a re-sealed segment permutation is still
//! caught.
//!
//! Reading order is explicitly **not** record order: the substrate pre-order
//! walk (own `text_ref`, then a documented control, then children in document
//! order, each followed by that child's `tail_ref`) only coincidentally matches
//! the raw `tN` stream. [`ReadingOrderIndex::record_order`] exposes the contrast
//! surface and [`ReadingOrderIndex::is_record_order_coincident`] compares them.
//!
//! The module is serialization-agnostic: it does not import `serde` or any JSON
//! crate. Non-claims: no raw decoded-text logging, no XML byte coordinates, no
//! closure of R1000 and no legal-completeness claim.

use std::collections::HashMap;
use std::fmt;

use crate::reader_contract::{
    ElementRef, FragmentRef, ReaderDerivedKind, ReaderRecordIndex, ReaderRole, ReaderViewKey,
    ReaderViewKind, control_derived_kind, tail_view_key, view_key,
};
use crate::reader_projection::{
    ProjectedSegment, ReaderProjection, SegmentId, SegmentOrigin, ViewId,
};
use crate::source_package::{ElementRecord, Record};

// ------------------------------------------------------------------- errors #

/// Failure class of the reading-order index.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReadingOrderErrorKind {
    /// The re-derived segment order does not match the projection's declared
    /// order for a primary view (including a resealed permutation).
    OrderMismatch,
    /// A primary view's segment ordinals are not a contiguous `0..n`.
    OrdinalGap,
    /// A primary view's `output_start` / `output_end` are not continuous from
    /// zero, or leave the view output length.
    OutputGap,
    /// A view references a segment id that has no record in
    /// `ReaderProjection::segments`.
    UnknownSegment,
    /// A non-primary (navigation) view was requested as a reading-order surface.
    NotPrimaryView,
}

impl ReadingOrderErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ReadingOrderErrorKind::OrderMismatch => "order_mismatch",
            ReadingOrderErrorKind::OrdinalGap => "ordinal_gap",
            ReadingOrderErrorKind::OutputGap => "output_gap",
            ReadingOrderErrorKind::UnknownSegment => "unknown_segment",
            ReadingOrderErrorKind::NotPrimaryView => "not_primary_view",
        }
    }
}

impl fmt::Display for ReadingOrderErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed reading-order error. Carries no serialization dependency.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReadingOrderError {
    kind: ReadingOrderErrorKind,
    detail: String,
}

impl ReadingOrderError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: ReadingOrderErrorKind, detail: impl Into<String>) -> Self {
        ReadingOrderError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> ReadingOrderErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for ReadingOrderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for ReadingOrderError {}

fn mismatch(detail: impl Into<String>) -> ReadingOrderError {
    ReadingOrderError::new(ReadingOrderErrorKind::OrderMismatch, detail)
}

// ------------------------------------------------------------ walk events #

/// One reading-order event reconstructed from the substrate (never re-parsed
/// from XML). References are intentionally absent: they never own a segment and
/// so never affect reading order.
#[derive(Debug, Clone, PartialEq, Eq)]
enum WalkEvent {
    Source {
        fragment_id: String,
        view: ReaderViewKey,
    },
    Derived {
        kind: ReaderDerivedKind,
        view: ReaderViewKey,
    },
}

impl WalkEvent {
    fn view_key(&self) -> &ReaderViewKey {
        match self {
            WalkEvent::Source { view, .. } | WalkEvent::Derived { view, .. } => view,
        }
    }
}

/// Reconstructs the ordered reading-order events from substrate records only,
/// mirroring the `capture` pre-order (own `text_ref`, a documented control,
/// children in document order, then each child's `tail_ref`).
fn document_events(index: &ReaderRecordIndex) -> Result<Vec<WalkEvent>, ReadingOrderError> {
    let mut children: HashMap<String, Vec<&ElementRecord>> = HashMap::new();
    let mut roots: Vec<&ElementRecord> = Vec::new();
    for element in index.elements() {
        match &element.parent {
            Some(parent) => children.entry(parent.clone()).or_default().push(element),
            None => roots.push(element),
        }
    }
    for kids in children.values_mut() {
        kids.sort_by_key(|element| index.source_pos(&element.id).unwrap_or(usize::MAX));
    }
    roots.sort_by_key(|element| index.source_pos(&element.id).unwrap_or(usize::MAX));

    enum Step<'a> {
        Node(&'a ElementRecord),
        Tail(&'a ElementRecord),
    }

    let mut events: Vec<WalkEvent> = Vec::new();
    let mut stack: Vec<Step<'_>> = roots.iter().rev().map(|root| Step::Node(root)).collect();
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(element) => {
                let role = index.role_of(&element.id).ok_or_else(|| {
                    mismatch(format!(
                        "element {} is missing from the substrate index",
                        element.id
                    ))
                })?;
                let element_ref = ElementRef::new(element.id.as_str());
                if let Some(text_ref) = &element.text_ref {
                    let view = view_key(index, &element_ref)
                        .map_err(|e| mismatch(e.detail().to_string()))?;
                    events.push(WalkEvent::Source {
                        fragment_id: text_ref.clone(),
                        view,
                    });
                }
                if role == ReaderRole::Control
                    && element.text_ref.is_none()
                    && let Some(kind) = control_derived_kind(&element.clark_tag, &element.attrs)
                {
                    let view = view_key(index, &element_ref)
                        .map_err(|e| mismatch(e.detail().to_string()))?;
                    events.push(WalkEvent::Derived { kind, view });
                }
                if let Some(kids) = children.get(&element.id) {
                    for child in kids.iter().rev() {
                        stack.push(Step::Tail(child));
                        stack.push(Step::Node(child));
                    }
                }
            }
            Step::Tail(element) => {
                if let Some(tail_ref) = &element.tail_ref {
                    let element_ref = ElementRef::new(element.id.as_str());
                    let view = tail_view_key(index, &element_ref)
                        .map_err(|e| mismatch(e.detail().to_string()))?;
                    events.push(WalkEvent::Source {
                        fragment_id: tail_ref.clone(),
                        view,
                    });
                }
            }
        }
    }
    Ok(events)
}

// --------------------------------------------------------------- content #

/// Resolved content of one ordered segment: a source fragment or a documented
/// derived control. The literal is recomputed from the kind, never trusted from
/// the projection.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Content {
    Source(FragmentRef),
    Derived(ReaderDerivedKind),
}

/// One primary view's confirmed reading order plus the content needed to render
/// it without trusting the projection.
#[derive(Debug, Clone, PartialEq, Eq)]
struct OrderedView {
    view: ViewId,
    segments: Vec<SegmentId>,
    contents: Vec<Content>,
}

/// One re-derived segment token used to compare against the projection.
#[derive(Debug, Clone, PartialEq, Eq)]
enum Token {
    Source(String),
    Derived(ReaderDerivedKind),
}

fn token_of_segment(segment: &ProjectedSegment) -> Option<Token> {
    match segment.origin {
        SegmentOrigin::SourceFragment => segment
            .fragment_ref
            .as_ref()
            .map(|fragment| Token::Source(fragment.as_str().to_string())),
        SegmentOrigin::Derived(kind) => Some(Token::Derived(kind)),
    }
}

fn content_len(index: &ReaderRecordIndex, segment: &ProjectedSegment) -> Option<usize> {
    match segment.origin {
        SegmentOrigin::SourceFragment => {
            let fragment = segment.fragment_ref.as_ref()?;
            Some(index.text(fragment.as_str())?.value.len())
        }
        SegmentOrigin::Derived(kind) => Some(kind.literal().len()),
    }
}

// ------------------------------------------------------------------ index #

/// Reading-order index over a reader projection: for every primary view it
/// carries the independently re-derived segment order and resolved content.
///
/// The index is a read-only additive surface. It does not mutate the projection
/// or the substrate and makes no legal claim.
#[derive(Debug, Clone)]
pub struct ReadingOrderIndex {
    index: ReaderRecordIndex,
    views: Vec<OrderedView>,
    /// View id -> position in `views`. An additive lookup index: without it
    /// [`ReadingOrderIndex::lookup`] was a linear scan of `views` on every call,
    /// which made a per-view consumer quadratic in the view count (a
    /// multi-paragraph document owns one primary view per paragraph). The map is
    /// derived from `views` and never changes the resolved order or any error.
    positions: HashMap<String, usize>,
}

impl ReadingOrderIndex {
    /// Independently re-derives each primary view's reading order from the
    /// substrate events and checks it against `projection`.
    ///
    /// Fails closed with every inconsistency found across the projection:
    /// [`ReadingOrderErrorKind::OrderMismatch`] (re-derived order diverges, or a
    /// substrate event targets a view the projection lacks),
    /// [`ReadingOrderErrorKind::OrdinalGap`],
    /// [`ReadingOrderErrorKind::OutputGap`] and
    /// [`ReadingOrderErrorKind::UnknownSegment`].
    pub fn build(
        projection: &ReaderProjection,
        records: &[Record],
    ) -> Result<ReadingOrderIndex, Vec<ReadingOrderError>> {
        let index = ReaderRecordIndex::new(records).map_err(|error| {
            vec![mismatch(format!(
                "substrate index is not readable: {}",
                error.detail()
            ))]
        })?;
        let events = document_events(&index).map_err(|error| vec![error])?;

        // Group the re-derived tokens by ownership view key.
        let mut derived: HashMap<(ReaderViewKind, String), Vec<Token>> = HashMap::new();
        for event in &events {
            let key = event.view_key();
            let bucket = derived
                .entry((key.kind, key.element_ref.as_str().to_string()))
                .or_default();
            match event {
                WalkEvent::Source { fragment_id, .. } => {
                    bucket.push(Token::Source(fragment_id.clone()));
                }
                WalkEvent::Derived { kind, .. } => bucket.push(Token::Derived(*kind)),
            }
        }

        let segment_by_id: HashMap<&str, &ProjectedSegment> = projection
            .segments
            .iter()
            .map(|segment| (segment.id.as_str(), segment))
            .collect();

        let mut errors: Vec<ReadingOrderError> = Vec::new();
        let mut views: Vec<OrderedView> = Vec::new();

        for view in &projection.views {
            if !view.kind.is_primary() {
                continue;
            }
            // Resolve the declared segment refs; an unresolved ref is a typed
            // refusal, never a silent skip.
            let mut resolved: Vec<&ProjectedSegment> = Vec::new();
            let mut missing = false;
            for id in &view.segment_refs {
                match segment_by_id.get(id.as_str()) {
                    Some(segment) => resolved.push(segment),
                    None => {
                        errors.push(ReadingOrderError::new(
                            ReadingOrderErrorKind::UnknownSegment,
                            format!("view {} references segment {} with no record", view.id, id),
                        ));
                        missing = true;
                    }
                }
            }
            if missing {
                continue;
            }

            // Ordinals within a primary view must be a contiguous `0..n`.
            let mut ordinals: Vec<usize> = resolved.iter().map(|segment| segment.ordinal).collect();
            ordinals.sort_unstable();
            if ordinals != (0..resolved.len()).collect::<Vec<_>>() {
                errors.push(ReadingOrderError::new(
                    ReadingOrderErrorKind::OrdinalGap,
                    format!(
                        "view {} ordinals are not a contiguous 0..{}: {:?}",
                        view.id,
                        resolved.len(),
                        ordinals
                    ),
                ));
                continue;
            }

            // Output ranges must chain from zero in ordinal order.
            let mut by_ordinal = resolved.clone();
            by_ordinal.sort_by_key(|segment| segment.ordinal);
            let mut running: usize = 0;
            let mut output_ok = true;
            for segment in &by_ordinal {
                if segment.output_start != running {
                    errors.push(ReadingOrderError::new(
                        ReadingOrderErrorKind::OutputGap,
                        format!(
                            "view {} segment {} starts at {} not {}",
                            view.id, segment.id, segment.output_start, running
                        ),
                    ));
                    output_ok = false;
                    break;
                }
                let Some(len) = content_len(&index, segment) else {
                    errors.push(mismatch(format!(
                        "view {} segment {} has no resolvable content",
                        view.id, segment.id
                    )));
                    output_ok = false;
                    break;
                };
                if segment.output_end != running + len {
                    errors.push(ReadingOrderError::new(
                        ReadingOrderErrorKind::OutputGap,
                        format!(
                            "view {} segment {} ends at {} not {}",
                            view.id,
                            segment.id,
                            segment.output_end,
                            running + len
                        ),
                    ));
                    output_ok = false;
                    break;
                }
                running = segment.output_end;
            }
            if !output_ok {
                continue;
            }

            // The declared order must equal the independently re-derived order.
            let mut actual: Vec<Token> = Vec::with_capacity(resolved.len());
            let mut token_ok = true;
            for segment in &resolved {
                match token_of_segment(segment) {
                    Some(token) => actual.push(token),
                    None => {
                        errors.push(mismatch(format!(
                            "view {} segment {} has no origin token",
                            view.id, segment.id
                        )));
                        token_ok = false;
                        break;
                    }
                }
            }
            if !token_ok {
                continue;
            }
            let expected = derived
                .get(&(view.kind, view.element_ref.as_str().to_string()))
                .cloned()
                .unwrap_or_default();
            if expected != actual {
                errors.push(mismatch(format!(
                    "view {} reading order diverges from the projection: substrate {expected:?} != projection {actual:?}",
                    view.id
                )));
                continue;
            }

            let segments: Vec<SegmentId> =
                resolved.iter().map(|segment| segment.id.clone()).collect();
            let contents: Vec<Content> = actual
                .iter()
                .map(|token| match token {
                    Token::Source(id) => Content::Source(FragmentRef::new(id.clone())),
                    Token::Derived(kind) => Content::Derived(*kind),
                })
                .collect();
            views.push(OrderedView {
                view: view.id.clone(),
                segments,
                contents,
            });
        }

        // A substrate event must target a view the projection actually carries.
        let known: HashMap<(ReaderViewKind, String), ()> = projection
            .views
            .iter()
            .map(|view| ((view.kind, view.element_ref.as_str().to_string()), ()))
            .collect();
        for (key, tokens) in &derived {
            if !tokens.is_empty() && !known.contains_key(key) {
                errors.push(mismatch(format!(
                    "substrate events target missing view {} {}",
                    key.0.as_str(),
                    key.1
                )));
            }
        }

        if !errors.is_empty() {
            return Err(errors);
        }
        Ok(ReadingOrderIndex {
            positions: views
                .iter()
                .enumerate()
                .map(|(position, ordered)| (ordered.view.as_str().to_string(), position))
                .collect(),
            index,
            views,
        })
    }

    /// The confirmed reading order of a primary view.
    ///
    /// A navigation view (or any id without a primary reading order) is refused
    /// with [`ReadingOrderErrorKind::NotPrimaryView`].
    pub fn reading_order(&self, view: &ViewId) -> Result<&[SegmentId], ReadingOrderError> {
        Ok(&self.lookup(view)?.segments)
    }

    /// Renders the view output by concatenating segments in reading order:
    /// source fragments contribute their decoded substrate value, derived
    /// segments contribute their documented literal.
    ///
    /// A navigation view is refused with
    /// [`ReadingOrderErrorKind::NotPrimaryView`].
    pub fn view_output(&self, view: &ViewId) -> Result<String, ReadingOrderError> {
        let ordered = self.lookup(view)?;
        let mut output = String::new();
        for content in &ordered.contents {
            match content {
                Content::Source(fragment) => {
                    let text = self.index.text(fragment.as_str()).ok_or_else(|| {
                        mismatch(format!("fragment {fragment} is missing from the substrate"))
                    })?;
                    output.push_str(&text.value);
                }
                Content::Derived(kind) => output.push_str(kind.literal()),
            }
        }
        Ok(output)
    }

    /// The document order of the `tN` substrate records as laid out in `records`
    /// (the contrast surface: record order is not reading order).
    pub fn record_order(&self, records: &[Record]) -> Vec<FragmentRef> {
        records
            .iter()
            .filter_map(|record| match record {
                Record::Text(text) => Some(FragmentRef::new(text.id.clone())),
                Record::Element(_) => None,
            })
            .collect()
    }

    /// True when the flattened reading order coincides with the substrate record
    /// order. A `false` result is the explicit proof that the two orders differ.
    pub fn is_record_order_coincident(&self, records: &[Record]) -> bool {
        let record = self.record_order(records);
        let mut reading: Vec<FragmentRef> = Vec::new();
        for view in &self.views {
            for content in &view.contents {
                if let Content::Source(fragment) = content {
                    reading.push(fragment.clone());
                }
            }
        }
        reading == record
    }

    fn lookup(&self, view: &ViewId) -> Result<&OrderedView, ReadingOrderError> {
        match self.positions.get(view.as_str()) {
            Some(position) => Ok(&self.views[*position]),
            None => Err(ReadingOrderError::new(
                ReadingOrderErrorKind::NotPrimaryView,
                format!("view {view} is not a primary reading-order view"),
            )),
        }
    }
}
