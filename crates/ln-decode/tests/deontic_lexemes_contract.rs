use ln_decode::{
    deontic::{extract_deontic_lexemes, DeonticLexemeKind},
    domain::{
        ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    },
};

fn block(text: &str, style: ParagraphStyle) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:deontic").unwrap(),
            SourceSpan::try_new(10, 900).unwrap(),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .unwrap()
}

#[test]
fn maps_bounded_morphology_forms_in_source_order_with_exact_spans() {
    let text = "Орган обязан, организация обязана, лицо обязано, стороны обязаны; заказчик вправе; передача запрещается, действия запрещены.";
    let items = extract_deontic_lexemes(&block(text, ParagraphStyle::BodyText));
    assert_eq!(items.len(), 7);
    assert_eq!(items[0].kind(), DeonticLexemeKind::Obligation);
    assert_eq!(items[4].kind(), DeonticLexemeKind::Permission);
    assert_eq!(items[5].kind(), DeonticLexemeKind::Prohibition);
    assert_eq!(items[6].kind(), DeonticLexemeKind::Prohibition);
    assert_eq!(
        &text[items[0].text_span().start()..items[0].text_span().end()],
        "обязан"
    );
    assert!(!items[0].negated());
    assert!(!items[6].negated());
}

#[test]
fn preserves_only_immediate_lexical_negation_without_inverting_kind() {
    let text = "Орган не вправе и не обязан; орган не, вправе; орган не сегодня обязан.";
    let items = extract_deontic_lexemes(&block(text, ParagraphStyle::BodyText));
    assert_eq!(items.len(), 4);
    assert!(items[0].negated());
    assert!(items[1].negated());
    assert!(!items[2].negated());
    assert!(!items[3].negated());
    assert_eq!(items[0].kind(), DeonticLexemeKind::Permission);
}

#[test]
fn filters_structural_markers_and_prefix_false_positives() {
    let text = "Статья 5 и пункт 2; обязанность и правоспособность; орган вправе.";
    let items = extract_deontic_lexemes(&block(text, ParagraphStyle::BodyText));
    assert_eq!(items.len(), 1);
    assert_eq!(items[0].kind(), DeonticLexemeKind::Permission);
}

#[test]
fn is_case_insensitive_repeat_deterministic_and_excludes_provider_comments() {
    let body = block("ОБЯЗАН и ЗАПРЕЩАЕТСЯ.", ParagraphStyle::BodyText);
    let comment = block("ОБЯЗАН и ЗАПРЕЩАЕТСЯ.", ParagraphStyle::ProviderComment);
    let first = extract_deontic_lexemes(&body);
    assert_eq!(first, extract_deontic_lexemes(&body));
    assert_eq!(first.len(), 2);
    assert!(extract_deontic_lexemes(&comment).is_empty());
}
