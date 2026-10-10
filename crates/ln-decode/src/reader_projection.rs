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
use std::fmt::{self, Write};

use sha2::{Digest, Sha256};

use crate::reader_contract::{
    ContractError, ContractErrorKind, ElementRef, FragmentRef, ReaderDerivedKind,
    ReaderFragmentSpan, ReaderRecordIndex, ReaderReferenceType, ReaderRole, ReaderSegmentKind,
    ReaderSemantic, ReaderViewKey, ReaderViewKind, check_fragment_span, control_derived_kind,
    partition_primary_views, reference_type_of, tail_view_key, view_key, whole_fragment_span,
};
use crate::source_package::{ElementRecord, Record, TextSlot};

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

    /// Recomputes the content seal over the canonical representation bytes.
    ///
    /// The seal is an integrity/version pin, never an authenticity claim: it is
    /// computed over the record stream only, so it never feeds back into its own
    /// input and `reseal()` is idempotent. It is not a legal-completeness claim.
    pub fn reseal(&mut self) {
        let digest = Sha256::digest(canonical_projection_bytes(self).as_bytes());
        self.content_hash = Some(hex_lower(&digest));
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

// --------------------------------------------------------- document events #

/// A single ordered projection event reconstructed from the substrate records
/// (never re-parsed from XML). Fragments come from `text_ref` / `tail_ref`;
/// controls and references come from the element roles. [`document_events`]
/// emits them in document order.
#[derive(Debug, Clone, PartialEq, Eq)]
enum ProjectionEvent {
    Fragment {
        fragment_id: String,
        slot: TextSlot,
        owner: String,
        view: ReaderViewKey,
    },
    Control {
        element: String,
        kind: ReaderDerivedKind,
        view: ReaderViewKey,
    },
    Reference {
        element: String,
        reference_type: ReaderReferenceType,
        view: ReaderViewKey,
    },
}

impl ProjectionEvent {
    /// The ownership view of the event.
    fn view_key(&self) -> &ReaderViewKey {
        match self {
            ProjectionEvent::Fragment { view, .. }
            | ProjectionEvent::Control { view, .. }
            | ProjectionEvent::Reference { view, .. } => view,
        }
    }
}

/// Clark namespace of a tag (`{ns}local`), or `None` for an unbound name.
/// Mirrors the private helper in `reader_contract`; duplicated here so the
/// frozen S02 surface does not need to change.
fn clark_namespace(clark_tag: &str) -> Option<&str> {
    let rest = clark_tag.strip_prefix('{')?;
    let close = rest.find('}')?;
    Some(&rest[..close])
}

/// True when `element_id` is a maximal `unknown` / `foreign` subtree root (a
/// namespace or role boundary): its parent is absent, is not unknown/foreign, or
/// lives in a different namespace. Nested unknown/foreign elements inside the
/// same subtree are covered by the boundary root and are not emitted again.
fn unknown_or_foreign_boundary(
    index: &ReaderRecordIndex,
    element_id: &str,
) -> Result<bool, ProjectionError> {
    let element = index.element(element_id).ok_or_else(|| {
        ProjectionError::new(
            ProjectionErrorKind::MissingView,
            format!("element {element_id} is missing from the substrate index"),
        )
    })?;
    let Some(parent_id) = &element.parent else {
        return Ok(true);
    };
    let parent = index.element(parent_id).ok_or_else(|| {
        ProjectionError::new(
            ProjectionErrorKind::MissingView,
            format!("element {parent_id} is missing from the substrate index"),
        )
    })?;
    if !matches!(
        role_of(index, parent_id)?,
        ReaderRole::Unknown | ReaderRole::Foreign
    ) {
        return Ok(true);
    }
    Ok(clark_namespace(&parent.clark_tag) != clark_namespace(&element.clark_tag))
}

/// True when `element_id` or any real ancestor has `role`.
fn ancestor_has_role(
    index: &ReaderRecordIndex,
    element_id: &str,
    role: ReaderRole,
) -> Result<bool, ProjectionError> {
    let mut current = element_id.to_string();
    loop {
        if role_of(index, &current)? == role {
            return Ok(true);
        }
        match index
            .element(&current)
            .and_then(|element| element.parent.clone())
        {
            Some(parent) => current = parent,
            None => return Ok(false),
        }
    }
}

/// Closed semantic for a source fragment: field, revision, whitespace, then body.
/// A tail belongs to the parent's content, not its closed capture owner's role.
fn text_semantic(
    index: &ReaderRecordIndex,
    owner: &str,
    slot: TextSlot,
    value: &str,
) -> Result<ReaderSemantic, ProjectionError> {
    let element = index.element(owner).ok_or_else(|| {
        ProjectionError::new(
            ProjectionErrorKind::MalformedSubstrate,
            format!("text owner {owner} is missing"),
        )
    })?;
    let context = match slot {
        TextSlot::Text => Some(owner),
        TextSlot::Tail => element.parent.as_deref(),
    };
    if let Some(owner) = context {
        if ancestor_has_role(index, owner, ReaderRole::Field)? {
            return Ok(ReaderSemantic::FieldCode);
        }
        if ancestor_has_role(index, owner, ReaderRole::RevisionInsertion)? {
            return Ok(ReaderSemantic::RevisionInsertion);
        }
        if ancestor_has_role(index, owner, ReaderRole::RevisionDeletion)? {
            return Ok(ReaderSemantic::RevisionDeletion);
        }
    }
    if value.trim().is_empty() {
        return Ok(ReaderSemantic::Whitespace);
    }
    Ok(ReaderSemantic::Body)
}

/// Reconstructs the ordered document events from substrate records only.
///
/// The walk is the same pre-order capture uses: an element's own `text_ref`
/// first, then its control/reference event, then its children in document
/// order, each followed by that child's `tail_ref`. It never re-parses XML.
fn document_events(index: &ReaderRecordIndex) -> Result<Vec<ProjectionEvent>, ProjectionError> {
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

    let mut events: Vec<ProjectionEvent> = Vec::new();
    let mut stack: Vec<Step<'_>> = roots.iter().rev().map(|root| Step::Node(root)).collect();
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(element) => {
                let role = role_of(index, &element.id)?;
                if let Some(text_ref) = &element.text_ref {
                    events.push(ProjectionEvent::Fragment {
                        fragment_id: text_ref.clone(),
                        slot: TextSlot::Text,
                        owner: element.id.clone(),
                        view: view_key(index, &ElementRef::new(element.id.as_str()))?,
                    });
                }
                if role == ReaderRole::Control
                    && element.text_ref.is_none()
                    && let Some(kind) = control_derived_kind(&element.clark_tag, &element.attrs)
                {
                    events.push(ProjectionEvent::Control {
                        element: element.id.clone(),
                        kind,
                        view: view_key(index, &ElementRef::new(element.id.as_str()))?,
                    });
                }
                if matches!(
                    role,
                    ReaderRole::NoteReference
                        | ReaderRole::Field
                        | ReaderRole::Unknown
                        | ReaderRole::Foreign
                ) {
                    let is_boundary = match role {
                        ReaderRole::Unknown | ReaderRole::Foreign => {
                            unknown_or_foreign_boundary(index, &element.id)?
                        }
                        _ => true,
                    };
                    if is_boundary
                        && let Some(reference_type) =
                            reference_type_of(&element.clark_tag, &element.attrs)
                    {
                        events.push(ProjectionEvent::Reference {
                            element: element.id.clone(),
                            reference_type,
                            view: view_key(index, &ElementRef::new(element.id.as_str()))?,
                        });
                    }
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
                    events.push(ProjectionEvent::Fragment {
                        fragment_id: tail_ref.clone(),
                        slot: TextSlot::Tail,
                        owner: element.id.clone(),
                        view: tail_view_key(index, &ElementRef::new(element.id.as_str()))?,
                    });
                }
            }
        }
    }
    Ok(events)
}

/// Builds the reader projection over the frozen substrate: the view forest plus
/// the ordered source-fragment / derived segments and unresolved references.
/// `content_hash` stays `None` until the serialization task recomputes the seal.
///
/// The view set is the union of:
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
///
/// Segments and references are produced from the substrate document-event walk
/// (never an XML re-parse): every text record becomes exactly one source
/// segment with a re-validated whole-fragment span, a documented control
/// becomes a derived segment with no source span, and note/field/unknown/
/// foreign elements become unresolved references.
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

    // Group the ordered document events by owning view so each primary view can
    // be filled in event order.
    let mut events_per_view: Vec<Vec<ProjectionEvent>> = vec![Vec::new(); views.len()];
    for event in document_events(&index)? {
        let key = event.view_key();
        let view_id = id_by_key
            .get(&(key.kind, key.element_ref.as_str().to_string()))
            .ok_or_else(|| {
                ProjectionError::new(
                    ProjectionErrorKind::MissingView,
                    format!(
                        "event view {} {} is missing",
                        key.kind.as_str(),
                        key.element_ref
                    ),
                )
            })?;
        let position = pos_by_id.get(view_id).copied().ok_or_else(|| {
            ProjectionError::new(
                ProjectionErrorKind::MissingView,
                format!("event view {view_id} has no projection position"),
            )
        })?;
        events_per_view[position].push(event);
    }

    // Segments and references are built view-by-view in view order; within a
    // primary view they follow the document-event order. Ids (`sN` / `rN`) are
    // therefore assigned in construction order.
    let mut segments: Vec<ProjectedSegment> = Vec::new();
    let mut references: Vec<ProjectedReference> = Vec::new();
    for (position, view) in views.iter_mut().enumerate() {
        if !view.kind.is_primary() {
            continue;
        }
        let mut output_bytes: usize = 0;
        let mut segment_ordinal: usize = 0;
        let mut reference_ordinal: usize = 0;
        for event in &events_per_view[position] {
            match event {
                ProjectionEvent::Fragment {
                    fragment_id,
                    slot,
                    owner,
                    ..
                } => {
                    let text = index.text(fragment_id).ok_or_else(|| {
                        ProjectionError::new(
                            ProjectionErrorKind::MissingView,
                            format!("fragment {fragment_id} is missing from the substrate"),
                        )
                    })?;
                    let fragment = FragmentRef::new(fragment_id.clone());
                    let span = whole_fragment_span(&fragment, &text.value);
                    if let Err(error) = check_fragment_span(&text.value, &span) {
                        return Err(ProjectionError::new(
                            ProjectionErrorKind::SpanInvalid,
                            error.detail().to_string(),
                        ));
                    }
                    let semantic = text_semantic(&index, owner, *slot, &text.value)?;
                    let source_pos = index.source_pos(owner).ok_or_else(|| {
                        ProjectionError::new(
                            ProjectionErrorKind::MissingView,
                            format!("text owner {owner} is missing"),
                        )
                    })?;
                    let id = SegmentId::new(format!("s{}", segments.len()));
                    let output_end = output_bytes + text.value.len();
                    segments.push(ProjectedSegment {
                        id: id.clone(),
                        view: view.id.clone(),
                        ordinal: segment_ordinal,
                        segment_kind: ReaderSegmentKind::Text,
                        fragment_ref: Some(fragment),
                        slot: Some(*slot),
                        span: Some(span),
                        output_start: output_bytes,
                        output_end,
                        chars: text.value.chars().count(),
                        origin: SegmentOrigin::SourceFragment,
                        semantic,
                        contextual: semantic != ReaderSemantic::Body,
                        element_ref: ElementRef::new(owner.clone()),
                        source_pos,
                        text: None,
                    });
                    view.segment_refs.push(id);
                    output_bytes = output_end;
                    segment_ordinal += 1;
                }
                ProjectionEvent::Control { element, kind, .. } => {
                    let literal = kind.literal();
                    let source_pos = index.source_pos(element).ok_or_else(|| {
                        ProjectionError::new(
                            ProjectionErrorKind::MissingView,
                            format!("control {element} is missing"),
                        )
                    })?;
                    let id = SegmentId::new(format!("s{}", segments.len()));
                    let output_end = output_bytes + literal.len();
                    segments.push(ProjectedSegment {
                        id: id.clone(),
                        view: view.id.clone(),
                        ordinal: segment_ordinal,
                        segment_kind: ReaderSegmentKind::Derived,
                        fragment_ref: None,
                        slot: None,
                        span: None,
                        output_start: output_bytes,
                        output_end,
                        chars: literal.chars().count(),
                        origin: SegmentOrigin::Derived(*kind),
                        semantic: ReaderSemantic::DerivedSeparator,
                        contextual: true,
                        element_ref: ElementRef::new(element.clone()),
                        source_pos,
                        text: Some(literal.to_string()),
                    });
                    view.segment_refs.push(id);
                    output_bytes = output_end;
                    segment_ordinal += 1;
                }
                ProjectionEvent::Reference {
                    element,
                    reference_type,
                    ..
                } => {
                    let source_pos = index.source_pos(element).ok_or_else(|| {
                        ProjectionError::new(
                            ProjectionErrorKind::MissingView,
                            format!("reference {element} is missing"),
                        )
                    })?;
                    let id = ReferenceId::new(format!("r{}", references.len()));
                    references.push(ProjectedReference {
                        id: id.clone(),
                        view: view.id.clone(),
                        ordinal: reference_ordinal,
                        reference_type: *reference_type,
                        element_ref: ElementRef::new(element.clone()),
                        source_pos,
                        resolved: false,
                    });
                    view.reference_refs.push(id);
                    reference_ordinal += 1;
                }
            }
        }
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

    // Coverage: every substrate text record must be referenced exactly once by a
    // source-fragment segment, so a substrate whose `text_ref` / `tail_ref`
    // disagree with the text ownership fails closed instead of losing content.
    let mut covered: HashSet<&str> = HashSet::new();
    let mut duplicate = false;
    for segment in &segments {
        if let Some(fragment) = &segment.fragment_ref
            && !covered.insert(fragment.as_str())
        {
            duplicate = true;
        }
    }
    if duplicate
        || covered.len() != index.texts().len()
        || index
            .texts()
            .iter()
            .any(|text| !covered.contains(text.id.as_str()))
    {
        return Err(ProjectionError::new(
            ProjectionErrorKind::PartitionIncomplete,
            format!(
                "coverage is not total and duplicate-free: {} covered of {} text record(s)",
                covered.len(),
                index.texts().len()
            ),
        ));
    }

    Ok(ReaderProjection {
        views,
        segments,
        references,
        content_hash: None,
    })
}

// --------------------------------------------------- canonical serialization #

/// Minimal canonical JSON value tree used only by the reader projection. It is
/// deliberately local: D633 keeps the writer inside `reader_projection.rs`
/// instead of widening the frozen `source_package` / `npa_wire` wire contracts.
/// The seam is additive — it does not touch the frozen S02 surface.
enum Json {
    Null,
    Bool(bool),
    Number(usize),
    Str(String),
    Arr(Vec<Json>),
    Obj(Vec<(&'static str, Json)>),
}

impl Json {
    fn string(value: impl Into<String>) -> Json {
        Json::Str(value.into())
    }

    fn unsigned(value: usize) -> Json {
        Json::Number(value)
    }

    fn array(items: Vec<Json>) -> Json {
        Json::Arr(items)
    }

    fn object(entries: Vec<(&'static str, Json)>) -> Json {
        Json::Obj(entries)
    }
}

fn push_indent(out: &mut String, depth: usize) {
    for _ in 0..depth {
        out.push_str("  ");
    }
}

/// Stable `ensure_ascii=False` escaping: quote, backslash, the short control
/// escapes and `\u00xx` for the remaining C0 controls; legal UTF-8 passes
/// through verbatim. Mirrors `npa_wire::write_json_string` and the
/// `source_package` canonical-JSON discipline.
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

/// Canonical renderer: ascending object keys at every level, 2-space indent,
/// one line per array element or object member, empty containers inline.
fn render_json(value: &Json, depth: usize, out: &mut String) {
    match value {
        Json::Null => out.push_str("null"),
        Json::Bool(flag) => out.push_str(if *flag { "true" } else { "false" }),
        Json::Number(number) => {
            let _ = write!(out, "{number}");
        }
        Json::Str(text) => write_json_string(text, out),
        Json::Arr(items) => {
            if items.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push_str("[\n");
            for (index, item) in items.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                push_indent(out, depth + 1);
                render_json(item, depth + 1, out);
            }
            out.push('\n');
            push_indent(out, depth);
            out.push(']');
        }
        Json::Obj(entries) => {
            let mut ordered: Vec<&(&'static str, Json)> = entries.iter().collect();
            ordered.sort_by(|left, right| left.0.cmp(right.0));
            if ordered.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push_str("{\n");
            for (index, (key, value)) in ordered.iter().enumerate() {
                if index > 0 {
                    out.push_str(",\n");
                }
                push_indent(out, depth + 1);
                write_json_string(key, out);
                out.push_str(": ");
                render_json(value, depth + 1, out);
            }
            out.push('\n');
            push_indent(out, depth);
            out.push('}');
        }
    }
}

fn span_json(span: &ReaderFragmentSpan) -> Json {
    Json::object(vec![
        ("end", Json::unsigned(span.end)),
        ("fragment", Json::string(span.fragment.as_str())),
        ("start", Json::unsigned(span.start)),
    ])
}

fn view_json(view: &ProjectedView) -> Json {
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
        ("kind", Json::string(view.kind.as_str())),
        (
            "parent_view",
            view.parent_view
                .as_ref()
                .map(|id| Json::string(id.as_str()))
                .unwrap_or(Json::Null),
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
        (
            "segment_refs",
            Json::array(
                view.segment_refs
                    .iter()
                    .map(|id| Json::string(id.as_str()))
                    .collect(),
            ),
        ),
    ])
}

fn segment_json(segment: &ProjectedSegment) -> Json {
    Json::object(vec![
        ("chars", Json::unsigned(segment.chars)),
        ("contextual", Json::Bool(segment.contextual)),
        ("element_ref", Json::string(segment.element_ref.as_str())),
        (
            "fragment_ref",
            segment
                .fragment_ref
                .as_ref()
                .map(|fragment| Json::string(fragment.as_str()))
                .unwrap_or(Json::Null),
        ),
        ("id", Json::string(segment.id.as_str())),
        ("ordinal", Json::unsigned(segment.ordinal)),
        ("origin", Json::string(segment.origin.as_str())),
        ("output_end", Json::unsigned(segment.output_end)),
        ("output_start", Json::unsigned(segment.output_start)),
        ("segment_kind", Json::string(segment.segment_kind.as_str())),
        ("semantic", Json::string(segment.semantic.as_str())),
        (
            "slot",
            segment
                .slot
                .map(|slot| Json::string(slot.as_str()))
                .unwrap_or(Json::Null),
        ),
        ("source_pos", Json::unsigned(segment.source_pos)),
        (
            "span",
            segment.span.as_ref().map(span_json).unwrap_or(Json::Null),
        ),
        (
            "text",
            segment
                .text
                .as_ref()
                .map(|text| Json::string(text.as_str()))
                .unwrap_or(Json::Null),
        ),
        ("view", Json::string(segment.view.as_str())),
    ])
}

fn reference_json(reference: &ProjectedReference) -> Json {
    Json::object(vec![
        ("element_ref", Json::string(reference.element_ref.as_str())),
        ("id", Json::string(reference.id.as_str())),
        ("ordinal", Json::unsigned(reference.ordinal)),
        (
            "reference_type",
            Json::string(reference.reference_type.as_str()),
        ),
        ("resolved", Json::Bool(reference.resolved)),
        ("source_pos", Json::unsigned(reference.source_pos)),
        ("view", Json::string(reference.view.as_str())),
    ])
}

/// Canonical, LF-terminated representation of the reader projection record
/// stream: one JSON record per `ProjectedView` / `ProjectedSegment` /
/// `ProjectedReference`, grouped under ascending root keys. Keys ascend at every
/// level, indentation is two spaces and escaping is stable, so two calls on equal
/// records produce identical bytes. The seal (`content_hash`) is deliberately
/// excluded; a full wire manifest/footer and metrics are S04.
pub fn canonical_projection_bytes(projection: &ReaderProjection) -> String {
    let root = Json::object(vec![
        (
            "references",
            Json::array(projection.references.iter().map(reference_json).collect()),
        ),
        (
            "segments",
            Json::array(projection.segments.iter().map(segment_json).collect()),
        ),
        (
            "views",
            Json::array(projection.views.iter().map(view_json).collect()),
        ),
    ]);
    let mut out = String::new();
    render_json(&root, 0, &mut out);
    out.push('\n');
    out
}

/// Lowercase hex digest, matching the `source_package` seal encoding: bare
/// 64-character lowercase hex. Never an authenticity claim and never a key.
fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::source_package::{Limits, TextRecord, capture};
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

    /// Links hand-built text records back to their owners exactly as `capture`
    /// does: `text` slots become `text_ref`, `tail` slots `tail_ref`. The real
    /// substrate always carries these links; a hand-built one must too, because
    /// the document-event walk reads them.
    fn link_texts(records: &mut [Record]) {
        let links: Vec<(String, TextSlot, String)> = records
            .iter()
            .filter_map(|record| match record {
                Record::Text(text) => Some((text.owner.clone(), text.slot, text.id.clone())),
                Record::Element(_) => None,
            })
            .collect();
        for record in records.iter_mut() {
            if let Record::Element(element) = record {
                for (owner, slot, id) in &links {
                    if &element.id == owner {
                        match slot {
                            TextSlot::Text => element.text_ref = Some(id.clone()),
                            TextSlot::Tail => element.tail_ref = Some(id.clone()),
                        }
                    }
                }
            }
        }
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
        let mut records = vec![
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
        ];
        link_texts(&mut records);
        records
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

    fn strings(values: &[&str]) -> Vec<String> {
        values.iter().map(|value| value.to_string()).collect()
    }

    fn segment_tokens(
        projection: &ReaderProjection,
        kind: ReaderViewKind,
        element_ref: &str,
    ) -> Vec<String> {
        view(projection, kind, element_ref)
            .segment_refs
            .iter()
            .map(|id| {
                let segment = projection
                    .segments
                    .iter()
                    .find(|segment| &segment.id == id)
                    .expect("segment ref must resolve");
                match segment.origin {
                    SegmentOrigin::SourceFragment => segment
                        .fragment_ref
                        .as_ref()
                        .expect("source segment carries a fragment")
                        .as_str()
                        .to_string(),
                    SegmentOrigin::Derived(kind) => format!("derived:{}", kind.as_str()),
                }
            })
            .collect()
    }

    fn reference_tokens(
        projection: &ReaderProjection,
        kind: ReaderViewKind,
        element_ref: &str,
    ) -> Vec<String> {
        view(projection, kind, element_ref)
            .reference_refs
            .iter()
            .map(|id| {
                projection
                    .references
                    .iter()
                    .find(|reference| &reference.id == id)
                    .expect("reference ref must resolve")
                    .reference_type
                    .as_str()
                    .to_string()
            })
            .collect()
    }

    fn source_segment<'a>(
        projection: &'a ReaderProjection,
        fragment: &str,
    ) -> &'a ProjectedSegment {
        projection
            .segments
            .iter()
            .find(|segment| {
                segment.fragment_ref.as_ref().map(FragmentRef::as_str) == Some(fragment)
            })
            .unwrap_or_else(|| panic!("fragment segment {fragment} missing"))
    }

    fn fixture_projection() -> ReaderProjection {
        const XML: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");
        let package = capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture");
        build_projection(package.records()).expect("projection must build")
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
        assert!(
            view(&projection, ReaderViewKind::Paragraph, "e2")
                .children
                .is_empty()
        );
        assert!(
            view(&projection, ReaderViewKind::Residual, "e11")
                .children
                .is_empty()
        );

        // T02: the synthetic tree carries three source fragments and no
        // references; the seal is still unset until the serialization task.
        assert_eq!(projection.segments.len(), 3);
        assert!(projection.references.is_empty());
        assert_eq!(projection.content_hash(), None);
        assert_eq!(
            segment_tokens(&projection, ReaderViewKind::Paragraph, "e2"),
            ["t0"]
        );
        assert_eq!(
            segment_tokens(&projection, ReaderViewKind::Paragraph, "e8"),
            ["t1"]
        );
        assert_eq!(
            segment_tokens(&projection, ReaderViewKind::Residual, "e11"),
            ["t2"]
        );

        // flags.empty is recomputed from the final segment/child content.
        for view in &projection.views {
            let expected_empty = if view.kind.is_primary() {
                view.segment_refs.is_empty()
            } else {
                view.children.is_empty()
            };
            assert_eq!(view.flags.empty, expected_empty, "{}", view.id);
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
    fn fixture_segments_and_references_match_handwritten_oracle() {
        let projection = fixture_projection();

        // Ordered per-view segment lists, hand-derived from the fixture XML
        // (`derived:<kind>` marks a rendered control).
        let segments: &[(ReaderViewKind, &str, &[&str])] = &[
            (ReaderViewKind::Paragraph, "e2", &["t0"]),
            (
                ReaderViewKind::Paragraph,
                "e5",
                &["t1", "derived:tab", "t2"],
            ),
            (ReaderViewKind::Paragraph, "e13", &["t3"]),
            (ReaderViewKind::Residual, "e13", &["t4"]),
            (ReaderViewKind::Residual, "e16", &["t5"]),
            (
                ReaderViewKind::Paragraph,
                "e19",
                &["derived:line_break", "derived:page_break", "t6"],
            ),
            (ReaderViewKind::Paragraph, "e24", &["t7", "t8"]),
            (ReaderViewKind::Paragraph, "e29", &["t9", "t10"]),
            (ReaderViewKind::Paragraph, "e38", &["t13"]),
            (ReaderViewKind::Paragraph, "e43", &["t14"]),
            (ReaderViewKind::Residual, "e46", &[]),
            (ReaderViewKind::Residual, "e0", &["t11", "t12"]),
        ];
        for (kind, element_ref, expected) in segments {
            assert_eq!(
                segment_tokens(&projection, *kind, element_ref),
                strings(expected),
                "segments for {kind:?} {element_ref}"
            );
        }

        // Ordered per-view reference lists.
        let references: &[(ReaderViewKind, &str, &[&str])] = &[
            (ReaderViewKind::Paragraph, "e5", &["field"]),
            (ReaderViewKind::Paragraph, "e24", &["field"]),
            (
                ReaderViewKind::Residual,
                "e0",
                &[
                    "unknown_wordml_element",
                    "foreign_element",
                    "note_reference",
                ],
            ),
            (ReaderViewKind::Residual, "e46", &["note_reference"]),
        ];
        for (kind, element_ref, expected) in references {
            assert_eq!(
                reference_tokens(&projection, *kind, element_ref),
                strings(expected),
                "references for {kind:?} {element_ref}"
            );
        }
        assert_eq!(projection.references.len(), 6);
        for reference in &projection.references {
            assert!(!reference.resolved, "{}", reference.id);
        }
    }

    #[test]
    fn fixture_fragment_semantics_follow_field_revision_and_whitespace() {
        let projection = fixture_projection();
        let cases: &[(&str, &str, TextSlot, ReaderSemantic, bool)] = &[
            ("t0", "e4", TextSlot::Text, ReaderSemantic::Body, false),
            ("t1", "e7", TextSlot::Text, ReaderSemantic::Body, false),
            ("t2", "e9", TextSlot::Text, ReaderSemantic::FieldCode, true),
            (
                "t4",
                "e13",
                TextSlot::Tail,
                ReaderSemantic::Whitespace,
                true,
            ),
            ("t7", "e27", TextSlot::Text, ReaderSemantic::FieldCode, true),
            ("t8", "e28", TextSlot::Text, ReaderSemantic::Body, false),
            (
                "t9",
                "e32",
                TextSlot::Text,
                ReaderSemantic::RevisionInsertion,
                true,
            ),
            (
                "t10",
                "e34",
                TextSlot::Text,
                ReaderSemantic::RevisionDeletion,
                true,
            ),
            ("t12", "e37", TextSlot::Text, ReaderSemantic::Body, false),
            ("t13", "e40", TextSlot::Text, ReaderSemantic::Body, false),
        ];
        for (fragment, owner, slot, semantic, contextual) in cases {
            let segment = source_segment(&projection, fragment);
            assert_eq!(&segment.element_ref.as_str(), owner, "{fragment}");
            assert_eq!(segment.slot, Some(*slot), "{fragment}");
            assert_eq!(segment.semantic, *semantic, "{fragment}");
            assert_eq!(segment.contextual, *contextual, "{fragment}");
        }
    }

    #[test]
    fn fixture_controls_render_as_derived_segments_without_spans() {
        let projection = fixture_projection();
        let derived: Vec<&ProjectedSegment> = projection
            .segments
            .iter()
            .filter(|segment| segment.segment_kind == ReaderSegmentKind::Derived)
            .collect();
        assert_eq!(derived.len(), 3);
        for segment in &derived {
            assert!(segment.fragment_ref.is_none());
            assert!(segment.slot.is_none());
            assert!(segment.span.is_none());
            assert_eq!(segment.semantic, ReaderSemantic::DerivedSeparator);
            assert!(segment.contextual);
            let kind = segment.origin.derived_kind().expect("derived origin");
            assert_eq!(segment.text.as_deref(), Some(kind.literal()));
            assert_eq!(segment.chars, kind.literal().chars().count());
        }
        let literals: Vec<&str> = derived
            .iter()
            .map(|segment| segment.text.as_deref().expect("derived literal"))
            .collect();
        assert!(literals.contains(&"\t"));
        assert_eq!(
            literals.iter().filter(|literal| **literal == "\n").count(),
            2
        );
    }

    #[test]
    fn fixture_coverage_is_total_duplicate_free_and_span_valid() {
        const XML: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");
        let package = capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture");
        let records = package.records();
        let projection = build_projection(records).expect("projection must build");

        let mut fragments: Vec<String> = projection
            .segments
            .iter()
            .filter_map(|segment| {
                segment
                    .fragment_ref
                    .as_ref()
                    .map(|f| f.as_str().to_string())
            })
            .collect();
        fragments.sort_unstable();
        let mut expected: Vec<String> = (0..15).map(|index| format!("t{index}")).collect();
        expected.sort_unstable();
        assert_eq!(fragments, expected);

        for segment in &projection.segments {
            let Some(fragment) = &segment.fragment_ref else {
                continue;
            };
            let value = records
                .iter()
                .find_map(|record| match record {
                    Record::Text(text) if text.id == fragment.as_str() => Some(text.value.as_str()),
                    _ => None,
                })
                .expect("fragment must name a substrate text record");
            let span = segment.span.as_ref().expect("text segment carries a span");
            assert_eq!(span.start, 0);
            assert_eq!(span.end, value.len());
            assert!(check_fragment_span(value, span).is_ok());
            assert_eq!(segment.chars, value.chars().count());
            assert_eq!(segment.output_end - segment.output_start, value.len());
        }

        // Per-view output offsets are contiguous from zero.
        for view in &projection.views {
            if !view.kind.is_primary() {
                continue;
            }
            let mut cursor = 0usize;
            for id in &view.segment_refs {
                let segment = projection
                    .segments
                    .iter()
                    .find(|segment| &segment.id == id)
                    .expect("segment ref must resolve");
                assert_eq!(segment.output_start, cursor, "{}", segment.id);
                cursor = segment.output_end;
            }
            // Navigation views never own a segment or a reference.
        }
        for view in &projection.views {
            if view.kind.is_navigation() {
                assert!(view.segment_refs.is_empty(), "{}", view.id);
                assert!(view.reference_refs.is_empty(), "{}", view.id);
            }
        }
    }

    #[test]
    fn empty_fragment_fails_closed_with_span_invalid() {
        // `capture` never emits an empty text record; a hand-built one must fail
        // closed at the mandatory whole-fragment span re-validation.
        let mut records = vec![
            element("e0", None, "wordDocument"),
            element("e1", Some("e0"), "p"),
            element("e2", Some("e1"), "t"),
            text("t0", "e2", TextSlot::Text, ""),
        ];
        link_texts(&mut records);
        let error = build_projection(&records).unwrap_err();
        assert_eq!(error.kind(), ProjectionErrorKind::SpanInvalid);
    }

    #[test]
    fn unlinked_text_fails_closed_with_partition_incomplete() {
        // A text record whose owner exists but is not linked through the
        // element's `text_ref` is a substrate inconsistency: the ownership map
        // and the document-event walk disagree, so coverage fails closed.
        let records = vec![
            element("e0", None, "wordDocument"),
            element("e1", Some("e0"), "p"),
            element("e2", Some("e1"), "t"),
            text("t0", "e2", TextSlot::Text, "Alpha"),
        ];
        let error = build_projection(&records).unwrap_err();
        assert_eq!(error.kind(), ProjectionErrorKind::PartitionIncomplete);
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

    #[test]
    fn canonical_bytes_are_deterministic_and_lf_terminated() {
        let projection = fixture_projection();
        let first = canonical_projection_bytes(&projection);
        let second = canonical_projection_bytes(&projection);
        assert_eq!(first, second);
        assert!(first.ends_with('\n'));
        assert!(!first.contains('\r'));

        // Root keys ascend: references < segments < views.
        let references = first.find("\"references\"").expect("references key");
        let segments = first.find("\"segments\"").expect("segments key");
        let views = first.find("\"views\"").expect("views key");
        assert!(references < segments && segments < views);

        // Derived controls serialize through their closed origin token and the
        // escaping is stable: no raw TAB byte ever reaches the stream.
        assert!(first.contains("\"origin\": \"derived:tab\""));
        assert!(!first.contains('\t'));
    }

    #[test]
    fn canonical_bytes_escape_unicode_and_controls() {
        let mut out = String::new();
        write_json_string("Право \"x\"\\\n\t\r\u{1}", &mut out);
        assert_eq!(out, "\"Право \\\"x\\\"\\\\\\n\\t\\r\\u0001\"");
        // Legal UTF-8 passes through verbatim (`ensure_ascii=False`).
        assert!(out.contains("Право"));
    }

    #[test]
    fn canonical_bytes_exclude_the_seal() {
        let mut projection = fixture_projection();
        let before = canonical_projection_bytes(&projection);
        projection.reseal();
        let after = canonical_projection_bytes(&projection);
        assert_eq!(
            before, after,
            "the seal must never feed back into its input"
        );
        assert!(projection.content_hash().is_some());
    }

    #[test]
    fn reseal_is_stable_and_recomputable() {
        let mut projection = fixture_projection();
        projection.reseal();
        let first = projection.content_hash().expect("sealed").to_string();
        assert_eq!(first.len(), 64);
        assert!(first.chars().all(|c| c.is_ascii_hexdigit()));
        assert_eq!(first, first.to_ascii_lowercase());

        // Clearing and recomputing yields the same digest (idempotent).
        projection.content_hash = None;
        projection.reseal();
        assert_eq!(projection.content_hash(), Some(first.as_str()));

        let mut hasher = Sha256::new();
        hasher.update(canonical_projection_bytes(&projection).as_bytes());
        assert_eq!(
            projection.content_hash().unwrap(),
            hex_lower(&hasher.finalize())
        );
    }

    #[test]
    fn seal_changes_when_a_record_changes() {
        let mut projection = fixture_projection();
        projection.reseal();
        let original = projection.content_hash().expect("sealed").to_string();

        let mut mutated = projection.clone();
        mutated.segments[0].chars += 1;
        mutated.reseal();
        assert_ne!(mutated.content_hash().unwrap(), original);
    }
}
