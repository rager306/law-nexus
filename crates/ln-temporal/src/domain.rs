use std::error::Error;
use std::fmt;

const MAX_ID_LEN: usize = 64;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdError {
    kind: &'static str,
    reason: &'static str,
}

impl fmt::Display for IdError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "invalid {}: {}", self.kind, self.reason)
    }
}

impl Error for IdError {}

fn parse_id(kind: &'static str, value: &str, max_len: usize) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind,
            reason: "empty",
        });
    }
    if value.len() > max_len {
        return Err(IdError {
            kind,
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.'))
    {
        return Err(IdError {
            kind,
            reason: "unsupported character",
        });
    }
    Ok(value.to_owned())
}

macro_rules! id_type {
    ($name:ident, $kind:literal) => {
        #[derive(Debug, Clone, PartialEq, Eq, Hash)]
        pub struct $name(String);
        impl $name {
            pub fn parse(value: &str) -> Result<Self, IdError> {
                parse_id($kind, value, MAX_ID_LEN).map(Self)
            }
            pub fn as_str(&self) -> &str {
                &self.0
            }
        }
    };
}

id_type!(AnchorId, "anchor id");
id_type!(RequestId, "request id");

pub const D118_POLICY_VERSION: &str = "d118:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ClockKind {
    FactualEvent,
    Proceeding,
    LegalActEffect,
    SourcePublication,
    SystemObservation,
}

impl ClockKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::FactualEvent => "factual_event",
            Self::Proceeding => "proceeding",
            Self::LegalActEffect => "legal_act_effect",
            Self::SourcePublication => "source_publication",
            Self::SystemObservation => "system_observation",
        }
    }

    pub fn all() -> [ClockKind; 5] {
        [
            Self::FactualEvent,
            Self::Proceeding,
            Self::LegalActEffect,
            Self::SourcePublication,
            Self::SystemObservation,
        ]
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SubstituteKind {
    OtherClock(ClockKind),
    WallClock,
    EditionOrder,
    LifecycleType,
}

impl SubstituteKind {
    pub fn as_str(self) -> String {
        match self {
            Self::OtherClock(clock) => format!("other_clock:{}", clock.as_str()),
            Self::WallClock => "wall_clock".to_owned(),
            Self::EditionOrder => "edition_order".to_owned(),
            Self::LifecycleType => "lifecycle_type".to_owned(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResolutionOutcome {
    Resolved,
    MissingAnchor,
    SubstituteRejected,
    Unknown,
    Conflict,
}

impl ResolutionOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Resolved => "resolved",
            Self::MissingAnchor => "missing-anchor",
            Self::SubstituteRejected => "substitute-rejected",
            Self::Unknown => "unknown",
            Self::Conflict => "conflict",
        }
    }

    pub fn is_fail_closed(self) -> bool {
        !matches!(self, Self::Resolved)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClockAnchor {
    pub clock: ClockKind,
    pub anchor_id: AnchorId,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolutionRequest {
    pub request_id: RequestId,
    pub governing_clock: ClockKind,
    /// Attempted non-governing sources offered by caller/adapter.
    pub attempted_substitutes: Vec<SubstituteKind>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecisionTrace {
    pub policy_version: String,
    pub governing_clock: ClockKind,
    pub governing_anchor: Option<AnchorId>,
    pub considered_substitutes: Vec<String>,
    pub rejected_substitutes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ResolutionResult {
    pub outcome: ResolutionOutcome,
    pub governing_clock: ClockKind,
    pub resolved_anchor: Option<AnchorId>,
    pub substitution_used: bool,
    pub trace: DecisionTrace,
}

/// Closed set of temporal reasoning capabilities that five-clock safety does
/// **not** provide (RC11-F06 design boundary / ADR-0009 non-claims).
///
/// These names are design inventory only. Presence of the enum does not implement
/// interval algebra, bitemporal storage, legal-date validation, or applicable-law
/// reasoning.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TemporalAlgebraCapability {
    IntervalOverlap,
    IntervalContainment,
    IntervalMerge,
    BitemporalCorrectionLedger,
    DerivedEffectiveWindowAsSourceTruth,
    LegalDateValidation,
    ApplicableLawSelection,
}

impl TemporalAlgebraCapability {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::IntervalOverlap => "interval_overlap",
            Self::IntervalContainment => "interval_containment",
            Self::IntervalMerge => "interval_merge",
            Self::BitemporalCorrectionLedger => "bitemporal_correction_ledger",
            Self::DerivedEffectiveWindowAsSourceTruth => "derived_effective_window_as_source_truth",
            Self::LegalDateValidation => "legal_date_validation",
            Self::ApplicableLawSelection => "applicable_law_selection",
        }
    }

    pub fn all() -> [TemporalAlgebraCapability; 7] {
        [
            Self::IntervalOverlap,
            Self::IntervalContainment,
            Self::IntervalMerge,
            Self::BitemporalCorrectionLedger,
            Self::DerivedEffectiveWindowAsSourceTruth,
            Self::LegalDateValidation,
            Self::ApplicableLawSelection,
        ]
    }
}

/// Fail-closed classification of a requested temporal capability relative to
/// the five-clock safety contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TemporalCapabilityClass {
    /// Covered by five-clock role safety (anchor resolve / no substitution).
    FiveClockSafety,
    /// Explicitly outside five-clock safety; requires a later design/runtime owner.
    DeferredAlgebra,
}

impl TemporalCapabilityClass {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::FiveClockSafety => "five_clock_safety",
            Self::DeferredAlgebra => "deferred_algebra",
        }
    }
}

/// Design-boundary answer: five-clock safety vs deferred algebra (RC11-F06).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemporalCapabilityBoundary {
    pub capability: TemporalAlgebraCapability,
    pub class: TemporalCapabilityClass,
    pub non_claims: Vec<&'static str>,
}

const F06_NON_CLAIMS: &[&str] = &[
    "Five-clock model is a safety contract, not a complete temporal algebra",
    "Does not implement interval or bitemporal algebra",
    "Does not validate real legal dates or applicable-law selection",
    "Derived effective_from/to windows are projections, not source truth",
    "Lifecycle: five-clock safety [bounded]; algebra remains deferred/proposed",
];

/// Classify a temporal capability against the ADR-0009 safety boundary.
///
/// Always returns `DeferredAlgebra` for the closed algebra inventory. This is
/// intentional: five-clock resolve cannot silently expand into algebra APIs.
pub fn classify_temporal_capability(
    capability: TemporalAlgebraCapability,
) -> TemporalCapabilityBoundary {
    TemporalCapabilityBoundary {
        capability,
        class: TemporalCapabilityClass::DeferredAlgebra,
        non_claims: F06_NON_CLAIMS.to_vec(),
    }
}

/// Fail-closed rejection of treating a derived interval projection as a sixth
/// clock or source-of-truth anchor (RC11-F06 / ADR-0009).
pub fn reject_derived_interval_as_source_truth() -> TemporalCapabilityBoundary {
    classify_temporal_capability(TemporalAlgebraCapability::DerivedEffectiveWindowAsSourceTruth)
}

/// Closed design inventory of legislative event kinds that must remain separated
/// (RC11-F07 / TSG-002 / ADR-0017).
///
/// These names are design taxonomy only. Presence of the enum does not implement
/// CTV event sourcing, amendment micro-events, or legal-effect determination.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LegislativeEventKind {
    /// Provenance-backed structural/content change (text/structure), not legal effect.
    TextChange,
    /// Proven change in legal consequence; must not be inferred from text alone.
    NormativeEffect,
}

impl LegislativeEventKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::TextChange => "text_change_event",
            Self::NormativeEffect => "normative_effect_event",
        }
    }

    pub fn all() -> [LegislativeEventKind; 2] {
        [Self::TextChange, Self::NormativeEffect]
    }
}

/// Classification of a legislative event kind relative to executable CTV runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum LegislativeEventKindClass {
    /// Named and separated in design; not an executable product event type yet.
    DesignOnly,
    /// Reserved for a future executable CTV/event runtime owner.
    ExecutableRuntime,
}

impl LegislativeEventKindClass {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::DesignOnly => "design_only",
            Self::ExecutableRuntime => "executable_runtime",
        }
    }
}

/// Design-boundary answer for TextChange vs NormativeEffect (RC11-F07).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LegislativeEventKindBoundary {
    pub kind: LegislativeEventKind,
    pub class: LegislativeEventKindClass,
    pub non_claims: Vec<&'static str>,
}

const F07_NON_CLAIMS: &[&str] = &[
    "TextChangeEvent and NormativeEffectEvent are not separated as executable product types",
    "Lexical or amendment text does not prove legal effect",
    "TextChangeEvent must not be collapsed into NormativeEffectEvent",
    "Design taxonomy is not CTV runtime, amendment micro-event execution, or legal correctness",
    "Lifecycle: event taxonomy design [proposed]; executable separation remains deferred",
];

/// Classify a legislative event kind against the ADR-0017/TSG-002 boundary.
///
/// Always returns `DesignOnly` for the closed inventory. This is intentional:
/// naming the separation must not mint an executable CTV event runtime.
pub fn classify_legislative_event_kind(kind: LegislativeEventKind) -> LegislativeEventKindBoundary {
    LegislativeEventKindBoundary {
        kind,
        class: LegislativeEventKindClass::DesignOnly,
        non_claims: F07_NON_CLAIMS.to_vec(),
    }
}

/// Fail-closed rejection of treating a text/structure change as normative effect
/// (RC11-F07 / TSG-002).
pub fn reject_text_change_as_normative_effect() -> LegislativeEventKindBoundary {
    let mut boundary = classify_legislative_event_kind(LegislativeEventKind::TextChange);
    boundary.non_claims = [
        F07_NON_CLAIMS,
        &[
            "TextChangeEvent does not prove NormativeEffectEvent",
            "Hostile substitution of text change for legal effect is rejected",
        ],
    ]
    .concat();
    boundary
}

/// Orthogonal normative reasoning dimensions that must not be collapsed
/// (RC11-F09 / TSG-004 / ADR-0018 + temporal model §6).
///
/// Design inventory only. Presence of the enum does not implement a
/// NormativeState resolver, CTV join, applicability decision, or epistemic
/// knowledge base.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NormativeDimension {
    /// Force/status at a governing time (`InForce`, `Suspended`, …) — ADR-0018.
    ForceStatus,
    /// Version/text relation (CTV/edition lineage) — ADR-0017; not force.
    VersionRelation,
    /// Case applicability decision/trace — ADR-0023; not force or text.
    Applicability,
    /// System/epistemic knowledge outcome (what is known vs Unknown/Conflict).
    EpistemicOutcome,
}

impl NormativeDimension {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ForceStatus => "force_status",
            Self::VersionRelation => "version_relation",
            Self::Applicability => "applicability",
            Self::EpistemicOutcome => "epistemic_outcome",
        }
    }

    pub fn all() -> [NormativeDimension; 4] {
        [
            Self::ForceStatus,
            Self::VersionRelation,
            Self::Applicability,
            Self::EpistemicOutcome,
        ]
    }
}

/// Classification of a normative dimension relative to executable product runtime.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NormativeDimensionClass {
    /// Named and separated in design; not a mixed mega-type runtime.
    DesignOrthogonal,
    /// Reserved for a future executable dimension owner/resolver.
    ExecutableRuntime,
}

impl NormativeDimensionClass {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::DesignOrthogonal => "design_orthogonal",
            Self::ExecutableRuntime => "executable_runtime",
        }
    }
}

/// Design-boundary answer for NormativeState dimensional separation (RC11-F09).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormativeDimensionBoundary {
    pub dimension: NormativeDimension,
    pub class: NormativeDimensionClass,
    pub non_claims: Vec<&'static str>,
}

const F09_NON_CLAIMS: &[&str] = &[
    "NormativeState must not mix force, version relation, applicability, and epistemic outcome",
    "Text/CTV presence does not imply InForce",
    "InForce does not imply Applicable",
    "Unknown/Conflict epistemic outcomes are not force or applicability decisions",
    "Design dimensional separation is not a NormativeState resolver or product legal correctness",
    "Lifecycle: NormativeState design [proposed]; executable dimensional resolvers remain deferred",
];

/// Classify a normative dimension against the ADR-0018/TSG-004 boundary.
///
/// Always returns `DesignOrthogonal` for the closed inventory. Naming the
/// separation must not mint a mixed mega-type or executable resolver.
pub fn classify_normative_dimension(dimension: NormativeDimension) -> NormativeDimensionBoundary {
    NormativeDimensionBoundary {
        dimension,
        class: NormativeDimensionClass::DesignOrthogonal,
        non_claims: F09_NON_CLAIMS.to_vec(),
    }
}

/// Fail-closed rejection of collapsing force into applicability (RC11-F09).
pub fn reject_force_as_applicability() -> NormativeDimensionBoundary {
    let mut boundary = classify_normative_dimension(NormativeDimension::ForceStatus);
    boundary.non_claims = [
        F09_NON_CLAIMS,
        &[
            "ForceStatus does not decide Applicability",
            "Hostile substitution of InForce for Applicable is rejected",
        ],
    ]
    .concat();
    boundary
}

/// Fail-closed rejection of treating version/text presence as force (RC11-F09).
pub fn reject_version_relation_as_force() -> NormativeDimensionBoundary {
    let mut boundary = classify_normative_dimension(NormativeDimension::VersionRelation);
    boundary.non_claims = [
        F09_NON_CLAIMS,
        &[
            "VersionRelation/CTV presence does not imply ForceStatus InForce",
            "Hostile substitution of text presence for InForce is rejected",
        ],
    ]
    .concat();
    boundary
}

// ─── RC11-F08 / TSG-003/013: CTV structural membership + industrial ops ─────
// Fail-closed pure structural spine only. Not a full CTV resolver, not legal
// amendment correctness, not corpus compilation product readiness.

id_type!(ComponentConceptId, "component concept id");
id_type!(CtvId, "ctv id");
id_type!(AmendingActId, "amending act id");
id_type!(IndustrialOpId, "industrial op id");

/// Closed industrial CTV operations (ADR-0017 micro-event surface, RC11-F08).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CtvIndustrialOpKind {
    Renumber,
    Move,
    Split,
    Merge,
}

impl CtvIndustrialOpKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Renumber => "renumber",
            Self::Move => "move",
            Self::Split => "split",
            Self::Merge => "merge",
        }
    }

    pub fn all() -> [CtvIndustrialOpKind; 4] {
        [Self::Renumber, Self::Move, Self::Split, Self::Merge]
    }
}

/// Structural membership edge parent_cc → child_cc (R67-style composition only).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MembershipEdge {
    parent: ComponentConceptId,
    child: ComponentConceptId,
}

impl MembershipEdge {
    pub fn try_new(
        parent: ComponentConceptId,
        child: ComponentConceptId,
    ) -> Result<Self, CtvOpsError> {
        if parent.as_str() == child.as_str() {
            return Err(CtvOpsError::SelfMembership);
        }
        Ok(Self { parent, child })
    }

    pub fn parent(&self) -> &ComponentConceptId {
        &self.parent
    }

    pub fn child(&self) -> &ComponentConceptId {
        &self.child
    }
}

/// In-memory structural membership graph (not a temporal CTV store).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct MembershipGraph {
    edges: Vec<MembershipEdge>,
}

impl MembershipGraph {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn edges(&self) -> &[MembershipEdge] {
        &self.edges
    }

    pub fn insert(&mut self, edge: MembershipEdge) -> Result<(), CtvOpsError> {
        if self.edges.iter().any(|e| {
            e.parent.as_str() == edge.parent.as_str() && e.child.as_str() == edge.child.as_str()
        }) {
            return Err(CtvOpsError::DuplicateMembership);
        }
        // Reject immediate reverse edge (A→B and B→A) as a minimal cycle guard.
        if self.edges.iter().any(|e| {
            e.parent.as_str() == edge.child.as_str() && e.child.as_str() == edge.parent.as_str()
        }) {
            return Err(CtvOpsError::MembershipCycle);
        }
        // Reject if child already has a different parent (single-parent structural rule).
        if self
            .edges
            .iter()
            .any(|e| e.child.as_str() == edge.child.as_str())
        {
            return Err(CtvOpsError::MultipleParents);
        }
        self.edges.push(edge);
        Ok(())
    }

    pub fn parent_of(&self, child: &ComponentConceptId) -> Option<&ComponentConceptId> {
        self.edges
            .iter()
            .find(|e| e.child.as_str() == child.as_str())
            .map(|e| &e.parent)
    }

    pub fn children_of(&self, parent: &ComponentConceptId) -> Vec<&ComponentConceptId> {
        self.edges
            .iter()
            .filter(|e| e.parent.as_str() == parent.as_str())
            .map(|e| &e.child)
            .collect()
    }
}

/// Fail-closed errors for structural membership / industrial ops (RC11-F08).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CtvOpsError {
    InvalidId(IdError),
    SelfMembership,
    DuplicateMembership,
    MembershipCycle,
    MultipleParents,
    MissingProvenance,
    InvalidArity,
    UnknownSubject,
    TargetCollision,
    WholeActIncomplete,
}

impl fmt::Display for CtvOpsError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidId(err) => write!(formatter, "{err}"),
            Self::SelfMembership => {
                write!(formatter, "component cannot be its own structural parent")
            }
            Self::DuplicateMembership => write!(formatter, "duplicate membership edge"),
            Self::MembershipCycle => write!(formatter, "membership cycle rejected"),
            Self::MultipleParents => {
                write!(formatter, "child already has a structural parent")
            }
            Self::MissingProvenance => {
                write!(formatter, "industrial op requires amending-act provenance")
            }
            Self::InvalidArity => write!(formatter, "industrial op arity is invalid"),
            Self::UnknownSubject => write!(formatter, "industrial op subject is unknown in graph"),
            Self::TargetCollision => {
                write!(formatter, "industrial op target collides with subject")
            }
            Self::WholeActIncomplete => {
                write!(
                    formatter,
                    "whole-act compile is fail-closed on incomplete membership"
                )
            }
        }
    }
}

impl Error for CtvOpsError {}

impl From<IdError> for CtvOpsError {
    fn from(value: IdError) -> Self {
        Self::InvalidId(value)
    }
}

/// Request to plan a structural industrial operation (not legal-effect execution).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndustrialOpRequest {
    pub op_id: IndustrialOpId,
    pub kind: CtvIndustrialOpKind,
    pub subjects: Vec<ComponentConceptId>,
    pub targets: Vec<ComponentConceptId>,
    pub provenance: AmendingActId,
}

/// Planned structural effects only — never a legal validity claim.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndustrialOpPlan {
    pub op_id: IndustrialOpId,
    pub kind: CtvIndustrialOpKind,
    pub provenance: AmendingActId,
    pub notes: Vec<&'static str>,
}

const F08_NON_CLAIMS: &[&str] = &[
    "Structural membership and industrial ops are not full CTV temporal resolution",
    "Does not prove legal amendment correctness or real-corpus compilation",
    "Renumber/move/split/merge plans are structural only; not NormativeEffect events",
    "Whole-act compile remains fail-closed; incomplete membership never assembles partially",
    "Lifecycle [proposed]; not product readiness or legal validation",
];

pub fn ctv_ops_non_claims() -> Vec<&'static str> {
    F08_NON_CLAIMS.to_vec()
}

/// Plan a fail-closed industrial op. Does not mutate legal force or CTV intervals.
pub fn plan_industrial_op(
    graph: &MembershipGraph,
    request: &IndustrialOpRequest,
) -> Result<IndustrialOpPlan, CtvOpsError> {
    if request.provenance.as_str().is_empty() {
        return Err(CtvOpsError::MissingProvenance);
    }
    match request.kind {
        CtvIndustrialOpKind::Renumber => {
            // one subject, one target label/id, subject must exist as node (edge endpoint or free).
            if request.subjects.len() != 1 || request.targets.len() != 1 {
                return Err(CtvOpsError::InvalidArity);
            }
            if request.subjects[0].as_str() == request.targets[0].as_str() {
                return Err(CtvOpsError::TargetCollision);
            }
        }
        CtvIndustrialOpKind::Move => {
            // subject moved under new parent target; both ids required; subject known as child or free.
            if request.subjects.len() != 1 || request.targets.len() != 1 {
                return Err(CtvOpsError::InvalidArity);
            }
            if request.subjects[0].as_str() == request.targets[0].as_str() {
                return Err(CtvOpsError::TargetCollision);
            }
            // If subject currently has a parent, move is allowed; unknown free subject is ok.
            let _ = graph.parent_of(&request.subjects[0]);
        }
        CtvIndustrialOpKind::Split => {
            // one subject split into >=2 targets
            if request.subjects.len() != 1 || request.targets.len() < 2 {
                return Err(CtvOpsError::InvalidArity);
            }
            if request
                .targets
                .iter()
                .any(|t| t.as_str() == request.subjects[0].as_str())
            {
                return Err(CtvOpsError::TargetCollision);
            }
            // duplicate targets rejected
            let mut seen = Vec::new();
            for t in &request.targets {
                if seen.contains(&t.as_str()) {
                    return Err(CtvOpsError::TargetCollision);
                }
                seen.push(t.as_str());
            }
        }
        CtvIndustrialOpKind::Merge => {
            // >=2 subjects merge into one target
            if request.subjects.len() < 2 || request.targets.len() != 1 {
                return Err(CtvOpsError::InvalidArity);
            }
            let target = request.targets[0].as_str();
            if request.subjects.iter().any(|s| s.as_str() == target) {
                return Err(CtvOpsError::TargetCollision);
            }
            let mut seen = Vec::new();
            for s in &request.subjects {
                if seen.contains(&s.as_str()) {
                    return Err(CtvOpsError::TargetCollision);
                }
                seen.push(s.as_str());
            }
        }
    }
    Ok(IndustrialOpPlan {
        op_id: request.op_id.clone(),
        kind: request.kind,
        provenance: request.provenance.clone(),
        notes: F08_NON_CLAIMS.to_vec(),
    })
}

/// Fail-closed whole-act structural compile gate over membership completeness.
///
/// `required_components` must all appear as an edge endpoint (parent or child).
/// Missing any component → WholeActIncomplete (never partial assembly).
pub fn whole_act_structural_compile(
    graph: &MembershipGraph,
    required_components: &[ComponentConceptId],
) -> Result<(), CtvOpsError> {
    for cc in required_components {
        let present = graph
            .edges()
            .iter()
            .any(|e| e.parent().as_str() == cc.as_str() || e.child().as_str() == cc.as_str());
        if !present {
            return Err(CtvOpsError::WholeActIncomplete);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn five_clocks_are_distinct() {
        assert_eq!(ClockKind::all().len(), 5);
        assert_eq!(ClockKind::FactualEvent.as_str(), "factual_event");
        assert_eq!(ClockKind::SystemObservation.as_str(), "system_observation");
    }

    #[test]
    fn resolved_is_not_fail_closed() {
        assert!(!ResolutionOutcome::Resolved.is_fail_closed());
        assert!(ResolutionOutcome::SubstituteRejected.is_fail_closed());
    }
}
