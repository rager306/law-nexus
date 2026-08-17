//! Document structural profiles (`document_groups`) must stay covered by the
//! decode-token catalog of the same YAML file (M171 S01 T01).
//!
//! Mirror of `crates/ln-decode/tests/catalog_coverage.rs` for the ontology
//! side: the `document_groups` section is YAML data, not a Rust type, and it
//! must not drift outside the decode catalog sections (`decode_level_aliases`,
//! `decode_marker_prefixes`, `decode_numbered_markers`) or the closed
//! `structural_roles` vocabulary. The profiles are a system_observation
//! heuristic, never legal classification (ADR-0020).

use ln_kb_ontology::catalog::OntologyCatalog;

const YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

fn catalog() -> OntologyCatalog {
    OntologyCatalog::embedded().expect("embedded kb-ontology.yaml")
}

/// Keys of the `decode_level_aliases:` mapping (decode tokens, title case).
fn decode_tokens() -> Vec<String> {
    yaml_section_keys(YAML, "decode_level_aliases:")
}

#[test]
fn every_ladder_token_is_covered_by_the_decode_catalog() {
    let catalog = catalog();
    let tokens = decode_tokens();
    assert!(!tokens.is_empty(), "decode_level_aliases missing");
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            let covered = catalog
                .structural_only_tokens
                .iter()
                .any(|item| item == &entry.token)
                || tokens
                    .iter()
                    .any(|token| token.eq_ignore_ascii_case(&entry.token));
            assert!(
                covered,
                "group {} ladder token {} is outside the decode-token catalog",
                group.id, entry.token
            );
        }
    }
}

#[test]
fn every_granularity_is_covered_by_the_decode_catalog() {
    let catalog = catalog();
    let tokens = decode_tokens();
    for group in &catalog.document_groups {
        if let Some(granularity) = &group.granularity {
            assert!(
                tokens
                    .iter()
                    .any(|token| token.eq_ignore_ascii_case(granularity)),
                "group {} granularity {} is outside the decode-token catalog",
                group.id,
                granularity
            );
        }
    }
}

#[test]
fn every_used_role_is_a_declared_structural_role() {
    let catalog = catalog();
    assert!(!catalog.structural_roles.is_empty());
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            assert!(
                catalog.is_structural_role(&entry.role),
                "group {} ladder entry {} uses undeclared role {}",
                group.id,
                entry.token,
                entry.role
            );
        }
        for role in &group.text_boundary {
            assert!(
                catalog.is_structural_role(role),
                "group {} text_boundary uses undeclared role {}",
                group.id,
                role
            );
        }
    }
}

#[test]
fn recursive_ladder_entries_carry_max_depth() {
    let catalog = catalog();
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            assert!(
                !entry.recursive || entry.max_depth.is_some(),
                "group {} recursive entry {} lacks max_depth",
                group.id,
                entry.token
            );
        }
    }
}

#[test]
fn ladder_styles_stay_inside_the_closed_style_vocabulary() {
    let catalog = catalog();
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            if let Some(suffix) = &entry.suffix {
                assert!(
                    suffix == "." || suffix == ")",
                    "group {} entry {} has suffix outside {{'.', ')'}}: {suffix}",
                    group.id,
                    entry.token
                );
            }
            if let Some(style) = &entry.number_style {
                assert!(
                    matches!(
                        style.as_str(),
                        "digit" | "letter_cyrillic" | "roman_or_digit"
                    ),
                    "group {} entry {} has number_style outside the closed set: {style}",
                    group.id,
                    entry.token
                );
            }
        }
    }
}

#[test]
fn structural_only_tokens_do_not_collide_with_decode_tokens() {
    let catalog = catalog();
    let tokens = decode_tokens();
    for token in &catalog.structural_only_tokens {
        assert!(
            !tokens
                .iter()
                .any(|decode| decode.eq_ignore_ascii_case(token)),
            "structural-only token {token} collides with a decode token"
        );
    }
}

#[test]
fn federal_law_v1_prefixes_cover_exactly_the_decode_marker_prefixes() {
    let catalog = catalog();
    let fl = catalog
        .document_group("federal_law@v1")
        .expect("federal_law@v1 group");
    let mut profile_levels: Vec<String> = fl
        .ladder
        .iter()
        .filter(|entry| matches!(entry.role.as_str(), "unit" | "container"))
        .map(|entry| capitalize(&entry.token))
        .collect();
    profile_levels.sort();
    let mut prefix_keys = yaml_section_keys(YAML, "decode_marker_prefixes:");
    prefix_keys.sort();
    assert_eq!(
        profile_levels, prefix_keys,
        "federal_law@v1 unit+container levels must equal the current decode_marker_prefixes set"
    );
}

#[test]
fn federal_law_v1_styles_match_decode_numbered_markers() {
    let catalog = catalog();
    let fl = catalog
        .document_group("federal_law@v1")
        .expect("federal_law@v1 group");
    let rows = numbered_marker_rows(YAML);
    for entry in &fl.ladder {
        let Some((_, suffix, number_style, compound)) = rows
            .iter()
            .find(|(token, _, _, _)| token.eq_ignore_ascii_case(&entry.token))
        else {
            continue;
        };
        assert_eq!(
            entry.suffix.as_deref(),
            Some(suffix.as_str()),
            "federal_law@v1 {} suffix deviates from decode_numbered_markers",
            entry.token
        );
        assert_eq!(
            entry.number_style.as_deref(),
            Some(number_style.as_str()),
            "federal_law@v1 {} number_style deviates from decode_numbered_markers",
            entry.token
        );
        assert_eq!(
            entry.compound,
            Some(*compound),
            "federal_law@v1 {} compound deviates from decode_numbered_markers",
            entry.token
        );
    }
}

// ─── raw-YAML section helpers (mirror ln-decode/tests/catalog_coverage.rs) ──

/// Keys of a mapping section (heading matched on the trimmed line; the section
/// ends at the first line no deeper than the heading indent).
fn yaml_section_keys(text: &str, heading: &str) -> Vec<String> {
    let mut keys = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
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
            if let Some((key, _)) = trimmed.trim().split_once(':') {
                let key = key.trim();
                if !key.is_empty() && !key.starts_with('-') {
                    keys.push(key.to_owned());
                }
            }
        }
    }
    keys
}

/// (decode token, suffix, number_style, allow_compound) rows of
/// `decode_numbered_markers:`.
fn numbered_marker_rows(text: &str) -> Vec<(String, String, String, bool)> {
    let mut rows = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = strip_comment(raw);
        if trimmed.trim().is_empty() {
            continue;
        }
        let indent = raw.len() - raw.trim_start().len();
        if trimmed.trim() == "decode_numbered_markers:" {
            in_map = true;
            heading_indent = indent;
            continue;
        }
        if in_map && indent <= heading_indent {
            break;
        }
        if !in_map {
            continue;
        }
        let line = trimmed.trim();
        let Some((token, rest)) = line.split_once(':') else {
            continue;
        };
        let token = token.trim();
        if token.is_empty() {
            continue;
        }
        let number_style = if rest.contains("letter_cyrillic") {
            "letter_cyrillic"
        } else {
            "digit"
        };
        let suffix = rest
            .split("suffix:")
            .nth(1)
            .and_then(|part| {
                let part = part.trim();
                part.strip_prefix('"')
                    .and_then(|quoted| quoted.chars().next())
                    .or_else(|| part.chars().next())
            })
            .unwrap_or('.')
            .to_string();
        let compound = rest.contains("allow_compound: true");
        rows.push((token.to_owned(), suffix, number_style.to_owned(), compound));
    }
    rows
}

fn strip_comment(line: &str) -> &str {
    match line.find('#') {
        Some(index) => line[..index].trim_end(),
        None => line.trim_end(),
    }
}

fn capitalize(token: &str) -> String {
    let mut chars = token.chars();
    match chars.next() {
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
        None => String::new(),
    }
}
