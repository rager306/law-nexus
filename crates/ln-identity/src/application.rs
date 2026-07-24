use std::collections::HashMap;

use crate::domain::{
    digest_pair, AssertRequest, C12Version, EvidenceSide, IdentityAssertion, IdentityId,
    IdentityOutcome, IdentityReason, IdentityRecord, C12_GATE_VERSION,
};
use crate::ports::IdentityStorePort;

/// C12 evidence-kernel identity policy. Families contribute evidence but cannot
/// merge. Store adapters may be hostile; identity survival is application-owned.
pub struct AssertIdentity<S> {
    store: S,
    identities: HashMap<String, IdentityRecord>,
}

impl<S> AssertIdentity<S>
where
    S: IdentityStorePort,
{
    pub fn new(store: S) -> Self {
        Self {
            store,
            identities: HashMap::new(),
        }
    }

    pub fn seed(&mut self, identity_id: IdentityId, label: impl Into<String>) -> IdentityRecord {
        let record = IdentityRecord {
            identity_id: identity_id.clone(),
            label: label.into(),
        };
        self.identities
            .insert(identity_id.as_str().to_owned(), record.clone());
        self.store.put(record.clone());
        record
    }

    pub fn assert_pair(&mut self, request: AssertRequest) -> IdentityAssertion {
        // Ensure both identities exist in the application ledger.
        self.ensure_present(&request.left_id);
        self.ensure_present(&request.right_id);

        let digest = digest_pair(&request.left_id, &request.right_id, &request.contributions);
        let contribution_ids = request
            .contributions
            .iter()
            .map(|c| c.contribution_id.clone())
            .collect();
        let evidence_ceiling_visible = request
            .contributions
            .iter()
            .any(|c| !c.evidence_ceiling.is_empty())
            || request.contributions.is_empty();

        let has_left = request
            .contributions
            .iter()
            .any(|c| matches!(c.side, EvidenceSide::Left | EvidenceSide::Bilateral));
        let has_right = request
            .contributions
            .iter()
            .any(|c| matches!(c.side, EvidenceSide::Right | EvidenceSide::Bilateral));
        let has_bilateral = request
            .contributions
            .iter()
            .any(|c| c.side == EvidenceSide::Bilateral)
            || (has_left && has_right);
        let has_any_evidence = !request.contributions.is_empty();
        let similarity_only = request.similarity_score.is_some() && !has_any_evidence;

        let (outcome, reason) = if request.claim_same {
            if similarity_only {
                (IdentityOutcome::Ambiguous, IdentityReason::SimilarityOnly)
            } else if !has_any_evidence {
                (
                    IdentityOutcome::NotResolvable,
                    IdentityReason::MissingEvidence,
                )
            } else if !has_bilateral {
                (IdentityOutcome::Candidate, IdentityReason::OneSidedEvidence)
            } else {
                // Bilateral evidence may support a Same *assertion* but never a merge.
                (IdentityOutcome::Same, IdentityReason::BilateralSameEvidence)
            }
        } else if has_bilateral {
            (
                IdentityOutcome::Different,
                IdentityReason::BilateralDifferentEvidence,
            )
        } else if has_any_evidence {
            (IdentityOutcome::Ambiguous, IdentityReason::OneSidedEvidence)
        } else if similarity_only {
            (IdentityOutcome::Ambiguous, IdentityReason::SimilarityOnly)
        } else {
            (
                IdentityOutcome::NotResolvable,
                IdentityReason::MissingEvidence,
            )
        };

        // C12 never performs physical/semantic merge. Both ids always survive.
        IdentityAssertion {
            c12_version: C12Version::parse(C12_GATE_VERSION).expect("static version"),
            outcome,
            reason,
            left_id: request.left_id.clone(),
            right_id: request.right_id.clone(),
            left_survives: self.identities.contains_key(request.left_id.as_str()),
            right_survives: self.identities.contains_key(request.right_id.as_str()),
            merge_performed: false,
            no_merge_observation: true,
            contribution_ids,
            input_chain_digest: digest,
            method: request.method,
            scope: request.scope,
            evidence_ceiling_visible,
        }
    }

    pub fn get(&self, identity_id: &IdentityId) -> Option<IdentityRecord> {
        self.identities.get(identity_id.as_str()).cloned()
    }

    pub fn contains(&self, identity_id: &IdentityId) -> bool {
        self.identities.contains_key(identity_id.as_str())
    }

    fn ensure_present(&mut self, identity_id: &IdentityId) {
        if self.identities.contains_key(identity_id.as_str()) {
            return;
        }
        let record = IdentityRecord {
            identity_id: identity_id.clone(),
            label: identity_id.as_str().to_owned(),
        };
        self.identities
            .insert(identity_id.as_str().to_owned(), record.clone());
        self.store.put(record);
    }
}
