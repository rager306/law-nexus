//! Independent verifier for the S03 reader projection.
//!
//! This module is the verifier half of
//! `prd/architecture/reader-projection-contract.md` (pinned provider profile
//! `reader_wordml_profile/v1`). It recomputes the expected view forest, the
//! document-event order and the fragment ownership from the frozen substrate
//! using only the S02 `crate::reader_contract` primitives — never the projection
//! builder. In particular it does **not** call
//! `crate::reader_projection::build_projection`, never trusts the record stream,
//! and never reads `ReaderProjection::content_hash`: a re-sealed semantic tamper
//! must still be caught.
//!
//! The module is serialization-agnostic: it does not import `serde` or any JSON
//! crate, so the verifier cannot be fooled by a canonical representation the
//! builder produced.
//!
//! Non-claims: raw decoded text without normalization; no XML byte coordinates;
//! no temporal `StructuralAst`/CST/CTV; provider-bounded Consultant WordML; no
//! R1000 closure and no legal-completeness claim.

use std::collections::hash_map::Entry;
use std::collections::{HashMap, HashSet};

use crate::reader_contract::{
    check_fragment_span, control_derived_kind, partition_primary_views, reference_type_of,
    tail_view_key, view_key, ElementRef, ReaderDerivedKind, ReaderRecordIndex, ReaderReferenceType,
    ReaderRole, ReaderSegmentKind, ReaderSemantic, ReaderViewKey, ReaderViewKind,
};
use crate::reader_projection::{
    ProjectedReference, ProjectedSegment, ReaderProjection, SegmentOrigin,
};
use crate::source_package::{ElementRecord, Record, TextSlot};

// ------------------------------------------------------------------- codes #

/// Closed verifier finding vocabulary. A finding names one concrete invariant
/// the projection violated; it never carries a legal claim.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum VerifyCode {
    /// The projection carries a view the substrate does not warrant.
    ViewUnexpected,
    /// The substrate warrants a view the projection does not carry.
    ViewMissing,
    /// The view's `parent_view` is not the nearest valid container.
    ViewParentMismatch,
    /// The view's `children` are not the substrate children in order.
    ViewChildrenMismatch,
    /// The view's `flags.empty` disagrees with its content.
    ViewEmptyFlagMismatch,
    /// A `segment_ref` does not resolve to a segment owned by that view.
    SegmentRefDangling,
    /// A view's ordered segment list differs from the document-event order.
    SegmentMembershipOrOrderMismatch,
    /// A source segment's span is absent or not the whole validated fragment.
    SegmentSourceMismatch,
    /// A source segment's owner element / `source_pos` is not the fragment owner.
    SegmentOwnerMismatch,
    /// A derived segment's element is not a documented control of that kind.
    DerivedNotControl,
    /// A derived segment's literal / semantic / flags disagree with the control.
    DerivedRenderMismatch,
    /// A derived segment carries a source fragment or span it cannot have.
    DerivedInventedSourceSpan,
    /// A view's ordered reference list differs from the document-event order.
    ReferenceMembershipMismatch,
    /// A reference record claims to be resolved.
    ReferenceResolved,
    /// The same substrate fragment is referenced by more than one source segment.
    DuplicateFragmentReference,
    /// A source segment references a fragment absent from the substrate.
    DanglingFragmentReference,
    /// A substrate text record is referenced by no source segment.
    MissingFragmentReference,
    /// A source segment was projected into a view other than its owner view.
    FragmentInWrongView,
    /// The substrate records are internally inconsistent and cannot be walked.
    SubstrateMalformed,
}

impl VerifyCode {
    /// Closed string form used in diagnostics.
    pub const fn as_str(self) -> &'static str {
        match self {
            VerifyCode::ViewUnexpected => "view_unexpected",
            VerifyCode::ViewMissing => "view_missing",
            VerifyCode::ViewParentMismatch => "view_parent_mismatch",
            VerifyCode::ViewChildrenMismatch => "view_children_mismatch",
            VerifyCode::ViewEmptyFlagMismatch => "view_empty_flag_mismatch",
            VerifyCode::SegmentRefDangling => "segment_ref_dangling",
            VerifyCode::SegmentMembershipOrOrderMismatch => "segment_membership_or_order_mismatch",
            VerifyCode::SegmentSourceMismatch => "segment_source_mismatch",
            VerifyCode::SegmentOwnerMismatch => "segment_owner_mismatch",
            VerifyCode::DerivedNotControl => "derived_not_control",
            VerifyCode::DerivedRenderMismatch => "derived_render_mismatch",
            VerifyCode::DerivedInventedSourceSpan => "derived_invented_source_span",
            VerifyCode::ReferenceMembershipMismatch => "reference_membership_mismatch",
            VerifyCode::ReferenceResolved => "reference_resolved",
            VerifyCode::DuplicateFragmentReference => "duplicate_fragment_reference",
            VerifyCode::DanglingFragmentReference => "dangling_fragment_reference",
            VerifyCode::MissingFragmentReference => "missing_fragment_reference",
            VerifyCode::FragmentInWrongView => "fragment_in_wrong_view",
            VerifyCode::SubstrateMalformed => "substrate_malformed",
        }
    }
}

/// One typed projection defect. `detail` is for diagnostics only and is never
/// parsed.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerifyFinding {
    pub code: VerifyCode,
    pub detail: String,
}

impl VerifyFinding {
    /// Builds a finding from a code and a human-readable detail.
    pub fn new(code: VerifyCode, detail: impl Into<String>) -> Self {
        VerifyFinding {
            code,
            detail: detail.into(),
        }
    }
}

// ---------------------------------------------------------------- expected #

/// Expected segment in document-event order.
enum ExpectedSegment {
    /// A source segment naming one substrate text record.
    Source(String),
    /// A derived segment generated from a documented control.
    Derived(ReaderDerivedKind),
}

/// One expected view recomputed from the substrate.
struct ExpectedView {
    parent: Option<ReaderViewKey>,
    children: Vec<ReaderViewKey>,
    segments: Vec<ExpectedSegment>,
    references: Vec<ReaderReferenceType>,
}

/// Independently recomputed projection model.
struct Expected {
    views: HashMap<ReaderViewKey, ExpectedView>,
    /// Expected primary view for every substrate text record.
    fragment_view: HashMap<String, ReaderViewKey>,
}

// ------------------------------------------------------------ substrate walk #

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

/// Deterministic rank used to order views sharing a `source_pos`.
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

/// Parent container roles for a view kind.
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

fn role_of(index: &ReaderRecordIndex, id: &str) -> Result<ReaderRole, String> {
    index
        .role_of(id)
        .ok_or_else(|| format!("element {id} has no role in the substrate index"))
}

fn add_seed(
    seeds: &mut Vec<(ReaderViewKind, ElementRef, usize)>,
    seen: &mut HashSet<(ReaderViewKind, String)>,
    index: &ReaderRecordIndex,
    kind: ReaderViewKind,
    eid: &str,
) -> Result<(), String> {
    let source_pos = index
        .source_pos(eid)
        .ok_or_else(|| format!("view element {eid} is missing from the substrate index"))?;
    if seen.insert((kind, eid.to_string())) {
        seeds.push((kind, ElementRef::new(eid), source_pos));
    }
    Ok(())
}

/// Nearest ancestor whose role is one of `allowed`, walked on the real `parent`
/// chain (starting from the element's parent, never itself).
fn nearest_container(
    index: &ReaderRecordIndex,
    element_ref: &ElementRef,
    allowed: &[ReaderRole],
) -> Result<Option<ElementRef>, String> {
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

/// Clark namespace of a tag (`{ns}local`), or `None` for an unbound name.
fn clark_namespace(clark_tag: &str) -> Option<&str> {
    let rest = clark_tag.strip_prefix('{')?;
    let close = rest.find('}')?;
    Some(&rest[..close])
}

/// True when `element_id` is a maximal `unknown` / `foreign` subtree root.
fn unknown_or_foreign_boundary(
    index: &ReaderRecordIndex,
    element_id: &str,
) -> Result<bool, String> {
    let element = index
        .element(element_id)
        .ok_or_else(|| format!("element {element_id} is missing from the substrate index"))?;
    let Some(parent_id) = &element.parent else {
        return Ok(true);
    };
    let parent = index
        .element(parent_id)
        .ok_or_else(|| format!("element {parent_id} is missing from the substrate index"))?;
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
) -> Result<bool, String> {
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

/// Recompute semantic context from substrate coordinates, independently of the
/// projection: tails start at the capture owner's parent; text starts at owner.
fn text_semantic(
    index: &ReaderRecordIndex,
    owner: &str,
    slot: TextSlot,
    value: &str,
) -> Result<ReaderSemantic, String> {
    let element = index
        .element(owner)
        .ok_or_else(|| format!("text owner {owner} is missing from the substrate index"))?;
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

/// A single ordered event reconstructed from the substrate records.
enum Event {
    Fragment {
        fragment_id: String,
        view: ReaderViewKey,
    },
    Control {
        kind: ReaderDerivedKind,
        view: ReaderViewKey,
    },
    Reference {
        reference_type: ReaderReferenceType,
        view: ReaderViewKey,
    },
}

impl Event {
    fn view_key(&self) -> &ReaderViewKey {
        match self {
            Event::Fragment { view, .. }
            | Event::Control { view, .. }
            | Event::Reference { view, .. } => view,
        }
    }
}

/// Reconstructs the ordered document events from substrate records only,
/// mirroring the `capture` pre-order (own `text_ref`, control/reference, children
/// in document order, then each child's `tail_ref`). It never re-parses XML.
fn document_events(index: &ReaderRecordIndex) -> Result<Vec<Event>, String> {
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

    let mut events: Vec<Event> = Vec::new();
    let mut stack: Vec<Step<'_>> = roots.iter().rev().map(|root| Step::Node(root)).collect();
    while let Some(step) = stack.pop() {
        match step {
            Step::Node(element) => {
                let role = role_of(index, &element.id)?;
                if let Some(text_ref) = &element.text_ref {
                    events.push(Event::Fragment {
                        fragment_id: text_ref.clone(),
                        view: view_key(index, &ElementRef::new(element.id.as_str()))
                            .map_err(|error| error.detail().to_string())?,
                    });
                }
                if role == ReaderRole::Control && element.text_ref.is_none() {
                    if let Some(kind) = control_derived_kind(&element.clark_tag, &element.attrs) {
                        events.push(Event::Control {
                            kind,
                            view: view_key(index, &ElementRef::new(element.id.as_str()))
                                .map_err(|error| error.detail().to_string())?,
                        });
                    }
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
                    if is_boundary {
                        if let Some(reference_type) =
                            reference_type_of(&element.clark_tag, &element.attrs)
                        {
                            events.push(Event::Reference {
                                reference_type,
                                view: view_key(index, &ElementRef::new(element.id.as_str()))
                                    .map_err(|error| error.detail().to_string())?,
                            });
                        }
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
                    events.push(Event::Fragment {
                        fragment_id: tail_ref.clone(),
                        view: tail_view_key(index, &ElementRef::new(element.id.as_str()))
                            .map_err(|error| error.detail().to_string())?,
                    });
                }
            }
        }
    }
    Ok(events)
}

/// Recomputes the expected view forest, ordered segment lists and reference
/// lists from the substrate alone.
fn build_expected(index: &ReaderRecordIndex) -> Result<Expected, String> {
    let mut seeds: Vec<(ReaderViewKind, ElementRef, usize)> = Vec::new();
    let mut seen: HashSet<(ReaderViewKind, String)> = HashSet::new();

    // 1. Structural views.
    for element in index.elements() {
        let role = role_of(index, &element.id)?;
        if let Some(kind) = structural_view_kind(role) {
            add_seed(&mut seeds, &mut seen, index, kind, &element.id)?;
        }
    }

    // 2. Residual anchors owned by a text record.
    let partition = partition_primary_views(index).map_err(|error| error.detail().to_string())?;
    for entry in &partition.entries {
        if entry.view.kind == ReaderViewKind::Residual {
            add_seed(
                &mut seeds,
                &mut seen,
                index,
                ReaderViewKind::Residual,
                entry.view.element_ref.as_str(),
            )?;
        }
    }

    // 3. Residual anchors owned by a control / reference element.
    for element in index.elements() {
        let role = role_of(index, &element.id)?;
        if matches!(
            role,
            ReaderRole::Control
                | ReaderRole::NoteReference
                | ReaderRole::Field
                | ReaderRole::Unknown
                | ReaderRole::Foreign
        ) {
            let key = view_key(index, &ElementRef::new(element.id.as_str()))
                .map_err(|error| error.detail().to_string())?;
            if key.kind == ReaderViewKind::Residual {
                add_seed(
                    &mut seeds,
                    &mut seen,
                    index,
                    ReaderViewKind::Residual,
                    key.element_ref.as_str(),
                )?;
            }
        }
    }

    seeds.sort_by(|a, b| {
        a.2.cmp(&b.2)
            .then_with(|| view_kind_rank(a.0).cmp(&view_kind_rank(b.0)))
            .then_with(|| a.1.as_str().cmp(b.1.as_str()))
    });

    let mut views: HashMap<ReaderViewKey, ExpectedView> = HashMap::new();
    let mut source_pos_of: HashMap<ReaderViewKey, usize> = HashMap::new();
    let mut keys: Vec<ReaderViewKey> = Vec::with_capacity(seeds.len());
    for (kind, element_ref, source_pos) in &seeds {
        let key = ReaderViewKey::new(*kind, element_ref.clone());
        source_pos_of.insert(key.clone(), *source_pos);
        keys.push(key.clone());
        views.insert(
            key,
            ExpectedView {
                parent: None,
                children: Vec::new(),
                segments: Vec::new(),
                references: Vec::new(),
            },
        );
    }

    // Parent = nearest valid container on the real parent chain.
    for key in &keys {
        let container = nearest_container(index, &key.element_ref, parent_roles(key.kind))?;
        if let Some(container_ref) = container {
            let role = role_of(index, container_ref.as_str())?;
            let kind = structural_view_kind(role)
                .ok_or_else(|| format!("container {container_ref} has no view kind"))?;
            let parent_key = ReaderViewKey::new(kind, container_ref);
            if !views.contains_key(&parent_key) {
                return Err(format!(
                    "parent view {} {} is missing",
                    parent_key.kind.as_str(),
                    parent_key.element_ref
                ));
            }
            if let Some(view) = views.get_mut(key) {
                view.parent = Some(parent_key);
            }
        }
    }

    // Children ordered by source_pos, then kind rank.
    let mut child_pairs: HashMap<ReaderViewKey, Vec<(usize, u8, String, ReaderViewKey)>> =
        HashMap::new();
    for key in &keys {
        if let Some(parent) = views.get(key).and_then(|view| view.parent.clone()) {
            let pos = source_pos_of.get(key).copied().unwrap_or(usize::MAX);
            child_pairs.entry(parent).or_default().push((
                pos,
                view_kind_rank(key.kind),
                key.element_ref.as_str().to_string(),
                key.clone(),
            ));
        }
    }
    for (parent, mut kids) in child_pairs {
        kids.sort_by(|a, b| {
            a.0.cmp(&b.0)
                .then_with(|| a.1.cmp(&b.1))
                .then_with(|| a.2.cmp(&b.2))
        });
        if let Some(view) = views.get_mut(&parent) {
            view.children = kids.into_iter().map(|(_, _, _, key)| key).collect();
        }
    }

    // Ordered segments / references per ownership view.
    for event in document_events(index)? {
        let key = event.view_key().clone();
        let view = views.get_mut(&key).ok_or_else(|| {
            format!(
                "event view {} {} is missing",
                key.kind.as_str(),
                key.element_ref
            )
        })?;
        match event {
            Event::Fragment { fragment_id, .. } => {
                view.segments.push(ExpectedSegment::Source(fragment_id))
            }
            Event::Control { kind, .. } => view.segments.push(ExpectedSegment::Derived(kind)),
            Event::Reference { reference_type, .. } => view.references.push(reference_type),
        }
    }

    let mut fragment_view: HashMap<String, ReaderViewKey> = HashMap::new();
    for entry in &partition.entries {
        fragment_view.insert(entry.fragment.as_str().to_string(), entry.view.clone());
    }

    Ok(Expected {
        views,
        fragment_view,
    })
}

// ------------------------------------------------------------- verifying #

fn expected_segment_token(segment: &ExpectedSegment) -> String {
    match segment {
        ExpectedSegment::Source(fragment) => fragment.clone(),
        ExpectedSegment::Derived(kind) => format!("derived:{}", kind.as_str()),
    }
}

fn actual_segment_token(segment: &ProjectedSegment) -> String {
    match segment.origin {
        SegmentOrigin::SourceFragment => segment
            .fragment_ref
            .as_ref()
            .map(|fragment| fragment.as_str().to_string())
            .unwrap_or_else(|| "source:<missing-fragment>".to_string()),
        SegmentOrigin::Derived(kind) => format!("derived:{}", kind.as_str()),
    }
}

/// Checks one source-fragment segment against the substrate and the mandatory
/// whole-fragment span re-validation.
fn verify_source_segment(
    segment: &ProjectedSegment,
    index: &ReaderRecordIndex,
    findings: &mut Vec<VerifyFinding>,
) {
    if segment.segment_kind != ReaderSegmentKind::Text {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!("{}: source origin is not a text segment", segment.id),
        ));
    }
    let Some(fragment_ref) = &segment.fragment_ref else {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!(
                "{}: source segment without a fragment reference",
                segment.id
            ),
        ));
        return;
    };
    let Some(text) = index.text(fragment_ref.as_str()) else {
        findings.push(VerifyFinding::new(
            VerifyCode::DanglingFragmentReference,
            format!(
                "{}: fragment {} is not a substrate text record",
                segment.id, fragment_ref
            ),
        ));
        return;
    };
    let value = text.value.as_str();

    let span_ok = match &segment.span {
        None => false,
        Some(span) => {
            span.fragment == *fragment_ref
                && span.start == 0
                && span.end == value.len()
                && check_fragment_span(value, span).is_ok()
        }
    };
    if !span_ok {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!(
                "{}: source span is absent or not the validated whole fragment {}",
                segment.id, fragment_ref
            ),
        ));
    }

    if segment.slot != Some(text.slot) {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!("{}: source slot is not the substrate slot", segment.id),
        ));
    }
    if segment.text.is_some() {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!(
                "{}: source segment must not carry a rendered literal",
                segment.id
            ),
        ));
    }
    match text_semantic(index, &text.owner, text.slot, value) {
        Ok(semantic) => {
            if segment.semantic != semantic
                || segment.contextual != (semantic != ReaderSemantic::Body)
            {
                findings.push(VerifyFinding::new(
                    VerifyCode::SegmentSourceMismatch,
                    format!(
                        "{}: semantic/contextual disagrees with the substrate owner",
                        segment.id
                    ),
                ));
            }
        }
        Err(detail) => findings.push(VerifyFinding::new(VerifyCode::SubstrateMalformed, detail)),
    }
    if segment.element_ref.as_str() != text.owner {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentOwnerMismatch,
            format!(
                "{}: owner {} is not the fragment owner {}",
                segment.id, segment.element_ref, text.owner
            ),
        ));
    }
    if index.source_pos(text.owner.as_str()) != Some(segment.source_pos) {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentOwnerMismatch,
            format!("{}: source_pos is not the owner source_pos", segment.id),
        ));
    }
    if segment.chars != value.chars().count() {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!("{}: chars is not the decoded code-point count", segment.id),
        ));
    }
}

/// Checks one derived segment against the documented control vocabulary.
fn verify_derived_segment(
    segment: &ProjectedSegment,
    expected_kind: ReaderDerivedKind,
    index: &ReaderRecordIndex,
    findings: &mut Vec<VerifyFinding>,
) {
    if segment.segment_kind != ReaderSegmentKind::Derived {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!("{}: derived origin is not a derived segment", segment.id),
        ));
    }
    if segment.fragment_ref.is_some() || segment.span.is_some() {
        findings.push(VerifyFinding::new(
            VerifyCode::DerivedInventedSourceSpan,
            format!(
                "{}: derived segment carries a source fragment or span",
                segment.id
            ),
        ));
    }
    if segment.slot.is_some() {
        findings.push(VerifyFinding::new(
            VerifyCode::SegmentSourceMismatch,
            format!(
                "{}: derived segment must not carry a source slot",
                segment.id
            ),
        ));
    }

    let mut control_ok = false;
    if let Some(element) = index.element(segment.element_ref.as_str()) {
        let role_ok = index.role_of(&element.id) == Some(ReaderRole::Control);
        let kind_ok =
            control_derived_kind(&element.clark_tag, &element.attrs) == Some(expected_kind);
        control_ok = role_ok && kind_ok;
    }
    if !control_ok {
        findings.push(VerifyFinding::new(
            VerifyCode::DerivedNotControl,
            format!(
                "{}: element {} is not a documented {} control",
                segment.id,
                segment.element_ref,
                expected_kind.as_str()
            ),
        ));
    }

    let literal = expected_kind.literal();
    let render_ok = segment.text.as_deref() == Some(literal)
        && segment.chars == literal.chars().count()
        && segment.semantic == ReaderSemantic::DerivedSeparator
        && segment.contextual;
    if !render_ok {
        findings.push(VerifyFinding::new(
            VerifyCode::DerivedRenderMismatch,
            format!(
                "{}: derived literal/semantic/flags disagree with the control",
                segment.id
            ),
        ));
    }
}

/// Compares the view forest and per-view membership/order.
fn verify_view_forest(
    projection: &ReaderProjection,
    expected: &Expected,
    id_to_key: &HashMap<&str, ReaderViewKey>,
    segment_by_id: &HashMap<&str, &ProjectedSegment>,
    reference_by_id: &HashMap<&str, &ProjectedReference>,
    findings: &mut Vec<VerifyFinding>,
) {
    let mut actual_by_key: HashMap<
        (ReaderViewKind, String),
        &crate::reader_projection::ProjectedView,
    > = HashMap::new();
    for view in &projection.views {
        let key = (view.kind, view.element_ref.as_str().to_string());
        match actual_by_key.entry(key) {
            Entry::Occupied(_) => {
                findings.push(VerifyFinding::new(
                    VerifyCode::ViewUnexpected,
                    format!("duplicate view {} {}", view.kind.as_str(), view.element_ref),
                ));
            }
            Entry::Vacant(slot) => {
                slot.insert(view);
            }
        }
    }

    for view in &projection.views {
        let key = (view.kind, view.element_ref.as_str().to_string());
        if !expected
            .views
            .contains_key(&ReaderViewKey::new(view.kind, view.element_ref.clone()))
        {
            findings.push(VerifyFinding::new(
                VerifyCode::ViewUnexpected,
                format!(
                    "view {} {} is not warranted",
                    view.kind.as_str(),
                    view.element_ref
                ),
            ));
        }
        let _ = key;
    }

    for (key, expected_view) in &expected.views {
        let actual = actual_by_key.get(&(key.kind, key.element_ref.as_str().to_string()));
        let Some(actual) = actual else {
            findings.push(VerifyFinding::new(
                VerifyCode::ViewMissing,
                format!(
                    "expected view {} {} is absent",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
            continue;
        };

        // Parent.
        let parent_dangling = actual.parent_view.is_some()
            && actual
                .parent_view
                .as_ref()
                .and_then(|id| id_to_key.get(id.as_str()))
                .is_none();
        let actual_parent = actual
            .parent_view
            .as_ref()
            .and_then(|id| id_to_key.get(id.as_str()))
            .cloned();
        if parent_dangling || actual_parent != expected_view.parent {
            findings.push(VerifyFinding::new(
                VerifyCode::ViewParentMismatch,
                format!(
                    "view {} {} has the wrong parent_view",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
        }

        // Children.
        let actual_children: Vec<ReaderViewKey> = actual
            .children
            .iter()
            .filter_map(|id| id_to_key.get(id.as_str()).cloned())
            .collect();
        if actual_children.len() != actual.children.len()
            || actual_children != expected_view.children
        {
            findings.push(VerifyFinding::new(
                VerifyCode::ViewChildrenMismatch,
                format!(
                    "view {} {} has the wrong children",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
        }

        // Empty flag.
        let expected_empty = if key.kind.is_primary() {
            expected_view.segments.is_empty()
        } else {
            expected_view.children.is_empty()
        };
        if actual.flags.empty != expected_empty {
            findings.push(VerifyFinding::new(
                VerifyCode::ViewEmptyFlagMismatch,
                format!(
                    "view {} {} flags.empty is {}, expected {}",
                    key.kind.as_str(),
                    key.element_ref,
                    actual.flags.empty,
                    expected_empty
                ),
            ));
        }

        // Segment membership / order.
        let mut dangling_ref = false;
        let mut actual_tokens: Vec<String> = Vec::new();
        for segment_id in &actual.segment_refs {
            match segment_by_id.get(segment_id.as_str()) {
                Some(segment) if segment.view == actual.id => {
                    actual_tokens.push(actual_segment_token(segment));
                }
                _ => dangling_ref = true,
            }
        }
        if dangling_ref {
            findings.push(VerifyFinding::new(
                VerifyCode::SegmentRefDangling,
                format!(
                    "view {} {} has a dangling segment_ref",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
        }
        let expected_tokens: Vec<String> = expected_view
            .segments
            .iter()
            .map(expected_segment_token)
            .collect();
        if actual_tokens != expected_tokens {
            findings.push(VerifyFinding::new(
                VerifyCode::SegmentMembershipOrOrderMismatch,
                format!(
                    "view {} {} segment order differs from the document-event order",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
        }

        // Reference membership / order.
        let mut reference_ok = true;
        let mut actual_types: Vec<ReaderReferenceType> = Vec::new();
        for reference_id in &actual.reference_refs {
            match reference_by_id.get(reference_id.as_str()) {
                Some(reference) if reference.view == actual.id => {
                    actual_types.push(reference.reference_type);
                }
                _ => reference_ok = false,
            }
        }
        if !reference_ok || actual_types != expected_view.references {
            findings.push(VerifyFinding::new(
                VerifyCode::ReferenceMembershipMismatch,
                format!(
                    "view {} {} reference order differs from the document-event order",
                    key.kind.as_str(),
                    key.element_ref
                ),
            ));
        }
    }
}

/// Compares fragment coverage / ownership and reference resolution.
fn verify_coverage(
    projection: &ReaderProjection,
    index: &ReaderRecordIndex,
    expected: &Expected,
    id_to_key: &HashMap<&str, ReaderViewKey>,
    findings: &mut Vec<VerifyFinding>,
) {
    // Duplicate and dangling source references.
    let mut counts: HashMap<&str, usize> = HashMap::new();
    let mut covered: HashSet<&str> = HashSet::new();
    for segment in &projection.segments {
        if segment.origin != SegmentOrigin::SourceFragment {
            continue;
        }
        if let Some(fragment) = &segment.fragment_ref {
            *counts.entry(fragment.as_str()).or_insert(0) += 1;
            covered.insert(fragment.as_str());
        }
    }
    for (fragment, count) in &counts {
        if *count > 1 {
            findings.push(VerifyFinding::new(
                VerifyCode::DuplicateFragmentReference,
                format!("fragment {fragment} is referenced {count} times"),
            ));
        }
        if index.text(fragment).is_none() {
            findings.push(VerifyFinding::new(
                VerifyCode::DanglingFragmentReference,
                format!("fragment {fragment} is not a substrate text record"),
            ));
        }
    }
    for text in index.texts() {
        if !covered.contains(text.id.as_str()) {
            findings.push(VerifyFinding::new(
                VerifyCode::MissingFragmentReference,
                format!(
                    "substrate text {} is referenced by no source segment",
                    text.id
                ),
            ));
        }
    }

    // Ownership: each source segment must sit in its expected owner view.
    for segment in &projection.segments {
        if segment.origin != SegmentOrigin::SourceFragment {
            continue;
        }
        let Some(fragment) = &segment.fragment_ref else {
            continue;
        };
        let Some(expected_key) = expected.fragment_view.get(fragment.as_str()) else {
            continue;
        };
        if let Some(actual_key) = id_to_key.get(segment.view.as_str()) {
            if actual_key != expected_key {
                findings.push(VerifyFinding::new(
                    VerifyCode::FragmentInWrongView,
                    format!(
                        "{}: fragment {} belongs to view {} {} but is in view {} {}",
                        segment.id,
                        fragment,
                        expected_key.kind.as_str(),
                        expected_key.element_ref,
                        actual_key.kind.as_str(),
                        actual_key.element_ref
                    ),
                ));
            }
        }
    }

    // References are always unresolved in S03.
    for reference in &projection.references {
        if reference.resolved {
            findings.push(VerifyFinding::new(
                VerifyCode::ReferenceResolved,
                format!("reference {} claims to be resolved", reference.id),
            ));
        }
    }
}

/// Independently verifies a projection against the substrate it was built from.
///
/// Returns `Ok(())` when the projection is a faithful, document-ordered,
/// coverage-total representation, or `Err(findings)` with one typed
/// [`VerifyFinding`] per violated invariant. The verifier never reads
/// `projection.content_hash`, so a re-sealed semantic tamper is still caught.
pub fn verify_projection(
    projection: &ReaderProjection,
    records: &[Record],
) -> Result<(), Vec<VerifyFinding>> {
    let index = match ReaderRecordIndex::new(records) {
        Ok(index) => index,
        Err(error) => {
            return Err(vec![VerifyFinding::new(
                VerifyCode::SubstrateMalformed,
                error.detail().to_string(),
            )]);
        }
    };

    let expected = match build_expected(&index) {
        Ok(expected) => expected,
        Err(detail) => {
            return Err(vec![VerifyFinding::new(
                VerifyCode::SubstrateMalformed,
                detail,
            )])
        }
    };

    let mut findings: Vec<VerifyFinding> = Vec::new();

    let id_to_key: HashMap<&str, ReaderViewKey> = projection
        .views
        .iter()
        .map(|view| {
            (
                view.id.as_str(),
                ReaderViewKey::new(view.kind, view.element_ref.clone()),
            )
        })
        .collect();
    let segment_by_id: HashMap<&str, &ProjectedSegment> = projection
        .segments
        .iter()
        .map(|segment| (segment.id.as_str(), segment))
        .collect();
    let reference_by_id: HashMap<&str, &ProjectedReference> = projection
        .references
        .iter()
        .map(|reference| (reference.id.as_str(), reference))
        .collect();

    verify_view_forest(
        projection,
        &expected,
        &id_to_key,
        &segment_by_id,
        &reference_by_id,
        &mut findings,
    );

    for segment in &projection.segments {
        match segment.origin {
            SegmentOrigin::SourceFragment => verify_source_segment(segment, &index, &mut findings),
            SegmentOrigin::Derived(kind) => {
                verify_derived_segment(segment, kind, &index, &mut findings)
            }
        }
    }

    verify_coverage(projection, &index, &expected, &id_to_key, &mut findings);

    if findings.is_empty() {
        Ok(())
    } else {
        Err(findings)
    }
}

// -------------------------------------------------------------------- tests #

#[cfg(test)]
mod tests {
    use super::*;
    use crate::reader_contract::{ContractErrorKind, ReaderFragmentSpan};
    use crate::reader_projection::{build_projection, SegmentId, ViewId};
    use crate::source_package::{capture, Limits, TextRecord, TextSlot};
    use std::collections::BTreeMap;

    const NS: &str = "{http://schemas.microsoft.com/office/word/2003/wordml}";
    const FIXTURE: &str = include_str!("../tests/fixtures/reader/mixed-wordml.xml");

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

    fn fixture_records() -> Vec<Record> {
        let package = capture(FIXTURE.as_bytes(), &Limits::default()).expect("fixture captures");
        package.records().to_vec()
    }

    fn codes(findings: &[VerifyFinding]) -> Vec<VerifyCode> {
        findings.iter().map(|finding| finding.code).collect()
    }

    fn find_segment<'a>(projection: &'a ReaderProjection, fragment: &str) -> &'a ProjectedSegment {
        projection
            .segments
            .iter()
            .find(|segment| segment.fragment_ref.as_ref().map(|f| f.as_str()) == Some(fragment))
            .unwrap_or_else(|| panic!("segment for fragment {fragment} missing"))
    }

    #[test]
    fn verifier_source_is_independent_of_the_builder() {
        let source = include_str!("reader_verifier.rs");
        let cut = source.find("mod tests").expect("tests module");
        // Ignore comment lines: the module doc explains the independence by
        // naming the builder, but the executable verifier must not call it.
        let code: String = source[..cut]
            .lines()
            .filter(|line| !line.trim_start().starts_with("//"))
            .collect::<Vec<_>>()
            .join("\n");
        assert!(
            !code.contains("build_projection"),
            "the verifier must not call the projection builder"
        );
    }

    #[test]
    fn untampered_synthetic_projection_verifies_ok() {
        let records = synthetic();
        let projection = build_projection(&records).expect("projection builds");
        assert!(verify_projection(&projection, &records).is_ok());
    }

    #[test]
    fn untampered_fixture_projection_verifies_ok() {
        let records = fixture_records();
        let projection = build_projection(&records).expect("projection builds");
        if let Err(findings) = verify_projection(&projection, &records) {
            panic!("untampered fixture must verify: {findings:?}");
        }
    }

    #[test]
    fn verifier_ignores_the_content_seal() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        projection.reseal();
        let mut resealed = projection.clone();
        // A bogus but plausible-looking seal must not influence verification.
        resealed.content_hash = Some("0".repeat(64));
        assert!(verify_projection(&resealed, &records).is_ok());
        assert_ne!(resealed.content_hash, projection.content_hash);
    }

    #[test]
    fn dropped_segment_is_reported_as_missing_fragment() {
        let records = synthetic();
        let mut projection = build_projection(&records).expect("projection builds");
        let victim = find_segment(&projection, "t0").id.clone();
        projection.segments.retain(|segment| segment.id != victim);
        for view in &mut projection.views {
            view.segment_refs.retain(|id| id != &victim);
        }
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::MissingFragmentReference));
    }

    #[test]
    fn reassigned_fragment_is_reported_as_wrong_view() {
        let records = synthetic();
        let mut projection = build_projection(&records).expect("projection builds");
        let victim = find_segment(&projection, "t0").id.clone();
        for view in &mut projection.views {
            view.segment_refs.retain(|id| id != &victim);
        }
        // Move t0 from its paragraph view into the cell residual view.
        for segment in &mut projection.segments {
            if segment.id == victim {
                segment.view = ViewId::from("v5");
            }
        }
        for view in &mut projection.views {
            if view.element_ref.as_str() == "e11" && view.kind == ReaderViewKind::Residual {
                view.segment_refs.push(SegmentId::from(victim.as_str()));
            }
        }
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::FragmentInWrongView));
    }

    #[test]
    fn promoted_derived_segment_is_reported_as_source_mismatch() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        let derived_index = projection
            .segments
            .iter()
            .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
            .expect("fixture carries derived controls");
        let segment = &mut projection.segments[derived_index];
        segment.origin = SegmentOrigin::SourceFragment;
        segment.segment_kind = ReaderSegmentKind::Text;
        segment.text = None;
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::SegmentSourceMismatch));
    }

    #[test]
    fn derived_invented_span_is_reported() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        let derived_index = projection
            .segments
            .iter()
            .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
            .expect("fixture carries derived controls");
        let segment = &mut projection.segments[derived_index];
        segment.span = Some(ReaderFragmentSpan::new(
            crate::reader_contract::FragmentRef::new("t0"),
            0,
            1,
        ));
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::DerivedInventedSourceSpan));
    }

    #[test]
    fn permuted_segment_order_is_reported() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        // Paragraph e5 owns [t1, derived:tab, t2]; swap the first two refs.
        let view = projection
            .views
            .iter_mut()
            .find(|view| {
                view.element_ref.as_str() == "e5" && view.kind == ReaderViewKind::Paragraph
            })
            .expect("paragraph e5");
        assert!(view.segment_refs.len() >= 2);
        view.segment_refs.swap(0, 1);
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::SegmentMembershipOrOrderMismatch));
    }

    #[test]
    fn resolved_reference_is_reported() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        assert!(projection
            .references
            .iter()
            .any(|reference| !reference.resolved));
        projection.references[0].resolved = true;
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::ReferenceResolved));
    }

    #[test]
    fn duplicate_fragment_is_reported() {
        let records = synthetic();
        let mut projection = build_projection(&records).expect("projection builds");
        let clone = projection.segments[0].clone();
        projection.segments.push(clone);
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::DuplicateFragmentReference));
    }

    #[test]
    fn derived_on_a_non_control_element_is_reported() {
        let records = fixture_records();
        let mut projection = build_projection(&records).expect("projection builds");
        let derived_index = projection
            .segments
            .iter()
            .position(|segment| matches!(segment.origin, SegmentOrigin::Derived(_)))
            .expect("fixture carries derived controls");
        // Point the derived segment at a `w:t` context element instead of a control.
        projection.segments[derived_index].element_ref = ElementRef::new("e4");
        let findings = verify_projection(&projection, &records).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::DerivedNotControl));
    }

    #[test]
    fn malformed_substrate_fails_closed() {
        let projection = build_projection(&synthetic()).expect("projection builds");
        let mut broken = synthetic();
        broken.push(element("e0", Some("e1"), "p"));
        let findings = verify_projection(&projection, &broken).unwrap_err();
        assert!(codes(&findings).contains(&VerifyCode::SubstrateMalformed));
    }

    #[test]
    fn error_codes_are_closed_and_stable() {
        assert_eq!(VerifyCode::ViewUnexpected.as_str(), "view_unexpected");
        assert_eq!(
            VerifyCode::SegmentMembershipOrOrderMismatch.as_str(),
            "segment_membership_or_order_mismatch"
        );
        assert_eq!(VerifyCode::ReferenceResolved.as_str(), "reference_resolved");
        // Sanity: the classification helpers this verifier relies on stay closed.
        assert_eq!(
            ReaderSegmentKind::from_wire("text").unwrap(),
            ReaderSegmentKind::Text
        );
        assert_eq!(
            ContractErrorKind::UnknownToken,
            ContractErrorKind::UnknownToken
        );
    }
}
