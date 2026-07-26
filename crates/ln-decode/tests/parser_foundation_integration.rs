use ln_decode::domain::{ParagraphStyle, ParsedBlock, SourceFormatId, SourceSpan, TextSpan};
use ln_decode::morphology::find_legal_markers;
use ln_decode::sentence::split_legal_sentences;

#[test]
fn parsed_block_composes_with_decoded_text_spans_without_claiming_source_mapping() {
    let text = "Статья 1. Орган не вправе действовать. Второе положение.";
    let original_source_span = SourceSpan::try_new(1_000, 2_000).expect("artifact span");
    let block = ParsedBlock::try_new(
        text.to_owned(),
        Some("provider-style-heading".to_owned()),
        ParagraphStyle::Heading,
        original_source_span,
        SourceFormatId::ConsultantWordMl,
    )
    .expect("valid block");

    let sentences = split_legal_sentences(block.text());
    let markers = find_legal_markers(block.text());

    assert_eq!(sentences.len(), 3);
    assert_eq!(markers.len(), 2);
    assert_eq!(block.source_span(), original_source_span);

    for sentence in &sentences {
        let span: TextSpan = sentence.text_span();
        assert!(span.end() <= block.text().len());
    }
    for marker in &markers {
        let marker_span: TextSpan = marker.text_span();
        assert!(sentences.iter().any(|sentence| {
            let sentence_span = sentence.text_span();
            sentence_span.start() <= marker_span.start() && marker_span.end() <= sentence_span.end()
        }));
    }
}
