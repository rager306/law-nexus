//! M201 S01 fail-closed provenance-envelope contract (TDD red first).
//!
//! This suite specifies a value object only. It does not wire provenance into
//! `edition_delta`, alter `AmendmentEvent`, resolve transitional rules, or
//! claim that constructing an envelope proves legal authority or closes R070.

use ln_temporal::domain::{AmendingActId, CanonRecordId, ComponentConceptId, EvidenceClass};
use ln_temporal::provenance::{
    CommencementEvidence, EditionProvenanceEnvelope, ProvenanceConstructionError,
    TransitionalEvidence,
};

fn act(value: &str) -> AmendingActId {
    AmendingActId::parse(value).expect("valid synthetic amending-act id")
}

fn provision(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("valid synthetic component-concept id")
}

fn record(value: &str) -> CanonRecordId {
    CanonRecordId::parse(value).expect("valid synthetic canon-record id")
}

fn commencement(class: EvidenceClass) -> Result<CommencementEvidence, ProvenanceConstructionError> {
    CommencementEvidence::try_new(20_000, class, "rec:commencement:1")
}

fn declared_transition() -> TransitionalEvidence {
    TransitionalEvidence::try_declared("rec:transition:1")
        .expect("declared transition has a valid evidence id")
}

fn full_packet() -> Result<EditionProvenanceEnvelope, ProvenanceConstructionError> {
    EditionProvenanceEnvelope::try_new(
        vec![act("act:z"), act("act:a")],
        vec![provision("cc:work/statya-9"), provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative)?,
        declared_transition(),
        vec![record("rec:delta:9"), record("rec:delta:1")],
    )
}

#[test]
fn full_packet_is_sorted_and_queryable() {
    let envelope = full_packet().expect("complete synthetic packet");

    assert_eq!(
        envelope
            .amending_acts()
            .iter()
            .map(AmendingActId::as_str)
            .collect::<Vec<_>>(),
        ["act:a", "act:z"]
    );
    assert_eq!(
        envelope
            .affected_provisions()
            .iter()
            .map(ComponentConceptId::as_str)
            .collect::<Vec<_>>(),
        ["cc:work/statya-1", "cc:work/statya-9"]
    );
    assert_eq!(
        envelope
            .delta_evidence()
            .iter()
            .map(CanonRecordId::as_str)
            .collect::<Vec<_>>(),
        ["rec:delta:1", "rec:delta:9"]
    );
    assert_eq!(envelope.commencement().effect_day(), 20_000);
    assert_eq!(
        envelope.commencement().evidence_class(),
        EvidenceClass::Legislative
    );
    assert_eq!(
        envelope.commencement().rule_ref().as_str(),
        "rec:commencement:1"
    );
    assert_eq!(envelope.transitional(), &declared_transition());
}

#[test]
fn missing_amending_act_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new(
        vec![],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:1")],
    )
    .expect_err("an edition packet needs at least one amending act");

    assert_eq!(error, ProvenanceConstructionError::MissingAmendingAct);
}

#[test]
fn missing_affected_provision_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:1")],
    )
    .expect_err("an edition packet needs at least one affected provision");

    assert_eq!(error, ProvenanceConstructionError::MissingAffectedProvision);
}

#[test]
fn missing_commencement_is_typed_refusal() {
    let error = CommencementEvidence::try_new(20_000, EvidenceClass::Legislative, "")
        .expect_err("an empty rule reference is not commencement evidence");

    assert_eq!(error, ProvenanceConstructionError::MissingCommencement);
}

#[test]
fn missing_transitional_is_typed_refusal() {
    let error = TransitionalEvidence::try_declared("")
        .expect_err("an unresolved transitional slot cannot construct evidence");

    assert_eq!(error, ProvenanceConstructionError::MissingTransitional);
}

#[test]
fn missing_delta_evidence_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![],
    )
    .expect_err("a resulting edition delta needs evidence record ids");

    assert_eq!(error, ProvenanceConstructionError::MissingDeltaEvidence);
}

#[test]
fn editorial_hint_commencement_is_unproven() {
    let error = commencement(EvidenceClass::EditorialHint)
        .expect_err("an editorial hint cannot prove commencement");

    assert_eq!(error, ProvenanceConstructionError::UnprovenCommencement);
}

#[test]
fn duplicate_amending_act_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a"), act("act:a")],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:1")],
    )
    .expect_err("duplicate acts are ambiguous provenance");

    assert_eq!(error, ProvenanceConstructionError::DuplicateAmendingAct);
}

#[test]
fn duplicate_provision_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![provision("cc:work/statya-1"), provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:1")],
    )
    .expect_err("duplicate provisions are ambiguous provenance");

    assert_eq!(error, ProvenanceConstructionError::DuplicateProvision);
}

#[test]
fn empty_vecs_are_missing_slots() {
    let acts_error = EditionProvenanceEnvelope::try_new(
        vec![],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::HypothesizedFromOracleDiff).unwrap(),
        TransitionalEvidence::ExplicitlyAbsent,
        vec![record("rec:delta:1")],
    )
    .expect_err("empty acts must fail closed");
    let provisions_error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![],
        commencement(EvidenceClass::HypothesizedFromOracleDiff).unwrap(),
        TransitionalEvidence::ExplicitlyAbsent,
        vec![record("rec:delta:1")],
    )
    .expect_err("empty provisions must fail closed");
    let delta_error = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::HypothesizedFromOracleDiff).unwrap(),
        TransitionalEvidence::ExplicitlyAbsent,
        vec![],
    )
    .expect_err("empty delta evidence must fail closed");

    assert_eq!(acts_error, ProvenanceConstructionError::MissingAmendingAct);
    assert_eq!(
        provisions_error,
        ProvenanceConstructionError::MissingAffectedProvision
    );
    assert_eq!(
        delta_error,
        ProvenanceConstructionError::MissingDeltaEvidence
    );
}
