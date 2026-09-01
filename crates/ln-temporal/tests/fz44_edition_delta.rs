//! Edition-delta read model for the 44-FZ walk — TDD red suite
//! (M196-bwvrj7 S02 T01; step 2 of the owner-requested temporal model).
//!
//! S01 landed the per-target `CheckoutProjection`; the second honest gap of
//! the fz44 walk is the computed edition delta between two governing dates
//! (R070 log-computable sub-step, D326): a diff of the two S01-style
//! checkouts over the half-open window `(from, to]`. Not a second fold, not
//! a checkout/fold semantics change.
//!
//! The roadmap demo over the combined fz44 walk, 2019-01-01 → 2021-07-01,
//! reports exactly two provisions — statya-93 InForce→Repealed and
//! statya-5 touched-by-law3 — each with record-id evidence of the window
//! (`rec:law3-93c` / `rec:law3-5c` + `act:44-fz:amend-3:2021-03-01`);
//! statya-93-1, admitted ON the from day by закон №2, must not enter the
//! delta (exclusive-from D326: an inclusive-from window would drag
//! `rec:law2-93-1c` in as a phantom third row). R038 guard: the suite goes
//! red if 93-1 leaks into the demo delta OR a force-only diff drops
//! statya-5.
//!
//! RED BY DESIGN: this suite must not compile until T02 lands
//! `edition_delta` / `EditionDelta` / `ProvisionDelta` and the
//! `ThreeCanonLogError::InvertedRange` variant; the unresolved imports
//! below are the failing proof (content-level verify for this task, not a
//! cargo-test verify).
//!
//! Bounded honesty: synthetic identities are not the real corpus; R070
//! (amending-act text provenance) stays open (D179); this is not the
//! crystal compiler, not bitemporal checkout, not interval algebra (D228).
//! No YAML minting (D216/D312). Helpers are duplicated from
//! `fz44_checkout_projection.rs` on purpose (walk/checkout suites stay
//! untouched); the ln-kb-ontology merkle field `checkout_projection` is a
//! name homonym only. Supports R068/R074/R081/R038; it does not validate
//! R070 and does not close D-03.

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    edition_delta, AmendmentFacetKind, C1Candidate, CanonRecordId, ComponentConceptId,
    EditionDelta, EditionOracle, EvidenceClass, NormativeState, ProvisionDelta, ThreeCanonEventLog,
    ThreeCanonLogError, ThreeCanonRecord,
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

/// `(record id, amending act provenance)` pairs of the amendment events.
fn amendment_records(events: &[ThreeCanonRecord]) -> Vec<(String, String)> {
    events
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

/// Combined log exactly as the S01 checkout/walk: the edition-0 oracle plus
/// all seven canon admissions across the three component concepts (R081:
/// one Work namespace `cc:44-fz`, never a minted Work per amendment).
fn combined_log() -> ThreeCanonEventLog {
    let mut combined = ThreeCanonEventLog::empty();

    // Edition-oracle checksum of edition 0, published on enactment day.
    combined
        .append(oracle("orc:ed0", "2013-04-05"))
        .expect("edition oracle");

    // Edition 0: the enacting law puts statya-5/statya-93 into force.
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
        &mut combined,
        "law1-5c",
        STATYA_5,
        LAW1_ACT,
        "2016-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );
    // Закон №2: statya-5 text change again + new statya-93-1 introduced
    // ON the demo's from day (2019-01-01) — the exclusive-from boundary.
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

    combined
}

/// Point the edition delta at a `(from, to]` window of ISO days (the API
/// T02 lands).
fn delta(log: &ThreeCanonEventLog, from_iso: &str, to_iso: &str) -> EditionDelta {
    edition_delta(log, day(from_iso), day(to_iso)).expect("edition delta")
}

fn provision<'a>(delta: &'a EditionDelta, target: &str) -> &'a ProvisionDelta {
    delta
        .provisions()
        .iter()
        .find(|p| p.target().as_str() == target)
        .unwrap_or_else(|| panic!("provision {target} missing"))
}

// ── The demo: the (from, to] window diff — two lines, per provision ─────────

#[test]
fn combined_delta_2019_to_2021_reports_statya_93_repealed_and_statya_5_touched() {
    let combined = combined_log();
    let demo = delta(&combined, "2019-01-01", "2021-07-01");

    assert_eq!(demo.from_day(), day("2019-01-01"));
    assert_eq!(demo.to_day(), day("2021-07-01"));
    assert!(
        !demo.non_claims().is_empty(),
        "the delta carries its non-claims"
    );

    // Exactly two provisions changed in the window, sorted by target string:
    // the repeal line and the touched line — no third row.
    let targets: Vec<&str> = demo
        .provisions()
        .iter()
        .map(|p| p.target().as_str())
        .collect();
    assert_eq!(
        targets,
        vec![STATYA_5, STATYA_93],
        "exactly two provisions, sorted by target.as_str()"
    );

    // statya-93: the only force transition — InForce at `from`, Repealed at
    // `to`, no conflict on either side.
    let statya_93 = provision(&demo, STATYA_93);
    assert_eq!(statya_93.force_from(), NormativeState::InForce);
    assert_eq!(statya_93.force_to(), NormativeState::Repealed);
    assert!(!statya_93.force_conflict_from(), "clean from-side readout");
    assert!(!statya_93.force_conflict_to(), "clean to-side readout");
    assert!(
        !statya_93.events().is_empty(),
        "the repeal carries evidence"
    );

    // statya-5: touched by закон №3 (Text+Force) while its force readout is
    // unchanged InForce→InForce — a force-only diff would drop this line.
    let statya_5 = provision(&demo, STATYA_5);
    assert_eq!(statya_5.force_from(), NormativeState::InForce);
    assert_eq!(statya_5.force_to(), NormativeState::InForce);
    assert!(!statya_5.force_conflict_from());
    assert!(!statya_5.force_conflict_to());
    assert!(!statya_5.events().is_empty(), "the touch carries evidence");
}

#[test]
fn demo_delta_omits_statya_93_1_admitted_on_from_day() {
    // Load-bearing for the window shape: закон №2 admits statya-93-1 with
    // effect ON the from day (2019-01-01). The window is half-open
    // (from, to] — D326 exclusive-from — so that admission is pre-existing
    // state at `from`, not a window event; an inclusive-from window would
    // drag rec:law2-93-1c into the demo delta as a phantom third row.
    let combined = combined_log();
    let demo = delta(&combined, "2019-01-01", "2021-07-01");

    assert!(
        demo.provisions()
            .iter()
            .all(|p| p.target().as_str() != STATYA_93_1),
        "{STATYA_93_1} is admitted on the from day and must not enter the (from, to] delta"
    );
}

#[test]
fn window_events_are_law3_record_ids_not_the_to_chain() {
    // The evidence carried by a delta row is the window, not the full `to`
    // chain: statya-93 carries the law-3 repeal record id with its amending
    // act and does NOT carry the edition-0 admission rec:ed0-93c (window
    // only). statya-5 keeps rec:law3-5c with the same act; its earlier text
    // edits (rec:law1-5c, rec:law2-5c) sit before/on the from boundary.
    let combined = combined_log();
    let demo = delta(&combined, "2019-01-01", "2021-07-01");

    let statya_93 = provision(&demo, STATYA_93);
    let records_93 = amendment_records(statya_93.events());
    assert!(
        records_93.iter().any(|(id, _)| id == "rec:law3-93c"),
        "the law-3 repeal record id is the window evidence"
    );
    let (_, provenance) = records_93
        .iter()
        .find(|(id, _)| id == "rec:law3-93c")
        .expect("law3 repeal record");
    assert_eq!(provenance, LAW3_ACT);
    assert!(
        records_93.iter().all(|(id, _)| id != "rec:ed0-93c"),
        "rec:ed0-93c predates the window: window only, not the to-chain"
    );

    let statya_5 = provision(&demo, STATYA_5);
    let records_5 = amendment_records(statya_5.events());
    assert!(
        records_5
            .iter()
            .any(|(id, act)| id == "rec:law3-5c" && act == LAW3_ACT),
        "statya-5 carries rec:law3-5c with the same amending act"
    );
    assert!(
        records_5.iter().all(|(id, _)| id != "rec:law2-5c"),
        "rec:law2-5c sits on the exclusive from boundary, outside (from, to]"
    );
}

#[test]
fn inverted_from_after_to_returns_inverted_range() {
    // Boundaries are never swapped: from after to is a caller error and
    // fails closed as `ThreeCanonLogError::InvertedRange` — not
    // `OrderingConflict` (that error is about log append order, not the
    // window). The same window in the correct order still reports the
    // two-line demo, so the error path never silently absorbs the window.
    let combined = combined_log();

    let inverted = edition_delta(&combined, day("2021-07-01"), day("2019-01-01"));
    assert_eq!(
        inverted.expect_err("inverted range must be rejected"),
        ThreeCanonLogError::InvertedRange
    );

    let forward = delta(&combined, "2019-01-01", "2021-07-01");
    assert_eq!(
        forward.provisions().len(),
        2,
        "two lines, not an empty delta"
    );
}

#[test]
fn equal_from_and_to_yield_empty_provisions() {
    // Equal dates are a legal degenerate window, not an error: the
    // half-open window (t, t] is empty, so no provision changed and the
    // delta carries zero provisions — never a synthetic or absorbed
    // readout.
    let combined = combined_log();
    let degenerate = delta(&combined, "2021-07-01", "2021-07-01");

    assert_eq!(degenerate.from_day(), day("2021-07-01"));
    assert_eq!(degenerate.to_day(), day("2021-07-01"));
    assert!(
        degenerate.provisions().is_empty(),
        "(t, t] is an empty window"
    );
}
