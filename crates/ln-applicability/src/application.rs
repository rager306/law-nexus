//! Application use case: evaluate case applicability fail-closed (ADR-0023).

use crate::domain::{
    compose_norm_rule_predicates, default_non_claims, first_prerequisite_abstention,
    AbstentionKind, ApplicabilityDecision, ApplicabilityRequest, ApplicabilityResult, CaseFactSet,
    ExplainableTrace, NormRule, PredicateOutcome, PredicateStep, PROTOCOL_VERSION,
};

/// Pure evaluator. No I/O. Never returns Applicable/NotApplicable in v0.
#[derive(Debug, Default, Clone, Copy)]
pub struct EvaluateApplicability;

impl EvaluateApplicability {
    pub fn new() -> Self {
        Self
    }

    pub fn evaluate(&self, request: ApplicabilityRequest) -> ApplicabilityResult {
        self.evaluate_inner(request, None, None)
    }

    /// IR-aware path without facts: structural IR observation + abstain only.
    pub fn evaluate_with_norm_rule(
        &self,
        request: ApplicabilityRequest,
        rule: &NormRule,
    ) -> ApplicabilityResult {
        self.evaluate_inner(request, Some(rule), None)
    }

    /// IR + synthetic facts: run pure predicate algebra, still top-level Abstain only.
    ///
    /// Algebra outcomes are recorded in the trace. Product Applicable/NotApplicable
    /// remains forbidden while lifecycle is `[proposed]` (RC11-F04b / ADR-0023).
    pub fn evaluate_with_norm_rule_and_facts(
        &self,
        request: ApplicabilityRequest,
        rule: &NormRule,
        facts: &CaseFactSet,
    ) -> ApplicabilityResult {
        self.evaluate_inner(request, Some(rule), Some(facts))
    }

    fn evaluate_inner(
        &self,
        request: ApplicabilityRequest,
        rule: Option<&NormRule>,
        facts: Option<&CaseFactSet>,
    ) -> ApplicabilityResult {
        if let Some(kind) = first_prerequisite_abstention(&request.prerequisites) {
            return self.finish(request, ApplicabilityDecision::Abstain(kind), Vec::new());
        }

        let mut predicate_steps = Vec::new();
        if let Some(rule) = rule {
            predicate_steps.push(PredicateStep {
                predicate_id: format!("norm_rule_ir:{}", rule.revision().as_str()),
                outcome: format!(
                    "ir_present_conditions={};exceptions={};defeaters={}",
                    rule.conditions().len(),
                    rule.exceptions().len(),
                    rule.defeaters().len()
                ),
            });

            if let Some(facts) = facts {
                let composed = compose_norm_rule_predicates(rule, facts);
                predicate_steps.extend(composed.steps);
                predicate_steps.push(PredicateStep {
                    predicate_id: "algebra:composed".to_owned(),
                    outcome: match composed.outcome {
                        PredicateOutcome::Satisfied => "algebra:satisfied".to_owned(),
                        PredicateOutcome::Unsatisfied => "algebra:unsatisfied".to_owned(),
                        PredicateOutcome::Abstain(kind) => {
                            format!("algebra:abstain:{}", kind.as_str())
                        }
                    },
                });
                // Algebra ran, but product decision stays ProtocolUnimplemented.
                // Mapping Satisfied/Unsatisfied → Applicable/NotApplicable is deferred.
            } else {
                predicate_steps.push(PredicateStep {
                    predicate_id: "algebra:skipped".to_owned(),
                    outcome: "no_case_facts_supplied".to_owned(),
                });
            }
        }

        self.finish(
            request,
            ApplicabilityDecision::Abstain(AbstentionKind::ProtocolUnimplemented),
            predicate_steps,
        )
    }

    fn finish(
        &self,
        request: ApplicabilityRequest,
        decision: ApplicabilityDecision,
        predicate_steps: Vec<PredicateStep>,
    ) -> ApplicabilityResult {
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
