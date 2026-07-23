use std::collections::HashMap;

use crate::domain::{
    EndpointId, FamilyId, PredicateId, RegisteredPredicate, RegistryVersion, RelationFact,
    DEFAULT_REGISTRY_VERSION,
};
use crate::ports::RelationRegistryPort;

#[derive(Debug)]
pub struct InMemoryClosedRegistry {
    version: RegistryVersion,
    predicates: HashMap<String, RegisteredPredicate>,
    facts: HashMap<String, RelationFact>,
}

impl InMemoryClosedRegistry {
    pub fn with_family_a_predicate() -> Self {
        let mut predicates = HashMap::new();
        let predicate_id = PredicateId::parse("amends").expect("static id");
        let owner = FamilyId::parse("family-A").expect("static id");
        predicates.insert(
            predicate_id.as_str().to_owned(),
            RegisteredPredicate {
                predicate_id,
                owner_family: owner,
            },
        );
        Self {
            version: RegistryVersion::parse(DEFAULT_REGISTRY_VERSION).expect("static version"),
            predicates,
            facts: HashMap::new(),
        }
    }
}

impl RelationRegistryPort for InMemoryClosedRegistry {
    fn registry_version(&self) -> RegistryVersion {
        self.version.clone()
    }

    fn lookup(&self, predicate_id: &PredicateId) -> Option<RegisteredPredicate> {
        self.predicates.get(predicate_id.as_str()).cloned()
    }

    fn registered_count(&self) -> usize {
        self.predicates.len()
    }

    fn try_store_fact(&mut self, fact: RelationFact) -> bool {
        let key = format!(
            "{}|{}|{}",
            fact.predicate_id.as_str(),
            fact.subject.as_str(),
            fact.object.as_str()
        );
        self.facts.insert(key, fact);
        true
    }

    fn fact_count(&self) -> usize {
        self.facts.len()
    }

    fn contains_fact(
        &self,
        predicate_id: &PredicateId,
        subject: &EndpointId,
        object: &EndpointId,
    ) -> bool {
        let key = format!(
            "{}|{}|{}",
            predicate_id.as_str(),
            subject.as_str(),
            object.as_str()
        );
        self.facts.contains_key(&key)
    }
}

/// Hostile registry that tries to persist every proposal as a fact, including
/// unknown/wrong-owner predicates, and invents open registry entries.
#[derive(Debug)]
pub struct OpenRelationHostileRegistry {
    inner: InMemoryClosedRegistry,
    illicit_facts: usize,
}

impl OpenRelationHostileRegistry {
    pub fn new() -> Self {
        Self {
            inner: InMemoryClosedRegistry::with_family_a_predicate(),
            illicit_facts: 0,
        }
    }

    pub fn illicit_fact_count(&self) -> usize {
        self.illicit_facts
    }
}

impl Default for OpenRelationHostileRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl RelationRegistryPort for OpenRelationHostileRegistry {
    fn registry_version(&self) -> RegistryVersion {
        self.inner.registry_version()
    }

    fn lookup(&self, predicate_id: &PredicateId) -> Option<RegisteredPredicate> {
        self.inner.lookup(predicate_id)
    }

    fn registered_count(&self) -> usize {
        self.inner.registered_count()
    }

    fn try_store_fact(&mut self, fact: RelationFact) -> bool {
        // Hostile: always store, even if application only intended accepted facts.
        self.illicit_facts += 1;
        self.inner.try_store_fact(fact)
    }

    fn fact_count(&self) -> usize {
        self.inner.fact_count()
    }

    fn contains_fact(
        &self,
        predicate_id: &PredicateId,
        subject: &EndpointId,
        object: &EndpointId,
    ) -> bool {
        self.inner.contains_fact(predicate_id, subject, object)
    }
}
