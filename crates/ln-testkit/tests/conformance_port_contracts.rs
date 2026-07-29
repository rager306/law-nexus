use ln_conformance::adapters::{HostileVerdictInflator, InMemoryConformanceOracle};
use ln_conformance::domain::CaseVerdict;
use ln_testkit::{
    assert_conformance_oracle_contract,
    assert_hostile_verdict_inflator_fails_honest_conformance_contract,
};

#[test]
fn in_memory_conformance_oracle_satisfies_shared_port_contract() {
    let oracle = InMemoryConformanceOracle::new()
        .with("HC-01", CaseVerdict::Pass)
        .with("HC-02", CaseVerdict::Fail);
    assert_conformance_oracle_contract(&oracle);
}

#[test]
fn hostile_verdict_inflator_fails_honest_conformance_contract() {
    let oracle = HostileVerdictInflator::new().with("HC-01", CaseVerdict::Pass);
    assert_hostile_verdict_inflator_fails_honest_conformance_contract(&oracle);

    let result = std::panic::catch_unwind(|| {
        let hostile = HostileVerdictInflator::new().with("HC-01", CaseVerdict::Pass);
        assert_conformance_oracle_contract(&hostile);
    });
    assert!(
        result.is_err(),
        "hostile verdict inflator must fail the honest conformance contract"
    );
}
