use std::io::{Cursor, Write};

use ln_decode::{
    adapters::garant_odt::GarantOdtBlockDecoder,
    application::DecodeBlocks,
    domain::{DecodeRequest, FamilyFormat, HierarchyLevel, ParagraphStyle, PayloadRef, TextSpan},
    hierarchy::extract_hierarchy,
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

fn request(bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:garant-hierarchy-integration").unwrap(),
        FamilyFormat::parse("family:garant-odt").unwrap(),
        bytes,
    )
}

fn content_xml() -> String {
    format!(
        r#"<office:document-content xmlns:office="{OFFICE_NS}" xmlns:text="{TEXT_NS}"><office:body><office:text><text:h text:style-name="Heading_20_1">РАЗДЕЛ I. ОБЩИЕ ПОЛОЖЕНИЯ</text:h><text:h text:style-name="Heading_20_2">Глава IV. Полномочия</text:h><text:p text:style-name="Standard">§ 3. Основные понятия</text:p><text:p text:style-name="Standard"><text:s text:c="2"/>Статья 5.1. Сфера применения</text:p><text:p text:style-name="Standard">В статье 5 описаны требования.</text:p><text:p text:style-name="s9">Комментарий поставщика</text:p></office:text></office:body></office:document-content>"#
    )
}

#[test]
fn garant_blocks_feed_shared_hierarchy_without_coordinate_translation_or_coupling() {
    let xml = content_xml();
    let bytes = package(&xml);
    let use_case = DecodeBlocks::new(GarantOdtBlockDecoder);

    let first = use_case
        .execute(&request(&bytes))
        .expect("bounded Garant ODT hierarchy fixture");
    let second = use_case
        .execute(&request(&bytes))
        .expect("repeat bounded Garant ODT hierarchy fixture");

    assert_eq!(first, second, "repeat decode must be deterministic");
    assert_eq!(first.len(), 6);

    let expected = [
        Some((HierarchyLevel::Razdel, "I", Some("ОБЩИЕ ПОЛОЖЕНИЯ"))),
        Some((HierarchyLevel::Glava, "IV", Some("Полномочия"))),
        Some((HierarchyLevel::Paragraph, "3", Some("Основные понятия"))),
        Some((HierarchyLevel::Statya, "5.1", Some("Сфера применения"))),
        None,
        None,
    ];

    for (block, expected_node) in first.iter().zip(expected) {
        assert_eq!(
            block.source_location().stream().as_str(),
            "package-member:content.xml"
        );
        let source_span = block.source_location().span();
        let source = &xml.as_bytes()[source_span.start()..source_span.end()];
        assert!(source.starts_with(b"<text:"));
        assert!(source.ends_with(b">"));

        let node = extract_hierarchy(block);
        match expected_node {
            Some((level, number, title)) => {
                let node = node.expect("supported bounded hierarchy marker");
                assert_eq!(node.level(), level);
                assert_eq!(node.number(), number);
                assert_eq!(node.title(), title);

                let marker = match level {
                    HierarchyLevel::Razdel => "РАЗДЕЛ I.",
                    HierarchyLevel::Glava => "Глава IV.",
                    HierarchyLevel::Paragraph => "§ 3.",
                    HierarchyLevel::Statya => "Статья 5.1.",
                    _ => unreachable!("only bounded hierarchy levels are expected"),
                };
                let start = block.text().find(marker).expect("marker in decoded block");
                assert_eq!(
                    node.marker_span(),
                    TextSpan::try_new(start, start + marker.len()).unwrap()
                );
                assert!(node.marker_span().end() <= block.text().len());
            }
            None => assert_eq!(node, None),
        }
    }

    assert_eq!(first[3].text(), "  Статья 5.1. Сфера применения");
    assert!(first[3].source_location().span().start() < first[3].source_location().span().end());
    assert!(first[3].source_location().span().len() > first[3].text().len());
    assert_eq!(first[5].style(), ParagraphStyle::ProviderComment);
    assert_eq!(extract_hierarchy(&first[5]), None);
}
