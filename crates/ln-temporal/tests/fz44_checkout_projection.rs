//! Per-provision checkout projection for the 44-FZ walk — TDD red suite
//! (M196-bwvrj7 S01 T01; step 2 of the owner-requested temporal model).
//!
//! Fold 8 of `fz44_edition_walk.rs` proved the honest log-wide lie: folding
//! the combined 44-FZ log at 2022-01-01 yields `Unknown` + `force_conflict`,
//! because same-day force outcomes diverge across different component
//! concepts (statya-5 InForce vs statya-93 Repealed). This suite pins the
//! per-target correction as tests against the read model T02 lands in
//! `domain.rs`:
//!
//! - `checkout_projection_at(&ThreeCanonEventLog, as_of_day)` returns a
//!   `CheckoutProjection` with one `ProvisionCheckout` per component
//!   concept: per-provision force readout, no false aggregate mix;
//! - a true same-target same-day conflict stays `Unknown` + `force_conflict`
//!   and does not infect neighboring concepts (R038);
//! - the log-wide fold contract is asserted unchanged in
//!   `combined_fold_at_2022_still_reports_false_aggregate_conflict` —
//!   Fold 8 is NOT painted green by this slice.
//!
//! RED BY DESIGN: this suite must not compile until T02 lands
//! `checkout_projection_at` / `CheckoutProjection` / `ProvisionCheckout`;
//! the unresolved imports below are the failing proof (content-level verify
//! for this task, not a cargo-test verify).
//!
//! Bounded honesty: synthetic identities are not the real corpus; R070
//! (amending-act text provenance) stays open (D179); this is a bounded D-03
//! grouping step, not the crystal compiler, not bitemporal checkout, not
//! interval algebra (D228). No YAML minting (D216/D312). Unrelated to the
//! ln-kb-ontology merkle field `checkout_projection` (name homonym only).
//! Supports R068/R074 and the R081 shape; it does not validate R070.

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    checkout_projection_at, fold_three_canon_at, AmendmentFacetKind, C1Candidate, CanonRecordId,
    CheckoutProjection, ComponentConceptId, EditionOracle, EvidenceClass, NormativeState,
    ProvisionCheckout, ThreeCanonEventLog, ThreeCanonLogError, ThreeCanonRecord,
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

/// Combined log exactly as the walk: the edition-0 oracle plus all seven
/// canon admissions across the three component concepts (R081: one Work
/// namespace `cc:44-fz`, never a minted Work per amendment).
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
    // Закон №2: statya-5 text change again + new statya-93-1 introduced.
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

/// Point per-target checkout at an ISO day (the API T02 lands).
fn checkout(log: &ThreeCanonEventLog, iso_day: &str) -> CheckoutProjection {
    checkout_projection_at(log, day(iso_day)).expect("checkout projection")
}

fn provision<'a>(checkout: &'a CheckoutProjection, target: &str) -> &'a ProvisionCheckout {
    checkout
        .provisions()
        .iter()
        .find(|p| p.target().as_str() == target)
        .unwrap_or_else(|| panic!("provision {target} missing"))
}

// ── The demo: per-provision force without the false aggregate mix ───────────

#[test]
fn combined_checkout_at_2022_reports_per_provision_force_without_false_aggregate() {
    let combined = combined_log();
    let at_2022 = checkout(&combined, "2022-01-01");

    assert_eq!(at_2022.as_of_day(), day("2022-01-01"));
    assert_eq!(at_2022.provisions().len(), 3, "three component concepts");
    assert!(
        !at_2022.non_claims().is_empty(),
        "the checkout carries its non-claims"
    );

    // Per-provision force at 2022-01-01: each provision reports its own
    // concrete status and none inherits the cross-concept `Unknown` mix.
    // The root carries no aggregate force readout at all, so the log-wide
    // mix (statya-5 InForce vs statya-93 Repealed) cannot reappear there.
    for (target, expected) in [
        (STATYA_5, NormativeState::InForce),
        (STATYA_93, NormativeState::Repealed),
        (STATYA_93_1, NormativeState::InForce),
    ] {
        let provision = provision(&at_2022, target);
        assert_eq!(provision.force_status(), expected, "{target}");
        assert!(!provision.force_conflict(), "{target}");
        assert_ne!(
            provision.force_status(),
            NormativeState::Unknown,
            "{target} must not carry the aggregate mix"
        );
        assert!(!provision.events().is_empty(), "{target} has its chain");
    }
}

#[test]
fn combined_fold_at_2022_still_reports_false_aggregate_conflict() {
    // Fold 8 honesty guard: the per-provision correction must not quietly
    // weaken the log-wide fold, which keeps refusing to mix same-day
    // divergent force outcomes across different component concepts.
    let combined = combined_log();
    let fold_2022 = fold_three_canon_at(&combined, day("2022-01-01")).expect("fold");
    assert!(
        fold_2022.force_conflict(),
        "aggregate conflict stays visible"
    );
    assert_eq!(fold_2022.force_status(), NormativeState::Unknown);
    assert_eq!(
        fold_2022.events().len(),
        7,
        "canon events only, oracle excluded"
    );
}

#[test]
fn true_same_target_same_day_conflict_is_unknown_and_does_not_infect_neighbors() {
    // R038 true conflict: two force-bearing records on ONE component concept
    // on the same day fold fail-closed to `Unknown` + conflict — while the
    // neighbor concept on the same day keeps its clean InForce readout.
    let mut log = ThreeCanonEventLog::empty();
    admit(
        &mut log,
        "dup-93a",
        STATYA_93,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Repealed),
    );
    admit(
        &mut log,
        "dup-93b",
        STATYA_93,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    admit(
        &mut log,
        "nbr-5",
        STATYA_5,
        LAW3_ACT,
        "2021-07-01",
        vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );

    let at_2021 = checkout(&log, "2021-07-01");
    assert_eq!(
        at_2021.provisions().len(),
        2,
        "only the two touched concepts"
    );

    let statya_93 = provision(&at_2021, STATYA_93);
    assert_eq!(statya_93.force_status(), NormativeState::Unknown);
    assert!(statya_93.force_conflict(), "true conflict is kept honest");

    let statya_5 = provision(&at_2021, STATYA_5);
    assert_eq!(statya_5.force_status(), NormativeState::InForce);
    assert!(
        !statya_5.force_conflict(),
        "the true conflict stays isolated"
    );
}

#[test]
fn law3_statya_93_carries_record_id_and_amending_act_provenance() {
    // The per-provision chain keeps per-record ids and per-act provenance:
    // statya-93 carries both the edition-0 admission and the law-3 repeal
    // with its amending act; statya-5 keeps its edition-0 root record.
    let combined = combined_log();
    let at_2022 = checkout(&combined, "2022-01-01");

    let statya_93 = provision(&at_2022, STATYA_93);
    let records_93 = amendment_records(statya_93.events());
    assert_eq!(records_93.len(), 2, "ed0 + law3 chain");
    assert!(records_93.iter().any(|(id, _)| id == "rec:law3-93c"));
    let (_, provenance) = records_93
        .iter()
        .find(|(id, _)| id == "rec:law3-93c")
        .expect("law3 repeal record");
    assert_eq!(provenance, LAW3_ACT);

    let statya_5 = provision(&at_2022, STATYA_5);
    assert!(amendment_records(statya_5.events())
        .iter()
        .any(|(id, _)| id == "rec:ed0-5c"));
}

// ── T03 honesty negatives: a green demo cannot hide D304 or oracle leakage ──

#[test]
fn checkout_before_edition0_has_zero_provisions_not_in_force() {
    // Before edition 0 is effective (2013-09-01) no provision exists: the
    // checkout projects zero provisions (the oracle is not a canon event)
    // and never synthesizes an InForce readout from absence (D304).
    let combined = combined_log();
    let before = checkout(&combined, "2013-08-31");

    assert_eq!(before.as_of_day(), day("2013-08-31"));
    assert!(
        before.provisions().is_empty(),
        "no canon event is effective before edition 0"
    );
    for target in [STATYA_5, STATYA_93, STATYA_93_1] {
        assert!(
            before
                .provisions()
                .iter()
                .all(|p| p.target().as_str() != target),
            "{target} must be absent before edition 0"
        );
    }
}

#[test]
fn checkout_at_2019_06_01_introduces_statya_93_1_and_keeps_93_in_force() {
    // Mid-walk cut: after закон №2 (2019-01-01) but before закон №3
    // (2021-07-01) all three provisions read InForce with clean per-target
    // readouts — the repeal has not happened yet, so no conflict, and the
    // 2022 Repealed on statya-93 must not leak backwards in time.
    let combined = combined_log();
    let at_2019 = checkout(&combined, "2019-06-01");

    assert_eq!(at_2019.provisions().len(), 3);
    for (target, expected) in [
        (STATYA_93_1, NormativeState::InForce),
        (STATYA_93, NormativeState::InForce),
        (STATYA_5, NormativeState::InForce),
    ] {
        let provision = provision(&at_2019, target);
        assert_eq!(provision.force_status(), expected, "{target}");
        assert!(!provision.force_conflict(), "{target}");
    }
}

#[test]
fn text_only_provision_is_unknown_without_conflict() {
    // A provision whose only projected events are Text-facet amendments
    // (no Force facet, no effect payload) stays honestly Unknown: text
    // edits never drive a force readout, and "no force evidence" is not
    // InForce (the D304 shape at the provision level).
    let mut log = ThreeCanonEventLog::empty();
    admit(
        &mut log,
        "law1-16t",
        "cc:44-fz:statya-16",
        LAW1_ACT,
        "2016-01-01",
        vec![AmendmentFacetKind::Text],
        None,
    );

    let at_2016 = checkout(&log, "2016-06-01");
    let statya_16 = provision(&at_2016, "cc:44-fz:statya-16");
    assert_eq!(statya_16.force_status(), NormativeState::Unknown);
    assert!(!statya_16.force_conflict());
    assert_eq!(
        statya_16.events().len(),
        1,
        "the text-only chain is kept, it just never drives force"
    );
}

#[test]
fn oracle_is_held_on_log_but_absent_from_every_provision_events() {
    // The edition oracle stays a log-level checksum (§1c): the combined
    // log holds it, but it never leaks into any provision's canon chain.
    let combined = combined_log();
    assert!(
        combined
            .records()
            .iter()
            .any(|record| matches!(record, ThreeCanonRecord::EditionOracle(_))),
        "the oracle is held on the log"
    );

    let at_2022 = checkout(&combined, "2022-01-01");
    assert!(!at_2022.provisions().is_empty());
    for provision in at_2022.provisions() {
        assert!(
            provision
                .events()
                .iter()
                .all(|record| !matches!(record, ThreeCanonRecord::EditionOracle(_))),
            "oracle never becomes a provision canon event"
        );
    }
}

#[test]
fn empty_or_oracle_only_log_yields_zero_provisions() {
    // D304 at the checkout level: an empty log and an oracle-only log both
    // project zero provisions — absence of canon events never becomes a
    // synthetic InForce provision, and the oracle is not a canon event.
    let empty = ThreeCanonEventLog::empty();
    assert!(checkout(&empty, "2022-01-01").provisions().is_empty());

    let mut oracle_only = ThreeCanonEventLog::empty();
    oracle_only
        .append(oracle("orc:solo", "2013-04-05"))
        .expect("edition oracle");
    assert!(checkout(&oracle_only, "2022-01-01").provisions().is_empty());
}

#[test]
fn checkout_is_deterministic_partial_eq() {
    // Deterministic read model: the same log and day produce an equal
    // projection (provisions are sorted by target string internally), and
    // a different as-of day is a different projection.
    let combined = combined_log();
    let first = checkout(&combined, "2022-01-01");
    let second = checkout(&combined, "2022-01-01");
    assert_eq!(first, second);
    assert_eq!(first.provisions().len(), second.provisions().len());
    assert_ne!(first, checkout(&combined, "2019-06-01"));
}

#[test]
fn unordered_log_returns_ordering_conflict() {
    // Defense-in-depth honesty: `checkout_projection_at` consumes the same
    // ordered-loop contract as `fold_three_canon_at` and never sorts. The
    // public API cannot even represent an unordered log — `append` itself
    // fails closed with `OrderingConflict` before any projection could see
    // one. Privacy is not weakened to force the Err path: the same
    // in-function ordered loop guards `checkout_projection_at` directly if
    // a raw constructor ever appears.
    let mut log = ThreeCanonEventLog::empty();
    admit(
        &mut log,
        "ed0-93",
        STATYA_93,
        EDITION0_ACT,
        "2013-09-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );

    // An earlier-than-last day cannot enter the ordered log...
    let unordered_attempt = log.append_c1_candidate(
        rid("rec:early-93"),
        change(
            "early-93",
            STATYA_93,
            LAW1_ACT,
            "2013-08-31",
            vec![AmendmentFacetKind::Force],
            Some(NormativeState::Repealed),
        ),
    );
    assert!(
        matches!(unordered_attempt, Err(ThreeCanonLogError::OrderingConflict)),
        "out-of-order admission is rejected"
    );

    // ...and the rejected record was not stored: the checkout still sees
    // exactly one in-order event and keeps the clean readout.
    let at_2022 = checkout(&log, "2022-01-01");
    assert_eq!(at_2022.provisions().len(), 1);
    let statya_93 = provision(&at_2022, STATYA_93);
    assert_eq!(statya_93.events().len(), 1, "rejection left no residue");
    assert_eq!(statya_93.force_status(), NormativeState::InForce);
    assert!(!statya_93.force_conflict());
}

#[test]
fn non_claims_are_nonempty_and_deny_bitemporal_compiler_and_r070() {
    // The checkout's honesty manifest (T02 statics) must survive any
    // future refactor: it names what the read model is not — not bitemporal
    // checkout, not the crystal compiler, provenance/bounded-step open.
    let combined = combined_log();
    let at_2022 = checkout(&combined, "2022-01-01");

    let claims = at_2022.non_claims();
    assert!(!claims.is_empty());
    let joined = claims.join("\n");
    assert!(
        joined.contains("not bitemporal checkout"),
        "denies the bitemporal-checkout reading"
    );
    assert!(
        joined.contains("crystal compiler"),
        "denies the crystal-compiler claim"
    );
    assert!(
        joined.contains("R070") || joined.contains("D-03"),
        "keeps the provenance / bounded-step honesty visible"
    );
}

#[test]
fn r081_one_work_namespace_on_provision_targets() {
    // R081 shape: every projected provision stays inside the single 44-FZ
    // Work namespace; amendments never mint a new Work per change.
    let combined = combined_log();
    let at_2022 = checkout(&combined, "2022-01-01");
    assert!(!at_2022.provisions().is_empty());
    for provision in at_2022.provisions() {
        assert!(
            provision.target().as_str().starts_with(FZ44),
            "{} leaves the {FZ44} namespace",
            provision.target().as_str()
        );
    }
}
