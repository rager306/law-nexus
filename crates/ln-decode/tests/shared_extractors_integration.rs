use ln_decode::{
    deontic::extract_deontic_lexemes,
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    },
    references::extract_reference_mentions,
    temporal::extract_temporal_phrases,
};

const TEXT: &str =
    "По статье 5.1 орган не вправе изменять акт, который утрачивает силу; пункт 2 вступает в силу.";

fn block(format: SourceFormatId, style: ParagraphStyle) -> ParsedBlock {
    let stream = match format {
        SourceFormatId::ConsultantWordMl => "artifact:whole",
        SourceFormatId::GarantOdt => "package-member:content.xml",
    };
    ParsedBlock::try_new(
        TEXT.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse(stream).unwrap(),
            SourceSpan::try_new(100, 500).unwrap(),
        ),
        format,
    )
    .unwrap()
}

#[test]
fn identical_decoded_text_has_identical_candidates_but_distinct_source_identity() {
    let consultant = block(SourceFormatId::ConsultantWordMl, ParagraphStyle::BodyText);
    let garant = block(SourceFormatId::GarantOdt, ParagraphStyle::BodyText);

    assert_eq!(
        extract_reference_mentions(&consultant),
        extract_reference_mentions(&garant)
    );
    assert_eq!(
        extract_temporal_phrases(&consultant),
        extract_temporal_phrases(&garant)
    );
    assert_eq!(
        extract_deontic_lexemes(&consultant),
        extract_deontic_lexemes(&garant)
    );
    assert_eq!(extract_reference_mentions(&consultant).len(), 2);
    assert_eq!(extract_temporal_phrases(&consultant).len(), 2);
    assert_eq!(extract_deontic_lexemes(&consultant).len(), 1);

    assert_ne!(consultant.source_format(), garant.source_format());
    assert_ne!(
        consultant.source_location().stream(),
        garant.source_location().stream()
    );
    assert_eq!(
        consultant.source_location().span(),
        garant.source_location().span()
    );
}

#[test]
fn provider_comments_are_excluded_for_both_provider_identities() {
    for format in [SourceFormatId::ConsultantWordMl, SourceFormatId::GarantOdt] {
        let comment = block(format, ParagraphStyle::ProviderComment);
        assert!(extract_reference_mentions(&comment).is_empty());
        assert!(extract_temporal_phrases(&comment).is_empty());
        assert!(extract_deontic_lexemes(&comment).is_empty());
    }
}
