//! Decode port contracts plus the M206/S07 RC28-F12 composed reference
//! vertical.
//!
//! S04 scenario map owned by this file for RC28-F12:
//! `F12-VERTICAL-POSITIVE`, `F12-VERTICAL-NEGATIVE`.
//! `F12-CONTEXT-SEPARATION` and `F12-NO-IR` are owned by
//! `crates/ln-temporal/tests/m206_scope_regressions.rs`; this file adds the
//! provider-isolation half of the separation contract.

use std::io::{Cursor, Write};

use ln_decode::adapters::garant_odt::GarantOdtBlockDecoder;
use ln_decode::adapters::{
    ConsultantWordMlBlockDecoder, HonestSyntheticDecoder, InMemoryDiagnosticSink,
    MaliciousSyntheticDecoder, WordMLStreamingDecoder,
};
use ln_decode::document_context::{
    build_document_analysis_overlay, build_document_structure_index, explicit_anchor_lookup,
    ContextStatus, DocumentVersionRef,
};
use ln_decode::domain::{
    BlockDecodeErrorKind, DecodeRequest, FamilyFormat, ParagraphStyle, ParsedBlock, PayloadRef,
    SourceFormatId,
};
use ln_decode::lawref::capture_lawrefs;
use ln_decode::local_grammar::extract_act_list_frames;
use ln_decode::ports::BlockDecoderPort;
use ln_temporal::document_context::TextSpan as TemporalTextSpan;
use ln_temporal::identity_binding::{
    BindingEndpoints, BindingStatus, BindingUnresolvedReason, BoundTarget,
    ReferenceBindingCandidate, ReferenceEndpoint,
};
use ln_testkit::{
    assert_decode_diagnostic_port_contract, assert_decoder_port_contract,
    assert_decoder_port_contract_with_fixture, assert_malicious_decoder_fails_honest_contract,
};
use zip::{write::SimpleFileOptions, CompressionMethod, ZipWriter};

const OFFICE_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:office:1.0";
const TEXT_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:text:1.0";

fn wordml_structural_fixture() -> &'static [u8] {
    br#"<?xml version="1.0"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
<w:body>
<w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Title text</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>Article 1.</w:t></w:r></w:p>
</w:body>
</w:wordDocument>"#
}

#[test]
fn honest_synthetic_decoder_satisfies_shared_port_contract() {
    assert_decoder_port_contract(&HonestSyntheticDecoder);
}

#[test]
fn wordml_streaming_decoder_satisfies_shared_port_contract() {
    assert_decoder_port_contract_with_fixture(
        &WordMLStreamingDecoder,
        "family:consultant-wordml",
        wordml_structural_fixture(),
    );
}

#[test]
fn malicious_synthetic_decoder_fails_honest_decoder_contract() {
    assert_malicious_decoder_fails_honest_contract(&MaliciousSyntheticDecoder);

    let result = std::panic::catch_unwind(|| {
        assert_decoder_port_contract(&MaliciousSyntheticDecoder);
    });
    assert!(
        result.is_err(),
        "malicious decoder must fail the honest decoder contract"
    );
}

#[test]
fn decode_in_memory_diagnostic_sink_satisfies_shared_port_contract() {
    let mut sink = InMemoryDiagnosticSink::new();
    assert_decode_diagnostic_port_contract(&mut sink);
}

// ---------------------------------------------------------------------------
// RC28-F12 composed reference vertical (T06).
//
// One hop chain per provider: decoded block -> mention -> capture -> context
// (structure index + analysis overlay) -> binding candidate -> inspection.
// Every hop keeps its own source-local UTF-8 anchor, no anchor crosses a block
// boundary, and a hop that cannot be proven ends in a typed non-resolved
// outcome instead of a confident binding.
// ---------------------------------------------------------------------------

fn consultant_reference_fixture() -> Vec<u8> {
    r#"<w:wordDocument xmlns:w="urn:word"><w:body><w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Статья 5.</w:t></w:r></w:p><w:p><w:r><w:t>Действует федеральный закон от 01.01.2020 N 1-ФЗ.</w:t></w:r></w:p></w:body></w:wordDocument>"#
        .as_bytes()
        .to_vec()
}

fn garant_reference_package() -> Vec<u8> {
    let content_xml = format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text><text:h text:style-name="Heading_20_1">Статья 6.</text:h><text:p text:style-name="Standard">Применяется федеральный закон от 02.02.2021 N 2-ФЗ.</text:p></office:text></office:body></office:document-content>"#
    );
    let mut writer = ZipWriter::new(Cursor::new(Vec::new()));
    let options = SimpleFileOptions::default().compression_method(CompressionMethod::Deflated);
    writer
        .start_file("content.xml", options)
        .expect("test content.xml entry");
    writer
        .write_all(content_xml.as_bytes())
        .expect("test content.xml bytes");
    writer.finish().expect("finish test ZIP").into_inner()
}

fn decode_blocks<D: BlockDecoderPort>(
    decoder: &D,
    family: &str,
    bytes: &[u8],
    payload: &str,
) -> Vec<ParsedBlock> {
    let request = DecodeRequest::new(
        PayloadRef::parse(payload).expect("payload ref"),
        FamilyFormat::parse(family).expect("family format"),
        bytes,
    );
    decoder.decode_blocks(&request).expect("own-family fixture")
}

#[derive(Debug)]
struct VerticalTrace {
    written: String,
    capture_anchor: (usize, usize),
    overlay_mention_anchor: (usize, usize),
    candidate_anchor: (usize, usize),
    candidate_status: BindingStatus,
    inspection_status: ContextStatus,
    inspection_anchor: (usize, usize),
    frame_ref: String,
}

/// Walk the whole vertical for one provider and return the trace. Panics
/// (with the S04 identifier in the message) when a hop cannot be proven.
fn run_reference_vertical(provider: &'static str, blocks: &[ParsedBlock]) -> VerticalTrace {
    let version = DocumentVersionRef::try_new(
        format!("{provider}-doc-v1"),
        format!("{provider}-rev-1"),
        "m206-s07-runtime-admission".to_owned(),
    )
    .expect("fixture document version");
    let index = build_document_structure_index(version, blocks).unwrap_or_else(|error| {
        panic!("F12-VERTICAL-POSITIVE: {provider} index failed: {error:?}")
    });

    // hop 1 (mention): the provider's own decoded text carries the citation.
    let mut cited_index = None;
    let mut cited_text = "";
    let mut captures = None;
    for (position, block) in blocks.iter().enumerate() {
        let batch = capture_lawrefs(block.text());
        if !batch.is_empty() {
            cited_index = Some(position);
            cited_text = block.text();
            captures = Some(batch);
            break;
        }
    }
    let (cited_index, captures) = match (cited_index, captures) {
        (Some(position), Some(batch)) => (position, batch),
        _ => panic!("F12-VERTICAL-POSITIVE: {provider} fixture must encode a citation mention"),
    };
    let block_id = ln_decode::document_context::BlockId::parse(&format!("block-{cited_index}"))
        .expect("fixture block id");
    let capture = captures
        .captures()
        .first()
        .expect("F12-VERTICAL-POSITIVE: the citation must be captured");

    // hop 2 (capture): the capture keeps the original UTF-8 span of the mention.
    let capture_anchor = (capture.span.start(), capture.span.end());
    let written = cited_text[capture_anchor.0..capture_anchor.1].to_owned();

    // hop 3 (context): the overlay mention node carries exactly that anchor, and
    // the block's own act frame carries its own local anchor.
    let frames = extract_act_list_frames(cited_text, &captures);
    assert!(
        !frames.is_empty(),
        "F12-VERTICAL-POSITIVE: {provider} must admit a local grammar frame"
    );
    let overlay = build_document_analysis_overlay(
        &index,
        &[(block_id.clone(), frames.clone(), Vec::new())],
        &[(block_id.clone(), captures.captures().to_vec())],
    )
    .unwrap_or_else(|error| panic!("F12-VERTICAL-POSITIVE: {provider} overlay failed: {error:?}"));
    let mention_node = overlay
        .mentions()
        .iter()
        .find(|node| node.block_id == block_id && node.local_anchor == capture.span)
        .unwrap_or_else(|| {
            panic!("F12-VERTICAL-POSITIVE: {provider} overlay must carry the captured mention")
        });
    let overlay_mention_anchor = (
        mention_node.local_anchor.start(),
        mention_node.local_anchor.end(),
    );

    // hop 4 (binding candidate): the mention anchor is reused byte-for-byte and
    // the endpoint anchor is source-local.
    let candidate = ReferenceBindingCandidate::new(
        TemporalTextSpan::new(overlay_mention_anchor.0, overlay_mention_anchor.1)
            .expect("mention anchor"),
        format!("{provider}:act"),
        BoundTarget::Claim(format!("{provider}:claim")),
        BindingEndpoints::Single(
            ReferenceEndpoint::new(
                written.clone(),
                TemporalTextSpan::new(capture_anchor.0, capture_anchor.1).expect("endpoint anchor"),
            )
            .expect("endpoint value"),
        ),
    )
    .expect("binding candidate");
    let candidate_anchor = (
        candidate.mention_anchor().start(),
        candidate.mention_anchor().end(),
    );

    // hop 5 (inspection): the local frame is addressable and returns an anchor.
    let frame_ref = format!("{}-frame-0", block_id.as_str());
    let outcome = explicit_anchor_lookup(&overlay, &frame_ref);

    VerticalTrace {
        written,
        capture_anchor,
        overlay_mention_anchor,
        candidate_anchor,
        candidate_status: candidate.status(),
        inspection_status: outcome.status,
        inspection_anchor: outcome
            .candidates
            .first()
            .and_then(|leaf| leaf.evidence.first())
            .map(|span| (span.start(), span.end()))
            .unwrap_or((0, 0)),
        frame_ref,
    }
}

fn assert_vertical_positive(provider: &'static str, blocks: &[ParsedBlock]) {
    let trace = run_reference_vertical(provider, blocks);
    assert_eq!(
        trace.overlay_mention_anchor, trace.capture_anchor,
        "F12-VERTICAL-POSITIVE: {provider} mention and capture anchors must agree"
    );
    assert_eq!(
        trace.candidate_anchor, trace.capture_anchor,
        "F12-VERTICAL-POSITIVE: {provider} binding candidate must reuse the captured anchor"
    );
    assert_eq!(
        trace.candidate_status,
        BindingStatus::Proposed,
        "F12-VERTICAL-POSITIVE: {provider} candidate stays a proposal"
    );
    assert_eq!(
        trace.inspection_status,
        ContextStatus::Resolved,
        "F12-VERTICAL-POSITIVE: {provider} inspection must resolve the proven frame"
    );
    assert!(
        trace.inspection_anchor.1 > trace.inspection_anchor.0,
        "F12-VERTICAL-POSITIVE: {provider} inspection must return a source-local anchor"
    );
    assert!(
        !trace.written.is_empty() && trace.frame_ref.ends_with("-frame-0"),
        "F12-VERTICAL-POSITIVE: {provider} must keep the written mention and address the local frame"
    );
    assert!(
        trace.frame_ref.starts_with("block-"),
        "F12-VERTICAL-POSITIVE: {provider} inspection addresses a decoded block frame"
    );
}

#[test]
fn rc28_f12_s04_f12_vertical_positive_composes_for_consultant() {
    let bytes = consultant_reference_fixture();
    let blocks = decode_blocks(
        &ConsultantWordMlBlockDecoder,
        "family:consultant-wordml",
        &bytes,
        "payload:m206-s07-f12-consultant",
    );
    assert!(
        blocks
            .iter()
            .all(|block| block.source_format() == SourceFormatId::ConsultantWordMl),
        "F12-VERTICAL-POSITIVE: the Consultant vertical keeps its provider format"
    );
    assert!(
        blocks
            .iter()
            .any(|block| block.style() == ParagraphStyle::Title),
        "F12-VERTICAL-POSITIVE: the Consultant fixture carries a structural heading"
    );
    assert_vertical_positive("consultant", &blocks);
}

#[test]
fn rc28_f12_s04_f12_vertical_positive_composes_for_garant() {
    let package = garant_reference_package();
    let blocks = decode_blocks(
        &GarantOdtBlockDecoder,
        "family:garant-odt",
        &package,
        "payload:m206-s07-f12-garant",
    );
    assert!(
        blocks
            .iter()
            .all(|block| block.source_format() == SourceFormatId::GarantOdt),
        "F12-VERTICAL-POSITIVE: the Garant vertical keeps its provider format"
    );
    assert!(
        blocks
            .iter()
            .any(|block| block.style() == ParagraphStyle::Heading),
        "F12-VERTICAL-POSITIVE: the Garant fixture carries a structural heading"
    );
    assert_vertical_positive("garant", &blocks);
}

#[test]
fn rc28_f12_s04_f12_vertical_negative_missing_context_stays_typed_unknown() {
    // F12-VERTICAL-NEGATIVE: a missing or unproven context hop must never be
    // reported as a confident binding. The candidate is retained and the
    // outcome is the typed context terminal.
    let bytes = consultant_reference_fixture();
    let blocks = decode_blocks(
        &ConsultantWordMlBlockDecoder,
        "family:consultant-wordml",
        &bytes,
        "payload:m206-s07-f12-consultant-negative",
    );
    let version = DocumentVersionRef::try_new(
        "consultant-doc-v1".to_owned(),
        "consultant-rev-1".to_owned(),
        "m206-s07-runtime-admission".to_owned(),
    )
    .expect("fixture document version");
    let index = build_document_structure_index(version, &blocks).expect("fixture index");
    let overlay = build_document_analysis_overlay(&index, &[], &[]).expect("empty overlay");

    // (a) an unknown frame reference is a typed Unavailable, not a resolution.
    let missing = explicit_anchor_lookup(&overlay, "block-0-frame-0");
    assert_eq!(
        missing.status,
        ContextStatus::Unavailable,
        "F12-VERTICAL-NEGATIVE: a missing frame must stay typed Unavailable"
    );
    assert!(
        missing.candidates.is_empty(),
        "F12-VERTICAL-NEGATIVE: a missing frame must not mint a candidate"
    );
    // The decode context terminal maps into the binding vocabulary without
    // merging the two crates' terminals: an unproven hop is carried across as
    // `BindingUnresolvedReason::ContextTerminal`.
    let binding = ln_temporal::identity_binding::BindingOutcome::Unresolved {
        reason: BindingUnresolvedReason::ContextTerminal(
            ln_temporal::document_context::Terminal::Unavailable,
        ),
    };
    match binding {
        ln_temporal::identity_binding::BindingOutcome::Unresolved { reason } => assert_eq!(
            reason,
            BindingUnresolvedReason::ContextTerminal(
                ln_temporal::document_context::Terminal::Unavailable
            ),
            "F12-VERTICAL-NEGATIVE: the unproven hop is retained as the typed context terminal"
        ),
        _ => panic!("F12-VERTICAL-NEGATIVE: a missing context must not produce a binding"),
    }

    // (b) an empty key is refused the same way: no wildcard resolution.
    let empty_key = explicit_anchor_lookup(&overlay, "");
    assert_eq!(
        empty_key.status,
        ContextStatus::Unavailable,
        "F12-VERTICAL-NEGATIVE: an empty key must not resolve"
    );
    assert!(empty_key.candidates.is_empty());
}

#[test]
fn rc28_f12_s04_f12_context_separation_isolates_providers() {
    // Provider isolation: the two adapters own disjoint family formats, refuse
    // each other's payload, and their mention anchors live in separate
    // documents, so neither provider's evidence can authorize the other.
    let consultant_bytes = consultant_reference_fixture();
    let garant_bytes = garant_reference_package();
    let consultant_blocks = decode_blocks(
        &ConsultantWordMlBlockDecoder,
        "family:consultant-wordml",
        &consultant_bytes,
        "payload:m206-s07-f12-consultant-isolation",
    );
    let garant_blocks = decode_blocks(
        &GarantOdtBlockDecoder,
        "family:garant-odt",
        &garant_bytes,
        "payload:m206-s07-f12-garant-isolation",
    );
    assert_ne!(
        consultant_blocks[0].source_format(),
        garant_blocks[0].source_format(),
        "F12-CONTEXT-SEPARATION: the pipelines are provider-specific"
    );

    let foreign_family_consultant = DecodeRequest::new(
        PayloadRef::parse("payload:m206-s07-f12-foreign-consultant").expect("payload"),
        FamilyFormat::parse("family:garant-odt").expect("family"),
        &consultant_bytes,
    );
    let refusal = ConsultantWordMlBlockDecoder
        .decode_blocks(&foreign_family_consultant)
        .expect_err("consultant adapter must refuse the garant family");
    assert_eq!(
        refusal.kind(),
        BlockDecodeErrorKind::UnsupportedFormat,
        "F12-CONTEXT-SEPARATION: Consultant must fail closed on the Garant payload"
    );

    let foreign_family_garant = DecodeRequest::new(
        PayloadRef::parse("payload:m206-s07-f12-foreign-garant").expect("payload"),
        FamilyFormat::parse("family:consultant-wordml").expect("family"),
        &consultant_bytes,
    );
    let refusal = GarantOdtBlockDecoder
        .decode_blocks(&foreign_family_garant)
        .expect_err("garant adapter must refuse the consultant payload");
    assert!(
        matches!(
            refusal.kind(),
            BlockDecodeErrorKind::InvalidPackage
                | BlockDecodeErrorKind::MissingContentXml
                | BlockDecodeErrorKind::UnsupportedFormat
        ),
        "F12-CONTEXT-SEPARATION: Garant must fail closed on the Consultant payload, got {:?}",
        refusal.kind()
    );

    // The two contexts are separate documents: the consultant mention anchor is
    // never addressable in the garant overlay.
    let consultant_trace = run_reference_vertical("consultant", &consultant_blocks);
    let garant_trace = run_reference_vertical("garant", &garant_blocks);
    assert_ne!(
        consultant_trace.written, garant_trace.written,
        "F12-CONTEXT-SEPARATION: the two providers cite different acts"
    );
    assert_eq!(
        consultant_trace.inspection_status,
        ContextStatus::Resolved,
        "F12-CONTEXT-SEPARATION: consultant vertical resolves in its own context"
    );
    assert_eq!(
        garant_trace.inspection_status,
        ContextStatus::Resolved,
        "F12-CONTEXT-SEPARATION: garant vertical resolves in its own context"
    );
    assert_ne!(
        consultant_trace.candidate_anchor.0, garant_trace.candidate_anchor.0,
        "F12-CONTEXT-SEPARATION: bindings stay inside their own provider's anchors"
    );
}
