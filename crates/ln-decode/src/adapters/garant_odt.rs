//! Independent fail-closed Garant ODT `content.xml` block adapter.
//!
//! Package intake, XML parsing and provider style interpretation remain adapter
//! concerns. The parser consumes only bounded in-memory member bytes and emits
//! provider-neutral domain blocks. It never resolves DTDs or external entities.

use quick_xml::events::{BytesStart, Event};
use quick_xml::name::ResolveResult;
use quick_xml::reader::NsReader;

use super::garant_odt_package::read_odt_content_xml;
use crate::domain::{
    BlockDecodeError, BlockDecodeErrorKind, DecodePhase, DecodeRequest, ParagraphStyle,
    ParsedBlock, SourceFormatId, SourceLocation, SourceSpan, SourceStreamId,
};
use crate::ports::BlockDecoderPort;

const OFFICE_NS: &[u8] = b"urn:oasis:names:tc:opendocument:xmlns:office:1.0";
const TEXT_NS: &[u8] = b"urn:oasis:names:tc:opendocument:xmlns:text:1.0";
const MAX_ODF_SPACES: usize = 64;
const MAX_DECODED_BLOCK_BYTES: usize = 1024 * 1024;

#[derive(Debug, Default)]
pub struct GarantOdtBlockDecoder;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum NamespaceKind {
    Office,
    Text,
    Other,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum BlockKind {
    Heading,
    Paragraph,
}

struct OpenBlock {
    kind: BlockKind,
    start: usize,
    text: String,
    provider_style_id: Option<String>,
}

impl BlockDecoderPort for GarantOdtBlockDecoder {
    fn decode_blocks(&self, request: &DecodeRequest) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
        let content = read_odt_content_xml(request)?;
        parse_content_xml(content.bytes())
    }
}

fn parse_content_xml(bytes: &[u8]) -> Result<Vec<ParsedBlock>, BlockDecodeError> {
    let source_stream =
        SourceStreamId::parse("package-member:content.xml").expect("static source stream id");
    let mut reader = NsReader::from_reader(bytes);
    let mut buffer = Vec::with_capacity(4096);
    let mut blocks = Vec::new();
    let mut open_block: Option<OpenBlock> = None;
    let mut open_elements = 0usize;
    let mut seen_root = false;
    let mut in_root = false;
    let mut in_body = false;
    let mut in_document_text = false;
    let mut seen_document_text = false;

    loop {
        buffer.clear();
        let event_start = usize::try_from(reader.buffer_position()).ok();
        let decoder = reader.decoder();
        let (resolved, event) = match reader.read_resolved_event_into(&mut buffer) {
            Ok(pair) => pair,
            Err(_) => {
                return Err(parse_error(
                    event_start.or_else(|| offset(reader.error_position())),
                ))
            }
        };
        let namespace = namespace_kind(&resolved);

        match event {
            Event::Start(element) => {
                validate_attributes(&element, event_start)?;
                if seen_root && !in_root {
                    return Err(parse_error(event_start));
                }
                let local = element.local_name();
                let local = local.as_ref();

                if local == b"document-content" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if seen_root || open_elements != 0 {
                        return Err(parse_error(event_start));
                    }
                    seen_root = true;
                    in_root = true;
                } else if local == b"body" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if !in_root || in_body || in_document_text {
                        return Err(parse_error(event_start));
                    }
                    in_body = true;
                } else if local == b"text" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if !in_body || in_document_text || seen_document_text {
                        return Err(parse_error(event_start));
                    }
                    in_document_text = true;
                    seen_document_text = true;
                } else if is_block_name(local) {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    if !in_document_text || open_block.is_some() {
                        return Err(parse_error(event_start));
                    }
                    let start = event_start.ok_or_else(|| parse_error(None))?;
                    let kind = if local == b"h" {
                        BlockKind::Heading
                    } else {
                        BlockKind::Paragraph
                    };
                    let provider_style_id = style_name(&reader, decoder, &element, event_start)?;
                    open_block = Some(OpenBlock {
                        kind,
                        start,
                        text: String::new(),
                        provider_style_id,
                    });
                } else if local == b"span" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    if open_block.is_none() {
                        return Err(parse_error(event_start));
                    }
                } else if local == b"s" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    return Err(parse_error(event_start));
                } else if open_block.is_some()
                    || (namespace == NamespaceKind::Text && in_document_text)
                {
                    return Err(parse_error(event_start));
                }
                open_elements = open_elements
                    .checked_add(1)
                    .ok_or_else(|| parse_error(event_start))?;
            }
            Event::Empty(element) => {
                validate_attributes(&element, event_start)?;
                if seen_root && !in_root {
                    return Err(parse_error(event_start));
                }
                let local = element.local_name();
                let local = local.as_ref();
                if is_block_name(local) {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    if !in_document_text || open_block.is_some() {
                        return Err(parse_error(event_start));
                    }
                } else if local == b"span" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    if open_block.is_none() {
                        return Err(parse_error(event_start));
                    }
                } else if local == b"s" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    let count = odf_space_count(&reader, decoder, &element, event_start)?;
                    let block = open_block
                        .as_mut()
                        .ok_or_else(|| parse_error(event_start))?;
                    ensure_decoded_capacity(block.text.len(), count, event_start)?;
                    block.text.extend(std::iter::repeat_n(' ', count));
                } else if matches!(local, b"document-content" | b"body" | b"text") {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    return Err(parse_error(event_start));
                } else if open_block.is_some()
                    || (namespace == NamespaceKind::Text && in_document_text)
                {
                    return Err(parse_error(event_start));
                }
            }
            Event::Text(value) => {
                let decoded = value.unescape().map_err(|_| parse_error(event_start))?;
                if let Some(block) = open_block.as_mut() {
                    ensure_decoded_capacity(block.text.len(), decoded.len(), event_start)?;
                    block.text.push_str(&decoded);
                } else if (in_document_text || (seen_root && !in_root))
                    && !decoded.trim().is_empty()
                {
                    return Err(parse_error(event_start));
                }
            }
            Event::CData(_) | Event::DocType(_) => return Err(parse_error(event_start)),
            Event::End(element) => {
                open_elements = open_elements
                    .checked_sub(1)
                    .ok_or_else(|| parse_error(event_start))?;
                let local = element.local_name();
                let local = local.as_ref();

                if is_block_name(local) {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    let expected = if local == b"h" {
                        BlockKind::Heading
                    } else {
                        BlockKind::Paragraph
                    };
                    let block = open_block.take().ok_or_else(|| parse_error(event_start))?;
                    if block.kind != expected {
                        return Err(parse_error(event_start));
                    }
                    if !block.text.trim().is_empty() {
                        let end = usize::try_from(reader.buffer_position())
                            .map_err(|_| validate_error(Some(block.start)))?;
                        let span = SourceSpan::try_new(block.start, end)
                            .map_err(|_| validate_error(Some(block.start)))?;
                        let style = map_style(block.kind, block.provider_style_id.as_deref());
                        let parsed = ParsedBlock::try_new(
                            block.text,
                            block.provider_style_id,
                            style,
                            SourceLocation::new(source_stream.clone(), span),
                            SourceFormatId::GarantOdt,
                        )
                        .map_err(|_| validate_error(Some(block.start)))?;
                        blocks.push(parsed);
                    }
                } else if local == b"span" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    if open_block.is_none() {
                        return Err(parse_error(event_start));
                    }
                } else if local == b"text" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if !in_document_text || open_block.is_some() {
                        return Err(parse_error(event_start));
                    }
                    in_document_text = false;
                } else if local == b"body" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if !in_body || in_document_text {
                        return Err(parse_error(event_start));
                    }
                    in_body = false;
                } else if local == b"document-content" {
                    require_namespace(namespace, NamespaceKind::Office, event_start)?;
                    if !in_root || in_body {
                        return Err(parse_error(event_start));
                    }
                    in_root = false;
                } else if local == b"s" {
                    require_namespace(namespace, NamespaceKind::Text, event_start)?;
                    return Err(parse_error(event_start));
                }
            }
            Event::Eof
                if seen_root
                    && seen_document_text
                    && !in_root
                    && !in_body
                    && !in_document_text
                    && open_block.is_none()
                    && open_elements == 0 =>
            {
                return Ok(blocks);
            }
            Event::Eof => return Err(parse_error(event_start)),
            Event::Decl(_) | Event::PI(_) | Event::Comment(_) => {}
        }
    }
}

fn namespace_kind(resolved: &ResolveResult<'_>) -> NamespaceKind {
    match resolved {
        ResolveResult::Bound(namespace) if namespace.as_ref() == OFFICE_NS => NamespaceKind::Office,
        ResolveResult::Bound(namespace) if namespace.as_ref() == TEXT_NS => NamespaceKind::Text,
        ResolveResult::Unbound | ResolveResult::Bound(_) | ResolveResult::Unknown(_) => {
            NamespaceKind::Other
        }
    }
}

fn require_namespace(
    actual: NamespaceKind,
    expected: NamespaceKind,
    byte_offset: Option<usize>,
) -> Result<(), BlockDecodeError> {
    if actual == expected {
        Ok(())
    } else {
        Err(parse_error(byte_offset))
    }
}

fn validate_attributes(
    element: &BytesStart<'_>,
    byte_offset: Option<usize>,
) -> Result<(), BlockDecodeError> {
    for attribute in element.attributes() {
        attribute.map_err(|_| parse_error(byte_offset))?;
    }
    Ok(())
}

fn style_name<R: std::io::BufRead>(
    reader: &NsReader<R>,
    decoder: quick_xml::encoding::Decoder,
    element: &BytesStart<'_>,
    byte_offset: Option<usize>,
) -> Result<Option<String>, BlockDecodeError> {
    let mut style = None;
    for attribute in element.attributes() {
        let attribute = attribute.map_err(|_| parse_error(byte_offset))?;
        let (resolved, local) = reader.resolve_attribute(attribute.key);
        if local.as_ref() != b"style-name" {
            continue;
        }
        if namespace_kind(&resolved) != NamespaceKind::Text || style.is_some() {
            return Err(parse_error(byte_offset));
        }
        let value = attribute
            .decode_and_unescape_value(decoder)
            .map_err(|_| parse_error(byte_offset))?;
        if value.trim().is_empty() {
            return Err(parse_error(byte_offset));
        }
        style = Some(value.into_owned());
    }
    Ok(style)
}

fn odf_space_count<R: std::io::BufRead>(
    reader: &NsReader<R>,
    decoder: quick_xml::encoding::Decoder,
    element: &BytesStart<'_>,
    byte_offset: Option<usize>,
) -> Result<usize, BlockDecodeError> {
    let mut count = None;
    for attribute in element.attributes() {
        let attribute = attribute.map_err(|_| parse_error(byte_offset))?;
        let (resolved, local) = reader.resolve_attribute(attribute.key);
        if local.as_ref() != b"c" {
            continue;
        }
        if namespace_kind(&resolved) != NamespaceKind::Text || count.is_some() {
            return Err(parse_error(byte_offset));
        }
        let value = attribute
            .decode_and_unescape_value(decoder)
            .map_err(|_| parse_error(byte_offset))?;
        count = Some(
            value
                .parse::<usize>()
                .map_err(|_| parse_error(byte_offset))?,
        );
    }
    let count = count.unwrap_or(1);
    if !(1..=MAX_ODF_SPACES).contains(&count) {
        return Err(parse_error(byte_offset));
    }
    Ok(count)
}

const fn is_block_name(local: &[u8]) -> bool {
    matches!(local, b"p" | b"h")
}

fn map_style(kind: BlockKind, provider_style_id: Option<&str>) -> ParagraphStyle {
    if kind == BlockKind::Heading {
        return ParagraphStyle::Heading;
    }
    match provider_style_id {
        Some("s9" | "s9header") => ParagraphStyle::ProviderComment,
        None | Some("Standard") => ParagraphStyle::BodyText,
        Some(_) => ParagraphStyle::Unknown,
    }
}

fn ensure_decoded_capacity(
    current: usize,
    additional: usize,
    byte_offset: Option<usize>,
) -> Result<(), BlockDecodeError> {
    if current
        .checked_add(additional)
        .is_some_and(|total| total <= MAX_DECODED_BLOCK_BYTES)
    {
        Ok(())
    } else {
        Err(parse_error(byte_offset))
    }
}

fn offset(value: u64) -> Option<usize> {
    usize::try_from(value).ok()
}

const fn parse_error(byte_offset: Option<usize>) -> BlockDecodeError {
    BlockDecodeError::new(
        DecodePhase::Parse,
        BlockDecodeErrorKind::MalformedInput,
        byte_offset,
    )
}

const fn validate_error(byte_offset: Option<usize>) -> BlockDecodeError {
    BlockDecodeError::new(
        DecodePhase::Validate,
        BlockDecodeErrorKind::InvalidBlock,
        byte_offset,
    )
}
