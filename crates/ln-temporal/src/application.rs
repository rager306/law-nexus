use crate::domain::{
    DecisionTrace, ResolutionOutcome, ResolutionRequest, ResolutionResult, SubstituteKind,
    D118_POLICY_VERSION,
};
use crate::ports::ClockEvidencePort;

/// D118 domain temporal policy. Family rules are evidence inputs only.
/// Application, adapters and wall-clock cannot own or substitute shared clocks.
pub struct ResolveFiveClockState<E> {
    evidence: E,
}

impl<E> ResolveFiveClockState<E>
where
    E: ClockEvidencePort,
{
    pub fn new(evidence: E) -> Self {
        Self { evidence }
    }

    pub fn resolve(&self, request: ResolutionRequest) -> ResolutionResult {
        let governing_anchor = self.evidence.anchor_for(request.governing_clock);
        let considered: Vec<String> = request
            .attempted_substitutes
            .iter()
            .map(|s| s.as_str())
            .collect();

        if let Some(anchor) = governing_anchor {
            // Governing anchor present: resolve without substitution.
            // Any attempted substitutes are still recorded as considered but unused.
            return ResolutionResult {
                outcome: ResolutionOutcome::Resolved,
                governing_clock: request.governing_clock,
                resolved_anchor: Some(anchor.clone()),
                substitution_used: false,
                trace: DecisionTrace {
                    policy_version: D118_POLICY_VERSION.to_owned(),
                    governing_clock: request.governing_clock,
                    governing_anchor: Some(anchor),
                    considered_substitutes: considered,
                    rejected_substitutes: Vec::new(),
                },
            };
        }

        // Missing governing anchor: every non-governing substitute is rejected.
        let rejected: Vec<String> = request
            .attempted_substitutes
            .iter()
            .filter(|s| !is_governing_identity(**s, request.governing_clock))
            .map(|s| s.as_str())
            .collect();

        let outcome = if rejected.is_empty() {
            ResolutionOutcome::MissingAnchor
        } else {
            ResolutionOutcome::SubstituteRejected
        };

        ResolutionResult {
            outcome,
            governing_clock: request.governing_clock,
            resolved_anchor: None,
            substitution_used: false,
            trace: DecisionTrace {
                policy_version: D118_POLICY_VERSION.to_owned(),
                governing_clock: request.governing_clock,
                governing_anchor: None,
                considered_substitutes: considered,
                rejected_substitutes: rejected,
            },
        }
    }
}

fn is_governing_identity(substitute: SubstituteKind, governing: crate::domain::ClockKind) -> bool {
    matches!(substitute, SubstituteKind::OtherClock(clock) if clock == governing)
}
