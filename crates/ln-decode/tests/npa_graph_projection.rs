//! T03 integration battery (M223-d2q075 S07): the `npa_graph_projection`
//! consumer over the saved `npa-analysis` JSONL.
//!
//! Executable core of `prd/architecture/intermediate-source-consumer-acceptance-contract.md`
//! (`npa_graph_projection`, §3 / §5). The battery asserts:
//!
//! * handwritten identity and endpoint oracles over **tracked** analysis
//!   fixtures (authored independently of the producer): every node/edge key is
//!   the composite `SourceIdentity ⊕ DocumentVersionRef`, never a bare local
//!   `tN` / member id;
//! * idempotent repeat import (byte-identical counts, no duplicates);
//! * closed refusals: `cross_document` / `source_identity_mismatch` /
//!   `document_version_mismatch` / `unknown_fragment`;
//! * no XML re-parse: the consumer reads the materialized JSONL only, and a
//!   genuine producer envelope (rendered from a tracked reader fixture) projects
//!   to the same identity and family counts as its read-back.
//!
//! Non-claims: this battery is `[bounded]` to the named fixtures. It is not
//! corpus coverage, not source authenticity and not semantic/legal gold. R1000
//! stays active and unclosed. Raw decoded corpus text is never logged.

use std::path::PathBuf;

use ln_decode::analysis_source_mapping::{SourceIdentity, SourceMapping};
use ln_decode::document_context::DocumentVersionRef;
use ln_decode::npa_analysis_records::analyze_document;
use ln_decode::npa_analysis_verify::read_back_npa_analysis;
use ln_decode::npa_analysis_wire::{
    AnalysisEnvelopeRequest, AnalysisLimits, AnalysisScope, render_npa_analysis,
};
use ln_decode::npa_graph_projection::{
    GraphErrorKind, GraphNode, GraphNodeKey, GraphNodeKind, LocalNodeKey, NPA_GRAPH_EDGE_KINDS,
    NPA_GRAPH_IDENTITY_COMPONENTS, NPA_GRAPH_NODE_KINDS, NPA_GRAPH_PROJECTION_PROFILE,
    NPA_GRAPH_REFUSALS, NpaGraph,
};
use ln_decode::reader_contract::{FragmentRef, ReaderRecordIndex};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, MODEL, PROFILE, capture};

// --------------------------------------------------------------- fixtures #

const ENVELOPE_A: &str = include_str!("fixtures/npa-graph/envelope-a.jsonl");
const ENVELOPE_A_V2: &str = include_str!("fixtures/npa-graph/envelope-a-v2.jsonl");
const ENVELOPE_B: &str = include_str!("fixtures/npa-graph/envelope-b.jsonl");
const ENVELOPE_UNKNOWN_FRAGMENT: &str =
    include_str!("fixtures/npa-graph/envelope-unknown-fragment.jsonl");
const ENVELOPE_CROSS_DOC: &str = include_str!("fixtures/npa-graph/envelope-cross-doc.jsonl");
const ENVELOPE_DOC_IDENTITY_MISMATCH: &str =
    include_str!("fixtures/npa-graph/envelope-doc-identity-mismatch.jsonl");

/// A tracked reader fixture used to render a genuine producer envelope.
const MIXED: &str = include_str!("fixtures/reader/mixed-wordml.xml");

const HEX_A: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

// ------------------------------------------------------------- pipeline #

fn module_source() -> String {
    let path = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("src/npa_graph_projection.rs");
    std::fs::read_to_string(path).expect("module source must be readable")
}

/// Renders a genuine S02 six-family analysis envelope from a tracked reader
/// fixture through the real pipeline (never a hand-copied literal).
fn render_envelope(xml: &[u8], document_version_ref: &str) -> String {
    let package = capture(xml, &Limits::default()).expect("fixture must capture");
    assert_eq!(
        gate_reader(package.records()).expect("gate must succeed"),
        ReaderSourceClass::SupportedWordml,
        "the fixture must gate as supported WordML"
    );
    let index = ReaderRecordIndex::new(package.records()).expect("substrate index");
    let projection = build_projection(package.records()).expect("projection");
    let identity = SourceIdentity::try_new(
        package.manifest().source.sha256.clone(),
        package.manifest().source.bytes,
        MODEL.to_string(),
        package.footer().records_seal_hash.clone(),
        package.footer().manifest_hash.clone(),
    )
    .expect("parent identity");
    let version = DocumentVersionRef::try_new(
        document_version_ref.to_string(),
        package.manifest().source.sha256.clone(),
        PROFILE.to_string(),
    )
    .expect("document version triple");
    let mut mapping = SourceMapping::new(identity.clone(), version);
    for text in index.texts() {
        mapping
            .pin_fragment(
                FragmentRef::from(text.id.as_str()),
                text.value.clone(),
                &identity,
            )
            .expect("fragment must pin");
    }
    let analysis = analyze_document(&projection, &index, &mapping).expect("document analysis");
    let request = AnalysisEnvelopeRequest {
        analysis: &analysis,
        projection: &projection,
        index: &index,
        mapping: &mapping,
        limits: AnalysisLimits::default(),
        scope: AnalysisScope::Bounded,
    };
    render_npa_analysis(&request).expect("envelope must render")
}

fn identity_of(artifact: &str) -> ln_decode::npa_graph_projection::GraphIdentity {
    let readback = read_back_npa_analysis(artifact).expect("hand-written envelope must read back");
    ln_decode::npa_graph_projection::GraphIdentity::from_readback(&readback.manifest)
        .expect("identity must build")
}

// ------------------------------------------------------------- oracles #

#[test]
fn handwritten_identity_and_endpoint_oracles() {
    let graph = NpaGraph::project_document(ENVELOPE_A).expect("projection must succeed");
    let identity = identity_of(ENVELOPE_A);

    // The identity is the composite parent pin ⊕ document version.
    assert_eq!(identity.source.source_sha256, HEX_A);
    assert_eq!(identity.source.source_bytes, 42);
    assert_eq!(
        identity.source.parent_schema,
        "law-nexus/cleaned-projection/v1"
    );
    assert!(identity.source.records_seal_hash.is_none());
    assert!(identity.source.manifest_hash.is_none());
    assert_eq!(identity.version.document_version_ref(), "doc-1");
    assert_eq!(identity.version.source_revision(), "rev-1");
    assert_eq!(identity.version.decoder_profile(), "npa_analysis_wordml/v1");

    // Node/edge counts are the handwritten oracle.
    let counts = graph.counts();
    assert_eq!(counts.fragments, 2);
    assert_eq!(counts.members, 2);
    assert_eq!(counts.classifications, 2);
    assert_eq!(counts.relations, 1);
    assert_eq!(counts.nodes(), 6);
    assert_eq!(counts.edges(), 1);

    // Every node key embeds the composite identity, never a bare local id.
    for node in graph.nodes() {
        assert_eq!(node.key().identity, identity);
    }
    let fragment_keys: Vec<&GraphNodeKey> = graph
        .nodes()
        .filter(|node| node.kind() == GraphNodeKind::Fragment)
        .map(GraphNode::key)
        .collect();
    assert!(
        fragment_keys
            .iter()
            .any(|key| { key.local == LocalNodeKey::Fragment(FragmentRef::new("t7")) })
    );
    assert!(
        fragment_keys
            .iter()
            .any(|key| { key.local == LocalNodeKey::Fragment(FragmentRef::new("t8")) })
    );

    // The relation edge endpoints are composite keys (identity ⊕ member id).
    let edge = graph.edges().next().expect("exactly one relation edge");
    assert_eq!(edge.kind, "approved_by");
    assert_eq!(
        edge.from,
        GraphNodeKey::new(identity.clone(), LocalNodeKey::Member(3))
    );
    assert_eq!(
        edge.to,
        GraphNodeKey::new(identity.clone(), LocalNodeKey::Member(4))
    );

    // A classification node points at its member node by composite key.
    let classification = graph
        .nodes()
        .find(|node| node.kind() == GraphNodeKind::Classification)
        .expect("a classification node");
    match classification {
        GraphNode::Classification { member, .. } => assert_eq!(
            member,
            &GraphNodeKey::new(identity.clone(), LocalNodeKey::Member(3))
        ),
        other => panic!("expected a classification node, got {other:?}"),
    }
}

#[test]
fn distinct_documents_never_collide_on_a_local_id() {
    let mut graph = NpaGraph::new();
    graph.import(ENVELOPE_A).expect("document a");
    graph.import(ENVELOPE_B).expect("document b");
    assert_eq!(graph.identities().count(), 2);
    // Both documents declare `t7`, but a distinct identity makes a distinct key.
    let identity_a = identity_of(ENVELOPE_A);
    let identity_b = identity_of(ENVELOPE_B);
    assert_ne!(identity_a, identity_b);
    assert_eq!(graph.counts().fragments, 3);
    assert_eq!(graph.counts().members, 3);
    assert_eq!(graph.nodes_for(&identity_a).len(), 6);
    assert_eq!(graph.nodes_for(&identity_b).len(), 2);
}

#[test]
fn repeat_import_is_idempotent() {
    let mut graph = NpaGraph::new();
    let first = graph.import(ENVELOPE_A).expect("first import");
    assert!(!first.already_present);
    assert_eq!(first.added_nodes, 6);
    assert_eq!(first.added_edges, 1);
    let after_first = graph.counts();

    let second = graph.import(ENVELOPE_A).expect("repeat import");
    assert!(second.already_present);
    assert_eq!(second.added_nodes, 0);
    assert_eq!(second.added_edges, 0);
    // Byte-identical counts: no duplicate nodes, edges or members.
    assert_eq!(second.counts, after_first);
    assert_eq!(graph.counts(), after_first);
    assert_eq!(graph.identities().count(), 1);
    assert_eq!(graph.nodes().count(), after_first.nodes());
    assert_eq!(graph.edges().count(), after_first.edges());
}

#[test]
fn same_document_version_ref_with_a_new_revision_is_refused() {
    let mut graph = NpaGraph::new();
    graph.import(ENVELOPE_A).expect("document a");
    let error = graph.import(ENVELOPE_A_V2).expect_err("must refuse");
    assert_eq!(error.kind(), GraphErrorKind::DocumentVersionMismatch);
    assert_eq!(error.kind().as_str(), "document_version_mismatch");
    // Nothing was merged: the graph still holds only document a.
    assert_eq!(graph.counts().fragments, 2);
}

#[test]
fn identity_mismatch_is_refused_without_rebase() {
    // (a) A pinned identity belonging to another document_version_ref.
    let mut graph = NpaGraph::new();
    let pinned = identity_of(ENVELOPE_B);
    let error = graph
        .import_pinned(ENVELOPE_A, &pinned)
        .expect_err("must refuse");
    assert_eq!(error.kind(), GraphErrorKind::CrossDocument);

    // (b) The `document` record's source pin disagrees with the manifest pin.
    let mut graph = NpaGraph::new();
    let error = graph
        .import(ENVELOPE_DOC_IDENTITY_MISMATCH)
        .expect_err("must refuse");
    assert_eq!(error.kind(), GraphErrorKind::SourceIdentityMismatch);
    assert_eq!(error.kind().as_str(), "source_identity_mismatch");
    assert!(graph.nodes().next().is_none(), "no partial graph");
}

#[test]
fn undeclared_fragment_is_refused() {
    let mut graph = NpaGraph::new();
    let error = graph
        .import(ENVELOPE_UNKNOWN_FRAGMENT)
        .expect_err("must refuse");
    assert_eq!(error.kind(), GraphErrorKind::UnknownFragment);
    assert_eq!(error.kind().as_str(), "unknown_fragment");
    assert!(graph.nodes().next().is_none(), "no partial graph");
}

#[test]
fn cross_document_endpoint_is_refused() {
    let mut graph = NpaGraph::new();
    let error = graph.import(ENVELOPE_CROSS_DOC).expect_err("must refuse");
    assert_eq!(error.kind(), GraphErrorKind::CrossDocument);
    assert!(graph.nodes().next().is_none(), "no partial graph");
}

#[test]
fn consumer_never_opens_the_source_xml() {
    let source = module_source();
    let code_end = source.find("#[cfg(test)]").unwrap_or(source.len());
    let code: String = source[..code_end]
        .lines()
        .filter(|line| !line.trim_start().starts_with("//"))
        .collect::<Vec<_>>()
        .join("\n");
    for forbidden in [
        "quick_xml",
        "XmlReader",
        "XmlNsReader",
        "capture(",
        "from_xml",
        "parse_xml",
        "serde",
    ] {
        assert!(
            !code.contains(forbidden),
            "the graph projection must read JSONL only, found {forbidden}"
        );
    }
    assert!(
        code.contains("read_back_npa_analysis"),
        "the consumer must read the materialized JSONL through the read-back"
    );
}

#[test]
fn real_producer_envelope_projects_without_reparse() {
    let envelope = render_envelope(MIXED.as_bytes(), "real:mixed-wordml");
    let readback = read_back_npa_analysis(&envelope).expect("read back");
    let expected_identity = identity_of(&envelope);

    let mut graph = NpaGraph::new();
    let report = graph.import(&envelope).expect("projection must succeed");
    assert_eq!(report.identity, expected_identity);
    assert_eq!(
        report.identity.source.source_sha256,
        readback.manifest.source_sha256
    );

    // The graph mirrors the read-back family counts exactly (no XML re-parse).
    let counts = graph.counts();
    assert_eq!(counts.fragments, readback.fragments.len());
    assert_eq!(counts.members, readback.linked_members.len());
    assert_eq!(counts.classifications, readback.classifications.len());
    assert_eq!(counts.relations, readback.relations.len());

    // Repeat import is idempotent over a genuine producer envelope.
    let again = graph.import(&envelope).expect("reproject");
    assert!(again.already_present);
    assert_eq!(again.added_nodes, 0);
    assert_eq!(again.added_edges, 0);
    assert_eq!(graph.counts(), counts);
}

#[test]
fn model_declarations_match_the_contract_block() {
    assert_eq!(NPA_GRAPH_PROJECTION_PROFILE, "npa_graph_projection/v1");
    assert_eq!(
        NPA_GRAPH_IDENTITY_COMPONENTS,
        [
            "SourceIdentity",
            "DocumentVersionRef",
            "composite_source_identity_xor_document_version_ref"
        ]
    );
    let nodes: Vec<&str> = NPA_GRAPH_NODE_KINDS
        .iter()
        .map(|kind| kind.as_str())
        .collect();
    assert_eq!(nodes, ["member", "fragment", "classification"]);
    assert_eq!(NPA_GRAPH_EDGE_KINDS, ["relation"]);
    assert_eq!(
        NPA_GRAPH_REFUSALS,
        [
            "cross_document",
            "source_identity_mismatch",
            "document_version_mismatch",
            "unknown_fragment"
        ]
    );
}
