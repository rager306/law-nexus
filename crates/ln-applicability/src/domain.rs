//! Pure applicability domain types (ADR-0023).
//!
//! No I/O, no profile adapters, no product readiness claims.

use std::error::Error;
use std::fmt;

const MAX_ID_LEN: usize = 128;

/// Protocol identity for revision-bound determinism of abstention algebra.
pub const PROTOCOL_VERSION: &str = "applicability-protocol:v0-abstain-only";

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

id_type!(NormRuleId, "norm rule id");
id_type!(PredicateRegistryRevision, "predicate registry revision");
id_type!(CaseFactsRevision, "case facts revision");
id_type!(ProfileInputRevision, "profile input revision");

/// Typed non-success reasons for case applicability (ADR-0023 §2).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AbstentionKind {
    MissingCtv,
    MissingNormativeState,
    UnresolvedTransitional,
    MissingProvenance,
    MissingOrAmbiguousFacts,
    UnknownProfileOrPredicateRevision,
    UnsupportedPredicateKind,
    /// Protocol is adopted as design only; positive decisions are not implemented.
    ProtocolUnimplemented,
}

impl AbstentionKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::MissingCtv => "missing_ctv",
            Self::MissingNormativeState => "missing_normative_state",
            Self::UnresolvedTransitional => "unresolved_transitional",
            Self::MissingProvenance => "missing_provenance",
            Self::MissingOrAmbiguousFacts => "missing_or_ambiguous_facts",
            Self::UnknownProfileOrPredicateRevision => "unknown_profile_or_predicate_revision",
            Self::UnsupportedPredicateKind => "unsupported_predicate_kind",
            Self::ProtocolUnimplemented => "protocol_unimplemented",
        }
    }
}

/// Conceptual outcome set from ADR-0023. Positive arms exist for future TDD
/// but must not be produced by the v0 evaluator.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ApplicabilityDecision {
    Applicable,
    NotApplicable,
    Abstain(AbstentionKind),
}

/// Prerequisite snapshot flags consumed without ownership (ADR-0023 §4).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct PrerequisiteSnapshot {
    pub ctv_present: bool,
    pub normative_state_present: bool,
    pub transitional_resolved: bool,
    pub provenance_present: bool,
}

impl PrerequisiteSnapshot {
    pub fn empty() -> Self {
        Self::default()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApplicabilityRequest {
    pub rule_id: NormRuleId,
    pub predicate_registry_revision: PredicateRegistryRevision,
    pub case_facts_revision: CaseFactsRevision,
    pub profile_input_revision: ProfileInputRevision,
    pub prerequisites: PrerequisiteSnapshot,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PredicateStep {
    pub predicate_id: String,
    pub outcome: String,
}

/// Mandatory explainable trace for every non-error outcome (ADR-0023 §6).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExplainableTrace {
    pub protocol_version: String,
    pub rule_id: NormRuleId,
    pub predicate_registry_revision: PredicateRegistryRevision,
    pub case_facts_revision: CaseFactsRevision,
    pub profile_input_revision: ProfileInputRevision,
    pub prerequisites: PrerequisiteSnapshot,
    pub predicate_steps: Vec<PredicateStep>,
    pub decision: ApplicabilityDecision,
    pub non_claims: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ApplicabilityResult {
    pub decision: ApplicabilityDecision,
    pub trace: ExplainableTrace,
}

/// Pure prerequisite gate: first missing prerequisite wins in stable order.
pub fn first_prerequisite_abstention(
    prerequisites: &PrerequisiteSnapshot,
) -> Option<AbstentionKind> {
    if !prerequisites.ctv_present {
        return Some(AbstentionKind::MissingCtv);
    }
    if !prerequisites.normative_state_present {
        return Some(AbstentionKind::MissingNormativeState);
    }
    if !prerequisites.transitional_resolved {
        return Some(AbstentionKind::UnresolvedTransitional);
    }
    if !prerequisites.provenance_present {
        return Some(AbstentionKind::MissingProvenance);
    }
    None
}

pub fn default_non_claims() -> Vec<String> {
    vec![
        "Non-authoritative applicability protocol evaluation".to_owned(),
        "Abstention is not Applicable and not NotApplicable".to_owned(),
        "Does not prove legal correctness or product readiness".to_owned(),
        "Does not invent NormRule IR, CaseFacts, or profile decisions".to_owned(),
        "Lifecycle [proposed]; positive applicability claims remain deferred".to_owned(),
    ]
}
