//! S05 clean view: versioned primary/service/dropped rules with retained
//! provenance over the frozen reader projection.
//!
//! This module is the filtered/display half of
//! `prd/architecture/intermediate-source-clean-view-contract.md`
//! (profile `reader_clean_profile/v1`). It is a read-only additive surface
//! over three frozen contracts: the S02 substrate records
//! (`crate::source_package`), the S03 reader projection
//! (`crate::reader_projection`) and the S04 reading-order index
//! (`crate::reader_reading_order`). It never calls
//! `crate::reader_projection::build_projection`, never re-parses XML and never
//! mutates its inputs; two builds over the same inputs are equal.
//!
//! Unit order comes only from [`ReadingOrderIndex::reading_order`]; unit
//! classification comes only from the segment's `semantic` through the total
//! [`CleanRuleProfile::v1()`] rule match (one pinned disposition per
//! `ReaderSemantic` class). A retained source unit keeps the §5 source
//! fragment form (`fragment_ref` / `slot` / `span`); a derived unit keeps the
//! derived form (`kind` plus literal, never an invented fragment or span); a
//! dropped unit carries its `rule_id` plus the element anchor and source
//! position, never an invented fragment or span. No revision class is
//! silently discarded: `revision_insertion` is primary and
//! `revision_deletion` is service.
//!
//! Non-claims: the clean view is not semantic or legal content, not
//! normalization, not an authenticity claim, and it does not close R1000.
//! Errors and provenance carry ids, offsets and rule ids only — never decoded
//! text.

use std::collections::HashMap;
use std::fmt;

use crate::reader_contract::{
    ElementRef, FragmentRef, ReaderDerivedKind, ReaderFragmentSpan, ReaderRecordIndex,
    ReaderSemantic, check_fragment_span,
};
use crate::reader_projection::{
    ProjectedSegment, ReaderProjection, SegmentId, SegmentOrigin, ViewId,
};
use crate::reader_reading_order::ReadingOrderIndex;
use crate::source_package::{Record, TextSlot};

// ------------------------------------------------------------------ profile #

/// The clean-rule profile id pinned by the S05 design contract.
pub const READER_CLEAN_PROFILE: &str = "reader_clean_profile/v1";

/// What a clean unit contributes to the filtered output.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CleanDisposition {
    /// Primary text: the readable body a display layer renders first.
    Primary,
    /// Service content: retained and mapped, but not part of the primary text.
    Service,
    /// Dropped from the clean output; the rule id and the anchor stay behind.
    Dropped,
}

impl CleanDisposition {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            CleanDisposition::Primary => "primary",
            CleanDisposition::Service => "service",
            CleanDisposition::Dropped => "dropped",
        }
    }
}

/// One versioned clean rule: a pinned rule id, the semantic class it owns and
/// the disposition it assigns. Rule ids match the machine-readable
/// `clean-rule-profile` block of the design contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct CleanRule {
    pub id: &'static str,
    pub class: ReaderSemantic,
    pub disposition: CleanDisposition,
}

static RULE_BODY: CleanRule = CleanRule {
    id: "rcv1_body",
    class: ReaderSemantic::Body,
    disposition: CleanDisposition::Primary,
};

static RULE_WHITESPACE: CleanRule = CleanRule {
    id: "rcv1_whitespace",
    class: ReaderSemantic::Whitespace,
    disposition: CleanDisposition::Service,
};

static RULE_FIELD_CODE: CleanRule = CleanRule {
    id: "rcv1_field_code",
    class: ReaderSemantic::FieldCode,
    disposition: CleanDisposition::Service,
};

static RULE_REVISION_INSERTION: CleanRule = CleanRule {
    id: "rcv1_revision_insertion",
    class: ReaderSemantic::RevisionInsertion,
    disposition: CleanDisposition::Primary,
};

static RULE_REVISION_DELETION: CleanRule = CleanRule {
    id: "rcv1_revision_deletion",
    class: ReaderSemantic::RevisionDeletion,
    disposition: CleanDisposition::Service,
};

static RULE_DERIVED_SEPARATOR: CleanRule = CleanRule {
    id: "rcv1_derived_separator",
    class: ReaderSemantic::DerivedSeparator,
    disposition: CleanDisposition::Service,
};

static RULE_EMPTY: CleanRule = CleanRule {
    id: "rcv1_empty",
    class: ReaderSemantic::Empty,
    disposition: CleanDisposition::Dropped,
};

static V1_RULES: &[CleanRule] = &[
    RULE_BODY,
    RULE_WHITESPACE,
    RULE_FIELD_CODE,
    RULE_REVISION_INSERTION,
    RULE_REVISION_DELETION,
    RULE_DERIVED_SEPARATOR,
    RULE_EMPTY,
];

static V1_PROFILE: CleanRuleProfile = CleanRuleProfile {
    id: READER_CLEAN_PROFILE,
    rules: V1_RULES,
};

/// The versioned clean-rule profile. Total over the closed seven-class
/// `ReaderSemantic` vocabulary: no class can fall through to a default.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CleanRuleProfile {
    id: &'static str,
    rules: &'static [CleanRule],
}

impl CleanRuleProfile {
    /// The pinned `v1` profile.
    pub const fn v1() -> &'static Self {
        &V1_PROFILE
    }

    /// The profile id (`reader_clean_profile/v1`).
    pub const fn id(&self) -> &'static str {
        self.id
    }

    /// Every rule of the profile, in pinned order.
    pub const fn rules(&self) -> &'static [CleanRule] {
        self.rules
    }

    /// The rule for a semantic class — a closed match over all seven classes.
    pub const fn rule_for(&self, class: ReaderSemantic) -> &'static CleanRule {
        match class {
            ReaderSemantic::Body => &RULE_BODY,
            ReaderSemantic::Whitespace => &RULE_WHITESPACE,
            ReaderSemantic::FieldCode => &RULE_FIELD_CODE,
            ReaderSemantic::RevisionInsertion => &RULE_REVISION_INSERTION,
            ReaderSemantic::RevisionDeletion => &RULE_REVISION_DELETION,
            ReaderSemantic::DerivedSeparator => &RULE_DERIVED_SEPARATOR,
            ReaderSemantic::Empty => &RULE_EMPTY,
        }
    }
}

// ------------------------------------------------------------------- errors #

/// Failure class of the clean view build.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CleanErrorKind {
    /// A primary-kind projection view has no entry in the reading-order index.
    UnknownView,
    /// The requested id is not a primary clean-view surface (a navigation view
    /// or an unknown id).
    NotPrimaryView,
    /// The confirmed reading order references a segment id with no projection
    /// record, or a segment owned by another view.
    UnknownSegment,
    /// A retained source span is not a valid non-empty half-open range of the
    /// decoded fragment value.
    SpanInvalid,
    /// A retained source unit cannot resolve its §5 source form: the fragment,
    /// slot or span is missing, or the substrate does not carry the fragment.
    SourceMappingIncomplete,
}

impl CleanErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            CleanErrorKind::UnknownView => "unknown_view",
            CleanErrorKind::NotPrimaryView => "not_primary_view",
            CleanErrorKind::UnknownSegment => "unknown_segment",
            CleanErrorKind::SpanInvalid => "span_invalid",
            CleanErrorKind::SourceMappingIncomplete => "source_mapping_incomplete",
        }
    }
}

impl fmt::Display for CleanErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed clean-view error. Carries no serialization dependency and never
/// contains decoded text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanError {
    kind: CleanErrorKind,
    detail: String,
}

impl CleanError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: CleanErrorKind, detail: impl Into<String>) -> Self {
        CleanError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> CleanErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for CleanError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for CleanError {}

// -------------------------------------------------------------------- units #

/// One clean unit: the projection segment as seen through the profile, with
/// its §5 provenance retained.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CleanUnit {
    /// A retained source segment: the full §5 source fragment form.
    Source {
        view: ViewId,
        segment: SegmentId,
        fragment_ref: FragmentRef,
        slot: TextSlot,
        span: ReaderFragmentSpan,
        element_ref: ElementRef,
        source_pos: usize,
        disposition: CleanDisposition,
    },
    /// A generated control segment: the derived form, with no fragment and no
    /// span.
    Derived {
        view: ViewId,
        segment: SegmentId,
        kind: ReaderDerivedKind,
        element_ref: ElementRef,
        source_pos: usize,
        literal: &'static str,
        disposition: CleanDisposition,
    },
    /// A dropped unit: rule id plus element anchor and source position, never
    /// an invented fragment or span.
    Dropped {
        view: ViewId,
        segment: SegmentId,
        element_ref: ElementRef,
        source_pos: usize,
        rule_id: &'static str,
    },
}

impl CleanUnit {
    /// The owning view.
    pub fn view(&self) -> &ViewId {
        match self {
            CleanUnit::Source { view, .. }
            | CleanUnit::Derived { view, .. }
            | CleanUnit::Dropped { view, .. } => view,
        }
    }

    /// The originating projection segment.
    pub fn segment(&self) -> &SegmentId {
        match self {
            CleanUnit::Source { segment, .. }
            | CleanUnit::Derived { segment, .. }
            | CleanUnit::Dropped { segment, .. } => segment,
        }
    }

    /// The disposition the profile assigned to this unit.
    pub const fn disposition(&self) -> CleanDisposition {
        match self {
            CleanUnit::Source { disposition, .. } | CleanUnit::Derived { disposition, .. } => {
                *disposition
            }
            CleanUnit::Dropped { .. } => CleanDisposition::Dropped,
        }
    }
}

// --------------------------------------------------------------------- view #

/// One primary view's filtered output: the primary text and the service text
/// concatenated in reading order.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ViewCleanText {
    view: ViewId,
    primary: String,
    service: String,
}

impl ViewCleanText {
    /// The view id.
    pub fn view(&self) -> &ViewId {
        &self.view
    }

    /// The view's primary text.
    pub fn primary(&self) -> &str {
        &self.primary
    }

    /// The view's service text.
    pub fn service(&self) -> &str {
        &self.service
    }
}

/// The clean view over a reader projection: every primary view's segments in
/// confirmed reading order, classified by the pinned profile, with provenance
/// retained per unit.
///
/// The view is a read-only additive surface: `build` consumes its inputs by
/// shared reference, never mutates them, and is idempotent.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CleanView {
    profile: &'static CleanRuleProfile,
    units: Vec<CleanUnit>,
    view_texts: Vec<ViewCleanText>,
    primary_text: String,
    service_text: String,
}

impl CleanView {
    /// Builds the clean view.
    ///
    /// Primary views are taken in projection order; within a view the segment
    /// order comes only from `ReadingOrderIndex::reading_order`. Navigation
    /// views are skipped: they are structure-only and never own a segment. A
    /// primary view missing from the index, an unresolvable segment, an
    /// invalid retained span or an unresolvable source form is a typed
    /// refusal, never a silent skip.
    pub fn build(
        projection: &ReaderProjection,
        order: &ReadingOrderIndex,
        records: &[Record],
    ) -> Result<CleanView, CleanError> {
        let record_index = ReaderRecordIndex::new(records).map_err(|error| {
            CleanError::new(
                CleanErrorKind::SourceMappingIncomplete,
                format!("substrate index is not readable: {}", error.detail()),
            )
        })?;
        let segment_by_id: HashMap<&str, &ProjectedSegment> = projection
            .segments
            .iter()
            .map(|segment| (segment.id.as_str(), segment))
            .collect();

        let mut units: Vec<CleanUnit> = Vec::new();
        let mut view_texts: Vec<ViewCleanText> = Vec::new();
        let mut primary_total = String::new();
        let mut service_total = String::new();

        for view in &projection.views {
            if !view.kind.is_primary() {
                // Navigation views are structure-only: they never own a
                // segment and never enter the clean output.
                continue;
            }
            let ordered = order.reading_order(&view.id).map_err(|error| {
                CleanError::new(
                    CleanErrorKind::UnknownView,
                    format!(
                        "primary view {} has no reading-order entry: {}",
                        view.id,
                        error.detail()
                    ),
                )
            })?;
            let mut primary = String::new();
            let mut service = String::new();
            for segment_id in ordered {
                let segment = segment_by_id
                    .get(segment_id.as_str())
                    .ok_or_else(|| {
                        CleanError::new(
                            CleanErrorKind::UnknownSegment,
                            format!(
                                "reading order of view {} references segment {segment_id} with no projection record",
                                view.id
                            ),
                        )
                    })?;
                if segment.view != view.id {
                    return Err(CleanError::new(
                        CleanErrorKind::UnknownSegment,
                        format!(
                            "segment {} is owned by view {}, not {}",
                            segment.id, segment.view, view.id
                        ),
                    ));
                }
                let rule = CleanRuleProfile::v1().rule_for(segment.semantic);
                match segment.origin {
                    SegmentOrigin::Derived(kind) => {
                        let literal = kind.literal();
                        units.push(CleanUnit::Derived {
                            view: view.id.clone(),
                            segment: segment.id.clone(),
                            kind,
                            element_ref: segment.element_ref.clone(),
                            source_pos: segment.source_pos,
                            literal,
                            disposition: rule.disposition,
                        });
                        push_rendered(&mut primary, &mut service, rule.disposition, literal);
                    }
                    SegmentOrigin::SourceFragment => {
                        if rule.disposition == CleanDisposition::Dropped {
                            units.push(CleanUnit::Dropped {
                                view: view.id.clone(),
                                segment: segment.id.clone(),
                                element_ref: segment.element_ref.clone(),
                                source_pos: segment.source_pos,
                                rule_id: rule.id,
                            });
                            continue;
                        }
                        let fragment = segment
                            .fragment_ref
                            .as_ref()
                            .ok_or_else(|| incomplete(segment, "has no fragment reference"))?;
                        let slot = segment
                            .slot
                            .ok_or_else(|| incomplete(segment, "has no text slot"))?;
                        let span = segment
                            .span
                            .clone()
                            .ok_or_else(|| incomplete(segment, "has no source span"))?;
                        let value = &record_index
                            .text(fragment.as_str())
                            .ok_or_else(|| {
                                incomplete(segment, "names a fragment missing from the substrate")
                            })?
                            .value;
                        if let Err(error) = check_fragment_span(value, &span) {
                            return Err(CleanError::new(
                                CleanErrorKind::SpanInvalid,
                                format!("segment {} retained span rejected: {error}", segment.id),
                            ));
                        }
                        let rendered = &value[span.start..span.end];
                        units.push(CleanUnit::Source {
                            view: view.id.clone(),
                            segment: segment.id.clone(),
                            fragment_ref: fragment.clone(),
                            slot,
                            span,
                            element_ref: segment.element_ref.clone(),
                            source_pos: segment.source_pos,
                            disposition: rule.disposition,
                        });
                        push_rendered(&mut primary, &mut service, rule.disposition, rendered);
                    }
                }
            }
            primary_total.push_str(&primary);
            service_total.push_str(&service);
            view_texts.push(ViewCleanText {
                view: view.id.clone(),
                primary,
                service,
            });
        }

        Ok(CleanView {
            profile: CleanRuleProfile::v1(),
            units,
            view_texts,
            primary_text: primary_total,
            service_text: service_total,
        })
    }

    /// The profile id the view was built with.
    pub const fn profile_id(&self) -> &'static str {
        self.profile.id()
    }

    /// Every clean unit, in per-view reading order.
    pub fn units(&self) -> &[CleanUnit] {
        &self.units
    }

    /// Per-view filtered output, in projection view order.
    pub fn view_texts(&self) -> &[ViewCleanText] {
        &self.view_texts
    }

    /// The ids of the primary clean-view surfaces.
    pub fn view_ids(&self) -> Vec<ViewId> {
        self.view_texts
            .iter()
            .map(|text| text.view.clone())
            .collect()
    }

    /// The full primary text across all views, in view order.
    pub fn primary_text(&self) -> &str {
        &self.primary_text
    }

    /// The full service text across all views, in view order.
    pub fn service_text(&self) -> &str {
        &self.service_text
    }

    /// The filtered output of one primary view.
    ///
    /// A navigation view (or any id without a primary clean surface) is
    /// refused with [`CleanErrorKind::NotPrimaryView`].
    pub fn view_text(&self, view: &ViewId) -> Result<&ViewCleanText, CleanError> {
        self.view_texts
            .iter()
            .find(|text| &text.view == view)
            .ok_or_else(|| {
                CleanError::new(
                    CleanErrorKind::NotPrimaryView,
                    format!("view {view} is not a primary clean-view surface"),
                )
            })
    }
}

fn push_rendered(
    primary: &mut String,
    service: &mut String,
    disposition: CleanDisposition,
    rendered: &str,
) {
    match disposition {
        CleanDisposition::Primary => primary.push_str(rendered),
        CleanDisposition::Service => service.push_str(rendered),
        CleanDisposition::Dropped => {}
    }
}

fn incomplete(segment: &ProjectedSegment, reason: &str) -> CleanError {
    CleanError::new(
        CleanErrorKind::SourceMappingIncomplete,
        format!("source segment {} {reason}", segment.id),
    )
}
