//! Read-only navigation index over the S02 read-back `CleanedProjection`.
//!
//! S02 ships a read-back projection that carries view/segment/reference
//! *anchors* but no unified addressable node space. This module is the S03
//! reading layer: it turns the frozen projection plus the frozen `Package`
//! into a [`NavIndex`] that lets a caller fetch one node by address, resolve
//! structural links (`Contains`/`Owns`/`ResolvesTo`/`Precedes`), walk to a
//! parent or up to a root, read the deterministic source order, and follow the
//! reverse anchors for an element or a fragment.
//!
//! Scope and non-claims: this is an in-memory, bounded, serialization-free
//! reader over the declared synthetic fixtures. It is **not** a graph
//! projection, **not** CST/AST/CTV, **not** citation resolution, **not** region
//! classification, and it never asserts legal authority or corpus coverage.
//!
//! The nav resolution never mutates the projection: `ProjectedReference.resolved`
//! stays `false` (a closed invariant of the frozen reader verifier). The
//! reference target, when one exists, lives only in a `NavLink`.
//!
//! Diagnostics carry only ids, closed codes and counters; decoded fragment text
//! is never interpolated.
//!
//! # Failure model
//!
//! `build_nav_index` fails closed on any structural inconsistency it cannot
//! resolve inside the same package: a duplicate node id, a view/segment/
//! reference cross-link that points at an absent node, a missing owning view, a
//! missing XML anchor, or a cycle in the `parent_view` chain (the last one
//! prevents an unbounded `path_to_root`). A wire read error is surfaced as
//! [`NavErrorKind::ArtifactUnreadable`].

use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fmt;

use crate::cleaned_wire::{CleanedProjection, read_cleaned_wire};
use crate::reader_contract::{
    ElementRef, FragmentRef, ReaderFragmentSpan, ReaderReferenceType, ReaderSegmentKind,
    ReaderSemantic, ReaderViewKind,
};
use crate::reader_projection::{
    ProjectedReference, ProjectedSegment, ProjectedView, ReaderProjection, ReferenceId, SegmentId,
    SegmentOrigin, ViewId,
};
use crate::source_package::{ElementRecord, Package, Record, TextSlot};

// ------------------------------------------------------------------ codes #

/// Closed navigation build error vocabulary. Each code names one structural
/// invariant the projection/substrate pair violated; none carries a legal
/// claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavErrorKind {
    /// Two nodes share one address inside the same id space.
    DuplicateNodeId,
    /// A `children` entry points at a view that does not exist.
    DanglingViewRef,
    /// A `segment_refs` entry points at a segment that does not exist.
    DanglingSegmentRef,
    /// A `reference_refs` entry points at a reference that does not exist.
    DanglingReferenceRef,
    /// A segment/reference `view` points at a view that does not exist.
    MissingOwningView,
    /// A `parent_view` points at a view that does not exist.
    DanglingParentView,
    /// An `element_ref`/`fragment_ref` has no record in the substrate.
    MissingAnchorElement,
    /// The wire artifact could not be read back.
    ArtifactUnreadable,
    /// The `parent_view` graph contains a cycle (would make `path_to_root`
    /// unbounded).
    CyclicViewGraph,
}

impl NavErrorKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavErrorKind::DuplicateNodeId => "duplicate_node_id",
            NavErrorKind::DanglingViewRef => "dangling_view_ref",
            NavErrorKind::DanglingSegmentRef => "dangling_segment_ref",
            NavErrorKind::DanglingReferenceRef => "dangling_reference_ref",
            NavErrorKind::MissingOwningView => "missing_owning_view",
            NavErrorKind::DanglingParentView => "dangling_parent_view",
            NavErrorKind::MissingAnchorElement => "missing_anchor_element",
            NavErrorKind::ArtifactUnreadable => "artifact_unreadable",
            NavErrorKind::CyclicViewGraph => "cyclic_view_graph",
        }
    }
}

/// A navigation build failure. `detail` carries ids, closed codes and counters
/// only; it never interpolates decoded fragment text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavError {
    kind: NavErrorKind,
    detail: String,
}

impl NavError {
    /// Builds an error from a closed kind and a text-free detail.
    pub fn new(kind: NavErrorKind, detail: impl Into<String>) -> Self {
        NavError {
            kind,
            detail: detail.into(),
        }
    }

    /// The closed failure kind.
    pub const fn kind(&self) -> NavErrorKind {
        self.kind
    }

    /// The text-free detail.
    pub fn detail(&self) -> &str {
        &self.detail
    }
}

impl fmt::Display for NavError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "nav failure {}: {}", self.kind.as_str(), self.detail)
    }
}

impl std::error::Error for NavError {}

/// Closed reason why a reference has no in-package target. Absence of a target
/// is a recorded outcome, never an invented link.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavResolveReason {
    /// No `footnote`/`endnote` definition carries the reference's `id`.
    NoMatchingNoteDefinition,
    /// More than one definition (or more than one note view) matches the `id`.
    MultipleMatchingNoteDefinitions,
    /// The reference type is never resolvable inside one package.
    NotAResolvableReference,
    /// The reference element itself is absent from the substrate.
    MissingAnchorElement,
    /// A definition exists but no note view anchors it.
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

// --------------------------------------------------------------- address #

/// Unified address of a navigation node. The id spaces are distinct, so the
/// variant is part of the identity: `vN`, `sN` and `rN` never collide.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum NodeAddress {
    /// A projected view address (`vN`).
    View(ViewId),
    /// A projected segment address (`sN`).
    Segment(SegmentId),
    /// A projected reference address (`rN`).
    Reference(ReferenceId),
}

/// Closed node kind carried by a [`NavNode`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NavNodeKind {
    /// A projected view.
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

/// Kind-specific body of a [`NavNode`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NavNodeBody {
    /// A view: its closed kind, its parent view (if any) and its empty flag.
    View {
        /// Closed reader view kind.
        view_kind: ReaderViewKind,
        /// The nearest enclosing view, as projected.
        parent_view: Option<ViewId>,
        /// `flags.empty` as projected.
        empty: bool,
    },
    /// A segment: its kind/origin/semantic plus source-fragment coordinates.
    Segment {
        /// Closed segment kind (text or derived).
        segment_kind: ReaderSegmentKind,
        /// Segment origin (source fragment or a documented control).
        origin: SegmentOrigin,
        /// Closed semantic classification.
        semantic: ReaderSemantic,
        /// The named fragment, for a source segment.
        fragment_ref: Option<FragmentRef>,
        /// The text slot, for a source segment.
        slot: Option<TextSlot>,
        /// The validated half-open span, for a source segment.
        span: Option<ReaderFragmentSpan>,
    },
    /// A reference: its closed reference type.
    Reference {
        /// Closed reference type.
        reference_type: ReaderReferenceType,
    },
}

/// One addressable navigation node.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavNode {
    /// The node address.
    pub address: NodeAddress,
    /// The XML element anchor.
    pub element_ref: ElementRef,
    /// Pre-order element position taken from the package, never parsed from an
    /// id token.
    pub source_pos: usize,
    /// The per-view ordinal, for segments and references.
    pub ordinal: Option<usize>,
    /// The owning view: `parent_view` for a view, the `view` field otherwise.
    pub owning_view: Option<ViewId>,
    /// The kind-specific body.
    pub body: NavNodeBody,
}

impl NavNode {
    /// The closed node kind.
    pub const fn kind(&self) -> NavNodeKind {
        match self.body {
            NavNodeBody::View { .. } => NavNodeKind::View,
            NavNodeBody::Segment { .. } => NavNodeKind::Segment,
            NavNodeBody::Reference { .. } => NavNodeKind::Reference,
        }
    }
}

// ----------------------------------------------------------------- links #

/// Closed navigation link vocabulary.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum NavLinkKind {
    /// A view contains a child view.
    Contains,
    /// A view owns a segment or a reference.
    Owns,
    /// A reference resolves to a note view inside the same package.
    ResolvesTo,
    /// A node is immediately followed by another in source order.
    Precedes,
}

impl NavLinkKind {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            NavLinkKind::Contains => "contains",
            NavLinkKind::Owns => "owns",
            NavLinkKind::ResolvesTo => "resolves_to",
            NavLinkKind::Precedes => "precedes",
        }
    }
}

/// A directed navigation link.
#[derive(Debug, Clone, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct NavLink {
    /// Link source.
    pub from: NodeAddress,
    /// Link target.
    pub to: NodeAddress,
    /// Closed link kind.
    pub kind: NavLinkKind,
}

// --------------------------------------------------------------- index #

/// The read-only navigation index. Every field is public so an independent
/// tamper battery can mutate a clone and prove fail-closed behaviour.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NavIndex {
    /// Every node by address.
    pub nodes_by_address: BTreeMap<NodeAddress, NavNode>,
    /// Grouped record order: views, then segments, then references, in
    /// projection vector order.
    pub record_order: Vec<NodeAddress>,
    /// Source order: views ordered by anchor position, then each view's
    /// segments by ordinal, then each view's references by ordinal.
    pub source_order: Vec<NodeAddress>,
    /// All structural links, deterministically ordered.
    pub links: Vec<NavLink>,
    /// Reverse anchors: element reference to every node anchored on it, in
    /// record order.
    pub element_index: BTreeMap<ElementRef, Vec<NodeAddress>>,
    /// Reverse anchor for a named fragment: its single source segment.
    pub fragment_index: BTreeMap<FragmentRef, NodeAddress>,
    /// Closed unresolved reasons, keyed by reference id.
    pub resolve_reasons: BTreeMap<ReferenceId, NavResolveReason>,
}

impl NavIndex {
    /// Fetch one node by address.
    pub fn resolve(&self, address: &NodeAddress) -> Option<&NavNode> {
        self.nodes_by_address.get(address)
    }

    /// The child views of a view, in `children` order.
    pub fn children(&self, view: &ViewId) -> Vec<NodeAddress> {
        let from = NodeAddress::View(view.clone());
        self.links
            .iter()
            .filter(|link| link.from == from && link.kind == NavLinkKind::Contains)
            .map(|link| link.to.clone())
            .collect()
    }

    /// The parent of a node: `parent_view` for a view, the owning view for a
    /// segment or reference.
    pub fn parent(&self, address: &NodeAddress) -> Option<NodeAddress> {
        let node = self.nodes_by_address.get(address)?;
        node.owning_view
            .as_ref()
            .map(|view| NodeAddress::View(view.clone()))
    }

    /// The chain from the root down to the node (root-first). A visited set
    /// bounds the walk, so a hand-built cyclic index can never loop forever.
    pub fn path_to_root(&self, address: &NodeAddress) -> Vec<NodeAddress> {
        let mut chain = Vec::new();
        let mut seen = BTreeSet::new();
        let mut current = Some(address.clone());
        while let Some(node) = current {
            if !seen.insert(node.clone()) {
                break;
            }
            chain.push(node.clone());
            current = self.parent(&node);
        }
        chain.reverse();
        chain
    }

    /// The deterministic source order.
    pub fn nodes_in_source_order(&self) -> &[NodeAddress] {
        &self.source_order
    }

    /// The owning view of a node.
    pub fn owning_view(&self, address: &NodeAddress) -> Option<&ViewId> {
        self.nodes_by_address
            .get(address)
            .and_then(|node| node.owning_view.as_ref())
    }

    /// Every node anchored on an element, in record order.
    pub fn anchors_of_element(&self, element_ref: &ElementRef) -> &[NodeAddress] {
        self.element_index
            .get(element_ref)
            .map(Vec::as_slice)
            .unwrap_or(&[])
    }

    /// The single source segment that names a fragment.
    pub fn anchors_of_fragment(&self, fragment: &FragmentRef) -> Option<&NodeAddress> {
        self.fragment_index.get(fragment)
    }

    /// All outward links of a node, in `links` order.
    pub fn outgoing(&self, address: &NodeAddress) -> Vec<&NavLink> {
        self.links
            .iter()
            .filter(|link| &link.from == address)
            .collect()
    }

    /// The recorded unresolved reason for a reference, if any.
    pub fn resolve_reason(&self, reference: &ReferenceId) -> Option<NavResolveReason> {
        self.resolve_reasons.get(reference).copied()
    }
}

// ------------------------------------------------------------- substrate #

/// Local, read-only view over the frozen package: element anchors in pre-order,
/// text-fragment ids, and the Clark-attribute helpers used for note resolution.
struct Substrate<'a> {
    elements: HashMap<&'a str, &'a ElementRecord>,
    element_pos: HashMap<&'a str, usize>,
    text_ids: HashSet<&'a str>,
}

impl<'a> Substrate<'a> {
    fn new(package: &'a Package) -> Result<Self, NavError> {
        let mut elements: HashMap<&'a str, &'a ElementRecord> = HashMap::new();
        let mut element_pos: HashMap<&'a str, usize> = HashMap::new();
        let mut text_ids: HashSet<&'a str> = HashSet::new();
        let mut position = 0usize;
        for record in package.records() {
            match record {
                Record::Element(element) => {
                    if elements.insert(element.id.as_str(), element).is_some() {
                        return Err(NavError::new(
                            NavErrorKind::DuplicateNodeId,
                            format!("duplicate element id {}", element.id),
                        ));
                    }
                    element_pos.insert(element.id.as_str(), position);
                    position += 1;
                }
                Record::Text(text) => {
                    text_ids.insert(text.id.as_str());
                }
            }
        }
        for element in elements.values() {
            if let Some(parent) = &element.parent
                && !elements.contains_key(parent.as_str())
            {
                return Err(NavError::new(
                    NavErrorKind::MissingAnchorElement,
                    format!("element {} parent {} is absent", element.id, parent),
                ));
            }
        }
        Ok(Substrate {
            elements,
            element_pos,
            text_ids,
        })
    }

    /// Pre-order element position, taken from the package.
    fn source_pos(&self, element_ref: &ElementRef) -> Option<usize> {
        self.element_pos.get(element_ref.as_str()).copied()
    }

    /// Whether a named fragment exists in the substrate.
    fn has_fragment(&self, fragment: &FragmentRef) -> bool {
        self.text_ids.contains(fragment.as_str())
    }

    /// Bounded note resolution: at most one `footnote`/`endnote` definition
    /// with the reference's local `id`, anchored by exactly one note view.
    fn resolve_reference(
        &self,
        reference: &ProjectedReference,
        projection: &ReaderProjection,
    ) -> Result<ViewId, NavResolveReason> {
        let definition_local = match reference.reference_type {
            ReaderReferenceType::NoteReference => "footnote",
            ReaderReferenceType::EndnoteReference => "endnote",
            _ => return Err(NavResolveReason::NotAResolvableReference),
        };
        let anchor = self
            .elements
            .get(reference.element_ref.as_str())
            .ok_or(NavResolveReason::MissingAnchorElement)?;
        let anchor_id =
            attr_local(&anchor.attrs, "id").ok_or(NavResolveReason::NoMatchingNoteDefinition)?;

        let mut definitions: Vec<&str> = Vec::new();
        for element in self.elements.values() {
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
        // The contract folds the zero-view case into the same closed reason as
        // the zero-definition case; `MissingNoteView` stays in the public
        // vocabulary for callers that distinguish the sub-case.
        match matches.len() {
            0 => Err(NavResolveReason::NoMatchingNoteDefinition),
            1 => Ok(matches[0].clone()),
            _ => Err(NavResolveReason::MultipleMatchingNoteDefinitions),
        }
    }
}

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

/// Value of the attribute whose *local* name is `local`.
fn attr_local<'a>(attrs: &'a BTreeMap<String, String>, local: &str) -> Option<&'a str> {
    attrs
        .iter()
        .find(|(key, _)| clark_local(key) == local)
        .map(|(_, value)| value.as_str())
}

fn missing_anchor(scope: &str, id: &str, element_ref: &ElementRef) -> NavError {
    NavError::new(
        NavErrorKind::MissingAnchorElement,
        format!(
            "{scope} {id} anchors absent element {}",
            element_ref.as_str()
        ),
    )
}

// --------------------------------------------------------------- build #

/// Builds the navigation index from a read-back projection and the frozen
/// package. The projection is never mutated.
pub fn build_nav_index(
    projection: &CleanedProjection,
    package: &Package,
) -> Result<NavIndex, NavError> {
    let substrate = Substrate::new(package)?;
    let proj = &projection.projection;

    let mut nodes_by_address: BTreeMap<NodeAddress, NavNode> = BTreeMap::new();
    let mut record_order: Vec<NodeAddress> = Vec::new();

    // Views first: they anchor every parent/child/ownership reference below.
    for view in &proj.views {
        let address = NodeAddress::View(view.id.clone());
        let source_pos = substrate
            .source_pos(&view.element_ref)
            .ok_or_else(|| missing_anchor("view", view.id.as_str(), &view.element_ref))?;
        let node = NavNode {
            address: address.clone(),
            element_ref: view.element_ref.clone(),
            source_pos,
            ordinal: None,
            owning_view: view.parent_view.clone(),
            body: NavNodeBody::View {
                view_kind: view.kind,
                parent_view: view.parent_view.clone(),
                empty: view.flags.empty,
            },
        };
        if nodes_by_address.insert(address.clone(), node).is_some() {
            return Err(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("duplicate view id {}", view.id),
            ));
        }
        record_order.push(address);
    }

    // Segments: each must anchor an element and name an existing owning view.
    for segment in &proj.segments {
        let address = NodeAddress::Segment(segment.id.clone());
        let source_pos = substrate
            .source_pos(&segment.element_ref)
            .ok_or_else(|| missing_anchor("segment", segment.id.as_str(), &segment.element_ref))?;
        if let Some(fragment) = &segment.fragment_ref
            && !substrate.has_fragment(fragment)
        {
            return Err(NavError::new(
                NavErrorKind::MissingAnchorElement,
                format!(
                    "segment {} names absent fragment {}",
                    segment.id,
                    fragment.as_str()
                ),
            ));
        }
        let owner = NodeAddress::View(segment.view.clone());
        if !nodes_by_address.contains_key(&owner) {
            return Err(NavError::new(
                NavErrorKind::MissingOwningView,
                format!("segment {} view {} is absent", segment.id, segment.view),
            ));
        }
        let node = NavNode {
            address: address.clone(),
            element_ref: segment.element_ref.clone(),
            source_pos,
            ordinal: Some(segment.ordinal),
            owning_view: Some(segment.view.clone()),
            body: NavNodeBody::Segment {
                segment_kind: segment.segment_kind,
                origin: segment.origin,
                semantic: segment.semantic,
                fragment_ref: segment.fragment_ref.clone(),
                slot: segment.slot,
                span: segment.span.clone(),
            },
        };
        if nodes_by_address.insert(address.clone(), node).is_some() {
            return Err(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("duplicate segment id {}", segment.id),
            ));
        }
        record_order.push(address);
    }

    // References: each must anchor an element and name an existing owning view.
    for reference in &proj.references {
        let address = NodeAddress::Reference(reference.id.clone());
        let source_pos = substrate
            .source_pos(&reference.element_ref)
            .ok_or_else(|| {
                missing_anchor("reference", reference.id.as_str(), &reference.element_ref)
            })?;
        let owner = NodeAddress::View(reference.view.clone());
        if !nodes_by_address.contains_key(&owner) {
            return Err(NavError::new(
                NavErrorKind::MissingOwningView,
                format!(
                    "reference {} view {} is absent",
                    reference.id, reference.view
                ),
            ));
        }
        let node = NavNode {
            address: address.clone(),
            element_ref: reference.element_ref.clone(),
            source_pos,
            ordinal: Some(reference.ordinal),
            owning_view: Some(reference.view.clone()),
            body: NavNodeBody::Reference {
                reference_type: reference.reference_type,
            },
        };
        if nodes_by_address.insert(address.clone(), node).is_some() {
            return Err(NavError::new(
                NavErrorKind::DuplicateNodeId,
                format!("duplicate reference id {}", reference.id),
            ));
        }
        record_order.push(address);
    }

    let mut links: Vec<NavLink> = Vec::new();

    // Contains (view -> child view) and parent validation.
    for view in &proj.views {
        let from = NodeAddress::View(view.id.clone());
        for child in &view.children {
            let to = NodeAddress::View(child.clone());
            if !nodes_by_address.contains_key(&to) {
                return Err(NavError::new(
                    NavErrorKind::DanglingViewRef,
                    format!("view {} child {} is absent", view.id, child),
                ));
            }
            links.push(NavLink {
                from: from.clone(),
                to,
                kind: NavLinkKind::Contains,
            });
        }
        if let Some(parent) = &view.parent_view {
            let target = NodeAddress::View(parent.clone());
            if !nodes_by_address.contains_key(&target) {
                return Err(NavError::new(
                    NavErrorKind::DanglingParentView,
                    format!("view {} parent {} is absent", view.id, parent),
                ));
            }
        }
    }

    // Owns (view -> segment and view -> reference).
    for view in &proj.views {
        let from = NodeAddress::View(view.id.clone());
        for segment_id in &view.segment_refs {
            let to = NodeAddress::Segment(segment_id.clone());
            if !nodes_by_address.contains_key(&to) {
                return Err(NavError::new(
                    NavErrorKind::DanglingSegmentRef,
                    format!("view {} segment {} is absent", view.id, segment_id),
                ));
            }
            links.push(NavLink {
                from: from.clone(),
                to,
                kind: NavLinkKind::Owns,
            });
        }
        for reference_id in &view.reference_refs {
            let to = NodeAddress::Reference(reference_id.clone());
            if !nodes_by_address.contains_key(&to) {
                return Err(NavError::new(
                    NavErrorKind::DanglingReferenceRef,
                    format!("view {} reference {} is absent", view.id, reference_id),
                ));
            }
            links.push(NavLink {
                from: from.clone(),
                to,
                kind: NavLinkKind::Owns,
            });
        }
    }

    // Reverse lookups used by source order and cycle detection.
    let mut views_by_id: HashMap<&str, &ProjectedView> = HashMap::new();
    for view in &proj.views {
        views_by_id.insert(view.id.as_str(), view);
    }
    let mut segments_by_id: HashMap<&str, &ProjectedSegment> = HashMap::new();
    for segment in &proj.segments {
        segments_by_id.insert(segment.id.as_str(), segment);
    }
    let mut references_by_id: HashMap<&str, &ProjectedReference> = HashMap::new();
    for reference in &proj.references {
        references_by_id.insert(reference.id.as_str(), reference);
    }

    // Source order: sorted views, then per-view segments by ordinal, then
    // per-view references by ordinal.
    let mut ordered_views: Vec<(usize, usize, ViewId)> = Vec::with_capacity(proj.views.len());
    for (position, view) in proj.views.iter().enumerate() {
        let source_pos = substrate
            .source_pos(&view.element_ref)
            .ok_or_else(|| missing_anchor("view", view.id.as_str(), &view.element_ref))?;
        ordered_views.push((source_pos, position, view.id.clone()));
    }
    ordered_views.sort_by(|left, right| left.0.cmp(&right.0).then(left.1.cmp(&right.1)));

    let mut source_order: Vec<NodeAddress> = Vec::new();
    for (_, _, view_id) in &ordered_views {
        source_order.push(NodeAddress::View(view_id.clone()));
    }
    for (_, _, view_id) in &ordered_views {
        let view = views_by_id
            .get(view_id.as_str())
            .ok_or_else(|| NavError::new(NavErrorKind::DanglingViewRef, "source view absent"))?;
        let mut segments: Vec<&ProjectedSegment> = Vec::new();
        for segment_id in &view.segment_refs {
            let segment = segments_by_id.get(segment_id.as_str()).ok_or_else(|| {
                NavError::new(
                    NavErrorKind::DanglingSegmentRef,
                    format!("view {view_id} segment {segment_id} is absent"),
                )
            })?;
            segments.push(segment);
        }
        segments.sort_by_key(|segment| segment.ordinal);
        for segment in segments {
            source_order.push(NodeAddress::Segment(segment.id.clone()));
        }
    }
    for (_, _, view_id) in &ordered_views {
        let view = views_by_id
            .get(view_id.as_str())
            .ok_or_else(|| NavError::new(NavErrorKind::DanglingViewRef, "source view absent"))?;
        let mut references: Vec<&ProjectedReference> = Vec::new();
        for reference_id in &view.reference_refs {
            let reference = references_by_id.get(reference_id.as_str()).ok_or_else(|| {
                NavError::new(
                    NavErrorKind::DanglingReferenceRef,
                    format!("view {view_id} reference {reference_id} is absent"),
                )
            })?;
            references.push(reference);
        }
        references.sort_by_key(|reference| reference.ordinal);
        for reference in references {
            source_order.push(NodeAddress::Reference(reference.id.clone()));
        }
    }

    // Precedes: adjacent nodes in source order.
    for pair in source_order.windows(2) {
        links.push(NavLink {
            from: pair[0].clone(),
            to: pair[1].clone(),
            kind: NavLinkKind::Precedes,
        });
    }

    // ResolvesTo (bounded note resolution) and closed unresolved reasons.
    let mut resolve_reasons: BTreeMap<ReferenceId, NavResolveReason> = BTreeMap::new();
    for reference in &proj.references {
        let from = NodeAddress::Reference(reference.id.clone());
        match substrate.resolve_reference(reference, proj) {
            Ok(view_id) => {
                links.push(NavLink {
                    from,
                    to: NodeAddress::View(view_id),
                    kind: NavLinkKind::ResolvesTo,
                });
            }
            Err(reason) => {
                resolve_reasons.insert(reference.id.clone(), reason);
            }
        }
    }

    // Fail closed on a parent_view cycle before exposing the index.
    for view in &proj.views {
        let mut visited: HashSet<&str> = HashSet::new();
        let mut current = Some(view.id.as_str());
        while let Some(id) = current {
            if !visited.insert(id) {
                return Err(NavError::new(
                    NavErrorKind::CyclicViewGraph,
                    format!("view parent cycle at {id}"),
                ));
            }
            current = views_by_id
                .get(id)
                .and_then(|view| view.parent_view.as_ref())
                .map(|parent| parent.as_str());
        }
    }

    let mut element_index: BTreeMap<ElementRef, Vec<NodeAddress>> = BTreeMap::new();
    let mut fragment_index: BTreeMap<FragmentRef, NodeAddress> = BTreeMap::new();
    for address in &record_order {
        let node = nodes_by_address
            .get(address)
            .ok_or_else(|| NavError::new(NavErrorKind::DuplicateNodeId, "node absent"))?;
        element_index
            .entry(node.element_ref.clone())
            .or_default()
            .push(address.clone());
        if let NavNodeBody::Segment {
            fragment_ref: Some(fragment),
            ..
        } = &node.body
        {
            fragment_index
                .entry(fragment.clone())
                .or_insert_with(|| address.clone());
        }
    }

    Ok(NavIndex {
        nodes_by_address,
        record_order,
        source_order,
        links,
        element_index,
        fragment_index,
        resolve_reasons,
    })
}

/// Reads a cleaned artifact back and builds the navigation index. A wire read
/// failure is surfaced as [`NavErrorKind::ArtifactUnreadable`] with the closed
/// wire kind as its detail.
pub fn build_nav_index_from_wire(artifact: &str, package: &Package) -> Result<NavIndex, NavError> {
    let cleaned = read_cleaned_wire(artifact).map_err(|error| {
        NavError::new(
            NavErrorKind::ArtifactUnreadable,
            error.kind().as_str().to_string(),
        )
    })?;
    build_nav_index(&cleaned, package)
}

// ---------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cleaned_wire::{
        WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
    };
    use crate::reader_projection::{ViewId, build_projection};
    use crate::source_package::{Limits, capture};

    const XML: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");

    fn fixture() -> (Package, CleanedProjection) {
        let package = capture(XML.as_bytes(), &Limits::default()).expect("fixture must capture");
        let projection = build_projection(package.records()).expect("projection must build");
        let artifact = render_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("render must succeed");
        let cleaned = read_cleaned_wire(&artifact).expect("read-back must succeed");
        (package, cleaned)
    }

    #[test]
    fn mixed_fixture_indexes_every_node() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        let total = cleaned.projection.views.len()
            + cleaned.projection.segments.len()
            + cleaned.projection.references.len();
        assert_eq!(index.nodes_by_address.len(), total);
        assert_eq!(index.record_order.len(), total);
        for view in &cleaned.projection.views {
            assert!(
                index.resolve(&NodeAddress::View(view.id.clone())).is_some(),
                "view {} must resolve",
                view.id
            );
        }
        for segment in &cleaned.projection.segments {
            assert!(
                index
                    .resolve(&NodeAddress::Segment(segment.id.clone()))
                    .is_some(),
                "segment {} must resolve",
                segment.id
            );
        }
        for reference in &cleaned.projection.references {
            assert!(
                index
                    .resolve(&NodeAddress::Reference(reference.id.clone()))
                    .is_some(),
                "reference {} must resolve",
                reference.id
            );
        }
    }

    #[test]
    fn footnote_reference_resolves_to_its_note_view() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        let reference = cleaned
            .projection
            .references
            .iter()
            .find(|reference| reference.element_ref.as_str() == "e41")
            .expect("e41 reference must exist");
        assert_eq!(reference.reference_type, ReaderReferenceType::NoteReference);
        assert_eq!(index.resolve_reason(&reference.id), None);
        let resolved: Vec<&NavLink> = index
            .links
            .iter()
            .filter(|link| {
                link.from == NodeAddress::Reference(reference.id.clone())
                    && link.kind == NavLinkKind::ResolvesTo
            })
            .collect();
        assert_eq!(resolved.len(), 1, "exactly one ResolvesTo link");
        let target = index.resolve(&resolved[0].to).expect("target node");
        match &target.body {
            NavNodeBody::View { view_kind, .. } => {
                assert_eq!(*view_kind, ReaderViewKind::Note);
            }
            _ => panic!("resolution target must be a view"),
        }
        assert_eq!(target.element_ref.as_str(), "e42");
    }

    #[test]
    fn second_footnote_reference_has_closed_reason() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        let reference = cleaned
            .projection
            .references
            .iter()
            .find(|reference| reference.element_ref.as_str() == "e46")
            .expect("e46 reference must exist");
        assert_eq!(reference.reference_type, ReaderReferenceType::NoteReference);
        assert_eq!(
            index.resolve_reason(&reference.id),
            Some(NavResolveReason::NoMatchingNoteDefinition)
        );
        assert!(index.links.iter().all(|link| {
            link.from != NodeAddress::Reference(reference.id.clone())
                || link.kind != NavLinkKind::ResolvesTo
        }));
    }

    #[test]
    fn non_note_references_stay_closed() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        for reference in &cleaned.projection.references {
            if matches!(
                reference.reference_type,
                ReaderReferenceType::NoteReference | ReaderReferenceType::EndnoteReference
            ) {
                continue;
            }
            assert_eq!(
                index.resolve_reason(&reference.id),
                Some(NavResolveReason::NotAResolvableReference),
                "reference {} must stay unresolved",
                reference.id
            );
        }
    }

    #[test]
    fn structural_views_and_every_link_resolve() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        for kind in [
            ReaderViewKind::Table,
            ReaderViewKind::Row,
            ReaderViewKind::Cell,
            ReaderViewKind::Note,
        ] {
            let view = cleaned
                .projection
                .views
                .iter()
                .find(|view| view.kind == kind)
                .unwrap_or_else(|| panic!("fixture must carry a {kind:?} view"));
            assert!(index.resolve(&NodeAddress::View(view.id.clone())).is_some());
        }
        for link in &index.links {
            assert!(index.resolve(&link.from).is_some(), "link source resolves");
            assert!(index.resolve(&link.to).is_some(), "link target resolves");
        }
        // The note view owns its paragraph and is reachable as a parent.
        let note = cleaned
            .projection
            .views
            .iter()
            .find(|view| view.kind == ReaderViewKind::Note)
            .expect("note view");
        let paragraph = cleaned
            .projection
            .views
            .iter()
            .find(|view| view.parent_view.as_ref() == Some(&note.id))
            .expect("paragraph under note");
        assert_eq!(
            index.parent(&NodeAddress::View(paragraph.id.clone())),
            Some(NodeAddress::View(note.id.clone()))
        );
    }

    #[test]
    fn source_order_is_deterministic_grouped_and_complete() {
        let (package, cleaned) = fixture();
        let first = build_nav_index(&cleaned, &package).expect("nav index must build");
        let second = build_nav_index(&cleaned, &package).expect("nav index must build");
        assert_eq!(first.source_order, second.source_order);

        let mut seen = BTreeSet::new();
        for address in &first.source_order {
            assert!(
                seen.insert(address.clone()),
                "source order has no duplicates"
            );
        }
        assert_eq!(seen.len(), first.nodes_by_address.len());

        let views = cleaned.projection.views.len();
        let segments = cleaned.projection.segments.len();
        assert!(
            first.source_order[..views]
                .iter()
                .all(|address| matches!(address, NodeAddress::View(_)))
        );
        assert!(
            first.source_order[views..views + segments]
                .iter()
                .all(|address| matches!(address, NodeAddress::Segment(_)))
        );
        assert!(
            first.source_order[views + segments..]
                .iter()
                .all(|address| matches!(address, NodeAddress::Reference(_)))
        );
    }

    #[test]
    fn reverse_indices_track_projection() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        for view in &cleaned.projection.views {
            assert!(
                index
                    .anchors_of_element(&view.element_ref)
                    .contains(&NodeAddress::View(view.id.clone()))
            );
        }
        for segment in &cleaned.projection.segments {
            if let Some(fragment) = &segment.fragment_ref {
                assert_eq!(
                    index.anchors_of_fragment(fragment),
                    Some(&NodeAddress::Segment(segment.id.clone()))
                );
            }
        }
        // e13 anchors both a paragraph and a cell-level residual view.
        assert!(index.anchors_of_element(&ElementRef::new("e13")).len() >= 2);
    }

    #[test]
    fn dangling_child_ref_fails_closed() {
        let (package, mut cleaned) = fixture();
        cleaned.projection.views[0]
            .children
            .push(ViewId::new("v999"));
        let error = build_nav_index(&cleaned, &package).expect_err("must fail closed");
        assert_eq!(error.kind(), NavErrorKind::DanglingViewRef);
    }

    #[test]
    fn dangling_parent_view_fails_closed() {
        let (package, mut cleaned) = fixture();
        cleaned.projection.views[0].parent_view = Some(ViewId::new("v999"));
        let error = build_nav_index(&cleaned, &package).expect_err("must fail closed");
        assert_eq!(error.kind(), NavErrorKind::DanglingParentView);
    }

    #[test]
    fn cyclic_parent_chain_fails_closed() {
        let (package, mut cleaned) = fixture();
        let first = cleaned.projection.views[0].id.clone();
        let second = cleaned.projection.views[1].id.clone();
        cleaned.projection.views[0].parent_view = Some(second);
        cleaned.projection.views[1].parent_view = Some(first);
        let error = build_nav_index(&cleaned, &package).expect_err("must fail closed");
        assert_eq!(error.kind(), NavErrorKind::CyclicViewGraph);
    }

    #[test]
    fn path_to_root_is_bounded_even_on_a_cyclic_index() {
        let (package, cleaned) = fixture();
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        // A well-formed view reaches a root and returns root-first.
        let view = cleaned
            .projection
            .views
            .iter()
            .find(|view| view.kind == ReaderViewKind::Paragraph)
            .expect("paragraph view");
        let path = index.path_to_root(&NodeAddress::View(view.id.clone()));
        assert_eq!(path.last(), Some(&NodeAddress::View(view.id.clone())));
        assert!(path.len() <= index.nodes_by_address.len());
    }

    #[test]
    fn inline_endnote_reference_resolves() {
        const ENDNOTE_XML: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>x</w:t></w:r></w:p><w:endnoteReference w:id="7"/><w:endnote w:id="7"><w:p><w:r><w:t>y</w:t></w:r></w:p></w:endnote></w:body></w:wordDocument>"#;
        let package = capture(ENDNOTE_XML.as_bytes(), &Limits::default()).expect("inline capture");
        let projection = build_projection(package.records()).expect("projection must build");
        let artifact = render_cleaned_projection(
            &package,
            &projection,
            &WireCompletion::Complete,
            &WireLimits::default(),
        )
        .expect("render must succeed");
        let cleaned = read_cleaned_wire(&artifact).expect("read-back must succeed");
        let index = build_nav_index(&cleaned, &package).expect("nav index must build");
        let reference = cleaned
            .projection
            .references
            .iter()
            .find(|reference| reference.reference_type == ReaderReferenceType::EndnoteReference)
            .expect("endnote reference must exist");
        assert_eq!(index.resolve_reason(&reference.id), None);
        let target = index
            .links
            .iter()
            .find(|link| {
                link.from == NodeAddress::Reference(reference.id.clone())
                    && link.kind == NavLinkKind::ResolvesTo
            })
            .expect("endnote must resolve");
        let node = index.resolve(&target.to).expect("target node");
        match &node.body {
            NavNodeBody::View { view_kind, .. } => {
                assert_eq!(*view_kind, ReaderViewKind::Note);
            }
            _ => panic!("resolution target must be a view"),
        }
    }

    #[test]
    fn unreadable_artifact_is_closed() {
        let (package, _) = fixture();
        let error = build_nav_index_from_wire("not a cleaned artifact", &package)
            .expect_err("must fail closed");
        assert_eq!(error.kind(), NavErrorKind::ArtifactUnreadable);
        assert!(!error.detail().is_empty());
    }

    #[test]
    fn diagnostics_carry_no_decoded_text() {
        let (package, mut cleaned) = fixture();
        cleaned.projection.views[0]
            .children
            .push(ViewId::new("v999"));
        let error = build_nav_index(&cleaned, &package).expect_err("must fail closed");
        for needle in ["Alpha", "Beta", "Gamma", "Epsilon", "Lambda"] {
            assert!(
                !error.detail().contains(needle),
                "diagnostic leaked decoded text"
            );
        }
        assert!(error.detail().contains("v999"));
    }
}
