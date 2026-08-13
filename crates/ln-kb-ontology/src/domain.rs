//! Pure L1–L3 write-set types. No store I/O.

use ln_identity::domain::{FrbrExpression, FrbrWork};
use ln_temporal::domain::{ForceMembershipJoin, ForceStatusEvent, MembershipEdge, NormativeState};

/// Graph node kinds allowed in the L1–L3 draft projection.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GraphNodeKind {
    Work,
    Expression,
    ComponentConcept,
    AmendingAct,
    MembershipEdge,
    ForceStatusEvent,
}

impl GraphNodeKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Work => "Work",
            Self::Expression => "Expression",
            Self::ComponentConcept => "ComponentConcept",
            Self::AmendingAct => "AmendingAct",
            Self::MembershipEdge => "MembershipEdge",
            Self::ForceStatusEvent => "ForceStatusEvent",
        }
    }
}

/// Graph edge kinds allowed in the L1–L3 draft projection.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum GraphEdgeKind {
    ExpressionOf,
    MembershipParent,
    ForceStatusOf,
    ProvAmendingAct,
}

impl GraphEdgeKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ExpressionOf => "expression_of",
            Self::MembershipParent => "membership_parent",
            Self::ForceStatusOf => "force_status_of",
            Self::ProvAmendingAct => "prov_amending_act",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphNode {
    pub kind: GraphNodeKind,
    pub id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GraphEdge {
    pub kind: GraphEdgeKind,
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
    fn empty() -> Self {
        Self {
            nodes: Vec::new(),
            edges: Vec::new(),
            claims_applicability: false,
            performs_io: false,
            structural_known: false,
            non_claims: WRITE_SET_NON_CLAIMS.to_vec(),
        }
    }

    fn push_node(&mut self, kind: GraphNodeKind, id: impl Into<String>) {
        let id = id.into();
        if !self.nodes.iter().any(|n| n.kind == kind && n.id == id) {
            self.nodes.push(GraphNode { kind, id });
        }
    }

    fn push_edge(
        &mut self,
        kind: GraphEdgeKind,
        from_id: impl Into<String>,
        to_id: impl Into<String>,
    ) {
        self.edges.push(GraphEdge {
            kind,
            from_id: from_id.into(),
            to_id: to_id.into(),
        });
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WriteSetError {
    ForbiddenKind(String),
    MissingIdentity,
    UnknownNotWritable,
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

const FORBIDDEN_KINDS: &[&str] = &[
    "ApplicableDecision",
    "PracticeRulingAsForce",
    "RiskScoreAsStatus",
    "ProfileCodeAsClock",
    "NormRuleAsAuthority",
    "NormativeBlob",
];

/// Reject L4–L7 / mixed kinds that must not enter the L1–L3 write-set.
pub fn reject_forbidden_kind(kind: &str) -> Result<(), WriteSetError> {
    if FORBIDDEN_KINDS.contains(&kind) {
        return Err(WriteSetError::ForbiddenKind(kind.to_owned()));
    }
    Ok(())
}

/// Project a FRBR Work to a Work node (no force, no Applicable).
pub fn project_work(work: &FrbrWork) -> Result<WriteSet, WriteSetError> {
    if work.work_id.as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    set.push_node(GraphNodeKind::Work, work.work_id.as_str());
    Ok(set)
}

/// Project an Expression plus `expression_of` edge to its Work.
pub fn project_expression(expression: &FrbrExpression) -> Result<WriteSet, WriteSetError> {
    if expression.expression_id.as_str().is_empty() || expression.work_id.as_str().is_empty() {
        return Err(WriteSetError::MissingIdentity);
    }
    let mut set = WriteSet::empty();
    set.push_node(GraphNodeKind::Expression, expression.expression_id.as_str());
    set.push_node(GraphNodeKind::Work, expression.work_id.as_str());
    set.push_edge(
        GraphEdgeKind::ExpressionOf,
        expression.expression_id.as_str(),
        expression.work_id.as_str(),
    );
    Ok(set)
}

/// Project a structural membership edge. Never emits force.
pub fn project_membership(edge: &MembershipEdge) -> Result<WriteSet, WriteSetError> {
    let mut set = WriteSet::empty();
    set.structural_known = true;
    set.push_node(GraphNodeKind::ComponentConcept, edge.parent().as_str());
    set.push_node(GraphNodeKind::ComponentConcept, edge.child().as_str());
    set.push_node(
        GraphNodeKind::MembershipEdge,
        format!("{}->{}", edge.parent().as_str(), edge.child().as_str()),
    );
    set.push_edge(
        GraphEdgeKind::MembershipParent,
        edge.parent().as_str(),
        edge.child().as_str(),
    );
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
    set.push_node(GraphNodeKind::ForceStatusEvent, &event_id);
    set.push_node(GraphNodeKind::ComponentConcept, event.component().as_str());
    set.push_node(GraphNodeKind::AmendingAct, event.provenance().as_str());
    set.push_edge(
        GraphEdgeKind::ForceStatusOf,
        &event_id,
        event.component().as_str(),
    );
    set.push_edge(
        GraphEdgeKind::ProvAmendingAct,
        &event_id,
        event.provenance().as_str(),
    );
    Ok(set)
}

/// Project a force↔membership join: structure always; force node only if known.
pub fn project_join(joined: &ForceMembershipJoin) -> Result<WriteSet, WriteSetError> {
    let mut set = WriteSet::empty();
    set.structural_known = joined.structural_known;
    set.push_node(GraphNodeKind::ComponentConcept, joined.component.as_str());
    if let Some(parent) = &joined.parent {
        set.push_node(GraphNodeKind::ComponentConcept, parent.as_str());
        set.push_edge(
            GraphEdgeKind::MembershipParent,
            parent.as_str(),
            joined.component.as_str(),
        );
    }
    for child in &joined.children {
        set.push_node(GraphNodeKind::ComponentConcept, child.as_str());
        set.push_edge(
            GraphEdgeKind::MembershipParent,
            joined.component.as_str(),
            child.as_str(),
        );
    }
    // Join projects structural context only. Force events come from
    // `project_force_event`. Unknown/conflict must never invent InForce nodes.
    let _ = joined.force.status;
    Ok(set)
}
