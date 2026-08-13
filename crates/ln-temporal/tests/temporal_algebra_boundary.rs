//! Design-boundary contracts: five-clock safety ≠ complete temporal algebra
//! (RC11-F06 / ADR-0009 non-claims).

use ln_temporal::domain::{
    classify_temporal_capability, reject_derived_interval_as_source_truth, ClockKind,
    TemporalAlgebraCapability, TemporalCapabilityClass,
};

#[test]
fn five_clock_kinds_remain_closed_set_of_five() {
    assert_eq!(ClockKind::all().len(), 5);
}

#[test]
fn algebra_capabilities_are_explicitly_deferred() {
    for capability in TemporalAlgebraCapability::all() {
        let boundary = classify_temporal_capability(capability);
        assert_eq!(boundary.class, TemporalCapabilityClass::DeferredAlgebra);
        assert_eq!(boundary.capability, capability);
        assert!(
            boundary
                .non_claims
                .iter()
                .any(|c| c.contains("not a complete temporal algebra")),
            "boundary must restate F06 non-claim for {:?}",
            capability
        );
        assert!(
            !boundary.non_claims.is_empty(),
            "non-claims required for {:?}",
            capability
        );
    }
}

#[test]
fn derived_interval_cannot_become_source_truth() {
    let boundary = reject_derived_interval_as_source_truth();
    assert_eq!(
        boundary.capability,
        TemporalAlgebraCapability::DerivedEffectiveWindowAsSourceTruth
    );
    assert_eq!(boundary.class, TemporalCapabilityClass::DeferredAlgebra);
    assert!(boundary
        .non_claims
        .iter()
        .any(|c| c.contains("projections") || c.contains("source truth")));
}

#[test]
fn algebra_inventory_does_not_expand_clock_set() {
    // Algebra capabilities are orthogonal inventory; they must not be clock kinds.
    let clock_names: Vec<&str> = ClockKind::all().iter().map(|c| c.as_str()).collect();
    for capability in TemporalAlgebraCapability::all() {
        assert!(
            !clock_names.contains(&capability.as_str()),
            "algebra capability {:?} must not collide with a five-clock role name",
            capability
        );
    }
}

#[test]
fn deferred_algebra_is_not_five_clock_safety() {
    let boundary = classify_temporal_capability(TemporalAlgebraCapability::IntervalOverlap);
    assert_ne!(boundary.class, TemporalCapabilityClass::FiveClockSafety);
    assert_eq!(boundary.class.as_str(), "deferred_algebra");
}
