use std::collections::HashMap;

use crate::domain::{
    digest_proposal, EndpointId, PredicateId, RelationFact, RelationOutcome, RelationProposal,
    RelationValidation, C13_GATE_VERSION,
};
use crate::ports::RelationRegistryPort;

/// C13 evidence-kernel relation registry policy. Families may contribute
/// registered entries under revision policy but are not co-owners of the gate.
/// Rejected relations are never exposed as query facts by application policy.
pub struct ValidateRelation<R> {
    registry: R,
    /// Application-owned accepted facts. Store adapters may be hostile.
    accepted_facts: HashMap<String, RelationFact>,
    initial_registered_count: usize,
}

impl<R> ValidateRelation<R>
where
    R: RelationRegistryPort,
{
    pub fn new(registry: R) -> Self {
        let initial_registered_count = registry.registered_count();
        Self {
            registry,
            accepted_facts: HashMap::new(),
            initial_registered_count,
        }
    }

    pub fn validate(&mut self, proposal: RelationProposal) -> RelationValidation {
        let digest = digest_proposal(&proposal);
        let registry_version = self.registry.registry_version();
        let registered_before = self.registry.registered_count();

        let outcome = match self.registry.lookup(&proposal.predicate_id) {
            None => RelationOutcome::UnknownPredicate,
            Some(registered) if registered.owner_family != proposal.proposed_owner => {
                RelationOutcome::WrongOwner
            }
            Some(_) if proposal.evidence_refs.is_empty() => RelationOutcome::InsufficientEvidence,
            Some(registered) => {
                let fact = RelationFact {
                    predicate_id: proposal.predicate_id.clone(),
                    subject: proposal.subject.clone(),
                    object: proposal.object.clone(),
                    owner_family: registered.owner_family,
                };
                let key = fact_key(&fact.predicate_id, &fact.subject, &fact.object);
                self.accepted_facts.insert(key, fact.clone());
                // Best-effort persistence only.
                let _ = self.registry.try_store_fact(fact);
                RelationOutcome::Accepted
            }
        };

        let stored_as_fact = matches!(outcome, RelationOutcome::Accepted)
            && self.accepted_facts.contains_key(&fact_key(
                &proposal.predicate_id,
                &proposal.subject,
                &proposal.object,
            ));
        // Query exposure is application-owned, not store-owned.
        let exposed_as_query_fact = stored_as_fact
            && self.query_has_fact(&proposal.predicate_id, &proposal.subject, &proposal.object);

        let registry_unchanged = self.registry.registered_count() == registered_before
            && self.registry.registered_count() == self.initial_registered_count;

        RelationValidation {
            c13_version: C13_GATE_VERSION.to_owned(),
            registry_version,
            outcome,
            predicate_id: proposal.predicate_id,
            subject: proposal.subject,
            object: proposal.object,
            proposed_owner: proposal.proposed_owner,
            registry_unchanged,
            stored_as_fact,
            exposed_as_query_fact,
            input_chain_digest: digest,
        }
    }

    pub fn query_has_fact(
        &self,
        predicate_id: &PredicateId,
        subject: &EndpointId,
        object: &EndpointId,
    ) -> bool {
        self.accepted_facts
            .contains_key(&fact_key(predicate_id, subject, object))
    }

    pub fn accepted_fact_count(&self) -> usize {
        self.accepted_facts.len()
    }

    pub fn registered_count(&self) -> usize {
        self.registry.registered_count()
    }
}

fn fact_key(predicate_id: &PredicateId, subject: &EndpointId, object: &EndpointId) -> String {
    format!(
        "{}|{}|{}",
        predicate_id.as_str(),
        subject.as_str(),
        object.as_str()
    )
}
