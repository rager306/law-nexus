//! D222 pin-suite for the E.2.1 operation registry (design-doc-as-data).
//!
//! `prd/architecture/operation-registry.yaml` is embedded via `include_str!`
//! and pinned with plain text/section assertions, mirroring the
//! `refers_to_listed_after_cites_in_yaml_vocabulary` pattern of
//! `cross_act_edges.rs`. Per D222/MEM938/MEM939 the registry carries neither
//! `rust_path` nor `rust_enum`: it is not a `closed_vocabularies` row and is
//! not parsed by `OntologyCatalog`, so no YAML crate is added here either.
//!
//! This suite deliberately contains no `use` items at all: it imports neither
//! `ln_kb_ontology` nor `ln_temporal`, and never references the runtime
//! industrial-op enum in code (grep-pinned in slice Verify). Coupling the pin
//! suite to the runtime type it guards would invert the D222 boundary.
//!
//! Negative surface (Q7): deleting a G0 name, dropping a required field,
//! emptying `typed_failures`, claiming `Applied` as a failure, minting a
//! `Merge:` G0 key, promoting lifecycle beyond `[proposed]`, flipping
//! `authoritative`, widening `runtime_today`, leaking S02 binding tokens
//! (`identity_ambulatory`, `reference_binding_vocabulary`, `cites` /
//! `IdentityAmbulatory` as keys), returning a seventh selector mode
//! (`ForRelationsAfter`) or review-26 rename tokens (`AtInstant`,
//! `AfterOfficialPublication`, `OnLegalEvent`, `RetroactiveFrom`) into the
//! parsed modes, minting two-space `ActivationTrigger:` /
//! `TransitionPredicate:` YAML entity keys, laundering `TriggerUnknown`
//! into `apply_results` or `effect_selector_modes`, widening
//! `transition_predicates` beyond one, or adding P2 ApplicabilityPredicate
//! DSL names to it all turn pins red on the tracked file itself — no tmp
//! fixtures, no runtime dependency.

/// Embedded registry, same lift as `kb-ontology.yaml` in `catalog.rs`.
/// Path is relative to `crates/ln-kb-ontology/tests/`.
const REGISTRY_YAML: &str = include_str!("../../../prd/architecture/operation-registry.yaml");

/// Five G0 families with their 29 reserved operation names, in declaration
/// order (ADR-0017 G0(g) / review-25 E.2.1 / MC-OPS).
const FAMILIES: &[(&str, &[&str])] = &[
    (
        "OP-T",
        &[
            "ReplaceText",
            "InsertText",
            "DeleteText",
            "SubstituteRange",
            "CorrectText",
        ],
    ),
    (
        "OP-S",
        &[
            "Attach",
            "Detach",
            "Move",
            "Renumber",
            "Redesignate",
            "Split",
            "Join",
            "ReplaceStructure",
            "ReserveDesignation",
        ],
    ),
    (
        "OP-F",
        &[
            "Commence",
            "Suspend",
            "Resume",
            "Repeal",
            "Expire",
            "Invalidate",
            "Restore",
        ],
    ),
    (
        "OP-P",
        &[
            "ScheduleEffect",
            "ModifyPendingEffect",
            "CancelPendingEffect",
        ],
    ),
    (
        "OP-L",
        &[
            "InsertEntry",
            "DeleteEntry",
            "SplitEntry",
            "MergeEntries",
            "ReclassifyEntry",
        ],
    ),
];

/// Closed 9-result apply set (ADR-0017 G0(g) / MC-RES), canonical order.
const APPLY_RESULTS: [&str; 9] = [
    "Applied",
    "TargetNotFound",
    "AmbiguousTarget",
    "PreconditionMismatch",
    "BaseVersionMismatch",
    "OrderingConflict",
    "UnknownEffect",
    "UnsupportedOperation",
    "IncompleteSource",
];

/// Closed 8-field per-operation contract (ADR-0017 G0(g)).
const REQUIRED_FIELDS: [&str; 8] = [
    "target_selector",
    "expected_base_version",
    "precondition",
    "payload",
    "effect_selector",
    "scope",
    "postcondition",
    "evidence_span",
];

/// Closed runtime-contour vocabulary accepted for `runtime_today`.
const RUNTIME_TODAY_VALUES: [&str; 3] = ["none", "industrial_spine", "membership_graph"];

struct OperationBlock {
    name: String,
    body: String,
}

fn all_operation_names() -> Vec<&'static str> {
    FAMILIES
        .iter()
        .flat_map(|(_, operations)| operations.iter().copied())
        .collect()
}

/// Line indices of six-space-indented PascalCase-colon lines — exactly the
/// shape of an operation entry under `families.*.operations`. Deeper
/// (eight-space field) lines, family headers and prose continuations never
/// match, so a stray `Merge:` key at operation depth would be caught here.
fn operation_key_line_indices(yaml: &str) -> Vec<usize> {
    yaml.lines()
        .enumerate()
        .filter_map(|(index, line)| {
            let rest = line.strip_prefix("      ")?;
            if rest.starts_with(' ') {
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

/// Operation blocks: from each operation key line to just before the next
/// operation key line (or EOF). Bodies may span into the next family header;
/// every assertion below is anchored on exact keys or exact values, so the
/// over-approximation cannot mask an absence pin.
fn operation_blocks(yaml: &str) -> Vec<OperationBlock> {
    let key_lines = operation_key_line_indices(yaml);
    let lines: Vec<&str> = yaml.lines().collect();
    key_lines
        .iter()
        .enumerate()
        .map(|(position, &start)| {
            let end = key_lines.get(position + 1).copied().unwrap_or(lines.len());
            OperationBlock {
                name: lines[start].trim().trim_end_matches(':').to_owned(),
                body: lines[start + 1..end].join("\n"),
            }
        })
        .collect()
}

fn block_of<'a>(blocks: &'a [OperationBlock], name: &str) -> &'a OperationBlock {
    blocks
        .iter()
        .find(|block| block.name == name)
        .unwrap_or_else(|| panic!("operation block missing: {name}"))
}

fn dash_items(section: &str) -> Vec<&str> {
    section
        .lines()
        .filter_map(|line| line.trim().strip_prefix("- "))
        .map(str::trim)
        .collect()
}

/// Slice from `start_marker` to the next `end_marker` (exclusive). Panics
/// when the registry loses a pinned closed-vocabulary section entirely.
fn section_between<'a>(yaml: &'a str, start_marker: &str, end_marker: &str) -> &'a str {
    let start = yaml
        .find(start_marker)
        .unwrap_or_else(|| panic!("registry section missing: {start_marker}"));
    let tail = &yaml[start..];
    let end = tail.find(end_marker).unwrap_or(tail.len());
    &tail[..end]
}

fn family_keys(yaml: &str) -> Vec<&str> {
    let families_line = yaml
        .lines()
        .position(|line| line == "families:")
        .expect("families section missing");
    yaml.lines()
        .skip(families_line + 1)
        .filter_map(|line| {
            let rest = line.strip_prefix("  ")?;
            if rest.starts_with(' ') {
                return None;
            }
            rest.strip_suffix(':')
        })
        .collect()
}

fn scalar_field<'a>(block: &'a str, field: &str, operation: &str) -> &'a str {
    let marker = format!("{field}:");
    block
        .lines()
        .find_map(|line| {
            let content = line.trim_start();
            content
                .starts_with(&marker)
                .then(|| content[marker.len()..].trim())
        })
        .unwrap_or_else(|| panic!("{operation}: required field {field} missing"))
        .trim_matches('"')
}

fn has_scalar_field(block: &str, field: &str) -> bool {
    let marker = format!("{field}:");
    block
        .lines()
        .any(|line| line.trim_start().starts_with(&marker))
}

fn typed_failures<'a>(block: &'a str, operation: &str) -> Vec<&'a str> {
    let raw = scalar_field(block, "typed_failures", operation);
    let inner = raw
        .strip_prefix('[')
        .and_then(|value| value.strip_suffix(']'))
        .unwrap_or_else(|| panic!("{operation}: typed_failures is not an inline list"));
    inner
        .split(',')
        .map(str::trim)
        .filter(|item| !item.is_empty())
        .collect()
}

#[test]
fn registry_embeds_as_data_and_declares_schema_identity() {
    assert!(!REGISTRY_YAML.is_empty(), "registry failed to embed");
    assert!(REGISTRY_YAML.contains("schema_version: law-nexus-operation-registry/v1"));
    assert!(REGISTRY_YAML.contains("owner_adr: ADR-0017"));
    assert!(REGISTRY_YAML.contains("force_overlay_adr: ADR-0018"));
}

#[test]
fn registry_lifecycle_stays_proposed_and_non_authoritative() {
    assert!(REGISTRY_YAML.contains("lifecycle: \"[proposed]\""));
    assert!(REGISTRY_YAML.contains("authoritative: false"));
    // Authority-laundering guards: promotion of the design registry to
    // runtime authority must break this pin before any consumer exists.
    assert!(!REGISTRY_YAML.contains("authoritative: true"));
    assert!(!REGISTRY_YAML.contains("[bounded]"));
}

#[test]
fn all_twenty_nine_g0_operations_are_declared_exactly_once() {
    let blocks = operation_blocks(REGISTRY_YAML);
    let mut declared: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    let mut expected = all_operation_names();
    assert_eq!(declared.len(), 29, "expected exactly 29 G0 operation keys");
    declared.sort_unstable();
    expected.sort_unstable();
    assert_eq!(declared, expected, "G0 operation key set drifted");
}

#[test]
fn families_are_the_closed_five_family_set() {
    assert_eq!(
        family_keys(REGISTRY_YAML),
        vec!["OP-T", "OP-S", "OP-F", "OP-P", "OP-L"]
    );
}

#[test]
fn apply_results_are_the_closed_nine_result_set_in_canon_order() {
    let section = section_between(REGISTRY_YAML, "apply_results:", "effect_selector_modes:");
    assert_eq!(dash_items(section), APPLY_RESULTS.to_vec());
}

#[test]
fn effect_selector_modes_are_the_closed_six_mode_set_without_for_relations_after() {
    // review-26 P0-4 / D252: the mode list drops ForRelationsAfter (it is a
    // TransitionPredicate, see below). The end marker is the new neighbor
    // key `transition_predicates:`, not `required_fields:` — without the
    // shift, dash_items would swallow RelationsArisingOnOrAfter as a
    // seventh mode (MEM1044).
    let section = section_between(
        REGISTRY_YAML,
        "effect_selector_modes:",
        "transition_predicates:",
    );
    let modes = dash_items(section);
    assert_eq!(
        modes,
        vec![
            "At",
            "AfterPublication",
            "OnEvent",
            "OnCondition",
            "RetroactiveTo",
            "Unknown"
        ]
    );
    // Parsed-item absences, not raw substrings (MEM951): the folded
    // scalars and non_claims legitimately name ForRelationsAfter after
    // review-26 P0-4, and the registry comment names the review-26
    // renames as non-living — only parsed modes must stay clean.
    assert!(
        !modes.contains(&"ForRelationsAfter"),
        "ForRelationsAfter is a TransitionPredicate, never a selector mode"
    );
    for token in [
        "AtInstant",
        "AfterOfficialPublication",
        "OnLegalEvent",
        "RetroactiveFrom",
    ] {
        assert!(
            !modes.contains(&token),
            "review-26 rename token {token} must not become a living mode name"
        );
    }
}

#[test]
fn transition_predicates_are_the_closed_one_set_relations_arising_on_or_after() {
    // review-26 P0-4 / D252: applicability-plane predicates live in their
    // own 1-set between the mode list and the folded scalars; the end
    // marker is the first folded scalar, not `required_fields:`.
    let section = section_between(
        REGISTRY_YAML,
        "transition_predicates:",
        "on_condition_is_a_guard:",
    );
    let predicates = dash_items(section);
    assert_eq!(
        predicates,
        vec!["RelationsArisingOnOrAfter"],
        "transition_predicates must stay exactly the 1-set"
    );
    // ForRelationsAfter is the extracted old name, never a member; the
    // P2 ApplicabilityPredicate DSL names are not members either.
    for token in [
        "ForRelationsAfter",
        "NoticePublishedOnOrAfter",
        "InvitationSentOnOrAfter",
        "ContractConcludedBefore",
        "PreserveOldRuleForOngoingProcedure",
        "And",
        "Or",
        "Not",
    ] {
        assert!(
            !predicates.contains(&token),
            "{token} must not join the transition_predicates set"
        );
    }
}

#[test]
fn on_condition_is_a_guard_and_unknown_is_trigger_unknown_not_false() {
    // review-26 P0-4 / D252 folded scalars, pinned like the S02
    // `superseded_is_version_relation` property (force_interval_set.rs):
    // whitespace-collapsed phrases, never parsed as entity keys and never
    // restated as a second list.
    let guard = section_between(
        REGISTRY_YAML,
        "on_condition_is_a_guard:",
        "unknown_condition_is_trigger_unknown_not_false:",
    );
    let collapsed = guard.split_whitespace().collect::<Vec<_>>().join(" ");
    for phrase in [
        "OnCondition is a guard",
        "not a clock",
        "not a sixth clock role",
    ] {
        assert!(
            collapsed.contains(phrase),
            "on_condition_is_a_guard lost the phrase `{phrase}`"
        );
    }
    let trigger_unknown = section_between(
        REGISTRY_YAML,
        "unknown_condition_is_trigger_unknown_not_false:",
        "required_fields:",
    );
    let collapsed = trigger_unknown
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ");
    for phrase in [
        "yields TriggerUnknown",
        "never false",
        "never a 7th selector mode",
        "never a 10th apply_result",
        "not crystal INV-15",
        "not an unknown trigger",
    ] {
        assert!(
            collapsed.contains(phrase),
            "unknown_condition_is_trigger_unknown_not_false lost the phrase `{phrase}`"
        );
    }
    // Fail-closed guards: TriggerUnknown is a prose fail-closed outcome,
    // never laundered into the two closed sets (Q7).
    let results = dash_items(section_between(
        REGISTRY_YAML,
        "apply_results:",
        "effect_selector_modes:",
    ));
    assert!(
        !results.contains(&"TriggerUnknown"),
        "TriggerUnknown must never become a 10th apply_result"
    );
    let modes = dash_items(section_between(
        REGISTRY_YAML,
        "effect_selector_modes:",
        "transition_predicates:",
    ));
    assert!(
        !modes.contains(&"TriggerUnknown"),
        "TriggerUnknown must never become a selector mode"
    );
    // The two review-26 planes stay prose, never YAML entity-depth keys.
    for key in ["ActivationTrigger", "TransitionPredicate"] {
        assert!(
            !REGISTRY_YAML.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected"
        );
    }
}

#[test]
fn required_fields_section_is_the_closed_eight_field_set() {
    let section = section_between(REGISTRY_YAML, "required_fields:", "industrial_spine_kinds:");
    assert_eq!(dash_items(section), REQUIRED_FIELDS.to_vec());
}

#[test]
fn industrial_spine_kinds_stay_the_lowercase_runtime_four_set() {
    let section = section_between(REGISTRY_YAML, "industrial_spine_kinds:", "name_mapping:");
    assert_eq!(
        dash_items(section),
        vec!["renumber", "move", "split", "merge"]
    );
}

#[test]
fn every_operation_carries_all_eight_required_fields_plus_typed_failures() {
    for block in operation_blocks(REGISTRY_YAML) {
        for field in REQUIRED_FIELDS {
            assert!(
                has_scalar_field(&block.body, field),
                "{}: missing required field {field}",
                block.name
            );
        }
        assert!(
            has_scalar_field(&block.body, "typed_failures"),
            "{}: missing typed_failures",
            block.name
        );
        assert!(
            has_scalar_field(&block.body, "runtime_today"),
            "{}: missing runtime_today",
            block.name
        );
    }
}

#[test]
fn typed_failures_stay_fail_closed_subsets_of_the_nine_results() {
    for block in operation_blocks(REGISTRY_YAML) {
        let failures = typed_failures(&block.body, &block.name);
        assert!(
            !failures.is_empty(),
            "{}: typed_failures must be non-empty (fail-closed)",
            block.name
        );
        assert!(
            !failures.contains(&"Applied"),
            "{}: Applied is success, never a typed failure",
            block.name
        );
        for failure in &failures {
            assert!(
                APPLY_RESULTS.contains(failure),
                "{}: unknown typed failure {failure}",
                block.name
            );
        }
    }
}

#[test]
fn merge_is_never_a_g0_operation_key_while_lowercase_merge_stays_industrial() {
    assert!(
        !all_operation_names().contains(&"Merge"),
        "Merge must not be minted as a G0 operation key (D222)"
    );
    assert!(
        !REGISTRY_YAML.contains("\n      Merge:"),
        "six-space `Merge:` operation key detected"
    );
    let section = section_between(REGISTRY_YAML, "industrial_spine_kinds:", "name_mapping:");
    assert!(
        dash_items(section).contains(&"merge"),
        "lowercase industrial merge kind lost from industrial_spine_kinds"
    );
}

#[test]
fn join_and_merge_entries_remain_distinct_reserved_operations() {
    let names = all_operation_names();
    assert!(names.contains(&"Join"), "G0 Join missing");
    assert!(names.contains(&"MergeEntries"), "G0 MergeEntries missing");
    assert!(REGISTRY_YAML.contains("\n      Join:"));
    assert!(REGISTRY_YAML.contains("\n      MergeEntries:"));
}

#[test]
fn s02_reference_binding_tokens_do_not_leak_into_the_registry() {
    // Underscore-form S02 tokens are wholly absent (hard absence pins).
    assert!(!REGISTRY_YAML.contains("identity_ambulatory"));
    assert!(!REGISTRY_YAML.contains("reference_binding_vocabulary"));
    // cites / IdentityAmbulatory may only appear inside the non_claims
    // disclaimer prose — never as operation or family keys.
    let names = all_operation_names();
    assert!(!names.contains(&"Cites"));
    assert!(!names.contains(&"IdentityAmbulatory"));
    assert!(!REGISTRY_YAML.contains("cites:"));
    assert!(!REGISTRY_YAML.contains("IdentityAmbulatory:"));
    let families = family_keys(REGISTRY_YAML);
    assert!(families.iter().all(|family| *family != "Cites"));
    let claims = dash_items(section_between(REGISTRY_YAML, "non_claims:", "families:"));
    assert!(
        claims
            .iter()
            .any(|claim| claim.contains("not operation ids")),
        "cites/IdentityAmbulatory disclaimer lost from non_claims"
    );
}

#[test]
fn runtime_today_is_a_closed_three_value_vocabulary() {
    for block in operation_blocks(REGISTRY_YAML) {
        let value = scalar_field(&block.body, "runtime_today", &block.name);
        assert!(
            RUNTIME_TODAY_VALUES.contains(&value),
            "{}: runtime_today {value:?} outside the closed set",
            block.name
        );
    }
}

#[test]
fn runtime_today_mapping_matches_the_load_bearing_name_map() {
    let blocks = operation_blocks(REGISTRY_YAML);
    for name in ["Move", "Renumber", "Split"] {
        let block = block_of(&blocks, name);
        assert_eq!(
            scalar_field(&block.body, "runtime_today", name),
            "industrial_spine",
            "{name} must stay on the industrial spine contour"
        );
    }
    assert_eq!(
        scalar_field(&block_of(&blocks, "Attach").body, "runtime_today", "Attach"),
        "membership_graph",
        "Attach must stay on the membership-graph contour"
    );
    for name in [
        "Detach",
        "Join",
        "MergeEntries",
        "Repeal",
        "CorrectText",
        "ReserveDesignation",
    ] {
        let block = block_of(&blocks, name);
        assert_eq!(
            scalar_field(&block.body, "runtime_today", name),
            "none",
            "{name} must stay design-only"
        );
    }
}

#[test]
fn name_mapping_section_pins_the_runtime_contours_verbatim() {
    assert!(REGISTRY_YAML.contains("industrial_spine: [Move, Renumber, Split]"));
    assert!(REGISTRY_YAML.contains("membership_graph: [Attach]"));
}

#[test]
fn boundary_and_non_claims_keep_the_registry_design_only() {
    assert!(REGISTRY_YAML.contains("Not a Rust enum"));
    assert!(REGISTRY_YAML.contains("not apply_industrial_op"));
    let claims = dash_items(section_between(REGISTRY_YAML, "non_claims:", "families:"));
    assert!(
        claims.iter().any(|claim| claim.contains("No Rust types")),
        "no-Rust-types non-claim lost"
    );
    assert!(
        claims
            .iter()
            .any(|claim| claim.contains("not G0 Join and not MergeEntries")),
        "industrial-merge vs Join/MergeEntries disclaimer lost"
    );
    // review-26 P0-4 / D252 boundary needles: the selector split and its
    // fail-closed outcome stay design-only prose in non_claims.
    assert!(
        claims
            .iter()
            .any(|claim| claim.contains("TransitionPredicate")),
        "TransitionPredicate boundary non-claim lost"
    );
    assert!(
        claims
            .iter()
            .any(|claim| claim.contains("OnCondition is a guard")),
        "OnCondition-as-guard non-claim lost"
    );
    assert!(
        claims.iter().any(|claim| claim.contains("TriggerUnknown")),
        "TriggerUnknown fail-closed non-claim lost"
    );
}
