//! Load the YAML ontology catalog. Kinds, levels, and FSM transitions are not
//! hardcoded in Rust; unknown tokens fail closed.

use std::fmt;

pub const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CatalogError {
    reason: &'static str,
}

impl CatalogError {
    pub(crate) fn new(reason: &'static str) -> Self {
        Self { reason }
    }
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
pub struct CorpusRoleSignal {
    pub role: String,
    pub field: String,
    pub needle: String,
    pub rank: u32,
}

/// One ranked metadata needle of a document group (factor A of detection).
/// `field` is one of `kind` / `type` / `path`; lower `rank` wins, mirroring
/// `corpus_role_signals` ranking (same-rank different groups is Conflict).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GroupNeedle {
    pub field: String,
    pub needle: String,
    pub rank: u32,
}

/// One ladder entry of a document structural profile: token + role + style.
/// The token is a hierarchy marker name (decode token or structural-only
/// pseudo-token); the role comes from the closed `structural_roles` set.
/// `surface` is the marker text for structural-only tokens (e.g.
/// primechanie -> "Примечание") — the collector recognizes these markers by
/// surface prefix because they have no decode `HierarchyLevel` (R8-09).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LadderEntry {
    pub token: String,
    pub role: String,
    pub recursive: bool,
    pub max_depth: Option<u32>,
    pub compound: Option<bool>,
    pub suffix: Option<String>,
    pub number_style: Option<String>,
    pub surface: Option<String>,
}

/// A document structural profile from `document_groups` (system_observation
/// heuristic, never legal classification; practice is not an AST, ADR-0020).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentGroup {
    pub id: String,
    pub granularity: Option<String>,
    pub text_boundary: Vec<String>,
    pub max_depth: Option<u32>,
    pub text_only: bool,
    pub needles: Vec<GroupNeedle>,
    pub ladder: Vec<LadderEntry>,
}

/// Parsed `document_groups:` section: closed role vocabulary, structural-only
/// tokens, non-claims, and the groups themselves.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct DocumentGroupsSection {
    pub structural_roles: Vec<String>,
    pub structural_only_tokens: Vec<String>,
    pub non_claims: Vec<String>,
    pub groups: Vec<DocumentGroup>,
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
    pub corpus_roles: Vec<String>,
    pub corpus_role_signals: Vec<CorpusRoleSignal>,
    pub cross_act_edge_kinds: Vec<String>,
    pub structural_roles: Vec<String>,
    pub structural_only_tokens: Vec<String>,
    pub document_group_non_claims: Vec<String>,
    pub document_groups: Vec<DocumentGroup>,
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
        let corpus_roles = list_under_vocabulary(text, "corpus_roles:")?;
        let corpus_role_signals = parse_corpus_role_signals(text)?;
        let cross_act_edge_kinds =
            list_under_vocabulary(text, "cross_act_edge_kinds:").unwrap_or_default();
        for signal in &corpus_role_signals {
            if !corpus_roles.iter().any(|role| role == &signal.role) {
                return Err(CatalogError {
                    reason: "corpus_role_signal names an unknown role",
                });
            }
        }
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
        let document_groups_section = parse_document_groups(text)?;
        validate_document_groups(&document_groups_section, &decode_level_aliases)?;
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
            corpus_roles,
            corpus_role_signals,
            cross_act_edge_kinds,
            structural_roles: document_groups_section.structural_roles,
            structural_only_tokens: document_groups_section.structural_only_tokens,
            document_group_non_claims: document_groups_section.non_claims,
            document_groups: document_groups_section.groups,
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

    pub fn is_cross_act_edge_kind(&self, kind: &str) -> bool {
        self.cross_act_edge_kinds.iter().any(|item| item == kind)
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

    pub fn hierarchy_level_rank(&self, level: &str) -> Option<usize> {
        self.hierarchy_levels.iter().position(|item| item == level)
    }

    /// R087/R8-13 recursive propose rank: (role order, ladder depth).
    /// Role order is the declaration position in `hierarchy_levels`; depth is
    /// the marker's path-segment count (flat markers are depth 1). Tuple
    /// lexicographic ordering keeps `pop while top >= rank` unchanged, while
    /// nested punkt ladders (4 -> 4.1 -> 4.1.2) no longer collapse to
    /// siblings: their depths differ even though the role order is equal.
    pub fn propose_rank(&self, level: &str, depth: usize) -> Option<(usize, usize)> {
        self.hierarchy_level_rank(level)
            .map(|role_order| (role_order, depth))
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

    /// Look up a document structural profile by id.
    pub fn document_group(&self, id: &str) -> Option<&DocumentGroup> {
        self.document_groups.iter().find(|group| group.id == id)
    }

    /// True when `role` is a declared structural role (closed vocabulary).
    pub fn is_structural_role(&self, role: &str) -> bool {
        self.structural_roles.iter().any(|item| item == role)
    }
}

pub(crate) fn strip_comment(line: &str) -> &str {
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

pub(crate) fn flow_field(line: &str, key: &str) -> Option<String> {
    let token = format!("{key}:");
    let bytes = line.as_bytes();
    let mut offset = 0usize;
    let start = loop {
        let rest = line.get(offset..)?;
        let rel = rest.find(&token)?;
        let abs = offset + rel;
        let boundary = abs == 0
            || matches!(
                bytes.get(abs.saturating_sub(1)).copied(),
                Some(b' ' | b',' | b'{' | b'-' | b'\t')
            );
        if boundary {
            break abs + token.len();
        }
        offset = abs + token.len();
    };
    let rest = line.get(start..)?.trim_start();
    if let Some(quoted) = rest.strip_prefix('"') {
        let end = quoted.find('"')?;
        return Some(quoted[..end].to_owned());
    }
    let value = rest.split([',', '}', ' ']).find(|part| !part.is_empty())?;
    Some(value.trim().to_owned())
}

fn parse_corpus_role_signals(text: &str) -> Result<Vec<CorpusRoleSignal>, CatalogError> {
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
    let mut signals = Vec::new();
    let mut in_list = false;
    let mut heading_indent = 0usize;
    for raw in slice.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == "corpus_role_signals:" {
            in_list = true;
            heading_indent = indent;
            continue;
        }
        if in_list && indent <= heading_indent && !trimmed.trim().starts_with('-') {
            break;
        }
        if !in_list {
            continue;
        }
        let line = trimmed.trim();
        if !line.starts_with('-') {
            continue;
        }
        let Some(role) = flow_field(line, "role") else {
            return Err(CatalogError {
                reason: "corpus_role_signal missing role",
            });
        };
        let Some(field) = flow_field(line, "field") else {
            return Err(CatalogError {
                reason: "corpus_role_signal missing field",
            });
        };
        let Some(needle) = flow_field(line, "needle") else {
            return Err(CatalogError {
                reason: "corpus_role_signal missing needle",
            });
        };
        let rank = match flow_field(line, "rank") {
            Some(raw_rank) => raw_rank.parse::<u32>().map_err(|_| CatalogError {
                reason: "corpus_role_signal rank is not an integer",
            })?,
            None => {
                return Err(CatalogError {
                    reason: "corpus_role_signal missing rank",
                })
            }
        };
        if needle.is_empty() || (field != "path" && field != "title") {
            return Err(CatalogError {
                reason: "corpus_role_signal field or needle is invalid",
            });
        }
        signals.push(CorpusRoleSignal {
            role,
            field,
            needle,
            rank,
        });
    }
    Ok(signals)
}

// ─── document_groups parsing and validation ─────────────────────────────────

/// Lines of a top-level mapping section starting at `heading`, with original
/// indentation, until the next line at or above the heading indent.
fn section_lines<'a>(text: &'a str, heading: &str) -> Option<Vec<(&'a str, usize)>> {
    let mut found = false;
    let mut heading_indent = 0usize;
    let mut out = Vec::new();
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if !found {
            if trimmed.trim() == heading {
                found = true;
                heading_indent = indent;
            }
            continue;
        }
        if indent <= heading_indent {
            break;
        }
        out.push((raw, indent));
    }
    found.then_some(out)
}

/// Collect `- item` lines under a sub-heading (lines deeper than
/// `heading_indent`); returns items and the index after the list.
fn dash_list(lines: &[(&str, usize)], start: usize, heading_indent: usize) -> (Vec<String>, usize) {
    let mut items = Vec::new();
    let mut index = start;
    while index < lines.len() {
        let (raw, indent) = lines[index];
        if indent <= heading_indent {
            break;
        }
        let trimmed = raw.trim();
        if let Some(item) = trimmed.strip_prefix("- ") {
            items.push(item.trim().trim_matches('"').trim().to_owned());
        }
        index += 1;
    }
    (items, index)
}

/// FNV-1a 64-bit hash of the raw `document_groups:` section lines (original
/// indentation preserved, blank lines skipped, section heading excluded),
/// hex-encoded as `fnv1a64-<16 lowercase hex>`.
///
/// Deterministic and language-portable: the harness Governor (T02) mirrors
/// this algorithm in Python to detect catalog drift — a parsed_as binding
/// carrying an older `catalog_version` is a visible warning, never a silent
/// skip. Absent section yields an empty string (fail-closed).
fn section_fnv1a64(text: &str, heading: &str) -> String {
    const OFFSET_BASIS: u64 = 0xcbf29ce484222325;
    const FNV_PRIME: u64 = 0x100000001b3;
    let Some(lines) = section_lines(text, heading) else {
        return String::new();
    };
    let mut hash = OFFSET_BASIS;
    for (raw, _) in lines {
        for byte in raw.as_bytes() {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(FNV_PRIME);
        }
        hash ^= u64::from(b'\n');
        hash = hash.wrapping_mul(FNV_PRIME);
    }
    format!("fnv1a64-{hash:016x}")
}

/// Hash of the `document_groups:` section in an arbitrary YAML text.
/// Exposed so tests can assert determinism and section sensitivity.
pub fn document_groups_section_hash(text: &str) -> String {
    section_fnv1a64(text, "document_groups:")
}

/// Current version of the embedded catalog's `document_groups:` section.
/// The parsed_as binding carries this value; drift vs the live file is a
/// visible Governor warning (T02), not a silent skip.
pub fn document_groups_version() -> String {
    document_groups_section_hash(EMBEDDED_ONTOLOGY_YAML)
}

/// Parse the top-level `document_groups:` section; absent section yields
/// empty defaults so legacy catalogs keep loading.
fn parse_document_groups(text: &str) -> Result<DocumentGroupsSection, CatalogError> {
    let Some(lines) = section_lines(text, "document_groups:") else {
        return Ok(DocumentGroupsSection::default());
    };
    let mut section = DocumentGroupsSection::default();
    let mut index = 0usize;
    while index < lines.len() {
        let (raw, indent) = lines[index];
        let trimmed = raw.trim();
        match trimmed {
            "structural_roles:" => {
                let (items, next) = dash_list(&lines, index + 1, indent);
                section.structural_roles = items;
                index = next;
            }
            "structural_only_tokens:" => {
                let (items, next) = dash_list(&lines, index + 1, indent);
                section.structural_only_tokens = items;
                index = next;
            }
            "non_claims:" => {
                let (items, next) = dash_list(&lines, index + 1, indent);
                section.non_claims = items;
                index = next;
            }
            "groups:" => {
                let (groups, next) = parse_groups(&lines, index + 1, indent)?;
                section.groups = groups;
                index = next;
            }
            _ => index += 1,
        }
    }
    Ok(section)
}

/// Parse the `groups:` list: each block starts with `- id:` at the same
/// indent and extends to the next `- id:` or the list end.
fn parse_groups(
    lines: &[(&str, usize)],
    start: usize,
    heading_indent: usize,
) -> Result<(Vec<DocumentGroup>, usize), CatalogError> {
    let mut groups = Vec::new();
    let mut index = start;
    while index < lines.len() {
        let (raw, indent) = lines[index];
        if indent <= heading_indent {
            break;
        }
        if !raw.trim().starts_with("- id:") {
            index += 1;
            continue;
        }
        let mut block: Vec<(&str, usize)> = Vec::new();
        block.push((raw, indent));
        let mut next = index + 1;
        while next < lines.len() {
            let (next_raw, next_indent) = lines[next];
            if next_indent <= heading_indent {
                break;
            }
            if next_indent == indent && next_raw.trim().starts_with("- id:") {
                break;
            }
            block.push((next_raw, next_indent));
            next += 1;
        }
        groups.push(parse_group_block(&block)?);
        index = next;
    }
    Ok((groups, index))
}

/// Parse one `- id:` block: scalar fields plus the optional `ladder:` list.
fn parse_group_block(block: &[(&str, usize)]) -> Result<DocumentGroup, CatalogError> {
    let mut id: Option<String> = None;
    let mut granularity: Option<String> = None;
    let mut text_boundary: Vec<String> = Vec::new();
    let mut max_depth: Option<u32> = None;
    let mut text_only = false;
    let mut needles: Vec<GroupNeedle> = Vec::new();
    let mut ladder: Vec<LadderEntry> = Vec::new();
    let mut in_needles = false;
    let mut needles_indent = 0usize;
    let mut in_ladder = false;
    let mut ladder_indent = 0usize;
    for (raw, indent) in block {
        let trimmed = raw.trim();
        if in_needles {
            if *indent <= needles_indent {
                in_needles = false;
            } else if let Some(flow) = trimmed.strip_prefix("- ") {
                needles.push(parse_group_needle(flow)?);
                continue;
            } else {
                continue;
            }
        }
        if in_ladder {
            if *indent <= ladder_indent {
                in_ladder = false;
            } else if let Some(flow) = trimmed.strip_prefix("- ") {
                ladder.push(parse_ladder_entry(flow)?);
                continue;
            } else {
                continue;
            }
        }
        if let Some(rest) = trimmed.strip_prefix("- id:") {
            id = Some(rest.trim().to_owned());
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("granularity:") {
            granularity = Some(rest.trim().to_owned());
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("text_boundary:") {
            text_boundary = parse_inline_list(rest)?;
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("max_depth:") {
            max_depth = Some(rest.trim().parse::<u32>().map_err(|_| CatalogError {
                reason: "document group max_depth is not an integer",
            })?);
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("text_only:") {
            text_only = rest.trim() == "true";
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("needles:") {
            let rest = rest.trim();
            if rest.is_empty() {
                in_needles = true;
                needles_indent = *indent;
            } else {
                let items = parse_inline_list(rest)?;
                if !items.is_empty() {
                    return Err(CatalogError {
                        reason: "inline needles list must be empty",
                    });
                }
                needles = Vec::new();
            }
            continue;
        }
        if let Some(rest) = trimmed.strip_prefix("ladder:") {
            let rest = rest.trim();
            if rest.is_empty() {
                in_ladder = true;
                ladder_indent = *indent;
            } else {
                let items = parse_inline_list(rest)?;
                if !items.is_empty() {
                    return Err(CatalogError {
                        reason: "inline ladder list must be empty",
                    });
                }
                ladder = Vec::new();
            }
            continue;
        }
    }
    let id = id.ok_or(CatalogError {
        reason: "document group missing id",
    })?;
    Ok(DocumentGroup {
        id,
        granularity,
        text_boundary,
        max_depth,
        text_only,
        needles,
        ladder,
    })
}

/// Parse one flow-style group needle entry: `{field: X, needle: Y, rank: N}`.
fn parse_group_needle(flow: &str) -> Result<GroupNeedle, CatalogError> {
    let field = flow_field(flow, "field").ok_or(CatalogError {
        reason: "group needle missing field",
    })?;
    let needle = flow_field(flow, "needle").ok_or(CatalogError {
        reason: "group needle missing needle",
    })?;
    let rank = match flow_field(flow, "rank") {
        Some(raw) => raw.parse::<u32>().map_err(|_| CatalogError {
            reason: "group needle rank is not an integer",
        })?,
        None => {
            return Err(CatalogError {
                reason: "group needle missing rank",
            })
        }
    };
    if needle.is_empty() {
        return Err(CatalogError {
            reason: "group needle is empty",
        });
    }
    Ok(GroupNeedle {
        field,
        needle,
        rank,
    })
}

/// Parse one flow-style ladder entry: `{token: X, role: Y, ...}`.
fn parse_ladder_entry(flow: &str) -> Result<LadderEntry, CatalogError> {
    let token = flow_field(flow, "token").ok_or(CatalogError {
        reason: "ladder entry missing token",
    })?;
    let role = flow_field(flow, "role").ok_or(CatalogError {
        reason: "ladder entry missing role",
    })?;
    let recursive = flow.contains("recursive: true");
    let max_depth = match flow_field(flow, "max_depth") {
        Some(value) => Some(value.parse::<u32>().map_err(|_| CatalogError {
            reason: "ladder entry max_depth is not an integer",
        })?),
        None => None,
    };
    let compound = flow_field(flow, "compound").map(|value| value == "true");
    let suffix = flow_field(flow, "suffix");
    let number_style = flow_field(flow, "number_style");
    let surface = flow_field(flow, "surface");
    Ok(LadderEntry {
        token,
        role,
        recursive,
        max_depth,
        compound,
        suffix,
        number_style,
        surface,
    })
}

/// Parse an inline YAML list `[a, b, c]` into items.
fn parse_inline_list(raw: &str) -> Result<Vec<String>, CatalogError> {
    let body = raw
        .trim()
        .strip_prefix('[')
        .and_then(|value| value.strip_suffix(']'))
        .ok_or(CatalogError {
            reason: "inline list expected",
        })?;
    let mut items = Vec::new();
    for part in body.split(',') {
        let item = part.trim();
        if !item.is_empty() {
            items.push(item.to_owned());
        }
    }
    Ok(items)
}

/// Fail-closed validation of the parsed `document_groups:` section.
///
/// - ladder roles must come from the closed `structural_roles` vocabulary;
/// - ladder tokens must be decode tokens (`decode_level_aliases` keys,
///   case-insensitive) or declared structural-only tokens;
/// - granularity must be a decode token; `text_boundary` items must be roles;
/// - recursive entries require `max_depth`; suffixes and number styles are
///   bounded; group ids are unique.
fn validate_document_groups(
    section: &DocumentGroupsSection,
    decode_level_aliases: &[(String, String)],
) -> Result<(), CatalogError> {
    let decode_tokens: Vec<&str> = decode_level_aliases
        .iter()
        .map(|(key, _)| key.as_str())
        .collect();
    if !section.groups.is_empty() && section.structural_roles.is_empty() {
        return Err(CatalogError {
            reason: "document_groups requires structural_roles",
        });
    }
    let mut seen_ids: Vec<&str> = Vec::new();
    for group in &section.groups {
        if group.id.is_empty() {
            return Err(CatalogError {
                reason: "document group id is empty",
            });
        }
        if seen_ids.contains(&group.id.as_str()) {
            return Err(CatalogError {
                reason: "duplicate document group id",
            });
        }
        seen_ids.push(&group.id);
        for entry in &group.ladder {
            if !section
                .structural_roles
                .iter()
                .any(|role| role == &entry.role)
            {
                return Err(CatalogError {
                    reason: "ladder entry names an unknown structural role",
                });
            }
            let token_known = section
                .structural_only_tokens
                .iter()
                .any(|token| token == &entry.token)
                || decode_tokens
                    .iter()
                    .any(|token| token.eq_ignore_ascii_case(&entry.token));
            if !token_known {
                return Err(CatalogError {
                    reason: "ladder token is outside the decode-token catalog",
                });
            }
            let is_structural_only = section
                .structural_only_tokens
                .iter()
                .any(|token| token == &entry.token);
            let is_decode_token = decode_tokens
                .iter()
                .any(|token| token.eq_ignore_ascii_case(&entry.token));
            // Structural-only tokens (no decode HierarchyLevel, R8-09) must
            // declare a surface: the collector can only recognize them by
            // surface prefix. Decode-level tokens must NOT declare one:
            // extract_hierarchy already recognizes them and a surface would
            // shadow the marker (fail-closed schema).
            if is_structural_only && entry.surface.is_none() {
                return Err(CatalogError {
                    reason: "structural-only ladder token must declare surface",
                });
            }
            if is_decode_token && entry.surface.is_some() {
                return Err(CatalogError {
                    reason: "decode-level ladder token must not declare surface",
                });
            }
            if entry
                .surface
                .as_ref()
                .is_some_and(|surface| surface.is_empty())
            {
                return Err(CatalogError {
                    reason: "ladder entry surface is empty",
                });
            }
            if entry.recursive && entry.max_depth.is_none() {
                return Err(CatalogError {
                    reason: "recursive ladder entry requires max_depth",
                });
            }
            if let Some(suffix) = &entry.suffix {
                if suffix != "." && suffix != ")" {
                    return Err(CatalogError {
                        reason: "ladder entry suffix is invalid",
                    });
                }
            }
            if let Some(style) = &entry.number_style {
                if !matches!(
                    style.as_str(),
                    "digit" | "letter_cyrillic" | "roman_or_digit"
                ) {
                    return Err(CatalogError {
                        reason: "ladder entry number_style is invalid",
                    });
                }
            }
        }
        for needle in &group.needles {
            if !matches!(needle.field.as_str(), "kind" | "type" | "path") {
                return Err(CatalogError {
                    reason: "group needle field is invalid",
                });
            }
            if needle.needle.is_empty() {
                return Err(CatalogError {
                    reason: "group needle is empty",
                });
            }
        }
        if let Some(granularity) = &group.granularity {
            let known = decode_tokens
                .iter()
                .any(|token| token.eq_ignore_ascii_case(granularity));
            if !known {
                return Err(CatalogError {
                    reason: "document group granularity is not a decode token",
                });
            }
        }
        for role in &group.text_boundary {
            if !section
                .structural_roles
                .iter()
                .any(|declared| declared == role)
            {
                return Err(CatalogError {
                    reason: "text_boundary names an unknown structural role",
                });
            }
        }
        // A structural group must declare a unit role: without one the
        // two-factor probe (T02) can never confirm structure and the group
        // would be permanently Unknown — a degenerate catalog entry.
        let has_unit = group.ladder.iter().any(|entry| entry.role == "unit");
        if !group.text_only && !has_unit {
            return Err(CatalogError {
                reason: "structural group requires a unit role",
            });
        }
    }
    Ok(())
}

/// Ranked group selection from kind/type/path needles (factor A of T02).
/// Mirrors `classify_corpus_role`: lower rank wins; same-rank different
/// groups is Conflict. Unknown when no needle matches.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DocumentGroupOutcome {
    Bound { group: String, needle: String },
    Unknown,
    Conflict { groups: Vec<String> },
}

impl OntologyCatalog {
    pub fn classify_document_group(
        &self,
        path: Option<&str>,
        kind: Option<&str>,
        doc_type: Option<&str>,
    ) -> DocumentGroupOutcome {
        let path_lc = path.map(str::to_lowercase);
        let kind_lc = kind.map(str::to_lowercase);
        let type_lc = doc_type.map(str::to_lowercase);
        let mut best_rank: Option<u32> = None;
        let mut best_groups: Vec<String> = Vec::new();
        let mut best_needle: Option<String> = None;
        for group in &self.document_groups {
            for needle in &group.needles {
                let haystack = match needle.field.as_str() {
                    "path" => path_lc.as_deref(),
                    "kind" => kind_lc.as_deref(),
                    "type" => type_lc.as_deref(),
                    _ => None,
                };
                let Some(haystack) = haystack else { continue };
                if !haystack.contains(&needle.needle.to_lowercase()) {
                    continue;
                }
                match best_rank {
                    None => {
                        best_rank = Some(needle.rank);
                        best_groups = vec![group.id.clone()];
                        best_needle = Some(needle.needle.clone());
                    }
                    Some(rank) if needle.rank < rank => {
                        best_rank = Some(needle.rank);
                        best_groups = vec![group.id.clone()];
                        best_needle = Some(needle.needle.clone());
                    }
                    Some(rank)
                        if needle.rank == rank
                            && !best_groups.iter().any(|item| item == &group.id) =>
                    {
                        best_groups.push(group.id.clone());
                    }
                    _ => {}
                }
            }
        }
        match best_groups.as_slice() {
            [] => DocumentGroupOutcome::Unknown,
            [group] => DocumentGroupOutcome::Bound {
                group: group.clone(),
                needle: best_needle.unwrap_or_default(),
            },
            _ => {
                let mut groups = best_groups.clone();
                groups.sort();
                DocumentGroupOutcome::Conflict { groups }
            }
        }
    }
}

/// Classify a provider file from path/title needles. Unknown if no signal matches.
/// Same-rank different roles is Conflict. Lower rank wins (more specific).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CorpusRoleOutcome {
    Bound { role: String },
    Unknown,
    Conflict { roles: Vec<String> },
}

impl OntologyCatalog {
    pub fn classify_corpus_role(&self, path: &str, title: &str) -> CorpusRoleOutcome {
        let path_lc = path.to_lowercase();
        let title_lc = title.to_lowercase();
        let mut best_rank: Option<u32> = None;
        let mut best_roles: Vec<String> = Vec::new();
        for signal in &self.corpus_role_signals {
            let haystack = match signal.field.as_str() {
                "path" => path_lc.as_str(),
                "title" => title_lc.as_str(),
                _ => continue,
            };
            if !haystack.contains(&signal.needle.to_lowercase()) {
                continue;
            }
            match best_rank {
                None => {
                    best_rank = Some(signal.rank);
                    best_roles = vec![signal.role.clone()];
                }
                Some(rank) if signal.rank < rank => {
                    best_rank = Some(signal.rank);
                    best_roles = vec![signal.role.clone()];
                }
                Some(rank)
                    if signal.rank == rank && !best_roles.iter().any(|r| r == &signal.role) =>
                {
                    best_roles.push(signal.role.clone());
                }
                _ => {}
            }
        }
        match best_roles.as_slice() {
            [] => CorpusRoleOutcome::Unknown,
            [role] => CorpusRoleOutcome::Bound { role: role.clone() },
            _ => {
                best_roles.sort();
                CorpusRoleOutcome::Conflict { roles: best_roles }
            }
        }
    }
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
        assert!(catalog.allows_transition("O2_decode_prefixes", "O2_calendar_ordinal"));
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
        assert!(catalog
            .corpus_roles
            .iter()
            .any(|role| role == "C2_edition_oracle"));
        assert!(!catalog.corpus_role_signals.is_empty());
        assert_eq!(catalog.hierarchy_level_rank("razdel"), Some(0));
        assert_eq!(catalog.hierarchy_level_rank("statya"), Some(3));
        assert_eq!(catalog.hierarchy_level_rank("Article"), None);
        // R8-13 recursive rank = (role order, depth); flat depth is 1.
        assert_eq!(catalog.hierarchy_level_rank("punkt"), Some(5));
        assert_eq!(catalog.propose_rank("punkt", 1), Some((5, 1)));
        assert_eq!(catalog.propose_rank("punkt", 2), Some((5, 2)));
        assert_eq!(catalog.propose_rank("statya", 1), Some((3, 1)));
        assert_eq!(catalog.propose_rank("Article", 1), None);
    }
}
