use ln_admission::adapters::{HonestBoundObservation, HostileVendorCapacity};
use ln_admission::domain::BoundId;
use ln_testkit::{
    assert_bound_observation_port_contract,
    assert_hostile_vendor_capacity_fails_honest_bound_contract,
};

#[test]
fn honest_bound_observation_satisfies_shared_port_contract() {
    let bound = HonestBoundObservation::measured(BoundId::parse("bound:contract-1").expect("id"));
    assert_bound_observation_port_contract(&bound);
}

#[test]
fn hostile_vendor_capacity_fails_honest_bound_contract() {
    let hostile = HostileVendorCapacity {
        pretend_measured: true,
        bound_id: Some(BoundId::parse("bound:fake").expect("id")),
    };
    assert_hostile_vendor_capacity_fails_honest_bound_contract(&hostile);

    let result = std::panic::catch_unwind(|| {
        let hostile = HostileVendorCapacity {
            pretend_measured: true,
            bound_id: Some(BoundId::parse("bound:fake").expect("id")),
        };
        assert_bound_observation_port_contract(&hostile);
    });
    assert!(
        result.is_err(),
        "hostile vendor capacity must fail the honest bound observation contract"
    );
}
