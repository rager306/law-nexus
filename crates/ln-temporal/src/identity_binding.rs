//! Proposed, evidence-bound identity field claims for the NPA contour.
//!
//! This module deliberately stops at candidates.  It does not mint `WorkId`,
//! resolve an identity, or turn a claim into an authoritative fact.

use crate::document_context::{BlockId, Terminal, TextSpan};

pub const MAX_IDENTITY_FIELD_CLAIMS_PER_BLOCK: usize = 32;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FieldKind {
    Type,
    Org,
    Geo,
    Date,
    Number,
    Name,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FieldSource {
    ExplicitMember,
    SameSeriesHead,
    PriorFrame,
    CurrentDocumentRequisites,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum FieldStatus {
    Explicit,
    Inherited,
    Conflicting,
    Unresolved,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityFieldClaim {
    field: FieldKind,
    block: BlockId,
    span: TextSpan,
    source: FieldSource,
    status: FieldStatus,
    compatibility_basis: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityFieldClaimError {
    EmptySpan,
}

impl IdentityFieldClaim {
    pub fn new(
        field: FieldKind,
        block: BlockId,
        span: TextSpan,
        source: FieldSource,
        status: FieldStatus,
        compatibility_basis: impl Into<String>,
    ) -> Result<Self, IdentityFieldClaimError> {
        if span.start() == span.end() {
            return Err(IdentityFieldClaimError::EmptySpan);
        }
        Ok(Self {
            field,
            block,
            span,
            source,
            status,
            compatibility_basis: compatibility_basis.into(),
        })
    }
    pub fn field(&self) -> FieldKind {
        self.field
    }
    pub fn block(&self) -> BlockId {
        self.block
    }
    pub fn span(&self) -> TextSpan {
        self.span
    }
    pub fn source(&self) -> FieldSource {
        self.source
    }
    pub fn status(&self) -> FieldStatus {
        self.status
    }
    pub fn compatibility_basis(&self) -> &str {
        &self.compatibility_basis
    }
    pub fn value(&self) -> &str {
        &self.compatibility_basis
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum ActType {
    Federal,
    PresidentialAgency,
    RegionalMunicipal,
    Other(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentifyingActCandidate {
    act_type: ActType,
    type_claim: IdentityFieldClaim,
    org: Option<IdentityFieldClaim>,
    geo: Option<IdentityFieldClaim>,
    date: Option<IdentityFieldClaim>,
    number: Option<IdentityFieldClaim>,
    title: Option<IdentityFieldClaim>,
}
impl IdentifyingActCandidate {
    /// Creates a candidate container; completeness is checked by the
    /// downstream projection, never assumed by this constructor.
    pub fn new(
        act_type: ActType,
        type_claim: IdentityFieldClaim,
        org: Option<IdentityFieldClaim>,
        geo: Option<IdentityFieldClaim>,
        date: Option<IdentityFieldClaim>,
        number: Option<IdentityFieldClaim>,
        title: Option<IdentityFieldClaim>,
    ) -> Self {
        Self {
            act_type,
            type_claim,
            org,
            geo,
            date,
            number,
            title,
        }
    }

    pub fn act_type(&self) -> &ActType {
        &self.act_type
    }
    pub fn type_claim(&self) -> &IdentityFieldClaim {
        &self.type_claim
    }
    pub fn org(&self) -> Option<&IdentityFieldClaim> {
        self.org.as_ref()
    }
    pub fn geo(&self) -> Option<&IdentityFieldClaim> {
        self.geo.as_ref()
    }
    pub fn date(&self) -> Option<&IdentityFieldClaim> {
        self.date.as_ref()
    }
    pub fn number(&self) -> Option<&IdentityFieldClaim> {
        self.number.as_ref()
    }
    pub fn title(&self) -> Option<&IdentityFieldClaim> {
        self.title.as_ref()
    }
    pub fn claims(&self) -> Vec<&IdentityFieldClaim> {
        [
            Some(&self.type_claim),
            self.org.as_ref(),
            self.geo.as_ref(),
            self.date.as_ref(),
            self.number.as_ref(),
            self.title.as_ref(),
        ]
        .into_iter()
        .flatten()
        .collect()
    }
}

/// The closed identity classes from the proposed identifying-cycle contract.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum IdentityClass {
    Federal,
    PresidentialAgency,
    RegionalMunicipal,
}

/// Required natural-key fields for an [`IdentityClass`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RequiredIdentityKey {
    Federal,
    PresidentialAgency,
    RegionalMunicipal,
}
impl RequiredIdentityKey {
    pub const fn fields(self) -> &'static [FieldKind] {
        match self {
            Self::Federal => &[FieldKind::Type, FieldKind::Number],
            Self::PresidentialAgency => &[
                FieldKind::Type,
                FieldKind::Org,
                FieldKind::Date,
                FieldKind::Number,
            ],
            Self::RegionalMunicipal => &[
                FieldKind::Type,
                FieldKind::Org,
                FieldKind::Geo,
                FieldKind::Date,
                FieldKind::Number,
            ],
        }
    }
}
impl From<IdentityClass> for RequiredIdentityKey {
    fn from(value: IdentityClass) -> Self {
        match value {
            IdentityClass::Federal => Self::Federal,
            IdentityClass::PresidentialAgency => Self::PresidentialAgency,
            IdentityClass::RegionalMunicipal => Self::RegionalMunicipal,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OfficialIdentityClaimCandidate {
    claim_id: String,
    class: IdentityClass,
    key: RequiredIdentityKey,
    type_claim: IdentityFieldClaim,
    org: Option<IdentityFieldClaim>,
    geo: Option<IdentityFieldClaim>,
    date: Option<IdentityFieldClaim>,
    number: IdentityFieldClaim,
    lifecycle: ProposedLifecycle,
    geo_role: GeoRole,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProposedLifecycle {
    Proposed,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GeoRole {
    Default,
    LoadBearing,
    NotApplicable,
}

impl OfficialIdentityClaimCandidate {
    pub fn claim_id(&self) -> &str {
        &self.claim_id
    }
    pub const fn class(&self) -> IdentityClass {
        self.class
    }
    pub const fn required_key(&self) -> RequiredIdentityKey {
        self.key
    }
    pub fn type_claim(&self) -> &IdentityFieldClaim {
        &self.type_claim
    }
    pub fn org(&self) -> Option<&IdentityFieldClaim> {
        self.org.as_ref()
    }
    pub fn geo(&self) -> Option<&IdentityFieldClaim> {
        self.geo.as_ref()
    }
    pub fn date(&self) -> Option<&IdentityFieldClaim> {
        self.date.as_ref()
    }
    pub fn number(&self) -> &IdentityFieldClaim {
        &self.number
    }
    pub const fn lifecycle(&self) -> ProposedLifecycle {
        self.lifecycle
    }
    pub const fn geo_role(&self) -> GeoRole {
        self.geo_role
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IdentityClaimOutcome {
    Proposed(Box<OfficialIdentityClaimCandidate>),
    Incomplete {
        missing: Vec<FieldKind>,
        reason: String,
    },
}

fn identity_class(act: &IdentifyingActCandidate) -> Option<IdentityClass> {
    match act.act_type() {
        ActType::Federal => Some(IdentityClass::Federal),
        ActType::PresidentialAgency => Some(IdentityClass::PresidentialAgency),
        ActType::RegionalMunicipal => Some(IdentityClass::RegionalMunicipal),
        ActType::Other(_) => None,
    }
}

fn claim_is_authorized(claim: Option<&IdentityFieldClaim>) -> bool {
    claim.is_some_and(|c| matches!(c.status(), FieldStatus::Explicit | FieldStatus::Inherited))
}

fn anchor_part(claim: &IdentityFieldClaim) -> String {
    format!(
        "{}:{}-{}",
        claim.block().get(),
        claim.span().start(),
        claim.span().end()
    )
}

/// Projects a complete act candidate into a proposed resolver lookup claim.
///
/// This is deliberately not a conversion to `WorkId`: the result has only
/// source claims and a deterministic anchor-derived label.
pub fn build_official_identity_claim(act: &IdentifyingActCandidate) -> IdentityClaimOutcome {
    let Some(class) = identity_class(act) else {
        return IdentityClaimOutcome::Incomplete {
            missing: vec![FieldKind::Type],
            reason: "act type is not an evidence-backed identity class".into(),
        };
    };
    let required = RequiredIdentityKey::from(class);
    let mut missing = Vec::new();
    for field in required.fields() {
        let present = match field {
            FieldKind::Type => claim_is_authorized(Some(act.type_claim())),
            FieldKind::Org => claim_is_authorized(act.org()),
            FieldKind::Geo => claim_is_authorized(act.geo()),
            FieldKind::Date => claim_is_authorized(act.date()),
            FieldKind::Number => claim_is_authorized(act.number()),
            FieldKind::Name => true,
        };
        if !present {
            missing.push(*field);
        }
    }
    let Some(number) = act.number().cloned() else {
        if !missing.contains(&FieldKind::Number) {
            missing.push(FieldKind::Number);
        }
        return IdentityClaimOutcome::Incomplete {
            missing,
            reason: "number claim has no authorized provenance".into(),
        };
    };
    if !missing.is_empty() {
        return IdentityClaimOutcome::Incomplete {
            missing,
            reason: "required identity key claim is absent or unresolved".into(),
        };
    }
    let mut anchors = act.claims();
    anchors.sort_by_key(|c| (c.field(), c.block(), c.span()));
    let claim_id = anchors
        .iter()
        .map(|c| anchor_part(c))
        .collect::<Vec<_>>()
        .join("|");
    IdentityClaimOutcome::Proposed(Box::new(OfficialIdentityClaimCandidate {
        claim_id,
        class,
        key: required,
        type_claim: act.type_claim().clone(),
        org: act.org().cloned(),
        geo: act.geo().cloned(),
        date: act.date().cloned(),
        number,
        lifecycle: ProposedLifecycle::Proposed,
        geo_role: match class {
            IdentityClass::Federal => GeoRole::Default,
            IdentityClass::RegionalMunicipal => GeoRole::LoadBearing,
            IdentityClass::PresidentialAgency => GeoRole::NotApplicable,
        },
    }))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ActAssemblyOutcome {
    Compatible(Box<IdentifyingActCandidate>),
    Conflicting {
        retained: Vec<IdentityFieldClaim>,
    },
    Incomplete {
        missing: Vec<FieldKind>,
        retained: Vec<IdentityFieldClaim>,
    },
    Rejected {
        reason: AssemblyRejection,
        retained: Vec<IdentityFieldClaim>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AssemblyRejection {
    ClaimLimit { limit: usize },
    InvalidGeoJurisdiction,
    UnresolvedTerminal(Terminal),
}

fn selected(claims: &[IdentityFieldClaim], field: FieldKind) -> Option<IdentityFieldClaim> {
    claims
        .iter()
        .find(|c| c.field == field && c.status != FieldStatus::Unresolved)
        .cloned()
}

fn distinct_values(claims: &[IdentityFieldClaim], field: FieldKind) -> bool {
    let mut values = claims
        .iter()
        .filter(|c| c.field == field)
        .map(|c| c.compatibility_basis.as_str());
    match values.next() {
        None => false,
        Some(first) => values.any(|x| x != first),
    }
}

pub fn assemble_identifying_act(claims: Vec<IdentityFieldClaim>) -> ActAssemblyOutcome {
    assemble_identifying_act_with_limit(claims, MAX_IDENTITY_FIELD_CLAIMS_PER_BLOCK)
}

pub fn assemble_identifying_act_with_limit(
    mut claims: Vec<IdentityFieldClaim>,
    limit: usize,
) -> ActAssemblyOutcome {
    claims.sort_by_key(|c| (c.field, c.block(), c.span()));
    if claims.len() > limit {
        return ActAssemblyOutcome::Rejected {
            reason: AssemblyRejection::ClaimLimit { limit },
            retained: claims.into_iter().take(limit).collect(),
        };
    }
    if claims
        .iter()
        .any(|c| c.status == FieldStatus::Conflicting && distinct_values(&claims, c.field))
    {
        return ActAssemblyOutcome::Conflicting { retained: claims };
    }
    if distinct_values(&claims, FieldKind::Org)
        || distinct_values(&claims, FieldKind::Geo)
        || distinct_values(&claims, FieldKind::Type)
        || distinct_values(&claims, FieldKind::Date)
        || distinct_values(&claims, FieldKind::Number)
    {
        return ActAssemblyOutcome::Conflicting { retained: claims };
    }
    if claims
        .iter()
        .any(|c| c.field == FieldKind::Geo && is_address_marker(c.compatibility_basis()))
    {
        return ActAssemblyOutcome::Rejected {
            reason: AssemblyRejection::InvalidGeoJurisdiction,
            retained: claims,
        };
    }
    let type_claim = selected(&claims, FieldKind::Type);
    let act_type = match type_claim.as_ref().map(|c| c.value()) {
        Some(v) if is_federal(v) => ActType::Federal,
        Some(v) if is_presidential(v) => ActType::PresidentialAgency,
        Some(v) if is_regional(v) => ActType::RegionalMunicipal,
        Some(v) => ActType::Other(v.to_owned()),
        None => {
            return ActAssemblyOutcome::Incomplete {
                missing: vec![FieldKind::Type],
                retained: claims,
            }
        }
    };
    let mut missing = Vec::new();
    for field in [FieldKind::Number] {
        if selected(&claims, field).is_none() {
            missing.push(field);
        }
    }
    if matches!(
        act_type,
        ActType::PresidentialAgency | ActType::RegionalMunicipal
    ) && selected(&claims, FieldKind::Org).is_none()
    {
        missing.push(FieldKind::Org);
    }
    if matches!(act_type, ActType::RegionalMunicipal) && selected(&claims, FieldKind::Geo).is_none()
    {
        missing.push(FieldKind::Geo);
    }
    if !missing.is_empty() {
        return ActAssemblyOutcome::Incomplete {
            missing,
            retained: claims,
        };
    }
    ActAssemblyOutcome::Compatible(Box::new(IdentifyingActCandidate {
        act_type,
        type_claim: type_claim.expect("type claim was checked above"),
        org: selected(&claims, FieldKind::Org),
        geo: selected(&claims, FieldKind::Geo),
        date: selected(&claims, FieldKind::Date),
        number: selected(&claims, FieldKind::Number),
        title: selected(&claims, FieldKind::Name),
    }))
}

pub fn assemble_from_terminal(
    claims: Vec<IdentityFieldClaim>,
    terminal: Terminal,
) -> ActAssemblyOutcome {
    if terminal == Terminal::Resolved {
        assemble_identifying_act(claims)
    } else {
        ActAssemblyOutcome::Rejected {
            reason: AssemblyRejection::UnresolvedTerminal(terminal),
            retained: claims,
        }
    }
}

pub fn split_collapsed_source_city(
    block: BlockId,
    org_span: TextSpan,
    geo_span: TextSpan,
    org: impl Into<String>,
    geo: impl Into<String>,
) -> Result<(IdentityFieldClaim, IdentityFieldClaim), IdentityFieldClaimError> {
    Ok((
        IdentityFieldClaim::new(
            FieldKind::Org,
            block,
            org_span,
            FieldSource::ExplicitMember,
            FieldStatus::Explicit,
            org,
        )?,
        IdentityFieldClaim::new(
            FieldKind::Geo,
            block,
            geo_span,
            FieldSource::ExplicitMember,
            FieldStatus::Explicit,
            geo,
        )?,
    ))
}

pub fn federal_default_geo(value: &str) -> bool {
    matches!(value.trim(), "Российская Федерация" | "РФ" | "Россия")
}
pub fn is_address_marker(value: &str) -> bool {
    ["площадка", "станция", "вокзал", "адрес"]
        .iter()
        .any(|x| value.to_lowercase().contains(x))
}
fn is_federal(v: &str) -> bool {
    v.to_lowercase().contains("федерал") || v == "Ф"
}
fn is_presidential(v: &str) -> bool {
    v.to_lowercase().contains("президент") || v.to_lowercase().contains("агент")
}
fn is_regional(v: &str) -> bool {
    v.to_lowercase().contains("регион")
        || v.to_lowercase().contains("муницип")
        || v.to_lowercase().contains("субъект")
}

/// Resolve-side endpoint budget from the identifying-cycle contract.
pub const MAX_EXPANDED_CANDIDATES: usize = 64;

/// One written endpoint of a reference.  The value is kept as a candidate
/// label and its span remains the source of truth; no integer range is
/// enumerated here.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct ReferenceEndpoint {
    value: String,
    anchor: TextSpan,
}

impl ReferenceEndpoint {
    pub fn new(value: impl Into<String>, anchor: TextSpan) -> Result<Self, BindingError> {
        if anchor.start() == anchor.end() {
            return Err(BindingError::EmptyAnchor);
        }
        let value = value.into();
        if value.is_empty() {
            return Err(BindingError::EmptyEndpoint);
        }
        Ok(Self { value, anchor })
    }

    pub fn value(&self) -> &str {
        &self.value
    }
    pub const fn anchor(&self) -> TextSpan {
        self.anchor
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct EndpointPair {
    lower: ReferenceEndpoint,
    upper: ReferenceEndpoint,
}

impl EndpointPair {
    pub fn new(lower: ReferenceEndpoint, upper: ReferenceEndpoint) -> Self {
        Self { lower, upper }
    }
    pub fn lower(&self) -> &ReferenceEndpoint {
        &self.lower
    }
    pub fn upper(&self) -> &ReferenceEndpoint {
        &self.upper
    }
    pub const fn len(&self) -> usize {
        2
    }
    pub const fn is_empty(&self) -> bool {
        false
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum BindingEndpoints {
    Single(ReferenceEndpoint),
    Pair(EndpointPair),
}

impl BindingEndpoints {
    pub const fn len(&self) -> usize {
        match self {
            Self::Single(_) => 1,
            Self::Pair(_) => 2,
        }
    }
    pub const fn is_empty(&self) -> bool {
        false
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BindingError {
    EmptyAnchor,
    EmptyEndpoint,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ExpansionLimit {
    requested: usize,
    limit: usize,
}

impl ExpansionLimit {
    pub const fn requested(self) -> usize {
        self.requested
    }
    pub const fn limit(self) -> usize {
        self.limit
    }
}

/// Expand a range to its two written endpoints, never to every integer in
/// the interval.  `requested` models the bounded upstream extraction count
/// and makes overflow observable rather than silently truncating it.
pub fn expand_range_to_endpoints(
    lower: ReferenceEndpoint,
    upper: ReferenceEndpoint,
    requested: usize,
) -> Result<EndpointPair, ExpansionLimit> {
    if requested > MAX_EXPANDED_CANDIDATES {
        return Err(ExpansionLimit {
            requested,
            limit: MAX_EXPANDED_CANDIDATES,
        });
    }
    Ok(EndpointPair::new(lower, upper))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BoundTarget {
    Claim(String),
    Unresolved,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BindingStatus {
    Proposed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReferenceBindingCandidate {
    mention_anchor: TextSpan,
    source_ref: String,
    target: BoundTarget,
    endpoints: BindingEndpoints,
    status: BindingStatus,
}

impl ReferenceBindingCandidate {
    pub fn new(
        mention_anchor: TextSpan,
        source_ref: impl Into<String>,
        target: BoundTarget,
        endpoints: BindingEndpoints,
    ) -> Result<Self, BindingError> {
        if mention_anchor.start() == mention_anchor.end() {
            return Err(BindingError::EmptyAnchor);
        }
        Ok(Self {
            mention_anchor,
            source_ref: source_ref.into(),
            target,
            endpoints,
            status: BindingStatus::Proposed,
        })
    }
    pub const fn mention_anchor(&self) -> TextSpan {
        self.mention_anchor
    }
    pub fn source_ref(&self) -> &str {
        &self.source_ref
    }
    pub fn target(&self) -> &BoundTarget {
        &self.target
    }
    pub fn endpoints(&self) -> &BindingEndpoints {
        &self.endpoints
    }
    pub const fn status(&self) -> BindingStatus {
        self.status
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BindingUnresolvedReason {
    MissingTargetClaim,
    IncompatibleIdentityClaim,
    ContextTerminal(Terminal),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BindingOutcome {
    Candidate(ReferenceBindingCandidate),
    Unresolved {
        reason: BindingUnresolvedReason,
    },
    Conflicting {
        retained: Vec<ReferenceBindingCandidate>,
    },
    ExpansionLimit(ExpansionLimit),
}

/// Zero-tolerance counters for one proposed identity/binding run.
///
/// These counters are event-derived: ordinary constructors cannot increment
/// either hostile counter.  The two hostile events below are reserved for
/// audit fixtures and upstream diagnostics, keeping a clean run honest.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct IdentityRunCounters {
    pub false_identity_mint: usize,
    pub false_link: usize,
    pub claims_total: usize,
    pub acts_total: usize,
    pub identity_claims_total: usize,
    pub bindings_total: usize,
    pub endpoint_pairs_total: usize,
    pub unresolved_total: usize,
    pub conflicting_total: usize,
    pub expansion_limit_total: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityBindingEvent {
    FalseIdentityMint,
    FalseLink,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityBindingViolation {
    FalseIdentityMint,
    FalseLink,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct IdentityBindingRun {
    counters: IdentityRunCounters,
}

impl IdentityBindingRun {
    pub const fn new() -> Self {
        Self {
            counters: IdentityRunCounters {
                false_identity_mint: 0,
                false_link: 0,
                claims_total: 0,
                acts_total: 0,
                identity_claims_total: 0,
                bindings_total: 0,
                endpoint_pairs_total: 0,
                unresolved_total: 0,
                conflicting_total: 0,
                expansion_limit_total: 0,
            },
        }
    }

    pub const fn counters(&self) -> IdentityRunCounters {
        self.counters
    }

    /// Record all retained field claims and the act assembly result.
    pub fn record_act_outcome(&mut self, outcome: &ActAssemblyOutcome) {
        self.counters.acts_total += 1;
        self.counters.claims_total += match outcome {
            ActAssemblyOutcome::Compatible(act) => act.claims().len(),
            ActAssemblyOutcome::Conflicting { retained }
            | ActAssemblyOutcome::Incomplete { retained, .. }
            | ActAssemblyOutcome::Rejected { retained, .. } => retained.len(),
        };
    }

    pub fn record_identity_claim_outcome(&mut self, outcome: &IdentityClaimOutcome) {
        self.counters.identity_claims_total += 1;
        if matches!(outcome, IdentityClaimOutcome::Incomplete { .. }) {
            self.counters.unresolved_total += 1;
        }
    }

    pub fn record_binding_outcome(&mut self, outcome: &BindingOutcome) {
        self.counters.bindings_total += 1;
        match outcome {
            BindingOutcome::Candidate(candidate) => {
                if candidate.endpoints().len() == 2 {
                    self.counters.endpoint_pairs_total += 1;
                }
            }
            BindingOutcome::Unresolved { .. } => self.counters.unresolved_total += 1,
            BindingOutcome::Conflicting { .. } => self.counters.conflicting_total += 1,
            BindingOutcome::ExpansionLimit(_) => self.counters.expansion_limit_total += 1,
        }
    }

    /// Inject a hostile audit event; production construction does not call it.
    pub fn record_event(&mut self, event: IdentityBindingEvent) {
        match event {
            IdentityBindingEvent::FalseIdentityMint => self.counters.false_identity_mint += 1,
            IdentityBindingEvent::FalseLink => self.counters.false_link += 1,
        }
    }
}

pub fn verify_identity_zero_tolerance(
    run: &IdentityBindingRun,
) -> Result<(), Vec<IdentityBindingViolation>> {
    let counters = run.counters;
    let mut violations = Vec::new();
    if counters.false_identity_mint != 0 {
        violations.push(IdentityBindingViolation::FalseIdentityMint);
    }
    if counters.false_link != 0 {
        violations.push(IdentityBindingViolation::FalseLink);
    }
    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

/// Render diagnostic counters only.  This is intentionally not a lifecycle,
/// readiness, promotion, or legal-authority report.
pub fn render_identity_run_json(run: &IdentityBindingRun) -> String {
    let c = run.counters;
    format!(
        "{{\"false_identity_mint\":{},\"false_link\":{},\"claims_total\":{},\"acts_total\":{},\"identity_claims_total\":{},\"bindings_total\":{},\"endpoint_pairs_total\":{},\"unresolved_total\":{},\"conflicting_total\":{},\"expansion_limit_total\":{}}}",
        c.false_identity_mint,
        c.false_link,
        c.claims_total,
        c.acts_total,
        c.identity_claims_total,
        c.bindings_total,
        c.endpoint_pairs_total,
        c.unresolved_total,
        c.conflicting_total,
        c.expansion_limit_total
    )
}
