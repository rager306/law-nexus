//! HC-05 decode and anchor boundary.
//!
//! Dependency direction is inward: adapters implement outbound ports, the
//! application service depends on ports, and domain types depend on neither.
//! Decoder output is limited to structural candidates and exact evidence
//! anchors. Gate-owned claims (verified lifecycle, identity merge, relation
//! minting) and raw payload leakage are rejected by policy.

pub mod adapters;
pub mod analysis_source_mapping;
pub mod application;
pub mod article_body;
pub mod capture_bounds;
pub mod cleaned_cli;
pub mod cleaned_completion;
pub mod cleaned_nav;
pub mod cleaned_nav_verifier;
pub mod cleaned_publish;
pub mod cleaned_verifier;
pub mod cleaned_wire;
pub mod current_requisites;
pub mod deontic;
pub mod document_context;
pub mod domain;
pub mod evaluator;
pub mod golden;
pub mod hierarchy;
pub mod hierarchy_artifact;
pub mod lawref;
pub mod lawref_resolve;
pub mod lexer;
pub mod local_grammar;
pub mod morphology;
pub mod npa_analysis_records;
pub mod npa_analysis_wire;
pub mod npa_anchor;
pub mod npa_bounds;
pub mod npa_classify;
pub mod npa_context_baseline;
pub mod npa_context_records;
pub mod npa_continuation;
pub mod npa_frames_baseline;
pub mod npa_link;
pub mod npa_report;
pub mod npa_sweep;
pub mod npa_typed;
pub mod npa_wire;
pub mod ports;
pub mod prefix_catalog;
pub mod reader_contract;
pub mod reader_gate;
pub mod reader_projection;
pub mod reader_verifier;
pub mod references;
pub mod sentence;
pub mod source_package;
pub mod structural_profile;
pub mod temporal;
mod tokenizer;
pub mod unknown_forms;
