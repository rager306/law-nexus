//! Design-boundary contracts: NormativeState dimensional separation
//! (RC11-F09 / TSG-004 / ADR-0018).

use ln_temporal::domain::{
    classify_normative_dimension, reject_force_as_applicability, reject_version_relation_as_force,
    NormativeDimension, NormativeDimensionClass,
};

#[test]
fn four_dimensions_are_named_and_distinct() {
    let dims = NormativeDimension::all();
    assert_eq!(dims.len(), 4);
    let names: Vec<&str> = dims.iter().map(|d| d.as_str()).collect();
    assert!(names.contains(&"force_status"));
    assert!(names.contains(&"version_relation"));
    assert!(names.contains(&"applicability"));
    assert!(names.contains(&"epistemic_outcome"));
    assert_eq!(
        names.len(),
        names
            .iter()
            .collect::<std::collections::BTreeSet<_>>()
            .len()
    );
}

#[test]
fn each_dimension_is_design_orthogonal_not_mixed_runtime() {
    for dimension in NormativeDimension::all() {
        let boundary = classify_normative_dimension(dimension);
        assert_eq!(boundary.class, NormativeDimensionClass::DesignOrthogonal);
        assert_eq!(boundary.dimension, dimension);
        assert!(
            boundary
                .non_claims
                .iter()
                .any(|c| c.contains("must not mix") || c.contains("does not imply")),
            "boundary must restate F09 non-claim for {:?}",
            dimension
        );
    }
}

#[test]
fn force_cannot_decide_applicability() {
    let boundary = reject_force_as_applicability();
    assert_eq!(boundary.dimension, NormativeDimension::ForceStatus);
    assert!(boundary.non_claims.iter().any(
        |c| c.contains("does not decide Applicability") || c.contains("InForce for Applicable")
    ),);
}

#[test]
fn version_relation_cannot_imply_force() {
    let boundary = reject_version_relation_as_force();
    assert_eq!(boundary.dimension, NormativeDimension::VersionRelation);
    assert!(boundary
        .non_claims
        .iter()
        .any(|c| c.contains("does not imply ForceStatus") || c.contains("text presence")),);
}

#[test]
fn design_class_is_not_executable_runtime() {
    let boundary = classify_normative_dimension(NormativeDimension::EpistemicOutcome);
    assert_ne!(boundary.class, NormativeDimensionClass::ExecutableRuntime);
    assert_eq!(boundary.class.as_str(), "design_orthogonal");
}
