//! Applicability capability inventory boundary (RC12-F05 / ADR-0023 / TSG-005/006).

use ln_applicability::domain::{
    classify_applicability_capability, reject_algebra_satisfied_as_applicable,
    reject_norm_rule_ir_as_product_runtime, ApplicabilityCapability, ApplicabilityCapabilityClass,
};

#[test]
fn seven_capabilities_are_named() {
    assert_eq!(ApplicabilityCapability::all().len(), 7);
    assert_eq!(
        ApplicabilityCapability::PositiveApplicabilityDecision.as_str(),
        "positive_applicability_decision"
    );
}

#[test]
fn landed_spines_are_explicit() {
    for cap in [
        ApplicabilityCapability::AbstentionKernel,
        ApplicabilityCapability::NormRuleIr,
        ApplicabilityCapability::PredicateAlgebraSpine,
    ] {
        let b = classify_applicability_capability(cap);
        assert_eq!(b.class, ApplicabilityCapabilityClass::LandedSpine);
        assert!(!b.non_claims.is_empty());
    }
}

#[test]
fn product_capabilities_remain_deferred() {
    for cap in [
        ApplicabilityCapability::PositiveApplicabilityDecision,
        ApplicabilityCapability::ProductCaseFactsPipeline,
        ApplicabilityCapability::ProfileSpecialPredicates,
        ApplicabilityCapability::RealCaseEvidenceAcceptance,
    ] {
        let b = classify_applicability_capability(cap);
        assert_eq!(b.class, ApplicabilityCapabilityClass::DeferredProduct);
        assert!(b
            .non_claims
            .iter()
            .any(|c| c.contains("deferred") || c.contains("not product")));
    }
}

#[test]
fn algebra_satisfied_cannot_mint_applicable() {
    let b = reject_algebra_satisfied_as_applicable();
    assert_eq!(
        b.capability,
        ApplicabilityCapability::PositiveApplicabilityDecision
    );
    assert_eq!(b.class, ApplicabilityCapabilityClass::DeferredProduct);
    assert!(b
        .non_claims
        .iter()
        .any(|c| c.contains("does not mint") || c.contains("Applicable")));
}

#[test]
fn norm_rule_ir_is_not_product_runtime_completeness() {
    let b = reject_norm_rule_ir_as_product_runtime();
    assert_eq!(b.capability, ApplicabilityCapability::NormRuleIr);
    assert_eq!(b.class, ApplicabilityCapabilityClass::LandedSpine);
    assert!(b
        .non_claims
        .iter()
        .any(|c| c.contains("not product applicability runtime") || c.contains("TSG-006")));
}
