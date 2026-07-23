//! HC-02 inventory immutable intake boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Inventory remains staging/review visibility and cannot mint curated,
//! current, promotion or publication authority.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
