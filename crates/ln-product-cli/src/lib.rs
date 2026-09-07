//! Thin cross-crate orchestration for the M202-9qf3ta S03
//! `hierarchy-registry-generator` (D427): ln-decode parses the closed S02
//! candidate artifact, ln-kb-ontology validates admission and renders the
//! complete registry projection deterministically.
//!
//! The generator validates every input before any mutation: `--check` only
//! renders in memory and byte-compares, never writes. `--write` targets
//! only the canonical registry projection or a repository-relative Cargo
//! target temp path (tests); absolute escapes, parent escapes, and other
//! tracked-tree writes are refused.

pub mod hierarchy_registry_generation;
