use crate::domain::{ExecutorReport, NodeId, RebuildOutcome, RebuildRequest};
use crate::ports::RebuildExecutorPort;

/// Honest executor that reports the configured failure/partial mode without
/// claiming authority.
#[derive(Debug, Clone)]
pub struct HonestExecutor {
    pub outcome: RebuildOutcome,
    pub residual_gaps: Vec<NodeId>,
    pub extra_stale: Vec<NodeId>,
}

impl RebuildExecutorPort for HonestExecutor {
    fn execute(&self, request: &RebuildRequest) -> ExecutorReport {
        let mut residual = self.residual_gaps.clone();
        if residual.is_empty() {
            residual = request.known_gaps.clone();
        }
        ExecutorReport {
            outcome: self.outcome,
            claims_complete: false,
            claims_current: false,
            claims_authoritative: false,
            invents_fact: false,
            hides_gaps: false,
            publication_authority_granted: false,
            extra_stale: self.extra_stale.clone(),
            residual_gaps: residual,
        }
    }
}

/// Hostile executor that claims complete/current/authoritative, invents facts,
/// hides gaps and tries to mint publication authority.
#[derive(Debug, Clone)]
pub struct HostileAuthoritativeExecutor {
    pub base_outcome: RebuildOutcome,
}

impl RebuildExecutorPort for HostileAuthoritativeExecutor {
    fn execute(&self, request: &RebuildRequest) -> ExecutorReport {
        let _ = request;
        ExecutorReport {
            outcome: self.base_outcome,
            claims_complete: true,
            claims_current: true,
            claims_authoritative: true,
            invents_fact: true,
            hides_gaps: true,
            publication_authority_granted: true,
            extra_stale: Vec::new(),
            residual_gaps: Vec::new(), // hides request.known_gaps
        }
    }
}
