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

id_type!(IdentityId, "identity id");
id_type!(ContributionId, "contribution id");
id_type!(FamilyId, "family id");
id_type!(C12Version, "c12 version");
id_type!(InputChainDigest, "input chain digest");

pub const C12_GATE_VERSION: &str = "c12:v1";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EvidenceSide {
    Left,
    Right,
    Bilateral,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceContribution {
    pub contribution_id: ContributionId,
    pub family_id: FamilyId,
    pub side: EvidenceSide,
    /// Human-readable ceiling label only; not a ranking authority.
    pub evidence_ceiling: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityOutcome {
    Same,
    Different,
    Candidate,
    Ambiguous,
    Conflict,
    NotResolvable,
}

impl IdentityOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Same => "same",
            Self::Different => "different",
            Self::Candidate => "candidate",
            Self::Ambiguous => "ambiguous",
            Self::Conflict => "conflict",
            Self::NotResolvable => "not-resolvable",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityReason {
    OneSidedEvidence,
    SimilarityOnly,
    MissingEvidence,
    BilateralSameEvidence,
    BilateralDifferentEvidence,
    ConflictingEvidence,
}

impl IdentityReason {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::OneSidedEvidence => "one-sided-evidence",
            Self::SimilarityOnly => "similarity-only",
            Self::MissingEvidence => "missing-evidence",
            Self::BilateralSameEvidence => "bilateral-same-evidence",
            Self::BilateralDifferentEvidence => "bilateral-different-evidence",
            Self::ConflictingEvidence => "conflicting-evidence",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityRecord {
    pub identity_id: IdentityId,
    pub label: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssertRequest {
    pub left_id: IdentityId,
    pub right_id: IdentityId,
    pub contributions: Vec<EvidenceContribution>,
    /// Caller claims `same` (e.g. from adapter/similarity). Policy decides.
    pub claim_same: bool,
    /// Optional similarity score used only as ranking within a ceiling.
    /// Cannot authorize same/merge by itself.
    pub similarity_score: Option<u8>,
    pub method: String,
    pub scope: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityAssertion {
    pub c12_version: C12Version,
    pub outcome: IdentityOutcome,
    pub reason: IdentityReason,
    pub left_id: IdentityId,
    pub right_id: IdentityId,
    pub left_survives: bool,
    pub right_survives: bool,
    pub merge_performed: bool,
    pub no_merge_observation: bool,
    pub contribution_ids: Vec<ContributionId>,
    pub input_chain_digest: InputChainDigest,
    pub method: String,
    pub scope: String,
    pub evidence_ceiling_visible: bool,
}

pub fn digest_pair(
    left_id: &IdentityId,
    right_id: &IdentityId,
    contributions: &[EvidenceContribution],
) -> InputChainDigest {
    let mut material = format!("{}|{}", left_id.as_str(), right_id.as_str());
    for item in contributions {
        material.push('|');
        material.push_str(item.contribution_id.as_str());
        material.push(':');
        material.push_str(item.family_id.as_str());
    }
    let mut hash = 0xcbf29ce484222325_u64;
    for byte in material.as_bytes() {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    InputChainDigest::parse(&format!("fnv1a64:{hash:016x}")).expect("static digest")
}

// ─── ADR-0016 / KBO-R011: FRBR Work/Expression spine (not C12 digest) ───────
// Number alone is never Work identity. ELI is compatibility projection only.

id_type!(WorkId, "work id");
id_type!(ExpressionId, "expression id");

/// Issuing authority token (not a legal competence graph).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct IssuingAuthority(String);

impl IssuingAuthority {
    pub fn parse(value: &str) -> Result<Self, FrbrIdentityError> {
        if value.is_empty() {
            return Err(FrbrIdentityError::MissingAuthority);
        }
        if value.len() > 32 {
            return Err(FrbrIdentityError::InvalidAuthority);
        }
        if !value
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
        {
            return Err(FrbrIdentityError::InvalidAuthority);
        }
        Ok(Self(value.to_owned()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// Act number token (e.g. `44-fz`). Never sufficient as Work identity alone.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct LegalActNumber(String);

impl LegalActNumber {
    pub fn parse(value: &str) -> Result<Self, FrbrIdentityError> {
        if value.is_empty() {
            return Err(FrbrIdentityError::MissingActNumber);
        }
        if value.len() > 24 {
            return Err(FrbrIdentityError::InvalidActNumber);
        }
        if !value
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || matches!(b, b'-' | b'.'))
        {
            return Err(FrbrIdentityError::InvalidActNumber);
        }
        Ok(Self(value.to_owned()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FrbrIdentityError {
    MissingAuthority,
    InvalidAuthority,
    MissingEnactmentDate,
    InvalidEnactmentDate,
    MissingActNumber,
    InvalidActNumber,
    InvalidEffectDay,
    InvalidId(IdError),
}

impl fmt::Display for FrbrIdentityError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingAuthority => write!(formatter, "work identity requires issuing authority"),
            Self::InvalidAuthority => write!(formatter, "issuing authority token is invalid"),
            Self::MissingEnactmentDate => {
                write!(formatter, "work identity requires enactment date")
            }
            Self::InvalidEnactmentDate => {
                write!(formatter, "enactment date must be ISO YYYY-MM-DD")
            }
            Self::MissingActNumber => write!(formatter, "work identity requires act number"),
            Self::InvalidActNumber => write!(formatter, "act number token is invalid"),
            Self::InvalidEffectDay => {
                write!(formatter, "expression effect day must be ISO YYYY-MM-DD")
            }
            Self::InvalidId(err) => write!(formatter, "{err}"),
        }
    }
}

impl Error for FrbrIdentityError {}

impl From<IdError> for FrbrIdentityError {
    fn from(value: IdError) -> Self {
        Self::InvalidId(value)
    }
}

const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

fn calendar_year_bounds() -> Option<(i32, i32)> {
    let min_year = yaml_calendar_scalar("min_year:")?.parse().ok()?;
    let max_year = yaml_calendar_scalar("max_year:")?.parse().ok()?;
    (min_year <= max_year).then_some((min_year, max_year))
}

fn yaml_calendar_scalar(key: &str) -> Option<String> {
    let mut in_calendar = false;
    let mut heading_indent = 0usize;
    for raw in EMBEDDED_ONTOLOGY_YAML.lines() {
        let trimmed = match raw.find('#') {
            Some(index) => raw[..index].trim_end(),
            None => raw.trim_end(),
        };
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == "calendar:" {
            in_calendar = true;
            heading_indent = indent;
            continue;
        }
        if in_calendar && indent <= heading_indent && trimmed.trim().ends_with(':') {
            in_calendar = false;
        }
        if in_calendar {
            if let Some(rest) = trimmed.trim().strip_prefix(key) {
                let value = rest.trim().trim_matches('"');
                if !value.is_empty() {
                    return Some(value.to_owned());
                }
            }
        }
    }
    None
}

fn is_leap_year(year: i32) -> bool {
    year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)
}

fn days_in_month(year: i32, month: u8) -> u8 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if is_leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn is_iso_day(value: &str) -> bool {
    if value.len() != 10
        || value.as_bytes().get(4) != Some(&b'-')
        || value.as_bytes().get(7) != Some(&b'-')
    {
        return false;
    }
    let bytes = value.as_bytes();
    if !bytes.iter().enumerate().all(|(i, b)| match i {
        4 | 7 => *b == b'-',
        _ => b.is_ascii_digit(),
    }) {
        return false;
    }
    let year: i32 = value[0..4].parse().unwrap_or(0);
    let month: u8 = value[5..7].parse().unwrap_or(0);
    let day: u8 = value[8..10].parse().unwrap_or(0);
    let Some((min_year, max_year)) = calendar_year_bounds() else {
        return false;
    };
    (min_year..=max_year).contains(&year) && day >= 1 && day <= days_in_month(year, month)
}

const FRBR_NON_CLAIMS: &[&str] = &[
    "FRBR Work/Expression spine is structural identity only; not C12 digest merge",
    "Work identity does not imply ForceStatus InForce",
    "Work/Expression presence does not imply Applicability",
    "ELI URN is a compatibility projection, not project-local canon",
    "Not corpus identity stability, not Manifestation/Item store, not legal validation",
    "Lifecycle [proposed]; KBO-R011 S2; not O3 fixture edges",
];

/// Abstract normative act (undated Work). Identity = authority + date + number.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrWork {
    pub work_id: WorkId,
    pub authority: IssuingAuthority,
    pub enactment_date: String,
    pub act_number: LegalActNumber,
    pub kind: &'static str,
    pub non_claims: Vec<&'static str>,
}

impl FrbrWork {
    pub fn eli_projection(&self) -> String {
        format!(
            "urn:lex:ru:{}:{}:{};{}",
            self.authority.as_str(),
            self.kind,
            self.enactment_date,
            self.act_number.as_str()
        )
    }
}

/// Dated edition of a Work (Expression). Temporal via legal_act_effect day.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrExpression {
    pub expression_id: ExpressionId,
    pub work_id: WorkId,
    pub legal_act_effect_day: String,
    pub non_claims: Vec<&'static str>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FrbrCompareOutcome {
    Same,
    Different,
    Conflict,
}

impl FrbrCompareOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Same => "same",
            Self::Different => "different",
            Self::Conflict => "conflict",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FrbrCompareResult {
    pub outcome: FrbrCompareOutcome,
    /// Always false: FRBR compare is not C12 digest identity.
    pub used_c12_digest: bool,
    pub non_claims: Vec<&'static str>,
}

/// Mint a Work. Number alone is rejected (missing authority/date).
pub fn mint_work(
    authority: &str,
    enactment_date: &str,
    act_number: &str,
) -> Result<FrbrWork, FrbrIdentityError> {
    let authority = IssuingAuthority::parse(authority)?;
    if enactment_date.is_empty() {
        return Err(FrbrIdentityError::MissingEnactmentDate);
    }
    if !is_iso_day(enactment_date) {
        return Err(FrbrIdentityError::InvalidEnactmentDate);
    }
    let act_number = LegalActNumber::parse(act_number)?;
    let kind = "zakon";
    let work_id = WorkId::parse(&format!(
        "work:ru:{}:{}:{}:{}",
        authority.as_str(),
        kind,
        enactment_date,
        act_number.as_str()
    ))?;
    Ok(FrbrWork {
        work_id,
        authority,
        enactment_date: enactment_date.to_owned(),
        act_number,
        kind,
        non_claims: FRBR_NON_CLAIMS.to_vec(),
    })
}

/// Mint an Expression of a Work at a governing legal-act-effect day.
pub fn mint_expression(
    work: &FrbrWork,
    legal_act_effect_day: &str,
) -> Result<FrbrExpression, FrbrIdentityError> {
    if legal_act_effect_day.is_empty() || !is_iso_day(legal_act_effect_day) {
        return Err(FrbrIdentityError::InvalidEffectDay);
    }
    let expression_id = ExpressionId::parse(&format!(
        "expr:ru:{}:{}:{}:{}:{}",
        work.authority.as_str(),
        work.kind,
        work.enactment_date,
        work.act_number.as_str(),
        legal_act_effect_day
    ))?;
    Ok(FrbrExpression {
        expression_id,
        work_id: work.work_id.clone(),
        legal_act_effect_day: legal_act_effect_day.to_owned(),
        non_claims: FRBR_NON_CLAIMS.to_vec(),
    })
}

/// Compare two Works: same keys → Same; same number + divergent authority/date → Conflict.
pub fn compare_work_identities(left: &FrbrWork, right: &FrbrWork) -> FrbrCompareResult {
    let outcome = if left.work_id.as_str() == right.work_id.as_str() {
        FrbrCompareOutcome::Same
    } else if left.act_number.as_str() == right.act_number.as_str() {
        FrbrCompareOutcome::Conflict
    } else {
        FrbrCompareOutcome::Different
    };
    FrbrCompareResult {
        outcome,
        used_c12_digest: false,
        non_claims: FRBR_NON_CLAIMS.to_vec(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_empty_identity_id() {
        assert!(IdentityId::parse("").is_err());
    }

    #[test]
    fn outcome_vocabulary_is_closed() {
        assert_eq!(IdentityOutcome::Same.as_str(), "same");
        assert_eq!(IdentityOutcome::NotResolvable.as_str(), "not-resolvable");
    }
}
