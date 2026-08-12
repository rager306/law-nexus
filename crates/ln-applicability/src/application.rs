//! Application use case: evaluate case applicability fail-closed (ADR-0023).

use crate::domain::{
    default_non_claims, first_prerequisite_abstention, AbstentionKind, ApplicabilityDecision,
    ApplicabilityRequest, ApplicabilityResult, ExplainableTrace, PROTOCOL_VERSION,
};

/// Pure evaluator. No I/O. Never returns Applicable/NotApplicable in v0.
#[derive(Debug, Default, Clone, Copy)]
pub struct EvaluateApplicability;

impl EvaluateApplicability {
    pub fn new() -> Self {
        Self
    }

    pub fn evaluate(&self, request: ApplicabilityRequest) -> ApplicabilityResult {
        let kind = first_prerequisite_abstention(&request.prerequisites)
            .unwrap_or(AbstentionKind::ProtocolUnimplemented);
        let decision = ApplicabilityDecision::Abstain(kind);
        let trace = ExplainableTrace {
            protocol_version: PROTOCOL_VERSION.to_owned(),
            rule_id: request.rule_id.clone(),
            predicate_registry_revision: request.predicate_registry_revision.clone(),
            case_facts_revision: request.case_facts_revision.clone(),
            profile_input_revision: request.profile_input_revision.clone(),
            prerequisites: request.prerequisites,
            predicate_steps: Vec::new(),
            decision,
            non_claims: default_non_claims(),
        };
        ApplicabilityResult { decision, trace }
    }
}
