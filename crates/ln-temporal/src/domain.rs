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
