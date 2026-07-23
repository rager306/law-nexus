//! HC-09 resolve five-clock state boundary (D118).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! A missing governing clock anchor cannot be filled from other clocks,
//! wall-clock, edition order or lifecycle type. Substitutions fail closed.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
