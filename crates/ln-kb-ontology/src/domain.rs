//! Pure L1–L3 write-set types. No store I/O.

use crate::catalog::OntologyCatalog;
use ln_identity::domain::{ExpressionId, FrbrExpression, FrbrWork};
use ln_temporal::domain::ComponentConceptId;
use ln_temporal::domain::{
    AmendingActId, CtvOpsError, ForceMembershipJoin, ForceStatusEvent, MembershipChangeKind,
    MembershipEdge, NormativeState, StructuralAst, StructuralAstNode, VersionedMembershipLog,
};

/// Catalog-validated node/edge kind token. Vocabulary lives in YAML, not Rust enums.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphNode {
    pub kind: String,
    pub id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphEdge {
    pub kind: String,
    pub from_id: String,
    pub to_id: String,
}

/// In-memory write-set. Never a store transaction.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WriteSet {
    pub nodes: Vec<GraphNode>,
    pub edges: Vec<GraphEdge>,
    pub claims_applicability: bool,
    pub performs_io: bool,
    pub structural_known: bool,
    pub non_claims: Vec<&'static str>,
}

impl WriteSet {
    pub fn empty() -> Self {
        Self {
            nodes: Vec::new(),
            edges: Vec::new(),
            claims_applicability: false,
            performs_io: false,
            structural_known: false,
            non_claims: WRITE_SET_NON_CLAIMS.to_vec(),
        }
    }

    pub fn try_push_node(
        &mut self,
        kind: &str,
        id: impl Into<String>,
    ) -> Result<(), WriteSetError> {
        let kind = catalog_node_kind(kind)?;
        let id = id.into();
        if !self.nodes.iter().any(|n| n.kind == kind && n.id == id) {
            self.nodes.push(GraphNode { kind, id });
        }
        Ok(())
    }

    pub fn try_push_edge(
        &mut self,
        kind: &str,
        from_id: impl Into<String>,
        to_id: impl Into<String>,
    ) -> Result<(), WriteSetError> {
        let kind = catalog_edge_kind(kind)?;
        self.edges.push(GraphEdge {
            kind,
            from_id: from_id.into(),
            to_id: to_id.into(),
        });
        Ok(())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WriteSetError {
    ForbiddenKind(String),
    MissingIdentity,
    UnknownNotWritable,
    PresenceConflict,
    MissingProvenance,
    HierarchyMapConflict,
    UnknownHierarchyLevel,
    UnknownFsmTransition,
    UnknownNodeKind,
    UnknownEdgeKind,
    UnknownPresenceKind,
}

impl std::fmt::Display for WriteSetError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::ForbiddenKind(kind) => {
                write!(formatter, "forbidden L1–L3 node kind: {kind}")
            }
            Self::MissingIdentity => write!(formatter, "projection requires a non-empty identity"),
            Self::UnknownNotWritable => {
                write!(
                    formatter,
                    "Unknown force is a read outcome, not a ForceStatusEvent write"
                )
            }
            Self::PresenceConflict => {
                write!(
                    formatter,
                    "same-day include and exclude of one component in one expression"
                )
            }
            Self::MissingProvenance => {
                write!(
                    formatter,
                    "component-in-expression event requires provenance"
                )
            }
            Self::HierarchyMapConflict => {
                write!(
                    formatter,
                    "hierarchy marker already bound to a different ComponentConcept"
                )
            }
            Self::UnknownHierarchyLevel => {
                write!(formatter, "hierarchy level is not in the YAML catalog")
            }
            Self::UnknownFsmTransition => {
                write!(
                    formatter,
                    "FSM transition is not declared in the YAML catalog"
                )
            }
            Self::UnknownNodeKind => {
                write!(formatter, "node kind is not in the YAML catalog")
            }
            Self::UnknownEdgeKind => {
                write!(formatter, "edge kind is not in the YAML catalog")
            }
            Self::UnknownPresenceKind => {
                write!(formatter, "presence change kind is not in the YAML catalog")
            }
        }
    }
}

impl std::error::Error for WriteSetError {}

const WRITE_SET_NON_CLAIMS: &[&str] = &[
    "Write-set is pure projection; performs no store I/O and is not RuVector materialization",
    "Work/Expression/membership presence does not imply ForceStatus InForce",
    "ForceStatusEvent projection does not imply Applicability",
    "Not production graph schema, not corpus edges, not legal validation",
    "Lifecycle [proposed]; KBO O2 write-set; not O3 fixture edges or O4 port I/O",
];

/// Reject L4–L7 / mixed kinds listed in the YAML catalog.
pub fn reject_forbidden_kind(kind: &str) -> Result<(), WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::MissingIdentity)?;
    if catalog.is_forbidden_kind(kind) {
        return Err(WriteSetError::ForbiddenKind(kind.to_owned()));
    }
    Ok(())
}

/// Advance the meta-prompt FSM only along YAML-declared edges.
pub fn advance_ontology_fsm(from: &str, to: &str) -> Result<(), WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownFsmTransition)?;
    if catalog.allows_transition(from, to) {
        return Ok(());
    }
    Err(WriteSetError::UnknownFsmTransition)
}

/// Project a FRBR Work to a Work node (no force, no Applicable).
pub fn project_work(work: &FrbrWork) -> Result<WriteSet, WriteSetError> {
    if work.work_id.as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    set.try_push_node("Work", work.work_id.as_str())?;
    Ok(set)
}

/// Project an Expression plus `expression_of` edge to its Work.
pub fn project_expression(expression: &FrbrExpression) -> Result<WriteSet, WriteSetError> {
    if expression.expression_id.as_str().is_empty() || expression.work_id.as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    set.try_push_node("Expression", expression.expression_id.as_str())?;
    set.try_push_node("Work", expression.work_id.as_str())?;
    set.try_push_edge(
        "expression_of",
        expression.expression_id.as_str(),
        expression.work_id.as_str(),
    )?;
    Ok(set)
}

/// Project a structural membership edge. Never emits force.
pub fn project_membership(edge: &MembershipEdge) -> Result<WriteSet, WriteSetError> {
    let mut set = WriteSet::empty();
    set.structural_known = true;
    set.try_push_node("ComponentConcept", edge.parent().as_str())?;
    set.try_push_node("ComponentConcept", edge.child().as_str())?;
    set.try_push_node(
        "MembershipEdge",
        format!("{}->{}", edge.parent().as_str(), edge.child().as_str()),
    )?;
    set.try_push_edge(
        "membership_parent",
        edge.parent().as_str(),
        edge.child().as_str(),
    )?;
    Ok(set)
}

/// Project a force-status transition event. `Unknown` is not writable.
pub fn project_force_event(event: &ForceStatusEvent) -> Result<WriteSet, WriteSetError> {
    if event.status() == NormativeState::Unknown {
        return Err(WriteSetError::UnknownNotWritable);
    }
    if event.component().as_str().is_empty() || event.provenance().as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    let event_id = format!(
        "force:{}:{}:{}",
        event.component().as_str(),
        event.effect_day(),
        event.provenance().as_str()
    );
    set.try_push_node("ForceStatusEvent", &event_id)?;
    set.try_push_node("ComponentConcept", event.component().as_str())?;
    set.try_push_node("AmendingAct", event.provenance().as_str())?;
    set.try_push_edge("force_status_of", &event_id, event.component().as_str())?;
    set.try_push_edge("prov_amending_act", &event_id, event.provenance().as_str())?;
    Ok(set)
}

/// Project a force↔membership join: structure always; force node only if known.
pub fn project_join(joined: &ForceMembershipJoin) -> Result<WriteSet, WriteSetError> {
    let mut set = WriteSet::empty();
    set.structural_known = joined.structural_known;
    set.try_push_node("ComponentConcept", joined.component.as_str())?;
    if let Some(parent) = &joined.parent {
        set.try_push_node("ComponentConcept", parent.as_str())?;
        set.try_push_edge(
            "membership_parent",
            parent.as_str(),
            joined.component.as_str(),
        )?;
    }
    for child in &joined.children {
        set.try_push_node("ComponentConcept", child.as_str())?;
        set.try_push_edge(
            "membership_parent",
            joined.component.as_str(),
            child.as_str(),
        )?;
    }
    // Join projects structural context only. Force events come from
    // `project_force_event`. Unknown/conflict must never invent InForce nodes.
    let _ = joined.force.status;
    Ok(set)
}

/// Project a folded StructuralAst. The AST remains a view; this is not I/O.
pub fn project_structural_ast(ast: &StructuralAst) -> Result<WriteSet, WriteSetError> {
    let mut set = WriteSet::empty();
    set.structural_known = !ast.roots().is_empty();
    for root in ast.roots() {
        project_ast_node(&mut set, root)?;
    }
    Ok(set)
}

fn project_ast_node(set: &mut WriteSet, node: &StructuralAstNode) -> Result<(), WriteSetError> {
    set.try_push_node("ComponentConcept", node.component().as_str())?;
    for child in node.children() {
        set.try_push_node("ComponentConcept", child.component().as_str())?;
        set.try_push_edge(
            "membership_parent",
            node.component().as_str(),
            child.component().as_str(),
        )?;
        project_ast_node(set, child)?;
    }
    Ok(())
}

// ─── Component-in-Expression presence (not CTV text, not force) ─────────────

/// Provenance-gated presence change of a CC in one Expression.
/// `kind` is a YAML catalog token (`include` / `exclude`), not a Rust enum.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ComponentInExpressionEvent {
    kind: String,
    expression_id: ExpressionId,
    component: ComponentConceptId,
    effect_day: i64,
    provenance: String,
}

impl ComponentInExpressionEvent {
    pub fn try_new(
        kind: &str,
        expression_id: ExpressionId,
        component: ComponentConceptId,
        effect_day: i64,
        provenance: &str,
    ) -> Result<Self, WriteSetError> {
        let kind = catalog_presence_kind(kind)?;
        if expression_id.as_str().is_empty() || component.as_str().is_empty() {
            return Err(WriteSetError::MissingIdentity);
        }
        if provenance.is_empty() {
            return Err(WriteSetError::MissingProvenance);
        }
        Ok(Self {
            kind,
            expression_id,
            component,
            effect_day,
            provenance: provenance.to_owned(),
        })
    }

    pub fn kind(&self) -> &str {
        &self.kind
    }

    pub fn expression_id(&self) -> &ExpressionId {
        &self.expression_id
    }

    pub fn component(&self) -> &ComponentConceptId {
        &self.component
    }

    pub fn effect_day(&self) -> i64 {
        self.effect_day
    }
}

/// Append-only presence log (offline synthetic).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ComponentInExpressionLog {
    events: Vec<ComponentInExpressionEvent>,
}

impl ComponentInExpressionLog {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn append(&mut self, event: ComponentInExpressionEvent) -> Result<(), WriteSetError> {
        self.events.push(event);
        Ok(())
    }
}

/// Folded presence set of components in one Expression at effect_day t.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExpressionPresenceSet {
    expression_id: String,
    as_of_day: i64,
    components: Vec<ComponentConceptId>,
}

impl ExpressionPresenceSet {
    pub fn is_projection(&self) -> bool {
        true
    }

    pub fn components(&self) -> &[ComponentConceptId] {
        &self.components
    }
}

const PRESENCE_NON_CLAIMS: &[&str] = &[
    "Expression presence is a fold projection, not CTV text and not force",
    "A later Expression does not silently inherit earlier presence",
    "Tree membership does not imply component_in_expression",
    "Not Manifestation, not applicability, not corpus reconstruction",
];

/// Fold include/exclude events for one Expression at t.
/// Same-day include+exclude of one CC → PresenceConflict.
pub fn fold_expression_presence(
    log: &ComponentInExpressionLog,
    expression_id: &ExpressionId,
    as_of_day: i64,
) -> Result<ExpressionPresenceSet, WriteSetError> {
    let mut applicable: Vec<&ComponentInExpressionEvent> = log
        .events
        .iter()
        .filter(|e| e.expression_id.as_str() == expression_id.as_str() && e.effect_day <= as_of_day)
        .collect();
    applicable.sort_by_key(|e| {
        (
            e.effect_day,
            e.kind.as_str(),
            e.component.as_str().to_owned(),
        )
    });

    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownPresenceKind)?;
    let mut present: Vec<String> = Vec::new();
    let mut i = 0;
    while i < applicable.len() {
        let day = applicable[i].effect_day;
        let mut j = i;
        while j < applicable.len() && applicable[j].effect_day == day {
            j += 1;
        }
        let slice = &applicable[i..j];

        let mut seen: Vec<(String, String)> = Vec::new();
        for ev in slice.iter() {
            let id = ev.component.as_str().to_owned();
            if let Some((_, prior)) = seen.iter().find(|(c, _)| c == &id) {
                if prior != &ev.kind {
                    return Err(WriteSetError::PresenceConflict);
                }
            } else {
                seen.push((id, ev.kind.clone()));
            }
        }

        for ev in slice {
            let id = ev.component.as_str().to_owned();
            match catalog.presence_fold_op(&ev.kind) {
                Some("add") => {
                    if !present.contains(&id) {
                        present.push(id);
                    }
                }
                Some("remove") => {
                    present.retain(|c| c != &id);
                }
                _ => return Err(WriteSetError::UnknownPresenceKind),
            }
        }
        i = j;
    }

    present.sort();
    let components = present
        .into_iter()
        .map(|id| ComponentConceptId::parse(&id).expect("folded ids are valid"))
        .collect();
    let _ = PRESENCE_NON_CLAIMS;
    Ok(ExpressionPresenceSet {
        expression_id: expression_id.as_str().to_owned(),
        as_of_day,
        components,
    })
}

pub fn expression_contains(set: &ExpressionPresenceSet, component: &ComponentConceptId) -> bool {
    set.components
        .iter()
        .any(|c| c.as_str() == component.as_str())
}

/// Keep StructuralAst nodes that are present in the Expression (or have present descendants).
pub fn filter_ast_to_expression(
    ast: &StructuralAst,
    presence: &ExpressionPresenceSet,
) -> Result<StructuralAst, WriteSetError> {
    let refs: Vec<&ComponentConceptId> = presence.components.iter().collect();
    Ok(ast.filter_to_components(&refs))
}

/// Project presence as component_in_expression edges. No I/O.
pub fn project_expression_presence(
    expression: &FrbrExpression,
    presence: &ExpressionPresenceSet,
) -> Result<WriteSet, WriteSetError> {
    if expression.expression_id.as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    set.try_push_node("Expression", expression.expression_id.as_str())?;
    for component in &presence.components {
        set.try_push_node("ComponentConcept", component.as_str())?;
        set.try_push_edge(
            "component_in_expression",
            component.as_str(),
            expression.expression_id.as_str(),
        )?;
    }
    Ok(set)
}

// ─── HierarchyMarker → CC lift (KBO-R024 / R3-02). Decode remains a candidate. ─
// Levels come from prd/architecture/kb-ontology.yaml, not a Rust enum.

fn catalog_node_kind(kind: &str) -> Result<String, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownNodeKind)?;
    if catalog.is_forbidden_kind(kind) {
        return Err(WriteSetError::ForbiddenKind(kind.to_owned()));
    }
    if catalog.is_node_kind(kind) {
        return Ok(kind.to_owned());
    }
    Err(WriteSetError::UnknownNodeKind)
}

fn catalog_edge_kind(kind: &str) -> Result<String, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownEdgeKind)?;
    if catalog.is_edge_kind(kind) {
        return Ok(kind.to_owned());
    }
    Err(WriteSetError::UnknownEdgeKind)
}

fn catalog_presence_kind(kind: &str) -> Result<String, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownPresenceKind)?;
    if catalog.is_presence_change_kind(kind) {
        return Ok(kind.to_owned());
    }
    Err(WriteSetError::UnknownPresenceKind)
}

fn catalog_level(level: &str) -> Result<String, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownHierarchyLevel)?;
    let level = level.trim();
    if catalog.is_hierarchy_level(level) {
        return Ok(level.to_owned());
    }
    Err(WriteSetError::UnknownHierarchyLevel)
}

/// Resolve a decode-facing token (`Statya`) through YAML aliases, then build a marker.
pub fn marker_from_decode_token(
    work_id: Option<&str>,
    decode_token: &str,
    number: &str,
    title: Option<&str>,
) -> Result<HierarchyMarker, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownHierarchyLevel)?;
    let level = catalog
        .resolve_decode_level_alias(decode_token)
        .ok_or(WriteSetError::UnknownHierarchyLevel)?;
    HierarchyMarker::try_new(work_id, &level, number, title)
}

/// Decode-facing candidate marker. Number+level is not a ComponentConcept.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyMarker {
    work_id: Option<String>,
    level: String,
    number: String,
    title: Option<String>,
}

impl HierarchyMarker {
    pub fn try_new(
        work_id: Option<&str>,
        level: &str,
        number: &str,
        title: Option<&str>,
    ) -> Result<Self, WriteSetError> {
        let number = number.trim();
        if number.is_empty() {
            return Err(WriteSetError::MissingIdentity);
        }
        if title.is_some_and(|value| value.trim().is_empty()) {
            return Err(WriteSetError::MissingIdentity);
        }
        Ok(Self {
            work_id: work_id.map(str::to_owned),
            level: catalog_level(level)?,
            number: number.to_owned(),
            title: title.map(str::to_owned),
        })
    }

    pub fn level(&self) -> &str {
        &self.level
    }

    pub fn number(&self) -> &str {
        &self.number
    }
}

/// Explicit binding of a marker key to a stable ComponentConcept.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyBinding {
    work_id: Option<String>,
    level: String,
    number: String,
    component: ComponentConceptId,
}

impl HierarchyBinding {
    pub fn try_new(
        work_id: Option<&str>,
        level: &str,
        number: &str,
        component: ComponentConceptId,
    ) -> Result<Self, WriteSetError> {
        let number = number.trim();
        if number.is_empty() || component.as_str().is_empty() {
            return Err(WriteSetError::MissingIdentity);
        }
        Ok(Self {
            work_id: work_id.map(str::to_owned),
            level: catalog_level(level)?,
            number: number.to_owned(),
            component,
        })
    }

    pub fn component(&self) -> &ComponentConceptId {
        &self.component
    }
}

/// Fail-closed registry. Duplicate key with a different CC is Conflict.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct HierarchyMap {
    bindings: Vec<HierarchyBinding>,
}

impl HierarchyMap {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn register(&mut self, binding: HierarchyBinding) -> Result<(), WriteSetError> {
        if let Some(existing) = self.bindings.iter().find(|item| same_key(item, &binding)) {
            if existing.component.as_str() != binding.component.as_str() {
                return Err(WriteSetError::HierarchyMapConflict);
            }
            return Ok(());
        }
        self.bindings.push(binding);
        Ok(())
    }
}

fn same_key(left: &HierarchyBinding, right: &HierarchyBinding) -> bool {
    left.work_id.as_deref() == right.work_id.as_deref()
        && left.level == right.level
        && left.number == right.number
}

/// Lift outcome. Unknown is honest absence, never an invented CC.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HierarchyMapOutcome {
    Bound { component: ComponentConceptId },
    Unknown,
}

impl HierarchyMapOutcome {
    pub fn non_claims(&self) -> &'static [&'static str] {
        HIERARCHY_LIFT_NON_CLAIMS
    }
}

const HIERARCHY_LIFT_NON_CLAIMS: &[&str] = &[
    "HierarchyMarker is a decode candidate; number+level does not mint a ComponentConcept",
    "Unmapped marker resolves Unknown, never an invented CC or InForce",
    "Lift does not imply Expression presence, CTV text, or applicability",
    "Not calendar legal_act_effect, not corpus reconstruction, not parser legal fact",
];

/// Draft attach from document-order markers. Not a membership log write.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MembershipProposal {
    pub parent: ComponentConceptId,
    pub child: ComponentConceptId,
}

/// Stack-propose report. Unknown markers stay quarantined.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MembershipProposeReport {
    pub proposals: Vec<MembershipProposal>,
    pub quarantined: usize,
    pub forest_roots: usize,
}

const MEMBERSHIP_PROPOSE_NON_CLAIMS: &[&str] = &[
    "Membership proposals are drafts; they do not append VersionedMembershipLog",
    "Unknown markers are quarantined and do not mint ComponentConcept",
    "Forest roots are unbound tops, not Work children and not InForce",
    "Not CTV text, not Expression include, not Applicable",
];

impl MembershipProposeReport {
    pub fn non_claims(&self) -> &'static [&'static str] {
        MEMBERSHIP_PROPOSE_NON_CLAIMS
    }
}

/// Propose attach edges from document-order markers using YAML level ranks.
/// Unknown markers skip the stack. Empty registry yields only quarantine.
pub fn propose_membership_from_markers(
    map: &HierarchyMap,
    markers: &[HierarchyMarker],
) -> Result<MembershipProposeReport, WriteSetError> {
    let catalog = OntologyCatalog::embedded().map_err(|_| WriteSetError::UnknownHierarchyLevel)?;
    let mut stack: Vec<(usize, ComponentConceptId)> = Vec::new();
    let mut proposals = Vec::new();
    let mut quarantined = 0usize;
    let mut forest_roots = 0usize;
    for marker in markers {
        let Some(rank) = catalog.hierarchy_level_rank(marker.level()) else {
            return Err(WriteSetError::UnknownHierarchyLevel);
        };
        match map_hierarchy_marker(map, marker) {
            HierarchyMapOutcome::Unknown => {
                quarantined = quarantined.saturating_add(1);
            }
            HierarchyMapOutcome::Bound { component } => {
                while stack.last().is_some_and(|(top_rank, _)| *top_rank >= rank) {
                    stack.pop();
                }
                if let Some((_, parent)) = stack.last() {
                    proposals.push(MembershipProposal {
                        parent: parent.clone(),
                        child: component.clone(),
                    });
                } else {
                    forest_roots = forest_roots.saturating_add(1);
                }
                stack.push((rank, component));
            }
        }
    }
    Ok(MembershipProposeReport {
        proposals,
        quarantined,
        forest_roots,
    })
}

/// Map a marker through an explicit registry. Missing key → Unknown.
pub fn map_hierarchy_marker(map: &HierarchyMap, marker: &HierarchyMarker) -> HierarchyMapOutcome {
    match map.bindings.iter().find(|item| {
        item.work_id.as_deref() == marker.work_id.as_deref()
            && item.level == marker.level
            && item.number == marker.number
    }) {
        Some(binding) => HierarchyMapOutcome::Bound {
            component: binding.component.clone(),
        },
        None => HierarchyMapOutcome::Unknown,
    }
}

// ─── S_admit: conflict quarantine on proposed drafts ───────────────────────────
// Admitted drafts are still not VersionedMembershipLog writes. Structural checks
// (cycle, two-parent, self-parent) are graph integrity, not legal hierarchy.

/// A proposal that survived the conflict gate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AdmittedMembership {
    pub parent: ComponentConceptId,
    pub child: ComponentConceptId,
}

/// Why a proposal was quarantined during admission.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum QuarantineReason {
    /// Child already has a different parent from an earlier admitted proposal.
    TwoParentConflict { other_parent: ComponentConceptId },
    /// Admitting this edge would create a parent-cycle.
    Cycle,
    /// Parent and child are the same CC.
    SelfParent,
}

/// A proposal quarantined during admission, with a structural reason.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct QuarantinedProposal {
    pub parent: ComponentConceptId,
    pub child: ComponentConceptId,
    pub reason: QuarantineReason,
}

/// S_admit report: admitted drafts + quarantined conflicts.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MembershipAdmitReport {
    pub admitted: Vec<AdmittedMembership>,
    pub quarantined: Vec<QuarantinedProposal>,
    pub forest_roots: usize,
}

const MEMBERSHIP_ADMIT_NON_CLAIMS: &[&str] = &[
    "Admitted proposals are still drafts; they do not append VersionedMembershipLog",
    "Quarantined proposals need human or provenance resolution before commit",
    "Not CTV text, not Expression include, not Applicable",
    "Cycle and two-parent checks are structural graph integrity, not legal hierarchy authority",
];

impl MembershipAdmitReport {
    pub fn non_claims(&self) -> &'static [&'static str] {
        MEMBERSHIP_ADMIT_NON_CLAIMS
    }
}

/// Admit proposed drafts through a structural conflict gate.
/// First parent wins; exact duplicates are silently deduplicated.
pub fn admit_membership_proposals(proposals: &[MembershipProposal]) -> MembershipAdmitReport {
    let mut admitted: Vec<AdmittedMembership> = Vec::new();
    let mut quarantined: Vec<QuarantinedProposal> = Vec::new();
    // (child, parent) for admitted edges, used for two-parent and cycle checks.
    let mut child_parents: Vec<(ComponentConceptId, ComponentConceptId)> = Vec::new();

    for proposal in proposals {
        if proposal.parent.as_str() == proposal.child.as_str() {
            quarantined.push(QuarantinedProposal {
                parent: proposal.parent.clone(),
                child: proposal.child.clone(),
                reason: QuarantineReason::SelfParent,
            });
            continue;
        }
        if admitted.iter().any(|edge| {
            edge.parent.as_str() == proposal.parent.as_str()
                && edge.child.as_str() == proposal.child.as_str()
        }) {
            continue;
        }
        if let Some((_, existing_parent)) = child_parents
            .iter()
            .find(|(child, _)| child.as_str() == proposal.child.as_str())
        {
            quarantined.push(QuarantinedProposal {
                parent: proposal.parent.clone(),
                child: proposal.child.clone(),
                reason: QuarantineReason::TwoParentConflict {
                    other_parent: existing_parent.clone(),
                },
            });
            continue;
        }
        if creates_cycle(&child_parents, &proposal.parent, &proposal.child) {
            quarantined.push(QuarantinedProposal {
                parent: proposal.parent.clone(),
                child: proposal.child.clone(),
                reason: QuarantineReason::Cycle,
            });
            continue;
        }
        child_parents.push((proposal.child.clone(), proposal.parent.clone()));
        admitted.push(AdmittedMembership {
            parent: proposal.parent.clone(),
            child: proposal.child.clone(),
        });
    }

    let parents: std::collections::HashSet<&str> =
        admitted.iter().map(|e| e.parent.as_str()).collect();
    let children: std::collections::HashSet<&str> =
        admitted.iter().map(|e| e.child.as_str()).collect();
    let forest_roots = parents.difference(&children).count();

    MembershipAdmitReport {
        admitted,
        quarantined,
        forest_roots,
    }
}

/// Walk the admitted parent chain from `parent`. If `child` is reachable,
/// admitting (parent → child) would close a cycle.
fn creates_cycle(
    edges: &[(ComponentConceptId, ComponentConceptId)],
    parent: &ComponentConceptId,
    child: &ComponentConceptId,
) -> bool {
    let mut current = parent.as_str();
    let mut visited = std::collections::HashSet::new();
    loop {
        if current == child.as_str() {
            return true;
        }
        if !visited.insert(current) {
            return false;
        }
        let Some(next) = edges
            .iter()
            .find(|(c, _)| c.as_str() == current)
            .map(|(_, p)| p.as_str())
        else {
            return false;
        };
        current = next;
    }
}

// ─── S_commit: append admitted drafts to VersionedMembershipLog ────────────────
// Provenance is synthetic for C2 editions until S_identify mints Expression IDs.
// Admitted edges become Attach events. Quarantined proposals are skipped.

const MEMBERSHIP_COMMIT_NON_CLAIMS: &[&str] = &[
    "Committed events are C2-oracle-derived; provenance is synthetic until S_identify",
    "Commit does not resolve CTV text, legal hierarchy authority, or applicability",
    "Not InForce, not corpus gold, not O3 representative fixtures",
];

/// Append each admitted edge as an Attach event with provenance and effect_day.
/// Returns the number of events committed.
pub fn commit_admitted_to_log(
    admit: &MembershipAdmitReport,
    log: &mut VersionedMembershipLog,
    effect_day: i64,
    provenance: &AmendingActId,
) -> Result<usize, CtvOpsError> {
    for edge in &admit.admitted {
        let event = ln_temporal::domain::VersionedMembershipEvent::try_new(
            MembershipChangeKind::Attach,
            edge.parent.clone(),
            edge.child.clone(),
            effect_day,
            provenance.clone(),
        )?;
        log.append(event)?;
    }
    Ok(admit.admitted.len())
}

pub fn membership_commit_non_claims() -> &'static [&'static str] {
    MEMBERSHIP_COMMIT_NON_CLAIMS
}

/// Summary of the assembled AST after commit → fold. Primitive counts only so
/// callers (CLI) do not need a direct ln-temporal dependency.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MembershipAstSummary {
    pub committed: usize,
    pub root_count: usize,
    pub node_count: usize,
}

/// Full assembly: admit → commit → fold. Returns primitive counts.
/// Provenance is synthetic for C2 editions until S_identify.
pub fn assemble_membership_ast(
    admit: &MembershipAdmitReport,
    effect_day: i64,
    provenance: &str,
) -> Result<MembershipAstSummary, CtvOpsError> {
    let provenance = AmendingActId::parse(provenance)?;
    let mut log = VersionedMembershipLog::empty();
    let committed = commit_admitted_to_log(admit, &mut log, effect_day, &provenance)?;
    let ast = ln_temporal::domain::fold_membership_at(&log, effect_day)?;
    let root_count = ast.roots().len();
    let node_count = ast.roots().iter().map(count_ast_subtree_nodes).sum();
    Ok(MembershipAstSummary {
        committed,
        root_count,
        node_count,
    })
}

/// Full assembly + oracle diff. Returns counts plus drift report.
/// Expected CCs come from the registry (Bound markers). Zero drift means
/// the event log perfectly reconstructs the oracle snapshot.
pub fn assemble_with_oracle_diff(
    admit: &MembershipAdmitReport,
    map: &HierarchyMap,
    effect_day: i64,
    provenance: &str,
) -> Result<AssemblyReport, CtvOpsError> {
    let prov = AmendingActId::parse(provenance)?;
    let mut log = VersionedMembershipLog::empty();
    let committed = commit_admitted_to_log(admit, &mut log, effect_day, &prov)?;
    let ast = ln_temporal::domain::fold_membership_at(&log, effect_day)?;
    let root_count = ast.roots().len();
    let node_count = ast.roots().iter().map(count_ast_subtree_nodes).sum();
    let expected: Vec<ComponentConceptId> =
        map.bindings.iter().map(|b| b.component().clone()).collect();
    let diff = oracle_diff(&ast, &expected);
    Ok(AssemblyReport {
        committed,
        root_count,
        node_count,
        drift: diff.drift,
        missing: diff.missing,
        phantom: diff.phantom,
    })
}

/// Assembly + oracle diff summary. Primitive counts only.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssemblyReport {
    pub committed: usize,
    pub root_count: usize,
    pub node_count: usize,
    pub drift: usize,
    pub missing: usize,
    pub phantom: usize,
}

fn count_ast_subtree_nodes(node: &StructuralAstNode) -> usize {
    1 + node
        .children()
        .iter()
        .map(count_ast_subtree_nodes)
        .sum::<usize>()
}

// ─── S_fold: edition_ast_at = membership fold + presence fold + filter ────────
// Combines three L2 canons: composition (membership) + edition (presence) →
// filtered StructuralAst. Not CTV text, not force.

/// Fold membership at t, fold presence at t, filter composition by presence.
/// A component absent from the Expression's presence set is pruned from
/// the edition AST even if it has a membership edge.
pub fn edition_ast_at(
    membership_log: &VersionedMembershipLog,
    presence_log: &ComponentInExpressionLog,
    expression_id: &ExpressionId,
    as_of_day: i64,
) -> Result<StructuralAst, WriteSetError> {
    let composition = ln_temporal::domain::fold_membership_at(membership_log, as_of_day)
        .map_err(|_| WriteSetError::MissingIdentity)?;
    let presence = fold_expression_presence(presence_log, expression_id, as_of_day)?;
    filter_ast_to_expression(&composition, &presence)
}

// ─── S_verify: oracle diff ────────────────────────────────────────────────────
// Compare folded AST against expected CCs from the EditionOracle snapshot.
// drift = missing (expected but not in AST) + phantom (in AST but not expected).

/// Diff report: expected vs actual CCs in the folded AST.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OracleDiffReport {
    pub expected: usize,
    pub actual: usize,
    pub missing: usize,
    pub phantom: usize,
    pub drift: usize,
}

/// Compare a folded StructuralAst against the set of CCs the oracle expects.
/// Zero drift means the event log perfectly reconstructs the oracle snapshot.
pub fn oracle_diff(ast: &StructuralAst, expected: &[ComponentConceptId]) -> OracleDiffReport {
    let actual_set: std::collections::HashSet<&str> =
        ast.roots().iter().flat_map(collect_subtree_ccs).collect();
    let expected_set: std::collections::HashSet<&str> =
        expected.iter().map(|c| c.as_str()).collect();
    let missing = expected_set.difference(&actual_set).count();
    let phantom = actual_set.difference(&expected_set).count();
    OracleDiffReport {
        expected: expected.len(),
        actual: actual_set.len(),
        missing,
        phantom,
        drift: missing + phantom,
    }
}

fn collect_subtree_ccs(node: &StructuralAstNode) -> Vec<&str> {
    let mut result = vec![node.component().as_str()];
    for child in node.children() {
        result.extend(collect_subtree_ccs(child));
    }
    result
}
