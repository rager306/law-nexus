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

/// T03 catalog pin: the `npa_abbrev_lexicon` YAML map must carry exactly the
/// 17-id S01 canon (ADR-0028 legal-drafting lexicon) — an extra id, a missing
/// id, or a duplicate id all fail. The lexer parses the same map fail-closed.
#[test]
fn npa_abbrev_lexicon_ids_are_exactly_the_s01_canon() {
    let keys = yaml_map_keys(YAML, "npa_abbrev_lexicon:");
    let mut sorted = keys.clone();
    sorted.sort();
    sorted.dedup();
    assert_eq!(
        sorted.len(),
        keys.len(),
        "npa_abbrev_lexicon must not repeat an id"
    );
    let mut expected: Vec<String> = [
        "st", "stst", "ch", "p", "pp", "podp", "abz", "gl", "razd", "pril", "prim", "red", "izm",
        "utv", "sm", "sr", "g",
    ]
    .into_iter()
    .map(String::from)
    .collect();
    expected.sort();
    assert_eq!(
        sorted, expected,
        "npa_abbrev_lexicon must equal the 17 S01 canon ids exactly (extra or missing fails)"
    );
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
