//! HC-09 resolve five-clock state boundary (D118).
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! A missing governing clock anchor cannot be filled from other clocks,
//! wall-clock, edition order or lifecycle type. Substitutions fail closed.
//!
//! RC11-F06 design boundary: the five-clock model is a **safety contract**
//! (role-bound anchors, no silent substitution). It is **not** a complete
//! temporal/interval/bitemporal algebra. Deferred algebra capabilities are
//! inventoried as explicit non-claims via `TemporalAlgebraCapability`.
//!
//! RC11-F07 design boundary: `TextChangeEvent` and `NormativeEffectEvent` are
//! named and separated as **design-only** kinds (`LegislativeEventKind`). Lexical
//! text change must not prove legal effect; taxonomy presence is not CTV runtime.
//!
//! RC11-F09 / TSG-004: force/status, version relation, applicability, and
//! epistemic outcome are **orthogonal** (`NormativeDimension`). Bounded offline
//! `resolve_force_status_at` covers **ForceStatus only**. KBO-R012 O2 adds
//! `join_force_with_membership` (force + structural membership by component) —
//! still not CTV text store, not applicability, not legal corpus proof.
//!
//! RC11-F08 / TSG-003/013: structural membership graph + industrial op planner
//! and bounded-runtime `apply_industrial_op` with append-only structural event log.
//! Versioned membership fold (`fold_membership_at` → `StructuralAst`) is a
//! projection at effect_day t, not a stored document tree, not CTV text.

pub mod adapters;
pub mod application;
pub mod domain;
pub mod ports;
