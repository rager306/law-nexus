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
fn missing_transitional_via_try_declared_empty_is_typed_refusal() {
    let empty = TransitionalEvidence::try_declared("");
    let whitespace = TransitionalEvidence::try_declared("   ");

    for attempt in [empty, whitespace] {
        assert_eq!(
            attempt.expect_err("unresolved transitional slot is a typed refusal"),
            ProvenanceConstructionError::MissingTransitional
        );
    }
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

#[test]
fn explicitly_absent_transitional_is_ok() {
    let envelope = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        TransitionalEvidence::ExplicitlyAbsent,
        vec![record("rec:delta:1")],
    )
    .expect("an affirmative no-transitional claim is a typed choice, not a default");

    assert_eq!(
        envelope.transitional(),
        &TransitionalEvidence::ExplicitlyAbsent
    );
}

#[test]
fn hypothesized_commencement_is_stored_not_upgraded() {
    let hypothesized = commencement(EvidenceClass::HypothesizedFromOracleDiff)
        .expect("oracle-diff hypothesized commencement is admissible evidence data");
    let envelope = EditionProvenanceEnvelope::try_new(
        vec![act("act:a")],
        vec![provision("cc:work/statya-1")],
        hypothesized.clone(),
        declared_transition(),
        vec![record("rec:delta:1")],
    )
    .expect("hypothesized commencement constructs a full packet");

    let stored = envelope.commencement();
    assert_eq!(stored, &hypothesized);
    assert_eq!(
        stored.evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
    assert_ne!(
        stored.evidence_class(),
        EvidenceClass::Legislative,
        "stored as data, never upgraded to legislative proof (D308)"
    );
}

#[test]
fn envelope_compare_by_value_is_deterministic() {
    let first = EditionProvenanceEnvelope::try_new(
        vec![act("act:b"), act("act:a")],
        vec![provision("cc:work/statya-2"), provision("cc:work/statya-1")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:2"), record("rec:delta:1")],
    )
    .expect("first packet");
    let second = EditionProvenanceEnvelope::try_new(
        vec![act("act:a"), act("act:b")],
        vec![provision("cc:work/statya-1"), provision("cc:work/statya-2")],
        commencement(EvidenceClass::Legislative).unwrap(),
        declared_transition(),
        vec![record("rec:delta:1"), record("rec:delta:2")],
    )
    .expect("same packet, different input order");
    let flipped_transitional = EditionProvenanceEnvelope::try_new(
        vec![act("act:a"), act("act:b")],
        vec![provision("cc:work/statya-1"), provision("cc:work/statya-2")],
        commencement(EvidenceClass::Legislative).unwrap(),
        TransitionalEvidence::ExplicitlyAbsent,
        vec![record("rec:delta:1"), record("rec:delta:2")],
    )
    .expect("same packet except the transitional slot");

    assert_eq!(
        first, second,
        "input order never changes value: packet lists are canonically sorted"
    );
    assert_ne!(
        first, flipped_transitional,
        "a different transitional slot is a different envelope value"
    );
}

#[test]
fn non_claims_name_r070_open_and_deny_activation_trigger() {
    let envelope = full_packet().expect("complete synthetic packet");
    let non_claims = envelope.non_claims();
    let joined = non_claims.join("\n");

    assert!(
        !non_claims.is_empty(),
        "the envelope must carry a non-claims honesty surface"
    );
    assert!(
        joined.contains("R070 stays open"),
        "constructing an envelope is evidence bookkeeping, never R070 coverage"
    );
    assert!(
        joined.contains("constructor-as-evidence"),
        "the D289/D308 non-claim must stay pinned on the envelope"
    );
    assert!(
        joined.contains("Not ActivationTrigger"),
        "the D252 effect_selector_modes vocabulary stays YAML-only (D216)"
    );
    assert!(
        joined.contains("Not TransitionalResolver"),
        "ADR-0021 stays [proposed]; no resolver and no chronology-only default"
    );
    assert!(
        joined.contains("D326"),
        "the (from, to] window and edition_delta keep-rule are untouched"
    );
    assert!(
        joined.contains("not a runtime selector"),
        "commencement evidence denies runtime effect resolution"
    );
    assert!(
        joined.contains("split-commencement"),
        "one packet is one CommencementEvidence, not a split-commencement algebra"
    );
}
