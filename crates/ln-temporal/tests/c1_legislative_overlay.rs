//! C1 legislative overlay on the three-canon event log (M191-kgdyqi S01).
//!
//! Review 10: the C1 amending-act packet is the commit of legal history. This
//! bounded slice admits C1 candidates onto the durable log as an overlay of
//! `AmendmentEvent` records — never as an overview parse (сводка ≠ канон,
//! D174). Fail-closed: overview-shaped input is not a legislative event, and
//! a missing amending-act identity is rejected before the log is touched.
//!
//! Bounded honesty: synthetic provenance is not read as a legislative fact
//! (D179); this is not the D172 AmendmentEvent store-type verdict; ADR-0017
//! grounding stays [bounded] (D145/D098); the 484-FZ pin is composition
//! evidence, not G1. No official corpus is parsed here and R070 stays open.

use ln_temporal::domain::{
    fold_three_canon_at, AmendmentFacetKind, C1Candidate, CanonRecordId, ComponentConceptId,
    EvidenceClass, NormativeState, ThreeCanonEventLog, ThreeCanonLogError, ThreeCanonRecord,
    C1_OVERLAY_NON_CLAIMS,
};

/// Synthetic C1 amending chain (offline; not the real corpus, not the 484 pin).
const ACT_A: &str = "act:syn:2020-01-01:100-fz";
const ACT_B: &str = "act:syn:2021-06-15:200-fz";
const ACT_C: &str = "act:syn:2022-03-01:300-fz";

const TARGET: &str = "cc:work:statya-93";

fn rid(id: &str) -> CanonRecordId {
    CanonRecordId::parse(id).expect("record id")
}

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("cc")
}

/// Legislative C1 candidate from one amending act of the synthetic chain.
fn legislative(
    act_raw: &str,
    day: i64,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) -> C1Candidate {
    C1Candidate::LegislativeAmendment {
        target: cc(TARGET),
        effect_day: day,
        amending_act_raw: act_raw.to_owned(),
        evidence: EvidenceClass::Legislative,
        facets,
        force_transition: force,
    }
}

// ── Must-have: synthetic amending chain appends with provenance ─────────────

#[test]
fn c1_synthetic_amending_chain_appends_events_with_provenance() {
    let mut log = ThreeCanonEventLog::empty();

    log.append_c1_candidate(
        rid("rec:c1-100"),
        legislative(ACT_A, 100, vec![AmendmentFacetKind::Text], None),
    )
    .expect("act A appends");
    log.append_c1_candidate(
        rid("rec:c1-200"),
        legislative(ACT_B, 200, vec![AmendmentFacetKind::Structural], None),
    )
    .expect("act B appends");
    log.append_c1_candidate(
        rid("rec:c1-300"),
        legislative(
            ACT_C,
            300,
            vec![AmendmentFacetKind::Force],
            Some(NormativeState::InForce),
        ),
    )
    .expect("act C appends");
    assert_eq!(log.len(), 3);

    // amending_act_id on events: every amendment carries its act provenance.
    let at350 = fold_three_canon_at(&log, 350).expect("fold@350");
    assert_eq!(at350.events().len(), 3);
    let provenance: Vec<(&str, &str)> = at350
        .events()
        .iter()
        .map(|record| match record {
            ThreeCanonRecord::Amendment(event) => {
                (event.record_id().as_str(), event.provenance().as_str())
            }
            other => panic!(
                "C1 chain fold must hold amendment events, got {:?}",
                other.record_id()
            ),
        })
        .collect();
    assert_eq!(
        provenance,
        vec![
            ("rec:c1-100", ACT_A),
            ("rec:c1-200", ACT_B),
            ("rec:c1-300", ACT_C),
        ]
    );

    // Point projection mid-chain: only acts effective by t are visible.
    let at150 = fold_three_canon_at(&log, 150).expect("fold@150");
    assert_eq!(at150.events().len(), 1);
    assert_eq!(at150.force_status(), NormativeState::Unknown);
    let at250 = fold_three_canon_at(&log, 250).expect("fold@250");
    assert_eq!(at250.events().len(), 2);
    assert_eq!(at250.force_status(), NormativeState::Unknown);

    // The last C1 act's Force facet drives the readout at the full horizon.
    assert_eq!(at350.force_status(), NormativeState::InForce);
    assert!(!at350.force_conflict());
}

// ── Must-have: overview-shaped input is not a legislative event ─────────────

#[test]
fn hostile_overview_shaped_input_is_not_a_legislative_event() {
    let mut log = ThreeCanonEventLog::empty();

    // Consultant change-overview shape (сводка изменений): a hint, never the
    // legislative event itself (D174). The overlay rejects it fail-closed.
    let overview = C1Candidate::OverviewHint {
        target: cc(TARGET),
        summary: "сводка изменений: внесены изменения в статью 93".to_owned(),
    };
    let err = log
        .append_c1_candidate(rid("rec:ov-1"), overview)
        .expect_err("overview must not become a legislative event");
    assert_eq!(err, ThreeCanonLogError::OverviewNotLegislativeEvent);
    assert_eq!(log.len(), 0, "rejected overview must not touch the log");

    // The rejection does not poison the log: a real C1 act appends after it.
    log.append_c1_candidate(
        rid("rec:c1-100"),
        legislative(ACT_A, 100, vec![AmendmentFacetKind::Text], None),
    )
    .expect("post-rejection append");
    let projection = fold_three_canon_at(&log, 100).expect("fold");
    assert_eq!(projection.events().len(), 1);
    assert_eq!(projection.force_status(), NormativeState::Unknown);
}

// ── Must-have: missing amending-act identity fails closed ───────────────────

#[test]
fn missing_amending_act_identity_fails_closed() {
    let mut log = ThreeCanonEventLog::empty();

    let empty = legislative("", 100, vec![AmendmentFacetKind::Text], None);
    let err = log
        .append_c1_candidate(rid("rec:no-act"), empty)
        .expect_err("empty act identity must fail closed");
    assert_eq!(err, ThreeCanonLogError::MissingAmendingActIdentity);

    let whitespace = legislative("   ", 100, vec![AmendmentFacetKind::Text], None);
    let err = log
        .append_c1_candidate(rid("rec:ws-act"), whitespace)
        .expect_err("whitespace act identity must fail closed");
    assert_eq!(err, ThreeCanonLogError::MissingAmendingActIdentity);

    // Non-empty but non-identifier input fails on the substrate charset.
    let malformed = legislative("поправка 484", 100, vec![AmendmentFacetKind::Text], None);
    let err = log
        .append_c1_candidate(rid("rec:bad-act"), malformed)
        .expect_err("non-identifier act identity must fail closed");
    assert!(matches!(err, ThreeCanonLogError::InvalidId(_)));

    assert_eq!(log.len(), 0, "no rejected candidate may enter the log");
}

// ── Evidence class is declared, never upgraded by the overlay ───────────────

#[test]
fn overlay_preserves_declared_evidence_class_never_upgrades() {
    let mut log = ThreeCanonEventLog::empty();

    // A candidate that arrives with only hint-grade evidence stays hint-grade
    // (D182/D183 bounds unchanged; an overview hint never upgrades here).
    let hint = C1Candidate::LegislativeAmendment {
        target: cc(TARGET),
        effect_day: 100,
        amending_act_raw: ACT_A.to_owned(),
        evidence: EvidenceClass::EditorialHint,
        facets: vec![AmendmentFacetKind::Text],
        force_transition: None,
    };
    log.append_c1_candidate(rid("rec:hint"), hint)
        .expect("declared hint stores as hint");

    let projection = fold_three_canon_at(&log, 100).expect("fold");
    match &projection.events()[0] {
        ThreeCanonRecord::Amendment(event) => {
            assert_eq!(event.evidence(), EvidenceClass::EditorialHint);
        }
        other => panic!("unexpected record {:?}", other.record_id()),
    }
}

// ── Overlay delegates duplicate / ordering checks to the substrate ──────────

#[test]
fn overlay_delegates_duplicate_and_ordering_to_substrate() {
    let mut log = ThreeCanonEventLog::empty();
    log.append_c1_candidate(
        rid("rec:c1-100"),
        legislative(ACT_A, 100, vec![AmendmentFacetKind::Text], None),
    )
    .expect("first append");

    let duplicate = log
        .append_c1_candidate(
            rid("rec:c1-100"),
            legislative(ACT_B, 150, vec![AmendmentFacetKind::Text], None),
        )
        .expect_err("duplicate record identity must fail closed");
    assert_eq!(duplicate, ThreeCanonLogError::DuplicateRecordId);

    let unordered = log
        .append_c1_candidate(
            rid("rec:c1-050"),
            legislative(ACT_B, 50, vec![AmendmentFacetKind::Text], None),
        )
        .expect_err("earlier-than-last day must fail closed");
    assert_eq!(unordered, ThreeCanonLogError::OrderingConflict);

    assert_eq!(log.len(), 1);
}

// ── Bounded non-claims stay declared (D172/D179; 484 pin ≠ G1) ──────────────

#[test]
fn c1_overlay_non_claims_stay_declared() {
    assert!(C1_OVERLAY_NON_CLAIMS
        .iter()
        .any(|c| c.contains("never becomes a legislative event")));
    assert!(C1_OVERLAY_NON_CLAIMS
        .iter()
        .any(|c| c.contains("not read as a legislative fact")));
    assert!(C1_OVERLAY_NON_CLAIMS
        .iter()
        .any(|c| c.contains("not the D172 store-type verdict")));
    assert!(C1_OVERLAY_NON_CLAIMS.iter().any(|c| c.contains("not G1")));
    assert!(C1_OVERLAY_NON_CLAIMS
        .iter()
        .any(|c| c.contains("not official-corpus parsing")));
}
