//! HC-07 assert identity boundary (C12) plus ADR-0016 FRBR Work/Expression spine.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! One-sided evidence and similarity alone cannot authorize `same` or merge.
//! Both identities remain separately addressable; assertions are not physical
//! or semantic merge operations.
//!
//! FRBR (`mint_work` / `mint_expression` / `compare_work_identities`) is a
//! distinct structural identity spine (KBO-R011 S2): number alone is never a
//! Work; ELI is compatibility projection only; not C12 digest, not force,
//! not applicability, not corpus identity proof.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
