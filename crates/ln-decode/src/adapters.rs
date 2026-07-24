use quick_xml::events::Event;
use quick_xml::reader::NsReader;

use crate::domain::{
    fingerprint_bytes, AnchorId, CandidateId, DecodeCategory, DecodeRequest, DecoderEmission,
    EvidenceAnchor,
};
use crate::ports::DecoderPort;

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
