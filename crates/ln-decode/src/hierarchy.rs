//! Bounded provider-neutral hierarchy extraction from decoded block text.

use crate::domain::{HierarchyLevel, HierarchyNode, ParsedBlock, TextSpan};

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
    let (level, number_start) = marker_prefix(candidate)?;
    let number_end = number_end(candidate, number_start, level)?;
    let number = &candidate[number_start..number_end];
    let punctuation = candidate.as_bytes().get(number_end).copied()?;
    if !matches!(punctuation, b'.' | b':') {
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
    for (variants, level) in [
        (
            ["Раздел", "РАЗДЕЛ", "раздел"].as_slice(),
            HierarchyLevel::Razdel,
        ),
        (
            ["Глава", "ГЛАВА", "глава"].as_slice(),
            HierarchyLevel::Glava,
        ),
        (
            ["Статья", "СТАТЬЯ", "статья"].as_slice(),
            HierarchyLevel::Statya,
        ),
    ] {
        for marker in variants {
            if let Some(rest) = candidate.strip_prefix(marker) {
                let whitespace_len = rest
                    .char_indices()
                    .take_while(|(_, character)| character.is_whitespace())
                    .map(|(_, character)| character.len_utf8())
                    .sum::<usize>();
                if whitespace_len > 0 {
                    return Some((level, marker.len() + whitespace_len));
                }
            }
        }
    }

    let rest = candidate.strip_prefix('§')?;
    let whitespace_len = rest
        .char_indices()
        .take_while(|(_, character)| character.is_whitespace())
        .map(|(_, character)| character.len_utf8())
        .sum::<usize>();
    Some((HierarchyLevel::Paragraph, '§'.len_utf8() + whitespace_len))
}

fn number_end(candidate: &str, start: usize, level: HierarchyLevel) -> Option<usize> {
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

    if !matches!(level, HierarchyLevel::Razdel | HierarchyLevel::Glava) {
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
