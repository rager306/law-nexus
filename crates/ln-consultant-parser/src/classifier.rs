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
    // Strip wrapping: "value"} → value  (} first, then ")
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

// ─── Multi-signal scoring engine (ADR-0027) ──────────────────────────────

/// A multi-signal template: composable needles with AND/OR logic.
#[derive(Debug, Clone)]
pub struct Template {
    pub name: String,
    pub kind: String,
    pub confidence: f64,
    pub match_all: bool,
    pub needles: Vec<String>,
}

/// Load multi-signal templates from YAML `classifier_templates`.
pub fn load_templates() -> Vec<Template> {
    parse_classifier_templates(EMBEDDED_YAML)
}

/// Score a link against one template. Returns confidence if match, 0.0 if not.
///
/// - match_all (AND): all needles must match → full confidence
/// - match_any (OR): at least one → confidence × (matched / total)
pub fn score_template(template: &Template, link: &RawLink) -> f64 {
    let total = template.needles.len();
    if total == 0 {
        return 0.0;
    }
    let matched = template
        .needles
        .iter()
        .filter(|n| link.context.contains(n.as_str()))
        .count();
    if template.match_all {
        if matched == total {
            template.confidence
        } else {
            0.0
        }
    } else if matched > 0 {
        template.confidence * (matched as f64 / total as f64)
    } else {
        0.0
    }
}

/// Classify using multi-signal scoring. Best score wins; ties → YAML order.
pub fn classify_link_scored(link: &RawLink, templates: &[Template]) -> ClassifiedLink {
    let mut best = ClassifiedLink {
        dest: link.dest.clone(),
        text: link.text.clone(),
        kind: "unknown".to_owned(),
        confidence: 0.1,
    };
    for t in templates {
        let score = score_template(t, link);
        if score > best.confidence {
            best = ClassifiedLink {
                dest: link.dest.clone(),
                text: link.text.clone(),
                kind: t.kind.clone(),
                confidence: score,
            };
        }
    }
    best
}

/// Classify all links using the scoring engine (templates preferred).
pub fn classify_all_scored(links: &[RawLink]) -> Vec<ClassifiedLink> {
    let templates = load_templates();
    if templates.is_empty() {
        return classify_all(links);
    }
    links
        .iter()
        .map(|l| classify_link_scored(l, &templates))
        .collect()
}

/// Parse `classifier_templates:` section from YAML.
fn parse_classifier_templates(text: &str) -> Vec<Template> {
    let heading = "classifier_templates:";
    let start = match text.find(heading) {
        Some(pos) => pos + heading.len(),
        None => return Vec::new(),
    };
    let mut templates = Vec::new();
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
        let name = extract_field(line, "name").unwrap_or_default();
        let kind = match extract_field(line, "kind") {
            Some(k) => k,
            None => continue,
        };
        let confidence = extract_field(line, "confidence")
            .and_then(|s| s.parse::<f64>().ok())
            .unwrap_or(0.5);
        let match_all = extract_field(line, "match").is_some_and(|m| m == "all");
        let needles: Vec<String> = extract_field(line, "needles")
            .map(|s| s.split('|').map(|n| n.trim().to_owned()).collect())
            .unwrap_or_default();
        if !needles.is_empty() {
            templates.push(Template {
                name,
                kind,
                confidence,
                match_all,
                needles,
            });
        }
    }
    templates
}
