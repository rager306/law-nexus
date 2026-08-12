//! Outbound adapters for applicability.
//!
//! v0 ships a null/in-memory identity adapter only. No production profile
//! pipeline and no positive applicability claim.

use crate::domain::{CaseFactsRevision, PredicateRegistryRevision, ProfileInputRevision};
use crate::ports::ProfileInputPort;

/// Fixed revision labels for synthetic/hostile tests.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StaticProfileInput {
    pub predicate_registry_revision: PredicateRegistryRevision,
    pub profile_input_revision: ProfileInputRevision,
    pub case_facts_revision: CaseFactsRevision,
}

impl ProfileInputPort for StaticProfileInput {
    fn predicate_registry_revision(&self) -> PredicateRegistryRevision {
        self.predicate_registry_revision.clone()
    }

    fn profile_input_revision(&self) -> ProfileInputRevision {
        self.profile_input_revision.clone()
    }

    fn case_facts_revision(&self) -> CaseFactsRevision {
        self.case_facts_revision.clone()
    }
}
