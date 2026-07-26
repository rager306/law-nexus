use ln_decode::domain::{
    HierarchyLevel, HierarchyNode, ParagraphStyle, ParsedBlock, ParserDomainError, SourceFormatId,
    SourceSpan, TextSpan,
};

#[test]
fn source_span_accepts_non_empty_ordered_offsets() {
    let span = SourceSpan::try_new(12, 37).expect("ordered non-empty span");

    assert_eq!(span.start(), 12);
    assert_eq!(span.end(), 37);
    assert_eq!(span.len(), 25);
}

#[test]
fn source_span_rejects_empty_or_reversed_offsets() {
    assert_eq!(
        SourceSpan::try_new(5, 5),
        Err(ParserDomainError::InvalidSourceSpan { start: 5, end: 5 })
    );
    assert_eq!(
        SourceSpan::try_new(9, 4),
        Err(ParserDomainError::InvalidSourceSpan { start: 9, end: 4 })
    );
}

#[test]
fn text_span_has_a_distinct_typed_failure_contract() {
    assert_eq!(
        TextSpan::try_new(7, 7),
        Err(ParserDomainError::InvalidTextSpan { start: 7, end: 7 })
    );
    let span = TextSpan::try_new(2, 9).expect("valid decoded text span");
    assert_eq!(span.start(), 2);
    assert_eq!(span.end(), 9);
    assert_eq!(span.len(), 7);
}

#[test]
fn parsed_block_preserves_provider_neutral_contract() {
    let block = ParsedBlock::try_new(
        "Статья 1. Предмет регулирования".to_owned(),
        Some("provider-style-42".to_owned()),
        ParagraphStyle::Heading,
        SourceSpan::try_new(100, 151).expect("valid span"),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid parsed block");

    assert_eq!(block.text(), "Статья 1. Предмет регулирования");
    assert_eq!(block.provider_style_id(), Some("provider-style-42"));
    assert_eq!(block.style(), ParagraphStyle::Heading);
    assert_eq!(block.source_span().start(), 100);
    assert_eq!(block.source_format(), SourceFormatId::ConsultantWordMl);
}

#[test]
fn parsed_block_rejects_empty_text_and_empty_provider_style() {
    let span = SourceSpan::try_new(0, 1).expect("valid span");
    assert_eq!(
        ParsedBlock::try_new(
            "  ".to_owned(),
            None,
            ParagraphStyle::BodyText,
            span,
            SourceFormatId::GarantOdt,
        ),
        Err(ParserDomainError::EmptyBlockText)
    );

    let span = SourceSpan::try_new(0, 4).expect("valid span");
    assert_eq!(
        ParsedBlock::try_new(
            "Текст".to_owned(),
            Some(" ".to_owned()),
            ParagraphStyle::BodyText,
            span,
            SourceFormatId::GarantOdt,
        ),
        Err(ParserDomainError::EmptyProviderStyleId)
    );
}

#[test]
fn hierarchy_node_encodes_level_number_title_text_and_decoded_marker_span() {
    let node = HierarchyNode::try_new(
        HierarchyLevel::Statya,
        "5.1".to_owned(),
        Some("Сфера применения".to_owned()),
        "Статья 5.1. Сфера применения".to_owned(),
        TextSpan::try_new(0, 11).expect("valid decoded marker span"),
    )
    .expect("valid hierarchy node");

    assert_eq!(node.level(), HierarchyLevel::Statya);
    assert_eq!(node.number(), "5.1");
    assert_eq!(node.title(), Some("Сфера применения"));
    assert_eq!(node.text(), "Статья 5.1. Сфера применения");
    assert_eq!(node.marker_span(), TextSpan::try_new(0, 11).unwrap());
}

#[test]
fn hierarchy_node_rejects_empty_title_or_text() {
    let span = TextSpan::try_new(1, 20).expect("valid decoded marker span");
    assert_eq!(
        HierarchyNode::try_new(
            HierarchyLevel::Glava,
            "2".to_owned(),
            Some(" ".to_owned()),
            "Глава 2".to_owned(),
            span,
        ),
        Err(ParserDomainError::EmptyHierarchyTitle)
    );

    let span = TextSpan::try_new(1, 20).expect("valid decoded marker span");
    assert_eq!(
        HierarchyNode::try_new(
            HierarchyLevel::Glava,
            "2".to_owned(),
            None,
            " ".to_owned(),
            span,
        ),
        Err(ParserDomainError::EmptyHierarchyText)
    );
}

#[test]
fn hierarchy_node_rejects_missing_marker_data_without_echoing_text() {
    let error = HierarchyNode::try_new(
        HierarchyLevel::Punkt,
        " ".to_owned(),
        None,
        "CANARY::RAW-LEGAL-TEXT".to_owned(),
        TextSpan::try_new(1, 20).expect("valid decoded marker span"),
    )
    .expect_err("empty hierarchy number must fail");

    assert_eq!(error, ParserDomainError::EmptyHierarchyNumber);
    assert!(!error.to_string().contains("CANARY"));
}
