use ln_testkit::{
    assert_domain_evidence_port_contract,
    assert_hostile_mutating_evidence_fails_honest_domain_contract,
};
use ln_work::adapters::{FixedDomainEvidence, HostileMutatingEvidence};
use ln_work::domain::{DomainSnapshotId, PublicationSnapshotId, WorkUnitId};

fn unit() -> WorkUnitId {
    WorkUnitId::parse("work:contract-1").expect("work unit")
}

#[test]
fn fixed_domain_evidence_satisfies_shared_port_contract() {
    let evidence = FixedDomainEvidence::with_unit(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("domain"),
        PublicationSnapshotId::parse("publication:P1").expect("publication"),
    );
    assert_domain_evidence_port_contract(&evidence);
}

#[test]
fn hostile_mutating_evidence_fails_honest_domain_contract() {
    let evidence = HostileMutatingEvidence::new(
        unit(),
        DomainSnapshotId::parse("domain:D1").expect("domain"),
        PublicationSnapshotId::parse("publication:P1").expect("publication"),
    );
    assert_hostile_mutating_evidence_fails_honest_domain_contract(&evidence);

    let result = std::panic::catch_unwind(|| {
        let evidence = HostileMutatingEvidence::new(
            unit(),
            DomainSnapshotId::parse("domain:D1").expect("domain"),
            PublicationSnapshotId::parse("publication:P1").expect("publication"),
        );
        assert_domain_evidence_port_contract(&evidence);
    });
    assert!(
        result.is_err(),
        "hostile mutating evidence must fail the honest domain evidence contract"
    );
}
