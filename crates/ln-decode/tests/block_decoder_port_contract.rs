use ln_decode::{
    application::DecodeBlocks,
    domain::{
        BlockDecodeError, BlockDecodeErrorKind, DecodePhase, DecodeRequest, FamilyFormat,
        ParagraphStyle, ParsedBlock, PayloadRef, SourceFormatId, SourceSpan,
    },
    ports::BlockDecoderPort,
};

struct SuccessfulDecoder;

impl BlockDecoderPort for SuccessfulDecoder {
    fn decode_blocks(
        &self,
        _request: &DecodeRequest,
    ) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
        Ok(vec![ParsedBlock::try_new(
            "Статья 1. Предмет регулирования.".to_owned(),
            Some("P1".to_owned()),
            ParagraphStyle::BodyText,
            SourceSpan::try_new(10, 96).expect("valid source span"),
            SourceFormatId::ConsultantWordMl,
        )
        .expect("valid parsed block")])
    }
}

struct FailingDecoder;

impl BlockDecoderPort for FailingDecoder {
    fn decode_blocks(
        &self,
        _request: &DecodeRequest,
    ) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
        Err(BlockDecodeError::new(
            DecodePhase::Parse,
            BlockDecodeErrorKind::MalformedInput,
            Some(47),
        ))
    }
}

fn request(bytes: &[u8]) -> DecodeRequest {
    DecodeRequest::new(
        PayloadRef::parse("payload:consultant-fixture").expect("valid payload ref"),
        FamilyFormat::parse("family:consultant-wordml").expect("valid family format"),
        bytes,
    )
}

#[test]
fn fallible_block_use_case_returns_validated_blocks_atomically() {
    let use_case = DecodeBlocks::new(SuccessfulDecoder);

    let blocks = use_case
        .execute(&request(b"bounded fixture"))
        .expect("successful decoder returns all blocks");

    assert_eq!(blocks.len(), 1);
    assert_eq!(blocks[0].text(), "Статья 1. Предмет регулирования.");
    assert_eq!(blocks[0].source_span().start(), 10);
    assert_eq!(blocks[0].source_span().end(), 96);
}

#[test]
fn failure_is_one_typed_error_without_partial_blocks_or_raw_payload() {
    const SECRET_SOURCE: &str = "секретный исходный текст";
    let use_case = DecodeBlocks::new(FailingDecoder);

    let error = use_case
        .execute(&request(SECRET_SOURCE.as_bytes()))
        .expect_err("malformed input must fail atomically");

    assert_eq!(error.phase(), DecodePhase::Parse);
    assert_eq!(error.kind(), BlockDecodeErrorKind::MalformedInput);
    assert_eq!(error.byte_offset(), Some(47));
    assert!(!error.to_string().contains(SECRET_SOURCE));
    assert!(!format!("{error:?}").contains(SECRET_SOURCE));
}
