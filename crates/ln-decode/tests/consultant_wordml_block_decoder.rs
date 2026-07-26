use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{
        BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat, ParagraphStyle, PayloadRef,
    },
    ports::BlockDecoderPort,
};

fn request(xml: &str) -> DecodeRequest {
    request_with_format(xml, "family:consultant-wordml")
}

fn request_with_format(xml: &str, family_format: &str) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:consultant-test").expect("valid payload ref"),
        FamilyFormat::parse(family_format).expect("valid family format"),
        xml.as_bytes(),
    )
}

#[test]
fn namespaced_paragraphs_emit_validated_blocks_with_artifact_spans() {
    let xml = r#"<w:wordDocument xmlns:w="urn:word"><w:body><w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Статья 1.</w:t></w:r></w:p><w:binData>AAAA</w:binData><w:p><w:pPr><w:pStyle w:val="99"/></w:pPr><w:r><w:t>Текст.</w:t></w:r></w:p></w:body></w:wordDocument>"#;

    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(xml))
        .expect("valid WordML");

    assert_eq!(blocks.len(), 2);
    assert_eq!(blocks[0].text(), "Статья 1.");
    assert_eq!(blocks[0].provider_style_id(), Some("2"));
    assert_eq!(blocks[0].style(), ParagraphStyle::Title);
    assert_eq!(blocks[1].style(), ParagraphStyle::Unknown);
    for block in &blocks {
        assert_eq!(block.source_location().stream().as_str(), "artifact:whole");
        let span = block.source_location().span();
        let source = &xml.as_bytes()[span.start()..span.end()];
        assert!(source.starts_with(b"<w:p>"));
        assert!(source.ends_with(b"</w:p>"));
        assert!(!source.windows(7).any(|part| part == b"binData"));
    }
}

#[test]
fn malformed_suffix_discards_previously_collected_blocks() {
    let xml = r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>Первый.</w:t></w:r></w:p><w:p><w:r><w:t>Сломан"#;

    let error = ConsultantWordMlBlockDecoder
        .decode_blocks(&request(xml))
        .expect_err("malformed XML must fail atomically");

    assert_eq!(error.phase(), DecodePhase::Parse);
    assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    assert!(error.byte_offset().is_some());
    assert!(!error.to_string().contains("Первый"));
}

#[test]
fn wrong_provider_format_is_rejected_before_parsing() {
    let error = ConsultantWordMlBlockDecoder
        .decode_blocks(&request_with_format("<root/>", "family:garant-odt"))
        .expect_err("provider-specific adapter must reject a different family format");

    assert_eq!(error.phase(), DecodePhase::Input);
    assert_eq!(error.kind(), BlockDecodeErrorKind::UnsupportedFormat);
    assert_eq!(error.byte_offset(), None);
}

#[test]
fn malformed_entity_and_attribute_fail_closed() {
    for xml in [
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>А &unknown; Б</w:t></w:r></w:p></w:wordDocument>"#,
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:pPr><w:pStyle w:val="2></w:pPr></w:p></w:wordDocument>"#,
    ] {
        let error = ConsultantWordMlBlockDecoder
            .decode_blocks(&request(xml))
            .expect_err("invalid XML detail must not be flattened");
        assert_eq!(error.phase(), DecodePhase::Parse);
        assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    }
}
