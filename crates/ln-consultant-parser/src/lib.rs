//! Consultant-specific parser: hyperlink extraction, catalog integration,
//! cross-act edge derivation. ADR-0025/0026.
//!
//! All matching logic is YAML-driven. This crate is a composition layer:
//! it reads Consultant WordML XML, extracts hyperlinks, classifies them,
//! and derives CrossActEdge instances. It does NOT decode blocks (that's
//! ln-decode) and does NOT own the edge vocabulary (that's ln-kb-ontology).

pub mod acceptance_retry_contract;
pub mod amendment_provenance;
pub mod artifact_output;
pub mod catalog;
pub mod catalog_sqlite;
pub mod classifier;
pub mod contour_diagnostics;
pub mod corpus_manifest;
pub mod corpus_sample;
pub mod document_profile;
pub mod drift_baseline;
pub mod edge_deriver;
pub mod gold_coding;
pub mod gold_eval;
pub mod hyperlink;
pub mod multi_edition;
pub mod npa_corpus_acceptance;
pub mod npa_corpus_acceptance_v2;
pub mod observation;
pub mod promotion_gate;
pub mod raw_link;

pub use catalog::{
    CatalogError, CatalogPort, CatalogRecord, InMemoryCatalog, coverage_summary, resolve_consids,
};
pub use catalog_sqlite::SqliteCatalog;
pub use classifier::{
    ClassifiedLink, ClassifierRule, Template, classify_all, classify_all_scored,
    classify_all_scored_for_path, classify_link, classify_link_scored, load_classifier_rules,
    load_templates, score_template,
};
pub use document_profile::{
    DetectedProfile, DocumentProfile, apply_boost, detect_profile, load_profiles,
};
pub use edge_deriver::{DerivedEdge, derive_edges};
pub use hyperlink::extract_hyperlinks;
pub use multi_edition::{
    EditionSummary, delta, parse_edition_filename, process_edition, process_edition_for_path,
};
pub use observation::{Observation, collect_observations, format_observations_yaml};
pub use raw_link::RawLink;
