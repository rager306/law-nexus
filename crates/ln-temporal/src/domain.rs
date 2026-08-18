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

// ─── TSG-004 S2/S3: force-status NormativeState bounded resolver (ADR-0018) ──
// Force dimension only. Not CTV join, not applicability, not legal corpus proof.

/// Canonical force/status values (ADR-0018). `Unknown` is fail-closed outcome only,
/// never a transition target written into the timeline.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum NormativeState {
    InForce,
    Suspended,
    Repealed,
    Superseded,
    Transitional,
    Unknown,
}

impl NormativeState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::InForce => "in_force",
            Self::Suspended => "suspended",
            Self::Repealed => "repealed",
            Self::Superseded => "superseded",
            Self::Transitional => "transitional",
            Self::Unknown => "unknown",
        }
    }

    pub fn is_transition_target(self) -> bool {
        !matches!(self, Self::Unknown)
    }
}

/// Fail-closed errors for force-status timeline / resolver.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NormativeStateError {
    InvalidId(IdError),
    MissingProvenance,
    UnknownNotTransition,
    EmptyComponent,
}

impl fmt::Display for NormativeStateError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::InvalidId(err) => write!(formatter, "{err}"),
            Self::MissingProvenance => {
                write!(
                    formatter,
                    "force-status event requires amending-act provenance"
                )
            }
            Self::UnknownNotTransition => {
                write!(
                    formatter,
                    "Unknown is a fail-closed outcome, not a transition status"
                )
            }
            Self::EmptyComponent => write!(formatter, "component concept id is required"),
        }
    }
}

impl Error for NormativeStateError {}

impl From<IdError> for NormativeStateError {
    fn from(value: IdError) -> Self {
        Self::InvalidId(value)
    }
}

/// Evidence-gated force-status transition (not CTV text, not applicability).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ForceStatusEvent {
    component: ComponentConceptId,
    status: NormativeState,
    /// Governing legal-act-effect day ordinal (synthetic offline unit; not wall clock).
    effect_day: i64,
    provenance: AmendingActId,
}

impl ForceStatusEvent {
    pub fn try_new(
        component: ComponentConceptId,
        status: NormativeState,
        effect_day: i64,
        provenance: AmendingActId,
    ) -> Result<Self, NormativeStateError> {
        if !status.is_transition_target() {
            return Err(NormativeStateError::UnknownNotTransition);
        }
        if provenance.as_str().is_empty() {
            return Err(NormativeStateError::MissingProvenance);
        }
        if component.as_str().is_empty() {
            return Err(NormativeStateError::EmptyComponent);
        }
        Ok(Self {
            component,
            status,
            effect_day,
            provenance,
        })
    }

    /// Test/helper path that parses component + provenance and rejects empty provenance.
    pub fn try_new_raw(
        component: &str,
        status: NormativeState,
        effect_day: i64,
        provenance: &str,
    ) -> Result<Self, NormativeStateError> {
        if provenance.is_empty() {
            return Err(NormativeStateError::MissingProvenance);
        }
        let component = ComponentConceptId::parse(component)?;
        let provenance = AmendingActId::parse(provenance)?;
        Self::try_new(component, status, effect_day, provenance)
    }

    pub fn component(&self) -> &ComponentConceptId {
        &self.component
    }

    pub fn status(&self) -> NormativeState {
        self.status
    }

    pub fn effect_day(&self) -> i64 {
        self.effect_day
    }

    pub fn provenance(&self) -> &AmendingActId {
        &self.provenance
    }
}

/// Append-only force-status timeline (offline synthetic; not product corpus store).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ForceStatusTimeline {
    events: Vec<ForceStatusEvent>,
}

impl ForceStatusTimeline {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn events(&self) -> &[ForceStatusEvent] {
        &self.events
    }

    pub fn append(&mut self, event: ForceStatusEvent) -> Result<(), NormativeStateError> {
        // Re-validate transition target (defense in depth).
        if !event.status.is_transition_target() {
            return Err(NormativeStateError::UnknownNotTransition);
        }
        self.events.push(event);
        Ok(())
    }
}

/// Force-status resolution result (ADR-0018 force dimension only).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ForceStatusResolution {
    pub component: ComponentConceptId,
    pub as_of_day: i64,
    pub status: NormativeState,
    pub conflict: bool,
    pub dimension: NormativeDimension,
    pub non_claims: Vec<&'static str>,
}

const FORCE_RESOLVER_NON_CLAIMS: &[&str] = &[
    "ForceStatus resolution is not CTV text presence or version join",
    "InForce does not imply Applicability",
    "Offline synthetic force timeline is not legal corpus status proof",
    "Unknown is fail-closed default when evidence is missing or conflicting",
    "Lifecycle [proposed]; not product readiness or legal validation",
];

/// Resolve force/status for a component at a governing effect day.
///
/// Rules (fail-closed, ADR-0018):
/// - no prior event → `Unknown` (never assume `InForce`)
/// - latest event with `effect_day <= as_of_day` wins
/// - same max day with distinct statuses → `Unknown` + conflict
/// - never mixes version relation or applicability
pub fn resolve_force_status_at(
    timeline: &ForceStatusTimeline,
    component: &ComponentConceptId,
    as_of_day: i64,
) -> Result<ForceStatusResolution, NormativeStateError> {
    if component.as_str().is_empty() {
        return Err(NormativeStateError::EmptyComponent);
    }

    let applicable: Vec<&ForceStatusEvent> = timeline
        .events()
        .iter()
        .filter(|e| e.component().as_str() == component.as_str() && e.effect_day() <= as_of_day)
        .collect();

    if applicable.is_empty() {
        return Ok(ForceStatusResolution {
            component: component.clone(),
            as_of_day,
            status: NormativeState::Unknown,
            conflict: false,
            dimension: NormativeDimension::ForceStatus,
            non_claims: [F09_NON_CLAIMS, FORCE_RESOLVER_NON_CLAIMS].concat(),
        });
    }

    let max_day = applicable
        .iter()
        .map(|e| e.effect_day())
        .max()
        .expect("non-empty applicable");
    let at_max: Vec<&ForceStatusEvent> = applicable
        .into_iter()
        .filter(|e| e.effect_day() == max_day)
        .collect();

    let mut statuses: Vec<NormativeState> = at_max.iter().map(|e| e.status()).collect();
    statuses.sort_by_key(|s| s.as_str());
    statuses.dedup();

    if statuses.len() > 1 {
        return Ok(ForceStatusResolution {
            component: component.clone(),
            as_of_day,
            status: NormativeState::Unknown,
            conflict: true,
            dimension: NormativeDimension::ForceStatus,
            non_claims: [F09_NON_CLAIMS, FORCE_RESOLVER_NON_CLAIMS].concat(),
        });
    }

    Ok(ForceStatusResolution {
        component: component.clone(),
        as_of_day,
        status: statuses[0],
        conflict: false,
        dimension: NormativeDimension::ForceStatus,
        non_claims: [F09_NON_CLAIMS, FORCE_RESOLVER_NON_CLAIMS].concat(),
    })
}

// ─── KBO-R012 / O2: offline force↔CTV membership join ───────────────────────
// Pure join by ComponentConceptId. Not CTV text store, not Applicable, not corpus.

/// Offline join of force-status resolution with structural membership context.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ForceMembershipJoin {
    pub component: ComponentConceptId,
    pub as_of_day: i64,
    pub force: ForceStatusResolution,
    /// True when component appears as parent or child in membership edges.
    pub structural_known: bool,
    pub parent: Option<ComponentConceptId>,
    pub children: Vec<ComponentConceptId>,
    /// Always false: join never mints applicability decisions.
    pub claims_applicability: bool,
    pub non_claims: Vec<&'static str>,
}

const FORCE_CTV_JOIN_NON_CLAIMS: &[&str] = &[
    "Force↔membership join is offline structural only; not CTV text edition store",
    "Structural membership does not imply ForceStatus InForce",
    "InForce after join still does not imply Applicability",
    "Not multi-provider identity, not corpus status edges, not product readiness",
    "Lifecycle [proposed]; KBO-R012 partial; not O3 fixture edges",
];

/// Join force-status resolution with CTV structural membership for one component.
///
/// Fail-closed rules:
/// - force via `resolve_force_status_at` (missing/conflict → Unknown)
/// - membership presence never upgrades force to InForce
/// - never sets `claims_applicability`
pub fn join_force_with_membership(
    timeline: &ForceStatusTimeline,
    graph: &MembershipGraph,
    component: &ComponentConceptId,
    as_of_day: i64,
) -> Result<ForceMembershipJoin, NormativeStateError> {
    let force = resolve_force_status_at(timeline, component, as_of_day)?;
    let parent = graph.parent_of(component).cloned();
    let children: Vec<ComponentConceptId> =
        graph.children_of(component).into_iter().cloned().collect();
    let structural_known = parent.is_some()
        || !children.is_empty()
        || graph.edges().iter().any(|e| {
            e.parent().as_str() == component.as_str() || e.child().as_str() == component.as_str()
        });

    Ok(ForceMembershipJoin {
        component: component.clone(),
        as_of_day,
        force,
        structural_known,
        parent,
        children,
        claims_applicability: false,
        non_claims: [
            F09_NON_CLAIMS,
            FORCE_RESOLVER_NON_CLAIMS,
            FORCE_CTV_JOIN_NON_CLAIMS,
        ]
        .concat(),
    })
}

// ─── RC11-F08 / TSG-003/013: CTV structural membership + industrial ops ─────
// Fail-closed pure structural spine only. Not a full CTV resolver, not legal
// amendment correctness, not corpus compilation product readiness.

/// ComponentConceptId (D191): ASCII slash permitted only here, as a path
/// separator (`cc:work:statya-93/punkt-4/punkt-4.2`). Every slash-separated
/// segment must be non-empty — leading/trailing/double slash is IdError.
/// Other id_type! parsers keep rejecting slash. MAX_ID_LEN stays 64;
/// deeper paths quarantine in the caller, not by widening the charset.
fn parse_component_concept_id(value: &str) -> Result<String, IdError> {
    if value.is_empty() {
        return Err(IdError {
            kind: "component concept id",
            reason: "empty",
        });
    }
    if value.len() > MAX_ID_LEN {
        return Err(IdError {
            kind: "component concept id",
            reason: "too long",
        });
    }
    if !value
        .bytes()
        .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b':' | b'.' | b'/'))
    {
        return Err(IdError {
            kind: "component concept id",
            reason: "unsupported character",
        });
    }
    if value.split('/').any(str::is_empty) {
        return Err(IdError {
            kind: "component concept id",
            reason: "empty path segment",
        });
    }
    Ok(value.to_owned())
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ComponentConceptId(String);

impl ComponentConceptId {
    pub fn parse(value: &str) -> Result<Self, IdError> {
        parse_component_concept_id(value).map(Self)
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

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
    PlanMismatch,
    DuplicateOpId,
    MembershipConflict,
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
            Self::PlanMismatch => {
                write!(formatter, "apply requires a plan matching the request")
            }
            Self::DuplicateOpId => {
                write!(formatter, "industrial op id already present in event log")
            }
            Self::MembershipConflict => {
                write!(
                    formatter,
                    "child has conflicting parents at the same effect day"
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

// ─── TSG-003/013 S3: bounded-runtime apply + structural event log ───────────
// Offline synthetic apply only. Not temporal CTV store, not legal effect.

/// Append-only structural industrial-op event (not NormativeEffect).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralIndustrialEvent {
    pub op_id: IndustrialOpId,
    pub kind: CtvIndustrialOpKind,
    pub subjects: Vec<ComponentConceptId>,
    pub targets: Vec<ComponentConceptId>,
    pub provenance: AmendingActId,
}

/// In-memory append-only log of applied structural ops.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct StructuralEventLog {
    events: Vec<StructuralIndustrialEvent>,
}

impl StructuralEventLog {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn events(&self) -> &[StructuralIndustrialEvent] {
        &self.events
    }

    fn contains_op(&self, op_id: &IndustrialOpId) -> bool {
        self.events
            .iter()
            .any(|e| e.op_id.as_str() == op_id.as_str())
    }
}

/// Receipt from a successful structural apply (bounded runtime).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndustrialOpApplyReceipt {
    pub op_id: IndustrialOpId,
    pub kind: CtvIndustrialOpKind,
    pub non_claims: Vec<&'static str>,
}

const S3_APPLY_NON_CLAIMS: &[&str] = &[
    "Structural membership apply is not full CTV temporal resolution",
    "Does not prove legal amendment correctness or real-corpus compilation",
    "Append-only structural events are not NormativeEffectEvent runtime",
    "Bounded offline apply only; lifecycle [proposed]; not product readiness",
];

fn remove_edges_involving(graph: &mut MembershipGraph, id: &ComponentConceptId) {
    graph
        .edges
        .retain(|e| e.parent.as_str() != id.as_str() && e.child.as_str() != id.as_str());
}

fn rewrite_component_id(
    graph: &mut MembershipGraph,
    from: &ComponentConceptId,
    to: &ComponentConceptId,
) -> Result<(), CtvOpsError> {
    if from.as_str() == to.as_str() {
        return Err(CtvOpsError::TargetCollision);
    }
    // Collision if `to` already appears as any endpoint.
    if graph
        .edges
        .iter()
        .any(|e| e.parent.as_str() == to.as_str() || e.child.as_str() == to.as_str())
    {
        return Err(CtvOpsError::TargetCollision);
    }
    for edge in &mut graph.edges {
        if edge.parent.as_str() == from.as_str() {
            edge.parent = to.clone();
        }
        if edge.child.as_str() == from.as_str() {
            edge.child = to.clone();
        }
    }
    Ok(())
}

/// Apply a planned industrial op: mutate membership graph and append a
/// structural event. Requires `plan` to match `request` (op_id, kind, provenance).
///
/// Not a temporal CTV resolver and not legal-effect determination.
pub fn apply_industrial_op(
    graph: &mut MembershipGraph,
    log: &mut StructuralEventLog,
    request: &IndustrialOpRequest,
    plan: &IndustrialOpPlan,
) -> Result<IndustrialOpApplyReceipt, CtvOpsError> {
    if plan.op_id.as_str() != request.op_id.as_str()
        || plan.kind != request.kind
        || plan.provenance.as_str() != request.provenance.as_str()
    {
        return Err(CtvOpsError::PlanMismatch);
    }
    // Re-validate against current graph (fail-closed; plan is not a capability claim).
    plan_industrial_op(graph, request)?;
    if log.contains_op(&request.op_id) {
        return Err(CtvOpsError::DuplicateOpId);
    }

    match request.kind {
        CtvIndustrialOpKind::Move => {
            let subject = &request.subjects[0];
            let new_parent = &request.targets[0];
            // Drop existing parent edge for subject if any.
            graph.edges.retain(|e| e.child.as_str() != subject.as_str());
            graph.insert(MembershipEdge::try_new(
                new_parent.clone(),
                subject.clone(),
            )?)?;
        }
        CtvIndustrialOpKind::Renumber => {
            let from = &request.subjects[0];
            let to = &request.targets[0];
            rewrite_component_id(graph, from, to)?;
        }
        CtvIndustrialOpKind::Split => {
            let subject = &request.subjects[0];
            let parent = graph.parent_of(subject).cloned();
            remove_edges_involving(graph, subject);
            if let Some(parent) = parent {
                for target in &request.targets {
                    graph.insert(MembershipEdge::try_new(parent.clone(), target.clone())?)?;
                }
            }
            // Free subject with no parent: targets remain free (structure only).
        }
        CtvIndustrialOpKind::Merge => {
            let target = &request.targets[0];
            // Prefer parent of first subject that has one.
            let mut parent: Option<ComponentConceptId> = None;
            for subject in &request.subjects {
                if let Some(p) = graph.parent_of(subject) {
                    parent = Some(p.clone());
                    break;
                }
            }
            for subject in &request.subjects {
                remove_edges_involving(graph, subject);
            }
            if let Some(parent) = parent {
                graph.insert(MembershipEdge::try_new(parent, target.clone())?)?;
            }
        }
    }

    log.events.push(StructuralIndustrialEvent {
        op_id: request.op_id.clone(),
        kind: request.kind,
        subjects: request.subjects.clone(),
        targets: request.targets.clone(),
        provenance: request.provenance.clone(),
    });

    Ok(IndustrialOpApplyReceipt {
        op_id: request.op_id.clone(),
        kind: request.kind,
        non_claims: [F08_NON_CLAIMS, S3_APPLY_NON_CLAIMS].concat(),
    })
}

// ─── TSG-013 / KBO fold: versioned membership → StructuralAst projection ─────
// Canonical source is the event log. AST is a view at effect_day t, not canon,
// not CTV text, not force, not a stored document tree.

/// Attach or detach a child under a parent at a governing effect day.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum MembershipChangeKind {
    Attach,
    Detach,
}

impl MembershipChangeKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Attach => "attach",
            Self::Detach => "detach",
        }
    }
}

/// Provenance-gated membership change (not CTV text, not legal effect).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VersionedMembershipEvent {
    kind: MembershipChangeKind,
    parent: ComponentConceptId,
    child: ComponentConceptId,
    effect_day: i64,
    provenance: AmendingActId,
}

impl VersionedMembershipEvent {
    pub fn try_new(
        kind: MembershipChangeKind,
        parent: ComponentConceptId,
        child: ComponentConceptId,
        effect_day: i64,
        provenance: AmendingActId,
    ) -> Result<Self, CtvOpsError> {
        if parent.as_str() == child.as_str() {
            return Err(CtvOpsError::SelfMembership);
        }
        if provenance.as_str().is_empty() {
            return Err(CtvOpsError::MissingProvenance);
        }
        Ok(Self {
            kind,
            parent,
            child,
            effect_day,
            provenance,
        })
    }

    pub fn kind(&self) -> MembershipChangeKind {
        self.kind
    }

    pub fn parent(&self) -> &ComponentConceptId {
        &self.parent
    }

    pub fn child(&self) -> &ComponentConceptId {
        &self.child
    }

    pub fn effect_day(&self) -> i64 {
        self.effect_day
    }

    pub fn provenance(&self) -> &AmendingActId {
        &self.provenance
    }
}

/// Append-only versioned membership log (offline synthetic).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct VersionedMembershipLog {
    events: Vec<VersionedMembershipEvent>,
}

impl VersionedMembershipLog {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn events(&self) -> &[VersionedMembershipEvent] {
        &self.events
    }

    pub fn append(&mut self, event: VersionedMembershipEvent) -> Result<(), CtvOpsError> {
        self.events.push(event);
        Ok(())
    }
}

/// One node of a structural AST projection (not a stored document node).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralAstNode {
    component: ComponentConceptId,
    children: Vec<StructuralAstNode>,
}

impl StructuralAstNode {
    pub fn component(&self) -> &ComponentConceptId {
        &self.component
    }

    pub fn children(&self) -> &[StructuralAstNode] {
        &self.children
    }
}

/// Folded membership tree at a governing effect day.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralAst {
    as_of_day: i64,
    roots: Vec<StructuralAstNode>,
    non_claims: Vec<&'static str>,
}

impl StructuralAst {
    pub fn as_of_day(&self) -> i64 {
        self.as_of_day
    }

    pub fn roots(&self) -> &[StructuralAstNode] {
        &self.roots
    }

    pub fn is_projection(&self) -> bool {
        true
    }

    pub fn non_claims(&self) -> &[&'static str] {
        &self.non_claims
    }

    /// Keep nodes that are present or have a present descendant. Projection only.
    pub fn filter_to_components(&self, present: &[&ComponentConceptId]) -> Self {
        let ids: Vec<&str> = present.iter().map(|c| c.as_str()).collect();
        let roots: Vec<StructuralAstNode> = self
            .roots
            .iter()
            .filter_map(|root| filter_node(root, &ids))
            .collect();
        Self {
            as_of_day: self.as_of_day,
            roots,
            non_claims: self.non_claims.clone(),
        }
    }
}

fn filter_node(node: &StructuralAstNode, present: &[&str]) -> Option<StructuralAstNode> {
    let children: Vec<StructuralAstNode> = node
        .children()
        .iter()
        .filter_map(|child| filter_node(child, present))
        .collect();
    let keep = present.contains(&node.component().as_str()) || !children.is_empty();
    if !keep {
        return None;
    }
    Some(StructuralAstNode {
        component: node.component().clone(),
        children,
    })
}

const FOLD_NON_CLAIMS: &[&str] = &[
    "StructuralAst is a fold projection, not canon and not a stored document tree",
    "Versioned membership is not CTV text resolution or legal amendment correctness",
    "Tree presence does not imply ForceStatus InForce",
    "Not Expression binding, not Manifestation, not applicability, not corpus proof",
    "Lifecycle [proposed]; TSG-013 fold spine; not O3 representative fixtures",
];

/// Fold membership events with `effect_day <= as_of_day` into a StructuralAst.
///
/// Same-day attach of one child under two parents → MembershipConflict.
/// Future events are invisible. Detach then attach is a move.
pub fn fold_membership_at(
    log: &VersionedMembershipLog,
    as_of_day: i64,
) -> Result<StructuralAst, CtvOpsError> {
    let mut applicable: Vec<&VersionedMembershipEvent> = log
        .events()
        .iter()
        .filter(|e| e.effect_day() <= as_of_day)
        .collect();
    applicable.sort_by_key(|e| {
        (
            e.effect_day(),
            e.kind().as_str(),
            e.child().as_str(),
            e.parent().as_str(),
        )
    });

    // child → parent after replay
    let mut parent_of: Vec<(String, String)> = Vec::new();

    let mut i = 0;
    while i < applicable.len() {
        let day = applicable[i].effect_day();
        let mut j = i;
        while j < applicable.len() && applicable[j].effect_day() == day {
            j += 1;
        }
        let slice = &applicable[i..j];

        // Same-day attach of one child under distinct parents is a conflict,
        // even if an intervening detach exists in the same day (ambiguous order).
        let mut attach_parents: Vec<(String, String)> = Vec::new();
        for ev in slice.iter() {
            if ev.kind() == MembershipChangeKind::Attach {
                attach_parents.push((
                    ev.child().as_str().to_owned(),
                    ev.parent().as_str().to_owned(),
                ));
            }
        }
        attach_parents.sort();
        let mut k = 0;
        while k < attach_parents.len() {
            let child = attach_parents[k].0.clone();
            let mut parents = vec![attach_parents[k].1.clone()];
            k += 1;
            while k < attach_parents.len() && attach_parents[k].0 == child {
                if !parents.contains(&attach_parents[k].1) {
                    parents.push(attach_parents[k].1.clone());
                }
                k += 1;
            }
            if parents.len() > 1 {
                return Err(CtvOpsError::MembershipConflict);
            }
        }

        for ev in slice {
            match ev.kind() {
                MembershipChangeKind::Detach => {
                    parent_of
                        .retain(|(c, p)| !(c == ev.child().as_str() && p == ev.parent().as_str()));
                }
                MembershipChangeKind::Attach => {
                    parent_of.retain(|(c, _)| c != ev.child().as_str());
                    parent_of.push((
                        ev.child().as_str().to_owned(),
                        ev.parent().as_str().to_owned(),
                    ));
                }
            }
        }
        i = j;
    }

    let ast = build_structural_ast(as_of_day, &parent_of)?;
    Ok(ast)
}

fn build_structural_ast(
    as_of_day: i64,
    parent_of: &[(String, String)],
) -> Result<StructuralAst, CtvOpsError> {
    let mut children_of: Vec<(String, Vec<String>)> = Vec::new();
    let mut child_set: Vec<String> = Vec::new();
    let mut parent_set: Vec<String> = Vec::new();
    for (child, parent) in parent_of {
        if !child_set.contains(child) {
            child_set.push(child.clone());
        }
        if !parent_set.contains(parent) {
            parent_set.push(parent.clone());
        }
        if let Some((_, kids)) = children_of.iter_mut().find(|(p, _)| p == parent) {
            if !kids.contains(child) {
                kids.push(child.clone());
            }
        } else {
            children_of.push((parent.clone(), vec![child.clone()]));
        }
    }
    for (_, kids) in &mut children_of {
        kids.sort();
    }

    let mut roots: Vec<String> = parent_set
        .into_iter()
        .filter(|p| !child_set.contains(p))
        .collect();
    roots.sort();

    let nodes: Vec<StructuralAstNode> = roots
        .iter()
        .map(|root| build_node(root, &children_of))
        .collect();

    Ok(StructuralAst {
        as_of_day,
        roots: nodes,
        non_claims: FOLD_NON_CLAIMS.to_vec(),
    })
}

fn build_node(id: &str, children_of: &[(String, Vec<String>)]) -> StructuralAstNode {
    let kids = children_of
        .iter()
        .find(|(p, _)| p == id)
        .map(|(_, k)| k.clone())
        .unwrap_or_default();
    StructuralAstNode {
        component: ComponentConceptId::parse(id).expect("folded ids are already valid"),
        children: kids.iter().map(|k| build_node(k, children_of)).collect(),
    }
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
