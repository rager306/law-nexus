//! Bounded provider-neutral hierarchy extraction from decoded block text.

use crate::domain::{HierarchyLevel, HierarchyNode, ParsedBlock, TextSpan};
use crate::prefix_catalog::{DecodePrefixCatalog, NumberStyle, NumberedStyle, SpacePolicy};

/// Extract a supported hierarchy marker at the start of decoded block text.
///
/// This function intentionally does not translate decoded [`TextSpan`] values
/// into source-stream coordinates. The owning [`ParsedBlock`] retains its
/// separate [`crate::domain::SourceLocation`] for an adapter to map with
/// additional evidence.
pub fn extract_hierarchy(block: &ParsedBlock) -> Option<HierarchyNode> {
    let text = block.text();
    let marker_start = text
        .char_indices()
        .find_map(|(index, character)| (!character.is_whitespace()).then_some(index))?;
    let candidate = &text[marker_start..];
    // Try explicit prefixes first (Статья, Глава), then numbered markers (1. 1) а))
    let (level, number_start) =
        marker_prefix(candidate).or_else(|| numbered_marker_prefix(candidate))?;
    let number_end = number_end(candidate, number_start, level)?;
    let number = &candidate[number_start..number_end];
    let punctuation = candidate.as_bytes().get(number_end).copied()?;
    // Accept '.', ':' (explicit prefixes) and ')' (numbered Punkt/Podpunkt markers)
    if !matches!(punctuation, b'.' | b':' | b')') {
        return None;
    }

    let marker_end = marker_start + number_end + 1;
    let suffix = &text[marker_end..];
    if suffix
        .chars()
        .next()
        .is_some_and(|character| !character.is_whitespace())
    {
        return None;
    }
    let title = suffix.trim();
    HierarchyNode::try_new(
        level,
        number.to_owned(),
        (!title.is_empty()).then(|| title.to_owned()),
        text.to_owned(),
        TextSpan::try_new(marker_start, marker_end).ok()?,
    )
    .ok()
}

fn marker_prefix(candidate: &str) -> Option<(HierarchyLevel, usize)> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    for rule in &catalog.prefixes {
        let Some(rest) = candidate.strip_prefix(rule.marker.as_str()) else {
            continue;
        };
        let whitespace_len = rest
            .char_indices()
            .take_while(|(_, character)| character.is_whitespace())
            .map(|(_, character)| character.len_utf8())
            .sum::<usize>();
        let space_ok = match rule.space {
            SpacePolicy::Required => whitespace_len > 0,
            SpacePolicy::Optional => true,
        };
        if space_ok {
            return Some((rule.level, rule.marker.len() + whitespace_len));
        }
    }
    None
}

fn number_end(candidate: &str, start: usize, level: HierarchyLevel) -> Option<usize> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    let style = catalog.number_style(level)?;
    let bytes = candidate.as_bytes();
    let first = *bytes.get(start)?;
    if first.is_ascii_digit() {
        let mut end = start;
        while let Some(byte) = bytes.get(end) {
            if byte.is_ascii_digit()
                || (*byte == b'.' && bytes.get(end + 1).is_some_and(u8::is_ascii_digit))
            {
                end += 1;
            } else {
                break;
            }
        }
        return (end > start).then_some(end);
    }
    if style != NumberStyle::RomanOrDigit {
        return None;
    }
    let mut end = start;
    while bytes.get(end).is_some_and(|byte| {
        matches!(
            byte.to_ascii_uppercase(),
            b'I' | b'V' | b'X' | b'L' | b'C' | b'D' | b'M'
        )
    }) {
        end += 1;
    }
    (end > start).then_some(end)
}

/// Try to match a numbered-list pattern (digit., digit), letter)) as a hierarchy marker.
/// Falls back when explicit prefixes (Статья, Глава) don't match.
/// All matching logic is driven by YAML NumberedMarkerRule fields.
fn numbered_marker_prefix(candidate: &str) -> Option<(HierarchyLevel, usize)> {
    let catalog = DecodePrefixCatalog::embedded().ok()?;
    let first_byte = candidate.as_bytes().first()?;
    for rule in &catalog.numbered_markers {
        let matches = match rule.number_style {
            NumberedStyle::Digit => first_byte.is_ascii_digit(),
            NumberedStyle::LetterCyrillic => {
                candidate.starts_with(|c: char| ('а'..='я').contains(&c))
            }
        };
        if !matches {
            continue;
        }
        // Walk the number: digits, and optionally dots-between-digits (YAML allow_compound)
        let bytes = candidate.as_bytes();
        let mut end = 0;
        while end < bytes.len() {
            let is_digit = bytes[end].is_ascii_digit();
            let is_compound_dot = rule.allow_compound
                && bytes[end] == b'.'
                && bytes.get(end + 1).is_some_and(u8::is_ascii_digit);
            if is_digit || is_compound_dot {
                end += 1;
            } else {
                break;
            }
        }
        if end == 0 {
            continue;
        }
        // Check that the suffix matches
        if let Some(&suffix_byte) = bytes.get(end) {
            if suffix_byte as char == rule.suffix {
                return Some((rule.level, 0));
            }
        }
    }
    None
}
