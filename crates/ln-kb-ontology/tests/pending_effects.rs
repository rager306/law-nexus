//! D222/D226 pin-suite for the E.2.3 pending-effects contract
//! (design-doc-as-data).
//!
//! `prd/architecture/pending-effects-contract.yaml` (owner: ADR-0017; the
//! ADR-0018 force overlay and ADR-0021 transitional relations are related,
//! never owners) is embedded via `include_str!` and pinned with plain
//! text/section assertions, mirroring `reference_binding.rs` (E.2.2) and
//! `operation_registry.rs` (E.2.1). Per D222/MEM938/MEM939 the contract
//! carries neither `rust_path` nor `rust_enum`, is not a
//! `closed_vocabularies` row and is not parsed by `OntologyCatalog`, so
//! this suite stays parser-free string/section work over two embedded YAML
//! files and adds no YAML crate dependency.
//!
//! Token alignment (6 selector modes x 3 OP-P names) is checked against
//! the embedded `operation-registry.yaml`: the name canon lives only
//! there (`effect_selector_modes` and `families.OP-P`). This suite
//! extracts both sides and compares; it never restates a token list as a
//! second canon (MEM951). The review-26 P0-4 / D252 transition_predicates
//! 1-set canon also lives only there; this suite pins its length and its
//! disjointness from selector_modes, never the predicate name itself.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor `ln_temporal`, and never references
//! `PendingEffect`, `CtvIndustrialOpKind` or `DisposeReview` as code
//! identifiers (grep-pinned in slice Verify). Coupling the pin suite to
//! the runtime types it guards would invert the D222 boundary; entity and
//! Review-Case homonymy stays prose in the YAML non_claims.
//!
//! Negative surface (Q7): minting a seventh selector mode
//! (`ForRelationsAfter` returning as a parsed selector_modes item), a
//! `modified` state, a third entity key (including two-space
//! `ActivationTrigger:` / `TransitionPredicate:` keys), widening
//! `typed_non_success` with a success, force or neighbor-contract token,
//! promoting lifecycle beyond `[proposed]`, flipping `authoritative`,
//! moving ownership away from ADR-0017, `runtime_today` beyond `none`,
//! seeding `InForce`, adding a fifth FSM row, or dropping a required
//! field all turn pins red on the tracked file itself — no tmp fixtures,
//! no runtime dependency. Absence pins over `states`, `typed_non_success`,
//! `force_status_seed` and `selector_modes` run on parsed items, not raw
//! substrings, because the contract's own comments and non_claims
//! legitimately name `modified`, `applied`, `InForce`-shaped tokens and
//! `ForRelationsAfter` after review-26 P0-4. Losing `Unclassified` is
//! E.2.2 reference-binding territory, not this suite's negative surface.

/// Embedded contract (T01): the E.2.3 entity/FSM layer.
/// Path is relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str = include_str!("../../../prd/architecture/pending-effects-contract.yaml");

/// Embedded name canon: selector modes and OP-P operation names must stay
/// character-identical to `effect_selector_modes` and `families.OP-P`.
const REGISTRY_YAML: &str = include_str!("../../../prd/architecture/operation-registry.yaml");

/// Closed canon sizes pinned inside the comparing tests (MEM951: sizes and
/// cross-file equality only, never a restated token list).
const SELECTOR_MODE_COUNT: usize = 6;
const OP_P_NAME_COUNT: usize = 3;

/// Closed typed non-success set (MC-RES minus Applied), canonical order.
/// Modify/Cancel on an applied or cancelled pending effect stays
/// PreconditionMismatch, never a new AlreadyApplied token.
const TYPED_NON_SUCCESS: [&str; 8] = [
    "TargetNotFound",
    "AmbiguousTarget",
    "PreconditionMismatch",
    "BaseVersionMismatch",
    "OrderingConflict",
    "UnknownEffect",
    "UnsupportedOperation",
    "IncompleteSource",
];

/// Successes, force states and neighbor-contract tokens that must stay out
/// of `typed_non_success` (parsed-item checks, not substrings — MEM951).
const NON_FAILURE_TOKENS: [&str; 6] = [
    "Applied",
    "Bound",
    "AlreadyApplied",
    "Suspended",
    "Transitional",
    "UnclassifiedRequired",
];

/// The only runtime contour this design-only contract accepts: neither
/// entity exists at runtime.
const RUNTIME_TODAY_VALUE: &str = "none";

struct EntityBlock {
    name: String,
    body: String,
}

fn contract_marker_line(yaml: &str, marker: &str) -> usize {
    yaml.lines()
        .position(|line| line.starts_with(marker))
        .unwrap_or_else(|| panic!("contract marker missing: {marker}"))
}

/// The top-level `key: ...` row of the contract (zero indent, line start).
fn top_level_row(key: &str) -> &'static str {
    CONTRACT_YAML
        .lines()
        .find(|line| line.starts_with(key))
        .unwrap_or_else(|| panic!("contract top-level row missing: {key}"))
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

/// The top-of-file authority block: everything before the first closed-set
/// key. Absence pins for `authoritative: true` / `[bounded]` run here, not
/// over the whole file, because body comments may legitimately name them.
fn header_block() -> String {
    let cut = contract_marker_line(CONTRACT_YAML, "selector_modes:");
    CONTRACT_YAML
        .lines()
        .take(cut)
        .collect::<Vec<_>>()
        .join("\n")
}

/// The contract without its trailing `non_claims:` section (MEM947): the
/// boundary prose there may legitimately name neighbor-contract tokens, so
/// raw-token isolation pins must not scan it.
fn contract_without_non_claims() -> &'static str {
    let cut = CONTRACT_YAML
        .find("\nnon_claims:")
        .expect("non_claims section missing");
    &CONTRACT_YAML[..cut]
}

/// Line indices of two-space-indented PascalCase-colon lines — exactly the
/// shape of an entity entry under `entities:`. Deeper field lines, FSM
/// rows (dash items and their four-space continuations), lowercase
/// two-space section keys and prose continuations never match, so a stray
/// `ScheduleEffect:` or `ReferenceMention:` entity key would be caught
/// here.
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
/// key line (or EOF — the last body spans into `transitions:` /
/// `modifies_pending_effect:` / `checkout:` / `non_claims:`). Every
/// assertion below is anchored on exact keys or exact values, so the
/// over-approximation cannot mask an absence pin.
fn entity_blocks(yaml: &str) -> Vec<EntityBlock> {
    let key_lines = entity_key_line_indices(yaml);
    assert!(
        key_lines.len() == 2,
        "expected exactly two entity keys, found {}",
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
/// The subsection ends at the next four-space key (`modification_provenance`,
/// `force_status_seed`, ...); eight-space folded-scalar continuations are
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

/// Six-space PascalCase-colon operation keys, scoped to the registry
/// `families.OP-P` block only (`  OP-P:` up to the next `  OP-` family
/// header). Scanning the whole registry would collect all 29 G0 keys; the
/// family boundary keeps the extraction at exactly the E.2.3 names.
fn registry_op_p_names() -> Vec<&'static str> {
    let lines: Vec<&str> = REGISTRY_YAML.lines().collect();
    let start = lines
        .iter()
        .position(|line| *line == "  OP-P:")
        .expect("registry OP-P family missing");
    let end = lines[start + 1..]
        .iter()
        .position(|line| line.starts_with("  OP-"))
        .map(|offset| start + 1 + offset)
        .unwrap_or(lines.len());
    lines[start + 1..end]
        .iter()
        .filter_map(|line| {
            let rest = line.strip_prefix("      ")?;
            if rest.starts_with(' ') {
                return None;
            }
            let key = rest.strip_suffix(':')?;
            let mut chars = key.chars();
            let starts_upper = chars.next().is_some_and(|c| c.is_ascii_uppercase());
            (starts_upper && chars.all(|c| c.is_ascii_alphanumeric())).then_some(key)
        })
        .collect()
}

/// FSM rows under the top-level `transitions:` key: (trigger, from, to).
/// The section ends at the next zero-indent line (blank, comment or key).
fn transition_rows() -> Vec<[&'static str; 3]> {
    let start = contract_marker_line(CONTRACT_YAML, "transitions:");
    let mut rows = Vec::new();
    let (mut trigger, mut from, mut to) = ("", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - trigger: ") {
            if !trigger.is_empty() {
                rows.push([trigger, from, to]);
            }
            (trigger, from, to) = (value.trim(), "", "");
        } else if let Some(value) = line.strip_prefix("    from: ") {
            from = value.trim();
        } else if let Some(value) = line.strip_prefix("    to: ") {
            to = value.trim();
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !trigger.is_empty() {
        rows.push([trigger, from, to]);
    }
    rows
}

/// Slice from `start_marker` to the next `end_marker` (exclusive). Panics
/// when the contract loses a pinned section entirely.
fn section_between<'a>(yaml: &'a str, start_marker: &str, end_marker: &str) -> &'a str {
    let start = yaml
        .find(start_marker)
        .unwrap_or_else(|| panic!("contract section missing: {start_marker}"));
    let tail = &yaml[start..];
    let end = tail.find(end_marker).unwrap_or(tail.len());
    &tail[..end]
}

/// Two-space-indented scalar inside a section slice; inline comments are
/// cut, surrounding quotes stripped.
fn section_scalar<'a>(section: &'a str, key: &str) -> &'a str {
    let marker = format!("  {key}:");
    section
        .lines()
        .find_map(|line| line.strip_prefix(marker.as_str()))
        .unwrap_or_else(|| panic!("section key {key} missing"))
        .split('#')
        .next()
        .unwrap_or_default()
        .trim()
        .trim_matches('"')
}

/// Items of the two-space inline `[a, b]` list under `key` in a section.
fn section_inline_items<'a>(section: &'a str, key: &str) -> Vec<&'a str> {
    let marker = format!("  {key}:");
    let line = section
        .lines()
        .find(|line| line.starts_with(marker.as_str()))
        .unwrap_or_else(|| panic!("section key {key} missing"));
    inline_bracket_items(line)
}

#[test]
fn contract_embeds_as_data_and_pins_schema_identity() {
    assert!(!CONTRACT_YAML.is_empty(), "contract failed to embed");
    assert!(
        CONTRACT_YAML.contains("schema_version: law-nexus-pending-effects-contract/v1"),
        "contract schema identity drifted"
    );
    assert!(!REGISTRY_YAML.is_empty(), "registry failed to embed");
}

#[test]
fn contract_lifecycle_stays_proposed_and_non_authoritative() {
    assert!(CONTRACT_YAML.contains("lifecycle: \"[proposed]\""));
    assert!(CONTRACT_YAML.contains("authoritative: false"));
    // Authority-laundering guards, scoped to the header block: body
    // comments may legitimately discuss bounded promotion; the authority
    // rows themselves may never carry it.
    let header = header_block();
    assert!(!header.contains("authoritative: true"));
    assert!(!header.contains("[bounded]"));
}

#[test]
fn header_points_at_owner_adr_and_the_registry_op_source() {
    assert!(CONTRACT_YAML.contains("owner_adr: ADR-0017"));
    assert!(CONTRACT_YAML.contains("force_overlay_adr: ADR-0018"));
    assert!(
        inline_bracket_items(top_level_row("related_adr:")).contains(&"ADR-0021"),
        "ADR-0021 lost from related_adr"
    );
    assert!(
        top_level_row("op_source:").contains("operation-registry.yaml#families.OP-P"),
        "op_source no longer points at the registry OP-P family"
    );
}

#[test]
fn selector_modes_stay_character_identical_to_the_registry_canon() {
    // Two embeds, zero restated lists (MEM951): both sides are extracted
    // from the tracked YAML files; the mode canon lives only in the
    // operation registry.
    let contract_modes = top_level_dash_items(CONTRACT_YAML, "selector_modes:");
    let registry_modes = top_level_dash_items(REGISTRY_YAML, "effect_selector_modes:");
    assert_eq!(
        contract_modes.len(),
        SELECTOR_MODE_COUNT,
        "mode count drifted"
    );
    assert_eq!(
        registry_modes.len(),
        SELECTOR_MODE_COUNT,
        "registry mode count drifted"
    );
    assert_eq!(
        contract_modes, registry_modes,
        "selector modes diverged from the registry canon"
    );
    // review-26 P0-4 / D252: parsed-item absence, not a raw substring —
    // the folded scalar and non_claims legitimately name ForRelationsAfter.
    assert!(
        !contract_modes.contains(&"ForRelationsAfter"),
        "ForRelationsAfter is a TransitionPredicate, never a selector mode"
    );
}

#[test]
fn for_relations_after_stays_a_transition_predicate_pointer_not_a_mode() {
    // review-26 P0-4 / D252: this contract copies selector_modes only; the
    // living transition_predicates 1-set stays in the registry. MEM951: no
    // second canon here — length plus identity with the registry extract,
    // never the predicate name restated in this suite.
    let scalar = top_level_row("for_relations_after_is_transition_predicate:");
    let collapsed = scalar.split_whitespace().collect::<Vec<_>>().join(" ");
    for phrase in [
        "ForRelationsAfter is a TransitionPredicate",
        "not a selector mode",
        "operation-registry.yaml transition_predicates",
        "this contract copies selector_modes only",
    ] {
        assert!(
            collapsed.contains(phrase),
            "for_relations_after_is_transition_predicate lost the phrase `{phrase}`"
        );
    }
    let registry_predicates = top_level_dash_items(REGISTRY_YAML, "transition_predicates:");
    assert_eq!(
        registry_predicates.len(),
        1,
        "registry transition_predicates must stay exactly a 1-set"
    );
    let contract_modes = top_level_dash_items(CONTRACT_YAML, "selector_modes:");
    for predicate in &registry_predicates {
        assert!(
            !contract_modes.contains(predicate),
            "the transition predicate {predicate} must never appear as a selector mode"
        );
    }
}

#[test]
fn op_p_names_stay_character_identical_to_the_registry_family_keys() {
    // Compare-extracted only (MEM951): the OP-P name canon lives in
    // families.OP-P of the registry, never restated here as a list.
    let contract_names = inline_bracket_items(top_level_row("op_p_names:"));
    let registry_names = registry_op_p_names();
    assert_eq!(
        contract_names.len(),
        OP_P_NAME_COUNT,
        "OP-P name count drifted"
    );
    assert_eq!(
        registry_names.len(),
        OP_P_NAME_COUNT,
        "registry OP-P family key count drifted"
    );
    assert_eq!(
        contract_names, registry_names,
        "OP-P names diverged from the registry canon"
    );
}

#[test]
fn dag_edges_are_the_closed_five_set_in_canon_order() {
    // This contract owns the DAG-edge canon, so the closed set is pinned
    // here, not compared against a second file.
    let edges = top_level_dash_items(CONTRACT_YAML, "dag_edges:");
    assert_eq!(edges.len(), 5, "DAG edge count drifted");
    assert_eq!(
        edges,
        vec![
            "depends_on",
            "targets_base_version",
            "supersedes",
            "cancels",
            "modifies_pending_effect"
        ],
        "closed DAG edge set drifted"
    );
}

#[test]
fn states_are_the_closed_four_set_without_a_modified_state() {
    let states = top_level_dash_items(CONTRACT_YAML, "states:");
    assert_eq!(states.len(), 4, "state count drifted");
    assert_eq!(
        states,
        vec!["scheduled", "cancelled", "applied", "unknown"],
        "closed state set drifted"
    );
    // Parsed-list absence, not a substring: the contract's own comments
    // legitimately say `modified` while explaining why it is not a state.
    assert!(
        !states.contains(&"modified"),
        "a `modified` state must never exist; ModifyPendingEffect is a transition, not a state"
    );
}

#[test]
fn two_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["PendingEffect", "ProspectiveVersion"],
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
            "PendingEffect",
            &[
                "pending_id",
                "authorized_effect",
                "effect_selector",
                "expected_base_version",
                "state",
                "evidence_span",
            ],
        ),
        (
            "ProspectiveVersion",
            &[
                "component_id",
                "text_version",
                "force_status",
                "as_of",
                "pending_effect_ids",
            ],
        ),
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
fn typed_non_success_is_the_closed_eight_set_without_failure_laundering() {
    let failures = top_level_dash_items(CONTRACT_YAML, "typed_non_success:");
    assert_eq!(
        failures,
        TYPED_NON_SUCCESS.to_vec(),
        "closed non-success set drifted"
    );
    for token in NON_FAILURE_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is a success, a force state or a neighbor token, never a pending-effect failure"
        );
    }
}

#[test]
fn per_entity_typed_non_success_stays_inside_the_closed_set() {
    // Parsed-item checks, not raw substrings: `applied` is a legal state
    // and section comments legitimately name exclusions (MEM951).
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
fn transitions_are_the_closed_four_fsm_rows() {
    let rows = transition_rows();
    assert_eq!(rows.len(), 4, "transition count drifted");
    assert_eq!(rows[0], ["ScheduleEffect", "none", "scheduled"]);
    assert_eq!(rows[1], ["ModifyPendingEffect", "scheduled", "scheduled"]);
    assert_eq!(rows[2], ["CancelPendingEffect", "scheduled", "cancelled"]);
    // selector_satisfied is the checkout fold, never an OP-P operation.
    assert_eq!(rows[3], ["selector_satisfied", "scheduled", "applied"]);
}

#[test]
fn modifies_pending_effect_edge_stays_distinct_from_the_operation() {
    let section = section_between(CONTRACT_YAML, "modifies_pending_effect:", "checkout:");
    assert_eq!(
        section_scalar(section, "kind"),
        "dag_edge",
        "modifies_pending_effect must stay a DAG edge kind"
    );
    assert_eq!(
        section_scalar(section, "distinct_from_op"),
        "ModifyPendingEffect",
        "the DAG edge and the OP-P operation must stay distinct"
    );
    assert_eq!(
        section_scalar(section, "target_state"),
        "scheduled",
        "the edge may only target a still-scheduled pending effect"
    );
    let never_targets = section_inline_items(section, "never_targets");
    assert!(
        never_targets.contains(&"applied") && never_targets.contains(&"cancelled"),
        "never_targets must contain applied and cancelled"
    );
}

#[test]
fn non_claims_carry_the_boundary_disclaimers() {
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    let has_claim = |needle: &str| claims.iter().any(|claim| claim.contains(needle));
    assert!(
        has_claim("ProspectiveVersion is not PendingEffect"),
        "Prospective-vs-Pending non-claim lost"
    );
    assert!(
        has_claim("modifies_pending_effect is not ModifyPendingEffect"),
        "DAG-edge-vs-operation non-claim lost"
    );
    assert!(
        has_claim("excluded_future is not Suspended"),
        "excluded_future-vs-Suspended non-claim lost"
    );
    assert!(
        has_claim("Review Case"),
        "Review Case homonymy non-claim lost"
    );
    assert!(
        has_claim("not a sixth clock"),
        "no-sixth-clock non-claim lost"
    );
    assert!(
        has_claim("Not a TransitionConstraint"),
        "not-TransitionConstraint non-claim lost"
    );
    // review-26 P0-4 / D252 boundary needles: the selector split, the
    // guard reading of OnCondition and the fail-closed TriggerUnknown
    // outcome stay prose in non_claims.
    assert!(
        has_claim("ForRelationsAfter"),
        "ForRelationsAfter TransitionPredicate non-claim lost"
    );
    assert!(
        has_claim("TransitionPredicate"),
        "TransitionPredicate boundary non-claim lost"
    );
    assert!(
        has_claim("OnCondition is a guard"),
        "OnCondition-as-guard non-claim lost"
    );
    assert!(
        has_claim("TriggerUnknown"),
        "TriggerUnknown fail-closed non-claim lost"
    );
    assert!(
        has_claim("preconditions live in operation-registry.yaml, not duplicated"),
        "OP-P precondition ownership non-claim lost"
    );
}

#[test]
fn neighbor_contract_tokens_never_mint_entity_keys() {
    // MEM947: raw-token isolation excludes the non_claims section — the
    // boundary prose there may legitimately name neighbor tokens.
    let body = contract_without_non_claims();
    assert!(
        !body.contains("identity_ambulatory"),
        "S02 reference-binding token leaked into the contract body"
    );
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in [
        "CausalEdge",
        "Modified",
        "ModifyPendingEffect",
        "ScheduleEffect",
        "ReplaceText",
        "Suspend",
        "ReferenceMention",
        "ActivationTrigger",
        "TransitionPredicate",
    ] {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !CONTRACT_YAML.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected"
        );
    }
}

#[test]
fn runtime_today_stays_design_only_for_both_entities() {
    let blocks = entity_blocks(CONTRACT_YAML);
    for name in ["PendingEffect", "ProspectiveVersion"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            RUNTIME_TODAY_VALUE,
            "{name} must stay design-only"
        );
    }
}

#[test]
fn prospective_force_status_seed_never_contains_in_force() {
    // Parsed items, not substrings: NotYetInForce legitimately contains the
    // InForce spelling; only an exact InForce seed item is forbidden
    // (MC-SEED: never automatic InForce).
    let blocks = entity_blocks(CONTRACT_YAML);
    let seed = inline_bracket_items(entity_scalar(
        block_of(&blocks, "ProspectiveVersion"),
        "force_status_seed",
    ));
    assert!(
        seed.contains(&"NotYetInForce") && seed.contains(&"Unknown"),
        "force_status_seed lost NotYetInForce or Unknown"
    );
    assert!(
        !seed.contains(&"InForce"),
        "InForce must never be an automatic seed (MC-SEED)"
    );
}
