//! HC-12 rebuild disposable projection boundary (outward projection).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Partial, stale-input, cancelled or failed rebuilds remain disposable and
//! non-authoritative. Rebuilds cannot invent facts, hide gaps or change
//! Publication Authority.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
