use crate::domain::{
    CeilingMetadata, CompletenessLabel, CurrencyLabel, ExecutorReport, NodeId, RebuildOutcome,
    RebuildRequest, RebuildResult, RebuildTrace, PROJECTION_POLICY_VERSION,
};
use crate::ports::RebuildExecutorPort;

/// Outward projection rebuild policy (HC-12).
/// Owns non-authoritative ceiling metadata and forbids Publication Authority
/// effects. Executor labels for complete/current/authoritative are demoted.
pub struct RebuildDisposableProjection<E> {
    executor: E,
}

impl<E> RebuildDisposableProjection<E>
where
    E: RebuildExecutorPort,
{
    pub fn new(executor: E) -> Self {
        Self { executor }
    }

    pub fn rebuild(&self, request: RebuildRequest) -> RebuildResult {
        let report = self.executor.execute(&request);
        let demoted = report.claims_complete
            || report.claims_current
            || report.claims_authoritative
            || report.invents_fact
            || report.hides_gaps
            || report.publication_authority_granted;

        let outcome = normalize_outcome(&report, demoted);
        let gaps = merge_gaps(&request.known_gaps, &report);
        let stale = report.extra_stale.clone();

        let ceiling = CeilingMetadata {
            // Always non-authoritative on this path.
            authoritative: false,
            completeness: CompletenessLabel::Incomplete,
            currency: CurrencyLabel::NotCurrent,
            baseline: request.baseline.clone(),
            scope: request.scope.clone(),
            cutoff: request.cutoff.clone(),
            rules: request.rules.clone(),
            stale,
            gaps,
        };

        // Publication authority never granted or changed by rebuild.
        let publication_authority = None;
        let publication_authority_changed = false;

        let trace = RebuildTrace {
            policy_version: PROJECTION_POLICY_VERSION.to_owned(),
            request_id: request.request_id.clone(),
            outcome,
            ceiling: ceiling.clone(),
            publication_authority,
            publication_authority_changed,
            executor_claimed_complete: report.claims_complete,
            executor_claimed_current: report.claims_current,
            executor_claimed_authoritative: report.claims_authoritative,
            executor_invented_fact: report.invents_fact,
            executor_hid_gaps: report.hides_gaps,
            demoted,
        };

        RebuildResult {
            outcome,
            ceiling,
            publication_authority,
            publication_authority_changed,
            demoted,
            trace,
        }
    }
}

fn normalize_outcome(report: &ExecutorReport, demoted: bool) -> RebuildOutcome {
    // Hostile success claims become failed disposable path, not authority.
    if demoted && matches!(report.outcome, RebuildOutcome::RebuiltDisposable) {
        return RebuildOutcome::Failed;
    }
    match report.outcome {
        RebuildOutcome::RebuiltDisposable
        | RebuildOutcome::Partial
        | RebuildOutcome::StaleInput
        | RebuildOutcome::Cancelled
        | RebuildOutcome::Failed => report.outcome,
    }
}

fn merge_gaps(known: &[NodeId], report: &ExecutorReport) -> Vec<NodeId> {
    // Gaps cannot be hidden: always preserve known request gaps plus residual.
    let mut out = known.to_vec();
    if !report.hides_gaps {
        for g in &report.residual_gaps {
            if !out.iter().any(|n| n == g) {
                out.push(g.clone());
            }
        }
    } else {
        // Hostile hid gaps: still keep known request gaps; do not trust empty residual.
        for g in known {
            if !out.iter().any(|n| n == g) {
                out.push(g.clone());
            }
        }
    }
    out
}
