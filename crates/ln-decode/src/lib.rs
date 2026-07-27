//! HC-05 decode and anchor boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Decoder output is limited to structural candidates and exact evidence
//! anchors. Gate-owned claims (verified lifecycle, identity merge, relation
//! minting) and raw payload leakage are rejected by policy.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod hierarchy;
pub mod morphology;
pub mod ports;
pub mod references;
pub mod sentence;
pub mod temporal;
