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
    pub context: String,
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
                context: link.context.clone(),
            };
        }
    }
    ClassifiedLink {
        dest: link.dest.clone(),
        text: link.text.clone(),
        kind: "unknown".to_owned(),
        confidence: 0.1,
        context: link.context.clone(),
    }
}

/// Classify all links using the embedded YAML rules.
pub fn classify_all(links: &[RawLink]) -> Vec<ClassifiedLink> {
    let rules = load_classifier_rules();
    links.iter().map(|l| classify_link(l, &rules)).collect()
}

/// Parse `link_classifiers:` section from YAML text.
fn parse_link_classifiers(text: &str) -> Vec<ClassifierRule> {
    parse_link_classifiers_from(text)
}

/// Parse link classifiers from YAML text. Test/helper surface; not a product API.
pub(crate) fn parse_link_classifiers_from(text: &str) -> Vec<ClassifierRule> {
    let mut rules = Vec::new();
    for raw in crate::document_profile::yaml_section_lines(text, "link_classifiers:") {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') || !line.starts_with('-') {
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
    /// Bounded morph variants. Any configured variant counts as one morph signal.
    pub morph_needles: Vec<String>,
}

/// Load multi-signal templates from YAML `classifier_templates`.
pub fn load_templates() -> Vec<Template> {
    parse_classifier_templates(EMBEDDED_YAML)
}

/// Score a link against one template. Returns confidence if match, 0.0 if not.
///
/// - match_all (AND): all contains needles and the morph signal (if configured) must match → full confidence
/// - match_any (OR): at least one contains needle or morph signal → confidence × (matched / total)
///
/// Morph is one extra signal: it matches when any configured variant is contained.
/// Empty morph_needles is not a signal (no extra slot).
pub fn score_template(template: &Template, link: &RawLink) -> f64 {
    let needle_total = template.needles.len();
    let morph_slot = usize::from(!template.morph_needles.is_empty());
    let total = needle_total + morph_slot;
    if total == 0 {
        return 0.0;
    }
    let needle_matched = template
        .needles
        .iter()
        .filter(|n| link.context.contains(n.as_str()))
        .count();
    let morph_matched = usize::from(
        !template.morph_needles.is_empty()
            && template
                .morph_needles
                .iter()
                .any(|n| link.context.contains(n.as_str())),
    );
    let matched = needle_matched + morph_matched;
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
        context: link.context.clone(),
    };
    for t in templates {
        let score = score_template(t, link);
        if score > best.confidence {
            best = ClassifiedLink {
                dest: link.dest.clone(),
                text: link.text.clone(),
                kind: t.kind.clone(),
                confidence: score,
                context: link.context.clone(),
            };
        }
    }
    best
}

/// Classify all links using the scoring engine (templates preferred).
/// Compatibility wrapper: empty path → default document profile (boost only).
pub fn classify_all_scored(links: &[RawLink]) -> Vec<ClassifiedLink> {
    classify_all_scored_for_path(links, "")
}

/// Path-aware scored classification: detect a YAML document profile from
/// `source_path` and multiply the winning template confidence by `apply_boost`.
/// Legal kind is never changed by the profile. Unknown stays at baseline 0.1.
pub fn classify_all_scored_for_path(links: &[RawLink], source_path: &str) -> Vec<ClassifiedLink> {
    let templates = load_templates();
    if templates.is_empty() {
        return classify_all(links);
    }
    let profiles = crate::document_profile::load_profiles();
    let profile = crate::document_profile::detect_profile(&profiles, source_path);
    links
        .iter()
        .map(|l| {
            let mut classified = classify_link_scored(l, &templates);
            if classified.kind != "unknown" {
                classified.confidence =
                    crate::document_profile::apply_boost(classified.confidence, &profile);
            }
            classified
        })
        .collect()
}

/// Parse `classifier_templates:` section from YAML.
fn parse_classifier_templates(text: &str) -> Vec<Template> {
    parse_classifier_templates_from(text)
}

/// Parse classifier templates from YAML text. Test/helper surface; not a product API.
pub(crate) fn parse_classifier_templates_from(text: &str) -> Vec<Template> {
    let mut templates = Vec::new();
    for raw in crate::document_profile::yaml_section_lines(text, "classifier_templates:") {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') || !line.starts_with('-') {
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
            .map(|s| {
                s.split('|')
                    .map(|n| n.trim().to_owned())
                    .filter(|n| !n.is_empty())
                    .collect()
            })
            .unwrap_or_default();
        let morph_needles: Vec<String> = extract_field(line, "morph_needles")
            .map(|s| {
                s.split('|')
                    .map(|n| n.trim().to_owned())
                    .filter(|n| !n.is_empty())
                    .collect()
            })
            .unwrap_or_default();
        if !needles.is_empty() || !morph_needles.is_empty() {
            templates.push(Template {
                name,
                kind,
                confidence,
                match_all,
                needles,
                morph_needles,
            });
        }
    }
    templates
}

#[cfg(test)]
mod tests {
    use super::*;

    const NESTED: &str = r#"
vocabulary:
  link_classifiers:
    - {kind: amends, context_needle: "в ред.", confidence: 0.9}
  document_profiles:
    - {name: federal_law, path_needles: "law_", boost: "1.0"}
  classifier_templates:
    - {name: amends_v_red, kind: amends, confidence: "0.9", match: all, needles: "ФЗ", morph_needles: "в ред.|в редакции"}
assembly_fsm:
  current: S_ready_bounded
"#;

    #[test]
    fn sibling_sections_do_not_leak_into_link_classifiers() {
        let rules = parse_link_classifiers_from(NESTED);
        assert_eq!(rules.len(), 1);
        assert_eq!(rules[0].kind, "amends");
        assert_eq!(rules[0].context_needle, "в ред.");
        assert!(!rules.iter().any(|r| r.kind == "federal_law"));
    }

    #[test]
    fn sibling_sections_do_not_leak_into_templates() {
        let templates = parse_classifier_templates_from(NESTED);
        assert_eq!(templates.len(), 1);
        assert_eq!(templates[0].name, "amends_v_red");
        assert_eq!(templates[0].needles, vec!["ФЗ".to_owned()]);
        assert_eq!(
            templates[0].morph_needles,
            vec!["в ред.".to_owned(), "в редакции".to_owned()]
        );
    }
}
