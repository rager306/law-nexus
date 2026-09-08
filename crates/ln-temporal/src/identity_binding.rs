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
