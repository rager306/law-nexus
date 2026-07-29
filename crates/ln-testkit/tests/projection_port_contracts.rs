use ln_projection::adapters::{HonestExecutor, HostileAuthoritativeExecutor};
use ln_projection::domain::{NodeId, RebuildOutcome};
use ln_testkit::{
    assert_hostile_authoritative_executor_fails_honest_rebuild_contract,
    assert_rebuild_executor_port_contract,
};

#[test]
fn honest_executor_satisfies_shared_port_contract() {
    let executor = HonestExecutor {
        outcome: RebuildOutcome::Partial,
        residual_gaps: vec![],
        extra_stale: vec![NodeId::parse("node:stale1").expect("node")],
    };
    assert_rebuild_executor_port_contract(&executor);
}

#[test]
fn hostile_authoritative_executor_fails_honest_rebuild_contract() {
    let hostile = HostileAuthoritativeExecutor {
        base_outcome: RebuildOutcome::RebuiltDisposable,
    };
    assert_hostile_authoritative_executor_fails_honest_rebuild_contract(&hostile);

    let result = std::panic::catch_unwind(|| {
        let hostile = HostileAuthoritativeExecutor {
            base_outcome: RebuildOutcome::RebuiltDisposable,
        };
        assert_rebuild_executor_port_contract(&hostile);
    });
    assert!(
        result.is_err(),
        "hostile authoritative executor must fail the honest rebuild executor contract"
    );
}
