use std::collections::{HashMap, HashSet, VecDeque};

use crate::domain::{
    ClosureRequest, ClosureResult, ClosureStatus, ClosureTrace, NodeId, PublicationEligibility,
    CLOSURE_POLICY_VERSION, MAX_BOUNDED_FANOUT,
};
use crate::ports::DependencyEvidencePort;

/// Inward dependency policy for Compute Dependency Closure (HC-11).
/// Owns completeness and publication eligibility. Freezes registered-node
/// evidence at compute start so hostile re-reads and invented unregistered
/// edges cannot force complete. Progress/queue depth are never completeness.
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

        // Freeze registered evidence once. Hostile later invents are ignored.
        let frozen_version = self.evidence.rule_version();
        let mut frozen_registered: HashSet<String> = HashSet::new();
        let mut frozen_deps: HashMap<String, Vec<NodeId>> = HashMap::new();
        for node in self.evidence.registered_nodes() {
            frozen_registered.insert(node.as_str().to_owned());
            if let Some(deps) = self.evidence.dependencies_of(&node) {
                frozen_deps.insert(node.as_str().to_owned(), deps);
            } else {
                frozen_deps.insert(node.as_str().to_owned(), Vec::new());
            }
        }
        // Observe progress/queue only to prove they are unused.
        let _progress = self.evidence.progress_count();
        let _queue = self.evidence.queue_depth();

        if frozen_version != request.expected_rule_version {
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

        let mut affected: Vec<NodeId> = Vec::new();
        let mut missing: Vec<NodeId> = Vec::new();
        let stale: Vec<NodeId> = Vec::new();
        let mut seen: HashSet<String> = HashSet::new();
        let mut queue: VecDeque<NodeId> = VecDeque::new();
        let mut unknown_seed = false;

        for node in &request.changed {
            if !frozen_registered.contains(node.as_str()) {
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

            if !frozen_registered.contains(node.as_str()) {
                // Unregistered non-seed already counted as missing; do not expand.
                if !request.changed.iter().any(|c| c == &node)
                    && !missing.iter().any(|n| n == &node)
                {
                    missing.push(node.clone());
                }
                continue;
            }

            let deps = frozen_deps.get(node.as_str()).cloned().unwrap_or_default();

            for dep in deps {
                if !seen.contains(dep.as_str()) {
                    if !frozen_registered.contains(dep.as_str()) {
                        if !missing.iter().any(|n| n == &dep) {
                            missing.push(dep.clone());
                        }
                        // Do not expand inventively beyond frozen registry.
                        continue;
                    }
                    queue.push_back(dep);
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
        self.finish(
            request,
            ClosureStatus::Complete,
            PublicationEligibility::Eligible,
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
