//! S06 reader navigation index over the frozen reader projection.
//!
//! This module is the navigation half of
//! `prd/architecture/intermediate-source-navigation-contract.md` (design pin
//! D736). It builds a read-only document-structure and navigation index over
//! three already-verified inputs: the S03 reader projection
//! (`crate::reader_projection`), the S04 reading-order index
//! (`crate::reader_reading_order`) and the S02 substrate records
//! (`crate::source_package`). It never calls
//! `crate::reader_projection::build_projection` and never re-parses XML.
//!
//! The index exposes three non-overlapping address spaces (`View` / `Segment` /
//! `Reference`), typed `Contains` / `Owns` / `Precedes` links, the structural
//! parent / children / siblings surfaces, a bounded root-first `path_to_root`,
//! reading-order neighbours taken from the substrate event walk, and element /
//! fragment anchor indexes. Every failure is fail-closed with a typed
//! [`NavErrorKind`]; error details carry ids and coordinates only, never decoded
//! text.
//!
//! Non-claims: not an R1000 closure artifact, not semantic or legal, not
//! temporal, not physical pagination, not an XML re-parse, not a clean view.
//! The module carries no serialization dependency and no JSON crate.

use std::collections::{BTreeMap, HashMap, HashSet};
use std::fmt;

use crate::reader_clean_view::CleanView;
use crate::reader_contract::{
    ElementRef, FragmentRef, ReaderFragmentSpan, ReaderRecordIndex, ReaderReferenceType,
    ReaderRole, ReaderSegmentKind, ReaderSemantic, ReaderViewKey, ReaderViewKind,
    control_derived_kind, tail_view_key, view_key,
};
use crate::reader_projection::{
    ProjectedReference, ReaderProjection, ReferenceId, SegmentId, SegmentOrigin, ViewId,
};
use crate::reader_reading_order::ReadingOrderIndex;
use crate::source_package::{ElementRecord, Record, TextSlot};

// ------------------------------------------------------------------- ids #

/// A navigation address: one of three non-overlapping id spaces.
///
/// `View(ViewId)` is a `vN` reader-projection view, `Segment(SegmentId)` a `sN`
/// projected segment and `Reference(ReferenceId)` an `rN` projected reference.
/// The three spaces are disjoint by construction; an address that names an
/// absent record is refused with a typed [`NavErrorKind::MissingAnchorView`],
/// [`NavErrorKind::MissingAnchorSegment`] or
/// [`NavErrorKind::MissingAnchorReference`], never defaulted.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum NodeAddress {
    /// A reader-projection view (`vN`).
    View(ViewId),
    /// A projected segment (`sN`).
    Segment(SegmentId),
    /// A projected reference (`rN`).
    Reference(ReferenceId),
}

impl NodeAddress {
    /// The raw id token of the address, without its variant.
    pub fn id_token(&self) -> &str {
        match self {
            NodeAddress::View(id) => id.as_str(),
            NodeAddress::Segment(id) => id.as_str(),
            NodeAddress::Reference(id) => id.as_str(),
        }
    }

    /// The address variant as a [`NavNodeKind`].
    pub fn kind(&self) -> NavNodeKind {
        match self {
            NodeAddress::View(_) => NavNodeKind::View,
            NodeAddress::Segment(_) => NavNodeKind::Segment,
            NodeAddress::Reference(_) => NavNodeKind::Reference,
        }
    }

    /// The view id when the address is a view.
    pub fn as_view(&self) -> Option<&ViewId> {
        match self {
            NodeAddress::View(id) => Some(id),
            _ => None,
        }
    }
}

impl fmt::Display for NodeAddress {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            NodeAddress::View(id) => write!(f, "view {id}"),
            NodeAddress::Segment(id) => write!(f, "segment {id}"),
            NodeAddress::Reference(id) => write!(f, "reference {id}"),
        }
    }
}

// ----------------------------------------------------------------- kinds #

/// The closed navigation node kind, mirroring the [`NodeAddress`] variant.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavNodeKind {
    /// A reader-projection view.
    View,
    /// A projected segment.
    Segment,
    /// A projected reference.
    Reference,
}

impl NavNodeKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavNodeKind::View => "view",
            NavNodeKind::Segment => "segment",
            NavNodeKind::Reference => "reference",
        }
    }
}

impl fmt::Display for NavNodeKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// The variant-specific, read-only payload of a navigation node.
///
/// A `View` body distinguishes a primary view (owns text segments) from a
/// navigation view (carries no text) through `primary`. A `Segment` body carries
/// the §5 provenance of the segment; a derived segment carries no `fragment_ref`
/// and no `span` and a consumer must not invent one. A `Reference` body stays
/// unresolved: S06 adds no resolution flag to the projection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NavNodeBody {
    /// A view node.
    View {
        /// Closed reader view vocabulary.
        view_kind: ReaderViewKind,
        /// Anchoring substrate element.
        element_ref: ElementRef,
        /// Nearest valid container view, or `None` for a root view.
        parent_view: Option<ViewId>,
        /// True when the view owns text segments (`paragraph` / `residual`).
        primary: bool,
    },
    /// A segment node.
    Segment {
        /// Owning view.
        view: ViewId,
        /// Closed segment kind.
        segment_kind: ReaderSegmentKind,
        /// Segment origin (source fragment or a documented control).
        origin: SegmentOrigin,
        /// Source fragment, absent for a derived segment.
        fragment_ref: Option<FragmentRef>,
        /// Source text slot, absent for a derived segment.
        slot: Option<TextSlot>,
        /// Validated decoded span, absent for a derived segment.
        span: Option<ReaderFragmentSpan>,
        /// Closed semantic label.
        semantic: ReaderSemantic,
        /// Anchoring substrate element.
        element_ref: ElementRef,
    },
    /// A reference node.
    Reference {
        /// Owning view.
        view: ViewId,
        /// Closed reference type.
        reference_type: ReaderReferenceType,
        /// Anchoring substrate element.
        element_ref: ElementRef,
    },
}

impl NavNodeBody {
    /// The owning view of the node the body belongs to.
    pub fn owning_view(&self) -> &ViewId {
        match self {
            NavNodeBody::View { .. } => unreachable!("a view body owns itself"),
            NavNodeBody::Segment { view, .. } | NavNodeBody::Reference { view, .. } => view,
        }
    }

    /// The anchoring substrate element.
    pub fn element_ref(&self) -> &ElementRef {
        match self {
            NavNodeBody::View { element_ref, .. }
            | NavNodeBody::Segment { element_ref, .. }
            | NavNodeBody::Reference { element_ref, .. } => element_ref,
        }
    }

    /// The source fragment when the node is a source-fragment segment.
    pub fn fragment_ref(&self) -> Option<&FragmentRef> {
        match self {
            NavNodeBody::Segment { fragment_ref, .. } => fragment_ref.as_ref(),
            _ => None,
        }
    }
}

/// One navigation node: an address, its kind, its body and the owner element
/// pre-order index (`source_pos`) used for source ordering.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavNode {
    /// The node address.
    pub address: NodeAddress,
    /// The node kind.
    pub kind: NavNodeKind,
    /// The variant-specific payload.
    pub body: NavNodeBody,
    /// Owner element pre-order index (ordering fact).
    pub source_pos: usize,
}

// ----------------------------------------------------------------- links #

/// The closed navigation link kind.
///
/// `Contains` and `Owns` and `Precedes` are built by [`build_navigation`];
/// `ResolvesTo` is added by the reference-resolution task (S06/T03) together
/// with the closed resolution-reason vocabulary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavLinkKind {
    /// Structural parent view → child view, from `parent_view` / `children`.
    Contains,
    /// View ownership of its segments / references.
    Owns,
    /// Source-order successor among siblings in the same parent.
    Precedes,
    /// A resolvable reference to exactly one note view (S06/T03).
    ResolvesTo,
}

impl NavLinkKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavLinkKind::Contains => "contains",
            NavLinkKind::Owns => "owns",
            NavLinkKind::Precedes => "precedes",
            NavLinkKind::ResolvesTo => "resolves_to",
        }
    }
}

impl fmt::Display for NavLinkKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// A directed, typed navigation edge between two addresses.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavLink {
    /// Source address.
    pub from: NodeAddress,
    /// Target address.
    pub to: NodeAddress,
    /// Edge kind.
    pub kind: NavLinkKind,
}

// -------------------------------------------------------------- resolution #

/// Closed reason why a reference carries no [`NavLinkKind::ResolvesTo`] link.
///
/// Absence of a target is a recorded outcome, never an invented link: a
/// reference address in [`NavigationIndex::nodes_by_address`] has **exactly
/// one** of a `ResolvesTo` link or one `NavResolveReason`, with no third state.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavResolveReason {
    /// No `footnote` / `endnote` definition carries the reference's `w:id`.
    NoMatchingNoteDefinition,
    /// More than one definition (or more than one note view) matches the `w:id`.
    MultipleMatchingNoteDefinitions,
    /// The reference type is not a note / endnote reference.
    NotAResolvableReference,
    /// The reference or its definition names no substrate element.
    MissingAnchorElement,
    /// A unique definition exists but no note view anchors it.
    MissingNoteView,
}

impl NavResolveReason {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavResolveReason::NoMatchingNoteDefinition => "no_matching_note_definition",
            NavResolveReason::MultipleMatchingNoteDefinitions => {
                "multiple_matching_note_definitions"
            }
            NavResolveReason::NotAResolvableReference => "not_a_resolvable_reference",
            NavResolveReason::MissingAnchorElement => "missing_anchor_element",
            NavResolveReason::MissingNoteView => "missing_note_view",
        }
    }
}

impl fmt::Display for NavResolveReason {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

// ------------------------------------------------------------- subtree text #

/// The two text channels of a view subtree, aggregated in reading order.
///
/// `primary` is the concatenation of the S05 `CleanView` `Primary` units over
/// the subtree's primary views; `service` is the concatenation of the `Service`
/// units. An empty subtree yields two empty channels, never a placeholder.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct SubtreeText {
    /// The concatenated primary channel, in reading order.
    pub primary: String,
    /// The concatenated service channel, in reading order.
    pub service: String,
}

impl SubtreeText {
    /// The empty subtree text.
    pub fn empty() -> Self {
        SubtreeText::default()
    }
}

// ------------------------------------------------------------- neighbours #

/// The reading-order neighbours of a primary view.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Neighbours {
    /// The previous primary view in reading order, if any.
    pub prev: Option<ViewId>,
    /// The next primary view in reading order, if any.
    pub next: Option<ViewId>,
}

impl Neighbours {
    /// The empty neighbour pair.
    pub const fn none() -> Self {
        Neighbours {
            prev: None,
            next: None,
        }
    }
}

// ----------------------------------------------------------------- errors #

/// Closed failure class of the navigation index.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NavErrorKind {
    /// Two records claim the same address id space token.
    DuplicateNodeId,
    /// An address or link names no substrate element.
    MissingAnchorElement,
    /// An address or link names no substrate text fragment.
    MissingAnchorFragment,
    /// A link or accessor names no view in the projection.
    MissingAnchorView,
    /// A link or accessor names no segment record.
    MissingAnchorSegment,
    /// A link or accessor names no reference record.
    MissingAnchorReference,
    /// `parent_view` / `children` form a cycle, so `path_to_root` is unbounded.
    ParentCycle,
    /// A substrate record is malformed or unreadable.
    UnreadableSubstrate,
}

impl NavErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavErrorKind::DuplicateNodeId => "duplicate_node_id",
            NavErrorKind::MissingAnchorElement => "missing_anchor_element",
            NavErrorKind::MissingAnchorFragment => "missing_anchor_fragment",
            NavErrorKind::MissingAnchorView => "missing_anchor_view",
            NavErrorKind::MissingAnchorSegment => "missing_anchor_segment",
            NavErrorKind::MissingAnchorReference => "missing_anchor_reference",
            NavErrorKind::ParentCycle => "parent_cycle",
            NavErrorKind::UnreadableSubstrate => "unreadable_substrate",
        }
    }
}

impl fmt::Display for NavErrorKind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

/// Typed navigation error. Carries no serialization dependency; `detail` names
/// ids and coordinates only, never decoded text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavError {
    kind: NavErrorKind,
    detail: String,
}

impl NavError {
    /// Builds an error from a class and a human-readable detail.
    pub fn new(kind: NavErrorKind, detail: impl Into<String>) -> Self {
        NavError {
            kind,
            detail: detail.into(),
        }
    }

    /// Error class.
    pub const fn kind(&self) -> NavErrorKind {
        self.kind
    }

    /// Human-readable detail (never parsed; for diagnostics only).
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for NavError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for NavError {}

fn unreadable(detail: impl Into<String>) -> NavError {
    NavError::new(NavErrorKind::UnreadableSubstrate, detail)
}

fn missing_view(view: &ViewId) -> NavError {
    NavError::new(
        NavErrorKind::MissingAnchorView,
        format!("view {view} is not in the navigation index"),
    )
}

// ------------------------------------------------------------- resolution #

/// Local name of a Clark-qualified name (`{ns}local`), or the whole token when
/// it is not namespace-qualified.
fn clark_local(name: &str) -> &str {
    if let Some(rest) = name.strip_prefix('{')
        && let Some(close) = rest.find('}')
    {
        return &rest[close + 1..];
    }
    name
}

/// Value of the attribute whose *local* name is `local`, from the Clark-keyed
/// substrate `attrs` map.
fn attr_local<'a>(attrs: &'a BTreeMap<String, String>, local: &str) -> Option<&'a str> {
    attrs
        .iter()
        .find(|(key, _)| clark_local(key) == local)
        .map(|(_, value)| value.as_str())
}

/// Bounded note resolution: a `NoteReference` / `EndnoteReference` resolves by
/// matching its substrate `w:id` attribute to the note definition element
/// (`footnote` for a note reference, `endnote` for an endnote reference) with
/// the same `w:id`, and then to the note view anchored at that definition.
///
/// Success requires **exactly one** matching definition and **exactly one**
/// note view for it. Anything else is a closed [`NavResolveReason`], never a
/// best-effort target and never an invented link.
fn resolve_reference(
    index: &ReaderRecordIndex,
    projection: &ReaderProjection,
    reference: &ProjectedReference,
) -> Result<ViewId, NavResolveReason> {
    let definition_local = match reference.reference_type {
        ReaderReferenceType::NoteReference => "footnote",
        ReaderReferenceType::EndnoteReference => "endnote",
        _ => return Err(NavResolveReason::NotAResolvableReference),
    };
    let anchor = index
        .element(reference.element_ref.as_str())
        .ok_or(NavResolveReason::MissingAnchorElement)?;
    let anchor_id =
        attr_local(&anchor.attrs, "id").ok_or(NavResolveReason::NoMatchingNoteDefinition)?;

    let mut definitions: Vec<&str> = Vec::new();
    for element in index.elements() {
        if clark_local(&element.clark_tag) == definition_local
            && attr_local(&element.attrs, "id") == Some(anchor_id)
        {
            definitions.push(element.id.as_str());
        }
    }
    if definitions.is_empty() {
        return Err(NavResolveReason::NoMatchingNoteDefinition);
    }
    if definitions.len() > 1 {
        return Err(NavResolveReason::MultipleMatchingNoteDefinitions);
    }
    let definition = definitions[0];

    let mut matches: Vec<&ViewId> = Vec::new();
    for view in &projection.views {
        if view.kind == ReaderViewKind::Note && view.element_ref.as_str() == definition {
            matches.push(&view.id);
        }
    }
    match matches.len() {
        0 => Err(NavResolveReason::MissingNoteView),
        1 => Ok(matches[0].clone()),
        _ => Err(NavResolveReason::MultipleMatchingNoteDefinitions),
    }
}

// ------------------------------------------------------------- view entry #

/// Private structural entry for a view, used by the accessors.
#[derive(Debug, Clone, PartialEq, Eq)]
struct ViewEntry {
    kind: ReaderViewKind,
    parent: Option<ViewId>,
    children: Vec<ViewId>,
    source_pos: usize,
}

/// A view sorted into its `precedes` sibling group. The derived field order is
/// the sort order: parent group, then source position, then view kind rank, then
/// view id.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
struct SiblingMember {
    parent: Option<ViewId>,
    source_pos: usize,
    rank: u8,
    id: ViewId,
}

/// Deterministic rank used to order views sharing a `source_pos`. Mirrors the
/// reader projection's tie-break so navigation re-derives the same order.
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

/// Total order key for the document pre-order (`source_order`).
fn order_key(node: &NavNode) -> (usize, u8, u8, String) {
    let kind_rank = match node.kind {
        NavNodeKind::View => 0u8,
        NavNodeKind::Segment => 1,
        NavNodeKind::Reference => 2,
    };
    let view_rank = match &node.body {
        NavNodeBody::View { view_kind, .. } => view_kind_rank(*view_kind),
        _ => 0,
    };
    (
        node.source_pos,
        kind_rank,
        view_rank,
        node.address.id_token().to_string(),
    )
}

// ------------------------------------------------------------------- index #

/// A read-only navigation index over a reader projection.
///
/// The index is the product of [`build_navigation`]. It carries the address map,
/// the document pre-order, the typed links and the element / fragment anchor
/// indexes, plus the private structural maps that back the accessors. It is a
/// read-only additive surface: it never mutates, reseals or re-bases its inputs.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavigationIndex {
    /// Every navigation node by address.
    pub nodes_by_address: BTreeMap<NodeAddress, NavNode>,
    /// Document pre-order of every node, ordered by `source_pos`.
    pub source_order: Vec<NodeAddress>,
    /// Every typed navigation link.
    pub links: Vec<NavLink>,
    /// Nodes anchored by each substrate element.
    pub element_index: BTreeMap<ElementRef, Vec<NodeAddress>>,
    /// Nodes anchored by each substrate text fragment.
    pub fragment_index: BTreeMap<FragmentRef, Vec<NodeAddress>>,
    /// Closed unresolved reasons, keyed by reference id. One entry per
    /// unresolved reference, exactly complementary to the `ResolvesTo` links.
    pub resolve_reasons: BTreeMap<ReferenceId, NavResolveReason>,
    views_by_id: BTreeMap<ViewId, ViewEntry>,
    siblings_by_view: BTreeMap<ViewId, Vec<ViewId>>,
    reading_order_views: Vec<ViewId>,
}

impl NavigationIndex {
    /// Looks up a node by address.
    pub fn resolve(&self, address: &NodeAddress) -> Result<&NavNode, NavError> {
        self.nodes_by_address
            .get(address)
            .ok_or_else(|| match address {
                NodeAddress::View(view) => missing_view(view),
                NodeAddress::Segment(segment) => NavError::new(
                    NavErrorKind::MissingAnchorSegment,
                    format!("segment {segment} is not in the navigation index"),
                ),
                NodeAddress::Reference(reference) => NavError::new(
                    NavErrorKind::MissingAnchorReference,
                    format!("reference {reference} is not in the navigation index"),
                ),
            })
    }

    /// The child views of a view, in the parent's `children` order. An unknown
    /// view yields an empty slice.
    pub fn children(&self, view: &ViewId) -> &[ViewId] {
        self.views_by_id
            .get(view)
            .map(|entry| entry.children.as_slice())
            .unwrap_or(&[])
    }

    /// The `parent_view` of a view, or `None` for a root or unknown view.
    pub fn parent(&self, view: &ViewId) -> Option<ViewId> {
        self.views_by_id
            .get(view)
            .and_then(|entry| entry.parent.clone())
    }

    /// The ancestor chain of a view, **root-first** (outermost view first,
    /// queried view last).
    ///
    /// The walk is bounded by a visited-set: a cyclic `parent_view` fails closed
    /// with [`NavErrorKind::ParentCycle`], so the call terminates on any input.
    /// An unknown view is refused with [`NavErrorKind::MissingAnchorView`].
    pub fn path_to_root(&self, view: &ViewId) -> Result<Vec<ViewId>, NavError> {
        if !self.views_by_id.contains_key(view) {
            return Err(missing_view(view));
        }
        let mut chain: Vec<ViewId> = vec![view.clone()];
        let mut visited: HashSet<ViewId> = HashSet::new();
        visited.insert(view.clone());
        let mut current = view.clone();
        loop {
            let parent = match self.views_by_id.get(&current) {
                Some(entry) => entry.parent.clone(),
                None => return Err(missing_view(&current)),
            };
            let Some(parent) = parent else {
                break;
            };
            if !self.views_by_id.contains_key(&parent) {
                return Err(missing_view(&parent));
            }
            if !visited.insert(parent.clone()) {
                return Err(NavError::new(
                    NavErrorKind::ParentCycle,
                    format!("parent chain from view {view} revisits view {parent}"),
                ));
            }
            chain.push(parent.clone());
            current = parent;
        }
        chain.reverse();
        Ok(chain)
    }

    /// The other children of the view's `parent_view`, in the parent's
    /// `children` order. A root view (no parent) has no structural siblings, and
    /// an unknown view yields an empty slice.
    pub fn siblings(&self, view: &ViewId) -> &[ViewId] {
        self.siblings_by_view
            .get(view)
            .map(|siblings| siblings.as_slice())
            .unwrap_or(&[])
    }

    /// The previous and next **primary** view in reading order, taken from the
    /// substrate event walk that backs the S04 reading-order index.
    ///
    /// A navigation view (or an unknown id) is refused with
    /// [`NavErrorKind::MissingAnchorView`]. An empty primary view owns no event,
    /// so it has no reading-order position and yields an empty neighbour pair.
    pub fn neighbours(&self, view: &ViewId) -> Result<Neighbours, NavError> {
        let entry = self
            .views_by_id
            .get(view)
            .ok_or_else(|| missing_view(view))?;
        if !entry.kind.is_primary() {
            return Err(NavError::new(
                NavErrorKind::MissingAnchorView,
                format!("view {view} is a navigation view, not a primary reading-order view"),
            ));
        }
        match self.reading_order_views.iter().position(|id| id == view) {
            Some(position) => Ok(Neighbours {
                prev: if position > 0 {
                    Some(self.reading_order_views[position - 1].clone())
                } else {
                    None
                },
                next: self.reading_order_views.get(position + 1).cloned(),
            }),
            None => Ok(Neighbours::none()),
        }
    }

    /// The primary views in reading order (the substrate event walk). An empty
    /// primary view owns no event and is absent from this sequence.
    pub fn reading_order_views(&self) -> &[ViewId] {
        &self.reading_order_views
    }

    /// The view that owns a node: a view owns itself, a segment / reference is
    /// owned by its `view`. An unknown address yields `None`.
    pub fn owning_view(&self, address: &NodeAddress) -> Option<ViewId> {
        match address {
            NodeAddress::View(view) => Some(view.clone()),
            _ => match self.nodes_by_address.get(address) {
                Some(NavNode {
                    body: NavNodeBody::Segment { view, .. },
                    ..
                })
                | Some(NavNode {
                    body: NavNodeBody::Reference { view, .. },
                    ..
                }) => Some(view.clone()),
                _ => None,
            },
        }
    }

    /// The nodes anchored by a substrate element.
    pub fn anchors_of_element(&self, element: &ElementRef) -> &[NodeAddress] {
        self.element_index
            .get(element)
            .map(|addresses| addresses.as_slice())
            .unwrap_or(&[])
    }

    /// The nodes anchored by a substrate text fragment.
    pub fn anchors_of_fragment(&self, fragment: &FragmentRef) -> &[NodeAddress] {
        self.fragment_index
            .get(fragment)
            .map(|addresses| addresses.as_slice())
            .unwrap_or(&[])
    }

    /// Every link of a given kind, in construction order.
    pub fn links_of_kind(&self, kind: NavLinkKind) -> Vec<&NavLink> {
        self.links.iter().filter(|link| link.kind == kind).collect()
    }

    /// The closed unresolved reason for a reference, if the reference has no
    /// `ResolvesTo` link. Returns `None` for a resolved reference (and for an
    /// unknown reference id).
    pub fn resolve_reason(&self, reference: &ReferenceId) -> Option<NavResolveReason> {
        self.resolve_reasons.get(reference).copied()
    }

    /// The text of a view's subtree (the view and all descendant views) in
    /// reading order, split into the S05 `primary` and `service` channels.
    ///
    /// Descendant primary views are visited in the S04 reading order; the text
    /// is read only from the supplied S05 [`CleanView`] — navigation views carry
    /// no text and are never asked. A derived separator (including a
    /// `page_break`) contributes its `service` literal and is never a page
    /// boundary. An unknown view, or a primary descendant absent from the clean
    /// view, is refused with [`NavErrorKind::MissingAnchorView`]; an empty
    /// subtree yields two empty channels.
    pub fn subtree_text(&self, view: &ViewId, clean: &CleanView) -> Result<SubtreeText, NavError> {
        if !self.views_by_id.contains_key(view) {
            return Err(missing_view(view));
        }

        // The subtree (the view plus every descendant), bounded by a visited-set
        // so a hostile cyclic child graph cannot loop.
        let mut subtree: HashSet<ViewId> = HashSet::new();
        let mut stack: Vec<ViewId> = vec![view.clone()];
        while let Some(current) = stack.pop() {
            if !subtree.insert(current.clone()) {
                continue;
            }
            if let Some(entry) = self.views_by_id.get(&current) {
                for child in &entry.children {
                    if !subtree.contains(child) {
                        stack.push(child.clone());
                    }
                }
            }
        }

        // Primary descendants in reading order first, then any remaining
        // descendant view in document pre-order (never silently dropped).
        let mut ordered: Vec<ViewId> = Vec::new();
        let mut placed: HashSet<ViewId> = HashSet::new();
        for candidate in &self.reading_order_views {
            if subtree.contains(candidate) && placed.insert(candidate.clone()) {
                ordered.push(candidate.clone());
            }
        }
        for address in &self.source_order {
            if let NodeAddress::View(candidate) = address
                && subtree.contains(candidate)
                && placed.insert(candidate.clone())
            {
                ordered.push(candidate.clone());
            }
        }

        let mut primary = String::new();
        let mut service = String::new();
        for candidate in &ordered {
            let is_primary = self
                .views_by_id
                .get(candidate)
                .map(|entry| entry.kind.is_primary())
                .unwrap_or(false);
            if !is_primary {
                continue;
            }
            let text = clean.view_text(candidate).map_err(|_| {
                NavError::new(
                    NavErrorKind::MissingAnchorView,
                    format!("primary view {candidate} has no clean-view text"),
                )
            })?;
            primary.push_str(text.primary());
            service.push_str(text.service());
        }
        Ok(SubtreeText { primary, service })
    }
}

// ------------------------------------------------------------------ build #

/// The ordered view keys produced by the substrate document-event walk (never an
/// XML re-parse). Mirrors the capture pre-order: an element's own text, then a
/// documented control, then its reference event, then its children in document
/// order, each followed by that child's `tail_ref`.
fn walk_view_keys(index: &ReaderRecordIndex) -> Result<Vec<ReaderViewKey>, NavError> {
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

    let mut keys: Vec<ReaderViewKey> = Vec::new();
    let mut stack: Vec<Step<'_>> = roots.iter().rev().map(|root| Step::Node(root)).collect();
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(element) => {
                let role = index
                    .role_of(&element.id)
                    .ok_or_else(|| unreadable(format!("element {} has no role", element.id)))?;
                let element_ref = ElementRef::new(element.id.as_str());
                if element.text_ref.is_some() {
                    keys.push(
                        view_key(index, &element_ref)
                            .map_err(|error| unreadable(error.detail().to_string()))?,
                    );
                }
                if role == ReaderRole::Control
                    && element.text_ref.is_none()
                    && control_derived_kind(&element.clark_tag, &element.attrs).is_some()
                {
                    keys.push(
                        view_key(index, &element_ref)
                            .map_err(|error| unreadable(error.detail().to_string()))?,
                    );
                }
                if matches!(
                    role,
                    ReaderRole::NoteReference
                        | ReaderRole::Field
                        | ReaderRole::Unknown
                        | ReaderRole::Foreign
                ) {
                    keys.push(
                        view_key(index, &element_ref)
                            .map_err(|error| unreadable(error.detail().to_string()))?,
                    );
                }
                if let Some(kids) = children.get(&element.id) {
                    for child in kids.iter().rev() {
                        stack.push(Step::Tail(child));
                        stack.push(Step::Node(child));
                    }
                }
            }
            Step::Tail(element) => {
                if element.tail_ref.is_some() {
                    let element_ref = ElementRef::new(element.id.as_str());
                    keys.push(
                        tail_view_key(index, &element_ref)
                            .map_err(|error| unreadable(error.detail().to_string()))?,
                    );
                }
            }
        }
    }
    Ok(keys)
}

/// The primary views in reading order: the first-appearance order of the primary
/// view keys in the substrate event walk.
fn reading_order_view_sequence(
    index: &ReaderRecordIndex,
    projection: &ReaderProjection,
) -> Result<Vec<ViewId>, NavError> {
    let mut id_by_key: HashMap<(ReaderViewKind, String), ViewId> = HashMap::new();
    for view in &projection.views {
        if view.kind.is_primary() {
            id_by_key.insert(
                (view.kind, view.element_ref.as_str().to_string()),
                view.id.clone(),
            );
        }
    }
    let mut order: Vec<ViewId> = Vec::new();
    let mut seen: HashSet<String> = HashSet::new();
    for key in walk_view_keys(index)? {
        if let Some(id) = id_by_key.get(&(key.kind, key.element_ref.as_str().to_string()))
            && seen.insert(id.as_str().to_string())
        {
            order.push(id.clone());
        }
    }
    Ok(order)
}

/// Builds the navigation index over an already-verified reader projection, its
/// S04 reading-order index and the S02 substrate records.
///
/// Every inconsistency is collected and returned as a typed [`NavError`]; a
/// partial or clamped index is never returned. The build validates address
/// existence, id-space uniqueness, anchor existence and parent / child
/// existence, and takes reading order from the substrate event walk (never from
/// `semantic`, `source_pos` or record order). It does not call
/// `reader_projection::build_projection` and does not re-parse XML.
pub fn build_navigation(
    projection: &ReaderProjection,
    order: &ReadingOrderIndex,
    records: &[Record],
) -> Result<NavigationIndex, Vec<NavError>> {
    let record_index = match ReaderRecordIndex::new(records) {
        Ok(index) => index,
        Err(error) => {
            return Err(vec![unreadable(format!(
                "substrate index is not readable: {}",
                error.detail()
            ))]);
        }
    };

    let mut errors: Vec<NavError> = Vec::new();
    let mut nodes_by_address: BTreeMap<NodeAddress, NavNode> = BTreeMap::new();
    let view_ids: HashSet<&str> = projection
        .views
        .iter()
        .map(|view| view.id.as_str())
        .collect();

    // 1. View nodes.
    for view in &projection.views {
        let Some(source_pos) = record_index.source_pos(view.element_ref.as_str()) else {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorElement,
                format!(
                    "view {} names element {} absent from the substrate",
                    view.id, view.element_ref
                ),
            ));
            continue;
        };
        let node = NavNode {
            address: NodeAddress::View(view.id.clone()),
            kind: NavNodeKind::View,
            body: NavNodeBody::View {
                view_kind: view.kind,
                element_ref: view.element_ref.clone(),
                parent_view: view.parent_view.clone(),
                primary: view.kind.is_primary(),
            },
            source_pos,
        };
        if nodes_by_address
            .insert(node.address.clone(), node)
            .is_some()
        {
            errors.push(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("view id {} appears more than once", view.id),
            ));
        }
    }

    // 2. Segment nodes.
    for segment in &projection.segments {
        if !view_ids.contains(segment.view.as_str()) {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorView,
                format!(
                    "segment {} names view {} absent from the projection",
                    segment.id, segment.view
                ),
            ));
            continue;
        }
        if record_index.element(segment.element_ref.as_str()).is_none() {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorElement,
                format!(
                    "segment {} names element {} absent from the substrate",
                    segment.id, segment.element_ref
                ),
            ));
            continue;
        }
        if let Some(fragment) = &segment.fragment_ref
            && record_index.text(fragment.as_str()).is_none()
        {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorFragment,
                format!(
                    "segment {} names fragment {} absent from the substrate",
                    segment.id, fragment
                ),
            ));
            continue;
        }
        let node = NavNode {
            address: NodeAddress::Segment(segment.id.clone()),
            kind: NavNodeKind::Segment,
            body: NavNodeBody::Segment {
                view: segment.view.clone(),
                segment_kind: segment.segment_kind,
                origin: segment.origin,
                fragment_ref: segment.fragment_ref.clone(),
                slot: segment.slot,
                span: segment.span.clone(),
                semantic: segment.semantic,
                element_ref: segment.element_ref.clone(),
            },
            source_pos: segment.source_pos,
        };
        if nodes_by_address
            .insert(node.address.clone(), node)
            .is_some()
        {
            errors.push(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("segment id {} appears more than once", segment.id),
            ));
        }
    }

    // 3. Reference nodes.
    for reference in &projection.references {
        if !view_ids.contains(reference.view.as_str()) {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorView,
                format!(
                    "reference {} names view {} absent from the projection",
                    reference.id, reference.view
                ),
            ));
            continue;
        }
        if record_index
            .element(reference.element_ref.as_str())
            .is_none()
        {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorElement,
                format!(
                    "reference {} names element {} absent from the substrate",
                    reference.id, reference.element_ref
                ),
            ));
            continue;
        }
        let node = NavNode {
            address: NodeAddress::Reference(reference.id.clone()),
            kind: NavNodeKind::Reference,
            body: NavNodeBody::Reference {
                view: reference.view.clone(),
                reference_type: reference.reference_type,
                element_ref: reference.element_ref.clone(),
            },
            source_pos: reference.source_pos,
        };
        if nodes_by_address
            .insert(node.address.clone(), node)
            .is_some()
        {
            errors.push(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("reference id {} appears more than once", reference.id),
            ));
        }
    }

    // 4. Structural maps: parents, children, siblings.
    let mut views_by_id: BTreeMap<ViewId, ViewEntry> = BTreeMap::new();
    for view in &projection.views {
        views_by_id.insert(
            view.id.clone(),
            ViewEntry {
                kind: view.kind,
                parent: view.parent_view.clone(),
                children: view.children.clone(),
                source_pos: record_index
                    .source_pos(view.element_ref.as_str())
                    .unwrap_or(usize::MAX),
            },
        );
    }
    for view in &projection.views {
        if let Some(parent) = &view.parent_view
            && !view_ids.contains(parent.as_str())
        {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorView,
                format!(
                    "view {} names parent view {} absent from the projection",
                    view.id, parent
                ),
            ));
        }
        for child in &view.children {
            if !view_ids.contains(child.as_str()) {
                errors.push(NavError::new(
                    NavErrorKind::MissingAnchorView,
                    format!(
                        "view {} names child view {} absent from the projection",
                        view.id, child
                    ),
                ));
            }
        }
    }

    let mut siblings_by_view: BTreeMap<ViewId, Vec<ViewId>> = BTreeMap::new();
    for view in &projection.views {
        let siblings = match &view.parent_view {
            Some(parent) => match views_by_id.get(parent) {
                Some(entry) => entry
                    .children
                    .iter()
                    .filter(|child| *child != &view.id)
                    .cloned()
                    .collect(),
                None => Vec::new(),
            },
            None => Vec::new(),
        };
        siblings_by_view.insert(view.id.clone(), siblings);
    }

    // 5. Reading order: the substrate event walk, tied to the S04 index.
    let reading_order_views = match reading_order_view_sequence(&record_index, projection) {
        Ok(sequence) => sequence,
        Err(error) => {
            errors.push(error);
            Vec::new()
        }
    };
    for view in &projection.views {
        if view.kind.is_primary() && order.reading_order(&view.id).is_err() {
            errors.push(NavError::new(
                NavErrorKind::MissingAnchorView,
                format!(
                    "primary view {} has no reading-order entry in the S04 index",
                    view.id
                ),
            ));
        }
    }

    // 6. Links: Contains, Owns, Precedes.
    let mut links: Vec<NavLink> = Vec::new();
    for view in &projection.views {
        if let Some(parent) = &view.parent_view
            && view_ids.contains(parent.as_str())
        {
            links.push(NavLink {
                from: NodeAddress::View(parent.clone()),
                to: NodeAddress::View(view.id.clone()),
                kind: NavLinkKind::Contains,
            });
        }
    }
    for segment in &projection.segments {
        if view_ids.contains(segment.view.as_str()) {
            links.push(NavLink {
                from: NodeAddress::View(segment.view.clone()),
                to: NodeAddress::Segment(segment.id.clone()),
                kind: NavLinkKind::Owns,
            });
        }
    }
    for reference in &projection.references {
        if view_ids.contains(reference.view.as_str()) {
            links.push(NavLink {
                from: NodeAddress::View(reference.view.clone()),
                to: NodeAddress::Reference(reference.id.clone()),
                kind: NavLinkKind::Owns,
            });
        }
    }

    // Document pre-order of every node.
    let mut source_order: Vec<NodeAddress> = nodes_by_address.keys().cloned().collect();
    source_order.sort_by(|left, right| {
        order_key(&nodes_by_address[left]).cmp(&order_key(&nodes_by_address[right]))
    });

    // Precedes: consecutive view siblings in a parent group (root group included),
    // ordered by the source order of the parent's children.
    let mut members: Vec<SiblingMember> = Vec::with_capacity(projection.views.len());
    for view in &projection.views {
        let entry = &views_by_id[&view.id];
        members.push(SiblingMember {
            parent: view.parent_view.clone(),
            source_pos: entry.source_pos,
            rank: view_kind_rank(view.kind),
            id: view.id.clone(),
        });
    }
    members.sort();
    for pair in members.windows(2) {
        if pair[0].parent == pair[1].parent {
            links.push(NavLink {
                from: NodeAddress::View(pair[0].id.clone()),
                to: NodeAddress::View(pair[1].id.clone()),
                kind: NavLinkKind::Precedes,
            });
        }
    }

    // ResolvesTo (bounded note resolution) and the closed unresolved reasons.
    // Every reference that became a node gets exactly one of a `ResolvesTo`
    // link or a `NavResolveReason`; a reference that failed validation is not a
    // node and is skipped here.
    let mut resolve_reasons: BTreeMap<ReferenceId, NavResolveReason> = BTreeMap::new();
    for reference in &projection.references {
        let address = NodeAddress::Reference(reference.id.clone());
        if !nodes_by_address.contains_key(&address) {
            continue;
        }
        match resolve_reference(&record_index, projection, reference) {
            Ok(view_id) => {
                links.push(NavLink {
                    from: address,
                    to: NodeAddress::View(view_id),
                    kind: NavLinkKind::ResolvesTo,
                });
            }
            Err(reason) => {
                resolve_reasons.insert(reference.id.clone(), reason);
            }
        }
    }

    // 7. Element and fragment anchor indexes, in document pre-order.
    let mut element_index: BTreeMap<ElementRef, Vec<NodeAddress>> = BTreeMap::new();
    let mut fragment_index: BTreeMap<FragmentRef, Vec<NodeAddress>> = BTreeMap::new();
    for address in &source_order {
        let node = &nodes_by_address[address];
        element_index
            .entry(node.body.element_ref().clone())
            .or_default()
            .push(address.clone());
        if let Some(fragment) = node.body.fragment_ref() {
            fragment_index
                .entry(fragment.clone())
                .or_default()
                .push(address.clone());
        }
    }

    if !errors.is_empty() {
        return Err(errors);
    }

    Ok(NavigationIndex {
        nodes_by_address,
        source_order,
        links,
        element_index,
        fragment_index,
        resolve_reasons,
        views_by_id,
        siblings_by_view,
        reading_order_views,
    })
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reader_contract::ReaderViewKind;
    use crate::reader_projection::{ReaderProjection, build_projection};
    use crate::reader_reading_order::ReadingOrderIndex;
    use crate::source_package::{Limits, capture};

    const MIXED: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");

    fn inputs_from(xml: &str) -> (Vec<Record>, ReaderProjection, ReadingOrderIndex) {
        let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture captures");
        let records = package.records().to_vec();
        let projection = build_projection(&records).expect("projection builds");
        let order = ReadingOrderIndex::build(&projection, &records).expect("reading order builds");
        (records, projection, order)
    }

    fn mixed() -> (Vec<Record>, ReaderProjection, ReadingOrderIndex) {
        inputs_from(MIXED)
    }

    fn view_id(projection: &ReaderProjection, kind: ReaderViewKind, element_ref: &str) -> ViewId {
        projection
            .views
            .iter()
            .find(|view| view.kind == kind && view.element_ref.as_str() == element_ref)
            .unwrap_or_else(|| panic!("view {kind:?} {element_ref} missing"))
            .id
            .clone()
    }

    fn view_address(view: &ViewId) -> NodeAddress {
        NodeAddress::View(view.clone())
    }

    fn contains_link(index: &NavigationIndex, parent: &ViewId, child: &ViewId) -> bool {
        index.links.iter().any(|link| {
            link.kind == NavLinkKind::Contains
                && link.from == view_address(parent)
                && link.to == view_address(child)
        })
    }

    fn precedes_link(index: &NavigationIndex, from: &ViewId, to: &ViewId) -> bool {
        index.links.iter().any(|link| {
            link.kind == NavLinkKind::Precedes
                && link.from == view_address(from)
                && link.to == view_address(to)
        })
    }

    #[test]
    fn structure_on_mixed_fixture() {
        let (records, projection, order) = mixed();
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");

        // Every projected view, segment and reference has a node.
        assert_eq!(
            index.nodes_by_address.len(),
            projection.views.len() + projection.segments.len() + projection.references.len()
        );

        // The table cell owns three child views: paragraph, residual, residual.
        let cell = view_id(&projection, ReaderViewKind::Cell, "e12");
        let para = view_id(&projection, ReaderViewKind::Paragraph, "e13");
        let residual = view_id(&projection, ReaderViewKind::Residual, "e13");
        let delta = view_id(&projection, ReaderViewKind::Residual, "e16");
        assert_eq!(
            index.children(&cell),
            &[para.clone(), residual.clone(), delta.clone()]
        );
        assert_eq!(index.parent(&para), Some(cell.clone()));
        assert!(contains_link(&index, &cell, &para));
        assert!(contains_link(&index, &cell, &residual));
        assert!(contains_link(&index, &cell, &delta));

        // A primary view owns its segments; the table owns its row.
        let table = view_id(&projection, ReaderViewKind::Table, "e10");
        let row = view_id(&projection, ReaderViewKind::Row, "e11");
        assert!(contains_link(&index, &table, &row));
        let paragraph = view_id(&projection, ReaderViewKind::Paragraph, "e2");
        assert!(
            index
                .links_of_kind(NavLinkKind::Owns)
                .iter()
                .any(|link| link.from == view_address(&paragraph))
        );

        // Every node resolves, and the owning view is well defined.
        for address in &index.source_order {
            let node = index.resolve(address).expect("node resolves");
            assert_eq!(node.address, *address);
            assert_eq!(node.kind, address.kind());
            assert!(index.owning_view(address).is_some());
        }

        // The anchor indexes cover the substrate coordinates.
        assert!(!index.anchors_of_element(&ElementRef::from("e2")).is_empty());
        let t0 = FragmentRef::from("t0");
        assert!(
            index
                .anchors_of_fragment(&t0)
                .iter()
                .all(|address| address.kind() == NavNodeKind::Segment)
        );
    }

    #[test]
    fn path_to_root_is_root_first_and_terminal() {
        let (records, projection, order) = mixed();
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");

        // The note view is a root; the paragraph inside it is its child.
        let note = view_id(&projection, ReaderViewKind::Note, "e42");
        let nu = view_id(&projection, ReaderViewKind::Paragraph, "e43");
        assert_eq!(index.path_to_root(&note).unwrap(), vec![note.clone()]);
        assert_eq!(
            index.path_to_root(&nu).unwrap(),
            vec![note.clone(), nu.clone()]
        );

        // A paragraph inside a table cell is root-first: table, row, cell, then
        // the paragraph.
        let table = view_id(&projection, ReaderViewKind::Table, "e10");
        let row = view_id(&projection, ReaderViewKind::Row, "e11");
        let cell = view_id(&projection, ReaderViewKind::Cell, "e12");
        let gamma = view_id(&projection, ReaderViewKind::Paragraph, "e13");
        assert_eq!(
            index.path_to_root(&gamma).unwrap(),
            vec![table, row, cell, gamma]
        );

        // The last element of the chain is the queried view; the first has no parent.
        for view in &projection.views {
            let chain = index.path_to_root(&view.id).expect("path resolves");
            assert_eq!(chain.last(), Some(&view.id));
            assert!(index.parent(chain.first().unwrap()).is_none());
        }

        // An unknown view is refused.
        let unknown = ViewId::from("v-does-not-exist");
        assert_eq!(
            index.path_to_root(&unknown).unwrap_err().kind(),
            NavErrorKind::MissingAnchorView
        );
    }

    #[test]
    fn siblings_and_precedes_are_structural() {
        let (records, projection, order) = mixed();
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");

        let para = view_id(&projection, ReaderViewKind::Paragraph, "e13");
        let residual = view_id(&projection, ReaderViewKind::Residual, "e13");
        let delta = view_id(&projection, ReaderViewKind::Residual, "e16");
        assert_eq!(index.siblings(&para), &[residual.clone(), delta.clone()]);
        assert_eq!(index.siblings(&residual), &[para.clone(), delta.clone()]);

        // Precedes follows the parent's source order.
        assert!(precedes_link(&index, &para, &residual));
        assert!(precedes_link(&index, &residual, &delta));
        assert!(!precedes_link(&index, &delta, &para));

        // A root view has no structural siblings, but root views still chain by
        // source order through precedes.
        let alpha = view_id(&projection, ReaderViewKind::Paragraph, "e2");
        let beta = view_id(&projection, ReaderViewKind::Paragraph, "e5");
        assert!(index.siblings(&alpha).is_empty());
        assert!(precedes_link(&index, &alpha, &beta));
    }

    #[test]
    fn neighbours_follow_reading_order_not_source_pos() {
        let (records, projection, order) = mixed();
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");

        let alpha = view_id(&projection, ReaderViewKind::Paragraph, "e2");
        let beta = view_id(&projection, ReaderViewKind::Paragraph, "e5");
        let gamma = view_id(&projection, ReaderViewKind::Paragraph, "e13");
        let theta = view_id(&projection, ReaderViewKind::Paragraph, "e29");
        let kappa = view_id(&projection, ReaderViewKind::Residual, "e0");
        let nbsp = view_id(&projection, ReaderViewKind::Paragraph, "e38");

        // Reading order: alpha, beta, gamma, ... kappa (residual e0) sits between
        // theta and nbsp, even though its element is source_pos 0.
        assert_eq!(index.neighbours(&alpha).unwrap().prev, None);
        assert_eq!(index.neighbours(&alpha).unwrap().next, Some(beta.clone()));
        assert_eq!(index.neighbours(&beta).unwrap().prev, Some(alpha.clone()));
        assert_eq!(index.neighbours(&beta).unwrap().next, Some(gamma.clone()));
        assert_eq!(index.neighbours(&theta).unwrap().next, Some(kappa.clone()));
        assert_eq!(index.neighbours(&kappa).unwrap().prev, Some(theta.clone()));
        assert_eq!(index.neighbours(&kappa).unwrap().next, Some(nbsp.clone()));

        // Reading order must not be a source_pos sort: kappa's element is e0.
        let sequence = index.reading_order_views();
        let kappa_position = sequence.iter().position(|id| id == &kappa).unwrap();
        let nbsp_position = sequence.iter().position(|id| id == &nbsp).unwrap();
        assert!(kappa_position < nbsp_position);

        // A navigation view has no reading-order neighbours.
        let cell = view_id(&projection, ReaderViewKind::Cell, "e12");
        assert_eq!(
            index.neighbours(&cell).unwrap_err().kind(),
            NavErrorKind::MissingAnchorView
        );
    }

    #[test]
    fn synthetic_forest_structure_and_root_precedes() {
        // Two root paragraphs: no shared parent, but the source-order chain links
        // them. A table cell holds two paragraphs, which are structural siblings.
        let xml = format!(
            "<w:wordDocument xmlns:w=\"{ns}\"><w:body>\
             <w:p><w:r><w:t>A</w:t></w:r></w:p>\
             <w:p><w:r><w:t>B</w:t></w:r></w:p>\
             <w:tbl><w:tr><w:tc>\
               <w:p><w:r><w:t>C</w:t></w:r></w:p>\
               <w:p><w:r><w:t>D</w:t></w:r></w:p>\
             </w:tc></w:tr></w:tbl>\
             </w:body></w:wordDocument>",
            ns = "http://schemas.microsoft.com/office/word/2003/wordml"
        );
        let (records, projection, order) = inputs_from(&xml);
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");

        let para_a = view_id(&projection, ReaderViewKind::Paragraph, "e2");
        let para_b = view_id(&projection, ReaderViewKind::Paragraph, "e5");
        let cell = view_id(&projection, ReaderViewKind::Cell, "e10");
        let para_c = view_id(&projection, ReaderViewKind::Paragraph, "e11");
        let para_d = view_id(&projection, ReaderViewKind::Paragraph, "e14");

        assert_eq!(index.children(&cell), &[para_c.clone(), para_d.clone()]);
        assert_eq!(index.siblings(&para_c), std::slice::from_ref(&para_d));
        assert!(index.siblings(&para_a).is_empty());
        assert!(precedes_link(&index, &para_a, &para_b));
        assert!(precedes_link(&index, &para_c, &para_d));

        // Reading order over the four paragraphs.
        let sequence = index.reading_order_views();
        assert_eq!(
            sequence,
            &[
                para_a.clone(),
                para_b.clone(),
                para_c.clone(),
                para_d.clone()
            ]
        );
    }

    #[test]
    fn typed_refusals_are_fail_closed() {
        let (records, projection, order) = mixed();

        // A missing substrate element anchor.
        let mut broken = projection.clone();
        broken.views[0].element_ref = ElementRef::from("e-absent");
        let errors = build_navigation(&broken, &order, &records).expect_err("must refuse");
        assert!(
            errors
                .iter()
                .any(|error| error.kind() == NavErrorKind::MissingAnchorElement),
            "expected MissingAnchorElement, got {errors:?}"
        );

        // A missing text fragment anchor on a source segment.
        let mut broken = projection.clone();
        let target = broken
            .segments
            .iter_mut()
            .find(|segment| segment.fragment_ref.is_some())
            .expect("a source segment exists");
        target.fragment_ref = Some(FragmentRef::from("t-absent"));
        let errors = build_navigation(&broken, &order, &records).expect_err("must refuse");
        assert!(
            errors
                .iter()
                .any(|error| error.kind() == NavErrorKind::MissingAnchorFragment),
            "expected MissingAnchorFragment, got {errors:?}"
        );

        // A missing owning view.
        let mut broken = projection.clone();
        broken.segments[0].view = ViewId::from("v-absent");
        let errors = build_navigation(&broken, &order, &records).expect_err("must refuse");
        assert!(
            errors
                .iter()
                .any(|error| error.kind() == NavErrorKind::MissingAnchorView),
            "expected MissingAnchorView, got {errors:?}"
        );

        // A duplicated view id.
        let mut broken = projection.clone();
        let duplicate = broken.views[0].clone();
        broken.views.push(duplicate);
        let errors = build_navigation(&broken, &order, &records).expect_err("must refuse");
        assert!(
            errors
                .iter()
                .any(|error| error.kind() == NavErrorKind::DuplicateNodeId),
            "expected DuplicateNodeId, got {errors:?}"
        );

        // An unreadable substrate (duplicate element id).
        let mut bad_records = records.clone();
        if let Some(Record::Element(element)) = bad_records.first().cloned() {
            bad_records.push(Record::Element(element));
        }
        let errors = build_navigation(&projection, &order, &bad_records).expect_err("must refuse");
        assert_eq!(errors[0].kind(), NavErrorKind::UnreadableSubstrate);

        // An absent address is refused by `resolve`.
        assert_eq!(
            build_navigation(&projection, &order, &records)
                .unwrap()
                .resolve(&NodeAddress::View(ViewId::from("v-absent")))
                .unwrap_err()
                .kind(),
            NavErrorKind::MissingAnchorView
        );
    }

    #[test]
    fn path_to_root_refuses_a_parent_cycle() {
        // A two-view parent cycle is bounded by the visited-set.
        let xml = format!(
            "<w:wordDocument xmlns:w=\"{ns}\"><w:body>\
             <w:p><w:r><w:t>A</w:t></w:r></w:p>\
             <w:p><w:r><w:t>B</w:t></w:r></w:p>\
             </w:body></w:wordDocument>",
            ns = "http://schemas.microsoft.com/office/word/2003/wordml"
        );
        let (records, mut projection, order) = inputs_from(&xml);
        assert!(projection.views.len() >= 2, "need at least two views");
        // Force a cycle among the two first views.
        let first = projection.views[0].id.clone();
        let second = projection.views[1].id.clone();
        projection.views[0].parent_view = Some(second.clone());
        projection.views[1].parent_view = Some(first.clone());
        let index =
            build_navigation(&projection, &order, &records).expect("structure is consistent");

        let error = index.path_to_root(&first).unwrap_err();
        assert_eq!(error.kind(), NavErrorKind::ParentCycle);
    }

    #[test]
    fn source_stays_serialization_free() {
        let source = include_str!("reader_navigation.rs");
        let production = source
            .split("#[cfg(test)]")
            .next()
            .expect("split yields the production prefix");
        for forbidden in ["serde", "Deserialize", "Serialize", "serde_json"] {
            assert!(
                !production.contains(forbidden),
                "reader_navigation.rs must stay serialization-free: found {forbidden}"
            );
        }
    }

    #[test]
    fn multiple_note_definitions_are_closed() {
        // Two note definitions share one `w:id`, so resolution is not unique.
        let xml = format!(
            "<w:wordDocument xmlns:w=\"{ns}\"><w:body>\
             <w:p><w:r><w:t>x</w:t></w:r></w:p>\
             <w:footnoteReference w:id=\"1\"/>\
             <w:footnote w:id=\"1\"><w:p><w:r><w:t>a</w:t></w:r></w:p></w:footnote>\
             <w:footnote w:id=\"1\"><w:p><w:r><w:t>b</w:t></w:r></w:p></w:footnote>\
             </w:body></w:wordDocument>",
            ns = "http://schemas.microsoft.com/office/word/2003/wordml"
        );
        let (records, projection, order) = inputs_from(&xml);
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");
        let reference = projection
            .references
            .iter()
            .find(|reference| reference.reference_type == ReaderReferenceType::NoteReference)
            .expect("a note reference exists");
        assert_eq!(
            index.resolve_reason(&reference.id),
            Some(NavResolveReason::MultipleMatchingNoteDefinitions)
        );
        assert!(
            index
                .links_of_kind(NavLinkKind::ResolvesTo)
                .iter()
                .all(|link| link.from != NodeAddress::Reference(reference.id.clone()))
        );
    }

    #[test]
    fn missing_note_view_is_closed() {
        // A unique definition exists, but no note view anchors it.
        let (records, mut projection, order) = mixed();
        let note_view = projection
            .views
            .iter_mut()
            .find(|view| view.kind == ReaderViewKind::Note)
            .expect("a note view exists");
        note_view.element_ref = ElementRef::from("e2");
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");
        let reference = projection
            .references
            .iter()
            .find(|reference| reference.reference_type == ReaderReferenceType::NoteReference)
            .expect("a note reference exists");
        assert_eq!(
            index.resolve_reason(&reference.id),
            Some(NavResolveReason::MissingNoteView)
        );
    }

    #[test]
    fn empty_subtree_yields_empty_channels() {
        let xml = format!(
            "<w:wordDocument xmlns:w=\"{ns}\"><w:body>\
             <w:tbl><w:tr><w:tc></w:tc></w:tr></w:tbl>\
             </w:body></w:wordDocument>",
            ns = "http://schemas.microsoft.com/office/word/2003/wordml"
        );
        let (records, projection, order) = inputs_from(&xml);
        let clean = CleanView::build(&projection, &order, &records).expect("clean view builds");
        let index = build_navigation(&projection, &order, &records).expect("navigation builds");
        let cell = projection
            .views
            .iter()
            .find(|view| view.kind == ReaderViewKind::Cell)
            .expect("a cell view exists");
        let text = index.subtree_text(&cell.id, &clean).expect("subtree text");
        assert!(text.primary.is_empty());
        assert!(text.service.is_empty());
    }
}
