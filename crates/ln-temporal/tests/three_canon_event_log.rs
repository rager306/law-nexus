//! Bounded durable three-canon event log (M190-lo7ucr S01, ADR-0017 §1a–§1c).
//!
//! Append-only log holding three record kinds: `AmendmentEvent` (n-ary causal
//! node, §1b), `EditionOracle` (checksum, not canon, §1c) and
//! assertion-or-effect records (G0(a) bounded payload; no lifecycle engine).
//! `fold_three_canon_at` is a point projection of canon events with
//! `effect_day <= t`. An empty log folds to an empty projection with force
//! `Unknown` — never `InForce`, never a membership claim. Unordered appends,
//! duplicate record identities and empty identity fail closed.
//!
//! Not checkout, not interval algebra (D228); no operation-registry.yaml or
//! model-crystal.md parsing into types (D216); the G0(a) assertion lifecycle
//! stays design-only data (D222/D233).

use ln_temporal::domain::{
    fold_three_canon_at, AmendingActId, AmendmentEvent, AmendmentFacetKind, AssertionOrEffect,
    AssertionOrEffectPayload, CanonRecordId, ComponentConceptId, EditionOracle, EvidenceClass,
    NormativeState, ThreeCanonEventLog, ThreeCanonLogError, ThreeCanonRecord,
};

fn rid(id: &str) -> CanonRecordId {
    CanonRecordId::parse(id).expect("record id")
}

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

fn act(id: &str) -> AmendingActId {
    AmendingActId::parse(id).expect("act")
}

fn amendment(
    id: &str,
    day: i64,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) -> ThreeCanonRecord {
    ThreeCanonRecord::Amendment(
        AmendmentEvent::try_new(
            rid(id),
            cc("cc:art-1"),
            day,
            act("act:amend-1"),
            EvidenceClass::Legislative,
            facets,
            force,
        )
        .expect("amendment"),
    )
}

fn oracle(id: &str, day: i64) -> ThreeCanonRecord {
    ThreeCanonRecord::EditionOracle(
        EditionOracle::try_new(rid(id), cc("cc:art-1"), day, "sha256:oracle-digest")
            .expect("oracle"),
    )
}

fn assertion_effect(id: &str, day: i64, status: NormativeState) -> ThreeCanonRecord {
    ThreeCanonRecord::AssertionOrEffect(
        AssertionOrEffect::try_new(
            rid(id),
            cc("cc:art-1"),
            day,
            EvidenceClass::HypothesizedFromOracleDiff,
            AssertionOrEffectPayload::Effect(status),
        )
        .expect("assertion-or-effect"),
    )
}

fn assertion_claim(id: &str, day: i64) -> ThreeCanonRecord {
    ThreeCanonRecord::AssertionOrEffect(
        AssertionOrEffect::try_new(
            rid(id),
            cc("cc:art-1"),
            day,
            EvidenceClass::EditorialHint,
            AssertionOrEffectPayload::Assertion,
        )
        .expect("assertion claim"),
    )
}

// ── Must-have: empty fold ────────────────────────────────────────────────────

#[test]
fn empty_log_folds_to_empty_unknown_not_in_force() {
    let log = ThreeCanonEventLog::empty();
    assert_eq!(log.len(), 0);
    assert!(log.is_empty());

    let projection = fold_three_canon_at(&log, 100).expect("fold");
    assert!(projection.is_empty());
    assert_eq!(projection.as_of_day(), 100);
    // Empty does not imply InForce (D304): Unknown is the only honest outcome.
    assert_eq!(projection.force_status(), NormativeState::Unknown);
    assert!(!projection.force_conflict());
    assert!(projection
        .non_claims()
        .iter()
        .any(|c| c.contains("Empty fold")));
    assert!(projection
        .non_claims()
        .iter()
        .any(|c| c.contains("checksum")));
}

// ── Must-have: ordered events fold at t ──────────────────────────────────────

#[test]
fn ordered_events_fold_as_point_projection_at_t() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment(
        "rec:a1",
        1,
        vec![AmendmentFacetKind::Structural],
        None,
    ))
    .expect("a1");
    log.append(amendment(
        "rec:e1",
        5,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    ))
    .expect("e1");
    log.append(amendment(
        "rec:t1",
        10,
        vec![AmendmentFacetKind::Text],
        None,
    ))
    .expect("t1");
    assert_eq!(log.len(), 3);

    // Fold at t=5: day-10 event is invisible; force readout is InForce.
    let at5 = fold_three_canon_at(&log, 5).expect("fold@5");
    assert_eq!(at5.events().len(), 2);
    assert_eq!(at5.events()[0].record_id().as_str(), "rec:a1");
    assert_eq!(at5.events()[1].record_id().as_str(), "rec:e1");
    assert_eq!(at5.force_status(), NormativeState::InForce);
    assert!(!at5.force_conflict());

    // Same-day boundary: effect_day == as_of_day is included (<=, not <).
    let at1 = fold_three_canon_at(&log, 1).expect("fold@1");
    assert_eq!(at1.events().len(), 1);

    // Before any event: empty projection, Unknown force.
    let at0 = fold_three_canon_at(&log, 0).expect("fold@0");
    assert!(at0.is_empty());
    assert_eq!(at0.force_status(), NormativeState::Unknown);

    // Full horizon includes every canon event.
    let at10 = fold_three_canon_at(&log, 10).expect("fold@10");
    assert_eq!(at10.events().len(), 3);
    assert_eq!(at10.force_status(), NormativeState::InForce);
}

// ── Must-have: hostile unordered append fails closed ─────────────────────────

#[test]
fn hostile_unordered_append_fails_closed_and_keeps_log_intact() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment(
        "rec:a1",
        5,
        vec![AmendmentFacetKind::Structural],
        None,
    ))
    .expect("a1");

    let err = log
        .append(amendment("rec:a2", 3, vec![AmendmentFacetKind::Text], None))
        .expect_err("unordered append must fail closed");
    assert_eq!(err, ThreeCanonLogError::OrderingConflict);

    // Append-only integrity: the rejected record is not partially stored.
    assert_eq!(log.len(), 1);
    assert_eq!(log.records()[0].record_id().as_str(), "rec:a1");

    // Same-day appends are legal (non-decreasing order, ties by append order).
    log.append(amendment(
        "rec:a3",
        5,
        vec![AmendmentFacetKind::Industrial],
        None,
    ))
    .expect("same-day append");
    assert_eq!(log.len(), 2);
}

// ── Must-have: identity required ─────────────────────────────────────────────

#[test]
fn empty_or_invalid_identity_fails_closed() {
    assert!(CanonRecordId::parse("").is_err());
    assert!(CanonRecordId::parse("has space").is_err());
    assert!(CanonRecordId::parse(&"x".repeat(65)).is_err());
    assert!(CanonRecordId::parse("rec:ok-1_2.3").is_ok());
}

#[test]
fn duplicate_record_identity_fails_closed() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment(
        "rec:dup",
        1,
        vec![AmendmentFacetKind::Text],
        None,
    ))
    .expect("first");
    let err = log
        .append(amendment(
            "rec:dup",
            2,
            vec![AmendmentFacetKind::Text],
            None,
        ))
        .expect_err("duplicate identity must fail closed");
    assert_eq!(err, ThreeCanonLogError::DuplicateRecordId);
    assert_eq!(log.len(), 1);
}

// ── Negative surface: oracle is a checksum, not canon ────────────────────────

#[test]
fn oracle_records_are_held_but_never_projected_as_events() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(oracle("rec:o1", 4)).expect("oracle");
    assert_eq!(log.len(), 1);

    // The oracle sits on the log timeline but is not a canon event: the fold
    // stays empty and force stays Unknown (§1c — never canon).
    let projection = fold_three_canon_at(&log, 10).expect("fold");
    assert!(projection.is_empty());
    assert_eq!(projection.force_status(), NormativeState::Unknown);
    assert!(projection
        .non_claims()
        .iter()
        .any(|c| c.contains("never writes an oracle")));

    // Oracle day does not break the ordering contract either.
    log.append(amendment(
        "rec:a1",
        4,
        vec![AmendmentFacetKind::Structural],
        None,
    ))
    .expect("same-day after oracle");
    let projection = fold_three_canon_at(&log, 4).expect("fold");
    assert_eq!(projection.events().len(), 1);
    assert!(projection.events()[0].is_canon_event());
}

// ── Negative surface: fail-closed record validation ──────────────────────────

#[test]
fn amendment_facet_and_force_transition_validation_fails_closed() {
    // Empty facet set is meaningless — reject.
    let err = AmendmentEvent::try_new(
        rid("rec:x1"),
        cc("cc:art-1"),
        1,
        act("act:a"),
        EvidenceClass::Legislative,
        Vec::new(),
        None,
    )
    .expect_err("empty facets");
    assert_eq!(err, ThreeCanonLogError::EmptyFacets);

    // Force facet requires a written transition target.
    let err = AmendmentEvent::try_new(
        rid("rec:x2"),
        cc("cc:art-1"),
        1,
        act("act:a"),
        EvidenceClass::Legislative,
        vec![AmendmentFacetKind::Force],
        None,
    )
    .expect_err("force facet without transition");
    assert_eq!(err, ThreeCanonLogError::ForceFacetMismatch);

    // A transition without the Force facet is unbound — reject.
    let err = AmendmentEvent::try_new(
        rid("rec:x3"),
        cc("cc:art-1"),
        1,
        act("act:a"),
        EvidenceClass::Legislative,
        vec![AmendmentFacetKind::Text],
        Some(NormativeState::InForce),
    )
    .expect_err("transition without force facet");
    assert_eq!(err, ThreeCanonLogError::ForceFacetMismatch);

    // Unknown is a fail-closed outcome, never a writable transition.
    let err = AmendmentEvent::try_new(
        rid("rec:x4"),
        cc("cc:art-1"),
        1,
        act("act:a"),
        EvidenceClass::Legislative,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Unknown),
    )
    .expect_err("Unknown transition");
    assert_eq!(err, ThreeCanonLogError::UnknownNotTransition);
}

#[test]
fn oracle_requires_non_empty_checksum() {
    let err =
        EditionOracle::try_new(rid("rec:o2"), cc("cc:art-1"), 1, "").expect_err("empty digest");
    assert_eq!(err, ThreeCanonLogError::EmptyDigest);
}

#[test]
fn effect_payload_rejects_unknown_transition() {
    let err = AssertionOrEffect::try_new(
        rid("rec:x5"),
        cc("cc:art-1"),
        1,
        EvidenceClass::Legislative,
        AssertionOrEffectPayload::Effect(NormativeState::Unknown),
    )
    .expect_err("Unknown effect");
    assert_eq!(err, ThreeCanonLogError::UnknownNotTransition);
}

// ── Negative surface: point readout conflict stays Unknown ───────────────────

#[test]
fn same_day_conflicting_force_outcomes_fold_to_unknown() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment(
        "rec:e1",
        5,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    ))
    .expect("e1");
    log.append(assertion_effect("rec:f1", 5, NormativeState::Suspended))
        .expect("f1");

    let projection = fold_three_canon_at(&log, 5).expect("fold");
    assert_eq!(projection.events().len(), 2);
    assert_eq!(projection.force_status(), NormativeState::Unknown);
    assert!(projection.force_conflict());
}

#[test]
fn assertion_claim_records_project_but_never_drive_force() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(assertion_claim("rec:cl1", 2)).expect("claim");

    let projection = fold_three_canon_at(&log, 5).expect("fold");
    assert_eq!(projection.events().len(), 1);
    // A bare assertion is a ledger claim candidate, not a force outcome.
    assert_eq!(projection.force_status(), NormativeState::Unknown);
    assert!(!projection.force_conflict());
}

#[test]
fn later_force_event_wins_at_its_day() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(amendment(
        "rec:e1",
        5,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    ))
    .expect("e1");
    log.append(amendment(
        "rec:e2",
        8,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Repealed),
    ))
    .expect("e2");

    let at7 = fold_three_canon_at(&log, 7).expect("fold@7");
    assert_eq!(at7.force_status(), NormativeState::InForce);

    let at8 = fold_three_canon_at(&log, 8).expect("fold@8");
    assert_eq!(at8.force_status(), NormativeState::Repealed);
}
