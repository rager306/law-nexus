//! HC-11 compute dependency closure boundary (inward dependency policy).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Incomplete, unknown, unbounded or rule-version-mismatch closures cannot
//! prove completeness or enable incremental authoritative publication.
//! Progress and queue depth are never completeness evidence.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
