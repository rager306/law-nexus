//! Explicit fixture bindings. Not legal identity and not a membership log.

use crate::catalog::{flow_field, strip_comment, CatalogError};
use crate::domain::{HierarchyBinding, HierarchyMap, WriteSetError};
use ln_temporal::domain::ComponentConceptId;

pub const EMBEDDED_HIERARCHY_REGISTRY_YAML: &str =
    include_str!("../../../prd/architecture/kb-hierarchy-registry.yaml");

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HierarchyRegistryBinding {
    pub path_needle: String,
    pub level: String,
    pub number: String,
    pub cc: String,
}

pub fn parse_hierarchy_registry(text: &str) -> Result<Vec<HierarchyRegistryBinding>, CatalogError> {
    let mut bindings = Vec::new();
    let mut in_list = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == "bindings:" {
            in_list = true;
            heading_indent = indent;
            continue;
        }
        if in_list && indent <= heading_indent && !trimmed.trim().starts_with('-') {
            break;
        }
        if !in_list || !trimmed.trim().starts_with('-') {
            continue;
        }
        let line = trimmed.trim();
        let path_needle = flow_field(line, "path_needle")
            .ok_or_else(|| CatalogError::new("hierarchy binding missing path_needle"))?;
        let level = flow_field(line, "level")
            .ok_or_else(|| CatalogError::new("hierarchy binding missing level"))?;
        let number = flow_field(line, "number")
            .ok_or_else(|| CatalogError::new("hierarchy binding missing number"))?;
        let cc = flow_field(line, "cc")
            .ok_or_else(|| CatalogError::new("hierarchy binding missing cc"))?;
        if path_needle.is_empty() || level.is_empty() || number.is_empty() || cc.is_empty() {
            return Err(CatalogError::new("hierarchy binding has an empty field"));
        }
        bindings.push(HierarchyRegistryBinding {
            path_needle,
            level,
            number,
            cc,
        });
    }
    Ok(bindings)
}

pub fn bindings_matching_path<'a>(
    bindings: &'a [HierarchyRegistryBinding],
    path: &str,
) -> Vec<&'a HierarchyRegistryBinding> {
    let path_lc = path.to_lowercase();
    bindings
        .iter()
        .filter(|binding| path_lc.contains(&binding.path_needle.to_lowercase()))
        .collect()
}

/// Load the embedded registry subset whose path_needle matches `path`.
/// Unmatched paths stay empty (all markers Unknown).
pub fn load_hierarchy_map_for_path(path: &str) -> Result<HierarchyMap, WriteSetError> {
    let parsed = parse_hierarchy_registry(EMBEDDED_HIERARCHY_REGISTRY_YAML)
        .map_err(|_| WriteSetError::MissingIdentity)?;
    let mut map = HierarchyMap::empty();
    for binding in bindings_matching_path(&parsed, path) {
        let component =
            ComponentConceptId::parse(&binding.cc).map_err(|_| WriteSetError::MissingIdentity)?;
        map.register(HierarchyBinding::try_new(
            None,
            &binding.level,
            &binding.number,
            component,
        )?)?;
    }
    Ok(map)
}

pub fn embedded_binding_count_for_path(path: &str) -> Result<usize, CatalogError> {
    let parsed = parse_hierarchy_registry(EMBEDDED_HIERARCHY_REGISTRY_YAML)?;
    Ok(bindings_matching_path(&parsed, path).len())
}

/// Load the civil-day ordinal for the edition matching `path`.
/// Returns None if no edition is registered or the date is invalid.
pub fn load_edition_day_for_path(path: &str) -> Option<i64> {
    let iso = edition_date_for_path(path)?;
    ln_temporal::calendar::legal_act_effect_day_to_ordinal(&iso).ok()
}

fn edition_date_for_path(path: &str) -> Option<String> {
    if let Some(date) = edition_date_from_table(path) {
        return Some(date);
    }
    // Filename grounding: rev-DATE per edition; rev-initial uses enactment.
    let (enactment_date, act_number) = parse_law_dir(path)?;
    let entry = works_entry_for_act(&act_number)?;
    if entry.enactment_date != enactment_date {
        return None;
    }
    parse_edition_rev(path).or(Some(enactment_date))
}

fn edition_date_from_table(path: &str) -> Option<String> {
    let text = EMBEDDED_HIERARCHY_REGISTRY_YAML;
    let edition_start = text.find("\neditions:")?;
    let slice = &text[edition_start..];
    let works_start = slice.find("\nworks:");
    let slice = works_start.map(|i| &slice[..i]).unwrap_or(slice);
    let path_lc = path.to_lowercase();
    for raw in slice.lines() {
        let trimmed = strip_comment(raw);
        if !trimmed.trim().starts_with('-') {
            continue;
        }
        let needle = flow_field(trimmed.trim(), "path_needle")?;
        if path_lc.contains(&needle.to_lowercase()) {
            return flow_field(trimmed.trim(), "edition_date");
        }
    }
    None
}

/// One `works:` entry used for filename-grounded identity minting.
struct WorkEntry {
    authority: String,
    enactment_date: String,
}

/// Parse `law_YYYY-MM-DD_N-fz` from a consru_export path.
/// Returns (enactment_date, act_number). Bounded: only the `law_` prefix
/// (federal laws exported under exports/npa) is recognized; other act
/// families fail closed and need their own `works:` needle.
fn parse_law_dir(path: &str) -> Option<(String, String)> {
    let marker = "law_";
    let bytes = path.as_bytes();
    let mut from = 0usize;
    while let Some(rel) = path[from..].find(marker) {
        let start = from + rel + marker.len();
        // YYYY-MM-DD
        if bytes.len() < start + 10 {
            return None;
        }
        let date = &path[start..start + 10];
        if !is_iso_day_ascii(date) {
            from = start;
            continue;
        }
        // _N-fz until '/', '_' or end
        if bytes.get(start + 10) != Some(&b'_') {
            from = start;
            continue;
        }
        let number_start = start + 11;
        let number_end = path[number_start..]
            .find(['/', '_'])
            .map(|i| number_start + i)
            .unwrap_or(path.len());
        let act = &path[number_start..number_end];
        if !act.ends_with("-fz") || act.len() <= 3 {
            from = start;
            continue;
        }
        return Some((date.to_owned(), act.to_owned()));
    }
    None
}

fn is_iso_day_ascii(candidate: &str) -> bool {
    let b = candidate.as_bytes();
    b.len() == 10
        && b[..4].iter().all(u8::is_ascii_digit)
        && b[4] == b'-'
        && b[5..7].iter().all(u8::is_ascii_digit)
        && b[7] == b'-'
        && b[8..].iter().all(u8::is_ascii_digit)
}

/// Parse the edition date from `edition-XXXX_rev-YYYY-MM-DD` in a path.
/// `rev-initial` returns None: the seed edition uses the enactment day.
fn parse_edition_rev(path: &str) -> Option<String> {
    let marker = "rev-";
    let bytes = path.as_bytes();
    let mut from = 0usize;
    while let Some(rel) = path[from..].find(marker) {
        let start = from + rel + marker.len();
        if bytes.len() < start + 10 {
            return None;
        }
        let date = &path[start..start + 10];
        if !is_iso_day_ascii(date) {
            from = start;
            continue;
        }
        // must be terminated by '_', '/' or end (not a longer token)
        let terminator = bytes.get(start + 10).copied();
        if let Some(c) = terminator {
            if c != b'_' && c != b'/' {
                from = start;
                continue;
            }
        }
        return Some(date.to_owned());
    }
    None
}

/// Ground identity from a consru_export edition path.
/// Authority comes from the `works:` table (act_number lookup); the filename
/// enactment date must match the table (fail-closed). Unknown acts fail
/// closed rather than inventing an authority.
fn expression_id_from_edition_path(path: &str) -> Option<String> {
    let (enactment_date, act_number) = parse_law_dir(path)?;
    let entry = works_entry_for_act(&act_number)?;
    if entry.enactment_date != enactment_date {
        return None;
    }
    let edition_date = parse_edition_rev(path).unwrap_or(enactment_date.clone());
    let work =
        ln_identity::domain::mint_work(&entry.authority, &enactment_date, &act_number).ok()?;
    let expression = ln_identity::domain::mint_expression(&work, &edition_date).ok()?;
    Some(expression.expression_id.as_str().to_owned())
}

fn works_entry_for_act(act_number: &str) -> Option<WorkEntry> {
    let text = EMBEDDED_HIERARCHY_REGISTRY_YAML;
    let works_start = text.find("\nworks:")?;
    let slice = &text[works_start..];
    for raw in slice.lines() {
        let trimmed = strip_comment(raw);
        let line = trimmed.trim();
        if !line.starts_with('-') {
            continue;
        }
        let number = flow_field(line, "act_number")?;
        if number != act_number {
            continue;
        }
        return Some(WorkEntry {
            authority: flow_field(line, "authority")?,
            enactment_date: flow_field(line, "enactment_date")?,
        });
    }
    None
}

/// Mint a Work + Expression for the fixture matching `path`.
/// Returns the Expression ID string for use as provenance.
/// Order: `works:` needle match (fixture paths), then consru_export edition
/// filename grounding (`law_DATE_N-fz` + `edition-XXXX_rev-DATE`).
/// Falls back to None if neither grounds (fail-closed).
pub fn load_expression_id_for_path(path: &str) -> Option<String> {
    let text = EMBEDDED_HIERARCHY_REGISTRY_YAML;
    let works_start = text.find("\nworks:")?;
    let slice = &text[works_start..];
    let path_lc = path.to_lowercase();
    for raw in slice.lines() {
        let trimmed = strip_comment(raw);
        if !trimmed.trim().starts_with('-') {
            continue;
        }
        let line = trimmed.trim();
        let needle = flow_field(line, "path_needle")?;
        if !path_lc.contains(&needle.to_lowercase()) {
            continue;
        }
        let authority = flow_field(line, "authority")?;
        let enactment_date = flow_field(line, "enactment_date")?;
        let act_number = flow_field(line, "act_number")?;
        let edition_date = flow_field(line, "edition_date")?;
        let work = ln_identity::domain::mint_work(&authority, &enactment_date, &act_number).ok()?;
        let expression = ln_identity::domain::mint_expression(&work, &edition_date).ok()?;
        return Some(expression.expression_id.as_str().to_owned());
    }
    // No needle matched: try consru_export edition filename grounding.
    expression_id_from_edition_path(path)
}
