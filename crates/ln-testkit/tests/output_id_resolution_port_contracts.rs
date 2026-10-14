//! Shared [`OutputIdResolutionPort`] contract for the real cleaned-projection
//! resolver (ADR-0015).
//!
//! `ln-query` ships two adapters of `OutputIdResolutionPort`: the synthetic
//! `FixtureGraphResolver` (the M012 proof topology — a fixture that happens to
//! live under `src`) and the production `ProjectionGraphResolver`, which
//! derives a proof-local resolution graph from a real `CleanedProjection`.
//! This is the shared real-adapter suite: it drives `ProjectionGraphResolver`
//! through the port trait over the same sha256-pinned synthetic WordML fixture
//! the M213 cleaned-text integration suite uses, so the port pair cannot
//! silently diverge.
//!
//! What each control establishes:
//! - positivity (non-vacuous): every evidence span the resolver exposes
//!   resolves to a typed record, and its block → document → legal unit → act
//!   edition chain resolves too;
//! - fail-closed: an absent evidence span, citation key, legal unit or act
//!   edition resolves to `None`/`Unresolved`, never a fabricated record.
//!
//! Non-claims: bounded repository-control evidence only. No retrieval-quality,
//! product-runtime or live-TEI/RuVector validation is claimed, and the fixture
//! sha256 pin is a content-drift guard rather than a legal or semantic proof.

use ln_decode::cleaned_wire::{
    CleanedProjection, WireCompletion, WireLimits, export_cleaned_projection, read_cleaned_wire,
};
use ln_decode::reader_gate::{ReaderSourceClass, gate_reader};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_query::retrieval_offline::ProjectionGraphResolver;
use ln_query::retrieval_output::{
    ActEditionId, CitationKey, CitationKeyResolution, EvidenceSpanId, LegalUnitId,
    OutputIdResolutionPort, OutputScopeId, ScopeAsOfDate,
};

/// One sha256-pinned synthetic, non-legal WordML fixture (shared with the M213
/// cleaned-text integration suite). `capture` recomputes the sha256 over these
/// exact bytes; a content drift fails the pin assertion below rather than being
/// silently re-pinned.
const MIXED_XML: &str = include_str!("../../ln-decode/tests/fixtures/reader/mixed-wordml.xml");
const MIXED_SHA256: &str = "d2fc1cd17f0697f575e94f09d83da5027d73afd37c700772eafa4c4a4fbc76db";

/// Drive `capture -> gate_reader -> build_projection -> export -> read_back`
/// over the pinned fixture and return the read-back cleaned projection.
fn projection() -> CleanedProjection {
    let package = capture(MIXED_XML.as_bytes(), &Limits::default())
        .expect("the pinned fixture bytes must capture as a source package");
    assert_eq!(
        package.manifest().source.sha256,
        MIXED_SHA256,
        "pinned fixture content drift; re-pin the sha256 explicitly instead of silently accepting a new hash"
    );
    let class = gate_reader(package.records()).expect("the fixture must gate as a reader source");
    assert_eq!(
        class,
        ReaderSourceClass::SupportedWordml,
        "the pinned fixture must gate as supported WordML"
    );
    let projection = build_projection(package.records()).expect("the pinned fixture must project");
    let artifact = export_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("the pinned projection must export a cleaned artifact");
    read_cleaned_wire(&artifact).expect("the cleaned artifact must read back")
}

#[test]
fn projection_graph_resolver_resolves_every_exposed_record() {
    let projection = projection();
    let resolver = ProjectionGraphResolver::new(&projection)
        .expect("the resolution graph must derive from the pinned projection");

    // Non-vacuity: the pinned document must expose at least one evidence span.
    let spans: Vec<&EvidenceSpanId> = resolver.evidence_span_ids().collect();
    assert!(
        !spans.is_empty(),
        "the pinned projection must expose at least one evidence span"
    );

    for span_id in &spans {
        let span = resolver
            .resolve_evidence_span(span_id)
            .expect("an exposed evidence span must resolve");
        let block = resolver
            .resolve_source_block(&span.source_block_id)
            .expect("an exposed block must resolve");
        assert_eq!(
            block.source_document_id, span.source_document_id,
            "the resolved block must belong to the span's own document"
        );
        resolver
            .resolve_source_document(&span.source_document_id)
            .expect("an exposed document must resolve");
        resolver
            .resolve_legal_unit(&span.legal_unit_id)
            .expect("an exposed legal unit must resolve");
        resolver
            .resolve_act_edition(&span.act_edition_id)
            .expect("an exposed act edition must resolve");
    }

    // A bound citation key resolves uniquely within its own scope.
    let key = resolver
        .segment_ids()
        .find_map(|segment| resolver.citation_key_for_segment(segment))
        .expect("the pinned projection must bind at least one citation key");
    assert!(matches!(
        resolver.resolve_citation_key(resolver.scope_id(), key),
        CitationKeyResolution::Unique(_)
    ));
}

#[test]
fn projection_graph_resolver_fails_closed_on_absent_ids() {
    let projection = projection();
    let resolver = ProjectionGraphResolver::new(&projection)
        .expect("the resolution graph must derive from the pinned projection");
    let as_of = ScopeAsOfDate::parse("2024-06-15").expect("bounded date token");

    assert!(
        resolver
            .resolve_evidence_span(&EvidenceSpanId::parse("EV-absent-from-graph").unwrap())
            .is_none(),
        "an absent evidence span must not be fabricated"
    );
    assert!(
        resolver
            .resolve_legal_unit(&LegalUnitId::parse("LU-absent-from-graph").unwrap())
            .is_none(),
        "an absent legal unit must not be fabricated"
    );
    assert!(
        resolver
            .resolve_act_edition(&ActEditionId::parse("ED-absent-from-graph").unwrap())
            .is_none(),
        "an absent act edition must not be fabricated"
    );
    assert!(
        resolver
            .resolve_valid_edition(&LegalUnitId::parse("LU-absent-from-graph").unwrap(), &as_of)
            .is_none(),
        "an absent legal unit must not resolve to a borrowed edition"
    );
    assert_eq!(
        resolver.resolve_citation_key(
            &OutputScopeId::parse("SCOPE-absent-from-graph").unwrap(),
            &CitationKey::parse("CIT-absent-from-graph").unwrap(),
        ),
        CitationKeyResolution::Unresolved,
        "an absent scope/key pair must resolve to Unresolved"
    );
}
