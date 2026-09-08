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
    org: Option<IdentityFieldClaim>,
    geo: Option<IdentityFieldClaim>,
    date: Option<IdentityFieldClaim>,
    number: Option<IdentityFieldClaim>,
    title: Option<IdentityFieldClaim>,
}
impl IdentifyingActCandidate {
    pub fn act_type(&self) -> &ActType {
        &self.act_type
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
