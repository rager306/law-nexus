use crate::domain::{PredicateId, RegisteredPredicate, RegistryVersion, RelationFact};

pub trait RelationRegistryPort {
    fn registry_version(&self) -> RegistryVersion;
    fn lookup(&self, predicate_id: &PredicateId) -> Option<RegisteredPredicate>;
    fn registered_count(&self) -> usize;
    /// Best-effort persistence of accepted facts only. Application policy decides
    /// what is allowed; hostile stores may lie.
    fn try_store_fact(&mut self, fact: RelationFact) -> bool;
    fn fact_count(&self) -> usize;
    fn contains_fact(
        &self,
        predicate_id: &PredicateId,
        subject: &crate::domain::EndpointId,
        object: &crate::domain::EndpointId,
    ) -> bool;
}
