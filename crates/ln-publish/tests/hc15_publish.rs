use ln_publish::adapters::{HostileDualWriterLedger, InMemoryPublicationLedger};
use ln_publish::application::PublishAuthoritativeH1;
use ln_publish::domain::{
    AuthoritySurface, CompletenessEvidence, CutoffId, InputDigest, OperationId, PublicationOutcome,
    PublishRequest, RuleVersion, ScopeId, WriterId, PUBLICATION_POLICY_VERSION,
};

fn request(
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

fn honest() -> PublishAuthoritativeH1<InMemoryPublicationLedger> {
    PublishAuthoritativeH1::new(InMemoryPublicationLedger::new())
}

#[test]
fn complete_candidate_first_publish_is_authoritative() {
    let mut svc = honest();
    let result = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));

    assert_eq!(result.outcome, PublicationOutcome::Published);
    assert!(result.authoritative);
    assert!(result.has_publication_authority());
    assert!(result.h1_unit_id.is_some());
    assert_eq!(result.authority_surface, AuthoritySurface::Publication);
    assert_eq!(result.policy_version, PUBLICATION_POLICY_VERSION);
    assert_eq!(
        result.input_digest.as_ref().map(|d| d.as_str()),
        Some("digest:D1")
    );
    assert_eq!(svc.authoritative_count(), 1);
    assert!(svc.has_authoritative_for_scope(&ScopeId::parse("scope:S1").unwrap()));
    assert_eq!(
        svc.writer_for_scope(&ScopeId::parse("scope:S1").unwrap())
            .as_ref()
            .map(|w| w.as_str()),
        Some("writer:A")
    );
}

#[test]
fn identical_operation_and_digest_is_duplicate_same_unit() {
    let mut svc = honest();
    let req = request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    );

    let first = svc.publish(req.clone());
    assert_eq!(first.outcome, PublicationOutcome::Published);
    let first_unit = first.h1_unit_id.clone();

    let second = svc.publish(req);
    assert_eq!(second.outcome, PublicationOutcome::Duplicate);
    assert_eq!(second.h1_unit_id, first_unit);
    assert!(second.authoritative);
    assert!(second.has_publication_authority());
    assert_eq!(svc.authoritative_count(), 1);
    assert_eq!(
        svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
        first_unit
    );
}

#[test]
fn partial_candidate_is_incomplete_and_non_authoritative() {
    let mut svc = honest();
    let result = svc.publish(request(
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
    assert_eq!(result.authority_surface, AuthoritySurface::Publication);
    assert_eq!(svc.authoritative_count(), 0);
    assert!(!svc.has_authoritative_for_scope(&ScopeId::parse("scope:S1").unwrap()));
}

#[test]
fn missing_completeness_is_incomplete_and_non_authoritative() {
    let mut svc = honest();
    let result = svc.publish(request(
        "op:missing",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Missing,
    ));

    assert_eq!(result.outcome, PublicationOutcome::Incomplete);
    assert!(!result.authoritative);
    assert!(!result.has_publication_authority());
    assert_eq!(svc.authoritative_count(), 0);
}

#[test]
fn competing_writer_for_same_scope_is_rejected_without_mutating_first_unit() {
    let mut svc = honest();
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(first.outcome, PublicationOutcome::Published);
    let first_unit = first.h1_unit_id.clone();

    let competitor = svc.publish(request(
        "op:2",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));

    assert_eq!(
        competitor.outcome,
        PublicationOutcome::CompetingWriterRejected
    );
    assert!(!competitor.authoritative);
    assert!(!competitor.has_publication_authority());
    // First unit identity is reported as the sole occupant; not replaced.
    assert_eq!(competitor.h1_unit_id, first_unit);
    assert_eq!(svc.authoritative_count(), 1);
    assert_eq!(
        svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
        first_unit
    );
    assert_eq!(
        svc.writer_for_scope(&ScopeId::parse("scope:S1").unwrap())
            .as_ref()
            .map(|w| w.as_str()),
        Some("writer:A")
    );
}

#[test]
fn one_authoritative_unit_only_across_duplicate_and_competitor() {
    let mut svc = honest();
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let _ = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let _ = svc.publish(request(
        "op:2",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));
    let _ = svc.publish(request(
        "op:partial",
        "writer:A",
        "scope:S1",
        "digest:D3",
        CompletenessEvidence::Partial,
    ));

    assert_eq!(svc.authoritative_count(), 1);
    assert_eq!(
        svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
        first.h1_unit_id
    );
}

#[test]
fn same_writer_conflicting_digest_is_conflict_not_second_unit() {
    let mut svc = honest();
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    let conflict = svc.publish(request(
        "op:2",
        "writer:A",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));

    assert_eq!(conflict.outcome, PublicationOutcome::Conflict);
    assert!(!conflict.authoritative);
    assert!(!conflict.has_publication_authority());
    assert_eq!(conflict.h1_unit_id, first.h1_unit_id);
    assert_eq!(svc.authoritative_count(), 1);
}

#[test]
fn hostile_dual_writer_ledger_cannot_create_second_authoritative_unit() {
    let mut svc = PublishAuthoritativeH1::new(HostileDualWriterLedger::new());
    let first = svc.publish(request(
        "op:1",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(first.outcome, PublicationOutcome::Published);
    let first_unit = first.h1_unit_id.clone();

    let competitor = svc.publish(request(
        "op:2",
        "writer:B",
        "scope:S1",
        "digest:D2",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(
        competitor.outcome,
        PublicationOutcome::CompetingWriterRejected
    );
    assert_eq!(competitor.h1_unit_id, first_unit);
    // Application-owned cardinality, not hostile ledger inflation.
    assert_eq!(svc.authoritative_count(), 1);
    assert_eq!(
        svc.unit_for_scope(&ScopeId::parse("scope:S1").unwrap()),
        first_unit
    );
}

#[test]
fn cancel_without_unit_is_cancelled_non_authoritative() {
    let mut svc = honest();
    let cancelled = svc.cancel(
        OperationId::parse("op:never").unwrap(),
        WriterId::parse("writer:A").unwrap(),
    );
    assert_eq!(cancelled.outcome, PublicationOutcome::Cancelled);
    assert!(!cancelled.authoritative);
    assert!(!cancelled.has_publication_authority());
    assert_eq!(svc.authoritative_count(), 0);
}

#[test]
fn explicit_fail_never_grants_authority() {
    let mut svc = honest();
    let failed = svc.fail(request(
        "op:fail",
        "writer:A",
        "scope:S1",
        "digest:D1",
        CompletenessEvidence::Complete,
    ));
    assert_eq!(failed.outcome, PublicationOutcome::Failed);
    assert!(!failed.authoritative);
    assert!(!failed.has_publication_authority());
    assert_eq!(svc.authoritative_count(), 0);
}
