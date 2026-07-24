//! HC-14 coordinate checkpoint and replay boundary (application replay policy).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Replay suppresses already-applied external effects by operation/effect
//! identity. Corrupt digests and incompatible rule versions fail closed
//! without authority change or rewritten lineage.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
