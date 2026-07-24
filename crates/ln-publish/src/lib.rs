//! HC-15 publish authoritative H1 unit boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Sole Publication Authority permits one complete authoritative H1 unit and
//! one writer per scope. Partial candidates remain non-authoritative.
//! Identical operation/digest retries yield Duplicate with the same unit.
//! Competing writers are rejected without mutating the first unit.
//! No fencing, transaction, or product storage claim.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
