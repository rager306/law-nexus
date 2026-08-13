//! Pure L1–L3 write-set types. No store I/O.

use crate::catalog::OntologyCatalog;
use ln_identity::domain::{ExpressionId, FrbrExpression, FrbrWork};
use ln_temporal::domain::ComponentConceptId;
use ln_temporal::domain::{
    ForceMembershipJoin, ForceStatusEvent, MembershipEdge, NormativeState, StructuralAst,
    StructuralAstNode,
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
