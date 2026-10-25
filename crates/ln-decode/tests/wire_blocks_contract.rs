//! T01 contract battery for the cleaned-wire → [`ParsedBlock`] bridge.
//!
//! Handwritten oracle: this battery shares no private code with the module
//! under test. It drives the tracked inline WordML fixture through
//! `source_package::capture` → `reader_projection::build_projection` →
//! `cleaned_wire::render_cleaned_projection` → `cleaned_wire::read_cleaned_wire`
//! and then through `wire_blocks::blocks_from_cleaned_projection`, comparing the
//! extracted marker stream against the independent XML decode path
//! (`ConsultantWordMlBlockDecoder`). Segment text survival is asserted
//! byte-for-byte.
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures in
//! this file and under `tests/fixtures/reader/`; never corpus coverage, never
//! source authenticity, never a legal-completeness claim. R1000 stays active.
//! Raw decoded legal text is never logged by the battery itself.

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::cleaned_wire::{
    CleanedProjection, WireCompletion, WireLimits, read_cleaned_wire, render_cleaned_projection,
};
use ln_decode::domain::{
    DecodeRequest, FamilyFormat, ParagraphStyle, ParsedBlock, PayloadRef, SourceFormatId,
};
use ln_decode::hierarchy::{HierarchyCandidateReport, extract_hierarchy_candidates};
use ln_decode::ports::BlockDecoderPort;
use ln_decode::reader_contract::ReaderViewKind;
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_decode::wire_blocks::{
    WIRE_BLOCKS_NON_CLAIMS, WireBlocksError, blocks_from_cleaned_projection,
};

// ---------------------------------------------------------------- fixtures #

/// Four plain paragraphs with hierarchy markers: one container (`glava`) and
/// two `statya` units, one of which owns a numbered `punkt`. Written on one
/// line so no inter-element whitespace creates residual text.
const PLAIN_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p><w:p><w:r><w:t>1) пункт первый</w:t></w:r></w:p><w:p><w:r><w:t>Статья 5. Сфера применения</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// One paragraph carrying a provider control (`w:tab`) between two source
/// fragments: the wire must re-emit the derived literal without normalizing the
/// source text.
const CONTROLS_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Alpha</w:t><w:tab/><w:t>Beta</w:t></w:r></w:p></w:body></w:wordDocument>"#;

// ------------------------------------------------------------ preparation #

/// Capture → project → render → read back one inline WordML fixture. The
/// returned projection is the materialized-layer value the bridge consumes.
fn readback(xml: &str) -> CleanedProjection {
    let package = capture(xml.as_bytes(), &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    let artifact = render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export");
    read_cleaned_wire(&artifact).expect("exported projection must read back")
}

/// The independent XML path: decode the same bytes with the frozen adapter.
fn xml_blocks(xml: &str) -> Vec<ParsedBlock> {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m224-s05-wire-blocks").expect("static payload ref"),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        xml.as_bytes(),
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("inline WordML fixture must decode")
}

/// `(catalog token, number, ladder path)` per candidate, in document order.
fn candidate_keys(report: &HierarchyCandidateReport) -> Vec<(String, String, Option<String>)> {
    report
        .candidates()
        .iter()
        .map(|candidate| {
            (
                candidate.catalog_token().to_string(),
                candidate.number().to_string(),
                candidate.path().map(str::to_owned),
            )
        })
        .collect()
}

fn text_of(blocks: &[ParsedBlock]) -> Vec<String> {
    blocks
        .iter()
        .map(|block| block.text().to_string())
        .collect()
}

// ------------------------------------------------------------- the oracle #

#[test]
fn bridge_reproduces_the_xml_marker_stream() {
    let wire = readback(PLAIN_FIXTURE);
    let bridged = blocks_from_cleaned_projection(&wire, SourceFormatId::ConsultantWordMl)
        .expect("bridge must accept the materialized projection");
    let decoded = xml_blocks(PLAIN_FIXTURE);

    // Byte-exact text survival: the bridged stream reproduces the XML-parsed
    // text of the same document, in the same document order.
    assert_eq!(
        text_of(&bridged),
        text_of(&decoded),
        "bridged block text must equal the XML decode path"
    );

    // Projection-local anchoring: wire:<view id>, never an XML artifact span.
    assert_eq!(bridged.len(), 4, "one block per paragraph");
    for (index, block) in bridged.iter().enumerate() {
        assert_eq!(
            block.source_location().stream().as_str(),
            format!("wire:v{index}"),
            "block {index} must be projection-locally anchored"
        );
        assert_eq!(block.source_location().span().start(), 0);
        assert_eq!(block.source_location().span().end(), block.text().len());
        assert_eq!(block.style(), ParagraphStyle::BodyText);
        assert_eq!(block.provider_style_id(), None);
        assert_eq!(block.source_format(), SourceFormatId::ConsultantWordMl);
    }

    // The extracted marker stream is identical down to ladder paths: the bridge
    // introduces no marker, drops none and mints nothing.
    let from_wire = extract_hierarchy_candidates(&bridged);
    let from_xml = extract_hierarchy_candidates(&decoded);
    assert!(!from_wire.candidates().is_empty(), "markers must extract");
    assert_eq!(candidate_keys(&from_wire), candidate_keys(&from_xml));
    assert_eq!(from_wire.extracted_count(), from_xml.extracted_count());
}

#[test]
fn bridge_re_emits_derived_controls_without_normalizing_source_text() {
    let wire = readback(CONTROLS_FIXTURE);
    let bridged = blocks_from_cleaned_projection(&wire, SourceFormatId::ConsultantWordMl)
        .expect("bridge must accept the derived-control projection");
    assert_eq!(bridged.len(), 1);
    assert_eq!(bridged[0].text(), "Alpha\tBeta");
}

#[test]
fn empty_and_whitespace_views_are_skipped_not_fabricated() {
    // A document whose paragraphs are empty (and whose table cells are empty or
    // hold a single paragraph) yields exactly the non-empty paragraph block.
    const EMPTY_STRUCTURE: &str = include_str!("fixtures/reader/diverse/empty-structure.xml");
    let wire = readback(EMPTY_STRUCTURE);
    let bridged = blocks_from_cleaned_projection(&wire, SourceFormatId::ConsultantWordMl)
        .expect("bridge must accept the empty-structure projection");
    assert_eq!(text_of(&bridged), vec!["X".to_string()]);

    // An empty projection (no views at all) yields zero blocks, not a
    // fabricated success.
    let mut empty = readback(PLAIN_FIXTURE);
    empty.projection.views.clear();
    let zero = blocks_from_cleaned_projection(&empty, SourceFormatId::ConsultantWordMl)
        .expect("empty projection is not an error");
    assert!(zero.is_empty(), "empty input must yield zero blocks");
}

#[test]
fn dangling_segment_ref_fails_closed() {
    let mut tampered = readback(PLAIN_FIXTURE);
    tampered.projection.segments.clear();
    let error = blocks_from_cleaned_projection(&tampered, SourceFormatId::ConsultantWordMl)
        .expect_err("a view without its segment must refuse");
    assert!(
        matches!(error, WireBlocksError::DanglingSegmentRef { .. }),
        "expected DanglingSegmentRef, got {error:?}"
    );
}

#[test]
fn missing_segment_text_fails_closed() {
    let mut tampered = readback(PLAIN_FIXTURE);
    let target = tampered
        .projection
        .segments
        .iter()
        .find(|segment| segment.text.is_none())
        .map(|segment| segment.id.as_str().to_string())
        .expect("source fragments carry no inline literal");
    tampered
        .inline_texts
        .retain(|inline| inline.segment_id != target);
    let error = blocks_from_cleaned_projection(&tampered, SourceFormatId::ConsultantWordMl)
        .expect_err("a segment without any text channel must refuse");
    assert!(
        matches!(error, WireBlocksError::MissingSegmentText { .. }),
        "expected MissingSegmentText, got {error:?}"
    );
}

#[test]
fn unknown_view_kind_token_is_refused_before_the_bridge() {
    // The closed wire vocabulary refuses an unknown token fail-closed; the
    // bridge can therefore never see an unclassified view kind.
    assert!(ReaderViewKind::from_wire("frobnicate").is_err());

    let package = capture(PLAIN_FIXTURE.as_bytes(), &Limits::default()).expect("capture");
    let projection = build_projection(package.records()).expect("projection");
    let artifact = render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("export");
    let tampered = artifact.replace(r#""view_kind":"paragraph""#, r#""view_kind":"frobnicate""#);
    assert_ne!(tampered, artifact, "the tamper needle must match");
    let error = read_cleaned_wire(&tampered).expect_err("unknown view kind must be refused");
    assert!(
        error.detail().contains("view_kind"),
        "refusal must name the offending field, got {:?}",
        error.detail()
    );
}

#[test]
fn bridge_non_claims_are_declared() {
    assert!(
        WIRE_BLOCKS_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("not source authenticity"))
    );
}
