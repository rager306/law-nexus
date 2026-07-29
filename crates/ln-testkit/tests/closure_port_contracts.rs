use ln_closure::adapters::{FixedDependencyEvidence, HostileProgressCompleteness};
use ln_closure::domain::{NodeId, RuleVersion};
use ln_testkit::{
    assert_dependency_evidence_port_contract,
    assert_hostile_progress_completeness_fails_honest_dependency_contract,
};

fn base_evidence() -> FixedDependencyEvidence {
    FixedDependencyEvidence::new(RuleVersion::parse("rules:v1").expect("rules"))
        .with_node(
            NodeId::parse("node:A").expect("node"),
            vec![NodeId::parse("node:B").expect("node")],
        )
        .with_node(
            NodeId::parse("node:B").expect("node"),
            vec![NodeId::parse("node:C").expect("node")],
        )
        .with_node(NodeId::parse("node:C").expect("node"), vec![])
}

#[test]
fn fixed_dependency_evidence_satisfies_shared_port_contract() {
    let evidence = base_evidence();
    assert_dependency_evidence_port_contract(&evidence);
}

#[test]
fn hostile_progress_completeness_fails_honest_dependency_contract() {
    let hostile = HostileProgressCompleteness::wrapping(base_evidence().with_progress(0, 0));
    assert_hostile_progress_completeness_fails_honest_dependency_contract(&hostile);

    let result = std::panic::catch_unwind(|| {
        let hostile = HostileProgressCompleteness::wrapping(base_evidence().with_progress(0, 0));
        assert_dependency_evidence_port_contract(&hostile);
    });
    assert!(
        result.is_err(),
        "hostile progress completeness must fail the honest dependency evidence contract"
    );
}
