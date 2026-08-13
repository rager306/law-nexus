//! Hostile predicate algebra cases (RC11-F04b).

use ln_applicability::application::EvaluateApplicability;
use ln_applicability::domain::{
    compose_norm_rule_predicates, AbstentionKind, ApplicabilityDecision, ApplicabilityRequest,
    CaseFactSet, CaseFactsRevision, NormRule, NormRuleCondition, NormRuleId, NormRuleRevision,
    PredicateOutcome, PredicateRegistryRevision, PrerequisiteSnapshot, ProfileInputRevision,
    TemporalScope,
};

#[test]
fn empty_fact_set_does_not_panic_and_abstains() {
    let rule = NormRule::try_new(
        NormRuleId::parse("rule:hostile").expect("id"),
        NormRuleRevision::parse("normrule:rev:h").expect("rev"),
        vec![NormRuleCondition::try_new("cond:x", "fact_required").expect("c")],
        vec![],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect("rule");
    let composed = compose_norm_rule_predicates(&rule, &CaseFactSet::empty());
    assert_eq!(
        composed.outcome,
        PredicateOutcome::Abstain(AbstentionKind::MissingOrAmbiguousFacts)
    );
}

#[test]
fn invalid_fact_id_fails_closed() {
    assert!(CaseFactSet::try_from_pairs(&[("", true)]).is_err());
    assert!(CaseFactSet::try_from_pairs(&[("bad id", true)]).is_err());
}

#[test]
fn missing_prerequisite_wins_before_algebra() {
    let rule = NormRule::try_new(
        NormRuleId::parse("rule:prereq").expect("id"),
        NormRuleRevision::parse("normrule:rev:p").expect("rev"),
        vec![NormRuleCondition::try_new("cond:a", "fact_required").expect("c")],
        vec![],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect("rule");
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true)]).expect("f");
    let evaluator = EvaluateApplicability::new();
    let request = ApplicabilityRequest {
        rule_id: rule.id().clone(),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("p"),
        case_facts_revision: CaseFactsRevision::parse("facts:v0").expect("f"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("pr"),
        prerequisites: PrerequisiteSnapshot::empty(),
    };
    let result = evaluator.evaluate_with_norm_rule_and_facts(request, &rule, &facts);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::MissingCtv)
    );
    // Algebra must not run past prerequisite gate.
    assert!(
        result
            .trace
            .predicate_steps
            .iter()
            .all(|s| !s.outcome.contains("algebra:satisfied")),
        "missing prerequisite must short-circuit algebra success claims"
    );
}

#[test]
fn satisfied_algebra_cannot_mint_applicable() {
    let rule = NormRule::try_new(
        NormRuleId::parse("rule:sat").expect("id"),
        NormRuleRevision::parse("normrule:rev:s").expect("rev"),
        vec![NormRuleCondition::try_new("cond:a", "fact_required").expect("c")],
        vec![],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect("rule");
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true)]).expect("f");
    let evaluator = EvaluateApplicability::new();
    let request = ApplicabilityRequest {
        rule_id: rule.id().clone(),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("p"),
        case_facts_revision: CaseFactsRevision::parse("facts:v0").expect("f"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("pr"),
        prerequisites: PrerequisiteSnapshot {
            ctv_present: true,
            normative_state_present: true,
            transitional_resolved: true,
            provenance_present: true,
        },
    };
    let result = evaluator.evaluate_with_norm_rule_and_facts(request, &rule, &facts);
    assert!(matches!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    ));
    assert!(!matches!(
        result.decision,
        ApplicabilityDecision::Applicable | ApplicabilityDecision::NotApplicable
    ));
}
