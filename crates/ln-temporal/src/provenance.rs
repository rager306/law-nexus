//! D405 edition provenance envelope constructor (R070 evidential packet).
//!
//! Standalone fail-closed value object: an edition may carry provenance only
//! when its evidential packet is complete — amending act(s), affected
//! provisions, commencement evidence, an explicit transitional slot, and
//! delta evidence record ids. A missing leg, a duplicate identity, or an
//! editor-shaped commencement hint is a typed refusal, never a partial
//! envelope (INV-08 / INV-10).
//!
//! The gated `edition_delta` seam lives here (D409): [`ProvenanceAdmission`]
//! is the caller-supplied commencement + transitional packet for one kept
//! target, and [`EditionDeltaError`] is the whole-edition typed refusal
//! surfaced by `domain::edition_delta`. Per D410 the admission stores the
//! raw commencement fields, so the commencement refusal surfaces at the
//! seam, not at admission construction. The module still does not resolve
//! transitional rules, does not mint runtime selectors, and does not close
//! R070 — see [`PROVENANCE_NON_CLAIMS`].

use std::error::Error;
use std::fmt;

use crate::domain::{
    AmendingActId, CanonRecordId, ComponentConceptId, EvidenceClass, IdError, ThreeCanonLogError,
};

/// Honesty surface carried by every [`EditionProvenanceEnvelope`].
///
/// Cites what constructing an envelope is **not**: it is evidence bookkeeping
/// about one edition, not a runtime authority and not provenance coverage.
pub const PROVENANCE_NON_CLAIMS: &[&str] = &[
    "R070 stays open: the envelope is an evidential packet, not provenance coverage; constructor-as-evidence (D289/D308) does not close R070",
    "Not ActivationTrigger: the D252 effect_selector_modes vocabulary stays YAML-only (D216); the commencement slot is opaque evidence, not a runtime selector",
    "Not TransitionalResolver: ADR-0021 stays [proposed]; no chronology-only default (TSG-009); ExplicitlyAbsent is an affirmative claim, not unknown-as-success",
    "D326 (from, to] window and the edition_delta keep-rule are untouched: the envelope stores no canon events and computes no delta",
    "Not a bitemporal checkout and not the model-crystal compiler: INV-08 / INV-10 are cited as constraints, not re-implemented here",
    "Not a split-commencement algebra: one packet carries one CommencementEvidence; split commencement means multiple envelopes, not a list",
];

/// Dedicated construction error for the provenance envelope.
///
/// Deliberately distinct from `ThreeCanonLogError` and
/// `NormativeStateError::MissingProvenance`: downstream wiring must be able
/// to map missing-provenance refusals without collapsing them into window or
/// force-status errors.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProvenanceConstructionError {
    /// Packet carries no amending act (R070 leg 1).
    MissingAmendingAct,
    /// Packet carries no affected provision (R070 leg 2).
    MissingAffectedProvision,
    /// Commencement leg has no rule reference at all.
    MissingCommencement,
    /// Packet carries no delta evidence record ids (R070 leg 4).
    MissingDeltaEvidence,
    /// Transitional slot is neither declared nor explicitly absent.
    MissingTransitional,
    /// Editor-shaped hint offered as proven commencement (Consultant ≠ Garant).
    UnprovenCommencement,
    /// The same amending act appears twice — ambiguous packet, fail closed.
    DuplicateAmendingAct,
    /// The same affected provision appears twice — ambiguous packet, fail closed.
    DuplicateProvision,
    /// An id in the packet violates the runtime id grammar.
    InvalidId(IdError),
}

impl fmt::Display for ProvenanceConstructionError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::MissingAmendingAct => {
                write!(formatter, "packet has no amending act")
            }
            Self::MissingAffectedProvision => {
                write!(formatter, "packet has no affected provision")
            }
            Self::MissingCommencement => {
                write!(formatter, "packet has no commencement rule reference")
            }
            Self::MissingDeltaEvidence => {
                write!(formatter, "packet has no delta evidence")
            }
            Self::MissingTransitional => {
                write!(
                    formatter,
                    "transitional slot is neither declared nor explicitly absent"
                )
            }
            Self::UnprovenCommencement => {
                write!(formatter, "editorial hint is not proven commencement")
            }
            Self::DuplicateAmendingAct => {
                write!(formatter, "packet repeats an amending act")
            }
            Self::DuplicateProvision => {
                write!(formatter, "packet repeats an affected provision")
            }
            Self::InvalidId(error) => {
                write!(formatter, "packet has an invalid id: {error}")
            }
        }
    }
}

impl Error for ProvenanceConstructionError {}

/// Whole-edition typed refusal of the gated `edition_delta` seam (D409).
///
/// Deliberately a new error, not a widened `ThreeCanonLogError`: the D326
/// window stays its own failure class, a kept target without an admission is
/// a caller packet gap, and an admission or window that cannot complete the
/// packet carries the S01 construction cause. Any variant means the caller
/// receives **no** edition — never a partial delta.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EditionDeltaError {
    /// The `(from, to]` window failed (inverted range, unordered log, …).
    Window(ThreeCanonLogError),
    /// A kept target's packet cannot be completed; the whole call is refused.
    Unresolved {
        target: ComponentConceptId,
        cause: ProvenanceConstructionError,
    },
    /// A kept target has no caller-supplied admission.
    MissingAdmission { target: ComponentConceptId },
}

impl fmt::Display for EditionDeltaError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Window(error) => {
                write!(formatter, "edition delta window failed: {error}")
            }
            Self::Unresolved { target, cause } => write!(
                formatter,
                "edition delta unresolved for {}: {cause}",
                target.as_str()
            ),
            Self::MissingAdmission { target } => write!(
                formatter,
                "kept edition target {} has no provenance admission",
                target.as_str()
            ),
        }
    }
}

impl Error for EditionDeltaError {
    fn source(&self) -> Option<&(dyn Error + 'static)> {
        match self {
            Self::Window(error) => Some(error),
            Self::Unresolved { cause, .. } => Some(cause),
            Self::MissingAdmission { .. } => None,
        }
    }
}

impl From<ThreeCanonLogError> for EditionDeltaError {
    fn from(value: ThreeCanonLogError) -> Self {
        Self::Window(value)
    }
}

/// Opaque commencement evidence leg: one governing rule reference plus the
/// effect day it pins.
///
/// Deliberately not an `ActivationTrigger` and not a `NormativeState` input:
/// the packet records *that* commencement is evidenced, it does not select
/// effects.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommencementEvidence {
    effect_day: i64,
    evidence_class: EvidenceClass,
    rule_ref: CanonRecordId,
}

impl CommencementEvidence {
    /// Records commencement evidence pinned to `effect_day`.
    ///
    /// Fail-closed: an `EditorialHint` class is refused as
    /// [`ProvenanceConstructionError::UnprovenCommencement`] (a hint never
    /// upgrades to legislative), a missing reference is refused as
    /// [`ProvenanceConstructionError::MissingCommencement`], and a malformed
    /// reference as [`ProvenanceConstructionError::InvalidId`].
    /// `HypothesizedFromOracleDiff` is stored as-is — stored, not upgraded.
    pub fn try_new(
        effect_day: i64,
        evidence_class: EvidenceClass,
        rule_ref: &str,
    ) -> Result<Self, ProvenanceConstructionError> {
        if evidence_class == EvidenceClass::EditorialHint {
            return Err(ProvenanceConstructionError::UnprovenCommencement);
        }
        let trimmed = rule_ref.trim();
        if trimmed.is_empty() {
            return Err(ProvenanceConstructionError::MissingCommencement);
        }
        let rule_ref =
            CanonRecordId::parse(trimmed).map_err(ProvenanceConstructionError::InvalidId)?;
        Ok(Self {
            effect_day,
            evidence_class,
            rule_ref,
        })
    }

    pub fn effect_day(&self) -> i64 {
        self.effect_day
    }

    pub fn evidence_class(&self) -> EvidenceClass {
        self.evidence_class
    }

    pub fn rule_ref(&self) -> &CanonRecordId {
        &self.rule_ref
    }
}

/// Explicit transitional slot of the packet.
///
/// `Declared` names the governing transitional rule; `ExplicitlyAbsent` is an
/// affirmative "no transitional rule governs this edition" claim — never a
/// chronology-only default and never a resolver (ADR-0021 stays `[proposed]`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TransitionalEvidence {
    /// The packet names the governing transitional rule reference.
    Declared(CanonRecordId),
    /// The packet affirmatively records that no transitional rule applies.
    ExplicitlyAbsent,
}

impl TransitionalEvidence {
    /// Declares a transitional rule reference; a missing reference is refused
    /// as [`ProvenanceConstructionError::MissingTransitional`].
    pub fn try_declared(rule_ref: &str) -> Result<Self, ProvenanceConstructionError> {
        let trimmed = rule_ref.trim();
        if trimmed.is_empty() {
            return Err(ProvenanceConstructionError::MissingTransitional);
        }
        let rule_ref =
            CanonRecordId::parse(trimmed).map_err(ProvenanceConstructionError::InvalidId)?;
        Ok(Self::Declared(rule_ref))
    }
}

/// Caller-supplied provenance admission for one kept `edition_delta` target
/// (D409).
///
/// The caller owns the commencement and transitional slots; the seam never
/// infers them (D289/D308/ADR-0021). Per D410 slot discipline the admission
/// stores the **raw** commencement fields — effect day, evidence class, and
/// the rule reference string — so an `EditorialHint` admission is storable
/// data and the `CommencementEvidence` refusal surfaces at the
/// `edition_delta` seam as [`EditionDeltaError::Unresolved`], never here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProvenanceAdmission {
    target: ComponentConceptId,
    effect_day: i64,
    evidence_class: EvidenceClass,
    rule_ref: String,
    transitional: TransitionalEvidence,
}

impl ProvenanceAdmission {
    /// Admits one target with its raw commencement fields.
    ///
    /// Fail-closed empty before parse: a whitespace-only rule reference is
    /// refused as [`ProvenanceConstructionError::MissingCommencement`] at
    /// admission time; every other commencement refusal (editorial hints,
    /// malformed references) is deferred to the seam, so the caller learns
    /// which kept target is unresolved.
    pub fn try_new(
        target: ComponentConceptId,
        effect_day: i64,
        evidence_class: EvidenceClass,
        rule_ref: &str,
        transitional: TransitionalEvidence,
    ) -> Result<Self, ProvenanceConstructionError> {
        if rule_ref.trim().is_empty() {
            return Err(ProvenanceConstructionError::MissingCommencement);
        }
        Ok(Self {
            target,
            effect_day,
            evidence_class,
            rule_ref: rule_ref.to_owned(),
            transitional,
        })
    }

    pub fn target(&self) -> &ComponentConceptId {
        &self.target
    }

    pub fn effect_day(&self) -> i64 {
        self.effect_day
    }

    pub fn evidence_class(&self) -> EvidenceClass {
        self.evidence_class
    }

    pub fn rule_ref(&self) -> &str {
        &self.rule_ref
    }

    pub fn transitional(&self) -> &TransitionalEvidence {
        &self.transitional
    }
}

/// Complete, sorted, fail-closed provenance packet of one edition (D405).
///
/// Constructed only through [`EditionProvenanceEnvelope::try_new`]; every
/// field is read through getters so the sorted, validated invariants cannot
/// be bypassed. The envelope carries [`PROVENANCE_NON_CLAIMS`] and owns no
/// runtime authority.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionProvenanceEnvelope {
    amending_acts: Vec<AmendingActId>,
    affected_provisions: Vec<ComponentConceptId>,
    commencement: CommencementEvidence,
    transitional: TransitionalEvidence,
    delta_evidence: Vec<CanonRecordId>,
}

impl EditionProvenanceEnvelope {
    /// Validates and canonicalises the full evidential packet.
    ///
    /// Fail-closed, in this deterministic order: every list slot must be
    /// non-empty (`Missing*`), duplicates are refused after sorting (no
    /// silent dedup), and the stored lists are deterministically sorted by id
    /// string so two equal packets compare equal.
    pub fn try_new(
        amending_acts: Vec<AmendingActId>,
        affected_provisions: Vec<ComponentConceptId>,
        commencement: CommencementEvidence,
        transitional: TransitionalEvidence,
        delta_evidence: Vec<CanonRecordId>,
    ) -> Result<Self, ProvenanceConstructionError> {
        if amending_acts.is_empty() {
            return Err(ProvenanceConstructionError::MissingAmendingAct);
        }
        if affected_provisions.is_empty() {
            return Err(ProvenanceConstructionError::MissingAffectedProvision);
        }
        if delta_evidence.is_empty() {
            return Err(ProvenanceConstructionError::MissingDeltaEvidence);
        }
        let mut amending_acts = amending_acts;
        amending_acts.sort_by(|a, b| a.as_str().cmp(b.as_str()));
        if amending_acts
            .windows(2)
            .any(|pair| pair[0].as_str() == pair[1].as_str())
        {
            return Err(ProvenanceConstructionError::DuplicateAmendingAct);
        }
        let mut affected_provisions = affected_provisions;
        affected_provisions.sort_by(|a, b| a.as_str().cmp(b.as_str()));
        if affected_provisions
            .windows(2)
            .any(|pair| pair[0].as_str() == pair[1].as_str())
        {
            return Err(ProvenanceConstructionError::DuplicateProvision);
        }
        let mut delta_evidence = delta_evidence;
        delta_evidence.sort_by(|a, b| a.as_str().cmp(b.as_str()));
        Ok(Self {
            amending_acts,
            affected_provisions,
            commencement,
            transitional,
            delta_evidence,
        })
    }

    /// String-shaped entry into [`EditionProvenanceEnvelope::try_new`].
    ///
    /// Mirrors `ThreeCanonLog::append_c1_candidate`: whitespace-only ids are
    /// refused as the slot's `Missing*` error before charset parsing.
    pub fn try_new_raw(
        amending_acts: &[&str],
        affected_provisions: &[&str],
        commencement: CommencementEvidence,
        transitional: TransitionalEvidence,
        delta_evidence: &[&str],
    ) -> Result<Self, ProvenanceConstructionError> {
        let amending_acts = parse_packet_ids(
            amending_acts,
            ProvenanceConstructionError::MissingAmendingAct,
            AmendingActId::parse,
        )?;
        let affected_provisions = parse_packet_ids(
            affected_provisions,
            ProvenanceConstructionError::MissingAffectedProvision,
            ComponentConceptId::parse,
        )?;
        let delta_evidence = parse_packet_ids(
            delta_evidence,
            ProvenanceConstructionError::MissingDeltaEvidence,
            CanonRecordId::parse,
        )?;
        Self::try_new(
            amending_acts,
            affected_provisions,
            commencement,
            transitional,
            delta_evidence,
        )
    }

    pub fn amending_acts(&self) -> &[AmendingActId] {
        &self.amending_acts
    }

    pub fn affected_provisions(&self) -> &[ComponentConceptId] {
        &self.affected_provisions
    }

    pub fn commencement(&self) -> &CommencementEvidence {
        &self.commencement
    }

    pub fn transitional(&self) -> &TransitionalEvidence {
        &self.transitional
    }

    pub fn delta_evidence(&self) -> &[CanonRecordId] {
        &self.delta_evidence
    }

    pub fn non_claims(&self) -> &'static [&'static str] {
        PROVENANCE_NON_CLAIMS
    }
}

fn parse_packet_ids<T>(
    values: &[&str],
    missing: ProvenanceConstructionError,
    parse: fn(&str) -> Result<T, IdError>,
) -> Result<Vec<T>, ProvenanceConstructionError> {
    if values.is_empty() {
        return Err(missing);
    }
    let mut parsed = Vec::with_capacity(values.len());
    for value in values {
        let trimmed = value.trim();
        if trimmed.is_empty() {
            return Err(missing);
        }
        parsed.push(parse(trimmed).map_err(ProvenanceConstructionError::InvalidId)?);
    }
    Ok(parsed)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn legislative_commencement() -> CommencementEvidence {
        CommencementEvidence::try_new(20_000, EvidenceClass::Legislative, "rec:commencement:1")
            .expect("legislative commencement")
    }

    #[test]
    fn raw_helper_refuses_whitespace_only_ids_before_charset_parse() {
        let error = EditionProvenanceEnvelope::try_new_raw(
            &["   "],
            &["cc:work/statya-1"],
            legislative_commencement(),
            TransitionalEvidence::ExplicitlyAbsent,
            &["rec:edition-delta:1"],
        )
        .expect_err("whitespace-only act id is a missing act, not a charset error");
        assert_eq!(error, ProvenanceConstructionError::MissingAmendingAct);
    }

    #[test]
    fn raw_helper_maps_bad_charset_to_invalid_id() {
        let error = EditionProvenanceEnvelope::try_new_raw(
            &["act:bad id"],
            &["cc:work/statya-1"],
            legislative_commencement(),
            TransitionalEvidence::try_declared("rec:transition:1").expect("declared"),
            &["rec:edition-delta:1"],
        )
        .expect_err("space is outside the runtime id grammar");
        assert!(matches!(error, ProvenanceConstructionError::InvalidId(_)));
    }

    #[test]
    fn raw_helper_parses_and_sorts_the_packet() {
        let envelope = EditionProvenanceEnvelope::try_new_raw(
            &["act:2020-99-fz", "act:2019-11-fz"],
            &["cc:koap/statya-20", "cc:koap/statya-19"],
            legislative_commencement(),
            TransitionalEvidence::ExplicitlyAbsent,
            &["rec:edition-delta:2", "rec:edition-delta:1"],
        )
        .expect("raw packet");
        assert_eq!(
            envelope
                .amending_acts()
                .iter()
                .map(AmendingActId::as_str)
                .collect::<Vec<_>>(),
            ["act:2019-11-fz", "act:2020-99-fz"]
        );
        assert_eq!(
            envelope
                .affected_provisions()
                .iter()
                .map(ComponentConceptId::as_str)
                .collect::<Vec<_>>(),
            ["cc:koap/statya-19", "cc:koap/statya-20"]
        );
        assert_eq!(
            envelope
                .delta_evidence()
                .iter()
                .map(CanonRecordId::as_str)
                .collect::<Vec<_>>(),
            ["rec:edition-delta:1", "rec:edition-delta:2"]
        );
        assert_eq!(
            envelope.transitional(),
            &TransitionalEvidence::ExplicitlyAbsent
        );
    }
}
