//! Consultant-specific parser: hyperlink extraction, catalog integration,
//! cross-act edge derivation. ADR-0025/0026.
//!
//! All matching logic is YAML-driven. This crate is a composition layer:
//! it reads Consultant WordML XML, extracts hyperlinks, classifies them,
//! and derives CrossActEdge instances. It does NOT decode blocks (that's
//! ln-decode) and does NOT own the edge vocabulary (that's ln-kb-ontology).

pub mod acceptance_retry_contract;
pub mod amendment_provenance;
pub mod anchor_coverage;
pub mod artifact_output;
pub mod catalog;
pub mod catalog_anchor;
pub mod catalog_sqlite;
pub mod classifier;
pub mod contour_diagnostics;
pub mod corpus_manifest;
pub mod corpus_pageindex;
pub mod corpus_sample;
pub mod document_group_coverage;
pub mod document_profile;
pub mod drift_baseline;
pub mod edge_deriver;
pub mod edition_timeline;
pub mod frbr_bridge;
pub mod gold_coding;
pub mod gold_eval;
pub mod hierarchy_lift_census;
pub mod hyperlink;
pub mod multi_edition;
pub mod npa_corpus_acceptance;
pub mod npa_corpus_acceptance_v2;
pub mod observation;
pub mod page_index_catalog;
pub mod promotion_gate;
pub mod raw_link;
pub mod reference_layer;

pub use anchor_coverage::{
    AnchorCoverage, AnchorCoverageEntry, AnchorCoverageError, COVERAGE_NON_CLAIMS, COVERAGE_SCHEMA,
    CorpusManifest, CoverageCli, MANIFEST_SCHEMA, ManifestEntry, NEGATIVE_PROBE_NUMBERS,
    NegativeProbe, NegativeProbeRow, R1000_STATUS, build_anchor_coverage, exit_code_for,
    parse_corpus_manifest, parse_coverage_args, read_corpus_manifest, render_coverage_json,
    render_envelope_jsonl, run_coverage, verify_artifacts,
};
pub use catalog::{
    CatalogError, CatalogPort, CatalogRecord, InMemoryCatalog, coverage_summary, resolve_consids,
};
pub use catalog_anchor::{
    CatalogAnchorPort, CatalogAnchorRecord, EXPORTS_PREFIX, InMemoryCatalogAnchor, exports_path,
};
pub use catalog_sqlite::{EditionJoinRow, SqliteCatalog};
pub use classifier::{
    ClassifiedLink, ClassifierRule, Template, classify_all, classify_all_scored,
    classify_all_scored_for_path, classify_link, classify_link_scored, load_classifier_rules,
    load_templates, score_template,
};
pub use corpus_pageindex::{
    BuildMeta, CorpusPageIndexCoverage, EnvelopeHeader, PageIndexBuildError, PageIndexCli,
    PageIndexCounts, build_corpus_pageindex, build_coverage, pageindex_exit_code_for,
    parse_envelope_header, parse_pageindex_args, render_pageindex_coverage_json,
    render_pageindex_jsonl, run_pageindex, verify_pageindex_artifacts,
};
pub use document_profile::{
    DetectedProfile, DocumentProfile, apply_boost, detect_profile, load_profiles,
};
pub use edge_deriver::{DerivedEdge, derive_edges};
pub use frbr_bridge::{
    BridgeCli, DEFAULT_ACT_NUMBER, DEFAULT_BINARY_PATH, DEFAULT_CATALOG_PATH,
    DEFAULT_EDITION_PREFIX, DEFAULT_ENVELOPE_PATH, DEFAULT_ONTOLOGY_PATH, DEFAULT_OUT_PATH,
    DEFAULT_RECEIPTS_PATH, DEFAULT_REGISTRY_PATH, DEFAULT_TIMELINE_PATH, ENVELOPE_HEADER_KIND,
    EXIT_DRIFT, EXIT_INPUT, EXIT_JOIN_REFUSED, EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_USAGE,
    FRBR_BRIDGE_KIND, FRBR_BRIDGE_NON_CLAIMS, FRBR_BRIDGE_SCHEMA, FRBR_BRIDGE_VERSION,
    FrbrBridgeError, FrbrBridgeJoin, FrbrBridgeJoinRow, FrbrBridgePins, FrbrBridgeTotals,
    RECEIPTS_SCHEMA, TIMELINE_SCHEMA, build_frbr_bridge_join, build_frbr_bridge_join_from_bytes,
    parse_bridge_args, render_frbr_bridge_json, run_bridge,
};
pub use hyperlink::extract_hyperlinks;
pub use multi_edition::{
    EditionSummary, delta, parse_edition_filename, process_edition, process_edition_for_path,
};
pub use observation::{Observation, collect_observations, format_observations_yaml};
pub use page_index_catalog::{
    CatalogPageIndexRecord, InMemoryPageIndexCatalog, PageIndexCatalogPort,
};
pub use raw_link::RawLink;
pub use reference_layer::{
    DeriveOptions as ReferenceDeriveOptions, RefError as ReferenceLayerError, Reference,
    act_dir_name as reference_layer_act_dir_name, derive as derive_reference_layer,
    edition_layer_document, measurement_applicable as reference_layer_measurement_applicable,
    measurement_artifact_paths as reference_layer_measurement_artifact_paths,
    pageindex_document as reference_layer_pageindex_document,
    references_document as reference_layer_references_document,
    run_check as reference_layer_run_check, try_derive as try_derive_reference_layer,
};
