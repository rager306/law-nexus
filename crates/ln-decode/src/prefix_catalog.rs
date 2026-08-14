//! YAML-backed decode marker prefixes and number styles.
//!
//! The catalog is data (`prd/architecture/kb-ontology.yaml`). This module does
//! not depend on `ln-kb-ontology` and must not invent prefixes absent from YAML.

use crate::domain::HierarchyLevel;

pub const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NumberStyle {
    Digit,
    RomanOrDigit,
}

/// Number style for numbered markers (Часть/Пункт/Подпункт).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NumberedStyle {
    Digit,
    LetterCyrillic,
}

/// A numbered-list hierarchy rule: «digit.» → Chast, «digit)» → Punkt.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NumberedMarkerRule {
    pub level: HierarchyLevel,
    pub number_style: NumberedStyle,
    pub suffix: char,
    pub allow_compound: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SpacePolicy {
    Required,
    Optional,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PrefixRule {
    pub level: HierarchyLevel,
    pub marker: String,
    pub space: SpacePolicy,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DecodePrefixCatalog {
    pub prefixes: Vec<PrefixRule>,
    pub number_styles: Vec<(HierarchyLevel, NumberStyle)>,
    pub numbered_markers: Vec<NumberedMarkerRule>,
}

impl DecodePrefixCatalog {
    pub fn embedded() -> Result<Self, &'static str> {
        Self::parse_yaml(EMBEDDED_ONTOLOGY_YAML)
    }

    pub fn parse_yaml(text: &str) -> Result<Self, &'static str> {
        let prefix_lists = map_inline_lists(text, "decode_marker_prefixes:")?;
        if prefix_lists.is_empty() {
            return Err("decode_marker_prefixes missing");
        }
        let space_pairs = map_scalars(text, "decode_prefix_space_policy:")?;
        let style_pairs = map_scalars(text, "decode_number_styles:")?;
        let default_space = space_pairs
            .iter()
            .find(|(key, _)| key == "default")
            .map(|(_, value)| parse_space(value))
            .unwrap_or(Some(SpacePolicy::Required))
            .ok_or("invalid default space policy")?;

        let mut prefixes = Vec::new();
        for (token, markers) in prefix_lists {
            let level =
                HierarchyLevel::from_token(&token).ok_or("prefix key is not a decode token")?;
            let space = space_pairs
                .iter()
                .find(|(key, _)| key == &token)
                .map(|(_, value)| parse_space(value))
                .unwrap_or(Some(default_space))
                .ok_or("invalid space policy")?;
            for marker in markers {
                if marker.is_empty() {
                    return Err("empty decode marker prefix");
                }
                prefixes.push(PrefixRule {
                    level,
                    marker,
                    space,
                });
            }
        }
        prefixes.sort_by(|left, right| right.marker.len().cmp(&left.marker.len()));

        let mut number_styles = Vec::new();
        for (token, style) in style_pairs {
            let level = HierarchyLevel::from_token(&token)
                .ok_or("number-style key is not a decode token")?;
            let style = parse_style(&style).ok_or("unknown number style")?;
            number_styles.push((level, style));
        }
        if number_styles.is_empty() {
            return Err("decode_number_styles missing");
        }
        let numbered_markers = parse_numbered_markers(text);
        Ok(Self {
            prefixes,
            number_styles,
            numbered_markers,
        })
    }

    pub fn number_style(&self, level: HierarchyLevel) -> Option<NumberStyle> {
        self.number_styles
            .iter()
            .find(|(item, _)| *item == level)
            .map(|(_, style)| *style)
    }
}

fn parse_space(value: &str) -> Option<SpacePolicy> {
    match value {
        "required" => Some(SpacePolicy::Required),
        "optional" => Some(SpacePolicy::Optional),
        _ => None,
    }
}

fn parse_style(value: &str) -> Option<NumberStyle> {
    match value {
        "digit" => Some(NumberStyle::Digit),
        "roman_or_digit" => Some(NumberStyle::RomanOrDigit),
        _ => None,
    }
}

fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => line[..index].trim_end(),
        None => line.trim_end(),
    }
}

fn map_inline_lists(text: &str, heading: &str) -> Result<Vec<(String, Vec<String>)>, &'static str> {
    let mut rows = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == heading {
            in_map = true;
            heading_indent = indent;
            continue;
        }
        if in_map && indent <= heading_indent {
            break;
        }
        if !in_map {
            continue;
        }
        let line = trimmed.trim();
        let Some((key, rest)) = line.split_once(':') else {
            continue;
        };
        let key = key.trim();
        if key.is_empty() {
            continue;
        }
        let items = parse_inline_list(rest.trim())?;
        rows.push((key.to_owned(), items));
    }
    Ok(rows)
}

fn map_scalars(text: &str, heading: &str) -> Result<Vec<(String, String)>, &'static str> {
    let mut rows = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == heading {
            in_map = true;
            heading_indent = indent;
            continue;
        }
        if in_map && indent <= heading_indent {
            break;
        }
        if !in_map {
            continue;
        }
        let line = trimmed.trim();
        let Some((key, value)) = line.split_once(':') else {
            continue;
        };
        let key = key.trim();
        let value = unquote(value.trim());
        if key.is_empty() || value.is_empty() {
            continue;
        }
        rows.push((key.to_owned(), value));
    }
    Ok(rows)
}

fn parse_inline_list(raw: &str) -> Result<Vec<String>, &'static str> {
    let body = raw
        .strip_prefix('[')
        .and_then(|value| value.strip_suffix(']'))
        .ok_or("decode marker prefixes must be inline lists")?;
    let mut items = Vec::new();
    for part in body.split(',') {
        let item = unquote(part.trim());
        if !item.is_empty() {
            items.push(item);
        }
    }
    if items.is_empty() {
        return Err("empty decode marker list");
    }
    Ok(items)
}

fn unquote(value: &str) -> String {
    value.trim().trim_matches('"').trim_matches('\'').to_owned()
}

/// Parse `decode_numbered_markers:` section from YAML.
/// Lines: `Chast: {number_style: digit, suffix: "."}`
fn parse_numbered_markers(text: &str) -> Vec<NumberedMarkerRule> {
    let heading = "decode_numbered_markers:";
    let start = match text.find(heading) {
        Some(pos) => pos + heading.len(),
        None => return Vec::new(),
    };
    let mut rules = Vec::new();
    for raw in text[start..].lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        // Stop at the next top-level key (non-indented, ends with ':')
        if !raw.starts_with(' ') && !raw.starts_with('\t') && line.ends_with(':') {
            break;
        }
        // Must look like: Level: {number_style: ..., suffix: ...}
        let Some(colon_pos) = line.find(':') else {
            continue;
        };
        let token = line[..colon_pos].trim();
        let Some(level) = HierarchyLevel::from_token(token) else {
            continue;
        };
        let rest = &line[colon_pos + 1..];
        let number_style = if rest.contains("letter_cyrillic") {
            NumberedStyle::LetterCyrillic
        } else {
            NumberedStyle::Digit
        };
        // Extract suffix: look for suffix: "X" or suffix: X
        let suffix = rest
            .split("suffix:")
            .nth(1)
            .and_then(|s| {
                let s = s.trim();
                if let Some(quoted) = s.strip_prefix('"') {
                    quoted.chars().next()
                } else {
                    s.chars().next()
                }
            })
            .unwrap_or('.');
        rules.push(NumberedMarkerRule {
            level,
            number_style,
            suffix,
            allow_compound: rest.contains("allow_compound: true"),
        });
    }
    rules
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_prefix_catalog_covers_current_extractable_tokens() {
        let catalog = DecodePrefixCatalog::embedded().expect("yaml");
        assert!(catalog
            .prefixes
            .iter()
            .any(|rule| rule.level == HierarchyLevel::Statya && rule.marker == "Статья"));
        assert!(catalog
            .prefixes
            .iter()
            .any(|rule| rule.level == HierarchyLevel::Paragraph && rule.marker == "§"));
        assert_eq!(
            catalog.number_style(HierarchyLevel::Razdel),
            Some(NumberStyle::RomanOrDigit)
        );
        assert_eq!(
            catalog.number_style(HierarchyLevel::Statya),
            Some(NumberStyle::Digit)
        );
    }
}
