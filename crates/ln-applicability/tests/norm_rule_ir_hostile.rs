//! Hostile NormRule IR and evaluator non-claim guards (RC11-F04a).
//!
//! Valid IR + complete prerequisites must still abstain. Positive decisions
//! remain forbidden under ADR-0023 [proposed].

use ln_applicability::application::EvaluateApplicability;
use ln_applicability::domain::{
    AbstentionKind, ApplicabilityDecision, ApplicabilityRequest, CaseFactsRevision, Defeater,
    Exception, NormRule, NormRuleCondition, NormRuleId, NormRuleIrError, NormRuleRevision,
    PredicateRegistryRevision, PrerequisiteSnapshot, ProfileInputRevision, TemporalScope,
};

fn complete_prereqs() -> PrerequisiteSnapshot {
    PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: true,
        transitional_resolved: true,
        provenance_present: true,
    }
}

fn valid_ir() -> NormRule {
    NormRule::try_new(
        NormRuleId::parse("rule:hostile:demo").expect("id"),
        NormRuleRevision::parse("normrule:rev:hostile").expect("rev"),
        vec![NormRuleCondition::try_new("cond:subject", "fact_required").expect("cond")],
        vec![Exception::try_new("exc:carve", "carve_out").expect("exc")],
        vec![Defeater::try_new("def:special", "special_norm_defeats").expect("def")],
        TemporalScope::try_new(Some("2024-01-01"), None).expect("scope"),
    )
    .expect("valid ir")
}

#[test]
fn valid_ir_with_complete_prerequisites_still_abstains() {
    let rule = valid_ir();
    // IR is constructed and inspected so the design spine is exercised, but the
    // v0 evaluator remains abstention-only (no IR evaluation algebra yet).
    assert!(!rule.conditions().is_empty());
    assert_eq!(rule.exceptions().len(), 1);
    assert_eq!(rule.defeaters().len(), 1);

    let evaluator = EvaluateApplicability::new();
    let request = ApplicabilityRequest {
        rule_id: rule.id().clone(),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("pred"),
        case_facts_revision: CaseFactsRevision::parse("facts:synthetic").expect("facts"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("profile"),
        prerequisites: complete_prereqs(),
    };
    let result = evaluator.evaluate(request);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    );
    assert!(
        !matches!(
            result.decision,
            ApplicabilityDecision::Applicable | ApplicabilityDecision::NotApplicable
        ),
        "IR presence must not mint positive applicability"
    );
    assert!(
        result
            .trace
            .non_claims
            .iter()
            .any(|c| c.contains("NormRule IR") || c.contains("structural design")),
        "trace non-claims must mention NormRule IR design boundary"
    );
}

#[test]
fn evaluate_with_norm_rule_records_ir_and_still_abstains() {
    let rule = valid_ir();
    let evaluator = EvaluateApplicability::new();
    let request = ApplicabilityRequest {
        rule_id: rule.id().clone(),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("pred"),
        case_facts_revision: CaseFactsRevision::parse("facts:synthetic").expect("facts"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("profile"),
        prerequisites: complete_prereqs(),
    };
    let result = evaluator.evaluate_with_norm_rule(request, &rule);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    );
    assert_eq!(result.trace.predicate_steps.len(), 1);
    assert!(
        result.trace.predicate_steps[0]
            .predicate_id
            .starts_with("norm_rule_ir:"),
        "trace must mark IR revision structurally"
    );
    assert!(
        result.trace.predicate_steps[0]
            .outcome
            .contains("abstain_only"),
        "IR observation must not claim evaluation success"
    );
    assert!(!matches!(
        result.decision,
        ApplicabilityDecision::Applicable | ApplicabilityDecision::NotApplicable
    ));
}

#[test]
fn unsupported_exception_kind_fails_closed() {
    let err = Exception::try_new("exc:x", "llm_invented_exception").expect_err("kind");
    assert!(matches!(err, NormRuleIrError::UnsupportedExceptionKind));
}

#[test]
fn unsupported_defeater_kind_fails_closed() {
    let err = Defeater::try_new("def:x", "profile_local_magic").expect_err("kind");
    assert!(matches!(err, NormRuleIrError::UnsupportedDefeaterKind));
}

#[test]
fn blank_rule_revision_fails_closed() {
    assert!(NormRuleRevision::parse("").is_err());
    assert!(NormRuleRevision::parse("bad revision spaces").is_err());
}

#[test]
fn ir_cannot_be_built_from_only_exceptions_without_conditions() {
    let err = NormRule::try_new(
        NormRuleId::parse("rule:no-cond").expect("id"),
        NormRuleRevision::parse("normrule:rev:x").expect("rev"),
        vec![],
        vec![Exception::try_new("exc:only", "exception_clause").expect("exc")],
        vec![],
        TemporalScope::unbounded(),
    )
    .expect_err("conditions required");
    assert!(matches!(err, NormRuleIrError::EmptyConditions));
}
