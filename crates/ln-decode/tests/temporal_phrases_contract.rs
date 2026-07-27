use ln_decode::{
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
        TextSpan,
    },
    temporal::{extract_temporal_phrases, TemporalPhraseKind},
};

fn block(text: &str, style: ParagraphStyle) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:temporal-phrases").unwrap(),
            SourceSpan::try_new(100, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

#[test]
fn extracts_all_bounded_forms_in_source_order_with_exact_utf8_spans() {
    let text = "Акт вступает в силу; закон вступил в силу; нормы вступают в силу. Положение утрачивает силу, приказ утратил силу, а правила утрачивают силу.";

    let phrases = extract_temporal_phrases(&block(text, ParagraphStyle::BodyText));

    assert_eq!(phrases.len(), 6);
    assert_eq!(phrases[0].kind(), TemporalPhraseKind::EntersIntoForce);
    assert_eq!(phrases[1].kind(), TemporalPhraseKind::EntersIntoForce);
    assert_eq!(phrases[2].kind(), TemporalPhraseKind::EntersIntoForce);
    assert_eq!(phrases[3].kind(), TemporalPhraseKind::LosesForce);
    assert_eq!(phrases[4].kind(), TemporalPhraseKind::LosesForce);
    assert_eq!(phrases[5].kind(), TemporalPhraseKind::LosesForce);

    let expected = [
        "вступает в силу",
        "вступил в силу",
        "вступают в силу",
        "утрачивает силу",
        "утратил силу",
        "утрачивают силу",
    ];
    for index in 0..expected.len() {
        let span = phrases[index].text_span();
        assert_eq!(&text[span.start()..span.end()], expected[index]);
    }
}

#[test]
fn matches_case_insensitively_and_accepts_horizontal_whitespace() {
    let text = "ВСТУПАЕТ\tВ   СИЛУ; УтРаЧиВаЕт\tСиЛу.";

    let phrases = extract_temporal_phrases(&block(text, ParagraphStyle::BodyText));

    assert_eq!(phrases.len(), 2);
    assert_eq!(phrases[0].kind(), TemporalPhraseKind::EntersIntoForce);
    assert_eq!(phrases[1].kind(), TemporalPhraseKind::LosesForce);
}

#[test]
fn rejects_line_breaks_punctuation_intervening_words_and_incomplete_forms() {
    let text = "вступает\nв силу; вступает, в силу; вступает немедленно в силу; вступает в полную силу; вступает в; утрачивает\nсилу; утрачивает, силу; утрачивает свою силу; утрачивает";

    assert!(extract_temporal_phrases(&block(text, ParagraphStyle::BodyText)).is_empty());
}

#[test]
fn rejects_embedded_and_unsupported_verb_forms() {
    let text = "невступает в силу; вступление в силу; вступала в силу; утрачивающий силу; утрата силы; переутрачивает силу";

    assert!(extract_temporal_phrases(&block(text, ParagraphStyle::BodyText)).is_empty());
}

#[test]
fn lexical_negation_does_not_invent_temporal_polarity() {
    let text = "Акт не вступает в силу, но норма не утрачивает силу.";

    let phrases = extract_temporal_phrases(&block(text, ParagraphStyle::BodyText));

    assert_eq!(phrases.len(), 2);
    assert_eq!(phrases[0].kind(), TemporalPhraseKind::EntersIntoForce);
    assert_eq!(phrases[1].kind(), TemporalPhraseKind::LosesForce);
}

#[test]
fn excludes_provider_comments_and_is_repeat_deterministic() {
    let body = block(
        "Вступает в силу и утрачивает силу.",
        ParagraphStyle::BodyText,
    );
    let comment = block(
        "Вступает в силу и утрачивает силу.",
        ParagraphStyle::ProviderComment,
    );

    let first = extract_temporal_phrases(&body);
    let second = extract_temporal_phrases(&body);

    assert_eq!(first, second);
    assert_eq!(first.len(), 2);
    assert!(extract_temporal_phrases(&comment).is_empty());
    let first_phrase = "Вступает в силу";
    assert_eq!(
        first[0].text_span(),
        TextSpan::try_new(0, first_phrase.len()).unwrap()
    );
}
