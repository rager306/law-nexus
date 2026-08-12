//! Outbound ports for applicability (ADR-0023).
//!
//! v0 evaluator does not require ports yet; the trait surface exists so later
//! profile/fact adapters plug in without domain→adapter inversion.

use crate::domain::{CaseFactsRevision, PredicateRegistryRevision, ProfileInputRevision};

/// Read-only profile/predicate registry identity. Profiles never emit final decisions.
pub trait ProfileInputPort {
    fn predicate_registry_revision(&self) -> PredicateRegistryRevision;
    fn profile_input_revision(&self) -> ProfileInputRevision;
    fn case_facts_revision(&self) -> CaseFactsRevision;
}
