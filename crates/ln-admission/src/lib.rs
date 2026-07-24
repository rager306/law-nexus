//! HC-13 decide admission boundary (application admission policy).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Bound-unknown, saturated and retry-amplification fail closed. Capacity
//! remains unknown without a measured local bound. Vendor/foreign benchmarks
//! cannot invent throughput, latency or storage precision, and admission
//! cannot invent legal-delay or completeness meaning.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
