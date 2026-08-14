//! Classify hyperlinks based on surrounding context (YAML-driven).
//! Reads `link_classifiers` from kb-ontology.yaml — no hardcoded rules.

use crate::raw_link::RawLink;

const EMBEDDED_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

/// A classification rule from YAML.
#[derive(Debug, Clone, PartialEq)]
pub struct ClassifierRule {
    pub kind: String,
    pub context_needle: String,
    pub confidence: f64,
}

/// Classification result for a raw link.
#[derive(Debug, Clone, PartialEq)]
pub struct ClassifiedLink {
    pub dest: String,
    pub text: String,
    pub kind: String,
    pub confidence: f64,
}

/// Load classifier rules from the embedded YAML.
pub fn load_classifier_rules() -> Vec<ClassifierRule> {
    parse_link_classifiers(EMBEDDED_YAML)
}

/// Classify a single raw link using the given rules.
/// First matching rule wins (YAML order = priority order).
pub fn classify_link(link: &RawLink, rules: &[ClassifierRule]) -> ClassifiedLink {
    for rule in rules {
        if link.context.contains(&rule.context_needle) {
            return ClassifiedLink {
                dest: link.dest.clone(),
                text: link.text.clone(),
                kind: rule.kind.clone(),
                confidence: rule.confidence,
            };
        }
    }
    ClassifiedLink {
        dest: link.dest.clone(),
        text: link.text.clone(),
        kind: "unknown".to_owned(),
        confidence: 0.1,
    }
}

/// Classify all links using the embedded YAML rules.
pub fn classify_all(links: &[RawLink]) -> Vec<ClassifiedLink> {
    let rules = load_classifier_rules();
    links.iter().map(|l| classify_link(l, &rules)).collect()
}

/// Parse `link_classifiers:` section from YAML text.
fn parse_link_classifiers(text: &str) -> Vec<ClassifierRule> {
    let heading = "link_classifiers:";
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
        // Stop at next top-level key
        if !raw.starts_with(' ') && !raw.starts_with('\t') && line.ends_with(':') {
            break;
        }
        if !line.starts_with('-') {
            continue;
        }
        let kind = extract_field(line, "kind");
        let needle = extract_field(line, "context_needle");
        let conf = extract_field(line, "confidence")
            .and_then(|s| s.parse::<f64>().ok())
            .unwrap_or(0.5);
        if let (Some(kind), Some(needle)) = (kind, needle) {
            rules.push(ClassifierRule {
                kind,
                context_needle: needle,
                confidence: conf,
            });
        }
    }
    rules
}

fn extract_field(line: &str, key: &str) -> Option<String> {
    let pattern = format!("{key}: ");
    let rest = line.split(&pattern).nth(1)?;
    let val = rest.split(',').next()?.trim();
    let val = val.strip_prefix('"').unwrap_or(val);
    let val = val.strip_suffix('"').unwrap_or(val);
    let val = val.strip_suffix('}').unwrap_or(val);
    Some(val.trim().to_owned())
}
