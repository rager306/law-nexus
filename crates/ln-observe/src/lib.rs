//! HC-01 source observation boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! This crate does not assign legal status, legal clocks, promotion authority or
//! publication authority.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
