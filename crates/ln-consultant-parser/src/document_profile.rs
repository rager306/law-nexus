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

/// Parse `document_profiles:` section from YAML.
fn parse_document_profiles(text: &str) -> Vec<DocumentProfile> {
    let heading = "document_profiles:";
    let start = match text.find(heading) {
        Some(pos) => pos + heading.len(),
        None => return Vec::new(),
    };
    let mut profiles = Vec::new();
    for raw in text[start..].lines() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if !raw.starts_with(' ') && !raw.starts_with('\t') && line.ends_with(':') {
            break;
        }
        if !line.starts_with('-') {
            continue;
        }
        let name = extract_field(line, "name");
        let needles = extract_field(line, "path_needles")
            .map(|s| s.split('|').map(|n| n.trim().to_owned()).collect())
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
