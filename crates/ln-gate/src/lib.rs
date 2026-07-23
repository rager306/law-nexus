//! HC-06 gate lifecycle boundary (C10).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Confidence-only and in-place lifecycle promotion are rejected. A successful
//! lifecycle step requires a new immutable outcome with predecessor chain and
//! gate evidence.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
