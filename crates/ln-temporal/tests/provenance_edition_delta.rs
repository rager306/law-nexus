//! Provenance-gated edition delta — TDD red suite (M201-w8ljqx S02 T01;
//! D409 caller-supplied admission + D410 raw commencement storage).
//!
//! S01 landed the standalone `EditionProvenanceEnvelope` constructor. The
//! second honest gap (R070 log-computable sub-step) is the `edition_delta`
//! seam: today the delta returns `ProvisionDelta` lines with force readouts
//! and window events but **no provenance envelope**, so a caller can receive
//! a consolidated edition whose provenance is incomplete (violates INV-10
//! and the S02 After-this).
//!
//! D409 contract pinned here (implemented by T02):
//! - `edition_delta` takes a fourth caller-supplied `&[ProvenanceAdmission]`
//!   argument and returns `Result<EditionDelta, EditionDeltaError>`.
//! - Every kept provision line carries a **full** envelope under
//!   `ProvisionDelta::provenance()`: amending acts set-extracted from the
//!   window `AmendmentEvent`s (two records of one act → one act), the target
//!   itself as the affected provision, unique-sorted window record ids as
//!   delta evidence, and the admission's commencement + transitional slots.
//! - Any kept line that cannot build a complete envelope fails the **whole
//!   call** as a typed `EditionDeltaError` — never a partial edition:
//!   `MissingAdmission { target }` when the caller did not admit a kept
//!   target, `Unresolved { target, cause }` when the admission or window
//!   evidence cannot complete the packet (editorial-hint commencement is
//!   `UnprovenCommencement`; an assertion-or-effect-only window is
//!   `MissingAmendingAct` — no act is ever synthesized).
//! - D410 slot discipline: `ProvenanceAdmission` stores the raw commencement
//!   fields (effect day, evidence class, rule ref string); the
//!   `CommencementEvidence::try_new` refusal must surface **at the seam**
//!   (`Unresolved`), so an `EditorialHint` admission never fails at
//!   admission construction — and an editorial-hint *class on a window
//!   event* is data, never commencement, and must not taint the packet.
//! - D326 window shape is untouched: exclusive-from inclusive-to, inverted
//!   range is `Window(InvertedRange)` and is checked **before** the
//!   admission gate; keep-rule unchanged. Vacuous windows — empty log,
//!   `(t, t]`, oracle-only — stay `Ok` with zero provisions and need no
//!   admissions (no edition is claimed, so nothing is unresolved).
//! - `EDITION_DELTA_NON_CLAIMS` gains one gated-envelope line naming R070
//!   open; the existing non-claims survive unchanged.
//!
//! T01 is red-first: until T02 lands `ProvenanceAdmission`,
//! `EditionDeltaError`, the new `edition_delta` arity and the
//! `ProvisionDelta::provenance` getter, this suite fails **at compile time**.
//! That is the expected red state, not a defect.
//!
//! Bounded honesty: synthetic identities are not the real corpus; R070
//! (amending-act text provenance) stays open (D179/D289/D308); this is not
//! the crystal compiler, not bitemporal checkout, not interval algebra
//! (D228); no YAML minting (D216/D312); no ActivationTrigger and no
//! TransitionalResolver (D252 / ADR-0021). Helpers are duplicated from
//! `fz44_edition_delta.rs` on purpose (walk/checkout suites stay untouched).

use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::domain::{
    edition_delta, AmendingActId, AmendmentFacetKind, AssertionOrEffect, AssertionOrEffectPayload,
    C1Candidate, CanonRecordId, ComponentConceptId, EditionDelta, EditionOracle, EvidenceClass,
    NormativeState, ProvisionDelta, ThreeCanonEventLog, ThreeCanonLogError, ThreeCanonRecord,
};
use ln_temporal::provenance::{
    EditionDeltaError, ProvenanceAdmission, ProvenanceConstructionError, TransitionalEvidence,
};

// One stable Work namespace (R081) shared with the fz44 walk suites.
const STATYA_5: &str = "cc:44-fz:statya-5";
const STATYA_93: &str = "cc:44-fz:statya-93";
const STATYA_93_1: &str = "cc:44-fz:statya-93-1";

// Edition 0: the enacting law (in force 2013-09-01, before every window).
const EDITION0_ACT: &str = "act:44-fz:2013-04-05:n44";
// Two amending laws (условные номера для симуляции).
const LAW2_ACT: &str = "act:44-fz:amend-2:2018-12-25";
const LAW3_ACT: &str = "act:44-fz:amend-3:2021-03-01";

// The demo window (from, to]: 2019-01-01 exclusive, 2021-07-01 inclusive.
const FROM_ISO: &str = "2019-01-01";
const TO_ISO: &str = "2021-07-01";
// Law 3 governing day, inside the window.
const LAW3_ISO: &str = "2021-03-01";

fn rid(id: &str) -> CanonRecordId {
    CanonRecordId::parse(id).expect("record id")
}

fn cc(id: &str) -> ComponentConceptId {
    ComponentConceptId::parse(id).expect("component concept")
}

fn day(iso_day: &str) -> i64 {
    legal_act_effect_day_to_ordinal(iso_day).expect("calendar day")
}

/// D409 admission: raw commencement fields + transitional slot per target
/// (D410 — no `CommencementEvidence` here, so the editorial-hint refusal
/// surfaces at the `edition_delta` seam, not at admission construction).
fn admission_with_class(
    target: &str,
    iso_day: &str,
    evidence_class: EvidenceClass,
    rule_ref: &str,
    transitional: TransitionalEvidence,
) -> ProvenanceAdmission {
    ProvenanceAdmission::try_new(
        cc(target),
        day(iso_day),
        evidence_class,
        rule_ref,
        transitional,
    )
    .expect("provenance admission")
}

/// Legislative admission (the common demo shape).
fn admission(
    target: &str,
    iso_day: &str,
    rule_ref: &str,
    transitional: TransitionalEvidence,
) -> ProvenanceAdmission {
    admission_with_class(
        target,
        iso_day,
        EvidenceClass::Legislative,
        rule_ref,
        transitional,
    )
}

/// Admit one change event into one log (fail-closed path of the C1 overlay).
#[allow(clippy::too_many_arguments)]
fn admit_with_evidence(
    log: &mut ThreeCanonEventLog,
    record: &str,
    target: &str,
    act_raw: &str,
    iso_day: &str,
    evidence: EvidenceClass,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) {
    log.append_c1_candidate(
        rid(&format!("rec:{record}")),
        C1Candidate::LegislativeAmendment {
            target: cc(target),
            effect_day: day(iso_day),
            amending_act_raw: act_raw.to_owned(),
            evidence,
            facets,
            force_transition: force,
        },
    )
    .expect("admission");
}

/// Legislative amendment event (default evidence class).
#[allow(clippy::too_many_arguments)]
fn admit(
    log: &mut ThreeCanonEventLog,
    record: &str,
    target: &str,
    act_raw: &str,
    iso_day: &str,
    facets: Vec<AmendmentFacetKind>,
    force: Option<NormativeState>,
) {
    admit_with_evidence(
        log,
        record,
        target,
        act_raw,
        iso_day,
        EvidenceClass::Legislative,
        facets,
        force,
    );
}

/// Edition-oracle record: a text checksum of an edition, not a canon event.
fn oracle(target: &str, record: &str, iso_day: &str) -> ThreeCanonRecord {
    ThreeCanonRecord::EditionOracle(
        EditionOracle::try_new(
            rid(&format!("rec:{record}")),
            cc(target),
            day(iso_day),
            "sha256:synthetic-edition-digest",
        )
        .expect("edition oracle"),
    )
}

/// Assertion-or-effect canon record: an effect claim with **no amending act**.
fn assertion_effect(record: &str, target: &str, iso_day: &str) -> ThreeCanonRecord {
    ThreeCanonRecord::AssertionOrEffect(
        AssertionOrEffect::try_new(
            rid(&format!("rec:{record}")),
            cc(target),
            day(iso_day),
            EvidenceClass::Legislative,
            AssertionOrEffectPayload::Effect(NormativeState::InForce),
        )
        .expect("assertion-or-effect"),
    )
}

/// Demo log: edition 0 before the window, the exclusive-from pin exactly on
/// `from` (statya-93-1), and the law-3 window events (two records for
/// statya-93 off ONE act, one text-only touch for statya-5), plus one
/// edition oracle inside the window.
///
/// `window_evidence` parameterizes the evidence class of the law-3 events so
/// the D410 slot-discipline test can carry editorial-hint *event* classes
/// without touching the admission slot.
fn demo_log_with_window_evidence(window_evidence: EvidenceClass) -> ThreeCanonEventLog {
    let mut log = ThreeCanonEventLog::empty();
    // Edition 0: enacting law, in force well before the window.
    admit(
        &mut log,
        "ed0-5c",
        STATYA_5,
        EDITION0_ACT,
        "2013-09-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    admit(
        &mut log,
        "ed0-93c",
        STATYA_93,
        EDITION0_ACT,
        "2013-09-01",
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    // statya-93-1 admitted exactly ON the from day: outside the (from, to]
    // window (exclusive-from, D326) — it must never become a kept line and
    // must never demand an admission.
    admit(
        &mut log,
        "law2-93-1c",
        STATYA_93_1,
        LAW2_ACT,
        FROM_ISO,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::InForce),
    );
    // Law 3 window events. Two statya-93 records share ONE amending act:
    // set extraction must yield a single act, not a duplicate-act refusal.
    admit_with_evidence(
        &mut log,
        "law3-93c",
        STATYA_93,
        LAW3_ACT,
        LAW3_ISO,
        window_evidence,
        vec![AmendmentFacetKind::Text],
        None,
    );
    admit_with_evidence(
        &mut log,
        "law3-93f",
        STATYA_93,
        LAW3_ACT,
        LAW3_ISO,
        window_evidence,
        vec![AmendmentFacetKind::Force],
        Some(NormativeState::Repealed),
    );
    admit_with_evidence(
        &mut log,
        "law3-5c",
        STATYA_5,
        LAW3_ACT,
        LAW3_ISO,
        window_evidence,
        vec![AmendmentFacetKind::Text],
        None,
    );
    // Edition oracle inside the window: a checksum is not canon evidence
    // (ADR-0017 §1c) and must never appear in any delta_evidence chain.
    log.append(oracle(STATYA_93, "oracle-93", "2021-06-01"))
        .expect("oracle append");
    log
}

fn demo_log() -> ThreeCanonEventLog {
    demo_log_with_window_evidence(EvidenceClass::Legislative)
}

/// Fully admitted demo packet: one admission per kept target.
fn demo_admissions() -> [ProvenanceAdmission; 2] {
    [
        admission(
            STATYA_5,
            LAW3_ISO,
            "rec:commencement:law3-5",
            TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
        ),
        admission(
            STATYA_93,
            LAW3_ISO,
            "rec:commencement:law3-93",
            TransitionalEvidence::try_declared("rec:transitional:law3-93").expect("declared"),
        ),
    ]
}

fn provision<'a>(delta: &'a EditionDelta, target: &str) -> &'a ProvisionDelta {
    delta
        .provisions()
        .iter()
        .find(|row| row.target().as_str() == target)
        .expect("kept provision row")
}

/// Happy path: two kept lines, both carrying a FULL envelope.
#[test]
fn two_line_window_with_legislative_admissions_carries_full_envelope() {
    let log = demo_log();
    let from = day(FROM_ISO);
    let to = day(TO_ISO);
    let delta =
        edition_delta(&log, from, to, &demo_admissions()).expect("fully admitted edition delta");

    assert_eq!(delta.from_day(), from);
    assert_eq!(delta.to_day(), to);

    // D326 exclusive-from: statya-93-1 lands exactly on `from`, stays out of
    // the window, creates no kept line, and needs no admission.
    let targets: Vec<&str> = delta
        .provisions()
        .iter()
        .map(|row| row.target().as_str())
        .collect();
    assert_eq!(targets, [STATYA_5, STATYA_93]);

    let row_93 = provision(&delta, STATYA_93);
    assert_eq!(row_93.force_from(), NormativeState::InForce);
    assert_eq!(row_93.force_to(), NormativeState::Repealed);
    let envelope_93 = row_93.provenance();
    // Set extraction: two window records of ONE act → exactly one act.
    let acts: Vec<&str> = envelope_93
        .amending_acts()
        .iter()
        .map(AmendingActId::as_str)
        .collect();
    assert_eq!(acts, [LAW3_ACT]);
    let affected: Vec<&str> = envelope_93
        .affected_provisions()
        .iter()
        .map(ComponentConceptId::as_str)
        .collect();
    assert_eq!(affected, [STATYA_93]);
    // Window record ids only; the oracle checksum never becomes evidence.
    let evidence: Vec<&str> = envelope_93
        .delta_evidence()
        .iter()
        .map(CanonRecordId::as_str)
        .collect();
    assert_eq!(evidence, ["rec:law3-93c", "rec:law3-93f"]);
    // Commencement and transitional slots come from the admission verbatim.
    assert_eq!(envelope_93.commencement().effect_day(), day(LAW3_ISO));
    assert_eq!(
        envelope_93.commencement().evidence_class(),
        EvidenceClass::Legislative
    );
    assert_eq!(
        envelope_93.commencement().rule_ref().as_str(),
        "rec:commencement:law3-93"
    );
    assert_eq!(
        envelope_93.transitional(),
        &TransitionalEvidence::try_declared("rec:transitional:law3-93").expect("declared")
    );

    let row_5 = provision(&delta, STATYA_5);
    assert_eq!(row_5.force_from(), NormativeState::InForce);
    assert_eq!(row_5.force_to(), NormativeState::InForce); // kept via window events
    let envelope_5 = row_5.provenance();
    let acts_5: Vec<&str> = envelope_5
        .amending_acts()
        .iter()
        .map(AmendingActId::as_str)
        .collect();
    assert_eq!(acts_5, [LAW3_ACT]);
    let affected_5: Vec<&str> = envelope_5
        .affected_provisions()
        .iter()
        .map(ComponentConceptId::as_str)
        .collect();
    assert_eq!(affected_5, [STATYA_5]);
    let evidence_5: Vec<&str> = envelope_5
        .delta_evidence()
        .iter()
        .map(CanonRecordId::as_str)
        .collect();
    assert_eq!(evidence_5, ["rec:law3-5c"]);
    // ExplicitlyAbsent is the admission's affirmative choice, never a default.
    assert_eq!(
        envelope_5.transitional(),
        &TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification")
    );

    // Deterministic read model: the same window computes an equal delta.
    assert_eq!(
        delta,
        edition_delta(&log, from, to, &demo_admissions()).expect("deterministic repeat")
    );
}

/// Whole-edition refusal: one kept target without an admission fails the
/// entire call — the caller never receives a partial edition.
#[test]
fn missing_admission_on_kept_target_refuses_whole_edition() {
    let log = demo_log();
    let from = day(FROM_ISO);
    let to = day(TO_ISO);

    let only_statya_5 = [admission(
        STATYA_5,
        LAW3_ISO,
        "rec:commencement:law3-5",
        TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
    )];
    assert_eq!(
        edition_delta(&log, from, to, &only_statya_5),
        Err(EditionDeltaError::MissingAdmission {
            target: cc(STATYA_93),
        })
    );

    // Order-independent: the gate reads the keep-set, not the admission order.
    let only_statya_93 = [admission(
        STATYA_93,
        LAW3_ISO,
        "rec:commencement:law3-93",
        TransitionalEvidence::try_declared("rec:transitional:law3-93").expect("declared"),
    )];
    assert_eq!(
        edition_delta(&log, from, to, &only_statya_93),
        Err(EditionDeltaError::MissingAdmission {
            target: cc(STATYA_5),
        })
    );

    // Empty admissions on a nonempty keep-set: the first kept row in the
    // deterministic (target-sorted) order is refused; no partial Ok.
    assert_eq!(
        edition_delta(&log, from, to, &[]),
        Err(EditionDeltaError::MissingAdmission {
            target: cc(STATYA_5),
        })
    );
}

/// Editorial-hint commencement is unresolved provenance: the refusal is
/// typed `Unresolved` carrying the S01 `UnprovenCommencement` cause, and —
/// per D410 slot discipline — an editorial-hint class on a *window event*
/// is data that never taints a legislative admission.
#[test]
fn editorial_hint_commencement_is_unresolved_unproven() {
    let log = demo_log();
    let from = day(FROM_ISO);
    let to = day(TO_ISO);

    let hint_93 = admission_with_class(
        STATYA_93,
        LAW3_ISO,
        EvidenceClass::EditorialHint,
        "rec:commencement:hint-93",
        TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
    );
    let legislative_5 = admission(
        STATYA_5,
        LAW3_ISO,
        "rec:commencement:law3-5",
        TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
    );
    assert_eq!(
        edition_delta(&log, from, to, &[legislative_5, hint_93]),
        Err(EditionDeltaError::Unresolved {
            target: cc(STATYA_93),
            cause: ProvenanceConstructionError::UnprovenCommencement,
        })
    );

    // Slot discipline (D410): the evidence class recorded on the window
    // AmendmentEvent is event data, not commencement — with a legislative
    // admission the same window succeeds and stores the admission's class
    // without upgrading anything.
    let hint_window_log = demo_log_with_window_evidence(EvidenceClass::EditorialHint);
    let delta = edition_delta(&hint_window_log, from, to, &demo_admissions())
        .expect("event evidence class is not the commencement slot");
    assert_eq!(
        provision(&delta, STATYA_93)
            .provenance()
            .commencement()
            .evidence_class(),
        EvidenceClass::Legislative
    );
}

/// Vacuous windows claim no edition: empty log, `(t, t]` and oracle-only
/// windows all stay `Ok` with zero provisions — no admissions demanded,
/// no synthetic force, no unresolved refusal (D304/D326).
#[test]
fn empty_and_equal_window_and_oracle_only_are_ok_zero_without_admissions() {
    // Empty log.
    let empty = ThreeCanonEventLog::empty();
    let delta = edition_delta(&empty, day(FROM_ISO), day(TO_ISO), &[]).expect("empty log");
    assert!(delta.provisions().is_empty());

    // Equal boundaries: (t, t] is empty by construction, even on a rich log.
    let log = demo_log();
    let t = day(TO_ISO);
    let delta = edition_delta(&log, t, t, &[]).expect("equal boundaries");
    assert!(delta.provisions().is_empty());

    // Oracle-only window: checksums are not canon events and never demand
    // admissions.
    let mut oracle_log = ThreeCanonEventLog::empty();
    oracle_log
        .append(oracle(STATYA_93, "oracle-93", "2021-06-01"))
        .expect("oracle append");
    let delta =
        edition_delta(&oracle_log, day(FROM_ISO), day(TO_ISO), &[]).expect("oracle-only window");
    assert!(delta.provisions().is_empty());
}

/// Window-error precedence: an inverted `(from, to]` is a D326 window error
/// (`Window(InvertedRange)`), checked before the admission gate even when
/// admissions are supplied and before any log traversal.
#[test]
fn inverted_range_is_window_error_before_admission() {
    let log = demo_log();
    // Admissions are present: the window error still wins.
    assert_eq!(
        edition_delta(&log, day(TO_ISO), day(FROM_ISO), &demo_admissions()),
        Err(EditionDeltaError::Window(ThreeCanonLogError::InvertedRange))
    );
    // The check precedes any log traversal: even an empty log inverts.
    assert_eq!(
        edition_delta(&ThreeCanonEventLog::empty(), 7, 3, &[]),
        Err(EditionDeltaError::Window(ThreeCanonLogError::InvertedRange))
    );
}

/// An assertion-or-effect window keeps its line (the effect drives force)
/// but carries no amending act: the whole call is `Unresolved` with
/// `MissingAmendingAct` — no act is ever synthesized from the assertion.
#[test]
fn assertion_or_effect_only_window_is_unresolved_missing_amending_act() {
    let mut log = ThreeCanonEventLog::empty();
    log.append(assertion_effect("assert-93-force", STATYA_93, LAW3_ISO))
        .expect("assertion append");
    let admissions = [admission(
        STATYA_93,
        LAW3_ISO,
        "rec:commencement:assert-93",
        TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
    )];
    assert_eq!(
        edition_delta(&log, day(FROM_ISO), day(TO_ISO), &admissions),
        Err(EditionDeltaError::Unresolved {
            target: cc(STATYA_93),
            cause: ProvenanceConstructionError::MissingAmendingAct,
        })
    );
}

/// The typed refusal names its target and cause in Display (bounded
/// diagnostics; no legal text, no raw payloads).
#[test]
fn edition_delta_error_display_names_window_unresolved_and_missing_admission() {
    let window = EditionDeltaError::Window(ThreeCanonLogError::InvertedRange).to_string();
    assert!(
        window.contains("inverted"),
        "window display must name the inversion: {window}"
    );

    let missing = EditionDeltaError::MissingAdmission {
        target: cc(STATYA_93),
    }
    .to_string();
    assert!(
        missing.contains(STATYA_93) && missing.contains("admission"),
        "missing-admission display must name the target: {missing}"
    );

    let unresolved = EditionDeltaError::Unresolved {
        target: cc(STATYA_93),
        cause: ProvenanceConstructionError::UnprovenCommencement,
    }
    .to_string();
    let cause = ProvenanceConstructionError::UnprovenCommencement.to_string();
    assert!(
        unresolved.contains(STATYA_93) && unresolved.contains(&cause),
        "unresolved display must name target and cause: {unresolved}"
    );
}

/// Honesty surface: one new gated-envelope non-claim naming R070 open, with
/// the existing D326/D325/D-03 non-claims preserved verbatim.
#[test]
fn non_claims_carry_gated_envelope_line_and_keep_r070_open() {
    let log = demo_log();
    let delta = edition_delta(&log, day(FROM_ISO), day(TO_ISO), &demo_admissions())
        .expect("delta for non-claims");
    let non_claims = delta.non_claims();
    assert!(
        non_claims
            .iter()
            .any(|line| line.contains("provenance") && line.contains("R070")),
        "the gated-envelope non-claim must name R070 open: {non_claims:?}"
    );
    // The S02 wiring must not drop the existing honesty lines.
    assert!(
        non_claims
            .iter()
            .any(|line| line.contains("not bitemporal checkout")),
        "bitemporal-checkout non-claim survives"
    );
    assert!(
        non_claims
            .iter()
            .any(|line| line.contains("interval algebra")),
        "interval-algebra non-claim survives"
    );
    assert!(
        non_claims
            .iter()
            .any(|line| line.contains("crystal compiler")),
        "crystal-compiler non-claim survives"
    );
}

#[test]
fn unused_admission_for_non_kept_target_is_ignored() {
    let log = demo_log();
    let mut admissions = demo_admissions().to_vec();
    admissions.push(admission(
        STATYA_93_1,
        FROM_ISO,
        "rec:commencement:unused-93-1",
        TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
    ));

    let delta = edition_delta(&log, day(FROM_ISO), day(TO_ISO), &admissions)
        .expect("an admission outside the keep-set is not a phantom row");
    assert_eq!(
        delta
            .provisions()
            .iter()
            .map(|row| row.target().as_str())
            .collect::<Vec<_>>(),
        [STATYA_5, STATYA_93]
    );
}

#[test]
fn hypothesized_commencement_is_stored_not_upgraded() {
    let admissions = [
        admission_with_class(
            STATYA_5,
            LAW3_ISO,
            EvidenceClass::HypothesizedFromOracleDiff,
            "rec:commencement:hypothesized-5",
            TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
        ),
        admission(
            STATYA_93,
            LAW3_ISO,
            "rec:commencement:legislative-93",
            TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
        ),
    ];

    let delta = edition_delta(&demo_log(), day(FROM_ISO), day(TO_ISO), &admissions)
        .expect("hypothesized evidence is data, not an upgraded claim");
    assert_eq!(
        provision(&delta, STATYA_5)
            .provenance()
            .commencement()
            .evidence_class(),
        EvidenceClass::HypothesizedFromOracleDiff
    );
}

#[test]
fn explicitly_absent_and_declared_transitional_roundtrip() {
    let declared_ref = rid("rec:transition:declared-93");
    let admissions = [
        admission(
            STATYA_5,
            LAW3_ISO,
            "rec:commencement:absent-5",
            TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification"),
        ),
        admission(
            STATYA_93,
            LAW3_ISO,
            "rec:commencement:declared-93",
            TransitionalEvidence::Declared(declared_ref.clone()),
        ),
    ];

    let delta = edition_delta(&demo_log(), day(FROM_ISO), day(TO_ISO), &admissions)
        .expect("both explicit transitional states are admitted");
    assert_eq!(
        provision(&delta, STATYA_5).provenance().transitional(),
        &TransitionalEvidence::try_explicitly_absent(
    "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).",
)
.expect("source-bound absence justification")
    );
    assert_eq!(
        provision(&delta, STATYA_93).provenance().transitional(),
        &TransitionalEvidence::Declared(declared_ref)
    );
}
