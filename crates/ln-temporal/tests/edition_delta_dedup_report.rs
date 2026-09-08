//! M203 S07 T02: duplicate provenance evidence is explicit, while fold-level
//! canonicalisation exposes deterministic counters instead of silent loss.

use ln_temporal::domain::{
    edition_delta, AmendingActId, AmendmentEvent, AmendmentFacetKind, CanonRecordId,
    ComponentConceptId, EvidenceClass, ThreeCanonEventLog, ThreeCanonRecord,
};
use ln_temporal::provenance::{
    CommencementEvidence, EditionDeltaError, EditionProvenanceEnvelope, ProvenanceAdmission,
    ProvenanceConstructionError, TransitionalEvidence,
};

fn id<T>(parse: fn(&str) -> Result<T, ln_temporal::domain::IdError>, value: &str) -> T {
    parse(value).expect("valid test id")
}

fn act(value: &str) -> AmendingActId {
    id(AmendingActId::parse, value)
}
fn cc(value: &str) -> ComponentConceptId {
    id(ComponentConceptId::parse, value)
}
fn record(value: &str) -> CanonRecordId {
    id(CanonRecordId::parse, value)
}

fn commencement() -> CommencementEvidence {
    CommencementEvidence::try_new(20, EvidenceClass::Legislative, "rec:commencement")
        .expect("valid commencement")
}

fn admission(target: &str) -> ProvenanceAdmission {
    ProvenanceAdmission::try_new(
        cc(target),
        20,
        EvidenceClass::Legislative,
        "rec:commencement",
        TransitionalEvidence::ExplicitlyAbsent,
    )
    .expect("valid admission")
}

fn amendment(record_id: &str, target: &str, act_id: &str, day: i64) -> ThreeCanonRecord {
    ThreeCanonRecord::Amendment(
        AmendmentEvent::try_new(
            record(record_id),
            cc(target),
            day,
            act(act_id),
            EvidenceClass::HypothesizedFromOracleDiff,
            vec![AmendmentFacetKind::Text],
            None,
        )
        .expect("valid amendment"),
    )
}

#[test]
fn packet_duplicate_delta_evidence_is_typed_refusal() {
    let error = EditionProvenanceEnvelope::try_new_raw(
        &["act:amend"],
        &["cc:44-fz:statya-93"],
        commencement(),
        TransitionalEvidence::ExplicitlyAbsent,
        &["rec:delta", "rec:delta"],
    )
    .expect_err("duplicate packet evidence must fail closed");

    assert_eq!(error, ProvenanceConstructionError::DuplicateDeltaEvidence);
}

#[test]
fn repeated_act_in_window_is_folded_and_reported() {
    let target = "cc:44-fz:statya-93";
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment("rec:amendment-1", target, "act:amend", 10))
        .expect("first event");
    log.append(amendment("rec:amendment-2", target, "act:amend", 11))
        .expect("second event");

    let delta = edition_delta(&log, 0, 20, &[admission(target)]).expect("delta");
    assert_eq!(delta.provisions().len(), 1);
    assert_eq!(
        delta.provisions()[0].provenance().amending_acts(),
        &[act("act:amend")]
    );
    assert_eq!(delta.dedup_report().amending_act_duplicates, 1);
    assert_eq!(delta.dedup_report().delta_evidence_duplicates, 1);
    assert!(!delta.dedup_report().is_zero());
}

#[test]
fn window_without_duplicates_has_zero_report() {
    let target = "cc:44-fz:statya-93";
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment("rec:amendment-1", target, "act:amend", 10))
        .expect("event");

    let delta = edition_delta(&log, 0, 20, &[admission(target)]).expect("delta");
    assert!(delta.dedup_report().is_zero());
    assert_eq!(delta.dedup_report().amending_act_duplicates, 0);
    assert_eq!(delta.dedup_report().delta_evidence_duplicates, 0);
}

#[test]
fn provenance_refusal_remains_whole_edition() {
    let target = "cc:44-fz:statya-93";
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment("rec:amendment-1", target, "act:amend", 10))
        .expect("event");

    let error = edition_delta(&log, 0, 20, &[]).expect_err("missing admission");
    assert!(matches!(
        error,
        EditionDeltaError::MissingAdmission { target: missing } if missing.as_str() == target
    ));
}

#[test]
fn dedup_report_is_deterministic_across_repeated_runs() {
    let target = "cc:44-fz:statya-93";
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment("rec:amendment-1", target, "act:amend", 10))
        .expect("first event");
    log.append(amendment("rec:amendment-2", target, "act:amend", 11))
        .expect("second event");

    let first = edition_delta(&log, 0, 20, &[admission(target)])
        .expect("first delta")
        .dedup_report()
        .clone();
    let second = edition_delta(&log, 0, 20, &[admission(target)])
        .expect("second delta")
        .dedup_report()
        .clone();
    assert_eq!(first, second);
}
