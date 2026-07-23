//! HC-08 validate relation boundary (C13).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Unknown predicates and wrong-owner emissions are rejected. The closed
//! registry remains unchanged for rejections, and rejected relations are never
//! exposed as query facts.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
