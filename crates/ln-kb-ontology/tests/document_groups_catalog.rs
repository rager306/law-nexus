//! Document structural profiles (`document_groups`) are YAML-driven.
//!
//! Contract (M171 S01 T01): structural roles form a closed vocabulary;
//! ladder tokens must resolve inside the decode-token catalog; federal_law@v1
//! must stay bitwise-identical to the current article-body boundaries
//! (Statya unit; Glava/Razdel/Paragraph containers) and to the current decode
//! styles (decode_numbered_markers / decode_marker_prefixes). A document group
//! is a system_observation heuristic, never legal classification (ADR-0020).

use ln_kb_ontology::catalog::{CatalogError, OntologyCatalog};

const YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

fn catalog() -> OntologyCatalog {
    OntologyCatalog::embedded().expect("yaml")
}

fn group<'a>(catalog: &'a OntologyCatalog, id: &str) -> &'a ln_kb_ontology::catalog::DocumentGroup {
    catalog.document_group(id).expect("group")
}

// ─── embedded catalog shape ────────────────────────────────────────────────

#[test]
fn embedded_catalog_declares_five_document_groups() {
    let catalog = catalog();
    let ids: Vec<&str> = catalog
        .document_groups
        .iter()
        .map(|g| g.id.as_str())
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
fn structural_roles_are_a_closed_vocabulary() {
    let catalog = catalog();
    assert_eq!(
        catalog.structural_roles,
        ["container", "unit", "subunit", "subunit-text", "text-only"]
    );
    assert!(catalog.is_structural_role("container"));
    assert!(!catalog.is_structural_role("bogus"));
}

#[test]
fn every_ladder_token_is_inside_the_decode_token_catalog() {
    let catalog = catalog();
    let decode_tokens = yaml_alias_keys(YAML, "decode_level_aliases:");
    assert!(!decode_tokens.is_empty(), "decode_level_aliases missing");
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            let known = catalog
                .structural_only_tokens
                .iter()
                .any(|token| token == &entry.token)
                || decode_tokens
                    .iter()
                    .any(|token| token.eq_ignore_ascii_case(&entry.token));
            assert!(
                known,
                "group {} ladder token {} is outside the decode-token catalog",
                group.id, entry.token
            );
        }
    }
}

#[test]
fn ladders_only_use_declared_structural_roles() {
    let catalog = catalog();
    for group in &catalog.document_groups {
        for entry in &group.ladder {
            assert!(
                catalog.is_structural_role(&entry.role),
                "group {} ladder entry {} has unknown role {}",
                group.id,
                entry.token,
                entry.role
            );
        }
    }
}

#[test]
fn document_group_non_claims_are_declared() {
    let catalog = catalog();
    assert!(!catalog.document_group_non_claims.is_empty());
    let joined = catalog.document_group_non_claims.join("\n");
    assert!(
        joined.contains("system_observation"),
        "non_claims must frame binding as a system_observation heuristic: {joined}"
    );
    assert!(
        joined.contains("not an AST"),
        "non_claims must state practice != AST (ADR-0020): {joined}"
    );
}

// ─── federal_law@v1 regression: bitwise current behavior ───────────────────

#[test]
fn federal_law_v1_boundaries_match_current_article_body_behavior() {
    let catalog = catalog();
    let fl = group(&catalog, "federal_law@v1");

    // Current collect_article_texts: statya starts an article; Glava/Razdel/
    // Paragraph reset accumulation (article_body.rs is_statya/is_boundary).
    assert_eq!(ladder_decode_tokens(fl, "unit"), ["Statya"]);
    assert_eq!(
        ladder_decode_tokens(fl, "container"),
        ["Glava", "Paragraph", "Razdel"]
    );
    assert_eq!(
        ladder_decode_tokens(fl, "subunit"),
        ["Chast", "Podpunkt", "Punkt"]
    );

    // Granularity and text boundaries come from the profile.
    assert_eq!(fl.granularity.as_deref(), Some("statya"));
    assert_eq!(fl.text_boundary, ["unit", "container"]);
}

#[test]
fn federal_law_v1_styles_match_decode_numbered_markers() {
    let catalog = catalog();
    let fl = group(&catalog, "federal_law@v1");
    let styles = decode_numbered_styles(YAML);
    assert_eq!(
        styles.len(),
        3,
        "decode_numbered_markers must cover chast/punkt/podpunkt"
    );
    for entry in &fl.ladder {
        let Some(expected) = styles
            .iter()
            .find(|(token, _, _, _)| token.eq_ignore_ascii_case(&entry.token))
        else {
            continue;
        };
        assert_eq!(
            entry.suffix.as_deref(),
            Some(expected.1.as_str()),
            "federal_law@v1 {} suffix deviates from decode catalog",
            entry.token
        );
        assert_eq!(
            entry.number_style.as_deref(),
            Some(expected.2.as_str()),
            "federal_law@v1 {} number_style deviates from decode catalog",
            entry.token
        );
        assert_eq!(
            entry.compound,
            Some(expected.3),
            "federal_law@v1 {} compound deviates from decode catalog",
            entry.token
        );
    }
}

#[test]
fn federal_law_v1_punkt_is_recursive_with_max_depth_2() {
    let catalog = catalog();
    let fl = group(&catalog, "federal_law@v1");
    let punkt = fl
        .ladder
        .iter()
        .find(|entry| entry.token == "punkt")
        .expect("punkt in ladder");
    assert!(punkt.recursive, "punkt must be recursive");
    assert_eq!(punkt.max_depth, Some(2));
}

#[test]
fn federal_law_v1_prefix_levels_match_decode_marker_prefixes() {
    let catalog = catalog();
    let fl = group(&catalog, "federal_law@v1");
    let prefix_keys = yaml_map_keys(YAML, "decode_marker_prefixes:");
    assert_eq!(
        prefix_keys.len(),
        4,
        "decode_marker_prefixes must cover razdel/glava/statya/paragraph"
    );
    // The prefix-bearing levels are exactly the unit+container levels of the
    // profile: the current extractable prefix set must not grow or shrink.
    let profile_levels: Vec<String> = fl
        .ladder
        .iter()
        .filter(|entry| matches!(entry.role.as_str(), "unit" | "container"))
        .map(|entry| capitalize(&entry.token))
        .collect();
    let mut profile_levels = profile_levels;
    profile_levels.sort();
    assert_eq!(profile_levels, prefix_keys);
}

// ─── per-group structure ───────────────────────────────────────────────────

#[test]
fn code_group_is_razdel_glava_statya_depth_2() {
    let catalog = catalog();
    let code = group(&catalog, "code");
    assert_eq!(code.max_depth, Some(2));
    let tokens: Vec<&str> = code.ladder.iter().map(|e| e.token.as_str()).collect();
    assert_eq!(tokens, ["razdel", "glava", "statya"]);
    assert_eq!(code.granularity.as_deref(), Some("statya"));
}

#[test]
fn government_resolution_punkt_is_dot_style_recursive_depth_3() {
    let catalog = catalog();
    let gr = group(&catalog, "government_resolution");
    let punkt = gr
        .ladder
        .iter()
        .find(|entry| entry.token == "punkt")
        .expect("punkt");
    assert_eq!(punkt.role, "unit");
    assert!(punkt.recursive);
    assert_eq!(punkt.max_depth, Some(3));
    assert_eq!(punkt.suffix.as_deref(), Some("."), "dot-style punkt");
    let prilozhenie = gr
        .ladder
        .iter()
        .find(|entry| entry.token == "prilozhenie")
        .expect("prilozhenie");
    assert_eq!(prilozhenie.role, "container");
}

#[test]
fn departmental_order_primechanie_is_subunit_text() {
    let catalog = catalog();
    let order = group(&catalog, "departmental_order");
    let punkt = order
        .ladder
        .iter()
        .find(|entry| entry.token == "punkt")
        .expect("punkt");
    assert_eq!(punkt.role, "unit");
    assert!(punkt.recursive);
    assert_eq!(punkt.max_depth, Some(4));
    let primechanie = order
        .ladder
        .iter()
        .find(|entry| entry.token == "primechanie")
        .expect("primechanie");
    assert_eq!(primechanie.role, "subunit-text");
    assert!(catalog
        .structural_only_tokens
        .iter()
        .any(|token| token == "primechanie"));
}

#[test]
fn court_practice_is_text_only_without_ladder() {
    let catalog = catalog();
    let practice = group(&catalog, "court_practice");
    assert!(practice.text_only, "court practice is text-only");
    assert!(practice.ladder.is_empty(), "no ladder for text-only group");
    assert!(practice.granularity.is_none());
    assert!(practice.text_boundary.is_empty());
}

// ─── fail-closed validation: fixtures ──────────────────────────────────────

/// Minimal catalog YAML that satisfies every other parse_yaml requirement;
/// `groups_body` is appended as the top-level document_groups section.
fn parse_with_document_groups(groups_body: &str) -> Result<OntologyCatalog, CatalogError> {
    OntologyCatalog::parse_yaml(&format!(
        r#"schema_version: test/v1
fsm:
  current: O0
  states:
    O0:
      name: zero
    O1:
      name: one
  transitions:
    - {{from: O0, to: O1, when: x}}
vocabulary:
  hierarchy_levels:
    - razdel
    - glava
    - paragraph
    - statya
    - chast
    - punkt
    - podpunkt
  node_kinds:
    - Work
  edge_kinds:
    - expression_of
  forbidden_node_kinds:
    - ApplicableDecision
  presence_change_kinds:
    - include
  membership_change_kinds:
    - attach
  industrial_op_kinds:
    - split
  force_status_values:
    - unknown
  decode_level_aliases:
    Razdel: razdel
    Glava: glava
    Paragraph: paragraph
    Statya: statya
    Chast: chast
    Punkt: punkt
    Podpunkt: podpunkt
{}
"#,
        groups_body
    ))
}

const ROLES_AND_TOKENS: &str = "document_groups:
  structural_roles:
    - container
    - unit
    - subunit
    - subunit-text
    - text-only
  structural_only_tokens:
    - primechanie
    - prilozhenie
  non_claims:
    - test fixture
  groups:
";

#[test]
fn unknown_structural_role_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      ladder:\n        - {{token: statya, role: bogus}}\n"
    );
    let err = parse_with_document_groups(&yaml).expect_err("unknown role must fail closed");
    assert!(
        err.to_string().contains("structural role"),
        "unexpected error: {err}"
    );
}

#[test]
fn ladder_token_outside_decode_catalog_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      ladder:\n        - {{token: staty, role: unit}}\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("token outside decode catalog must fail closed");
    assert!(
        err.to_string().contains("decode-token catalog"),
        "unexpected error: {err}"
    );
}

#[test]
fn recursive_ladder_entry_requires_max_depth() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      ladder:\n        - {{token: punkt, role: subunit, recursive: true}}\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("recursive entry without max_depth must fail closed");
    assert!(err.to_string().contains("max_depth"), "unexpected: {err}");
}

#[test]
fn invalid_granularity_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      granularity: staty\n      ladder: []\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("granularity outside decode catalog must fail closed");
    assert!(
        err.to_string().contains("granularity"),
        "unexpected error: {err}"
    );
}

#[test]
fn invalid_suffix_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      ladder:\n        - {{token: punkt, role: subunit, suffix: x}}\n"
    );
    let err = parse_with_document_groups(&yaml).expect_err("invalid suffix must fail closed");
    assert!(
        err.to_string().contains("suffix"),
        "unexpected error: {err}"
    );
}

#[test]
fn invalid_number_style_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      ladder:\n        - {{token: punkt, role: subunit, number_style: hex}}\n"
    );
    let err = parse_with_document_groups(&yaml).expect_err("invalid number_style must fail closed");
    assert!(
        err.to_string().contains("number_style"),
        "unexpected error: {err}"
    );
}

#[test]
fn text_boundary_unknown_role_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      text_boundary: [bogus]\n      ladder: []\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("unknown role in text_boundary must fail closed");
    assert!(
        err.to_string().contains("text_boundary"),
        "unexpected error: {err}"
    );
}

#[test]
fn duplicate_group_id_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: dup\n      ladder:\n        - {{token: statya, role: unit}}\n    - id: dup\n      ladder:\n        - {{token: statya, role: unit}}\n"
    );
    let err = parse_with_document_groups(&yaml).expect_err("duplicate group id must fail closed");
    assert!(err.to_string().contains("duplicate"), "unexpected: {err}");
}

#[test]
fn groups_require_declared_structural_roles() {
    let yaml = "document_groups:\n  groups:\n    - id: x\n      ladder: []\n";
    let err = parse_with_document_groups(yaml)
        .expect_err("groups without structural_roles must fail closed");
    assert!(
        err.to_string().contains("structural_roles"),
        "unexpected error: {err}"
    );
}

#[test]
fn missing_document_groups_section_is_tolerated() {
    // Legacy catalogs without the section must still load (defaults are empty).
    let yaml = "schema_version: test/v1\nfsm:\n  current: O0\n  states:\n    O0:\n  transitions:\n    - {from: O0, to: O0, when: x}\nvocabulary:\n  hierarchy_levels:\n    - statya\n  node_kinds:\n    - Work\n  edge_kinds:\n    - expression_of\n  forbidden_node_kinds:\n    - ApplicableDecision\n  presence_change_kinds:\n    - include\n  membership_change_kinds:\n    - attach\n  industrial_op_kinds:\n    - split\n  force_status_values:\n    - unknown\n  decode_level_aliases:\n    Statya: statya\n";
    let catalog = OntologyCatalog::parse_yaml(yaml).expect("legacy catalog still loads");
    assert!(catalog.document_groups.is_empty());
    assert!(catalog.structural_roles.is_empty());
}

// ─── needles (factor A of two-factor detection, T02) ───────────────────────

#[test]
fn every_document_group_declares_needles_with_valid_fields() {
    let catalog = catalog();
    for group in &catalog.document_groups {
        assert!(
            !group.needles.is_empty(),
            "group {} must declare at least one metadata needle",
            group.id
        );
        for needle in &group.needles {
            assert!(
                matches!(needle.field.as_str(), "kind" | "type" | "path"),
                "group {} needle field {} is invalid",
                group.id,
                needle.field
            );
            assert!(
                !needle.needle.is_empty(),
                "group {} has an empty needle",
                group.id
            );
        }
    }
}

#[test]
fn invalid_needle_field_fails_load() {
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: federal_law@v1\n      needles:\n        - {{field: bogus, needle: x, rank: 10}}\n      ladder:\n        - {{token: statya, role: unit}}\n"
    );
    let err = parse_with_document_groups(&yaml).expect_err("invalid needle field must fail closed");
    assert!(
        err.to_string().contains("needle field"),
        "unexpected error: {err}"
    );
}

#[test]
fn structural_group_without_unit_role_fails_load() {
    let yaml = format!("{ROLES_AND_TOKENS}    - id: broken\n      ladder: []\n");
    let err = parse_with_document_groups(&yaml)
        .expect_err("structural group without a unit role must fail closed");
    assert!(
        err.to_string().contains("unit role"),
        "unexpected error: {err}"
    );
}

#[test]
fn structural_only_token_without_surface_fails_load() {
    // R8-09: primechanie/prilozhenie have no decode HierarchyLevel — the
    // collector recognizes them by their catalog `surface` marker. A
    // structural-only token without a surface is a degenerate entry the
    // collector can never recognize (fail-closed schema).
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: broken\n      ladder:\n        - {{token: primechanie, role: subunit-text}}\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("structural-only token without surface must fail closed");
    assert!(
        err.to_string().contains("surface"),
        "unexpected error: {err}"
    );
}

#[test]
fn decode_level_token_with_surface_fails_load() {
    // Decode-level tokens (statya, punkt, ...) are recognized by
    // extract_hierarchy; declaring a surface would shadow the marker.
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: broken\n      ladder:\n        - {{token: statya, role: unit, surface: \"Статья\"}}\n"
    );
    let err = parse_with_document_groups(&yaml)
        .expect_err("decode-level token with surface must fail closed");
    assert!(
        err.to_string().contains("surface"),
        "unexpected error: {err}"
    );
}

#[test]
fn structural_only_tokens_declare_surfaces_in_embedded_catalog() {
    let catalog = catalog();
    let order = group(&catalog, "departmental_order");
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
    let gr = group(&catalog, "government_resolution");
    let prilozhenie_gr = gr
        .ladder
        .iter()
        .find(|entry| entry.token == "prilozhenie")
        .expect("prilozhenie");
    assert_eq!(prilozhenie_gr.surface.as_deref(), Some("Приложение"));
}

#[test]
fn classify_document_group_binds_by_ranked_needle() {
    use ln_kb_ontology::catalog::DocumentGroupOutcome;
    let catalog = catalog();
    match catalog.classify_document_group(Some("federalnyi-zakon-44-fz"), None, None) {
        DocumentGroupOutcome::Bound { group, needle } => {
            assert_eq!(group, "federal_law@v1");
            // Lower rank wins: federalnyi-zakon (10) beats law_ (20).
            assert_eq!(needle, "federalnyi-zakon");
        }
        other => panic!("expected Bound, got {other:?}"),
    }
    match catalog.classify_document_group(Some("reshenie-fas-2024-123"), None, None) {
        DocumentGroupOutcome::Bound { group, .. } => assert_eq!(group, "court_practice"),
        other => panic!("expected Bound court_practice, got {other:?}"),
    }
    match catalog.classify_document_group(Some("prikaz-minzdrava-2024"), None, None) {
        DocumentGroupOutcome::Bound { group, .. } => assert_eq!(group, "departmental_order"),
        other => panic!("expected Bound departmental_order, got {other:?}"),
    }
}

#[test]
fn classify_document_group_kind_field_binds() {
    use ln_kb_ontology::catalog::DocumentGroupOutcome;
    let catalog = catalog();
    match catalog.classify_document_group(None, Some("law"), None) {
        DocumentGroupOutcome::Bound { group, .. } => assert_eq!(group, "federal_law@v1"),
        other => panic!("expected Bound federal_law@v1, got {other:?}"),
    }
    match catalog.classify_document_group(None, Some("court"), None) {
        DocumentGroupOutcome::Bound { group, .. } => assert_eq!(group, "court_practice"),
        other => panic!("expected Bound court_practice, got {other:?}"),
    }
    match catalog.classify_document_group(None, None, Some("order")) {
        DocumentGroupOutcome::Bound { group, .. } => assert_eq!(group, "departmental_order"),
        other => panic!("expected Bound departmental_order, got {other:?}"),
    }
}

#[test]
fn classify_document_group_unknown_when_no_needle_matches() {
    use ln_kb_ontology::catalog::DocumentGroupOutcome;
    let catalog = catalog();
    assert_eq!(
        catalog.classify_document_group(Some("mystery-file.docx"), None, None),
        DocumentGroupOutcome::Unknown
    );
    assert_eq!(
        catalog.classify_document_group(None, None, None),
        DocumentGroupOutcome::Unknown
    );
}

#[test]
fn classify_document_group_same_rank_different_groups_is_conflict() {
    use ln_kb_ontology::catalog::DocumentGroupOutcome;
    let yaml = format!(
        "{ROLES_AND_TOKENS}    - id: alpha\n      needles:\n        - {{field: path, needle: shared-doc, rank: 10}}\n      ladder:\n        - {{token: statya, role: unit}}\n    - id: beta\n      needles:\n        - {{field: path, needle: shared-doc, rank: 10}}\n      ladder:\n        - {{token: punkt, role: unit}}\n"
    );
    let catalog = parse_with_document_groups(&yaml).expect("fixture loads");
    match catalog.classify_document_group(Some("shared-doc-1"), None, None) {
        DocumentGroupOutcome::Conflict { groups } => {
            assert_eq!(groups, ["alpha", "beta"]);
        }
        other => panic!("expected Conflict, got {other:?}"),
    }
}

// ─── local YAML decode-section helpers (mirror catalog_coverage.rs) ────────

fn ladder_decode_tokens(group: &ln_kb_ontology::catalog::DocumentGroup, role: &str) -> Vec<String> {
    let alias_keys = yaml_alias_keys(YAML, "decode_level_aliases:");
    let mut tokens: Vec<String> = group
        .ladder
        .iter()
        .filter(|entry| entry.role == role)
        .map(|entry| {
            alias_keys
                .iter()
                .find(|key| key.eq_ignore_ascii_case(&entry.token))
                .expect("ladder token resolves to a decode token")
                .clone()
        })
        .collect();
    tokens.sort();
    tokens
}

fn yaml_alias_keys(text: &str, heading: &str) -> Vec<String> {
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
                if !key.is_empty() {
                    keys.push(key.to_owned());
                }
            }
        }
    }
    keys
}

fn yaml_map_keys(text: &str, heading: &str) -> Vec<String> {
    let mut keys = yaml_alias_keys(text, heading);
    keys.sort();
    keys
}

/// (decode token, number_style, suffix, allow_compound) rows of
/// `decode_numbered_markers:`.
fn decode_numbered_styles(text: &str) -> Vec<(String, String, String, bool)> {
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
