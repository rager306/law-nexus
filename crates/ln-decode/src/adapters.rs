use quick_xml::events::Event;
use quick_xml::reader::NsReader;

use crate::domain::{
    fingerprint_bytes, AnchorId, BlockDecodeError, BlockDecodeErrorKind, CandidateId,
    DecodeCategory, DecodePhase, DecodeRequest, DecoderEmission, EvidenceAnchor,
    ParagraphStyle as DomainParagraphStyle, ParsedBlock, SourceFormatId, SourceSpan,
};
use crate::ports::{BlockDecoderPort, DecoderPort};

/// Streaming WordML parser for Consultant XML source documents.
///
/// Uses `NsReader` for proper namespace handling. Extracts paragraphs with
/// style classification and text content, producing StructuralCandidate
/// emissions with byte-range evidence anchors.
///
/// Key design decisions:
/// - `NsReader` + `read_resolved_event_into` for correct namespace resolution
/// - `local_name()` for unprefixed element matching
/// - Explicit skip of `w:binData` (base64 image blobs)
/// - Only `w:t` text within `w:r` within `w:p` is collected
/// - Gate-owned categories are never emitted
#[derive(Debug, Default)]
pub struct WordMLStreamingDecoder;

/// Paragraph style classification from WordML `<w:pStyle w:val="N"/>`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParagraphStyle {
    Title,
    Normal,
    Nonformat,
    JurTerm,
    DocList,
    TextList,
    TitlePage,
    Cell,
    Unknown(String),
}

impl ParagraphStyle {
    pub fn from_style_id(id: &str) -> Self {
        match id {
            "0" => Self::Normal,
            "1" => Self::Nonformat,
            "2" => Self::Title,
            "3" => Self::Cell,
            "4" => Self::DocList,
            "5" => Self::TitlePage,
            "6" => Self::JurTerm,
            "7" | "8" => Self::TextList,
            other => Self::Unknown(other.to_owned()),
        }
    }

    pub fn is_structural(self) -> bool {
        matches!(
            self,
            Self::Title | Self::Normal | Self::JurTerm | Self::DocList | Self::TextList
        )
    }
}

fn local_name_match(local: &[u8], expected: &str) -> bool {
    local == expected.as_bytes()
}

/// Fail-closed Consultant WordML adapter for provider-neutral parsed blocks.
#[derive(Debug, Default)]
pub struct ConsultantWordMlBlockDecoder;

impl BlockDecoderPort for ConsultantWordMlBlockDecoder {
    fn decode_blocks(&self, request: &DecodeRequest) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
        if request.family_format.as_str() != "family:consultant-wordml" {
            return Err(BlockDecodeError::new(
                DecodePhase::Input,
                BlockDecodeErrorKind::UnsupportedFormat,
                None,
            ));
        }

        let mut reader = NsReader::from_reader(request.bytes.as_slice());
        let mut buf = Vec::with_capacity(4096);
        let mut blocks = Vec::new();
        let mut text = String::new();
        let mut provider_style_id = None;
        let mut paragraph_start = None;
        let mut in_text = false;
        let mut in_bindata = false;
        let mut open_elements = 0usize;

        loop {
            buf.clear();
            let event_start = usize::try_from(reader.buffer_position()).ok();
            let decoder = reader.decoder();
            let (_, event) = match reader.read_resolved_event_into(&mut buf) {
                Ok(pair) => pair,
                Err(_) => {
                    return Err(BlockDecodeError::new(
                        DecodePhase::Parse,
                        BlockDecodeErrorKind::MalformedInput,
                        usize::try_from(reader.error_position()).ok(),
                    ));
                }
            };

            match event {
                Event::Start(element) => {
                    open_elements += 1;
                    let local = element.local_name();
                    if local_name_match(local.as_ref(), "binData") {
                        in_bindata = true;
                    } else if local_name_match(local.as_ref(), "p") {
                        paragraph_start = event_start;
                        provider_style_id = None;
                        text.clear();
                    } else if local_name_match(local.as_ref(), "t")
                        && paragraph_start.is_some()
                        && !in_bindata
                    {
                        in_text = true;
                    } else if local_name_match(local.as_ref(), "pStyle")
                        && paragraph_start.is_some()
                    {
                        provider_style_id = style_id(decoder, &element, event_start)?;
                    }
                }
                Event::Empty(element)
                    if local_name_match(element.local_name().as_ref(), "pStyle")
                        && paragraph_start.is_some() =>
                {
                    provider_style_id = style_id(decoder, &element, event_start)?;
                }
                Event::Text(value) if in_text && !in_bindata => {
                    let decoded = value.unescape().map_err(|_| {
                        BlockDecodeError::new(
                            DecodePhase::Parse,
                            BlockDecodeErrorKind::MalformedInput,
                            event_start,
                        )
                    })?;
                    text.push_str(&decoded);
                }
                Event::End(element) => {
                    open_elements = open_elements.checked_sub(1).ok_or_else(|| {
                        BlockDecodeError::new(
                            DecodePhase::Parse,
                            BlockDecodeErrorKind::MalformedInput,
                            event_start,
                        )
                    })?;
                    let local = element.local_name();
                    if local_name_match(local.as_ref(), "binData") {
                        in_bindata = false;
                    } else if local_name_match(local.as_ref(), "t") {
                        in_text = false;
                    } else if local_name_match(local.as_ref(), "p") {
                        if let Some(start) = paragraph_start.take() {
                            let end = usize::try_from(reader.buffer_position()).map_err(|_| {
                                BlockDecodeError::new(
                                    DecodePhase::Validate,
                                    BlockDecodeErrorKind::InvalidBlock,
                                    Some(start),
                                )
                            })?;
                            if !text.trim().is_empty() {
                                let source_span =
                                    SourceSpan::try_new(start, end).map_err(|_| {
                                        BlockDecodeError::new(
                                            DecodePhase::Validate,
                                            BlockDecodeErrorKind::InvalidBlock,
                                            Some(start),
                                        )
                                    })?;
                                let style = map_paragraph_style(provider_style_id.as_deref());
                                let block = ParsedBlock::try_new(
                                    text.clone(),
                                    provider_style_id.take(),
                                    style,
                                    source_span,
                                    SourceFormatId::ConsultantWordMl,
                                )
                                .map_err(|_| {
                                    BlockDecodeError::new(
                                        DecodePhase::Validate,
                                        BlockDecodeErrorKind::InvalidBlock,
                                        Some(start),
                                    )
                                })?;
                                blocks.push(block);
                            }
                            text.clear();
                            provider_style_id = None;
                        }
                    }
                }
                Event::Eof if open_elements == 0 => return Ok(blocks),
                Event::Eof => {
                    return Err(BlockDecodeError::new(
                        DecodePhase::Parse,
                        BlockDecodeErrorKind::MalformedInput,
                        event_start,
                    ));
                }
                _ => {}
            }
        }
    }
}

fn style_id(
    decoder: quick_xml::encoding::Decoder,
    element: &quick_xml::events::BytesStart<'_>,
    byte_offset: Option<usize>,
) -> Result<Option<String>, BlockDecodeError> {
    for attribute in element.attributes() {
        let attribute = attribute.map_err(|_| {
            BlockDecodeError::new(
                DecodePhase::Parse,
                BlockDecodeErrorKind::MalformedInput,
                byte_offset,
            )
        })?;
        let key = attribute.key.as_ref();
        if key == b"val" || key.ends_with(b":val") {
            let value = attribute.decode_and_unescape_value(decoder).map_err(|_| {
                BlockDecodeError::new(
                    DecodePhase::Parse,
                    BlockDecodeErrorKind::MalformedInput,
                    byte_offset,
                )
            })?;
            return Ok(Some(value.into_owned()));
        }
    }
    Ok(None)
}

fn map_paragraph_style(style_id: Option<&str>) -> DomainParagraphStyle {
    match style_id.unwrap_or("0") {
        "0" | "1" => DomainParagraphStyle::BodyText,
        "2" | "5" => DomainParagraphStyle::Title,
        "3" => DomainParagraphStyle::TableCell,
        "4" | "7" | "8" => DomainParagraphStyle::BodyText,
        "6" => DomainParagraphStyle::JurTerm,
        _ => DomainParagraphStyle::Unknown,
    }
}

impl DecoderPort for WordMLStreamingDecoder {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission> {
        let bytes = &request.bytes;
        let mut reader = NsReader::from_reader(bytes.as_slice());
        reader.config_mut().trim_text(true);

        let mut buf = Vec::with_capacity(4096);
        let mut text_buf = String::new();
        let mut current_style: Option<String> = None;
        let mut in_paragraph = false;
        let mut in_text = false;
        let mut in_bindata = false;
        let mut para_count = 0usize;
        let mut emissions = Vec::new();

        loop {
            buf.clear();
            let (ns, event) = match reader.read_resolved_event_into(&mut buf) {
                Ok(pair) => pair,
                Err(_) => break,
            };

            match event {
                Event::Start(e) => {
                    let local = e.local_name();
                    if local_name_match(local.as_ref(), "binData") {
                        in_bindata = true;
                    } else if local_name_match(local.as_ref(), "p") {
                        in_paragraph = true;
                        current_style = None;
                        text_buf.clear();
                    } else if local_name_match(local.as_ref(), "t") && in_paragraph {
                        in_text = true;
                    } else if local_name_match(local.as_ref(), "pStyle") && in_paragraph {
                        for attr in e.attributes().flatten() {
                            let key = attr.key.as_ref();
                            if key == b"val" || key.ends_with(b":val") {
                                current_style =
                                    Some(String::from_utf8_lossy(attr.value.as_ref()).into_owned());
                            }
                        }
                    }
                    let _ = ns;
                }
                Event::Empty(e) => {
                    let local = e.local_name();
                    if local_name_match(local.as_ref(), "pStyle") && in_paragraph {
                        for attr in e.attributes().flatten() {
                            let key = attr.key.as_ref();
                            if key == b"val" || key.ends_with(b":val") {
                                current_style =
                                    Some(String::from_utf8_lossy(attr.value.as_ref()).into_owned());
                            }
                        }
                    }
                }
                Event::Text(e) if in_text => {
                    text_buf.push_str(&e.unescape().unwrap_or_default());
                }
                Event::End(e) => {
                    let local = e.local_name();
                    if local_name_match(local.as_ref(), "binData") {
                        in_bindata = false;
                    } else if local_name_match(local.as_ref(), "t") {
                        in_text = false;
                    } else if local_name_match(local.as_ref(), "p") && in_paragraph && !in_bindata {
                        in_paragraph = false;
                        let style_id = current_style.as_deref().unwrap_or("0");
                        let style = ParagraphStyle::from_style_id(style_id);

                        if style.is_structural() && !text_buf.trim().is_empty() {
                            para_count += 1;
                            let text_bytes = text_buf.as_bytes();
                            let cand_id = format!("cand:{para_count}");
                            let anchor_id = format!("anchor:{para_count}");
                            emissions.push(DecoderEmission {
                                category: DecodeCategory::StructuralCandidate,
                                candidate_id: CandidateId::parse(&cand_id).ok(),
                                anchor: Some(EvidenceAnchor {
                                    anchor_id: AnchorId::parse(&anchor_id).unwrap_or_else(|_| {
                                        AnchorId::parse("anchor:fallback").unwrap()
                                    }),
                                    start_offset: 0,
                                    end_offset: text_bytes.len(),
                                    fingerprint: fingerprint_bytes(text_bytes),
                                }),
                                raw_context: None,
                            });
                        }
                        text_buf.clear();
                    }
                }
                Event::Eof => break,
                _ => {}
            }
        }

        emissions
    }
}

// Legacy synthetic adapters preserved for HC-05 hostile contract tests.

use crate::ports::DiagnosticPort;

#[derive(Debug, Default)]
pub struct HonestSyntheticDecoder;

impl DecoderPort for HonestSyntheticDecoder {
    fn decode(&self, request: &DecodeRequest) -> Vec<DecoderEmission> {
        let fp = fingerprint_bytes(&request.bytes);
        vec![DecoderEmission {
            category: DecodeCategory::StructuralCandidate,
            candidate_id: CandidateId::parse("cand:synthetic-honest").ok(),
            anchor: Some(EvidenceAnchor {
                anchor_id: AnchorId::parse("anchor:synthetic-honest").expect("static id"),
                start_offset: 0,
                end_offset: request.bytes.len(),
                fingerprint: fp,
            }),
            raw_context: None,
        }]
    }
}

#[derive(Debug, Default)]
pub struct MaliciousSyntheticDecoder;

impl DecoderPort for MaliciousSyntheticDecoder {
    fn decode(&self, _request: &DecodeRequest) -> Vec<DecoderEmission> {
        vec![
            DecoderEmission {
                category: DecodeCategory::VerifiedAssertion,
                candidate_id: None,
                anchor: None,
                raw_context: Some("CANARY::SYNTHETIC-LEGAL-TEXT-DO-NOT-LEAK".to_owned()),
            },
            DecoderEmission {
                category: DecodeCategory::MergedIdentity,
                candidate_id: None,
                anchor: None,
                raw_context: Some("CANARY::MERGED-IDENTITY".to_owned()),
            },
            DecoderEmission {
                category: DecodeCategory::UnregisteredRelation,
                candidate_id: None,
                anchor: None,
                raw_context: Some("CANARY::UNREGISTERED-RELATION".to_owned()),
            },
            DecoderEmission {
                category: DecodeCategory::RawFailureContext,
                candidate_id: None,
                anchor: None,
                raw_context: Some("CANARY::RAW-FAILURE-CONTEXT".to_owned()),
            },
        ]
    }
}

#[derive(Debug, Default)]
pub struct InMemoryDiagnosticSink {
    events: Vec<crate::domain::SafeDiagnostic>,
}

impl InMemoryDiagnosticSink {
    pub fn new() -> Self {
        Self::default()
    }
}

impl DiagnosticPort for InMemoryDiagnosticSink {
    fn record(&mut self, event: crate::domain::SafeDiagnostic) {
        self.events.push(event);
    }
    fn events(&self) -> &[crate::domain::SafeDiagnostic] {
        &self.events
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::domain::{FamilyFormat, PayloadRef};

    #[test]
    fn parses_basic_wordml_with_namespaces() {
        let xml = br#"<?xml version="1.0"?>
<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml">
<w:body>
<w:p><w:pPr><w:pStyle w:val="2"/></w:pPr><w:r><w:t>Title text</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>Article 1.</w:t></w:r></w:p>
</w:body>
</w:wordDocument>"#;
        let req = DecodeRequest::new(
            PayloadRef::parse("payload:test").unwrap(),
            FamilyFormat::parse("consultant-xml").unwrap(),
            xml,
        );
        let decoder = WordMLStreamingDecoder;
        let emissions = decoder.decode(&req);
        assert_eq!(emissions.len(), 2, "should extract 2 structural paragraphs");
        assert!(emissions.iter().all(|e| e.category.is_structural()));
        assert!(emissions.iter().all(|e| e.candidate_id.is_some()));
        assert!(emissions.iter().all(|e| e.anchor.is_some()));
        assert!(emissions.iter().all(|e| e.raw_context.is_none()));
    }

    #[test]
    fn skips_non_structural_styles() {
        let xml = br#"<w:body xmlns:w="urn:w">
<w:p><w:pPr><w:pStyle w:val="3"/></w:pPr><w:r><w:t>Cell content</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>Body text</w:t></w:r></w:p>
</w:body>"#;
        let req = DecodeRequest::new(
            PayloadRef::parse("p:1").unwrap(),
            FamilyFormat::parse("f:1").unwrap(),
            xml,
        );
        let decoder = WordMLStreamingDecoder;
        let emissions = decoder.decode(&req);
        assert_eq!(emissions.len(), 1, "cell style should be skipped");
    }

    #[test]
    fn handles_empty_document() {
        let xml = br#"<w:body xmlns:w="urn:w"></w:body>"#;
        let req = DecodeRequest::new(
            PayloadRef::parse("p:1").unwrap(),
            FamilyFormat::parse("f:1").unwrap(),
            xml,
        );
        let decoder = WordMLStreamingDecoder;
        let emissions = decoder.decode(&req);
        assert!(emissions.is_empty());
    }

    #[test]
    fn skips_bindata_base64_blobs() {
        let xml = br#"<w:body xmlns:w="urn:w">
<w:binData w:name="wordml://img.png">aGVsbG8gd29ybGQgdGhpcyBpcyBhIHZlcnkgbG9uZyBiYXNlNjQgYmxvYg==</w:binData>
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>Real text</w:t></w:r></w:p>
</w:body>"#;
        let req = DecodeRequest::new(
            PayloadRef::parse("p:1").unwrap(),
            FamilyFormat::parse("f:1").unwrap(),
            xml,
        );
        let decoder = WordMLStreamingDecoder;
        let emissions = decoder.decode(&req);
        assert_eq!(emissions.len(), 1, "only the paragraph, not binData");
    }

    #[test]
    fn style_classification() {
        assert_eq!(ParagraphStyle::from_style_id("0"), ParagraphStyle::Normal);
        assert_eq!(ParagraphStyle::from_style_id("2"), ParagraphStyle::Title);
        assert_eq!(ParagraphStyle::from_style_id("6"), ParagraphStyle::JurTerm);
        assert!(ParagraphStyle::Title.is_structural());
        assert!(!ParagraphStyle::Cell.is_structural());
    }

    #[test]
    fn handles_multiple_text_runs_in_single_paragraph() {
        let xml = br#"<w:body xmlns:w="urn:w">
<w:p><w:pPr><w:pStyle w:val="0"/></w:pPr><w:r><w:t>First part. </w:t></w:r><w:r><w:t>Second part.</w:t></w:r></w:p>
</w:body>"#;
        let req = DecodeRequest::new(
            PayloadRef::parse("p:1").unwrap(),
            FamilyFormat::parse("f:1").unwrap(),
            xml,
        );
        let decoder = WordMLStreamingDecoder;
        let emissions = decoder.decode(&req);
        assert_eq!(
            emissions.len(),
            1,
            "multiple runs in one paragraph = one candidate"
        );
    }
}
