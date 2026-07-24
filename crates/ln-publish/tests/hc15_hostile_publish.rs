//! HC-15 Hostile publication contracts.
//!
//! These tests prove the application-owned publication authority survives
//! adversarial ledger behavior:
//! - Hostile dual-writer cannot mint a second authoritative unit.
//! - Hostile count inflation cannot trick application-owned cardinality.
//! - Partial candidates never gain authority under a hostile ledger.
//! - First unit identity is stable across repeated hostile attacks.
//! - Duplicate after hostile attack still maps to the original unit.

use ln_publish::adapters::HostileDualWriterLedger;
use ln_publish::application::PublishAuthoritativeH1;
use ln_publish::domain::{
    AuthoritySurface, CompletenessEvidence, CutoffId, InputDigest, OperationId, PublicationOutcome,
    PublishRequest, RuleVersion, ScopeId, WriterId, PUBLICATION_POLICY_VERSION,
};

fn hostile() -> PublishAuthoritativeH1<HostileDualWriterLedger> {
    PublishAuthoritativeH1::new(HostileDualWriterLedger::new())
}

fn req(
    op: &str,
    writer: &str,
    scope: &str,
    digest: &str,
    completeness: CompletenessEvidence,
) -> PublishRequest {
    PublishRequest {
        operation_id: OperationId::parse(op).expect("op"),
        writer_id: WriterId::parse(writer).expect("writer"),
        scope_id: ScopeId::parse(scope).expect("scope"),
        cutoff_id: CutoffId::parse("cutoff:2026-07-01").expect("cutoff"),
        rule_version: RuleVersion::parse("rules:v1").expect("rules"),
        input_digest: InputDigest::parse(digest).expect("digest"),
        completeness,
    }
}

#[test]
fn hostile_dual_writer_cannot_mint_second_authority_for_same_scope() {
    let mut svc = hostile();
    let first = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(first.outcome, PublicationOutcome::Published);
    assert!(first.authoritative);
    let first_unit = first.h1_unit_id.clone().expect("first unit");

    let attacker = svc.publish(req(
        "op:hostile",
        "writer:hostile",
        "scope:S1",
        "digest:D-evil",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(
        attacker.outcome,
        PublicationOutcome::CompetingWriterRejected
    );
    assert!(!attacker.authoritative);
    assert_eq!(attacker.h1_unit_id, Some(first_unit.clone()));
    assert_eq!(svc.authoritative_count(), 1);
    assert_eq!(
        svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
        Some(first_unit)
    );
}

#[test]
fn hostile_ledger_count_inflation_does_not_affect_app_owned_cardinality() {
    let mut svc = hostile();
    let _ = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let _ = svc.publish(req(
        "op:2",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));
    // HostileDualWriterLedger.authoritative_count() returns >=99, but
    // application-owned count must be exactly 1.
    assert_eq!(svc.authoritative_count(), 1);
}

#[test]
fn partial_candidate_never_authoritative_under_hostile_ledger() {
    let mut svc = hostile();
    let result = svc.publish(req(
        "op:partial",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Partial,
    ));
    assert_eq!(result.outcome, PublicationOutcome::Incomplete);
    assert!(!result.authoritative);
    assert!(!result.has_publication_authority());
    assert!(result.h1_unit_id.is_none());
    assert_eq!(svc.authoritative_count(), 0);
}

#[test]
fn missing_candidate_never_authoritative_under_hostile_ledger() {
    let mut svc = hostile();
    let result = svc.publish(req(
        "op:missing",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Missing,
    ));
    assert_eq!(result.outcome, PublicationOutcome::Incomplete);
    assert!(!result.authoritative);
    assert_eq!(svc.authoritative_count(), 0);
}

#[test]
fn first_unit_identity_stable_across_repeated_hostile_attacks() {
    let mut svc = hostile();
    let first = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let first_unit = first.h1_unit_id.clone().expect("first unit");

    for i in 1..=5 {
        let attacker = svc.publish(req(
            &format!("op:attack-{i}"),
            "writer:attacker",
            "scope:S1",
            &format!("digest:evil-{i}"),
            CompletenessEvidence::Complete,
        ));
        assert_eq!(
            attacker.outcome,
            PublicationOutcome::CompetingWriterRejected
        );
        assert_eq!(svc.authoritative_count(), 1);
        assert_eq!(
            svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
            Some(first_unit.clone())
        );
    }
}

#[test]
fn duplicate_after_hostile_attack_still_maps_to_first_unit() {
    let mut svc = hostile();
    let first = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let first_unit = first.h1_unit_id.clone().expect("first unit");

    // Hostile attack
    let _ = svc.publish(req(
        "op:hostile",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));

    // Honest duplicate of original operation
    let dup = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(dup.outcome, PublicationOutcome::Duplicate);
    assert!(dup.authoritative);
    assert_eq!(dup.h1_unit_id, Some(first_unit));
    assert_eq!(svc.authoritative_count(), 1);
}

#[test]
fn hostile_adapter_did_attempt_second_writer_but_app_rejected() {
    let mut ledger = HostileDualWriterLedger::new();
    let mut svc = PublishAuthoritativeH1::new(HostileDualWriterLedger::new());

    let _ = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));

    // The service's internal ledger was called put() which triggers
    // forced_second_writer_attempts on the HostileDualWriterLedger.
    // But app-owned count stays 1 regardless.
    assert_eq!(svc.authoritative_count(), 1);

    // Verify the hostile adapter mechanism exists by checking the standalone
    // ledger behavior.
    use ln_publish::domain::PublicationRecord;
    use ln_publish::ports::PublicationLedgerPort;
    let record = PublicationRecord {
        operation_id: OperationId::parse("op:test").unwrap(),
        writer_id: WriterId::parse("writer:X").unwrap(),
        scope_id: ScopeId::parse("scope:T").unwrap(),
        cutoff_id: CutoffId::parse("cutoff:c").unwrap(),
        rule_version: RuleVersion::parse("rules:r").unwrap(),
        input_digest: InputDigest::parse("digest:d").unwrap(),
        h1_unit_id: ln_publish::domain::H1UnitId::parse("h1:t").unwrap(),
        completeness: CompletenessEvidence::Complete,
        authoritative: true,
        publication_authority: Some(ln_publish::domain::PublicationAuthority::default()),
        authority_surface: AuthoritySurface::Publication,
    };
    ledger.put(record);
    assert!(ledger.forced_second_writer_attempts() > 0);
    // Hostile inflated count
    assert!(ledger.authoritative_count() >= 99);
}

#[test]
fn hostile_scenario_preserves_authority_surface_and_policy_version() {
    let mut svc = hostile();
    let result = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let _ = svc.publish(req(
        "op:hostile",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));

    assert_eq!(result.authority_surface, AuthoritySurface::Publication);
    assert_eq!(result.policy_version, PUBLICATION_POLICY_VERSION);
    assert_eq!(svc.authoritative_count(), 1);
}

#[test]
fn hostile_scenario_same_writer_conflict_preserves_first_unit() {
    let mut svc = hostile();
    let first = svc.publish(req(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let first_unit = first.h1_unit_id.clone().expect("first unit");

    // Same writer tries different digest for same scope
    let conflict = svc.publish(req(
        "op:2",
        "writer:A",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(conflict.outcome, PublicationOutcome::Conflict);
    assert!(!conflict.authoritative);
    assert_eq!(conflict.h1_unit_id, Some(first_unit));
    assert_eq!(svc.authoritative_count(), 1);
}
