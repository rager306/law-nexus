use crate::domain::{
    digest_chain, CandidateId, CandidateRecord, GateOutcome, GateReason, GateRequest, GateResult,
    GateVersion, LifecycleType, C10_GATE_VERSION,
};
use crate::ports::CandidateStorePort;

/// C10 evidence-kernel gate policy. Family/workflow adapters are not co-owners.
pub struct GateLifecycle<S> {
    store: S,
    next_seq: u64,
}

impl<S> GateLifecycle<S>
where
    S: CandidateStorePort,
{
    pub fn new(store: S) -> Self {
        Self { store, next_seq: 0 }
    }

    pub fn seed_extracted(
        &mut self,
        candidate_id: CandidateId,
        evidence_refs: Vec<crate::domain::EvidenceRef>,
    ) -> CandidateRecord {
        let record = CandidateRecord {
            candidate_id: candidate_id.clone(),
            lifecycle_type: LifecycleType::ExtractedCandidate,
            evidence_refs,
            predecessor: None,
        };
        self.store.put(record.clone());
        record
    }

    pub fn request_transition(&mut self, request: GateRequest) -> GateResult {
        let original = self
            .store
            .get(&request.candidate_id)
            .unwrap_or(CandidateRecord {
                candidate_id: request.candidate_id.clone(),
                lifecycle_type: LifecycleType::ExtractedCandidate,
                evidence_refs: Vec::new(),
                predecessor: None,
            });

        let input_chain_digest = digest_chain(&request.candidate_id, &request.evidence_refs);
        let gate_version = GateVersion::parse(C10_GATE_VERSION).expect("static version");

        // In-place mutation is always invalid under C10.
        if request.in_place {
            return GateResult {
                gate_version,
                outcome: GateOutcome::InvalidTransition,
                reason: GateReason::InPlaceMutation,
                original_id: original.candidate_id.clone(),
                original_type: original.lifecycle_type,
                resulting_id: original.candidate_id,
                resulting_type: original.lifecycle_type,
                predecessor: original.predecessor,
                input_chain_digest,
                confidence_used_as_authority: false,
            };
        }

        // Confidence may rank within a lifecycle but cannot cross the boundary.
        let evidence_ok = !request.evidence_refs.is_empty();
        if !evidence_ok {
            let reason = if request.confidence >= 90 {
                GateReason::ConfidenceOnly
            } else {
                GateReason::MissingEvidenceChain
            };
            return GateResult {
                gate_version,
                outcome: GateOutcome::InsufficientEvidence,
                reason,
                original_id: original.candidate_id.clone(),
                original_type: original.lifecycle_type,
                resulting_id: original.candidate_id,
                resulting_type: original.lifecycle_type,
                predecessor: original.predecessor,
                input_chain_digest,
                confidence_used_as_authority: request.confidence >= 90,
            };
        }

        // Required evidence present: mint a NEW immutable outcome identity.
        // Never mutate the original record's type in place.
        self.next_seq += 1;
        let new_id = CandidateId::parse(&format!(
            "{}:v{}",
            original.candidate_id.as_str(),
            self.next_seq
        ))
        .expect("static candidate id");
        let new_record = CandidateRecord {
            candidate_id: new_id.clone(),
            lifecycle_type: request.requested_type,
            evidence_refs: request.evidence_refs,
            predecessor: Some(original.candidate_id.clone()),
        };
        self.store.put(new_record);

        GateResult {
            gate_version,
            outcome: GateOutcome::AcceptedNewOutcome,
            reason: GateReason::EvidenceChainSatisfied,
            original_id: original.candidate_id.clone(),
            original_type: original.lifecycle_type,
            resulting_id: new_id,
            resulting_type: request.requested_type,
            predecessor: Some(original.candidate_id),
            input_chain_digest,
            confidence_used_as_authority: false,
        }
    }

    pub fn get(&self, candidate_id: &CandidateId) -> Option<CandidateRecord> {
        self.store.get(candidate_id)
    }
}
