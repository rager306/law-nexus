//! Consultant-specific parser: hyperlink extraction, catalog integration,
//! cross-act edge derivation. ADR-0025/0026.
//!
//! All matching logic is YAML-driven. This crate is a composition layer:
//! it reads Consultant WordML XML, extracts hyperlinks, classifies them,
//! and derives CrossActEdge instances. It does NOT decode blocks (that's
//! ln-decode) and does NOT own the edge vocabulary (that's ln-kb-ontology).

pub mod classifier;
pub mod edge_deriver;
pub mod hyperlink;
pub mod observation;
pub mod raw_link;

pub use classifier::{
    classify_all, classify_all_scored, classify_link, classify_link_scored, load_classifier_rules,
    load_templates, score_template, ClassifiedLink, ClassifierRule, Template,
};
pub use edge_deriver::{derive_edges, DerivedEdge};
pub use hyperlink::extract_hyperlinks;
pub use observation::{collect_observations, format_observations_yaml, Observation};
pub use raw_link::RawLink;
