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
id_type!(NormRuleRevision, "norm rule revision");
id_type!(PredicateRegistryRevision, "predicate registry revision");
id_type!(CaseFactsRevision, "case facts revision");
id_type!(ProfileInputRevision, "profile input revision");

/// Structural IR validation errors (RC11-F04a design spine). Not product claims.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NormRuleIrError {
    EmptyConditions,
    InvertedTemporalScope,
    InvalidTemporalDate,
    UnsupportedConditionKind,
    UnsupportedExceptionKind,
    UnsupportedDefeaterKind,
    InvalidId(IdError),
}

impl fmt::Display for NormRuleIrError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::EmptyConditions => {
                write!(formatter, "norm rule IR requires at least one condition")
            }
            Self::InvertedTemporalScope => {
                write!(
                    formatter,
                    "temporal scope effective_from must be <= effective_to"
                )
            }
            Self::InvalidTemporalDate => {
                write!(formatter, "temporal date must be YYYY-MM-DD or empty bound")
            }
            Self::UnsupportedConditionKind => write!(formatter, "unsupported condition kind"),
            Self::UnsupportedExceptionKind => write!(formatter, "unsupported exception kind"),
            Self::UnsupportedDefeaterKind => write!(formatter, "unsupported defeater kind"),
            Self::InvalidId(err) => write!(formatter, "{err}"),
        }
    }
}

impl Error for NormRuleIrError {}

impl From<IdError> for NormRuleIrError {
    fn from(value: IdError) -> Self {
        Self::InvalidId(value)
    }
}

const CLOSED_CONDITION_KINDS: &[&str] = &["fact_required", "fact_forbidden", "status_required"];
const CLOSED_EXCEPTION_KINDS: &[&str] = &["exception_clause", "carve_out"];
const CLOSED_DEFEATER_KINDS: &[&str] = &["special_norm_defeats", "higher_rank_defeats"];

fn is_yyyy_mm_dd(value: &str) -> bool {
    if value.len() != 10 {
        return false;
    }
    let bytes = value.as_bytes();
    bytes[4] == b'-'
        && bytes[7] == b'-'
        && bytes[0..4].iter().all(u8::is_ascii_digit)
        && bytes[5..7].iter().all(u8::is_ascii_digit)
        && bytes[8..10].iter().all(u8::is_ascii_digit)
}

/// Closed temporal applicability window for a NormRule IR (design only).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemporalScope {
    effective_from: Option<String>,
    effective_to: Option<String>,
}

impl TemporalScope {
    pub fn unbounded() -> Self {
        Self {
            effective_from: None,
            effective_to: None,
        }
    }

    pub fn try_new(
        effective_from: Option<&str>,
        effective_to: Option<&str>,
    ) -> Result<Self, NormRuleIrError> {
        let from = match effective_from {
            None => None,
            Some(value) if is_yyyy_mm_dd(value) => Some(value.to_owned()),
            Some(_) => return Err(NormRuleIrError::InvalidTemporalDate),
        };
        let to = match effective_to {
            None => None,
            Some(value) if is_yyyy_mm_dd(value) => Some(value.to_owned()),
            Some(_) => return Err(NormRuleIrError::InvalidTemporalDate),
        };
        if let (Some(start), Some(end)) = (&from, &to) {
            if start > end {
                return Err(NormRuleIrError::InvertedTemporalScope);
            }
        }
        Ok(Self {
            effective_from: from,
            effective_to: to,
        })
    }

    pub fn effective_from(&self) -> Option<&str> {
        self.effective_from.as_deref()
    }

    pub fn effective_to(&self) -> Option<&str> {
        self.effective_to.as_deref()
    }
}

/// Atomic condition in NormRule IR (closed kind vocabulary).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormRuleCondition {
    id: String,
    kind: String,
}

impl NormRuleCondition {
    pub fn try_new(id: &str, kind: &str) -> Result<Self, NormRuleIrError> {
        let id = parse_id("condition id", id, MAX_ID_LEN)?;
        if !CLOSED_CONDITION_KINDS.contains(&kind) {
            return Err(NormRuleIrError::UnsupportedConditionKind);
        }
        Ok(Self {
            id,
            kind: kind.to_owned(),
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn kind(&self) -> &str {
        &self.kind
    }
}

/// Exception clause attached to a NormRule IR.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Exception {
    id: String,
    kind: String,
}

impl Exception {
    pub fn try_new(id: &str, kind: &str) -> Result<Self, NormRuleIrError> {
        let id = parse_id("exception id", id, MAX_ID_LEN)?;
        if !CLOSED_EXCEPTION_KINDS.contains(&kind) {
            return Err(NormRuleIrError::UnsupportedExceptionKind);
        }
        Ok(Self {
            id,
            kind: kind.to_owned(),
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn kind(&self) -> &str {
        &self.kind
    }
}

/// Defeater attached to a NormRule IR (special-norm / rank defeat, design only).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Defeater {
    id: String,
    kind: String,
}

impl Defeater {
    pub fn try_new(id: &str, kind: &str) -> Result<Self, NormRuleIrError> {
        let id = parse_id("defeater id", id, MAX_ID_LEN)?;
        if !CLOSED_DEFEATER_KINDS.contains(&kind) {
            return Err(NormRuleIrError::UnsupportedDefeaterKind);
        }
        Ok(Self {
            id,
            kind: kind.to_owned(),
        })
    }

    pub fn id(&self) -> &str {
        &self.id
    }

    pub fn kind(&self) -> &str {
        &self.kind
    }
}

/// Fail-closed NormRule intermediate representation (ADR-0023 / RC11-F04a).
///
/// Structural design only. Does not evaluate applicability and does not claim
/// legal correctness. Positive Applicable/NotApplicable remains deferred.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NormRule {
    id: NormRuleId,
    revision: NormRuleRevision,
    conditions: Vec<NormRuleCondition>,
    exceptions: Vec<Exception>,
    defeaters: Vec<Defeater>,
    temporal_scope: TemporalScope,
}

impl NormRule {
    pub fn try_new(
        id: NormRuleId,
        revision: NormRuleRevision,
        conditions: Vec<NormRuleCondition>,
        exceptions: Vec<Exception>,
        defeaters: Vec<Defeater>,
        temporal_scope: TemporalScope,
    ) -> Result<Self, NormRuleIrError> {
        if conditions.is_empty() {
            return Err(NormRuleIrError::EmptyConditions);
        }
        Ok(Self {
            id,
            revision,
            conditions,
            exceptions,
            defeaters,
            temporal_scope,
        })
    }

    pub fn id(&self) -> &NormRuleId {
        &self.id
    }

    pub fn revision(&self) -> &NormRuleRevision {
        &self.revision
    }

    pub fn conditions(&self) -> &[NormRuleCondition] {
        &self.conditions
    }

    pub fn exceptions(&self) -> &[Exception] {
        &self.exceptions
    }

    pub fn defeaters(&self) -> &[Defeater] {
        &self.defeaters
    }

    pub fn temporal_scope(&self) -> &TemporalScope {
        &self.temporal_scope
    }
}

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
        "CaseFactSet is synthetic structural input, not legal fact authority".to_owned(),
        "NormRule IR and predicate algebra are not product applicability decisions".to_owned(),
        "Lifecycle [proposed]; positive applicability claims remain deferred".to_owned(),
    ]
}

/// Intermediate pure algebra outcome (not the product ApplicabilityDecision).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PredicateOutcome {
    Satisfied,
    Unsatisfied,
    Abstain(AbstentionKind),
}

impl PredicateOutcome {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Satisfied => "satisfied",
            Self::Unsatisfied => "unsatisfied",
            Self::Abstain(_) => "abstain",
        }
    }
}

/// Fail-closed structural fact bag for algebra evaluation (not legal authority).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct CaseFactSet {
    facts: Vec<(String, bool)>,
}

impl CaseFactSet {
    pub fn empty() -> Self {
        Self::default()
    }

    pub fn try_from_pairs(pairs: &[(&str, bool)]) -> Result<Self, IdError> {
        let mut facts = Vec::with_capacity(pairs.len());
        for (id, value) in pairs {
            let id = parse_id("case fact id", id, MAX_ID_LEN)?;
            facts.push((id, *value));
        }
        Ok(Self { facts })
    }

    pub fn get(&self, id: &str) -> Option<bool> {
        self.facts
            .iter()
            .find(|(key, _)| key == id)
            .map(|(_, value)| *value)
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ComposedPredicateResult {
    pub outcome: PredicateOutcome,
    pub steps: Vec<PredicateStep>,
}

fn lookup_bool(facts: &CaseFactSet, id: &str) -> Result<bool, AbstentionKind> {
    match facts.get(id) {
        Some(value) => Ok(value),
        None => Err(AbstentionKind::MissingOrAmbiguousFacts),
    }
}

/// Evaluate one closed-kind condition against synthetic facts.
pub fn evaluate_condition(condition: &NormRuleCondition, facts: &CaseFactSet) -> PredicateOutcome {
    match condition.kind() {
        "fact_required" => match lookup_bool(facts, condition.id()) {
            Ok(true) => PredicateOutcome::Satisfied,
            Ok(false) => PredicateOutcome::Unsatisfied,
            Err(kind) => PredicateOutcome::Abstain(kind),
        },
        "fact_forbidden" => match lookup_bool(facts, condition.id()) {
            Ok(false) => PredicateOutcome::Satisfied,
            Ok(true) => PredicateOutcome::Unsatisfied,
            Err(kind) => PredicateOutcome::Abstain(kind),
        },
        "status_required" => match lookup_bool(facts, condition.id()) {
            Ok(true) => PredicateOutcome::Satisfied,
            Ok(false) => PredicateOutcome::Unsatisfied,
            Err(kind) => PredicateOutcome::Abstain(kind),
        },
        _ => PredicateOutcome::Abstain(AbstentionKind::UnsupportedPredicateKind),
    }
}

fn evaluate_exception(exception: &Exception, facts: &CaseFactSet) -> PredicateOutcome {
    // Closed kinds: exception fires only when its id fact is explicitly true.
    // Missing fact means the exception does not apply (not an algebra abstention).
    match facts.get(exception.id()) {
        Some(true) => PredicateOutcome::Satisfied,
        Some(false) | None => PredicateOutcome::Unsatisfied,
    }
}

fn evaluate_defeater(defeater: &Defeater, facts: &CaseFactSet) -> PredicateOutcome {
    // Defeater fires only on explicit true; missing means inactive.
    match facts.get(defeater.id()) {
        Some(true) => PredicateOutcome::Satisfied,
        Some(false) | None => PredicateOutcome::Unsatisfied,
    }
}

/// Compose NormRule IR predicates deterministically.
///
/// Order: conditions (all must be satisfied unless exception carves out),
/// then defeaters (any firing defeater forces Unsatisfied).
/// First Abstain wins. This is algebra only — not product Applicable.
pub fn compose_norm_rule_predicates(
    rule: &NormRule,
    facts: &CaseFactSet,
) -> ComposedPredicateResult {
    let mut steps = Vec::new();
    let mut condition_outcome = PredicateOutcome::Satisfied;

    for condition in rule.conditions() {
        let outcome = evaluate_condition(condition, facts);
        steps.push(PredicateStep {
            predicate_id: condition.id().to_owned(),
            outcome: format!("algebra:{}", outcome.as_str()),
        });
        match outcome {
            PredicateOutcome::Abstain(kind) => {
                return ComposedPredicateResult {
                    outcome: PredicateOutcome::Abstain(kind),
                    steps,
                };
            }
            PredicateOutcome::Unsatisfied => condition_outcome = PredicateOutcome::Unsatisfied,
            PredicateOutcome::Satisfied => {}
        }
    }

    if matches!(condition_outcome, PredicateOutcome::Unsatisfied) {
        let mut carved = false;
        for exception in rule.exceptions() {
            let outcome = evaluate_exception(exception, facts);
            steps.push(PredicateStep {
                predicate_id: exception.id().to_owned(),
                outcome: format!("algebra:exception:{}", outcome.as_str()),
            });
            match outcome {
                PredicateOutcome::Abstain(kind) => {
                    return ComposedPredicateResult {
                        outcome: PredicateOutcome::Abstain(kind),
                        steps,
                    };
                }
                PredicateOutcome::Satisfied => carved = true,
                PredicateOutcome::Unsatisfied => {}
            }
        }
        if carved {
            condition_outcome = PredicateOutcome::Satisfied;
        }
    } else {
        // Still record inactive exceptions for determinism/trace completeness.
        for exception in rule.exceptions() {
            let outcome = evaluate_exception(exception, facts);
            steps.push(PredicateStep {
                predicate_id: exception.id().to_owned(),
                outcome: format!("algebra:exception:{}", outcome.as_str()),
            });
            if let PredicateOutcome::Abstain(kind) = outcome {
                return ComposedPredicateResult {
                    outcome: PredicateOutcome::Abstain(kind),
                    steps,
                };
            }
        }
    }

    for defeater in rule.defeaters() {
        let outcome = evaluate_defeater(defeater, facts);
        steps.push(PredicateStep {
            predicate_id: defeater.id().to_owned(),
            outcome: format!("algebra:defeater:{}", outcome.as_str()),
        });
        match outcome {
            PredicateOutcome::Abstain(kind) => {
                return ComposedPredicateResult {
                    outcome: PredicateOutcome::Abstain(kind),
                    steps,
                };
            }
            PredicateOutcome::Satisfied => {
                return ComposedPredicateResult {
                    outcome: PredicateOutcome::Unsatisfied,
                    steps,
                };
            }
            PredicateOutcome::Unsatisfied => {}
        }
    }

    ComposedPredicateResult {
        outcome: condition_outcome,
        steps,
    }
}
