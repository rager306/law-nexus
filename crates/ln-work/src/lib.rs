//! HC-10 transition work state boundary (application processing policy).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Work cancel/resume/stale transitions cannot create or mutate lifecycle,
//! clock, identity, relation or authority state. Processing state is not
//! legal state.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
