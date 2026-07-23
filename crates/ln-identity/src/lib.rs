//! HC-07 assert identity boundary (C12).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! One-sided evidence and similarity alone cannot authorize `same` or merge.
//! Both identities remain separately addressable; assertions are not physical
//! or semantic merge operations.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
