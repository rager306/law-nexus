//! Application use case: evaluate case applicability fail-closed (ADR-0023).

use crate::domain::{
    default_non_claims, first_prerequisite_abstention, AbstentionKind, ApplicabilityDecision,
    ApplicabilityRequest, ApplicabilityResult, ExplainableTrace, NormRule, PredicateStep,
    PROTOCOL_VERSION,
};

/// Pure evaluator. No I/O. Never returns Applicable/NotApplicable in v0.
#[derive(Debug, Default, Clone, Copy)]
pub struct EvaluateApplicability;

impl EvaluateApplicability {
    pub fn new() -> Self {
        Self
    }

    pub fn evaluate(&self, request: ApplicabilityRequest) -> ApplicabilityResult {
        self.evaluate_inner(request, None)
    }

    /// IR-aware path: records NormRule identity/revision structurally, still only abstains.
    ///
    /// Presence of validated IR is not an applicability decision (RC11-F04a / ADR-0023).
    pub fn evaluate_with_norm_rule(
        &self,
        request: ApplicabilityRequest,
        rule: &NormRule,
    ) -> ApplicabilityResult {
        self.evaluate_inner(request, Some(rule))
    }

    fn evaluate_inner(
        &self,
        request: ApplicabilityRequest,
        rule: Option<&NormRule>,
    ) -> ApplicabilityResult {
        let kind = first_prerequisite_abstention(&request.prerequisites)
            .unwrap_or(AbstentionKind::ProtocolUnimplemented);
        let decision = ApplicabilityDecision::Abstain(kind);
        let mut predicate_steps = Vec::new();
        if let Some(rule) = rule {
            // Structural observation only — not predicate algebra evaluation.
            predicate_steps.push(PredicateStep {
                predicate_id: format!("norm_rule_ir:{}", rule.revision().as_str()),
                outcome: format!(
                    "ir_present_conditions={};exceptions={};defeaters={};abstain_only",
                    rule.conditions().len(),
                    rule.exceptions().len(),
                    rule.defeaters().len()
                ),
            });
        }
        let trace = ExplainableTrace {
            protocol_version: PROTOCOL_VERSION.to_owned(),
            rule_id: request.rule_id.clone(),
            predicate_registry_revision: request.predicate_registry_revision.clone(),
            case_facts_revision: request.case_facts_revision.clone(),
            profile_input_revision: request.profile_input_revision.clone(),
            prerequisites: request.prerequisites,
            predicate_steps,
            decision,
            non_claims: default_non_claims(),
        };
        ApplicabilityResult { decision, trace }
    }
}
