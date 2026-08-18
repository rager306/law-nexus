use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{
        DecodeRequest, FamilyFormat, HierarchyLevel, ParagraphStyle, ParsedBlock, PayloadRef,
        SourceFormatId, SourceLocation, SourceSpan, SourceStreamId, TextSpan,
    },
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};

fn block(text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        ParagraphStyle::Heading,
        SourceLocation::new(
            SourceStreamId::parse("fixture:hierarchy").unwrap(),
            SourceSpan::try_new(500, 900).expect("independent artifact span"),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid parsed block")
}

#[test]
fn extracts_bounded_russian_hierarchy_markers_with_exact_text_spans() {
    let cases = [
        (
            "РАЗДЕЛ I. ОБЩИЕ ПОЛОЖЕНИЯ",
            "РАЗДЕЛ I.",
            HierarchyLevel::Razdel,
            "I",
            Some("ОБЩИЕ ПОЛОЖЕНИЯ"),
        ),
        (
            "  Глава IV. Общие положения",
            "Глава IV.",
            HierarchyLevel::Glava,
            "IV",
            Some("Общие положения"),
        ),
        (
            "§ 3. Основные понятия",
            "§ 3.",
            HierarchyLevel::Paragraph,
            "3",
            Some("Основные понятия"),
        ),
        (
            "Статья 5.1. Сфера применения",
            "Статья 5.1.",
            HierarchyLevel::Statya,
            "5.1",
            Some("Сфера применения"),
        ),
    ];

    for (text, marker, level, number, title) in cases {
        let node = extract_hierarchy(&block(text)).expect("bounded marker");
        let marker_start = text.find(marker).expect("marker in fixture");
        let marker_end = marker_start + marker.len();
        assert_eq!(node.level(), level);
        assert_eq!(node.number(), number);
        assert_eq!(node.title(), title);
        assert_eq!(node.text(), text);
        assert_eq!(
            node.marker_span(),
            TextSpan::try_new(marker_start, marker_end).unwrap()
        );
    }
}

#[test]
fn marker_without_title_remains_valid_and_does_not_infer_one() {
    let node = extract_hierarchy(&block("Статья 7.")).expect("bounded marker");

    assert_eq!(node.number(), "7");
    assert_eq!(node.title(), None);
    assert_eq!(node.marker_span(), TextSpan::try_new(0, 15).unwrap());
}

#[test]
fn extracts_compound_punkt_number() {
    let node =
        extract_hierarchy(&block("4.1) поставщик подрядчик исполнитель")).expect("compound punkt");
    assert_eq!(node.level(), HierarchyLevel::Punkt);
    assert_eq!(node.number(), "4.1");
}

#[test]
fn extracts_compound_chast_number() {
    let node = extract_hierarchy(&block("4.1. Поставщик определяется по результатам"))
        .expect("compound chast");
    assert_eq!(node.level(), HierarchyLevel::Chast);
    assert_eq!(node.number(), "4.1");
}

#[test]
fn prose_missing_numbers_and_unsupported_context_do_not_become_hierarchy() {
    for text in [
        "В статье 5 описаны требования.",
        "Статья без номера",
        "Статья IV. Не numeric article",
        "Статья 5.Текст без разделителя",
        "Статья 5.. Двойная точка",
        "Глава",
        "§ IV. Не numeric paragraph",
        "Часть 1. Общие положения",
        "Подпункт а) применяется.",
        // Note: "1. Общие положения" and "а) текст" are now VALID numbered
        // markers (Chast/Podpunkt) extracted by numbered_marker_prefix.
        // They are filtered downstream by the registry lift (Unknown if unregistered).
    ] {
        assert_eq!(extract_hierarchy(&block(text)), None, "fixture={text}");
    }
}

#[test]
fn structural_only_surface_markers_are_not_hierarchy_levels() {
    // R8-09 hostile: primechanie/prilozhenie are role tokens with catalog
    // `surface` markers ("Примечание"/"Приложение") — they have no decode
    // HierarchyLevel, so extract_hierarchy must return None (Unknown). A
    // bare "Приложение" without a number is Unknown; the note marker
    // "Примечание" never produces a hierarchy node (no CC source). The
    // profile collector recognizes them by surface prefix (article_body.rs),
    // never here.
    for text in [
        "Приложение",
        "Приложение N 1",
        "Приложение 1",
        "Приложение к приказу",
        "Примечание",
        "Примечание 1.",
        "примечание",
        "приложение 1",
        "Примечания к пункту",
    ] {
        assert_eq!(extract_hierarchy(&block(text)), None, "fixture={text}");
    }
}

#[test]
fn razdel_marker_still_decodes_for_code_group_documents() {
    // R8-08: razdel is active only in the code ladder — the decode catalog
    // keeps the РАЗДЕЛ prefix so code documents (ГК, НК, УК, ...) still
    // extract. The profile-ladder assertion (federal_law@v1 declares no
    // razdel) lives in document_groups_catalog.
    let node = extract_hierarchy(&block("Раздел I. Общие положения"))
        .expect("code-group razdel still decodes");
    assert_eq!(node.level(), HierarchyLevel::Razdel);
    assert_eq!(node.number(), "I");
    assert_eq!(node.title(), Some("Общие положения"));
}

#[test]
fn consultant_block_feeds_shared_hierarchy_without_coordinate_translation() {
    let xml = r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Статья 9. Полномочия</w:t></w:r></w:p></w:wordDocument>"#;
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:hierarchy-integration").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml.as_bytes(),
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("valid bounded WordML");
    let block = blocks.first().expect("one parsed block");
    let node = extract_hierarchy(block).expect("bounded article marker");

    assert_eq!(block.source_location().stream().as_str(), "artifact:whole");
    let span = block.source_location().span();
    let artifact = &xml.as_bytes()[span.start()..span.end()];
    assert!(artifact.starts_with(b"<w:p>"));
    assert!(artifact.ends_with(b"</w:p>"));
    assert_eq!(node.marker_span(), TextSpan::try_new(0, 15).unwrap());
    assert_eq!(&block.text().as_bytes()[0..15], "Статья 9.".as_bytes());
}

#[test]
fn artifact_span_is_not_reused_as_decoded_marker_span() {
    let parsed = block("Статья 2. Текст");
    let source_location = parsed.source_location();
    let node = extract_hierarchy(&parsed).expect("bounded marker");

    assert_eq!(source_location.stream().as_str(), "fixture:hierarchy");
    assert_eq!(
        source_location.span(),
        SourceSpan::try_new(500, 900).unwrap()
    );
    assert_eq!(node.marker_span(), TextSpan::try_new(0, 15).unwrap());
}
