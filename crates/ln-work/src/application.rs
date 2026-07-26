use std::collections::HashMap;

use crate::domain::{
    next_state, CheckpointId, DomainSnapshotId, LegalMappingAttempt, PublicationSnapshotId,
    TransitionOutcome, TransitionRequest, TransitionResult, TransitionTrace, WorkState, WorkUnitId,
    WORK_POLICY_VERSION,
};
use crate::ports::DomainEvidencePort;

#[derive(Debug, Clone)]
struct WorkRecord {
    state: WorkState,
    checkpoint: CheckpointId,
    /// Application-owned freeze of domain identity at unit creation.
    domain_snapshot: DomainSnapshotId,
    /// Application-owned freeze of publication identity at unit creation.
    publication_snapshot: PublicationSnapshotId,
    checkpoint_seq: u64,
}

/// Application processing policy for Transition Work State (HC-10).
/// Owns work transitions only. Domain/publication identities are frozen at
/// open and never rewritten by cancel/resume/progress. Forbidden legal-mapping
/// attempts are rejected without applying domain mutation.
pub struct TransitionWorkState<E> {
    evidence: E,
    units: HashMap<String, WorkRecord>,
}

impl<E> TransitionWorkState<E>
where
    E: DomainEvidencePort,
{
    pub fn new(evidence: E) -> Self {
        Self {
            evidence,
            units: HashMap::new(),
        }
    }

    /// Open a work unit in Requested with frozen domain/publication snapshots.
    pub fn open(&mut self, work_unit_id: WorkUnitId) -> TransitionResult {
        let domain = self.evidence.domain_snapshot(&work_unit_id);
        let publication = self.evidence.publication_snapshot(&work_unit_id);
        let checkpoint = CheckpointId::parse("cp:0").expect("static id");
        let record = WorkRecord {
            state: WorkState::Requested,
            checkpoint: checkpoint.clone(),
            domain_snapshot: domain.clone(),
            publication_snapshot: publication.clone(),
            checkpoint_seq: 0,
        };
        self.units
            .insert(work_unit_id.as_str().to_owned(), record.clone());
        self.result_for(
            work_unit_id,
            crate::domain::WorkEvent::Start,
            TransitionOutcome::Transitioned,
            WorkState::Requested,
            WorkState::Requested,
            &record,
            &record,
            LegalMappingAttempt::None,
            false,
            checkpoint.clone(),
            checkpoint,
        )
    }

    pub fn state_of(&self, work_unit_id: &WorkUnitId) -> Option<WorkState> {
        self.units.get(work_unit_id.as_str()).map(|r| r.state)
    }

    pub fn domain_snapshot_of(&self, work_unit_id: &WorkUnitId) -> Option<DomainSnapshotId> {
        self.units
            .get(work_unit_id.as_str())
            .map(|r| r.domain_snapshot.clone())
    }

    pub fn publication_snapshot_of(
        &self,
        work_unit_id: &WorkUnitId,
    ) -> Option<PublicationSnapshotId> {
        self.units
            .get(work_unit_id.as_str())
            .map(|r| r.publication_snapshot.clone())
    }

    pub fn transition(&mut self, request: TransitionRequest) -> TransitionResult {
        let Some(prior) = self.units.get(request.work_unit_id.as_str()).cloned() else {
            // Unknown unit: treat as invalid without inventing legal state.
            let empty_domain = DomainSnapshotId::parse("domain:unknown-unit").expect("static id");
            let empty_pub =
                PublicationSnapshotId::parse("publication:unknown-unit").expect("static id");
            let cp = CheckpointId::parse("cp:none").expect("static id");
            return TransitionResult {
                outcome: TransitionOutcome::InvalidTransition,
                state: WorkState::Failed,
                checkpoint: cp.clone(),
                domain_snapshot: empty_domain.clone(),
                publication_snapshot: empty_pub.clone(),
                domain_unchanged: true,
                publication_unchanged: true,
                legal_mapping_applied: false,
                trace: TransitionTrace {
                    policy_version: WORK_POLICY_VERSION.to_owned(),
                    work_unit_id: request.work_unit_id,
                    event: request.event,
                    from_state: WorkState::Failed,
                    to_state: WorkState::Failed,
                    prior_checkpoint: cp.clone(),
                    new_checkpoint: cp,
                    domain_snapshot_before: empty_domain.clone(),
                    domain_snapshot_after: empty_domain,
                    publication_snapshot_before: empty_pub.clone(),
                    publication_snapshot_after: empty_pub,
                    domain_unchanged: true,
                    publication_unchanged: true,
                    legal_mapping_attempt: request.legal_mapping,
                    legal_mapping_applied: false,
                },
            };
        };

        // Stale checkpoint: typed failure; domain/publication frozen ids stay.
        if let Some(expected) = request.expected_checkpoint.as_ref() {
            if expected != &prior.checkpoint {
                return self.result_for(
                    request.work_unit_id,
                    request.event,
                    TransitionOutcome::StaleCheckpoint,
                    prior.state,
                    prior.state,
                    &prior,
                    &prior,
                    request.legal_mapping,
                    false,
                    prior.checkpoint.clone(),
                    prior.checkpoint.clone(),
                );
            }
        }

        // Forbidden legal-mapping attempts never apply and never rewrite snapshots.
        if request.legal_mapping.is_forbidden() {
            // Still allow reading hostile evidence (which may invent new ids);
            // application continues to report frozen ids only.
            let _ = self.evidence.domain_snapshot(&request.work_unit_id);
            return self.result_for(
                request.work_unit_id,
                request.event,
                TransitionOutcome::LegalMutationRejected,
                prior.state,
                prior.state,
                &prior,
                &prior,
                request.legal_mapping,
                false,
                prior.checkpoint.clone(),
                prior.checkpoint.clone(),
            );
        }

        let Some(next) = next_state(prior.state, request.event) else {
            return self.result_for(
                request.work_unit_id,
                request.event,
                TransitionOutcome::InvalidTransition,
                prior.state,
                prior.state,
                &prior,
                &prior,
                request.legal_mapping,
                false,
                prior.checkpoint.clone(),
                prior.checkpoint.clone(),
            );
        };

        // Processing transition only: advance work state + checkpoint.
        // Domain/publication remain the application-frozen values.
        let new_seq = prior.checkpoint_seq + 1;
        let new_checkpoint = CheckpointId::parse(&format!("cp:{new_seq}")).expect("checkpoint id");
        let updated = WorkRecord {
            state: next,
            checkpoint: new_checkpoint.clone(),
            domain_snapshot: prior.domain_snapshot.clone(),
            publication_snapshot: prior.publication_snapshot.clone(),
            checkpoint_seq: new_seq,
        };
        self.units
            .insert(request.work_unit_id.as_str().to_owned(), updated.clone());

        // Hostile adapters may change on re-read; ignore for authority.
        let _ = self.evidence.domain_snapshot(&request.work_unit_id);

        self.result_for(
            request.work_unit_id,
            request.event,
            TransitionOutcome::Transitioned,
            prior.state,
            next,
            &prior,
            &updated,
            request.legal_mapping,
            false,
            prior.checkpoint.clone(),
            new_checkpoint,
        )
    }

    // Keep the authority trace inputs explicit: collapsing before/after snapshots,
    // checkpoints, event, and legal-mapping evidence risks hiding HC-10 invariants.
    // A structural parameter-object refactor requires a dedicated HC-10 proof slice.
    #[allow(clippy::too_many_arguments)]
    fn result_for(
        &self,
        work_unit_id: WorkUnitId,
        event: crate::domain::WorkEvent,
        outcome: TransitionOutcome,
        from: WorkState,
        to: WorkState,
        before: &WorkRecord,
        after: &WorkRecord,
        legal_mapping: LegalMappingAttempt,
        legal_mapping_applied: bool,
        prior_checkpoint: CheckpointId,
        new_checkpoint: CheckpointId,
    ) -> TransitionResult {
        let domain_unchanged = before.domain_snapshot == after.domain_snapshot;
        let publication_unchanged = before.publication_snapshot == after.publication_snapshot;
        TransitionResult {
            outcome,
            state: after.state,
            checkpoint: after.checkpoint.clone(),
            domain_snapshot: after.domain_snapshot.clone(),
            publication_snapshot: after.publication_snapshot.clone(),
            domain_unchanged,
            publication_unchanged,
            legal_mapping_applied,
            trace: TransitionTrace {
                policy_version: WORK_POLICY_VERSION.to_owned(),
                work_unit_id,
                event,
                from_state: from,
                to_state: to,
                prior_checkpoint,
                new_checkpoint,
                domain_snapshot_before: before.domain_snapshot.clone(),
                domain_snapshot_after: after.domain_snapshot.clone(),
                publication_snapshot_before: before.publication_snapshot.clone(),
                publication_snapshot_after: after.publication_snapshot.clone(),
                domain_unchanged,
                publication_unchanged,
                legal_mapping_attempt: legal_mapping,
                legal_mapping_applied,
            },
        }
    }
}
