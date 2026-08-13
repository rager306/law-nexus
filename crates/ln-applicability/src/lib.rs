//! Fail-closed applicability protocol kernel (ADR-0023) `[proposed]`.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//!
//! While lifecycle remains `[proposed]`, the evaluator never emits
//! `Applicable` / `NotApplicable`. Every evaluation abstains with a typed
//! kind and a mandatory `ExplainableTrace`. Documentation, CTV presence,
//! NormativeState labels, roadmap completion, NormRule IR presence, predicate
//! algebra outcomes, and LLM prose cannot mint a positive applicability claim.
//! NormRule IR (RC11-F04a) and pure predicate algebra (RC11-F04b) are fail-closed
//! design/implementation spines, not product legal validation.
//!
//! RC12-F05 capability inventory (`ApplicabilityCapability`) names landed spines
//! versus deferred product capabilities. Inventory presence is not TSG-006 closure
//! and cannot mint Applicable/NotApplicable.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
