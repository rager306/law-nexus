//! Domain semantic contracts for the fail-closed applicability protocol (ADR-0023).
//!
//! Lifecycle [proposed]/ no Applicable/NotApplicable product claim exists yet.
//! Every evaluation must abstain with an explicit kind and mandatory trace.

use ln_applicability::application::EvaluateApplicability;
use ln_applicability::domain::{
    AbstentionKind, ApplicabilityDecision, ApplicabilityRequest, CaseFactsRevision, NormRuleId,
    PredicateRegistryRevision, PrerequisiteSnapshot, ProfileInputRevision, PROTOCOL_VERSION,
};

fn request(rule: &str) -> ApplicabilityRequest {
    ApplicabilityRequest {
        rule_id: NormRuleId::parse(rule).expect("rule"),
        predicate_registry_revision: PredicateRegistryRevision::parse("pred:v0").expect("pred"),
        case_facts_revision: CaseFactsRevision::parse("facts:missing").expect("facts"),
        profile_input_revision: ProfileInputRevision::parse("profile:none").expect("profile"),
        prerequisites: PrerequisiteSnapshot::empty(),
    }
}

#[test]
fn empty_prerequisites_abstain_missing_ctv_with_trace() {
    let evaluator = EvaluateApplicability::new();
    let result = evaluator.evaluate(request("rule:demo"));

    match result.decision {
        ApplicabilityDecision::Abstain(kind) => {
            assert_eq!(kind, AbstentionKind::MissingCtv);
        }
        other => panic!("expected abstain, got {other:?}"),
    }
    assert_eq!(result.trace.protocol_version, PROTOCOL_VERSION);
    assert_eq!(result.trace.rule_id.as_str(), "rule:demo");
    assert!(!result.trace.non_claims.is_empty());
    assert!(
        result
            .trace
            .non_claims
            .iter()
            .any(|c| c.contains("not Applicable") || c.contains("not product readiness")),
        "trace must carry explicit non-claims"
    );
}

#[test]
fn missing_normative_state_abstains_before_positive_decision() {
    let evaluator = EvaluateApplicability::new();
    let mut req = request("rule:ns");
    req.prerequisites = PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: false,
        transitional_resolved: true,
        provenance_present: true,
    };
    let result = evaluator.evaluate(req);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::MissingNormativeState)
    );
}

#[test]
fn unresolved_transitional_version_abstains() {
    let evaluator = EvaluateApplicability::new();
    let mut req = request("rule:tr");
    req.prerequisites = PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: true,
        transitional_resolved: false,
        provenance_present: true,
    };
    let result = evaluator.evaluate(req);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::UnresolvedTransitional)
    );
}

#[test]
fn missing_provenance_abstains() {
    let evaluator = EvaluateApplicability::new();
    let mut req = request("rule:prov");
    req.prerequisites = PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: true,
        transitional_resolved: true,
        provenance_present: false,
    };
    let result = evaluator.evaluate(req);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::MissingProvenance)
    );
}

#[test]
fn complete_prerequisites_still_abstain_protocol_unimplemented() {
    // ADR-0023: while [proposed], no positive applicability claim exists.
    // Even with complete prerequisite flags, the protocol remains abstention-only
    // until predicate algebra and real proof land.
    let evaluator = EvaluateApplicability::new();
    let mut req = request("rule:complete");
    req.prerequisites = PrerequisiteSnapshot {
        ctv_present: true,
        normative_state_present: true,
        transitional_resolved: true,
        provenance_present: true,
    };
    let result = evaluator.evaluate(req);
    assert_eq!(
        result.decision,
        ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented)
    );
    assert!(result.trace.predicate_steps.is_empty());
}

#[test]
fn invalid_rule_id_fails_closed() {
    assert!(NormRuleId::parse("").is_err());
    assert!(NormRuleId::parse("bad id with spaces").is_err());
}

#[test]
fn applicable_and_not_applicable_constructors_are_not_exposed_as_success_paths() {
    // Guard against accidental product success smoothing: the only public
    // decision surface used by EvaluateApplicability is Abstain for now.
    let evaluator = EvaluateApplicability::new();
    let result = evaluator.evaluate(request("rule:no-success"));
    assert!(matches!(result.decision, ApplicabilityDecision::Abstain(_)));
    assert!(!matches!(
        result.decision,
        ApplicabilityDecision::Applicable | ApplicabilityDecision::NotApplicable
    ));
}
