use ln_replay::adapters::{sample_checkpoint, InMemoryCheckpointStore, InMemoryEffectLedger};
use ln_replay::application::CoordinateCheckpointAndReplay;
use ln_replay::domain::{
    CheckpointDigest, CheckpointId, EffectId, OperationId, ReplayOutcome, ReplayRequest, RequestId,
    RuleVersion, REPLAY_POLICY_VERSION,
};

fn request(digest: &str, rules: &str, operation: &str, effect: &str) -> ReplayRequest {
    ReplayRequest {
        request_id: RequestId::parse("req:R1").expect("id"),
        checkpoint_id: CheckpointId::parse("cp:1").expect("id"),
        expected_digest: CheckpointDigest::parse(digest).expect("id"),
        expected_rule_version: RuleVersion::parse(rules).expect("id"),
        operation_id: OperationId::parse(operation).expect("id"),
        effect_id: EffectId::parse(effect).expect("id"),
    }
}

fn honest_svc() -> CoordinateCheckpointAndReplay<InMemoryCheckpointStore, InMemoryEffectLedger> {
    let store = InMemoryCheckpointStore::new().insert(sample_checkpoint(
        "cp:1",
        "digest:abc",
        "rules:v1",
        "op:1",
        "effect:1",
        "history:h1",
    ));
    CoordinateCheckpointAndReplay::new(store, InMemoryEffectLedger::new())
}

#[test]
fn first_apply_then_suppress_on_identical_replay() {
    let mut svc = honest_svc();
    let req = request("digest:abc", "rules:v1", "op:1", "effect:1");
    let first = svc.replay(req.clone());
    assert_eq!(first.outcome, ReplayOutcome::Applied);
    assert!(!first.effect_suppressed);
    assert_eq!(first.applied_count, 1);
    assert!(first.publication_authority.is_none());
    assert!(!first.publication_authority_changed);
    assert!(!first.lineage_rewritten);
    assert_eq!(first.trace.policy_version, REPLAY_POLICY_VERSION);

    let second = svc.replay(req);
    assert_eq!(second.outcome, ReplayOutcome::Suppressed);
    assert!(second.effect_suppressed);
    assert_eq!(second.applied_count, 1);
    assert_eq!(second.trace.applied_count_before, 1);
    assert_eq!(second.trace.applied_count_after, 1);
    assert!(second.publication_authority.is_none());
    assert!(!second.publication_authority_changed);
    assert!(!second.lineage_rewritten);
    assert_eq!(
        second
            .trace
            .prior_applied_digest
            .as_ref()
            .map(|d| d.as_str()),
        Some("digest:abc")
    );
}

#[test]
fn corrupt_digest_fails_without_apply() {
    let mut svc = honest_svc();
    let result = svc.replay(request("digest:WRONG", "rules:v1", "op:1", "effect:1"));
    assert_eq!(result.outcome, ReplayOutcome::Corrupt);
    assert_eq!(result.applied_count, 0);
    assert!(!result.effect_suppressed);
    assert!(!result.lineage_rewritten);
    assert!(result.publication_authority.is_none());
    assert!(!result.publication_authority_changed);
}

#[test]
fn incompatible_rule_version_fails_without_apply() {
    let mut svc = honest_svc();
    let result = svc.replay(request("digest:abc", "rules:v2", "op:1", "effect:1"));
    assert_eq!(result.outcome, ReplayOutcome::IncompatibleRule);
    assert_eq!(result.applied_count, 0);
    assert!(!result.lineage_rewritten);
    assert!(result.publication_authority.is_none());
}

#[test]
fn missing_checkpoint_is_incomplete() {
    let store = InMemoryCheckpointStore::new();
    let mut svc = CoordinateCheckpointAndReplay::new(store, InMemoryEffectLedger::new());
    let result = svc.replay(request("digest:abc", "rules:v1", "op:1", "effect:1"));
    assert_eq!(result.outcome, ReplayOutcome::Incomplete);
    assert_eq!(result.applied_count, 0);
}

#[test]
fn operation_mismatch_does_not_apply() {
    let mut svc = honest_svc();
    let result = svc.replay(request("digest:abc", "rules:v1", "op:OTHER", "effect:1"));
    assert_eq!(result.outcome, ReplayOutcome::Mismatch);
    assert_eq!(result.applied_count, 0);
}
