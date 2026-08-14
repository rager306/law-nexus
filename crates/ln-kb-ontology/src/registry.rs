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
    let text = EMBEDDED_HIERARCHY_REGISTRY_YAML;
    let edition_start = text.find("\neditions:")?;
    let slice = &text[edition_start..];
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

/// Mint a Work + Expression for the fixture matching `path`.
/// Returns the Expression ID string for use as provenance.
/// Falls back to None if no `works:` entry matches.
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
    None
}
