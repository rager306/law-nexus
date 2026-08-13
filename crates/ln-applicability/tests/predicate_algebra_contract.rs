//! Contract tests for fail-closed predicate algebra over NormRule IR (RC11-F04b).
//!
//! Algebra outcomes are structural/compositional only. Top-level product decision
//! remains Abstain under ADR-0023 [proposed] — never Applicable/NotApplicable.

use ln_applicability::application::EvaluateApplicability;
use ln_applicability::domain::{
    compose_norm_rule_predicates, evaluate_condition, AbstentionKind, ApplicabilityDecision,
    ApplicabilityRequest, CaseFactSet, CaseFactsRevision, Defeater, Exception, NormRule,
    NormRuleCondition, NormRuleId, NormRuleRevision, PredicateOutcome, PredicateRegistryRevision,
    PrerequisiteSnapshot, ProfileInputRevision, TemporalScope,
};

fn complete_prereqs() -> PrerequisiteSnapshot {
    PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: true,
        transitional_resolved: true,
        provenance_present: true,
    }
}

fn base_rule(conditions: Vec<NormRuleCondition>) -> NormRule {
    NormRule::try_new(
        NormRuleId::parse("rule:algebra:demo").expect("id"),
        NormRuleRevision::parse("normrule:rev:algebra").expect("rev"),
        conditions,
        vec![],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect("rule")
}

#[test]
fn fact_required_satisfied_when_present() {
    let cond = NormRuleCondition::try_new("cond:subject", "fact_required").expect("c");
    let facts = CaseFactSet::try_from_pairs(&[("cond:subject", true)]).expect("facts");
    assert_eq!(
        evaluate_condition(&cond, &facts),
        PredicateOutcome::Satisfied
    );
}

#[test]
fn fact_required_abstains_when_missing() {
    let cond = NormRuleCondition::try_new("cond:subject", "fact_required").expect("c");
    let facts = CaseFactSet::empty();
    assert_eq!(
        evaluate_condition(&cond, &facts),
        PredicateOutcome::Abstain(AbstentionKind::MissingOrAmbiguousFacts)
    );
}

#[test]
fn fact_forbidden_unsatisfied_when_present() {
    let cond = NormRuleCondition::try_new("cond:banned", "fact_forbidden").expect("c");
    let facts = CaseFactSet::try_from_pairs(&[("cond:banned", true)]).expect("facts");
    assert_eq!(
        evaluate_condition(&cond, &facts),
        PredicateOutcome::Unsatisfied
    );
}

#[test]
fn compose_all_conditions_satisfied() {
    let rule = base_rule(vec![
        NormRuleCondition::try_new("cond:a", "fact_required").expect("a"),
        NormRuleCondition::try_new("cond:b", "fact_required").expect("b"),
    ]);
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true), ("cond:b", true)]).expect("f");
    let composed = compose_norm_rule_predicates(&rule, &facts);
    assert_eq!(composed.outcome, PredicateOutcome::Satisfied);
    assert_eq!(composed.steps.len(), 2);
}

#[test]
fn compose_propagates_missing_fact_abstention() {
    let rule = base_rule(vec![
        NormRuleCondition::try_new("cond:a", "fact_required").expect("a"),
        NormRuleCondition::try_new("cond:b", "fact_required").expect("b"),
    ]);
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true)]).expect("f");
    let composed = compose_norm_rule_predicates(&rule, &facts);
    assert_eq!(
        composed.outcome,
        PredicateOutcome::Abstain(AbstentionKind::MissingOrAmbiguousFacts)
    );
}

#[test]
fn exception_can_carve_out_unsatisfied_condition() {
    // fact_forbidden present => condition Unsatisfied; carve_out exception fact true => Satisfied.
    let rule = NormRule::try_new(
        NormRuleId::parse("rule:carve").expect("id"),
        NormRuleRevision::parse("normrule:rev:carve").expect("rev"),
        vec![NormRuleCondition::try_new("cond:banned", "fact_forbidden").expect("c")],
        vec![Exception::try_new("exc:small", "carve_out").expect("e")],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect("rule");
    let facts =
        CaseFactSet::try_from_pairs(&[("cond:banned", true), ("exc:small", true)]).expect("f");
    let composed = compose_norm_rule_predicates(&rule, &facts);
    assert_eq!(composed.outcome, PredicateOutcome::Satisfied);
}

#[test]
fn defeater_forces_unsatisfied_when_triggered() {
    let rule = NormRule::try_new(
        NormRuleId::parse("rule:def").expect("id"),
        NormRuleRevision::parse("normrule:rev:def").expect("rev"),
        vec![NormRuleCondition::try_new("cond:a", "fact_required").expect("c")],
        vec![],
        vec![Defeater::try_new("def:special", "special_norm_defeats").expect("d")],
        TemporalScope::unbounded(),
    )
    .expect("rule");
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true), ("def:special", true)]).expect("f");
    let composed = compose_norm_rule_predicates(&rule, &facts);
    assert_eq!(composed.outcome, PredicateOutcome::Unsatisfied);
}

#[test]
fn evaluate_with_norm_rule_and_facts_still_never_applicable() {
    let rule = base_rule(vec![
        NormRuleCondition::try_new("cond:a", "fact_required").expect("a")
    ]);
    let facts = CaseFactSet::try_from_pairs(&[("cond:a", true)]).expect("f");
    let evaluator = EvaluateApplicability::new();
    let request = ApplicabilityRequest {
        rule_id: rule.id().clone(),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("p"),
        case_facts_revision: CaseFactsRevision::parse("facts:v0").expect("f"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("pr"),
        prerequisites: complete_prereqs(),
    };
    let result = evaluator.evaluate_with_norm_rule_and_facts(request, &rule, &facts);
    assert!(
        !matches!(
            result.decision,
            ApplicabilityDecision::Applicable | ApplicabilityDecision::NotApplicable
        ),
        "algebra must not mint product Applicable/NotApplicable under [proposed]"
    );
    assert!(matches!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    ));
    assert!(
        result
            .trace
            .predicate_steps
            .iter()
            .any(|s| s.outcome.contains("algebra:") || s.predicate_id.starts_with("cond:")),
        "trace must record algebra steps"
    );
}
