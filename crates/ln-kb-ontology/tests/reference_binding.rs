//! D222/D224 pin-suite for the E.2.2 reference binding contract
//! (design-doc-as-data).
//!
//! `prd/architecture/reference-binding-contract.yaml` (owner: ADR-0019 G0)
//! is embedded via `include_str!` and pinned with plain text/section
//! assertions, mirroring `operation_registry.rs` (E.2.1). Per
//! D222/MEM938/MEM939/D224 the contract carries neither `rust_path` nor
//! `rust_enum`, is not a `closed_vocabularies` row and is not parsed by
//! `OntologyCatalog`, so this suite stays parser-free string/section work
//! over two embedded YAML files and adds no YAML crate dependency.
//!
//! Token alignment (4 statuses x 6 semantics modes) is checked against the
//! embedded `reference_binding_vocabulary` section of `kb-ontology.yaml` —
//! the token canon lives only in that YAML; this suite extracts both sides
//! and compares, it never restates the token lists as a second canon.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor `ln_temporal` nor `ln_decode`, and never
//! references `ReferenceMention`, `CtvIndustrialOpKind` or
//! `try_cross_act_edge` in code (grep-pinned in slice Verify). Coupling the
//! pin suite to the runtime types it guards would invert the D222 boundary;
//! decode homonymy stays prose in the YAML non_claims.
//!
//! Negative surface (Q7): losing `unclassified`, flipping the default to
//! `identity_ambulatory`, dropping `survives_repealed_target: true`,
//! promoting lifecycle beyond `[proposed]`, flipping `authoritative`,
//! widening `typed_non_success` with `Applied`/`Bound`/`RepealedTarget`,
//! minting a fourth PascalCase entity key (`MergeEntries:`, `Join:`,
//! `IdentityAmbulatory:`), dropping a required field, breaking the 6<->6
//! alias bijection, widening `runtime_today`, or drifting a token away from
//! the kb-ontology canon all turn pins red on the tracked files themselves —
//! no tmp fixtures, no runtime dependency. Absence pins over
//! `typed_non_success` run on parsed items, not raw substrings, because the
//! contract's own section comments legitimately name `Bound`/`Applied` as
//! exclusions.

/// Embedded contract, same lift as `operation-registry.yaml`.
/// Path is relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str =
    include_str!("../../../prd/architecture/reference-binding-contract.yaml");

/// Embedded token canon: statuses and semantics modes must stay
/// character-identical to `vocabulary.reference_binding_vocabulary`.
const ONTOLOGY_YAML: &str = include_str!("../../../prd/architecture/kb-ontology.yaml");

/// Closed 4-status x 6-mode token counts (canon sizes, not token copies).
const STATUS_COUNT: usize = 4;
const MODE_COUNT: usize = 6;

/// Closed typed non-success set (review-25 E.2.2), canonical order.
/// `Applied`/`Bound` are successes; `RepealedTarget` is a force fact
/// (AXIS-5), never a binding failure.
const TYPED_NON_SUCCESS: [&str; 4] = [
    "TargetNotFound",
    "AmbiguousTarget",
    "IncompleteSource",
    "UnclassifiedRequired",
];

/// Successes and non-failures that must stay out of `typed_non_success`.
const NON_FAILURE_TOKENS: [&str; 3] = ["Applied", "Bound", "RepealedTarget"];

/// Closed runtime-contour vocabulary accepted for per-entity `runtime_today`.
const RUNTIME_TODAY_VALUES: [&str; 3] = ["lexical_decode", "none", "inventory_constructor"];

struct EntityBlock {
    name: String,
    body: String,
}

fn contract_marker_line(yaml: &str, marker: &str) -> usize {
    yaml.lines()
        .position(|line| line.starts_with(marker))
        .unwrap_or_else(|| panic!("contract marker missing: {marker}"))
}

/// Two-space dash items directly under a top-level contract key; collection
/// stops at the first non-item line (blank separator or the next key).
fn top_level_dash_items<'a>(yaml: &'a str, marker: &str) -> Vec<&'a str> {
    let start = contract_marker_line(yaml, marker);
    yaml.lines()
        .skip(start + 1)
        .map_while(|line| line.strip_prefix("  - "))
        .map(str::trim)
        .collect()
}

/// Items of an inline `[a, b, c]` list on a single YAML line.
fn inline_bracket_items(line: &str) -> Vec<&str> {
    let open = line.find('[').expect("inline list opening bracket");
    let close = line.find(']').expect("inline list closing bracket");
    line[open + 1..close]
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .collect()
}

/// Inline `statuses` list inside `reference_binding_vocabulary`.
fn ontology_status_tokens() -> Vec<&'static str> {
    let line = ONTOLOGY_YAML
        .lines()
        .find(|line| line.starts_with("    statuses:"))
        .expect("kb-ontology statuses row missing");
    inline_bracket_items(line)
}

/// Six-space dash items under
/// `vocabulary.reference_binding_vocabulary.semantics_modes`; the fixed
/// indent keeps collection from running into the sibling `non_claims` list.
fn ontology_mode_tokens() -> Vec<&'static str> {
    let start = ONTOLOGY_YAML
        .lines()
        .position(|line| line == "    semantics_modes:")
        .expect("kb-ontology semantics_modes row missing");
    ONTOLOGY_YAML
        .lines()
        .skip(start + 1)
        .map_while(|line| line.strip_prefix("      - "))
        .map(str::trim)
        .collect()
}

/// Line indices of two-space-indented PascalCase-colon lines — exactly the
/// shape of an entity entry under `entities:`. Deeper field lines,
/// alias/family/strike rows (lowercase keys), dash items and prose
/// continuations never match, so a stray `MergeEntries:` or
/// `IdentityAmbulatory:` entity key would be caught here.
fn entity_key_line_indices(yaml: &str) -> Vec<usize> {
    yaml.lines()
        .enumerate()
        .filter_map(|(index, line)| {
            let rest = line.strip_prefix("  ")?;
            if rest.starts_with(' ') || rest.starts_with('-') {
                return None;
            }
            let key = rest.strip_suffix(':')?;
            let mut chars = key.chars();
            let starts_upper = chars.next().is_some_and(|c| c.is_ascii_uppercase());
            if starts_upper && chars.all(|c| c.is_ascii_alphanumeric()) {
                Some(index)
            } else {
                None
            }
        })
        .collect()
}

/// Entity blocks: from each entity key line to just before the next entity
/// key line (or EOF — the last body spans into `strike:`/`non_claims:`).
/// Every assertion below is anchored on exact keys or exact values, so the
/// over-approximation cannot mask an absence pin.
fn entity_blocks(yaml: &str) -> Vec<EntityBlock> {
    let key_lines = entity_key_line_indices(yaml);
    assert!(
        key_lines.len() == 3,
        "expected exactly three entity keys, found {}",
        key_lines.len()
    );
    let lines: Vec<&str> = yaml.lines().collect();
    key_lines
        .iter()
        .enumerate()
        .map(|(position, &start)| {
            let end = key_lines.get(position + 1).copied().unwrap_or(lines.len());
            EntityBlock {
                name: lines[start].trim().trim_end_matches(':').to_owned(),
                body: lines[start + 1..end].join("\n"),
            }
        })
        .collect()
}

fn block_of<'a>(blocks: &'a [EntityBlock], name: &str) -> &'a EntityBlock {
    blocks
        .iter()
        .find(|block| block.name == name)
        .unwrap_or_else(|| panic!("entity block missing: {name}"))
}

/// Four-space-indented scalar field inside an entity body; inline comments
/// (` # ...`) are cut, surrounding quotes stripped.
fn entity_scalar<'a>(block: &'a EntityBlock, field: &str) -> &'a str {
    let marker = format!("{field}:");
    block
        .body
        .lines()
        .filter_map(|line| {
            let rest = line.strip_prefix("    ")?;
            rest.strip_prefix(marker.as_str())
        })
        .next()
        .unwrap_or_else(|| panic!("{}: scalar field {field} missing", block.name))
        .split('#')
        .next()
        .unwrap_or_default()
        .trim()
        .trim_matches('"')
}

/// Field keys inside the `required_fields:` subsection of an entity body.
/// The subsection ends at the next four-space key (`confirmed_target`,
/// `typed_non_success`, ...); eight-space folded-scalar continuations are
/// skipped, so prose colons cannot masquerade as field keys.
fn required_field_keys(block: &EntityBlock) -> Vec<&str> {
    let lines: Vec<&str> = block.body.lines().collect();
    let start = lines
        .iter()
        .position(|line| *line == "    required_fields:")
        .unwrap_or_else(|| panic!("{}: required_fields section missing", block.name));
    let mut keys = Vec::new();
    for line in &lines[start + 1..] {
        if line.starts_with("    ") && !line.starts_with("      ") {
            break; // next four-space key ends the subsection
        }
        if let Some(rest) = line.strip_prefix("      ") {
            if rest.starts_with(' ') || rest.starts_with('-') || rest.starts_with(':') {
                continue;
            }
            if let Some(key) = rest.split(':').next() {
                let key = key.trim();
                if !key.is_empty() {
                    keys.push(key);
                }
            }
        }
    }
    keys
}

/// `snake_case: PascalAlias` rows of the top-level `adr_aliases` section
/// (bounded by the following `edge_family` key).
fn adr_alias_rows() -> Vec<(&'static str, &'static str)> {
    let start = contract_marker_line(CONTRACT_YAML, "adr_aliases:");
    let end = contract_marker_line(CONTRACT_YAML, "edge_family:");
    CONTRACT_YAML
        .lines()
        .skip(start + 1)
        .take(end - start - 1)
        .filter_map(|line| {
            let rest = line.strip_prefix("  ")?;
            if rest.starts_with(' ') {
                return None;
            }
            let (snake, pascal) = rest.split_once(": ")?;
            Some((snake, pascal))
        })
        .collect()
}

#[test]
fn contract_embeds_as_data_and_pins_schema_identity() {
    assert!(!CONTRACT_YAML.is_empty(), "contract failed to embed");
    assert!(
        CONTRACT_YAML.contains("schema_version: law-nexus-reference-binding-contract/v1"),
        "contract schema identity drifted"
    );
}

#[test]
fn contract_lifecycle_stays_proposed_and_non_authoritative() {
    assert!(CONTRACT_YAML.contains("lifecycle: \"[proposed]\""));
    assert!(CONTRACT_YAML.contains("authoritative: false"));
    // Authority-laundering guards: promotion of the design contract to
    // bounded/runtime authority must break this pin before any consumer
    // exists (mirrors operation_registry.rs).
    assert!(!CONTRACT_YAML.contains("authoritative: true"));
    assert!(!CONTRACT_YAML.contains("[bounded]"));
}

#[test]
fn header_points_at_owner_adr_and_the_kb_ontology_token_source() {
    assert!(CONTRACT_YAML.contains("owner_adr: ADR-0019"));
    assert!(CONTRACT_YAML.contains(
        "token_source: prd/architecture/kb-ontology.yaml#vocabulary.reference_binding_vocabulary"
    ));
}

#[test]
fn status_and_mode_tokens_stay_character_identical_to_the_kb_ontology_canon() {
    // Two embeds, zero restated lists: both sides are extracted from the
    // tracked YAML files; the token canon lives only in kb-ontology.yaml.
    let contract_statuses = top_level_dash_items(CONTRACT_YAML, "binding_statuses:");
    let ontology_statuses = ontology_status_tokens();
    assert_eq!(
        contract_statuses.len(),
        STATUS_COUNT,
        "status count drifted"
    );
    assert_eq!(
        ontology_statuses.len(),
        STATUS_COUNT,
        "kb-ontology statuses lost"
    );
    assert_eq!(
        contract_statuses, ontology_statuses,
        "status tokens diverged"
    );

    let contract_modes = top_level_dash_items(CONTRACT_YAML, "semantics_modes:");
    let ontology_modes = ontology_mode_tokens();
    assert_eq!(contract_modes.len(), MODE_COUNT, "mode count drifted");
    assert_eq!(ontology_modes.len(), MODE_COUNT, "kb-ontology modes lost");
    assert_eq!(contract_modes, ontology_modes, "mode tokens diverged");
}

#[test]
fn unclassified_is_present_and_is_the_declared_default() {
    let modes = top_level_dash_items(CONTRACT_YAML, "semantics_modes:");
    assert!(modes.contains(&"unclassified"), "honest default token lost");
    assert!(
        CONTRACT_YAML.contains("default_semantics_mode: unclassified"),
        "default_semantics_mode declaration lost"
    );
    assert!(
        !CONTRACT_YAML.contains("default_semantics_mode: identity_ambulatory"),
        "identity_ambulatory must never become the default (F11-A)"
    );
}

#[test]
fn three_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["ReferenceMention", "ReferenceBinding", "ReferenceSemantics"],
        "entity key set/order drifted"
    );
    for name in &names {
        assert_eq!(
            CONTRACT_YAML.matches(&format!("\n  {name}:")).count(),
            1,
            "{name} entity key must appear exactly once"
        );
    }
}

#[test]
fn every_entity_carries_its_required_fields() {
    let expected: &[(&str, &[&str])] = &[
        (
            "ReferenceMention",
            &["span", "literal_wording", "source_ctv", "occurrence_id"],
        ),
        (
            "ReferenceBinding",
            &["mention_ref", "candidates", "evidence", "status"],
        ),
        ("ReferenceSemantics", &["kind", "temporal_binding_mode"]),
    ];
    let blocks = entity_blocks(CONTRACT_YAML);
    for (name, fields) in expected {
        assert_eq!(
            required_field_keys(block_of(&blocks, name)),
            fields.to_vec(),
            "{name}: required_fields drifted"
        );
    }
}

#[test]
fn typed_non_success_is_the_closed_four_set_without_failure_laundering() {
    let failures = top_level_dash_items(CONTRACT_YAML, "typed_non_success:");
    assert_eq!(
        failures,
        TYPED_NON_SUCCESS.to_vec(),
        "closed non-success set drifted"
    );
    for token in NON_FAILURE_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is a success or a force fact, never a binding failure"
        );
    }
}

#[test]
fn per_entity_typed_non_success_stays_inside_the_closed_set() {
    // Parsed-item checks, not raw substrings: the section comments may
    // legitimately name Applied/Bound/RepealedTarget as exclusions.
    for block in entity_blocks(CONTRACT_YAML) {
        let failures = inline_bracket_items(entity_scalar(&block, "typed_non_success"));
        assert!(
            !failures.is_empty(),
            "{}: typed_non_success must be non-empty (fail-closed)",
            block.name
        );
        for failure in &failures {
            assert!(
                TYPED_NON_SUCCESS.contains(failure),
                "{}: unknown typed non-success {failure}",
                block.name
            );
            assert!(
                !NON_FAILURE_TOKENS.contains(failure),
                "{}: {failure} laundered into typed_non_success",
                block.name
            );
        }
    }
}

#[test]
fn strike_behavior_and_repealed_survival_are_declared() {
    for key in ["on_source", "on_target", "repealed_target"] {
        assert!(
            CONTRACT_YAML.contains(&format!("\n  {key}:")),
            "strike key {key} missing"
        );
    }
    // AXIS-5 != AXIS-7 (INV-06): a successful binding survives a Repealed
    // target; force loss never reads as a broken binding and never upgrades
    // cites to authority.
    assert!(
        CONTRACT_YAML.contains("survives_repealed_target: true"),
        "survives_repealed_target invariant lost"
    );
}

#[test]
fn non_claims_carry_cites_never_authority_and_decode_homonymy() {
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    let has_claim = |needle: &str| claims.iter().any(|claim| claim.contains(needle));
    assert!(
        has_claim("cites never upgrades to authority"),
        "cites-never-authority non-claim lost (review-25 D.1)"
    );
    assert!(
        has_claim("lexical Article/Point candidate"),
        "ln-decode decode-homonymy non-claim lost"
    );
    assert!(
        has_claim("IdentityAmbulatory is not inferred"),
        "no-inferred-alias non-claim lost"
    );
    assert!(
        has_claim("Merge/Join/ReplaceText are not binding entities"),
        "operation-name disclaimer lost"
    );
    assert!(
        has_claim("No Rust types are minted"),
        "no-Rust-types non-claim lost"
    );
    assert!(
        has_claim("No closed_vocabularies row"),
        "not-a-closed-vocabulary non-claim lost"
    );
}

#[test]
fn amends_stays_outside_the_reference_edge_family() {
    // kind(Semantics) is limited to refers_to/cites: refers_to is the
    // superset family, cites its subset, and amends/authority stay never.
    assert!(CONTRACT_YAML.contains("superset: refers_to"));
    assert!(CONTRACT_YAML.contains("subset: [cites]"));
    assert!(
        CONTRACT_YAML.contains("never: [amends, authority, citation_authority]"),
        "amends/authority must stay outside the reference edge family"
    );
}

#[test]
fn s01_operation_names_never_mint_entity_keys() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in [
        "ReplaceText",
        "MergeEntries",
        "Join",
        "Cites",
        "IdentityAmbulatory",
    ] {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !CONTRACT_YAML.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected"
        );
    }
    // MEM947 isolation is owned by operation-registry.yaml plus its own pin
    // suite; this contract legitimately carries cites / IdentityAmbulatory
    // as alias data and prose (checked above) and must not grow a cross-file
    // registry path reference in either direction.
    assert!(
        !CONTRACT_YAML.contains("operation-registry.yaml"),
        "cross-file registry path leaked into the contract"
    );
}

#[test]
fn adr_aliases_form_a_bijection_with_the_snake_case_modes() {
    let modes = top_level_dash_items(CONTRACT_YAML, "semantics_modes:");
    let aliases = adr_alias_rows();
    let snakes: Vec<&str> = aliases.iter().map(|(snake, _)| *snake).collect();
    let pascals: Vec<&str> = aliases.iter().map(|(_, pascal)| *pascal).collect();

    assert_eq!(aliases.len(), MODE_COUNT, "alias table must stay 6<->6");
    assert_eq!(
        snakes, modes,
        "alias rows must cover every mode, canon order"
    );

    let mut sorted_pascals = pascals.clone();
    sorted_pascals.sort_unstable();
    sorted_pascals.dedup();
    assert_eq!(
        sorted_pascals.len(),
        MODE_COUNT,
        "PascalCase aliases must be distinct"
    );

    for pascal in pascals {
        let mut chars = pascal.chars();
        assert!(
            chars.next().is_some_and(|c| c.is_ascii_uppercase())
                && chars.all(|c| c.is_ascii_alphanumeric()),
            "alias {pascal} is not a PascalCase spelling"
        );
        assert!(
            !CONTRACT_YAML.contains(&format!("\n  {pascal}:")),
            "PascalCase mode {pascal} must never be an entity-depth key"
        );
    }
}

#[test]
fn runtime_today_is_a_closed_three_value_vocabulary_per_entity() {
    for block in entity_blocks(CONTRACT_YAML) {
        let value = entity_scalar(&block, "runtime_today");
        assert!(
            RUNTIME_TODAY_VALUES.contains(&value),
            "{}: runtime_today {value:?} outside the closed set",
            block.name
        );
    }
}

#[test]
fn runtime_today_mapping_matches_the_design_only_contours() {
    let blocks = entity_blocks(CONTRACT_YAML);
    assert_eq!(
        entity_scalar(block_of(&blocks, "ReferenceMention"), "runtime_today"),
        "lexical_decode",
        "Mention contour is ln-decode lexical candidates only"
    );
    for name in ["ReferenceBinding", "ReferenceSemantics"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            "none",
            "{name} must stay design-only"
        );
    }
}
