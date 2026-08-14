use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{DecodeRequest, FamilyFormat, PayloadRef};
use ln_decode::hierarchy::extract_hierarchy;
use ln_decode::ports::BlockDecoderPort;

#[test]
fn entity_167_decodes_to_section_sign() {
    let xml = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:wordDocument xmlns:w="urn:word"><w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>&#167; 1. Общие положения</w:t></w:r></w:p></w:wordDocument>"#;
    let req = DecodeRequest::new(
        PayloadRef::parse("payload:entity").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml.as_bytes(),
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&req)
        .expect("decode");
    let text = blocks[0].text();
    println!("DECODED: {text:?}");
    assert!(
        text.contains('\u{00a7}'),
        "§ (U+00A7) must be present after entity decode; got: {text:?}"
    );
    assert!(
        !text.contains("&#167;"),
        "raw entity must not survive decode; got: {text:?}"
    );
}

#[test]
fn paragraph_marker_extracted_from_entity() {
    let xml = r#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:wordDocument xmlns:w="urn:word"><w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>&#167; 1. Общие положения</w:t></w:r></w:p></w:wordDocument>"#;
    let req = DecodeRequest::new(
        PayloadRef::parse("payload:para").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml.as_bytes(),
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&req)
        .expect("decode");
    let node = extract_hierarchy(&blocks[0]);
    println!("HIERARCHY: {node:?}");
    assert!(node.is_some(), "§ 1 must be extracted as Paragraph marker");
    let node = node.unwrap();
    assert_eq!(node.number(), "1");
}
