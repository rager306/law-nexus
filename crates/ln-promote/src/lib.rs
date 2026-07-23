//! HC-04 commit curated promotion boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Cancel mid-attempt leaves no curated effect; identical retry yields one
//! commit or already-committed with the same digest; mismatched reuse is
//! rejected. Promotion never grants publication authority.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
