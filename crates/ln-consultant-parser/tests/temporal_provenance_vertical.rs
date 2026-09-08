//! M203 S07 T04: bounded XML -> mention -> binding -> amendment -> provenance
//! -> normative state -> edition delta -> checkout vertical.
//!
//! This is an evidence-backed integration fixture, not a corpus coverage claim.
//! The staged manifest remains non-authoritative and R070 remains open.

use std::path::{Path, PathBuf};

use ln_decode::lawref::capture_lawrefs;
use ln_temporal::calendar::legal_act_effect_day_to_ordinal;
use ln_temporal::document_context::{BlockId, TextSpan};
use ln_temporal::domain::{
    checkout_projection_at, edition_delta, AmendingActId, AmendmentFacetKind, C1Candidate,
    CanonRecordId, ComponentConceptId, EvidenceClass, ForceStatusEvent, ForceStatusTimeline,
    NormativeState, ThreeCanonEventLog,
};
use ln_temporal::identity_binding::{
    assemble_identifying_act, build_official_identity_claim, ActAssemblyOutcome, BindingEndpoints,
    BindingOutcome, BindingUnresolvedReason, BoundTarget, FieldKind, FieldSource, FieldStatus,
    IdentityFieldClaim, ReferenceBindingCandidate, ReferenceEndpoint,
};
use ln_temporal::provenance::{
    EditionProvenanceEnvelope, ProvenanceAdmission, TransitionalEvidence,
};

const MANIFEST_JSON: &str =
    include_str!("../../../prd/migration/rust-evidence/m203-s07-staged-edition-manifest.json");
const CANON_484: &str =
    "consru_export/consru_export/exports/npa/law_2024-12-26_484-fz_rev-unknown_1a599b98.xml";
const TARGET: &str = "cc:44-fz:statya-93";
const ACT: &str = "act:484-fz:2024-12-26";
const RECORD: &str = "rec:amend:484-93";
const RULE_REF: &str = "rec:commencement:484-93:hypothesized";
const TRANSITIONAL_NOTE: &str = "affirmative fixture declaration that no transitional rule is evidenced in this bounded packet; not a product default and not a chronology guess (D406 / ADR-0021 TSG-009).";

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..").join(
        std::env::var("CONSULTANT_EXPORT_DIR")
            .ok()
            .filter(|value| !value.trim().is_empty())
            .unwrap_or_else(|| "consru_export".to_owned()),
    )
}

fn day(value: &str) -> i64 {
    legal_act_effect_day_to_ordinal(value).expect("valid civil day")
}
fn cc(value: &str) -> ComponentConceptId {
    ComponentConceptId::parse(value).expect("component id")
}
fn rid(value: &str) -> CanonRecordId {
    CanonRecordId::parse(value).expect("record id")
}
fn act(value: &str) -> AmendingActId {
    AmendingActId::parse(value).expect("act id")
}

fn claim(field: FieldKind, value: &str, span: TextSpan) -> IdentityFieldClaim {
    IdentityFieldClaim::new(
        field,
        BlockId::new(1),
        span,
        FieldSource::ExplicitMember,
        FieldStatus::Explicit,
        value,
    )
    .expect("non-empty identity claim")
}

fn log() -> ThreeCanonEventLog {
    let mut log = ThreeCanonEventLog::empty();
    log.append_c1_candidate(
        rid(RECORD),
        C1Candidate::LegislativeAmendment {
            target: cc(TARGET),
            effect_day: day("2024-12-26"),
            amending_act_raw: ACT.to_owned(),
            evidence: EvidenceClass::HypothesizedFromOracleDiff,
            facets: vec![AmendmentFacetKind::Text, AmendmentFacetKind::Force],
            force_transition: Some(NormativeState::InForce),
        },
    )
    .expect("C1 legislative candidate");
    log
}

fn admission() -> ProvenanceAdmission {
    ProvenanceAdmission::try_new(
        cc(TARGET),
        day("2024-12-26"),
        EvidenceClass::HypothesizedFromOracleDiff,
        RULE_REF,
        TransitionalEvidence::try_explicitly_absent(TRANSITIONAL_NOTE).expect("manifest note"),
    )
    .expect("manifest admission")
}

#[test]
fn staged_manifest_runs_the_complete_temporal_vertical() {
    // Honesty pins are read from the tracked mirror, never inferred from XML.
    assert!(MANIFEST_JSON.contains("\"authoritative\": false"));
    assert!(MANIFEST_JSON.contains("R070 remains active"));
    assert!(MANIFEST_JSON.contains("\"explicit_unresolved\""));
    assert!(MANIFEST_JSON.contains("\"cc:44-fz\""));
    assert!(!MANIFEST_JSON.contains("promotion"));
    assert!(MANIFEST_JSON.contains("D216"));

    // XML -> mention: invalid UTF-8 is a typed, file-specific failure rather
    // than a lossy read or a skipped evidence-backed test.
    let path = root().join(CANON_484.strip_prefix("consru_export/").unwrap());
    let bytes = std::fs::read(&path).unwrap_or_else(|error| panic!("{}: {error}", path.display()));
    let xml = String::from_utf8(bytes)
        .unwrap_or_else(|error| panic!("{} is not UTF-8: {error}", path.display()));
    let captures = capture_lawrefs(&xml);
    let mention = captures
        .captures()
        .iter()
        .find(|candidate| candidate.user_text(&xml).contains("93"))
        .expect("canon must yield a target law-reference mention");
    let mention_text = mention.user_text(&xml);
    assert!(!mention_text.is_empty());
    assert_eq!(&xml[mention.span.start()..mention.span.end()], mention_text);

    // Binding: a complete identity claim can be projected, while a missing
    // target remains an explicit unresolved terminal outcome.
    let span = TextSpan::new(mention.span.start(), mention.span.end()).expect("mention span");
    let assembled = assemble_identifying_act(vec![
        claim(FieldKind::Type, "федеральный закон", span),
        claim(FieldKind::Number, "484-ФЗ", span),
    ]);
    let ActAssemblyOutcome::Compatible(identity) = assembled else {
        panic!("federal identity claims should assemble")
    };
    assert!(matches!(
        build_official_identity_claim(&identity),
        ln_temporal::identity_binding::IdentityClaimOutcome::Proposed(_)
    ));
    let endpoint = ReferenceEndpoint::new(TARGET, span).expect("target endpoint");
    let candidate = ReferenceBindingCandidate::new(
        span,
        ACT,
        BoundTarget::Claim(TARGET.to_owned()),
        BindingEndpoints::Single(endpoint),
    )
    .expect("bound reference");
    assert!(matches!(
        BindingOutcome::Candidate(candidate),
        BindingOutcome::Candidate(_)
    ));
    assert!(matches!(
        BindingOutcome::Unresolved {
            reason: BindingUnresolvedReason::MissingTargetClaim
        },
        BindingOutcome::Unresolved { .. }
    ));

    // Amendment event -> provenance -> EditionDelta, retaining all evidence
    // legs and the hypothesized class without upgrading it.
    let event_log = log();
    let delta = edition_delta(
        &event_log,
        day("2024-12-01"),
        day("2024-12-26"),
        &[admission()],
    )
    .expect("fully admitted staged edition delta");
    assert_eq!(delta.provisions().len(), 1);
    assert!(!delta.provisions()[0].events().is_empty());
    let envelope = delta.provisions()[0].provenance();
    assert!(!envelope.amending_acts().is_empty());
    assert!(!envelope.affected_provisions().is_empty());
    assert!(!envelope.delta_evidence().is_empty());
    assert!(!envelope.non_claims().is_empty());
    assert_eq!(
        envelope.transitional().justification(),
        Some(TRANSITIONAL_NOTE)
    );
    assert_eq!(delta.dedup_report().amending_act_duplicates, 0);
    assert_eq!(delta.dedup_report().delta_evidence_duplicates, 0);

    // NormativeState -> checkout: Unknown before the force event, then the
    // event's own status at the right boundary; no neighboring concept exists.
    let mut timeline = ForceStatusTimeline::empty();
    timeline
        .append(
            ForceStatusEvent::try_new(
                cc(TARGET),
                NormativeState::InForce,
                day("2024-12-26"),
                act(ACT),
            )
            .expect("force event from staged log"),
        )
        .expect("timeline append");
    let before =
        ln_temporal::domain::resolve_force_status_at(&timeline, &cc(TARGET), day("2024-12-01"))
            .expect("pre-effect resolution");
    assert_eq!(before.status, NormativeState::Unknown);
    let at_effect =
        ln_temporal::domain::resolve_force_status_at(&timeline, &cc(TARGET), day("2024-12-26"))
            .expect("effect-day resolution");
    assert_eq!(at_effect.status, NormativeState::InForce);

    let before_checkout = checkout_projection_at(&ThreeCanonEventLog::empty(), day("2024-12-01"))
        .expect("pre-effect checkout");
    assert!(before_checkout.provisions().is_empty());
    let after_checkout =
        checkout_projection_at(&event_log, day("2024-12-26")).expect("effect-day checkout");
    assert_eq!(after_checkout.provisions().len(), 1);
    assert_eq!(after_checkout.provisions()[0].target().as_str(), TARGET);
    assert!(!after_checkout.non_claims().is_empty());
}

#[test]
fn staged_manifest_keeps_source_bound_packet_constructor_fail_closed() {
    let error = EditionProvenanceEnvelope::try_new_raw(
        &[ACT],
        &[TARGET],
        ln_temporal::provenance::CommencementEvidence::try_new(
            day("2024-12-26"),
            EvidenceClass::HypothesizedFromOracleDiff,
            RULE_REF,
        )
        .expect("commencement"),
        TransitionalEvidence::try_explicitly_absent(TRANSITIONAL_NOTE).expect("note"),
        &[RECORD, RECORD],
    )
    .expect_err("packet duplicate must not be silently folded");
    assert_eq!(
        error,
        ln_temporal::provenance::ProvenanceConstructionError::DuplicateDeltaEvidence
    );
}

#[test]
fn staged_manifest_source_has_expected_edition_pin_shape() {
    assert!(MANIFEST_JSON.contains(CANON_484));
    assert!(
        MANIFEST_JSON.contains("67f781dbd6a7d03d6035e6a509c983b17fcc519213c493987cf8f71debc1a37d")
    );
    assert!(MANIFEST_JSON.contains("\"evidence_backed\""));
    assert!(MANIFEST_JSON.contains("\"works\": 1"));
}
