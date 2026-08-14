//! Document profile detection (ADR-0027 Layer 1).
//! Determines document type from path needles, applies confidence boost.
//! All logic YAML-driven — new document types = new YAML entries.

const EMBEDDED_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

/// A document profile from YAML.
#[derive(Debug, Clone, PartialEq)]
pub struct DocumentProfile {
    pub name: String,
    pub path_needles: Vec<String>,
    pub boost: f64,
}

/// Detected profile for a document path.
#[derive(Debug, Clone, PartialEq)]
pub struct DetectedProfile {
    pub name: String,
    pub boost: f64,
}

/// Load document profiles from YAML.
pub fn load_profiles() -> Vec<DocumentProfile> {
    parse_document_profiles(EMBEDDED_YAML)
}

/// Detect the profile for a document path.
/// First profile whose needle matches the path wins; default is fallback.
pub fn detect_profile(profiles: &[DocumentProfile], path: &str) -> DetectedProfile {
    let path_lc = path.to_lowercase();
    for p in profiles {
        if p.name == "default" {
            continue;
        }
        if p.path_needles.iter().any(|n| path_lc.contains(n)) {
            return DetectedProfile {
                name: p.name.clone(),
                boost: p.boost,
            };
        }
    }
    // Default profile
    profiles
        .iter()
        .find(|p| p.name == "default")
        .map(|p| DetectedProfile {
            name: p.name.clone(),
            boost: p.boost,
        })
        .unwrap_or(DetectedProfile {
            name: "default".to_owned(),
            boost: 0.7,
        })
}

/// Apply profile boost to a raw classification confidence.
pub fn apply_boost(confidence: f64, profile: &DetectedProfile) -> f64 {
    confidence * profile.boost
}

/// Leading whitespace width: spaces count as 1, tabs as 2 (bounded YAML indent).
pub(crate) fn yaml_indent(raw: &str) -> usize {
    raw.chars()
        .take_while(|c| *c == ' ' || *c == '\t')
        .map(|c| if c == '\t' { 2 } else { 1 })
        .sum()
}

/// True when `raw` is a mapping key at `section_indent` (sibling of the heading).
/// List items (`- ...`) are not sibling keys even at the same indent.
pub(crate) fn is_yaml_sibling_key(raw: &str, section_indent: usize) -> bool {
    let indent = yaml_indent(raw);
    if indent != section_indent {
        return false;
    }
    let trimmed = raw.trim();
    !trimmed.is_empty()
        && !trimmed.starts_with('#')
        && !trimmed.starts_with('-')
        && trimmed.ends_with(':')
}

/// Collect lines of a YAML mapping section, stopping at the next sibling key
/// at the same indent as `heading` or at a shallower key.
pub(crate) fn yaml_section_lines<'a>(text: &'a str, heading: &str) -> Vec<&'a str> {
    let heading_pos = match text.find(heading) {
        Some(pos) => pos,
        None => return Vec::new(),
    };
    let heading_line_start = text[..heading_pos].rfind('\n').map(|i| i + 1).unwrap_or(0);
    let section_indent = yaml_indent(&text[heading_line_start..heading_pos]);
    let after = &text[heading_pos + heading.len()..];
    let mut out = Vec::new();
    for raw in after.lines() {
        let indent = yaml_indent(raw);
        let trimmed = raw.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            out.push(raw);
            continue;
        }
        if indent < section_indent || is_yaml_sibling_key(raw, section_indent) {
            break;
        }
        out.push(raw);
    }
    out
}

/// Parse `document_profiles:` section from YAML.
fn parse_document_profiles(text: &str) -> Vec<DocumentProfile> {
    parse_document_profiles_from(text)
}

/// Parse document profiles from YAML text. Test/helper surface; not a product API.
pub(crate) fn parse_document_profiles_from(text: &str) -> Vec<DocumentProfile> {
    let mut profiles = Vec::new();
    for raw in yaml_section_lines(text, "document_profiles:") {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') || !line.starts_with('-') {
            continue;
        }
        let name = extract_field(line, "name");
        let needles = extract_field(line, "path_needles")
            .map(|s| {
                s.split('|')
                    .map(|n| n.trim().to_owned())
                    .filter(|n| !n.is_empty())
                    .collect()
            })
            .unwrap_or_default();
        let boost = extract_field(line, "boost")
            .and_then(|s| s.parse::<f64>().ok())
            .unwrap_or(0.7);
        if let Some(name) = name {
            profiles.push(DocumentProfile {
                name,
                path_needles: needles,
                boost,
            });
        }
    }
    profiles
}

fn extract_field(line: &str, key: &str) -> Option<String> {
    let pattern = format!("{key}: ");
    let rest = line.split(&pattern).nth(1)?;
    let val = rest.split(',').next()?.trim();
    let val = val.strip_suffix('}').unwrap_or(val);
    let val = val
        .strip_prefix('"')
        .or_else(|| val.strip_prefix("'\""))
        .unwrap_or(val);
    let val = val
        .strip_suffix('"')
        .or_else(|| val.strip_suffix("'\""))
        .unwrap_or(val);
    Some(val.trim().to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    const NESTED: &str = r#"
vocabulary:
  document_profiles:
    - {name: federal_law, path_needles: "federalnyi-zakon|law_", boost: "1.0"}
    - {name: default, path_needles: "", boost: "0.7"}
  classifier_templates:
    - {name: amends_v_red, kind: amends, confidence: "0.9", match: all, needles: "ФЗ"}
assembly_fsm:
  current: S_ready_bounded
"#;

    #[test]
    fn sibling_section_at_same_indent_is_not_consumed() {
        let profiles = parse_document_profiles_from(NESTED);
        assert_eq!(profiles.len(), 2);
        assert_eq!(profiles[0].name, "federal_law");
        assert_eq!(profiles[1].name, "default");
        assert!(!profiles.iter().any(|p| p.name == "amends_v_red"));
    }

    #[test]
    fn missing_section_returns_empty() {
        assert!(parse_document_profiles_from("fsm:\n  current: O0\n").is_empty());
    }
}
