use ln_decode::{
    deontic::extract_deontic_lexemes,
    domain::{
        HierarchyLevel, ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan,
        SourceStreamId, TextSpan,
    },
    evaluator::{evaluate, EvaluatorError},
    golden::{GoldenAnnotation, GoldenFixture, GoldenLayer, GoldenSource},
    references::extract_reference_mentions,
};

fn source() -> GoldenSource {
    GoldenSource::try_new(
        "synthetic:evaluator",
        "0000000000000000000000000000000000000000000000000000000000000000",
        128,
        "fnv1a64:0000000000000000",
    )
    .unwrap()
}

fn span(start: usize, end: usize) -> TextSpan {
    TextSpan::try_new(start, end).unwrap()
}

fn block(text: &str, format: SourceFormatId) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        ParagraphStyle::BodyText,
        SourceLocation::new(
            SourceStreamId::parse("fixture:evaluator").unwrap(),
            SourceSpan::try_new(0, 100).unwrap(),
        ),
        format,
    )
    .unwrap()
}

fn approx_eq(actual: f64, expected: f64) -> bool {
    (actual - expected).abs() < 1e-9
}

#[test]
fn perfect_deontic_match_yields_unit_metrics() {
    let blk = block(
        "Орган обязан действовать.",
        SourceFormatId::ConsultantWordMl,
    );
    let actual = extract_deontic_lexemes(&blk);
    assert_eq!(actual.len(), 1);

    let annotations: Vec<_> = actual
        .iter()
        .map(|lexeme| GoldenAnnotation::Deontic {
            block_index: 0,
            kind: lexeme.kind(),
            span: lexeme.text_span(),
            negated: lexeme.negated(),
        })
        .collect();

    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::ConsultantWordMl,
        annotations,
        Vec::new(),
    )
    .unwrap();

    let metrics = evaluate(&fixture, std::slice::from_ref(&blk)).unwrap();
    assert_eq!(metrics.len(), 1);
    assert_eq!(metrics[0].layer(), GoldenLayer::Deontic);
    assert_eq!(metrics[0].true_positives(), 1);
    assert_eq!(metrics[0].false_positives(), 0);
    assert_eq!(metrics[0].false_negatives(), 0);
    assert!(approx_eq(metrics[0].precision(), 1.0));
    assert!(approx_eq(metrics[0].recall(), 1.0));
    assert!(approx_eq(metrics[0].f1(), 1.0));
}

#[test]
fn extra_actual_items_reduce_precision() {
    let blk = block(
        "Орган обязан и вправе действовать.",
        SourceFormatId::ConsultantWordMl,
    );
    let actual = extract_deontic_lexemes(&blk);
    assert_eq!(actual.len(), 2);

    // Fixture only has the first deontic lexeme
    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::ConsultantWordMl,
        vec![GoldenAnnotation::Deontic {
            block_index: 0,
            kind: actual[0].kind(),
            span: actual[0].text_span(),
            negated: actual[0].negated(),
        }],
        Vec::new(),
    )
    .unwrap();

    let metrics = evaluate(&fixture, std::slice::from_ref(&blk)).unwrap();
    assert_eq!(metrics[0].true_positives(), 1);
    assert_eq!(metrics[0].false_positives(), 1);
    assert_eq!(metrics[0].false_negatives(), 0);
    assert!(approx_eq(metrics[0].precision(), 0.5));
    assert!(approx_eq(metrics[0].recall(), 1.0));
}

#[test]
fn total_miss_yields_zero_recall() {
    let blk = block(
        "Техническое описание процедуры.",
        SourceFormatId::ConsultantWordMl,
    );
    let actual = extract_deontic_lexemes(&blk);
    assert!(actual.is_empty());

    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::ConsultantWordMl,
        vec![GoldenAnnotation::Deontic {
            block_index: 0,
            kind: ln_decode::deontic::DeonticLexemeKind::Permission,
            span: span(0, 10),
            negated: false,
        }],
        Vec::new(),
    )
    .unwrap();

    let metrics = evaluate(&fixture, std::slice::from_ref(&blk)).unwrap();
    assert_eq!(metrics[0].true_positives(), 0);
    assert_eq!(metrics[0].false_positives(), 0);
    assert_eq!(metrics[0].false_negatives(), 1);
    assert!(approx_eq(metrics[0].precision(), 1.0));
    assert!(approx_eq(metrics[0].recall(), 0.0));
    assert!(approx_eq(metrics[0].f1(), 0.0));
}

#[test]
fn reference_layer_evaluates_independently() {
    let blk = block(
        "По статье 3 и пункту 2 применяются правила.",
        SourceFormatId::GarantOdt,
    );
    let actual = extract_reference_mentions(&blk);
    assert_eq!(actual.len(), 2);

    let annotations: Vec<_> = actual
        .iter()
        .map(|mention| GoldenAnnotation::Reference {
            block_index: 0,
            kind: mention.kind(),
            number: mention.number().to_owned(),
            span: mention.text_span(),
        })
        .collect();

    let fixture =
        GoldenFixture::try_new(source(), SourceFormatId::GarantOdt, annotations, Vec::new())
            .unwrap();

    let metrics = evaluate(&fixture, std::slice::from_ref(&blk)).unwrap();
    assert_eq!(metrics.len(), 1);
    assert_eq!(metrics[0].layer(), GoldenLayer::Reference);
    assert_eq!(metrics[0].true_positives(), 2);
    assert_eq!(metrics[0].false_positives(), 0);
    assert_eq!(metrics[0].false_negatives(), 0);
    assert!(approx_eq(metrics[0].f1(), 1.0));
}

#[test]
fn rejects_provider_mismatch() {
    let blk = block("Орган обязан.", SourceFormatId::ConsultantWordMl);
    let actual = extract_deontic_lexemes(&blk);

    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::GarantOdt,
        vec![GoldenAnnotation::Deontic {
            block_index: 0,
            kind: actual[0].kind(),
            span: actual[0].text_span(),
            negated: actual[0].negated(),
        }],
        Vec::new(),
    )
    .unwrap();

    assert!(matches!(
        evaluate(&fixture, std::slice::from_ref(&blk)),
        Err(EvaluatorError::ProviderMismatch { .. })
    ));
}

#[test]
fn rejects_block_index_out_of_range() {
    let blk = block("Орган обязан.", SourceFormatId::ConsultantWordMl);
    let actual = extract_deontic_lexemes(&blk);

    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::ConsultantWordMl,
        vec![GoldenAnnotation::Deontic {
            block_index: 5,
            kind: actual[0].kind(),
            span: actual[0].text_span(),
            negated: actual[0].negated(),
        }],
        Vec::new(),
    )
    .unwrap();

    assert!(matches!(
        evaluate(&fixture, std::slice::from_ref(&blk)),
        Err(EvaluatorError::BlockIndexOutOfRange { .. })
    ));
}

#[test]
fn rejects_empty_blocks() {
    let fixture = GoldenFixture::try_new(
        source(),
        SourceFormatId::ConsultantWordMl,
        vec![GoldenAnnotation::Hierarchy {
            block_index: 0,
            level: HierarchyLevel::Statya,
            span: span(0, 7),
        }],
        Vec::new(),
    )
    .unwrap();

    assert!(matches!(
        evaluate(&fixture, &[]),
        Err(EvaluatorError::EmptyBlocks)
    ));
}
