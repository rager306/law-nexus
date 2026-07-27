use ln_decode::{
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
        TextSpan,
    },
    references::{extract_reference_mentions, ReferenceMentionKind},
};

fn block(text: &str, style: ParagraphStyle) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:references").unwrap(),
            SourceSpan::try_new(100, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

#[test]
fn extracts_supported_forms_and_bounded_numbers_in_source_order() {
    let text = "По статье 5.1 и пунктам 2.3.4, а также статьёй 7 установлены правила.";

    let mentions = extract_reference_mentions(&block(text, ParagraphStyle::BodyText));

    assert_eq!(mentions.len(), 3);
    assert_eq!(mentions[0].kind(), ReferenceMentionKind::Article);
    assert_eq!(mentions[0].number(), "5.1");
    assert_eq!(
        &text[mentions[0].text_span().start()..mentions[0].text_span().end()],
        "статье 5.1"
    );
    assert_eq!(
        &text[mentions[0].term_span().start()..mentions[0].term_span().end()],
        "статье"
    );
    assert_eq!(
        &text[mentions[0].number_span().start()..mentions[0].number_span().end()],
        "5.1"
    );

    assert_eq!(mentions[1].kind(), ReferenceMentionKind::Point);
    assert_eq!(mentions[1].number(), "2.3.4");
    assert_eq!(
        &text[mentions[1].text_span().start()..mentions[1].text_span().end()],
        "пунктам 2.3.4"
    );

    assert_eq!(mentions[2].kind(), ReferenceMentionKind::Article);
    assert_eq!(mentions[2].number(), "7");
    assert_eq!(
        &text[mentions[2].text_span().start()..mentions[2].text_span().end()],
        "статьёй 7"
    );
}

#[test]
fn accepts_the_complete_bounded_inflection_dictionary() {
    let text = "статья 1 статьи 2 статье 3 статью 4 статей 5 статьёй 6 статьей 7 статьями 8 статьях 9 пункт 10 пункта 11 пункту 12 пунктом 13 пункте 14 пункты 15 пунктов 16 пунктам 17 пунктами 18 пунктах 19";

    let mentions = extract_reference_mentions(&block(text, ParagraphStyle::BodyText));

    assert_eq!(mentions.len(), 19);
    assert_eq!(mentions[0].kind(), ReferenceMentionKind::Article);
    assert_eq!(mentions[8].kind(), ReferenceMentionKind::Article);
    assert_eq!(mentions[9].kind(), ReferenceMentionKind::Point);
    assert_eq!(mentions[18].kind(), ReferenceMentionKind::Point);
    assert_eq!(mentions[18].number(), "19");
}

#[test]
fn accepts_horizontal_whitespace_but_not_line_broken_mentions() {
    let text = "статья\t5; пункт   6; статья\n7";

    let mentions = extract_reference_mentions(&block(text, ParagraphStyle::BodyText));

    assert_eq!(mentions.len(), 2);
    assert_eq!(mentions[0].number(), "5");
    assert_eq!(mentions[1].number(), "6");
}

#[test]
fn rejects_embedded_terms_and_ambiguous_or_malformed_numbers() {
    let text = "подстатья 1; пунктуация 2; статья V; статья -5; статья .5; статья 5..1; статья 5а; статья 5.а; пункт +2; пункт 3_1; статья без номера";

    assert!(extract_reference_mentions(&block(text, ParagraphStyle::BodyText)).is_empty());
}

#[test]
fn excludes_provider_comments_and_is_repeat_deterministic() {
    let body = block("Статья 44 и пункт 2.", ParagraphStyle::BodyText);
    let comment = block("Статья 44 и пункт 2.", ParagraphStyle::ProviderComment);

    let first = extract_reference_mentions(&body);
    let second = extract_reference_mentions(&body);

    assert_eq!(first, second);
    assert_eq!(first.len(), 2);
    assert!(extract_reference_mentions(&comment).is_empty());
    assert_eq!(first[0].text_span(), TextSpan::try_new(0, 15).unwrap());
    assert_eq!(first[1].number(), "2");
}
