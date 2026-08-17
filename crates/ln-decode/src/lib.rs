//! HC-05 decode and anchor boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Decoder output is limited to structural candidates and exact evidence
//! anchors. Gate-owned claims (verified lifecycle, identity merge, relation
//! minting) and raw payload leakage are rejected by policy.

pub mod adapters;
pub mod application;
pub mod article_body;
pub mod deontic;
pub mod domain;
pub mod evaluator;
pub mod golden;
pub mod hierarchy;
pub mod morphology;
pub mod ports;
pub mod prefix_catalog;
pub mod references;
pub mod sentence;
pub mod structural_profile;
pub mod temporal;
mod tokenizer;
pub mod unknown_forms;
