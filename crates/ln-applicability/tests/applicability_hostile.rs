//! Hostile contracts: prerequisites cannot invent Applicable/NotApplicable.

use ln_applicability::application::EvaluateApplicability;
use ln_applicability::domain::{
    AbstentionKind, ApplicabilityDecision, ApplicabilityRequest, CaseFactsRevision, NormRuleId,
    PredicateRegistryRevision, PrerequisiteSnapshot, ProfileInputRevision,
};

#[test]
fn hostile_all_flags_true_cannot_mint_applicable() {
    let evaluator = EvaluateApplicability::new();
    let result = evaluator.evaluate(ApplicabilityRequest {
        rule_id: NormRuleId::parse("rule:hostile").expect("id"),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("id"),
        case_facts_revision: CaseFactsRevision::parse("facts:synthetic").expect("id"),
        profile_input_revision: ProfileInputRevision::parse("profile:hostile").expect("id"),
        prerequisites: PrerequisiteSnapshot {
            ctv_present: true,
            normative_state_present: true,
            transitional_resolved: true,
            provenance_present: true,
        },
    });
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    );
}

#[test]
fn first_missing_prerequisite_wins_in_stable_order() {
    let evaluator = EvaluateApplicability::new();
    // CTV missing should win over later missing flags.
    let result = evaluator.evaluate(ApplicabilityRequest {
        rule_id: NormRuleId::parse("rule:order").expect("id"),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("id"),
        case_facts_revision: CaseFactsRevision::parse("facts:x").expect("id"),
        profile_input_revision: ProfileInputRevision::parse("profile:x").expect("id"),
        prerequisites: PrerequisiteSnapshot {
            ctv_present: false,
            normative_state_present: false,
            transitional_resolved: false,
            provenance_present: false,
        },
    });
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::MissingCtv)
    );
}
