use std::io::{Cursor, Write};

use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    application::DecodeBlocks,
    domain::{
        BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat, ParagraphStyle, PayloadRef,
        SourceFormatId,
    },
};
use zip::{write::SimpleFileOptions, CompressionMethod, ZipWriter};

const OFFICE_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:office:1.0";
const TEXT_NS: &str = "urn:oasis:names:tc:opendocument:xmlns:text:1.0";

fn package(content_xml: &str) -> Vec<u8> {
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

fn request(bytes: &[u8], family: &str) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:garant-odt-block-test").unwrap(),
        FamilyFormat::parse(family).unwrap(),
        bytes,
    )
}

fn document(body: &str) -> String {
    format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text>{body}</office:text></office:body></office:document-content>"#
    )
}

fn decode(
    content_xml: &str,
) -> Result<Vec<ln_decode::domain::ParsedBlock>, ln_decode::domain::BlockDecodeError> {
    let bytes = package(content_xml);
    DecodeBlocks::new(GarantOdtBlockDecoder).execute(&request(&bytes, "family:garant-odt"))
}

fn assert_parse_error(content_xml: &str) {
    let error = decode(content_xml).expect_err("hostile content.xml must fail atomically");
    assert_eq!(error.phase(), DecodePhase::Parse);
    assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    assert!(!error.to_string().contains("CANARY"));
    assert!(!format!("{error:?}").contains("CANARY"));
}

#[test]
fn emits_headings_paragraphs_nested_spans_and_bounded_odf_spaces() {
    let xml = document(
        r#"<text:h text:style-name="Heading_20_1">Статья 1.<text:s text:c="2"/>Название</text:h><text:p text:style-name="Standard">Текст <text:span text:style-name="Emphasis">абзаца</text:span>.</text:p><text:p text:style-name="s9">Комментарий</text:p>"#,
    );

    let blocks = decode(&xml).expect("valid bounded ODF content");

    assert_eq!(blocks.len(), 3);
    assert_eq!(blocks[0].text(), "Статья 1.  Название");
    assert_eq!(blocks[0].provider_style_id(), Some("Heading_20_1"));
    assert_eq!(blocks[0].style(), ParagraphStyle::Heading);
    assert_eq!(blocks[1].text(), "Текст абзаца.");
    assert_eq!(blocks[1].provider_style_id(), Some("Standard"));
    assert_eq!(blocks[1].style(), ParagraphStyle::BodyText);
    assert_eq!(blocks[2].style(), ParagraphStyle::ProviderComment);

    for block in &blocks {
        assert_eq!(block.source_format(), SourceFormatId::GarantOdt);
        assert_eq!(
            block.source_location().stream().as_str(),
            "package-member:content.xml"
        );
        let span = block.source_location().span();
        let source = &xml.as_bytes()[span.start()..span.end()];
        assert!(source.starts_with(b"<text:"));
        assert!(source.ends_with(b">"));
    }
    let heading_span = blocks[0].source_location().span();
    assert_eq!(
        &xml.as_bytes()[heading_span.start()..heading_span.end()],
        r#"<text:h text:style-name="Heading_20_1">Статья 1.<text:s text:c="2"/>Название</text:h>"#
            .as_bytes()
    );
}

#[test]
fn wrong_family_fails_before_package_or_xml_parsing() {
    let bytes = package(&document("<text:p>CANARY</text:p>"));
    let error = GarantOdtBlockDecoder
        .decode_blocks(&request(&bytes, "family:consultant-wordml"))
        .expect_err("wrong family must fail");

    assert_eq!(error.phase(), DecodePhase::Input);
    assert_eq!(error.kind(), BlockDecodeErrorKind::UnsupportedFormat);
    assert!(!error.to_string().contains("CANARY"));
}

#[test]
fn malformed_suffix_discards_previously_collected_blocks() {
    assert_parse_error(&document("<text:p>Первый блок</text:p><text:p>CANARY"));
}

#[test]
fn rejects_target_elements_outside_the_odf_text_namespace() {
    assert_parse_error(&format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="urn:wrong" xmlns:evil="urn:evil"><office:body><office:text><text:p>CANARY</text:p></office:text></office:body></office:document-content>"#
    ));
    assert_parse_error(&format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:evil="urn:evil"><office:body><office:text><evil:p>CANARY</evil:p></office:text></office:body></office:document-content>"#
    ));
}

#[test]
fn rejects_nested_blocks_unknown_text_semantics_and_invalid_space_expansion() {
    assert_parse_error(&document("<text:p>outer<text:p>CANARY</text:p></text:p>"));
    assert_parse_error(&document("<text:p>before<text:a>CANARY</text:a></text:p>"));
    assert_parse_error(&document("CANARY<text:p>block</text:p>"));
    assert_parse_error(&document(
        r#"<text:p>before<text:s text:c="65"/>CANARY</text:p>"#,
    ));
    assert_parse_error(&document(
        r#"<text:p>before<text:s text:c="zero"/>CANARY</text:p>"#,
    ));
}

#[test]
fn rejects_decoded_whitespace_amplification() {
    let spaces = r#"<text:s text:c="64"/>"#.repeat(16_385);
    assert_parse_error(&document(&format!("<text:p>{spaces}CANARY</text:p>")));
}

#[test]
fn rejects_missing_or_trailing_document_topology() {
    assert_parse_error(&format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"/>"#
    ));
    assert_parse_error(&format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text><text:p>first</text:p></office:text></office:body></office:document-content><evil:tail xmlns:evil="urn:evil">CANARY</evil:tail>"#
    ));
}

#[test]
fn rejects_doctype_and_custom_entity_input_without_resolution() {
    let xml = format!(
        r#"<!DOCTYPE office:document-content [<!ENTITY secret SYSTEM "file:///CANARY">]><office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text><text:p>&secret;</text:p></office:text></office:body></office:document-content>"#
    );
    assert_parse_error(&xml);
}

use ln_decode::ports::BlockDecoderPort;
