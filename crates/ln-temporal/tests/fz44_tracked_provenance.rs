//! Bounded tracked 484-FZ → 44-FZ provenance chain (M201 S03).
//!
//! The tracked C1 pin grounds only the amending-act identity and target edge.
//! It is `authoritative: false` and is not a legal commencement source. This
//! suite therefore supplies a named caller admission as
//! `HypothesizedFromOracleDiff` and verifies that the public runtime preserves
//! that class without upgrading it. R070 remains open.

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    edition_delta, AmendmentFacetKind, C1Candidate, CanonRecordId, ComponentConceptId,
    EvidenceClass, NormativeState, ThreeCanonEventLog,
};
use ln_temporal::provenance::{
    EditionDeltaError, ProvenanceAdmission, ProvenanceConstructionError, TransitionalEvidence,
};

const TARGET: &str = "cc:44-fz:statya-93";
const AMENDING_ACT: &str = "act:484-fz:2024-12-26";
const AMENDMENT_RECORD: &str = "rec:amend:484-93";
const COMMENCEMENT_RULE_REF: &str = "rec:commencement:484-93:hypothesized";
const EFFECT_ISO: &str = "2024-12-26";
const FROM_ISO: &str = "2024-12-01";
const TO_ISO: &str = "2024-12-26";
const PIN_SHA256: &str = "67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d";

const TRACKED_CHAIN_YAML: &str =
    include_str!("../../../prd/architecture/fz44-tracked-edition-chain.yaml");
const TRACKED_CHAIN_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m201-s03-tracked-chain.json");

fn cc(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("valid component concept")
}

fn rid(value: &str) -> CanonRecordId {
    CanonRecordId::parse(value).expect("valid canon record id")
}

fn day(value: &str) -> i64 {
    legal_act_effect_day_to_ordinal(value).expect("valid civil day")
}

fn tracked_log() -> ThreeCanonEventLog {
    let mut log = ThreeCanonEventLog::empty();
    log.append_c1_candidate(
        rid(AMENDMENT_RECORD),
        C1Candidate::LegislativeAmendment {
            target: cc(TARGET),
            effect_day: day(EFFECT_ISO),
            amending_act_raw: AMENDING_ACT.to_owned(),
            evidence: EvidenceClass::HypothesizedFromOracleDiff,
            facets: vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
            force_transition: Some(NormativeState::InForce),
        },
    )
    .expect("bounded C1 event");
    log
}

fn admission_with_class(class: EvidenceClass) -> ProvenanceAdmission {
    ProvenanceAdmission::try_new(
        cc(TARGET),
        day(EFFECT_ISO),
        class,
        COMMENCEMENT_RULE_REF,
        TransitionalEvidence::ExplicitlyAbsent,
    )
    .expect("bounded caller-supplied admission")
}

#[test]
fn tracked_484_statya_93_window_carries_bounded_hypothesized_envelope() {
    let delta = edition_delta(
        &tracked_log(),
        day(FROM_ISO),
        day(TO_ISO),
        &[admission_with_class(
            EvidenceClass::HypothesizedFromOracleDiff,
        )],
    )
    .expect("bounded tracked chain");

    assert_eq!(delta.provisions().len(), 1);
    let row = &delta.provisions()[0];
    assert_eq!(row.target().as_str(), TARGET);
    assert_eq!(row.provenance().amending_acts()[0].as_str(), AMENDING_ACT);
    assert_eq!(row.provenance().affected_provisions(), &[cc(TARGET)]);
    assert_eq!(
        row.provenance().commencement().evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
    assert_eq!(
        row.provenance().commencement().rule_ref().as_str(),
        COMMENCEMENT_RULE_REF
    );
    assert_eq!(
        row.provenance().transitional(),
        &TransitionalEvidence::ExplicitlyAbsent
    );
    assert_eq!(row.provenance().delta_evidence(), &[rid(AMENDMENT_RECORD)]);
}

#[test]
fn missing_admission_on_tracked_statya_93_refuses_whole_edition() {
    assert_eq!(
        edition_delta(&tracked_log(), day(FROM_ISO), day(TO_ISO), &[]),
        Err(EditionDeltaError::MissingAdmission { target: cc(TARGET) })
    );
}

#[test]
fn editorial_hint_commencement_on_tracked_chain_is_unresolved_unproven() {
    assert_eq!(
        edition_delta(
            &tracked_log(),
            day(FROM_ISO),
            day(TO_ISO),
            &[admission_with_class(EvidenceClass::EditorialHint)],
        ),
        Err(EditionDeltaError::Unresolved {
            target: cc(TARGET),
            cause: ProvenanceConstructionError::UnprovenCommencement,
        })
    );
}

#[test]
fn tracked_chain_preserves_hypothesized_commencement_without_upgrade() {
    let delta = edition_delta(
        &tracked_log(),
        day(FROM_ISO),
        day(TO_ISO),
        &[admission_with_class(
            EvidenceClass::HypothesizedFromOracleDiff,
        )],
    )
    .expect("hypothesized admission remains usable bounded data");

    assert_eq!(
        delta.provisions()[0]
            .provenance()
            .commencement()
            .evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
}

#[test]
fn tracked_chain_pin_constants_match_yaml_and_count_json() {
    for expected in [
        PIN_SHA256,
        TARGET,
        AMENDING_ACT,
        AMENDMENT_RECORD,
        COMMENCEMENT_RULE_REF,
        "hypothesized_from_oracle_diff",
        "authoritative: false",
        "R070",
    ] {
        assert!(
            TRACKED_CHAIN_YAML.contains(expected) || TRACKED_CHAIN_JSON.contains(expected),
            "portable tracked-chain artifacts must contain {expected}"
        );
    }
    assert!(TRACKED_CHAIN_YAML.contains("legal commencement"));
    assert!(TRACKED_CHAIN_JSON.contains("kept_lines"));
}
