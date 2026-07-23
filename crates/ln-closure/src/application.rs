use std::collections::{HashSet, VecDeque};

use crate::domain::{
    ClosureRequest, ClosureResult, ClosureStatus, ClosureTrace, NodeId, PublicationEligibility,
    CLOSURE_POLICY_VERSION, MAX_BOUNDED_FANOUT,
};
use crate::ports::DependencyEvidencePort;

/// Inward dependency policy for Compute Dependency Closure (HC-11).
/// Owns completeness and publication eligibility. Progress/queue depth and
/// hostile invented edges cannot force complete or eligible publication.
pub struct ComputeDependencyClosure<E> {
    evidence: E,
}

impl<E> ComputeDependencyClosure<E>
where
    E: DependencyEvidencePort,
{
    pub fn new(evidence: E) -> Self {
        Self { evidence }
    }

    pub fn compute(&self, request: ClosureRequest) -> ClosureResult {
        // Forbidden completeness claims never apply and always block.
        if request.completeness_claim.is_forbidden() {
            let claimed_missing = request.changed.clone();
            return self.finish(
                request,
                ClosureStatus::Incomplete,
                PublicationEligibility::Blocked,
                Vec::new(),
                claimed_missing,
                Vec::new(),
                false,
                false,
                false,
            );
        }

        let observed = self.evidence.rule_version();
        if observed != request.expected_rule_version {
            return self.finish(
                request,
                ClosureStatus::RuleVersionMismatch,
                PublicationEligibility::Blocked,
                Vec::new(),
                Vec::new(),
                Vec::new(),
                false,
                false,
                false,
            );
        }

        // Progress/queue are observed only to prove they are unused.
        let _progress = self.evidence.progress_count();
        let _queue = self.evidence.queue_depth();

        let mut affected: Vec<NodeId> = Vec::new();
        let mut missing: Vec<NodeId> = Vec::new();
        let mut stale: Vec<NodeId> = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();
        let mut queue: VecDeque<NodeId> = VecDeque::new();
        let mut unknown_seed = false;

        for node in &request.changed {
            // Seed/changed nodes without any evidence record are unknown.
            if self.evidence.dependencies_of(node).is_none() && !self.evidence.known(node) {
                unknown_seed = true;
                if !missing.iter().any(|n| n == node) {
                    missing.push(node.clone());
                }
            }
            queue.push_back(node.clone());
        }

        while let Some(node) = queue.pop_front() {
            if !seen.insert(node.as_str().to_owned()) {
                continue;
            }
            affected.push(node.clone());

            if affected.len() > MAX_BOUNDED_FANOUT {
                return self.finish(
                    request,
                    ClosureStatus::Unbounded,
                    PublicationEligibility::Blocked,
                    affected,
                    missing,
                    stale,
                    false,
                    false,
                    false,
                );
            }

            match self.evidence.dependencies_of(&node) {
                None => {
                    // Non-seed missing targets are incomplete, not unknown.
                    // Seed unknown already recorded above.
                    if !request.changed.iter().any(|c| c == &node)
                        && !missing.iter().any(|n| n == &node)
                    {
                        missing.push(node.clone());
                    }
                }
                Some(deps) => {
                    if !self.evidence.known(&node) {
                        stale.push(node.clone());
                    }
                    for dep in deps {
                        if !seen.contains(dep.as_str()) {
                            // Referenced dependency with no evidence → incomplete.
                            if self.evidence.dependencies_of(&dep).is_none()
                                && !self.evidence.known(&dep)
                            {
                                if !missing.iter().any(|n| n == &dep) {
                                    missing.push(dep.clone());
                                }
                                // Do not expand inventively; record missing only.
                                continue;
                            }
                            queue.push_back(dep);
                        }
                    }
                }
            }
        }

        if unknown_seed {
            return self.finish(
                request,
                ClosureStatus::Unknown,
                PublicationEligibility::Blocked,
                affected,
                missing,
                stale,
                false,
                false,
                false,
            );
        }

        if !missing.is_empty() {
            return self.finish(
                request,
                ClosureStatus::Incomplete,
                PublicationEligibility::Blocked,
                affected,
                missing,
                stale,
                false,
                false,
                false,
            );
        }

        // Fully evidenced, bounded, matching rules → complete.
        // Incremental authoritative publication is eligible only then.
        let eligibility = if request.request_incremental_publication {
            PublicationEligibility::Eligible
        } else {
            // Still complete; eligibility for publication only when requested.
            PublicationEligibility::Eligible
        };

        self.finish(
            request,
            ClosureStatus::Complete,
            eligibility,
            affected,
            missing,
            stale,
            false,
            false,
            false,
        )
    }

    #[allow(clippy::too_many_arguments)]
    fn finish(
        &self,
        request: ClosureRequest,
        status: ClosureStatus,
        publication_eligibility: PublicationEligibility,
        affected: Vec<NodeId>,
        missing: Vec<NodeId>,
        stale: Vec<NodeId>,
        completeness_claim_applied: bool,
        progress_used: bool,
        queue_used: bool,
    ) -> ClosureResult {
        // Non-complete statuses always block publication.
        let publication_eligibility = if status.is_complete() {
            publication_eligibility
        } else {
            PublicationEligibility::Blocked
        };

        let fanout = affected.len();
        let observed = self.evidence.rule_version();
        let trace = ClosureTrace {
            policy_version: CLOSURE_POLICY_VERSION.to_owned(),
            request_id: request.request_id.clone(),
            status,
            publication_eligibility,
            changed: request.changed.clone(),
            affected: affected.clone(),
            missing: missing.clone(),
            stale: stale.clone(),
            observed_rule_version: Some(observed),
            expected_rule_version: request.expected_rule_version.clone(),
            completeness_claim: request.completeness_claim,
            completeness_claim_applied,
            progress_used_as_completeness: progress_used,
            queue_depth_used_as_completeness: queue_used,
            fanout,
        };

        ClosureResult {
            status,
            publication_eligibility,
            changed: request.changed,
            affected,
            missing,
            stale,
            completeness_claim_applied,
            progress_used_as_completeness: progress_used,
            queue_depth_used_as_completeness: queue_used,
            trace,
        }
    }
}
