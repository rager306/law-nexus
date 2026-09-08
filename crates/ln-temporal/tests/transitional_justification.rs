//! T03 contract for source-bound ExplicitlyAbsent transitional evidence.

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    edition_delta, AmendmentFacetKind, C1Candidate, CanonRecordId, ComponentConceptId,
    EvidenceClass, NormativeState, ThreeCanonEventLog,
};
use ln_temporal::provenance::{
    EditionProvenanceEnvelope, ProvenanceAdmission, ProvenanceConstructionError,
    TransitionalEvidence,
};

const JUSTIFICATION: &str = "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).";

fn cc(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("valid target")
}

fn record(value: &str) -> CanonRecordId {
    CanonRecordId::parse(value).expect("valid record")
}

fn day(value: &str) -> i64 {
    legal_act_effect_day_to_ordinal(value).expect("valid date")
}

fn absent() -> TransitionalEvidence {
    TransitionalEvidence::try_explicitly_absent(JUSTIFICATION).expect("source-bound justification")
}

fn commencement() -> ln_temporal::provenance::CommencementEvidence {
    ln_temporal::provenance::CommencementEvidence::try_new(
        day("2024-12-26"),
        EvidenceClass::HypothesizedFromOracleDiff,
        "rec:commencement:484-93:hypothesized",
    )
    .expect("valid commencement")
}

#[test]
fn empty_or_whitespace_absence_justification_is_rejected() {
    for value in ["", "   ", "\n\t"] {
        assert_eq!(
            TransitionalEvidence::try_explicitly_absent(value),
            Err(ProvenanceConstructionError::MissingTransitionalJustification)
        );
    }
}

#[test]
fn absence_justification_round_trips_without_normalization() {
    let value = "  source note: no transitional rule evidenced  \n";
    let evidence = TransitionalEvidence::try_explicitly_absent(value).expect("non-empty note");
    assert_eq!(evidence.justification(), Some(value));
    assert_eq!(absent().justification(), Some(JUSTIFICATION));
}

#[test]
fn declared_path_remains_unchanged() {
    let declared = TransitionalEvidence::try_declared("rec:transition:1").expect("declared");
    assert_eq!(declared.justification(), None);
    assert!(matches!(declared, TransitionalEvidence::Declared(_)));
}

#[test]
fn admission_carries_justification_through_to_envelope() {
    let target = cc("cc:44-fz:statya-93");
    let admission = ProvenanceAdmission::try_new(
        target.clone(),
        day("2024-12-26"),
        EvidenceClass::HypothesizedFromOracleDiff,
        "rec:commencement:484-93:hypothesized",
        absent(),
    )
    .expect("valid admission");
    assert_eq!(
        admission.transitional().justification(),
        Some(JUSTIFICATION)
    );

    let mut log = ThreeCanonEventLog::empty();
    log.append_c1_candidate(
        record("rec:amend:484-93"),
        C1Candidate::LegislativeAmendment {
            target: target.clone(),
            effect_day: day("2024-12-26"),
            amending_act_raw: "act:484-fz:2024-12-26".to_owned(),
            evidence: EvidenceClass::HypothesizedFromOracleDiff,
            facets: vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
            force_transition: Some(NormativeState::InForce),
        },
    )
    .expect("valid event");

    let delta = edition_delta(&log, day("2024-12-01"), day("2024-12-26"), &[admission])
        .expect("valid edition delta");
    assert_eq!(
        delta.provisions()[0]
            .provenance()
            .transitional()
            .justification(),
        Some(JUSTIFICATION)
    );

    let envelope = EditionProvenanceEnvelope::try_new_raw(
        &["act:484-fz:2024-12-26"],
        &["cc:44-fz:statya-93"],
        commencement(),
        absent(),
        &["rec:amend:484-93"],
    )
    .expect("valid envelope");
    assert_eq!(envelope.transitional().justification(), Some(JUSTIFICATION));
}
