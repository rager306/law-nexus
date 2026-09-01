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
//! T02 landed `edition_delta` / `EditionDelta` / `ProvisionDelta` and the
//! `ThreeCanonLogError::InvertedRange` variant (the T01 red suite went
//! green). T03 adds the honesty negatives over the same fixture: empty and
//! oracle-only logs yield zero provisions (D304: never a synthetic
//! InForce), the oracle is absent from every window-evidence chain, the
//! introduction window pins the target-exists-only-at-`to` path (Unknown
//! at `from`), a text-only touch without force change keeps its line,
//! the delta compares by value deterministically, the non-claims deny
//! list names bitemporal checkout / crystal compiler / R070 / D-03, every
//! delta target stays inside the one `cc:44-fz` Work namespace (R081),
//! and the Fold 8 aggregate conflict plus the S01 per-provision checkout
//! stay untouched regressions.
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
    checkout_projection_at, edition_delta, fold_three_canon_at, AmendmentFacetKind, C1Candidate,
    CanonRecordId, ComponentConceptId, EditionDelta, EditionOracle, EvidenceClass, NormativeState,
    ProvisionDelta, ThreeCanonEventLog, ThreeCanonLogError, ThreeCanonRecord,
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

// ── Honesty negatives: empty/oracle-only, introduction window, keep rule ────

#[test]
fn empty_or_oracle_only_log_yields_zero_delta_provisions() {
    // D304 honesty over a valid window: a log with no projected canon
    // events checks out to zero provisions, so the delta is zero lines —
    // never a synthetic InForce readout for a target nothing put in force.
    let empty = ThreeCanonEventLog::empty();
    assert_eq!(
        delta(&empty, "2019-01-01", "2021-07-01").provisions().len(),
        0,
        "an empty log deltas to zero provisions"
    );

    // Oracle-only: the edition checksum rides the append-only timeline but
    // is not a canon event (§1c) — the delta still sees zero provisions.
    let mut oracle_only = ThreeCanonEventLog::empty();
    oracle_only
        .append(oracle("orc:ed0", "2013-04-05"))
        .expect("edition oracle");
    assert_eq!(
        delta(&oracle_only, "2019-01-01", "2021-07-01")
            .provisions()
            .len(),
        0,
        "an oracle-only log deltas to zero provisions"
    );
}

#[test]
fn oracle_is_absent_from_every_delta_events() {
    // The combined fixture really carries the edition oracle on the log,
    // yet no window-evidence chain may contain it: EditionOracle records
    // are checksums, not canon events (§1c) — the window is canon only.
    let combined = combined_log();
    assert!(
        combined
            .records()
            .iter()
            .any(|record| matches!(record, ThreeCanonRecord::EditionOracle(_))),
        "the fixture carries the oracle on the log"
    );

    let demo = delta(&combined, "2019-01-01", "2021-07-01");
    assert!(!demo.provisions().is_empty(), "the demo window is nonempty");
    for line in demo.provisions() {
        let events = line.events();
        assert!(
            events
                .iter()
                .all(|record| !matches!(record, ThreeCanonRecord::EditionOracle(_))),
            "oracle leaked into window evidence of {}",
            line.target().as_str()
        );
    }
}

#[test]
fn introduction_window_shows_93_1_unknown_to_in_force_and_statya_5_touched() {
    // The one window that pins the D304 from-side: from 2018-12-31 the
    // law-2 admission sits inside the window, so statya-93-1 exists only at
    // `to`. The from-side readout is Unknown — absence is not InForce. Not
    // in the roadmap demo, but the only pin that the
    // target-exists-only-at-`to` path reads Unknown at `from` instead of a
    // synthetic InForce.
    let combined = combined_log();
    let introduction = delta(&combined, "2018-12-31", "2019-01-01");

    let targets: Vec<&str> = introduction
        .provisions()
        .iter()
        .map(|line| line.target().as_str())
        .collect();
    assert_eq!(
        targets,
        vec![STATYA_5, STATYA_93_1],
        "statya-93 has no window event and stays InForce across this window"
    );

    let statya_93_1 = provision(&introduction, STATYA_93_1);
    assert_eq!(
        statya_93_1.force_from(),
        NormativeState::Unknown,
        "D304: the target exists only at `to`, the from side is Unknown"
    );
    assert!(
        !statya_93_1.force_conflict_from(),
        "absence is not a conflict"
    );
    assert_eq!(statya_93_1.force_to(), NormativeState::InForce);
    assert!(!statya_93_1.force_conflict_to());
    let records_93_1 = amendment_records(statya_93_1.events());
    assert!(
        records_93_1.iter().any(|(id, _)| id == "rec:law2-93-1c"),
        "rec:law2-93-1c is the introduction evidence"
    );

    let statya_5 = provision(&introduction, STATYA_5);
    assert_eq!(statya_5.force_from(), NormativeState::InForce);
    assert_eq!(statya_5.force_to(), NormativeState::InForce);
    let records_5_intro = amendment_records(statya_5.events());
    assert!(
        records_5_intro.iter().any(|(id, _)| id == "rec:law2-5c"),
        "the law-2 text touch keeps statya-5 in this window"
    );

    assert!(
        introduction
            .provisions()
            .iter()
            .all(|line| line.target().as_str() != STATYA_93),
        "{STATYA_93} has no window event here: InForce on both cuts, no line"
    );
}

#[test]
fn text_only_touch_without_force_change_stays_in_delta() {
    // A dedicated small log (not the combined fixture): Force InForce on
    // the target early, then a later text-only amendment inside the window
    // with no Force facet. The line must stay in the delta with
    // force_from == force_to == InForce and nonempty events — a force-only
    // keep rule (keep only when force_from != force_to) would drop it.
    const STATYA_10: &str = "cc:44-fz:statya-10";
    let mut log = ThreeCanonEventLog::empty();
    admit(
        &mut log,
        "ed0-10c",
        STATYA_10,
        EDITION0_ACT,
        "2013-09-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    admit(
        &mut log,
        "law2-10c",
        STATYA_10,
        LAW2_ACT,
        "2019-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );

    let line_delta = delta(&log, "2016-01-01", "2019-06-01");
    let targets: Vec<&str> = line_delta
        .provisions()
        .iter()
        .map(|line| line.target().as_str())
        .collect();
    assert_eq!(targets, vec![STATYA_10], "exactly the touched target");

    let statya_10 = provision(&line_delta, STATYA_10);
    assert_eq!(
        statya_10.force_from(),
        NormativeState::InForce,
        "force-only readout at `from` comes from the early admission"
    );
    assert_eq!(
        statya_10.force_to(),
        NormativeState::InForce,
        "the text-only touch carries no Force facet"
    );
    assert!(!statya_10.force_conflict_from());
    assert!(!statya_10.force_conflict_to());
    assert!(
        !statya_10.events().is_empty(),
        "the touch is window evidence"
    );
    assert_eq!(
        amendment_records(statya_10.events()),
        vec![("rec:law2-10c".to_owned(), LAW2_ACT.to_owned())],
        "the text-only touch is the only window evidence"
    );
}

#[test]
fn delta_is_deterministic_partial_eq() {
    // The same log and the same window compute an equal delta twice: the
    // read model is deterministic (HashMap order is never observable) and
    // EditionDelta compares by value.
    let combined = combined_log();
    let first = delta(&combined, "2019-01-01", "2021-07-01");
    let second = delta(&combined, "2019-01-01", "2021-07-01");
    assert_eq!(first, second, "same log and window, equal delta");

    let introduction = delta(&combined, "2018-12-31", "2019-01-01");
    assert_ne!(
        first, introduction,
        "a different window is a different delta"
    );
}

#[test]
fn non_claims_are_nonempty_and_deny_bitemporal_compiler_and_r070() {
    // Match the T02 statics: the delta carries its honesty non-claims —
    // not bitemporal checkout, not the crystal compiler — and keeps R070
    // and D-03 named-open instead of claiming them closed.
    let combined = combined_log();
    let demo = delta(&combined, "2019-01-01", "2021-07-01");
    let joined = demo.non_claims().join(" | ");
    assert!(
        !demo.non_claims().is_empty(),
        "the delta carries its non-claims"
    );
    assert!(
        joined.contains("not bitemporal"),
        "the deny list names the bitemporal-checkout non-claim"
    );
    assert!(
        joined.contains("crystal compiler") || joined.contains("MicroOperation"),
        "the deny list names the crystal-compiler non-claim"
    );
    assert!(
        joined.contains("R070") || joined.contains("D-03"),
        "R070 / D-03 stay named-open in the non-claims"
    );
}

#[test]
fn r081_one_work_namespace_on_delta_targets() {
    // Every delta line targets the one stable Work namespace cc:44-fz
    // (R081): an amendment never mints a new Work, so no window line —
    // demo or introduction — may point outside cc:44-fz.
    let combined = combined_log();
    for window in [
        delta(&combined, "2019-01-01", "2021-07-01"),
        delta(&combined, "2018-12-31", "2019-01-01"),
    ] {
        assert!(!window.provisions().is_empty());
        for line in window.provisions() {
            let target = line.target().as_str();
            assert!(
                target.starts_with(FZ44),
                "{target} is outside the one cc:44-fz Work namespace"
            );
        }
    }
}

#[test]
fn combined_fold_at_2022_still_reports_false_aggregate_conflict() {
    // Regression pin on the log-wide fold: the delta work must not "fix"
    // Fold 8. At 2022 the combined aggregate still honestly reports the
    // same-day divergent force across different concepts (statya-5 InForce
    // vs statya-93 Repealed) as Unknown + force_conflict.
    let combined = combined_log();
    let fold_2022 = fold_three_canon_at(&combined, day("2022-01-01")).expect("fold");
    assert!(
        fold_2022.force_conflict(),
        "Fold 8 stays honestly conflicted"
    );
    assert_eq!(fold_2022.force_status(), NormativeState::Unknown);
}

#[test]
fn checkout_at_2022_still_reports_per_provision_force() {
    // S01 regression pin: the point per-target checkout at 2022 still reads
    // per-provision force — statya-5 InForce, statya-93 Repealed,
    // statya-93-1 InForce — conflict-free. The projection structurally
    // carries no aggregate force readout at the root (the only force
    // surface is per-provision); the delta work must not change that
    // surface and must not "fix" Fold 8 through the checkout either.
    let combined = combined_log();
    let at_2022 = checkout_projection_at(&combined, day("2022-01-01")).expect("checkout");
    assert_eq!(at_2022.as_of_day(), day("2022-01-01"));
    assert_eq!(at_2022.provisions().len(), 3, "three component concepts");

    let expected = [
        (STATYA_5, NormativeState::InForce),
        (STATYA_93, NormativeState::Repealed),
        (STATYA_93_1, NormativeState::InForce),
    ];
    for (target, expected_status) in expected {
        let line = at_2022
            .provisions()
            .iter()
            .find(|line| line.target().as_str() == target)
            .unwrap_or_else(|| panic!("{target} missing"));
        assert_eq!(line.force_status(), expected_status, "{target}");
        assert!(!line.force_conflict(), "{target} checks out conflict-free");
    }
    let force_of = |target: &str| {
        at_2022
            .provisions()
            .iter()
            .find(|line| line.target().as_str() == target)
            .expect("provision")
            .force_status()
    };
    assert_ne!(
        force_of(STATYA_5),
        force_of(STATYA_93),
        "divergent per-provision readouts coexist with no aggregate root force"
    );
}
