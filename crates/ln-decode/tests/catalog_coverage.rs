//! Decode hierarchy tokens must stay covered by YAML `decode_level_aliases`.
//! No ontology crate dependency: the catalog is data, not a Rust type.

use ln_decode::domain::HierarchyLevel;

const YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

#[test]
fn every_hierarchy_level_token_is_a_yaml_alias_key() {
    let keys = yaml_map_keys(YAML, "decode_level_aliases:");
    assert!(!keys.is_empty(), "decode_level_aliases missing from YAML");
    for level in HierarchyLevel::all() {
        assert!(
            keys.iter().any(|key| key == level.as_str()),
            "YAML decode_level_aliases missing decode token {}",
            level.as_str()
        );
    }
}

#[test]
fn yaml_prefixes_cover_currently_extractable_tokens() {
    let keys = yaml_map_keys(YAML, "decode_marker_prefixes:");
    for token in ["Razdel", "Glava", "Statya", "Paragraph"] {
        assert!(
            keys.iter().any(|key| key == token),
            "decode_marker_prefixes missing {token}"
        );
    }
}

#[test]
fn unknown_prefix_token_is_rejected_by_catalog() {
    let yaml = concat!(
        "decode_marker_prefixes:\n",
        "  Article: [Article]\n",
        "decode_prefix_space_policy:\n",
        "  default: required\n",
        "decode_number_styles:\n",
        "  Article: digit\n",
    );
    let err = ln_decode::prefix_catalog::DecodePrefixCatalog::parse_yaml(yaml)
        .expect_err("unknown token");
    assert!(err.contains("decode token") || err.contains("prefix key"));
}

#[test]
fn hierarchy_level_tokens_are_unique() {
    let mut seen = Vec::new();
    for level in HierarchyLevel::all() {
        let token = level.as_str();
        assert!(!token.is_empty());
        assert!(!seen.contains(&token), "duplicate token {token}");
        seen.push(token);
    }
}

fn yaml_map_keys(text: &str, heading: &str) -> Vec<String> {
    let mut keys = Vec::new();
    let mut in_map = false;
    let mut heading_indent = 0usize;
    for raw in text.lines() {
        let trimmed = raw.split('#').next().unwrap_or(raw);
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
