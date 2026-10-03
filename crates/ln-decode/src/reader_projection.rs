//! S03 reader projection over the frozen `source_package`.
//!
//! This module is the typed record half of
//! `prd/architecture/reader-projection-contract.md` (pinned provider profile
//! `reader_wordml_profile/v1`). It builds the view forest on top of the S02
//! coordinate base (`crate::reader_contract`); the ordered segment and reference
//! records are filled by later tasks of the same slice.
//!
//! The module has no serialization dependency: it does not import `serde` or any
//! JSON crate. Canonical serialization is a hand-rolled writer and the content
//! seal is a `sha2` digest over those bytes.
//!
//! Non-claims: raw decoded text without normalization; no XML byte coordinates;
//! no temporal `StructuralAst`/CST/CTV; provider-bounded Consultant WordML; no
//! R1000 closure and no legal-completeness claim.

use std::collections::{HashMap, HashSet};
use std::fmt;

use crate::reader_contract::{
    partition_primary_views, view_key, ContractError, ContractErrorKind, ElementRef, FragmentRef,
    ReaderDerivedKind, ReaderFragmentSpan, ReaderRecordIndex, ReaderReferenceType, ReaderRole,
    ReaderSegmentKind, ReaderSemantic, ReaderViewKind,
};
use crate::source_package::{Record, TextSlot};

// ------------------------------------------------------------------- ids #

/// Reader projection view id (`vN`), assigned in `source_pos` order.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ViewId(String);

impl ViewId {
    /// Builds a view id from a raw token.
    pub fn new(id: impl Into<String>) -> Self {
        ViewId(id.into())
    }

    /// The raw token.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for ViewId {
    fn from(id: &str) -> Self {
        ViewId(id.to_string())
    }
}

impl fmt::Display for ViewId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Reader projection segment id (`sN`), assigned in construction order.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct SegmentId(String);

impl SegmentId {
    /// Builds a segment id from a raw token.
    pub fn new(id: impl Into<String>) -> Self {
        SegmentId(id.into())
    }

    /// The raw token.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for SegmentId {
    fn from(id: &str) -> Self {
        SegmentId(id.to_string())
    }
}

impl fmt::Display for SegmentId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Reader projection reference id (`rN`), assigned in construction order.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct ReferenceId(String);

impl ReferenceId {
    /// Builds a reference id from a raw token.
    pub fn new(id: impl Into<String>) -> Self {
        ReferenceId(id.into())
    }

    /// The raw token.
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl From<&str> for ReferenceId {
    fn from(id: &str) -> Self {
        ReferenceId(id.to_string())
    }
}

impl fmt::Display for ReferenceId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

// -------------------------------------------------------------- view flags #

/// Per-view flags. `empty` follows the record model, not the substrate: a
/// primary view (`paragraph` / `residual`) is empty when it owns no segment; a
/// navigation view (`table` / `row` / `cell` / `note`) is empty when it has no
/// child views.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ViewFlags {
    pub empty: bool,
}

impl ViewFlags {
    /// Builds a flag set.
    pub const fn new(empty: bool) -> Self {
        ViewFlags { empty }
    }
}

// --------------------------------------------------------- segment origin #

/// Origin of a projected segment.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SegmentOrigin {
    /// The segment names one substrate text fragment.
    SourceFragment,
    /// The segment is generated from a documented control; it has no source
    /// fragment and no source span.
    Derived(ReaderDerivedKind),
}

impl SegmentOrigin {
    /// Closed wire form used in diagnostics.
    pub fn as_str(self) -> &'static str {
        match self {
            SegmentOrigin::SourceFragment => "source_fragment",
            SegmentOrigin::Derived(ReaderDerivedKind::Tab) => "derived:tab",
            SegmentOrigin::Derived(ReaderDerivedKind::LineBreak) => "derived:line_break",
            SegmentOrigin::Derived(ReaderDerivedKind::PageBreak) => "derived:page_break",
        }
    }

    /// The derived control kind, when this is a derived origin.
    pub const fn derived_kind(self) -> Option<ReaderDerivedKind> {
        match self {
            SegmentOrigin::SourceFragment => None,
            SegmentOrigin::Derived(kind) => Some(kind),
        }
    }
}

// --------------------------------------------------------------- records #

/// One projected reader view.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectedView {
    pub id: ViewId,
    pub kind: ReaderViewKind,
    pub element_ref: ElementRef,
    pub parent_view: Option<ViewId>,
    pub children: Vec<ViewId>,
    pub segment_refs: Vec<SegmentId>,
    pub reference_refs: Vec<ReferenceId>,
    pub flags: ViewFlags,
}

/// One projected reader segment. A source-fragment segment carries a whole
/// fragment reference, slot and validated span; a derived segment carries a
/// generated literal and no fragment/span.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectedSegment {
    pub id: SegmentId,
    pub view: ViewId,
    pub ordinal: usize,
    pub segment_kind: ReaderSegmentKind,
    pub fragment_ref: Option<FragmentRef>,
    pub slot: Option<TextSlot>,
    pub span: Option<ReaderFragmentSpan>,
    pub output_start: usize,
    pub output_end: usize,
    pub chars: usize,
    pub origin: SegmentOrigin,
    pub semantic: ReaderSemantic,
    pub contextual: bool,
    pub element_ref: ElementRef,
    pub source_pos: usize,
    pub text: Option<String>,
}

/// One projected unresolved reference assigned to its ownership view.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectedReference {
    pub id: ReferenceId,
    pub view: ViewId,
    pub ordinal: usize,
    pub reference_type: ReaderReferenceType,
    pub element_ref: ElementRef,
    pub source_pos: usize,
    pub resolved: bool,
}

/// A reader projection: the view forest plus (in later tasks) ordered segments
/// and references. `content_hash` is an integrity/version pin, never an
/// authenticity or legal-completeness claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReaderProjection {
    pub views: Vec<ProjectedView>,
    pub segments: Vec<ProjectedSegment>,
    pub references: Vec<ProjectedReference>,
    pub content_hash: Option<String>,
}

impl ReaderProjection {
    /// The content seal, when one has been computed.
    pub fn content_hash(&self) -> Option<&str> {
        self.content_hash.as_deref()
    }

    /// Look up a view by id.
    pub fn view(&self, id: &ViewId) -> Option<&ProjectedView> {
        self.views.iter().find(|view| &view.id == id)
    }
}

// ----------------------------------------------------------------- errors #

/// Failure class of the reader projection build.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProjectionErrorKind {
    /// The substrate records are internally inconsistent.
    MalformedSubstrate,
    /// A view referenced by the projection has no record.
    MissingView,
    /// The same view key was produced twice.
    DuplicateView,
    /// A residual anchor is not reachable on the real parent chain.
    UnexpectedResidual,
    /// A fragment span failed validation.
    SpanInvalid,
    /// The coverage partition is not a total, duplicate-free function.
    PartitionIncomplete,
}

impl ProjectionErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            ProjectionErrorKind::MalformedSubstrate => "malformed_substrate",
            ProjectionErrorKind::MissingView => "missing_view",
            ProjectionErrorKind::DuplicateView => "duplicate_view",
            ProjectionErrorKind::UnexpectedResidual => "unexpected_residual",
            ProjectionErrorKind::SpanInvalid => "span_invalid",
            ProjectionErrorKind::PartitionIncomplete => "partition_incomplete",
        }
    }
}

impl fmt::Display for ProjectionErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed reader-projection error. Carries no serialization dependency.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectionError {
    kind: ProjectionErrorKind,
    detail: String,
}

impl ProjectionError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: ProjectionErrorKind, detail: impl Into<String>) -> Self {
        ProjectionError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> ProjectionErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for ProjectionError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for ProjectionError {}

impl From<ContractError> for ProjectionError {
    fn from(err: ContractError) -> Self {
        let kind = match err.kind() {
            ContractErrorKind::PartitionIncomplete => ProjectionErrorKind::PartitionIncomplete,
            _ => ProjectionErrorKind::MalformedSubstrate,
        };
        ProjectionError::new(kind, err.detail().to_string())
    }
}

// -------------------------------------------------------------------- build #

/// The reader view kind anchored by a structural element role, if any.
fn structural_view_kind(role: ReaderRole) -> Option<ReaderViewKind> {
    match role {
        ReaderRole::Paragraph => Some(ReaderViewKind::Paragraph),
        ReaderRole::Table => Some(ReaderViewKind::Table),
        ReaderRole::Row => Some(ReaderViewKind::Row),
        ReaderRole::Cell => Some(ReaderViewKind::Cell),
        ReaderRole::Note => Some(ReaderViewKind::Note),
        _ => None,
    }
}

/// Deterministic rank used to order views (and children) sharing a
/// `source_pos`. Only `paragraph` and `residual` can share an element, so the
/// rank makes that tie explicit: `paragraph` before `residual`.
fn view_kind_rank(kind: ReaderViewKind) -> u8 {
    match kind {
        ReaderViewKind::Paragraph => 0,
        ReaderViewKind::Residual => 1,
        ReaderViewKind::Table => 2,
        ReaderViewKind::Row => 3,
        ReaderViewKind::Cell => 4,
        ReaderViewKind::Note => 5,
    }
}

struct ViewSeed {
    kind: ReaderViewKind,
    element_ref: ElementRef,
    source_pos: usize,
}

fn role_of(index: &ReaderRecordIndex, id: &str) -> Result<ReaderRole, ProjectionError> {
    index.role_of(id).ok_or_else(|| {
        ProjectionError::new(
            ProjectionErrorKind::MalformedSubstrate,
            format!("element {id} has no role in the substrate index"),
        )
    })
}

fn add_seed(
    seeds: &mut Vec<ViewSeed>,
    seen: &mut HashSet<(ReaderViewKind, String)>,
    index: &ReaderRecordIndex,
    kind: ReaderViewKind,
    eid: &str,
) -> Result<(), ProjectionError> {
    let source_pos = index.source_pos(eid).ok_or_else(|| {
        ProjectionError::new(
            ProjectionErrorKind::MissingView,
            format!("view element {eid} is missing from the substrate index"),
        )
    })?;
    if seen.insert((kind, eid.to_string())) {
        seeds.push(ViewSeed {
            kind,
            element_ref: ElementRef::new(eid),
            source_pos,
        });
    }
    Ok(())
}

/// Nearest ancestor whose role is one of `allowed`, walked on the real `parent`
/// chain (starting from the element's parent, never itself).
fn nearest_container(
    index: &ReaderRecordIndex,
    element_ref: &ElementRef,
    allowed: &[ReaderRole],
) -> Result<Option<ElementRef>, ProjectionError> {
    let mut current = index
        .element(element_ref.as_str())
        .and_then(|element| element.parent.clone());
    while let Some(parent_id) = current {
        let role = role_of(index, &parent_id)?;
        if allowed.contains(&role) {
            return Ok(Some(ElementRef::new(parent_id)));
        }
        current = index
            .element(&parent_id)
            .and_then(|element| element.parent.clone());
    }
    Ok(None)
}

/// Parent container roles for a view kind. `paragraph`, `residual`, `table` and
/// `note` attach to the nearest `cell` / `note`; `row` attaches to the nearest
/// `table`; `cell` attaches to the nearest `row`.
fn parent_roles(kind: ReaderViewKind) -> &'static [ReaderRole] {
    match kind {
        ReaderViewKind::Paragraph
        | ReaderViewKind::Residual
        | ReaderViewKind::Table
        | ReaderViewKind::Note => &[ReaderRole::Cell, ReaderRole::Note],
        ReaderViewKind::Row => &[ReaderRole::Table],
        ReaderViewKind::Cell => &[ReaderRole::Row],
    }
}

/// Builds the reader view forest over the frozen substrate.
///
/// In T01 the `segments` and `references` vectors are empty and `content_hash`
/// is `None`; later tasks of the slice fill them. The view set is the union of:
///
/// 1. every element whose role is `paragraph` / `table` / `row` / `cell` /
///    `note`;
/// 2. every distinct residual anchor owned by a text record (via
///    `partition_primary_views`);
/// 3. every distinct residual anchor owned by a `control` / `note_reference` /
///    `field` / `unknown` / `foreign` element.
///
/// Views are ordered by `source_pos` (with a deterministic kind tie-break),
/// `parent_view` is the nearest valid container on the real parent chain, and
/// `children` are ordered by `source_pos`.
pub fn build_projection(records: &[Record]) -> Result<ReaderProjection, ProjectionError> {
    let index = ReaderRecordIndex::new(records)?;

    let mut seeds: Vec<ViewSeed> = Vec::new();
    let mut seen: HashSet<(ReaderViewKind, String)> = HashSet::new();

    // 1. Structural views.
    for element in index.elements() {
        let role = role_of(&index, &element.id)?;
        if let Some(kind) = structural_view_kind(role) {
            add_seed(&mut seeds, &mut seen, &index, kind, &element.id)?;
        }
    }

    // 2. Residual anchors from every text record.
    let partition = partition_primary_views(&index)?;
    for entry in &partition.entries {
        if entry.view.kind == ReaderViewKind::Residual {
            add_seed(
                &mut seeds,
                &mut seen,
                &index,
                ReaderViewKind::Residual,
                entry.view.element_ref.as_str(),
            )?;
        }
    }

    // 3. Residual anchors from control / reference elements.
    for element in index.elements() {
        let role = role_of(&index, &element.id)?;
        if matches!(
            role,
            ReaderRole::Control
                | ReaderRole::NoteReference
                | ReaderRole::Field
                | ReaderRole::Unknown
                | ReaderRole::Foreign
        ) {
            let key = view_key(&index, &ElementRef::new(element.id.as_str()))?;
            if key.kind == ReaderViewKind::Residual {
                add_seed(
                    &mut seeds,
                    &mut seen,
                    &index,
                    ReaderViewKind::Residual,
                    key.element_ref.as_str(),
                )?;
            }
        }
    }

    // Deterministic view order: source_pos, then kind rank, then element id.
    seeds.sort_by(|a, b| {
        a.source_pos
            .cmp(&b.source_pos)
            .then_with(|| view_kind_rank(a.kind).cmp(&view_kind_rank(b.kind)))
            .then_with(|| a.element_ref.as_str().cmp(b.element_ref.as_str()))
    });

    let mut views: Vec<ProjectedView> = Vec::with_capacity(seeds.len());
    let mut source_pos_of: Vec<usize> = Vec::with_capacity(seeds.len());
    let mut id_by_key: HashMap<(ReaderViewKind, String), ViewId> = HashMap::new();
    for (index_in_order, seed) in seeds.iter().enumerate() {
        let id = ViewId::new(format!("v{index_in_order}"));
        id_by_key.insert(
            (seed.kind, seed.element_ref.as_str().to_string()),
            id.clone(),
        );
        source_pos_of.push(seed.source_pos);
        views.push(ProjectedView {
            id,
            kind: seed.kind,
            element_ref: seed.element_ref.clone(),
            parent_view: None,
            children: Vec::new(),
            segment_refs: Vec::new(),
            reference_refs: Vec::new(),
            flags: ViewFlags::new(false),
        });
    }

    // Parent view: nearest valid container on the real parent chain.
    for view in &mut views {
        let allowed = parent_roles(view.kind);
        let container = nearest_container(&index, &view.element_ref, allowed)?;
        view.parent_view = match container {
            None => None,
            Some(element_ref) => {
                let role = role_of(&index, element_ref.as_str())?;
                let kind = structural_view_kind(role).ok_or_else(|| {
                    ProjectionError::new(
                        ProjectionErrorKind::MissingView,
                        format!("container {} has no view kind", element_ref.as_str()),
                    )
                })?;
                let key = (kind, element_ref.as_str().to_string());
                Some(id_by_key.get(&key).cloned().ok_or_else(|| {
                    ProjectionError::new(
                        ProjectionErrorKind::MissingView,
                        format!("parent view {} {} is missing", kind.as_str(), element_ref),
                    )
                })?)
            }
        };
    }

    // Children: reverse parent map, ordered by source_pos then kind rank.
    let pos_by_id: HashMap<ViewId, usize> = views
        .iter()
        .enumerate()
        .map(|(position, view)| (view.id.clone(), position))
        .collect();
    let mut child_positions: Vec<Vec<usize>> = vec![Vec::new(); views.len()];
    for (position, view) in views.iter().enumerate() {
        if let Some(parent) = &view.parent_view {
            let parent_position = pos_by_id.get(parent).copied().ok_or_else(|| {
                ProjectionError::new(
                    ProjectionErrorKind::MissingView,
                    format!("parent view {parent} is not in the projection"),
                )
            })?;
            child_positions[parent_position].push(position);
        }
    }
    for parent_position in 0..views.len() {
        child_positions[parent_position].sort_by(|left, right| {
            source_pos_of[*left]
                .cmp(&source_pos_of[*right])
                .then_with(|| {
                    view_kind_rank(views[*left].kind).cmp(&view_kind_rank(views[*right].kind))
                })
        });
        let child_ids: Vec<ViewId> = child_positions[parent_position]
            .iter()
            .map(|position| views[*position].id.clone())
            .collect();
        views[parent_position].children = child_ids;
    }

    // Flags: primary empty = owns no segment; navigation empty = no children.
    for view in &mut views {
        let empty = if view.kind.is_primary() {
            view.segment_refs.is_empty()
        } else {
            view.children.is_empty()
        };
        view.flags = ViewFlags::new(empty);
    }

    Ok(ReaderProjection {
        views,
        segments: Vec::new(),
        references: Vec::new(),
        content_hash: None,
    })
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::source_package::{capture, ElementRecord, Limits, TextRecord};
    use std::collections::BTreeMap;

    const NS: &str = "{http://schemas.microsoft.com/office/word/2003/wordml}";

    fn wordml(local: &str) -> String {
        format!("{NS}{local}")
    }

    fn element(id: &str, parent: Option<&str>, local: &str) -> Record {
        Record::Element(ElementRecord {
            kind: "element".into(),
            schema: "test".into(),
            id: id.into(),
            parent: parent.map(str::to_string),
            child_index: None,
            depth: 0,
            clark_tag: wordml(local),
            attrs: BTreeMap::new(),
            namespace_declarations: BTreeMap::new(),
            xml_space_declared: None,
            xml_space_effective: false,
            text_ref: None,
            tail_ref: None,
        })
    }

    fn text(id: &str, owner: &str, slot: TextSlot, value: &str) -> Record {
        Record::Text(TextRecord {
            kind: "text".into(),
            schema: "test".into(),
            id: id.into(),
            owner: owner.into(),
            slot,
            value: value.into(),
            chars: value.chars().count() as u64,
            bytes: value.len() as u64,
        })
    }

    //   e0 wordDocument
    //     e1 body
    //       e2 p (paragraph)
    //         e3 r
    //           e4 t "Alpha"   (t0)
    //       e5 tbl
    //         e6 tr
    //           e7 tc
    //             e8 p (paragraph inside cell)
    //               e9 r
    //                 e10 t "Beta"  (t1)
    //             e11 r (sibling residual anchor in the cell)
    //               e12 t "Tail"  (t2)
    fn synthetic() -> Vec<Record> {
        vec![
            element("e0", None, "wordDocument"),
            element("e1", Some("e0"), "body"),
            element("e2", Some("e1"), "p"),
            element("e3", Some("e2"), "r"),
            element("e4", Some("e3"), "t"),
            text("t0", "e4", TextSlot::Text, "Alpha"),
            element("e5", Some("e1"), "tbl"),
            element("e6", Some("e5"), "tr"),
            element("e7", Some("e6"), "tc"),
            element("e8", Some("e7"), "p"),
            element("e9", Some("e8"), "r"),
            element("e10", Some("e9"), "t"),
            text("t1", "e10", TextSlot::Text, "Beta"),
            element("e11", Some("e7"), "r"),
            element("e12", Some("e11"), "t"),
            text("t2", "e12", TextSlot::Text, "Tail"),
        ]
    }

    fn view<'a>(
        projection: &'a ReaderProjection,
        kind: ReaderViewKind,
        element_ref: &str,
    ) -> &'a ProjectedView {
        projection
            .views
            .iter()
            .find(|view| view.kind == kind && view.element_ref.as_str() == element_ref)
            .unwrap_or_else(|| panic!("view {kind:?} {element_ref} missing"))
    }

    #[test]
    fn synthetic_view_set_parents_children_and_order() {
        let projection = build_projection(&synthetic()).expect("projection must build");

        let actual: Vec<(ReaderViewKind, &str)> = projection
            .views
            .iter()
            .map(|view| (view.kind, view.element_ref.as_str()))
            .collect();
        let expected = [
            (ReaderViewKind::Paragraph, "e2"),
            (ReaderViewKind::Table, "e5"),
            (ReaderViewKind::Row, "e6"),
            (ReaderViewKind::Cell, "e7"),
            (ReaderViewKind::Paragraph, "e8"),
            (ReaderViewKind::Residual, "e11"),
        ];
        assert_eq!(actual, expected);

        for (position, view) in projection.views.iter().enumerate() {
            assert_eq!(view.id.as_str(), format!("v{position}"));
        }

        // parent_view = nearest valid container on the real parent chain.
        assert_eq!(
            view(&projection, ReaderViewKind::Paragraph, "e2").parent_view,
            None
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Table, "e5").parent_view,
            None
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Row, "e6").parent_view,
            Some(ViewId::from("v1"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Cell, "e7").parent_view,
            Some(ViewId::from("v2"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Paragraph, "e8").parent_view,
            Some(ViewId::from("v3"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Residual, "e11").parent_view,
            Some(ViewId::from("v3"))
        );

        // children are ordered by source_pos.
        assert_eq!(
            view(&projection, ReaderViewKind::Table, "e5").children,
            vec![ViewId::from("v2")]
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Row, "e6").children,
            vec![ViewId::from("v3")]
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Cell, "e7").children,
            vec![ViewId::from("v4"), ViewId::from("v5")]
        );
        assert!(view(&projection, ReaderViewKind::Paragraph, "e2")
            .children
            .is_empty());
        assert!(view(&projection, ReaderViewKind::Residual, "e11")
            .children
            .is_empty());

        // T01: only the forest is built.
        assert!(projection.segments.is_empty());
        assert!(projection.references.is_empty());
        assert_eq!(projection.content_hash(), None);

        // Primary views carry no segments yet; navigation views are non-empty
        // exactly when they have children.
        for view in &projection.views {
            if view.kind.is_primary() {
                assert!(view.flags.empty, "primary view {} must be empty", view.id);
            } else {
                assert_eq!(view.flags.empty, view.children.is_empty(), "{}", view.id);
            }
        }
    }

    #[test]
    fn fixture_view_forest_matches_handwritten_oracle() {
        const XML: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");
        let package = capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture");
        let projection = build_projection(package.records()).expect("projection must build");

        let actual: Vec<(ReaderViewKind, &str)> = projection
            .views
            .iter()
            .map(|view| (view.kind, view.element_ref.as_str()))
            .collect();
        let expected = [
            (ReaderViewKind::Residual, "e0"),
            (ReaderViewKind::Paragraph, "e2"),
            (ReaderViewKind::Paragraph, "e5"),
            (ReaderViewKind::Table, "e10"),
            (ReaderViewKind::Row, "e11"),
            (ReaderViewKind::Cell, "e12"),
            (ReaderViewKind::Paragraph, "e13"),
            (ReaderViewKind::Residual, "e13"),
            (ReaderViewKind::Residual, "e16"),
            (ReaderViewKind::Cell, "e18"),
            (ReaderViewKind::Paragraph, "e19"),
            (ReaderViewKind::Paragraph, "e24"),
            (ReaderViewKind::Paragraph, "e29"),
            (ReaderViewKind::Paragraph, "e38"),
            (ReaderViewKind::Note, "e42"),
            (ReaderViewKind::Paragraph, "e43"),
            (ReaderViewKind::Residual, "e46"),
        ];
        assert_eq!(actual, expected);
        assert_eq!(projection.views.len(), 17);
        for (position, view) in projection.views.iter().enumerate() {
            assert_eq!(view.id.as_str(), format!("v{position}"));
        }

        // e13 is both a paragraph view and a cell-level residual view; the
        // source_pos tie breaks paragraph before residual.
        assert_eq!(
            view(&projection, ReaderViewKind::Paragraph, "e13").parent_view,
            Some(ViewId::from("v5"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Residual, "e13").parent_view,
            Some(ViewId::from("v5"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Residual, "e16").parent_view,
            Some(ViewId::from("v5"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Row, "e11").parent_view,
            Some(ViewId::from("v3"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Cell, "e12").parent_view,
            Some(ViewId::from("v4"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Cell, "e18").parent_view,
            Some(ViewId::from("v4"))
        );
        // A footnote is a navigation view at the document root; its paragraph
        // and the trailing note reference residual attach to it.
        assert_eq!(
            view(&projection, ReaderViewKind::Note, "e42").parent_view,
            None
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Paragraph, "e43").parent_view,
            Some(ViewId::from("v14"))
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Residual, "e46").parent_view,
            Some(ViewId::from("v14"))
        );

        // Cell children in document order, with the paragraph/residual tie.
        let cell_children: Vec<&str> = view(&projection, ReaderViewKind::Cell, "e12")
            .children
            .iter()
            .map(|id| {
                projection
                    .view(id)
                    .expect("child view")
                    .element_ref
                    .as_str()
            })
            .collect();
        assert_eq!(cell_children, ["e13", "e13", "e16"]);
        assert_eq!(
            view(&projection, ReaderViewKind::Cell, "e18").children,
            vec![ViewId::from("v10")]
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Row, "e11").children,
            vec![ViewId::from("v5"), ViewId::from("v9")]
        );
        assert_eq!(
            view(&projection, ReaderViewKind::Note, "e42").children,
            vec![ViewId::from("v15"), ViewId::from("v16")]
        );
    }

    #[test]
    fn view_order_is_deterministic() {
        let records = synthetic();
        let first = build_projection(&records).expect("projection must build");
        let second = build_projection(&records).expect("projection must build");
        assert_eq!(first, second);
    }

    #[test]
    fn malformed_substrate_fails_closed() {
        let mut duplicate = synthetic();
        duplicate.push(element("e0", Some("e1"), "p"));
        assert_eq!(
            build_projection(&duplicate).unwrap_err().kind(),
            ProjectionErrorKind::MalformedSubstrate
        );

        let mut orphan = synthetic();
        orphan.push(element("e99", Some("e404"), "p"));
        assert_eq!(
            build_projection(&orphan).unwrap_err().kind(),
            ProjectionErrorKind::MalformedSubstrate
        );

        let mut bad_owner = synthetic();
        bad_owner.push(text("t404", "e404", TextSlot::Text, "x"));
        assert_eq!(
            build_projection(&bad_owner).unwrap_err().kind(),
            ProjectionErrorKind::MalformedSubstrate
        );
    }

    #[test]
    fn projection_error_display_is_stable() {
        let err = ProjectionError::new(ProjectionErrorKind::MissingView, "v9");
        assert_eq!(err.to_string(), "missing_view: v9");
        let converted: ProjectionError =
            ContractError::new(ContractErrorKind::PartitionIncomplete, "coverage").into();
        assert_eq!(converted.kind(), ProjectionErrorKind::PartitionIncomplete);
    }

    #[test]
    fn module_declares_no_serialization_dependency() {
        // Needles are assembled at runtime so this test's own source text does
        // not trivially satisfy `contains`.
        let source = include_str!("reader_projection.rs");
        for line in source.lines() {
            let trimmed = line.trim_start();
            if trimmed.starts_with("use ") || trimmed.starts_with("pub use ") {
                assert!(
                    !trimmed.contains("serde"),
                    "reader projection must stay serialization-agnostic: {trimmed}"
                );
            }
        }
        let needles = [
            format!("{} {}", "use", "serde"),
            format!("{}::", "serde"),
            format!("{}_json", "serde"),
            format!("{} crate serde", "extern"),
        ];
        for needle in needles {
            assert!(
                !source.contains(needle.as_str()),
                "reader projection must not reference {needle}"
            );
        }
    }
}
