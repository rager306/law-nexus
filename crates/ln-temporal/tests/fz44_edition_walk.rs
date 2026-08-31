//! Owner-requested model exercise (2026-08-31): walk the temporal model over
//! 44-FZ edition 0 (the enacting law of 2013-04-05) plus three amending laws,
//! folding the durable three-canon event log at governing dates.
//!
//! What this proves about the model (bounded, synthetic identities):
//! - edition 0 is admitted as a legislative event with act provenance;
//! - three amending laws append in day order with per-act provenance;
//! - point folds at governing dates expose exactly the events effective by t;
//! - force readout follows the latest force-bearing day (InForce → Repealed);
//! - an aggregate (log-wide) fold with same-day divergent force outcomes
//!   across different component concepts surfaces honestly as
//!   `force_conflict` + `Unknown` (fail-closed, never a silent mix);
//! - the Work identity stays one stable `cc:44-fz` namespace (R081 shape:
//!   dated editions are expressions of one Work, not new Works);
//! - admission fails closed on overview hints, empty act identity, duplicate
//!   record ids and out-of-order effect days; folds are deterministic.
//!
//! Bounded honesty: synthetic identities are not the real corpus; R070
//! (edition provenance) stays open (D179); this is not the D-03 checkout
//! type and not interval algebra (D228). No YAML minting (D216/D312).

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    fold_three_canon_at, AmendmentFacetKind, C1Candidate, CanonRecordId, ComponentConceptId,
    EditionOracle, EvidenceClass, NormativeState, ThreeCanonEventLog, ThreeCanonLogError,
    ThreeCanonProjection, ThreeCanonRecord,
};

// One stable Work (R081): every component concept lives in this namespace.
const FZ44: &str = "cc:44-fz";
const STATYA_5: &str = "cc:44-fz:statya-5";
const STATYA_93: &str = "cc:44-fz:statya-93";
const STATYA_93_1: &str = "cc:44-fz:statya-93-1";

// Edition 0: the enacting law (published 2013-04-05, in force 2013-09-01).
const EDITION0_ACT: &str = "act:44-fz:2013-04-05:n44";
// Three amending laws (условные номера для симуляции).
const LAW1_ACT: &str = "act:44-fz:amend-1:2015-07-13";
const LAW2_ACT: &str = "act:44-fz:amend-2:2018-12-25";
const LAW3_ACT: &str = "act:44-fz:amend-3:2021-03-01";

fn rid(id: &str) -> CanonRecordId {
    CanonRecordId::parse(id).expect("record id")
}

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("component concept")
}

fn day(iso_day: &str) -> i64 {
    legal_act_effect_day_to_ordinal(iso_day).expect("calendar day")
}

/// Legislative candidate: one change event carried by an amending act.
fn change(
    _record: &str,
    target: &str,
    act_raw: &str,
    iso_day: &str,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) -> C1Candidate {
    C1Candidate::LegislativeAmendment {
        target: cc(target),
        effect_day: day(iso_day),
        amending_act_raw: act_raw.to_owned(),
        evidence: EvidenceClass::Legislative,
        facets,
        force_transition: force,
    }
}

/// Admit one change event into one log (fail-closed path of the overlay).
fn admit(
    log: &mut ThreeCanonEventLog,
    record: &str,
    target: &str,
    act_raw: &str,
    iso_day: &str,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) {
    log.append_c1_candidate(
        rid(&format!("rec:{record}")),
        change(record, target, act_raw, iso_day, facets, force),
    )
    .expect("admission");
}

/// Edition-oracle record: a text checksum of an edition, not a canon event.
fn oracle(record: &str, iso_day: &str) -> ThreeCanonRecord {
    ThreeCanonRecord::EditionOracle(
        EditionOracle::try_new(
            rid(record),
            cc(FZ44),
            day(iso_day),
            "sha256:synthetic-edition-digest",
        )
        .expect("edition oracle"),
    )
}

fn fold(log: &ThreeCanonEventLog, iso_day: &str) -> ThreeCanonProjection {
    fold_three_canon_at(log, day(iso_day)).expect("fold")
}

fn amendment_records(projection: &ThreeCanonProjection) -> Vec<(String, String)> {
    projection
        .events()
        .iter()
        .filter_map(|record| match record {
            ThreeCanonRecord::Amendment(event) => Some((
                event.record_id().as_str().to_owned(),
                event.provenance().as_str().to_owned(),
            )),
            _ => None,
        })
        .collect()
}

// ── The walk: edition 0 → laws 1, 2, 3, folded at governing dates ───────────

#[test]
fn fz44_edition0_plus_three_amendments_walks_the_model() {
    // One log per component concept: per-статья state evolution.
    let mut statya_5 = ThreeCanonEventLog::empty();
    let mut statya_93 = ThreeCanonEventLog::empty();
    let mut statya_93_1 = ThreeCanonEventLog::empty();
    // One combined log: the aggregate (log-wide) readout.
    let mut combined = ThreeCanonEventLog::empty();

    // Edition-oracle checksum of edition 0, published on enactment day:
    // not a canon event, but the append-only timeline still keeps it ordered.
    combined
        .append(oracle("orc:ed0", "2013-04-05"))
        .expect("edition oracle");

    // Edition 0: the enacting law puts statya-5/statya-93 into force.
    admit(
        &mut statya_5,
        "ed0-5",
        STATYA_5,
        EDITION0_ACT,
        "2013-09-01",
        vec![
            AmendmentFacetKind::Structural,
            AmendmentFacetKind::Text,
            AmendmentFacetKind::Force,
        ],
        Some(NormativeState::InForce),
    );
    admit(
        &mut statya_93,
        "ed0-93",
        STATYA_93,
        EDITION0_ACT,
        "2013-09-01",
        vec![
            AmendmentFacetKind::Structural,
            AmendmentFacetKind::Text,
            AmendmentFacetKind::Force,
        ],
        Some(NormativeState::InForce),
    );
    admit(
        &mut combined,
        "ed0-5c",
        STATYA_5,
        EDITION0_ACT,
        "2013-09-01",
        vec![
            AmendmentFacetKind::Structural,
            AmendmentFacetKind::Text,
            AmendmentFacetKind::Force,
        ],
        Some(NormativeState::InForce),
    );
    admit(
        &mut combined,
        "ed0-93c",
        STATYA_93,
        EDITION0_ACT,
        "2013-09-01",
        vec![
            AmendmentFacetKind::Structural,
            AmendmentFacetKind::Text,
            AmendmentFacetKind::Force,
        ],
        Some(NormativeState::InForce),
    );
    // Закон №1: text change of statya-5, effective 2016-01-01.
    admit(
        &mut statya_5,
        "law1-5",
        STATYA_5,
        LAW1_ACT,
        "2016-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );
    admit(
        &mut combined,
        "law1-5c",
        STATYA_5,
        LAW1_ACT,
        "2016-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );

    // Закон №2: statya-5 text change again + new statya-93-1 introduced.
    admit(
        &mut statya_5,
        "law2-5",
        STATYA_5,
        LAW2_ACT,
        "2019-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );
    admit(
        &mut statya_93_1,
        "law2-93-1",
        STATYA_93_1,
        LAW2_ACT,
        "2019-01-01",
        vec![AmendmentFacetKind::Structural, AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    admit(
        &mut combined,
        "law2-5c",
        STATYA_5,
        LAW2_ACT,
        "2019-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );
    admit(
        &mut combined,
        "law2-93-1c",
        STATYA_93_1,
        LAW2_ACT,
        "2019-01-01",
        vec![AmendmentFacetKind::Structural, AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );

    // Закон №3: statya-93 loses force; statya-5 stays in force (same day!).
    admit(
        &mut statya_93,
        "law3-93",
        STATYA_93,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Repealed),
    );
    admit(
        &mut statya_5,
        "law3-5",
        STATYA_5,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    admit(
        &mut combined,
        "law3-93c",
        STATYA_93,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Repealed),
    );
    admit(
        &mut combined,
        "law3-5c",
        STATYA_5,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );

    // ── Fold 1: before edition 0 enters force — nothing, Unknown ────────────
    let before = fold(&statya_5, "2013-08-31");
    assert_eq!(before.events().len(), 0, "nothing is effective yet");
    assert_eq!(before.force_status(), NormativeState::Unknown);
    assert!(!before.force_conflict());
    assert!(
        !before.non_claims().is_empty(),
        "the projection carries its non-claims"
    );

    // ── Fold 2: edition 0 in force ──────────────────────────────────────────
    let at_ed0 = fold(&statya_5, "2013-09-01");
    assert_eq!(at_ed0.events().len(), 1);
    assert_eq!(at_ed0.force_status(), NormativeState::InForce);
    assert_eq!(
        amendment_records(&at_ed0),
        vec![("rec:ed0-5".to_owned(), EDITION0_ACT.to_owned())]
    );

    // ── Fold 3: after закон №1 — amendment provenance is per-act ────────────
    let after_law1 = fold(&statya_5, "2016-06-01");
    assert_eq!(after_law1.events().len(), 2);
    assert_eq!(after_law1.force_status(), NormativeState::InForce);
    assert_eq!(
        amendment_records(&after_law1)[1],
        ("rec:law1-5".to_owned(), LAW1_ACT.to_owned())
    );

    // ── Fold 4: after закон №2 — statya-93-1 exists from 2019-01-01 ─────────
    let after_law2_93_1 = fold(&statya_93_1, "2019-06-01");
    assert_eq!(after_law2_93_1.events().len(), 1);
    assert_eq!(after_law2_93_1.force_status(), NormativeState::InForce);
    let before_law2 = fold(&statya_93_1, "2018-12-31");
    assert_eq!(
        before_law2.events().len(),
        0,
        "statya-93-1 does not exist yet"
    );

    // ── Fold 5: after закон №3 — statya-93 is Repealed ──────────────────────
    let after_law3_93 = fold(&statya_93, "2022-01-01");
    assert_eq!(after_law3_93.events().len(), 2);
    assert_eq!(after_law3_93.force_status(), NormativeState::Repealed);
    assert!(!after_law3_93.force_conflict());

    // ── Fold 6: statya-5 stays InForce through the whole walk ───────────────
    let after_law3_5 = fold(&statya_5, "2022-01-01");
    assert_eq!(after_law3_5.events().len(), 4);
    assert_eq!(after_law3_5.force_status(), NormativeState::InForce);

    // ── Fold 7: combined aggregate at 2019-06-01 — InForce, no conflict ─────
    let combined_2019 = fold(&combined, "2019-06-01");
    assert_eq!(combined_2019.force_status(), NormativeState::InForce);
    assert!(!combined_2019.force_conflict());

    // ── Fold 8: combined aggregate at 2021-07-01 — honest conflict ──────────
    // Same day, two component concepts, divergent force outcomes
    // (statya-5 InForce vs statya-93 Repealed). The log-wide fold refuses to
    // mix them: Unknown + force_conflict (fail-closed honesty).
    let combined_2022 = fold(&combined, "2022-01-01");
    assert!(combined_2022.force_conflict());
    assert_eq!(combined_2022.force_status(), NormativeState::Unknown);
    assert_eq!(combined_2022.events().len(), 7, "canon events only");

    // The edition-oracle checksum never enters the canon projection.
    assert!(combined
        .records()
        .iter()
        .any(|record| matches!(record, ThreeCanonRecord::EditionOracle(_))));

    // ── R081 shape: one stable Work, no Work minted per amendment ───────────
    let mut works: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for record in combined.records() {
        let target: &str = match record {
            ThreeCanonRecord::Amendment(event) => event.target().as_str(),
            ThreeCanonRecord::EditionOracle(oracle) => oracle.target().as_str(),
            ThreeCanonRecord::AssertionOrEffect(effect) => effect.target().as_str(),
        };
        let work: String = target.split(':').take(2).collect::<Vec<_>>().join(":");
        works.insert(work);
    }
    assert_eq!(works.len(), 1, "one stable Work namespace");
    assert!(works.contains(FZ44));

    // ── Determinism: the same fold twice is the same projection ─────────────
    assert_eq!(fold(&combined, "2022-01-01"), combined_2022);
}

// ── Fail-closed admissions on the 44-FZ log ─────────────────────────────────

#[test]
fn fz44_walk_admission_fails_closed() {
    let mut log = ThreeCanonEventLog::empty();

    // Consultant overview (сводка изменений) is a hint, never the event.
    let overview = C1Candidate::OverviewHint {
        target: cc(STATYA_93),
        summary: "сводка изменений в статью 93 закона 44-ФЗ".to_owned(),
    };
    assert_eq!(
        log.append_c1_candidate(rid("rec:ov"), overview)
            .expect_err("overview rejected"),
        ThreeCanonLogError::OverviewNotLegislativeEvent
    );

    // Missing amending-act identity rejected before the log is touched.
    let err = log
        .append_c1_candidate(
            rid("rec:no-act"),
            change("rec:no-act", STATYA_93, "", "2013-09-01", vec![], None),
        )
        .expect_err("empty act rejected");
    assert_eq!(err, ThreeCanonLogError::MissingAmendingActIdentity);

    // Out-of-order effect day rejected by the append itself.
    admit(
        &mut log,
        "ed0-93",
        STATYA_93,
        EDITION0_ACT,
        "2013-09-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    let err = log
        .append_c1_candidate(
            rid("rec:early"),
            change(
                "rec:early",
                STATYA_93,
                LAW1_ACT,
                "2013-08-31",
                vec![AmendmentFacetKind::Force],
                Some(NormativeState::InForce),
            ),
        )
        .expect_err("earlier-than-last day rejected");
    assert!(matches!(err, ThreeCanonLogError::OrderingConflict));

    // Duplicate record id rejected. Facet validation runs before the
    // duplicate check, so the probe repeats a fully valid record.
    let err = log
        .append_c1_candidate(
            rid("rec:ed0-93"),
            change(
                "rec:ed0-93",
                STATYA_93,
                EDITION0_ACT,
                "2013-09-01",
                vec![AmendmentFacetKind::Force],
                Some(NormativeState::InForce),
            ),
        )
        .expect_err("duplicate record id rejected");
    assert!(matches!(err, ThreeCanonLogError::DuplicateRecordId));

    assert_eq!(log.len(), 1, "only the first clean append survived");
}
