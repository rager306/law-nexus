//! HC-03 dispose review boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Pending/quarantined dispositions cannot become acceptance and cannot produce
//! promotion commits.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
