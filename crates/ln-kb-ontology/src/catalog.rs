//! Load the YAML ontology catalog. Kinds, levels, and FSM transitions are not
//! hardcoded in Rust; unknown tokens fail closed.

use std::fmt;

pub const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogError {
    reason: &'static str,
}

impl fmt::Display for CatalogError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "ontology catalog: {}", self.reason)
    }
}

impl std::error::Error for CatalogError {}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FsmTransition {
    pub from: String,
    pub to: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OntologyCatalog {
    pub schema_version: String,
    pub current_state: String,
    pub states: Vec<String>,
    pub transitions: Vec<FsmTransition>,
    pub hierarchy_levels: Vec<String>,
    pub node_kinds: Vec<String>,
    pub edge_kinds: Vec<String>,
    pub forbidden_node_kinds: Vec<String>,
    pub presence_change_kinds: Vec<String>,
    pub membership_change_kinds: Vec<String>,
    pub industrial_op_kinds: Vec<String>,
    pub force_status_values: Vec<String>,
    pub decode_level_aliases: Vec<(String, String)>,
    pub presence_fold_ops: Vec<(String, String)>,
}

impl OntologyCatalog {
    pub fn embedded() -> Result<Self, CatalogError> {
        Self::parse_yaml(EMBEDDED_ONTOLOGY_YAML)
    }

    pub fn parse_yaml(text: &str) -> Result<Self, CatalogError> {
        let schema_version = required_scalar(text, "schema_version")?;
        let current_state = required_nested_scalar(text, "fsm:", "current:")?;
        let states = map_keys_under(text, "states:")?;
        if states.is_empty() {
            return Err(CatalogError {
                reason: "fsm.states is empty",
            });
        }
        if !states.iter().any(|state| state == &current_state) {
            return Err(CatalogError {
                reason: "fsm.current is not a declared state",
            });
        }
        let transitions = parse_transitions(text)?;
        for edge in &transitions {
            if !states.iter().any(|state| state == &edge.from)
                || !states.iter().any(|state| state == &edge.to)
            {
                return Err(CatalogError {
                    reason: "fsm transition names an unknown state",
                });
            }
        }
        let hierarchy_levels = list_under_vocabulary(text, "hierarchy_levels:")?;
        let node_kinds = list_under_vocabulary(text, "node_kinds:")?;
        let edge_kinds = list_under_vocabulary(text, "edge_kinds:")?;
        let forbidden_node_kinds = list_under_vocabulary(text, "forbidden_node_kinds:")?;
        let presence_change_kinds = list_under_vocabulary(text, "presence_change_kinds:")?;
        let membership_change_kinds = list_under_vocabulary(text, "membership_change_kinds:")?;
        let industrial_op_kinds = list_under_vocabulary(text, "industrial_op_kinds:")?;
        let force_status_values = list_under_vocabulary(text, "force_status_values:")?;
        let decode_level_aliases = map_pairs_under_vocabulary(text, "decode_level_aliases:")?;
        let presence_fold_ops = map_pairs_under_vocabulary(text, "presence_fold_ops:")?;
        if hierarchy_levels.is_empty() || node_kinds.is_empty() || forbidden_node_kinds.is_empty() {
            return Err(CatalogError {
                reason: "vocabulary lists are incomplete",
            });
        }
        for (_, target) in &decode_level_aliases {
            if !hierarchy_levels.iter().any(|level| level == target) {
                return Err(CatalogError {
                    reason: "decode alias target is not a hierarchy level",
                });
            }
        }
        Ok(Self {
            schema_version,
            current_state,
            states,
            transitions,
            hierarchy_levels,
            node_kinds,
            edge_kinds,
            forbidden_node_kinds,
            presence_change_kinds,
            membership_change_kinds,
            industrial_op_kinds,
            force_status_values,
            decode_level_aliases,
            presence_fold_ops,
        })
    }

    pub fn is_hierarchy_level(&self, level: &str) -> bool {
        self.hierarchy_levels.iter().any(|item| item == level)
    }

    pub fn is_node_kind(&self, kind: &str) -> bool {
        self.node_kinds.iter().any(|item| item == kind)
    }

    pub fn is_edge_kind(&self, kind: &str) -> bool {
        self.edge_kinds.iter().any(|item| item == kind)
    }

    pub fn is_forbidden_kind(&self, kind: &str) -> bool {
        self.forbidden_node_kinds.iter().any(|item| item == kind)
    }

    pub fn is_known_state(&self, state: &str) -> bool {
        self.states.iter().any(|item| item == state)
    }

    pub fn allows_transition(&self, from: &str, to: &str) -> bool {
        self.transitions
            .iter()
            .any(|edge| edge.from == from && edge.to == to)
    }

    pub fn is_presence_change_kind(&self, kind: &str) -> bool {
        self.presence_change_kinds.iter().any(|item| item == kind)
    }

    pub fn is_membership_change_kind(&self, kind: &str) -> bool {
        self.membership_change_kinds.iter().any(|item| item == kind)
    }

    pub fn is_industrial_op_kind(&self, kind: &str) -> bool {
        self.industrial_op_kinds.iter().any(|item| item == kind)
    }

    pub fn is_force_status(&self, value: &str) -> bool {
        self.force_status_values.iter().any(|item| item == value)
    }

    pub fn presence_fold_op(&self, kind: &str) -> Option<&str> {
        self.presence_fold_ops
            .iter()
            .find(|(source, _)| source == kind)
            .map(|(_, op)| op.as_str())
    }

    pub fn resolve_decode_level_alias(&self, token: &str) -> Option<String> {
        self.decode_level_aliases
            .iter()
            .find(|(source, _)| source == token)
            .map(|(_, target)| target.clone())
            .or_else(|| {
                if self.is_hierarchy_level(token) {
                    Some(token.to_owned())
                } else {
                    None
                }
            })
    }
}

fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => line[..index].trim_end(),
        None => line.trim_end(),
    }
}

fn required_scalar(text: &str, key: &str) -> Result<String, CatalogError> {
    for raw in text.lines() {
        let line = strip_comment(raw).trim();
        let prefix = format!("{key}:");
        if let Some(rest) = line.strip_prefix(&prefix) {
            let value = rest.trim().trim_matches('"');
            if !value.is_empty() {
                return Ok(value.to_owned());
            }
        }
    }
    Err(CatalogError {
        reason: "required scalar missing",
    })
}

fn required_nested_scalar(text: &str, section: &str, key: &str) -> Result<String, CatalogError> {
    let mut in_section = false;
    let mut section_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == section {
            in_section = true;
            section_indent = indent;
            continue;
        }
        if in_section && indent <= section_indent && trimmed.trim().ends_with(':') {
            in_section = false;
        }
        if in_section {
            let line = trimmed.trim();
            if let Some(rest) = line.strip_prefix(key) {
                let value = rest.trim().trim_matches('"');
                if !value.is_empty() {
                    return Ok(value.to_owned());
                }
            }
        }
    }
    Err(CatalogError {
        reason: "required nested scalar missing",
    })
}

fn map_keys_under(text: &str, heading: &str) -> Result<Vec<String>, CatalogError> {
    let mut keys = Vec::new();
    let mut in_section = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == heading {
            in_section = true;
            heading_indent = indent;
            continue;
        }
        if in_section && indent <= heading_indent {
            break;
        }
        if in_section && indent > heading_indent {
            let line = trimmed.trim();
            if let Some(name) = line.strip_suffix(':') {
                if !name.is_empty() && !name.contains(' ') && !name.starts_with('-') {
                    keys.push(name.to_owned());
                }
            }
        }
    }
    Ok(keys)
}

fn list_under_vocabulary(text: &str, heading: &str) -> Result<Vec<String>, CatalogError> {
    let vocab_start = text.find("\nvocabulary:").or_else(|| {
        if text.starts_with("vocabulary:") {
            Some(0)
        } else {
            None
        }
    });
    let Some(start) = vocab_start else {
        return Err(CatalogError {
            reason: "vocabulary section missing",
        });
    };
    let slice = &text[start..];
    let mut items = Vec::new();
    let mut in_list = false;
    let mut heading_indent = 0usize;
    for raw in slice.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == heading {
            in_list = true;
            heading_indent = indent;
            continue;
        }
        if in_list && indent <= heading_indent && !trimmed.trim().starts_with('-') {
            break;
        }
        if in_list {
            if let Some(item) = trimmed.trim().strip_prefix("- ") {
                items.push(item.trim().to_owned());
            }
        }
    }
    Ok(items)
}

fn map_pairs_under_vocabulary(
    text: &str,
    heading: &str,
) -> Result<Vec<(String, String)>, CatalogError> {
    let vocab_start = text.find("\nvocabulary:").or_else(|| {
        if text.starts_with("vocabulary:") {
            Some(0)
        } else {
            None
        }
    });
    let Some(start) = vocab_start else {
        return Err(CatalogError {
            reason: "vocabulary section missing",
        });
    };
    let slice = &text[start..];
    let mut pairs = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in slice.lines() {
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
        if in_map {
            let line = trimmed.trim();
            if let Some((key, value)) = line.split_once(':') {
                let key = key.trim();
                let value = value.trim();
                if !key.is_empty() && !value.is_empty() {
                    pairs.push((key.to_owned(), value.to_owned()));
                }
            }
        }
    }
    Ok(pairs)
}

fn parse_transitions(text: &str) -> Result<Vec<FsmTransition>, CatalogError> {
    let mut edges = Vec::new();
    let mut in_transitions = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == "transitions:" {
            in_transitions = true;
            heading_indent = indent;
            continue;
        }
        if in_transitions && indent <= heading_indent && !trimmed.trim().starts_with('-') {
            break;
        }
        if !in_transitions {
            continue;
        }
        let line = trimmed.trim();
        if !(line.contains("from:") && line.contains("to:")) {
            continue;
        }
        let Some(from) = flow_field(line, "from") else {
            continue;
        };
        let Some(to) = flow_field(line, "to") else {
            continue;
        };
        edges.push(FsmTransition { from, to });
    }
    if edges.is_empty() {
        return Err(CatalogError {
            reason: "fsm.transitions missing",
        });
    }
    Ok(edges)
}

fn flow_field(line: &str, key: &str) -> Option<String> {
    let token = format!("{key}:");
    let rest = line.split(&token).nth(1)?;
    let value = rest.split([',', '}', ' ']).find(|part| !part.is_empty())?;
    Some(value.trim().to_owned())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_catalog_declares_current_state_and_levels() {
        let catalog = OntologyCatalog::embedded().expect("yaml");
        assert!(catalog.is_known_state(&catalog.current_state));
        assert!(catalog.is_hierarchy_level("statya"));
        assert!(catalog.is_forbidden_kind("ApplicableDecision"));
        assert!(catalog.allows_transition("O2_decode_lift", "O2_catalog_kinds"));
        assert!(!catalog.allows_transition("O1", "O6_closed_validated"));
        assert!(catalog.is_node_kind("Manifestation"));
        assert!(!catalog.is_node_kind("NormativeBlobAsWork"));
        assert_eq!(catalog.presence_fold_op("include"), Some("add"));
        assert_eq!(
            catalog.resolve_decode_level_alias("Statya").as_deref(),
            Some("statya")
        );
        assert!(catalog.is_presence_change_kind("include"));
        assert!(catalog.is_industrial_op_kind("split"));
        assert!(catalog.is_force_status("unknown"));
    }
}
