use ln_decode::document_context::{
    ContextBudgets, ContextRequest, ContextRequestKind, DocumentVersionRef, FrameRef,
    IndexBuildError, OverlayBuildError,
};
use ln_decode::document_pipeline::{
    BoundedLegalMarkerMorphProvider, DocumentPipeline, MorphEvidenceProvider, MorphEvidenceRecord,
    MorphEvidenceSet, NullMorphProvider,
};
use ln_decode::domain::{
    ParagraphStyle, ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
    TextSpan,
};
use ln_decode::lexer::{NpaToken, TokenKind};

fn block(index: usize, style: ParagraphStyle, text: &str) -> ParsedBlock {
    ParsedBlock::try_new(
        text.to_owned(),
        None,
        style,
        SourceLocation::new(
            SourceStreamId::parse("fixture:pipeline").expect("stream id"),
            SourceSpan::try_new(index * 200, index * 200 + text.len()).expect("span"),
        ),
        SourceFormatId::ConsultantWordMl,
    )
    .expect("parsed block")
}

fn version() -> DocumentVersionRef {
    DocumentVersionRef::try_new(
        "doc:44-fz:ed-112".to_owned(),
        "rev-2024-11-30".to_owned(),
        "wordml-2003".to_owned(),
    )
    .expect("version ref")
}

#[test]
fn typestate_pipeline_walks_p0_to_p5_and_freezes_literal_mentions() {
    let blocks = vec![
        block(0, ParagraphStyle::Heading, "Статья 3. Основные понятия"),
        block(
            1,
            ParagraphStyle::BodyText,
            "1. В соответствии со статьей 93 Федерального закона от 05.04.2013 № 44-ФЗ заказчик обязан разместить извещение.",
        ),
    ];

    let raw = DocumentPipeline::new(version(), blocks);
    assert_eq!(raw.block_count(), 2);

    let indexed = raw.into_indexed().expect("P0 -> P1 indexing must succeed");
    assert_eq!(indexed.index().source_blocks().len(), 2);

    let analyzed = indexed
        .into_analyzed(&BoundedLegalMarkerMorphProvider)
        .expect("P1 -> P2/P3/P4 analysis must succeed");
    assert_eq!(analyzed.local_analysis().len(), 2);
    assert!(
        !analyzed.local_analysis()[1].morph.records.is_empty(),
        "bounded morph provider must emit legal marker records on covering Word spans"
    );
    let frozen_mentions_before = analyzed.local_analysis()[1].literal_mentions.clone();

    let req = ContextRequest::new(
        ContextRequestKind::AncestorPath,
        "doc:44-fz:ed-112".to_owned(),
        FrameRef::parse("block-1").expect("frame ref"),
        vec!["ancestor".to_owned()],
        None,
        None,
        vec![],
        2,
        "structural".to_owned(),
    );
    let closed = analyzed.into_context_closed(None, &[req], ContextBudgets::default());

    // INV-06 / npa-semantic-process invariant: P5 context closure never alters frozen P3 mentions.
    assert_eq!(
        closed.local_analysis()[1].literal_mentions,
        frozen_mentions_before
    );
    assert_eq!(closed.context_report().results.len(), 1);
}

#[test]
fn bounded_morph_provider_excludes_abbrevs_tracks_negation_and_enforces_word_only_seam() {
    // ADR-0028 dual-tokenizer invariant: Abbrev tokens (`ст.`, `п.`, `ч.`, `подп.`)
    // MUST NEVER be emitted as MorphEvidenceRecord; only covering `TokenKind::Word`
    // tokens are eligible.
    let blocks = vec![block(
        0,
        ParagraphStyle::BodyText,
        "По ст. 93 п. 1 ч. 2 подп. \"а\" заказчик не обязан и не вправе нарушать статью 3.",
    )];
    let analyzed = DocumentPipeline::new(version(), blocks.clone())
        .into_indexed()
        .expect("index")
        .into_analyzed(&BoundedLegalMarkerMorphProvider)
        .expect("analyze");

    let analysis = &analyzed.local_analysis()[0];
    assert_eq!(analysis.morph.provider_id, "bounded-legal-markers/v1");
    let abbrev_spans: Vec<TextSpan> = analysis
        .tokens
        .iter()
        .filter(|t| t.kind == TokenKind::Abbrev)
        .map(|t| t.span)
        .collect();
    let word_spans: Vec<TextSpan> = analysis
        .tokens
        .iter()
        .filter(|t| t.kind == TokenKind::Word)
        .map(|t| t.span)
        .collect();
    assert!(
        abbrev_spans.len() >= 4,
        "expected Abbrev tokens for ст./п./ч./подп., got {:?}",
        abbrev_spans
    );
    for rec in &analysis.morph.records {
        assert!(
            !abbrev_spans.contains(&rec.span),
            "ADR-0028 violation: Abbrev span {:?} leaked into MorphEvidenceRecord",
            rec.span
        );
        assert!(
            word_spans.contains(&rec.span),
            "every MorphEvidenceRecord must align to a covering TokenKind::Word span"
        );
    }
    assert!(
        analysis
            .morph
            .records
            .iter()
            .any(|r| r.lemma == "обязан" && r.tags.iter().any(|t| t == "negated")),
        "expected negated 'не обязан' marker"
    );

    // Hostile MorphEvidenceProvider attempting to return a non-Word span must
    // fail closed while returning ownership of DocumentPipeline<IndexedPhase>.
    struct BogusSpanMorphProvider;
    impl MorphEvidenceProvider for BogusSpanMorphProvider {
        fn provider_id(&self) -> &'static str {
            "hostile-bogus-span/v1"
        }
        fn analyze_covering_words(
            &self,
            block_index: usize,
            _src: &str,
            _word_tokens: &[NpaToken],
        ) -> MorphEvidenceSet {
            MorphEvidenceSet {
                block_index,
                provider_id: self.provider_id(),
                records: vec![MorphEvidenceRecord {
                    span: TextSpan::try_new(0, 1).expect("span"),
                    lemma: "bogus".to_owned(),
                    tags: vec![],
                }],
            }
        }
    }

    let indexed = DocumentPipeline::new(version(), blocks)
        .into_indexed()
        .expect("index");
    let (returned_indexed, err) = indexed
        .into_analyzed(&BogusSpanMorphProvider)
        .expect_err("bogus non-Word morph span must fail closed");
    assert_eq!(err, OverlayBuildError::InvalidCaptureSpan);
    assert_eq!(returned_indexed.index().source_blocks().len(), 1);
}

#[test]
fn typestate_pipeline_preserves_ownership_on_empty_document_error_and_null_morph_is_silent() {
    let raw = DocumentPipeline::new(version(), Vec::new());
    let (returned_raw, err) = raw
        .into_indexed()
        .expect_err("empty document must fail P0 -> P1");
    assert_eq!(err, IndexBuildError::EmptyDocument);
    assert_eq!(returned_raw.block_count(), 0);

    let single = DocumentPipeline::new(
        version(),
        vec![block(
            0,
            ParagraphStyle::BodyText,
            "Статья 1. Заказчик обязан соблюдать требования.",
        )],
    );
    let analyzed = single
        .into_indexed()
        .expect("index")
        .into_analyzed(&NullMorphProvider)
        .expect("analyze");
    assert!(analyzed.local_analysis()[0].morph.records.is_empty());
    assert_eq!(
        analyzed.local_analysis()[0].morph.provider_id,
        "null-morph/v1"
    );
}
