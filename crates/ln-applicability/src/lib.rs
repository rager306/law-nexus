//! Fail-closed applicability protocol kernel (ADR-0023) `[proposed]`.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//!
//! While lifecycle remains `[proposed]`, the evaluator never emits
//! `Applicable` / `NotApplicable`. Every evaluation abstains with a typed
//! kind and a mandatory `ExplainableTrace`. Documentation, CTV presence,
//! NormativeState labels, roadmap completion, and LLM prose cannot mint a
//! positive applicability claim.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
