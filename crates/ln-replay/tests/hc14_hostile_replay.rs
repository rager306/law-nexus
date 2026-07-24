use ln_replay::adapters::{
    sample_checkpoint, HostileDuplicateEffectLedger, InMemoryCheckpointStore,
};
use ln_replay::application::CoordinateCheckpointAndReplay;
use ln_replay::domain::{
    CheckpointDigest, CheckpointId, EffectId, OperationId, ReplayOutcome, ReplayRequest,
    RequestId, RuleVersion,
};

fn request(digest: &str, rules: &str) -> ReplayRequest {
    ReplayRequest {
        request_id: RequestId::parse("req:hostile").expect("id"),
        checkpoint_id: CheckpointId::parse("cp:1").expect("id"),
        expected_digest: CheckpointDigest::parse(digest).expect("id"),
        expected_rule_version: RuleVersion::parse(rules).expect("id"),
        operation_id: OperationId::parse("op:1").expect("id"),
        effect_id: EffectId::parse("effect:1").expect("id"),
    }
}

fn hostile_svc(
) -> CoordinateCheckpointAndReplay<InMemoryCheckpointStore, HostileDuplicateEffectLedger> {
    let store = InMemoryCheckpointStore::new().insert(sample_checkpoint(
        "cp:1",
        "digest:abc",
        "rules:v1",
        "op:1",
        "effect:1",
        "history:h1",
    ));
    CoordinateCheckpointAndReplay::new(store, HostileDuplicateEffectLedger::new())
}

#[test]
fn hostile_ledger_cannot_force_duplicate_external_effect() {
    let mut svc = hostile_svc();
    let req = request("digest:abc", "rules:v1");
    let first = svc.replay(req.clone());
    assert_eq!(first.outcome, ReplayOutcome::Applied);
    assert_eq!(first.applied_count, 1);

    let second = svc.replay(req.clone());
    assert_eq!(second.outcome, ReplayOutcome::Suppressed);
    assert!(second.effect_suppressed);
    assert_eq!(second.applied_count, 1);
    assert_eq!(second.trace.applied_count_before, 1);
    assert_eq!(second.trace.applied_count_after, 1);
    assert!(!second.lineage_rewritten);
    assert!(second.publication_authority.is_none());
    assert!(!second.publication_authority_changed);

    // Third replay still suppressed; application count stays 1.
    let third = svc.replay(req);
    assert_eq!(third.outcome, ReplayOutcome::Suppressed);
    assert_eq!(third.applied_count, 1);
}

#[test]
fn hostile_cannot_override_corrupt_fail_closed() {
    let mut svc = hostile_svc();
    // First apply legitimately.
    let _ = svc.replay(request("digest:abc", "rules:v1"));
    let corrupt = svc.replay(request("digest:WRONG", "rules:v1"));
    assert_eq!(corrupt.outcome, ReplayOutcome::Corrupt);
    assert_eq!(corrupt.applied_count, 1);
    assert!(!corrupt.lineage_rewritten);
    assert!(corrupt.publication_authority.is_none());
}

#[test]
fn hostile_cannot_override_version_skew_fail_closed() {
    let mut svc = hostile_svc();
    let skew = svc.replay(request("digest:abc", "rules:v2"));
    assert_eq!(skew.outcome, ReplayOutcome::IncompatibleRule);
    assert_eq!(skew.applied_count, 0);
    assert!(!skew.lineage_rewritten);
    assert!(skew.publication_authority.is_none());
}

#[test]
fn hostile_never_grants_publication_authority_on_apply_or_suppress() {
    let mut svc = hostile_svc();
    let first = svc.replay(request("digest:abc", "rules:v1"));
    let second = svc.replay(request("digest:abc", "rules:v1"));
    assert!(first.publication_authority.is_none());
    assert!(!first.publication_authority_changed);
    assert!(second.publication_authority.is_none());
    assert!(!second.publication_authority_changed);
}
