//! Two-factor document group detection (M171 S01 T02).
//!
//! Factor A (metadata): ranked `kind` / `type` / `path` needles from the
//! `document_groups` catalog section, with `classify_corpus_role`-style
//! ranking (lower rank wins; same-rank different groups is Conflict).
//! Factor B (structural probe): decoded blocks are probed for the candidate
//! group's unit markers — statya prefix markers for law/code, numbered
//! punkt markers (group-specific suffix style, R8-04) for resolutions and
//! orders. Both factors must agree; any conflict, missing metadata, or
//! absent structure is Unknown (fail-closed, never guess).
//!
//! Text-only profiles (court_practice) declare no structure: numbered lists
//! are never structure for them, so a FAS decision with depth-4 numbering
//! does not produce a structural group (R8-05 hostile case).
//!
//! Non-claim: group detection is a `system_observation` heuristic, never
//! legal classification; practice is not an AST (ADR-0020). Determinism is
//! mandatory: the outcome is a pure function of (metadata, blocks) — no
//! randomness, no wall clock, no iteration-order dependence.

use crate::domain::{HierarchyLevel, ParagraphStyle, ParsedBlock};
use crate::prefix_catalog::{DecodePrefixCatalog, NumberStyle, SpacePolicy};

pub const EMBEDDED_ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

/// One ranked metadata needle of a document group (factor A).
/// `field` is one of `kind` / `type` / `path`; lower `rank` wins.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GroupNeedle {
    pub field: String,
    pub needle: String,
    pub rank: u32,
}

/// One ladder entry of a document structural profile: token + role + style.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LadderEntry {
    pub token: String,
    pub role: String,
    pub recursive: bool,
    pub max_depth: Option<u32>,
    pub compound: Option<bool>,
    pub suffix: Option<String>,
    pub number_style: Option<String>,
    /// Surface marker text for structural-only tokens (tokens outside the
    /// decode `HierarchyLevel` set, e.g. primechanie -> "Примечание"). The
    /// collector recognizes these markers by surface prefix because
    /// `extract_hierarchy` has no level for them (R8-09). Decode-level
    /// tokens must not declare a surface (the catalog validator enforces).
    pub surface: Option<String>,
}

/// A document structural profile (system_observation heuristic).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GroupProfile {
    pub id: String,
    pub text_only: bool,
    pub ladder: Vec<LadderEntry>,
    pub needles: Vec<GroupNeedle>,
}

/// Embedded `document_groups` section plus the decode prefix catalog used by
/// the structural probe (same YAML file, same crate — no cross-crate dep).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StructuralProfile {
    pub non_claims: Vec<String>,
    pub groups: Vec<GroupProfile>,
    prefixes: DecodePrefixCatalog,
}

impl StructuralProfile {
    pub fn embedded() -> Result<Self, &'static str> {
        Self::parse_yaml(EMBEDDED_ONTOLOGY_YAML)
    }

    pub fn parse_yaml(text: &str) -> Result<Self, &'static str> {
        let prefixes = DecodePrefixCatalog::parse_yaml(text)?;
        let (non_claims, groups) = parse_document_groups_section(text)?;
        Ok(Self {
            non_claims,
            groups,
            prefixes,
        })
    }

    pub fn group(&self, id: &str) -> Option<&GroupProfile> {
        self.groups.iter().find(|group| group.id == id)
    }
}

/// Factor A outcome: ranked needle selection.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MetadataOutcome {
    Bound { group: String, needle: String },
    Unknown,
    Conflict { groups: Vec<String> },
}

/// Factor B outcome: unit-marker probe over decoded blocks.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProbeVerdict {
    /// Blocks contain markers matching the candidate group's unit style.
    StructureFound {
        unit_token: String,
        marker_count: usize,
    },
    /// No unit markers found (or the profile declares none — text-only).
    NoStructure,
}

/// Which factor(s) produced a Bound outcome (observability for inspect).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DetectionFactor {
    /// Factor A alone: text-only profile — numbered lists are never
    /// structure (R8-05), so the probe adds no confirmatory signal.
    Needle,
    /// Both factors agreed: metadata needle + structural probe.
    NeedleAndProbe,
}

/// Why detection ended in Unknown (fail-closed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UnknownReason {
    /// No metadata needle matched (no data).
    NoMetadata,
    /// Metadata bound a structural group but the probe found no unit
    /// markers (conflict — do not guess).
    ProbeConflict { metadata_group: String },
}

/// Deterministic two-factor detection outcome.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GroupDetection {
    Bound {
        group: String,
        factor: DetectionFactor,
    },
    Unknown {
        reason: UnknownReason,
    },
    Conflict {
        groups: Vec<String>,
    },
}

impl StructuralProfile {
    /// Factor A: rank kind/type/path needles across all groups.
    pub fn detect_metadata(
        &self,
        path: Option<&str>,
        kind: Option<&str>,
        doc_type: Option<&str>,
    ) -> MetadataOutcome {
        let path_lc = path.map(str::to_lowercase);
        let kind_lc = kind.map(str::to_lowercase);
        let type_lc = doc_type.map(str::to_lowercase);
        let mut best_rank: Option<u32> = None;
        let mut best_groups: Vec<String> = Vec::new();
        let mut best_needle: Option<String> = None;
        for group in &self.groups {
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
            [] => MetadataOutcome::Unknown,
            [group] => MetadataOutcome::Bound {
                group: group.clone(),
                needle: best_needle.unwrap_or_default(),
            },
            _ => {
                let mut groups = best_groups.clone();
                groups.sort();
                MetadataOutcome::Conflict { groups }
            }
        }
    }

    /// Factor B: probe blocks against the candidate group's unit style.
    ///
    /// Text-only profiles declare no structure — the probe is trivially
    /// NoStructure, so numbered lists never produce a structural group
    /// (R8-05: FAS decisions with depth-4 numbering stay text-only).
    /// Unknown group ids fail closed to NoStructure.
    pub fn probe(&self, group_id: &str, blocks: &[ParsedBlock]) -> ProbeVerdict {
        let Some(group) = self.group(group_id) else {
            return ProbeVerdict::NoStructure;
        };
        if group.text_only {
            return ProbeVerdict::NoStructure;
        }
        let unit_entries: Vec<&LadderEntry> = group
            .ladder
            .iter()
            .filter(|entry| entry.role == "unit")
            .collect();
        if unit_entries.is_empty() {
            return ProbeVerdict::NoStructure;
        }
        // Deterministic: ladder order is catalog order.
        let mut total = 0usize;
        let mut unit_token = String::new();
        for entry in unit_entries {
            let count = blocks
                .iter()
                .filter(|block| self.block_matches_unit(block, entry))
                .count();
            if count > 0 {
                total += count;
                if unit_token.is_empty() {
                    unit_token = entry.token.clone();
                }
            }
        }
        if total > 0 {
            ProbeVerdict::StructureFound {
                unit_token,
                marker_count: total,
            }
        } else {
            ProbeVerdict::NoStructure
        }
    }

    /// Two-factor detection: both factors must agree.
    pub fn detect(
        &self,
        path: Option<&str>,
        kind: Option<&str>,
        doc_type: Option<&str>,
        blocks: &[ParsedBlock],
    ) -> GroupDetection {
        match self.detect_metadata(path, kind, doc_type) {
            MetadataOutcome::Unknown => GroupDetection::Unknown {
                reason: UnknownReason::NoMetadata,
            },
            MetadataOutcome::Conflict { groups } => GroupDetection::Conflict { groups },
            MetadataOutcome::Bound { group, .. } => {
                let text_only = self.group(&group).is_some_and(|profile| profile.text_only);
                if text_only {
                    // Text-only profile: the needle binds directly; the probe
                    // confirms nothing because the profile declares no
                    // structure (numbered lists are not structure, R8-05).
                    return GroupDetection::Bound {
                        group,
                        factor: DetectionFactor::Needle,
                    };
                }
                match self.probe(&group, blocks) {
                    ProbeVerdict::StructureFound { .. } => GroupDetection::Bound {
                        group,
                        factor: DetectionFactor::NeedleAndProbe,
                    },
                    ProbeVerdict::NoStructure => GroupDetection::Unknown {
                        reason: UnknownReason::ProbeConflict {
                            metadata_group: group,
                        },
                    },
                }
            }
        }
    }

    /// Does one block start with a marker matching the entry's unit style?
    fn block_matches_unit(&self, block: &ParsedBlock, entry: &LadderEntry) -> bool {
        if block.style() == ParagraphStyle::ProviderComment {
            return false;
        }
        let text = block.text().trim_start();
        if text.is_empty() {
            return false;
        }
        if let Some(level) = level_from_ladder_token(&entry.token) {
            if self.has_prefix_markers(level) {
                return self.prefix_match(text, level);
            }
        }
        Self::numbered_match(text, entry)
    }

    fn has_prefix_markers(&self, level: HierarchyLevel) -> bool {
        self.prefixes
            .prefixes
            .iter()
            .any(|rule| rule.level == level)
    }

    /// Prefix-style unit marker: `Статья 1. ...` (decode_marker_prefixes +
    /// space policy + level number style).
    fn prefix_match(&self, text: &str, level: HierarchyLevel) -> bool {
        for rule in &self.prefixes.prefixes {
            if rule.level != level {
                continue;
            }
            let Some(rest) = text.strip_prefix(rule.marker.as_str()) else {
                continue;
            };
            let whitespace_bytes = rest
                .char_indices()
                .take_while(|(_, character)| character.is_whitespace())
                .map(|(index, character)| index + character.len_utf8())
                .last()
                .unwrap_or(0);
            let space_ok = match rule.space {
                SpacePolicy::Required => whitespace_bytes > 0,
                SpacePolicy::Optional => true,
            };
            if !space_ok {
                continue;
            }
            let after = &rest[whitespace_bytes..];
            if starts_with_number(after, level, &self.prefixes) {
                return true;
            }
        }
        false
    }

    /// Numbered-style unit marker: `1)` / `1.` / `а)` with the entry's
    /// suffix and number style (group-specific styles, R8-04). Compound
    /// dots are honored when the entry declares `compound: true` or is
    /// recursive (R8-03: ПП/orders reach compound depth 3–4).
    fn numbered_match(text: &str, entry: &LadderEntry) -> bool {
        entry.numbered_matches(text)
    }
}

impl LadderEntry {
    /// Does `text` start with this entry's declared numbered-marker style
    /// (suffix + number style + compound/recursive)? Shared by the group
    /// probe (`block_matches_unit`) and the article-body collector fallback
    /// (group number styles are authoritative, R8-04). Surface-only tokens
    /// (primechanie/prilozhenie) never match here — they are recognized by
    /// their surface prefix (R8-09).
    pub(crate) fn numbered_matches(&self, text: &str) -> bool {
        let Some(suffix) = self.suffix.as_deref() else {
            return false;
        };
        let style = self.number_style.as_deref().unwrap_or("digit");
        let allow_compound = self.compound == Some(true) || self.recursive;
        let bytes = text.as_bytes();
        let end = match style {
            "letter_cyrillic" => {
                let Some(first) = text.chars().next() else {
                    return false;
                };
                if !('а'..='я').contains(&first) {
                    return false;
                }
                first.len_utf8()
            }
            _ => {
                if !bytes.first().is_some_and(u8::is_ascii_digit) {
                    return false;
                }
                let mut end = 1;
                while end < bytes.len() {
                    let is_digit = bytes[end].is_ascii_digit();
                    let is_compound_dot = allow_compound
                        && bytes[end] == b'.'
                        && bytes.get(end + 1).is_some_and(u8::is_ascii_digit);
                    if is_digit || is_compound_dot {
                        end += 1;
                    } else {
                        break;
                    }
                }
                end
            }
        };
        text[end..].starts_with(suffix)
    }
}

impl GroupProfile {
    /// First ladder entry whose declared numbered-marker style matches
    /// `text`. Used by the article-body collector to reclassify decode-level
    /// markers that the group's ladder does not declare (e.g. PP "1." points
    /// decode as Chast but are punkt units for government_resolution — the
    /// group's dot style is authoritative, R8-04). Surface-only entries are
    /// skipped (they never match numbered styles, R8-09).
    pub(crate) fn style_match(&self, text: &str) -> Option<&LadderEntry> {
        self.ladder
            .iter()
            .find(|entry| entry.surface.is_none() && entry.numbered_matches(text))
    }
}

fn level_from_ladder_token(token: &str) -> Option<HierarchyLevel> {
    HierarchyLevel::all()
        .into_iter()
        .find(|level| level.as_str().eq_ignore_ascii_case(token))
}

fn starts_with_number(text: &str, level: HierarchyLevel, catalog: &DecodePrefixCatalog) -> bool {
    let Some(first) = text.chars().next() else {
        return false;
    };
    if first.is_ascii_digit() {
        return true;
    }
    if catalog.number_style(level) == Some(NumberStyle::RomanOrDigit)
        && matches!(
            first.to_ascii_uppercase(),
            'I' | 'V' | 'X' | 'L' | 'C' | 'D' | 'M'
        )
    {
        return true;
    }
    false
}

// ─── minimal YAML parsing (no dependency on ln-kb-ontology) ────────────────

fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => line[..index].trim_end(),
        None => line.trim_end(),
    }
}

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

/// Collect `- item` lines under a sub-heading; returns items and the next
/// index after the list.
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

fn parse_document_groups_section(
    text: &str,
) -> Result<(Vec<String>, Vec<GroupProfile>), &'static str> {
    let Some(lines) = section_lines(text, "document_groups:") else {
        return Ok((Vec::new(), Vec::new()));
    };
    let mut non_claims = Vec::new();
    let mut groups = Vec::new();
    let mut index = 0usize;
    while index < lines.len() {
        let (raw, indent) = lines[index];
        let trimmed = raw.trim();
        match trimmed {
            "non_claims:" => {
                let (items, next) = dash_list(&lines, index + 1, indent);
                non_claims = items;
                index = next;
            }
            "groups:" => {
                let (parsed, next) = parse_group_profiles(&lines, index + 1, indent)?;
                groups = parsed;
                index = next;
            }
            _ => index += 1,
        }
    }
    Ok((non_claims, groups))
}

/// Parse the `groups:` list: each block starts with `- id:` at the same
/// indent and extends to the next `- id:` or the list end.
fn parse_group_profiles(
    lines: &[(&str, usize)],
    start: usize,
    heading_indent: usize,
) -> Result<(Vec<GroupProfile>, usize), &'static str> {
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
        groups.push(parse_group_profile(&block)?);
        index = next;
    }
    Ok((groups, index))
}

fn parse_group_profile(block: &[(&str, usize)]) -> Result<GroupProfile, &'static str> {
    let mut id: Option<String> = None;
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
        if let Some(rest) = trimmed.strip_prefix("text_only:") {
            text_only = rest.trim() == "true";
            continue;
        }
        if trimmed == "needles:" {
            in_needles = true;
            needles_indent = *indent;
            continue;
        }
        if trimmed == "ladder:" {
            in_ladder = true;
            ladder_indent = *indent;
            continue;
        }
    }
    let id = id.ok_or("document group missing id")?;
    Ok(GroupProfile {
        id,
        text_only,
        ladder,
        needles,
    })
}

fn parse_group_needle(flow: &str) -> Result<GroupNeedle, &'static str> {
    let field = flow_field(flow, "field").ok_or("group needle missing field")?;
    let needle = flow_field(flow, "needle").ok_or("group needle missing needle")?;
    let rank = flow_field(flow, "rank")
        .ok_or("group needle missing rank")?
        .parse::<u32>()
        .map_err(|_| "group needle rank is not an integer")?;
    Ok(GroupNeedle {
        field,
        needle,
        rank,
    })
}

fn parse_ladder_entry(flow: &str) -> Result<LadderEntry, &'static str> {
    let token = flow_field(flow, "token").ok_or("ladder entry missing token")?;
    let role = flow_field(flow, "role").ok_or("ladder entry missing role")?;
    let recursive = flow.contains("recursive: true");
    let max_depth = match flow_field(flow, "max_depth") {
        Some(value) => Some(value.parse::<u32>().map_err(|_| "bad max_depth")?),
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

/// Extract a flow-style field value: `{field: value, ...}` (mirror of the
/// ontology catalog parser; ln-decode must not depend on ln-kb-ontology).
fn flow_field(line: &str, key: &str) -> Option<String> {
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedded_profile_loads_five_groups() {
        let profile = StructuralProfile::embedded().expect("yaml");
        let ids: Vec<&str> = profile
            .groups
            .iter()
            .map(|group| group.id.as_str())
            .collect();
        assert_eq!(
            ids,
            [
                "federal_law@v1",
                "code",
                "government_resolution",
                "departmental_order",
                "court_practice"
            ]
        );
    }

    #[test]
    fn embedded_profile_declares_non_claims() {
        let profile = StructuralProfile::embedded().expect("yaml");
        let joined = profile.non_claims.join("\n");
        assert!(
            joined.contains("system_observation"),
            "detection must be framed as a system_observation heuristic: {joined}"
        );
        assert!(
            joined.contains("not an AST"),
            "practice != AST must be declared (ADR-0020): {joined}"
        );
    }

    #[test]
    fn structural_only_surfaces_are_parsed() {
        // Parser-drift lock (mirror of document_groups_catalog): the ln-decode
        // parser must read `surface` exactly like ln-kb-ontology so the
        // collector can recognize primechanie/prilozhenie markers (R8-09).
        let profile = StructuralProfile::embedded().expect("yaml");
        let order = profile.group("departmental_order").expect("order");
        let primechanie = order
            .ladder
            .iter()
            .find(|entry| entry.token == "primechanie")
            .expect("primechanie");
        assert_eq!(primechanie.surface.as_deref(), Some("Примечание"));
        let prilozhenie = order
            .ladder
            .iter()
            .find(|entry| entry.token == "prilozhenie")
            .expect("prilozhenie");
        assert_eq!(prilozhenie.surface.as_deref(), Some("Приложение"));
    }
}
