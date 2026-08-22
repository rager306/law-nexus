//! D222/D229 pin-suite for the E.2.4 force interval set contract
//! (design-doc-as-data).
//!
//! `prd/architecture/force-interval-set-contract.yaml` (owner: ADR-0018
//! G0(b)/G0(c); ADR-0017 operation names and ADR-0021 transitional
//! relations are related, never owners) is embedded via `include_str!` and
//! pinned with plain text/section assertions, mirroring
//! `pending_effects.rs` (E.2.3), `reference_binding.rs` (E.2.2) and
//! `operation_registry.rs` (E.2.1). Per D222/MEM938/MEM939 the contract
//! carries neither `rust_path` nor `rust_enum`, is not a
//! `closed_vocabularies` row and is not parsed by `OntologyCatalog`, so
//! this suite stays parser-free string/section work over two embedded YAML
//! files and adds no YAML crate dependency.
//!
//! Token alignment (7 OP-F names x one shared typed_failures list) is
//! checked against the embedded `operation-registry.yaml`: the name and
//! failure canon lives only in `families.OP-F`. This suite extracts both
//! sides and compares; it never restates that canon as a second list
//! (MEM951). The written-status seven-set and the opens/closes transition
//! algebra are owned by this contract itself (D229) and are pinned here
//! directly, the way `pending_effects.rs` pins its own closed sets.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor `ln_temporal`, and never references
//! `ForceInterval`, `NormativeState`, `ForceStatusEvent` or
//! `CtvIndustrialOpKind` as code identifiers (grep-pinned in slice
//! Verify). Coupling the pin suite to the runtime types it guards would
//! invert the D222 boundary; status/operation homonymy stays prose in the
//! YAML non_claims.
//!
//! Negative surface (Q7): minting an eighth OP-F name, an eighth written
//! status, `Unknown`/`Transitional` inside `written_statuses`, a third
//! entity key, widening `typed_non_success` with `UnknownEffect` or any
//! success/force/neighbor token, promoting lifecycle beyond `[proposed]`,
//! flipping `authoritative`, moving ownership away from ADR-0018,
//! collapsing Resume into Restore, `runtime_today` beyond `none`, or
//! dropping a required field all turn pins red on the tracked file itself
//! — no tmp fixtures, no runtime dependency. Absence pins over
//! `written_statuses` and `typed_non_success` run on parsed items, not
//! raw substrings, because the contract's own comments, sections and
//! non_claims legitimately name `Unknown`, `Transitional` and `Suspended`
//! (MEM951).

/// Embedded contract (T01): the E.2.4 force interval / interval-set layer.
/// Path is relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str =
    include_str!("../../../prd/architecture/force-interval-set-contract.yaml");

/// Embedded name and failure canon: the seven OP-F operation names and
/// their shared `typed_failures` list must stay character-identical to
/// `families.OP-F` of the operation registry.
const REGISTRY_YAML: &str = include_str!("../../../prd/architecture/operation-registry.yaml");

/// Closed canon sizes pinned inside the comparing tests (MEM951: sizes and
/// cross-file equality only, never a restated OP-F token list).
const OP_F_NAME_COUNT: usize = 7;
const WRITTEN_STATUS_COUNT: usize = 7;
const TRANSITION_COUNT: usize = 7;

/// Closed written-status seven-set (ADR-0018 G0(c)), canonical order. This
/// contract owns the canon, so the set is pinned here, not compared
/// against a second file; the runtime NormativeState six-set
/// (kb-ontology.yaml force_status_values) is a different vocabulary.
const WRITTEN_STATUSES: [&str; 7] = [
    "InForce",
    "NotYetInForce",
    "Suspended",
    "Repealed",
    "Superseded",
    "Expired",
    "Invalidated",
];

/// Successes, statuses, point-query outcomes and neighbor-contract tokens
/// that must stay out of `typed_non_success` (parsed-item checks, not
/// substrings — MEM951). `UnknownEffect` is the lawful OP-P eighth token;
/// it never widens the OP-F interval failure set.
const NON_FAILURE_TOKENS: [&str; 7] = [
    "Applied",
    "Bound",
    "AlreadyApplied",
    "UnknownEffect",
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

/// Scalar value of a YAML row: inline comments (` # ...`) cut, trimmed.
/// The contract carries inline comments on its transition trigger rows,
/// so row pins must never compare the raw value text.
fn row_value(raw: &str) -> &str {
    raw.split('#').next().unwrap_or_default().trim()
}

/// The top-of-file authority block: everything before the first closed-set
/// key. Absence pins for `authoritative: true` / `[bounded]` / a wrong
/// `owner_adr` run here, not over the whole file, because body comments
/// may legitimately name them.
fn header_block() -> String {
    let cut = contract_marker_line(CONTRACT_YAML, "op_f_names:");
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
/// shape of an entity entry under `entities:`. Deeper field lines,
/// transition rows (dash items and their four-space continuations),
/// lowercase two-space section keys and prose continuations never match,
/// so a stray `Suspend:` or `ForceStatusEvent:` entity key would be caught
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
/// `suspend_is_not_a_status:` / `projection:` / `non_claims:`). Every
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
/// The subsection ends at the next four-space key (`typed_non_success`,
/// `in_force_members`, ...); eight-space folded-scalar continuations are
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
/// `families.OP-F` block only (`  OP-F:` up to the next `  OP-` family
/// header, which is `  OP-P:`). Scanning the whole registry would collect
/// all 29 G0 keys; the family boundary keeps the extraction at exactly
/// the E.2.4 names.
fn registry_op_f_names() -> Vec<&'static str> {
    let lines: Vec<&str> = REGISTRY_YAML.lines().collect();
    let start = lines
        .iter()
        .position(|line| *line == "  OP-F:")
        .expect("registry OP-F family missing");
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

/// `typed_failures` lists of the OP-F operations, keyed by operation name,
/// from the same bounded family block. All seven operations must carry the
/// identical closed list; this suite compares instead of restating it
/// (MEM951 — no hardcoded eighth `UnknownEffect`).
fn registry_op_f_typed_failures() -> Vec<(&'static str, Vec<&'static str>)> {
    let lines: Vec<&str> = REGISTRY_YAML.lines().collect();
    let start = lines
        .iter()
        .position(|line| *line == "  OP-F:")
        .expect("registry OP-F family missing");
    let end = lines[start + 1..]
        .iter()
        .position(|line| line.starts_with("  OP-"))
        .map(|offset| start + 1 + offset)
        .unwrap_or(lines.len());
    let mut rows = Vec::new();
    let mut current = "";
    for line in &lines[start + 1..end] {
        if let Some(value) = line.strip_prefix("        typed_failures:") {
            rows.push((current, inline_bracket_items(value)));
        } else if let Some(rest) = line.strip_prefix("      ") {
            if !rest.starts_with(' ') {
                if let Some(key) = rest.strip_suffix(':') {
                    let mut chars = key.chars();
                    let starts_upper = chars.next().is_some_and(|c| c.is_ascii_uppercase());
                    if starts_upper && chars.all(|c| c.is_ascii_alphanumeric()) {
                        current = key;
                    }
                }
            }
        }
    }
    rows
}

/// Interval rows under the top-level `transitions:` key:
/// (trigger, closes, opens). The section ends at the next zero-indent line
/// (blank separator, comment or key). Inline comments are cut so
/// `trigger: Commence  # seed` pins as `Commence`.
fn transition_rows() -> Vec<[&'static str; 3]> {
    let start = contract_marker_line(CONTRACT_YAML, "transitions:");
    let mut rows = Vec::new();
    let (mut trigger, mut closes, mut opens) = ("", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - trigger: ") {
            if !trigger.is_empty() {
                rows.push([trigger, closes, opens]);
            }
            (trigger, closes, opens) = (row_value(value), "", "");
        } else if let Some(value) = line.strip_prefix("    closes: ") {
            closes = row_value(value);
        } else if let Some(value) = line.strip_prefix("    opens: ") {
            opens = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !trigger.is_empty() {
        rows.push([trigger, closes, opens]);
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

#[test]
fn contract_embeds_as_data_and_pins_schema_identity() {
    assert!(!CONTRACT_YAML.is_empty(), "contract failed to embed");
    assert!(
        CONTRACT_YAML.contains("schema_version: law-nexus-force-interval-set-contract/v1"),
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
fn header_points_at_owner_adr_0018_and_the_registry_op_source() {
    assert!(CONTRACT_YAML.contains("owner_adr: ADR-0018"));
    let related = inline_bracket_items(top_level_row("related_adr:"));
    assert!(
        related.contains(&"ADR-0017") && related.contains(&"ADR-0021"),
        "related_adr lost ADR-0017 (operation names) or ADR-0021 (transitional relations)"
    );
    assert!(
        top_level_row("op_source:").contains("operation-registry.yaml#families.OP-F"),
        "op_source no longer points at the registry OP-F family"
    );
    // Ownership may never drift onto a related ADR: ADR-0017 owns the
    // operation names, not the interval-set contract (the related_adr row
    // legitimately names it, so the substring is header-scoped and exact).
    assert!(
        !header_block().contains("owner_adr: ADR-0017"),
        "owner_adr must stay ADR-0018; ADR-0017 is related, never owner"
    );
}

#[test]
fn op_f_names_stay_character_identical_to_the_registry_family_keys() {
    // Compare-extracted only (MEM951): the OP-F name canon lives in
    // families.OP-F of the registry, never restated here as a list.
    let contract_names = inline_bracket_items(top_level_row("op_f_names:"));
    let registry_names = registry_op_f_names();
    assert_eq!(
        contract_names.len(),
        OP_F_NAME_COUNT,
        "OP-F name count drifted"
    );
    assert_eq!(
        registry_names.len(),
        OP_F_NAME_COUNT,
        "registry OP-F family key count drifted"
    );
    assert_eq!(
        contract_names, registry_names,
        "OP-F names diverged from the registry canon"
    );
}

#[test]
fn written_statuses_are_the_closed_seven_set_without_unknown_or_transitional() {
    let statuses = top_level_dash_items(CONTRACT_YAML, "written_statuses:");
    assert_eq!(
        statuses.len(),
        WRITTEN_STATUS_COUNT,
        "written status count drifted"
    );
    assert_eq!(
        statuses,
        WRITTEN_STATUSES.to_vec(),
        "closed written-status set drifted"
    );
    // Parsed-list absence, not substrings: the contract's own comments,
    // sections and non_claims legitimately name both tokens while
    // excluding them (MEM951). Unknown is the point-query outcome;
    // Transitional is F13-T / ADR-0021 territory.
    assert!(
        !statuses.contains(&"Unknown"),
        "Unknown is the fail-closed point-query outcome, never a written status"
    );
    assert!(
        !statuses.contains(&"Transitional"),
        "Transitional is not a force interval (F13-T / ADR-0021)"
    );
}

#[test]
fn two_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["ForceInterval", "ForceIntervalSet"],
        "entity key set/order drifted"
    );
    for name in &names {
        assert_eq!(
            CONTRACT_YAML.matches(&format!("\n  {name}:")).count(),
            1,
            "{name} entity key must appear exactly once"
        );
    }
    // Entity-depth absence: statuses, S01 tokens and OP-F operation names
    // are values and prose here, never entity keys. The two-space `X:`
    // pattern cannot collide with `  - ` non_claims dash items.
    for key in [
        "ForceStatusEvent",
        "Suspended",
        "Transitional",
        "PendingEffect",
        "ProspectiveVersion",
        "ScheduleEffect",
        "Suspend",
        "Resume",
        "Restore",
        "ModifyPendingEffect",
    ] {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !CONTRACT_YAML.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected"
        );
    }
}

#[test]
fn every_entity_carries_its_required_fields() {
    let expected: &[(&str, &[&str])] = &[
        (
            "ForceInterval",
            &[
                "component_id",
                "status",
                "opened_by",
                "closed_by",
                "evidence_span",
            ],
        ),
        ("ForceIntervalSet", &["component_id", "intervals"]),
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
fn typed_non_success_matches_the_registry_op_f_failure_rows() {
    // Compare-extracted (MEM951): every OP-F operation carries the same
    // closed failure list in the registry; the contract restates it once
    // and this suite never hardcodes the tokens (no eighth UnknownEffect).
    let failures = top_level_dash_items(CONTRACT_YAML, "typed_non_success:");
    assert_eq!(failures.len(), 7, "typed non-success count drifted");

    let registry_names = registry_op_f_names();
    let registry_rows = registry_op_f_typed_failures();
    assert_eq!(
        registry_rows.len(),
        OP_F_NAME_COUNT,
        "every OP-F operation must carry typed_failures"
    );
    let row_names: Vec<&str> = registry_rows.iter().map(|(name, _)| *name).collect();
    assert_eq!(
        row_names, registry_names,
        "typed_failures rows drifted from the OP-F family keys"
    );
    let reference: &[&'static str] = &registry_rows[0].1;
    for (name, list) in &registry_rows {
        assert_eq!(
            list, reference,
            "{}: typed_failures diverged inside families.OP-F",
            name
        );
    }
    assert_eq!(
        failures, reference,
        "typed_non_success diverged from the registry OP-F typed_failures"
    );
    for token in NON_FAILURE_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is a success, a status, a point-query outcome or the OP-P eighth token, never an OP-F interval failure"
        );
    }

    // The ForceInterval entity restates the same closed list inline.
    let blocks = entity_blocks(CONTRACT_YAML);
    let entity_failures = inline_bracket_items(entity_scalar(
        block_of(&blocks, "ForceInterval"),
        "typed_non_success",
    ));
    assert_eq!(
        entity_failures, reference,
        "ForceInterval typed_non_success diverged from the registry canon"
    );
}

#[test]
fn transitions_are_the_closed_seven_interval_rows() {
    let rows = transition_rows();
    assert_eq!(rows.len(), TRANSITION_COUNT, "transition count drifted");
    assert_eq!(rows[0], ["Commence", "none", "InForce"]);
    assert_eq!(rows[1], ["Suspend", "InForce", "Suspended"]);
    assert_eq!(rows[2], ["Resume", "Suspended", "InForce"]);
    assert_eq!(rows[3], ["Repeal", "current_force", "Repealed"]);
    assert_eq!(rows[4], ["Expire", "InForce", "Expired"]);
    assert_eq!(rows[5], ["Invalidate", "current_force", "Invalidated"]);
    assert_eq!(
        rows[6],
        [
            "Restore",
            "Repealed_or_Invalidated_or_Suspended",
            "force_per_overlay"
        ]
    );
    // Triggers follow the OP-F canon — compare-extracted, not restated.
    let triggers: Vec<&str> = rows.iter().map(|row| row[0]).collect();
    assert_eq!(
        triggers,
        registry_op_f_names(),
        "transition triggers diverged from the registry OP-F canon"
    );
    // Resume re-opens a new disjoint InForce member out of a Suspended
    // interval; Restore is a distinct row with overlay-decided force.
    let resume = rows
        .iter()
        .find(|row| row[0] == "Resume")
        .expect("Resume transition row missing");
    assert_eq!((resume[1], resume[2]), ("Suspended", "InForce"));
    let restore = rows
        .iter()
        .find(|row| row[0] == "Restore")
        .expect("Restore transition row missing");
    assert_ne!(
        resume, restore,
        "Resume collapsed into Restore; they are distinct operations"
    );
}

#[test]
fn suspend_is_an_operation_never_a_written_status() {
    let section = section_between(
        CONTRACT_YAML,
        "suspend_is_not_a_status:",
        "resume_is_not_restore:",
    );
    assert_eq!(
        section_scalar(section, "kind"),
        "operation",
        "Suspend must stay an operation kind, never a status"
    );
    assert_eq!(
        section_scalar(section, "distinct_from_status"),
        "Suspended",
        "the operation and the written status it opens must stay distinct"
    );
    assert_eq!(section_scalar(section, "opens"), "Suspended");
    assert_eq!(section_scalar(section, "closes"), "InForce");
    assert_eq!(
        section_scalar(section, "later_resume"),
        "expected_not_implied",
        "a later Resume is expected, never implied by the suspension"
    );
    // Roadmap negative: suspend is an interval-opening operation, not a
    // member of any status enumeration a resolver could read.
    let statuses = top_level_dash_items(CONTRACT_YAML, "written_statuses:");
    assert!(
        !statuses.contains(&"Suspend"),
        "Suspend is an OP-F operation, never a written status"
    );
}

#[test]
fn resume_stays_distinct_from_restore() {
    let section = section_between(CONTRACT_YAML, "resume_is_not_restore:", "projection:");
    assert_eq!(
        section_scalar(section, "kind"),
        "operation",
        "Resume must stay an operation kind"
    );
    assert_eq!(
        section_scalar(section, "distinct_from_op"),
        "Restore",
        "Resume and Restore must stay distinct operations"
    );
    assert_eq!(
        section_scalar(section, "requires_open"),
        "Suspended",
        "Resume requires an open Suspended interval"
    );
}

#[test]
fn non_claims_carry_the_boundary_disclaimers() {
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    let has_claim = |needle: &str| claims.iter().any(|claim| claim.contains(needle));
    assert!(
        has_claim("Suspend is not Suspended"),
        "Suspend-vs-Suspended non-claim lost"
    );
    assert!(
        has_claim("Resume is not Restore"),
        "Resume-vs-Restore non-claim lost"
    );
    assert!(
        has_claim("Unknown is not a written interval"),
        "Unknown-vs-interval non-claim lost"
    );
    assert!(
        has_claim("Transitional is not a force interval"),
        "Transitional non-claim lost"
    );
    assert!(
        has_claim("Not the OP-P pending-effects contract"),
        "pending-effects boundary non-claim lost"
    );
    assert!(
        has_claim("Not a sixth clock"),
        "no-sixth-clock non-claim lost"
    );
    assert!(
        has_claim("Resume is not Work cancel_resume"),
        "Work cancel_resume homonymy non-claim lost"
    );
    assert!(
        has_claim("Commence is not ScheduleEffect"),
        "Commence-vs-ScheduleEffect non-claim lost"
    );
    assert!(
        has_claim("Repeal is not Detach"),
        "Repeal-vs-Detach non-claim lost"
    );
    assert!(
        has_claim("OP-F preconditions live in operation-registry.yaml, not duplicated"),
        "OP-F precondition ownership non-claim lost"
    );
    assert!(
        has_claim("ForceStatusEvent is not a YAML entity"),
        "no-ForceStatusEvent-entity non-claim lost"
    );
}

#[test]
fn neighbor_contract_tokens_never_mint_entity_keys() {
    // MEM947: raw-token isolation excludes the non_claims section — the
    // boundary prose there may legitimately name S01 / OP-T tokens.
    let body = contract_without_non_claims();
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in [
        "PendingEffect",
        "ProspectiveVersion",
        "ScheduleEffect",
        "ModifyPendingEffect",
        "CancelPendingEffect",
        "ReplaceText",
    ] {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !body.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected in the contract body"
        );
    }
}

#[test]
fn runtime_today_stays_design_only_for_both_entities() {
    let blocks = entity_blocks(CONTRACT_YAML);
    for name in ["ForceInterval", "ForceIntervalSet"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            RUNTIME_TODAY_VALUE,
            "{name} must stay design-only"
        );
    }
}

#[test]
fn projection_rules_stay_projections_never_source() {
    let section = section_between(CONTRACT_YAML, "projection:", "non_claims:");
    assert_eq!(
        section_scalar(section, "point_query"),
        "one_status_at_t_or_Unknown",
        "a point query yields one status or Unknown"
    );
    assert_eq!(
        section_scalar(section, "set"),
        "multiple_disjoint_in_force_legal",
        "multiple disjoint InForce members are legal (suspension/resumption)"
    );
    assert_eq!(
        section_scalar(section, "effective_from_to"),
        "projection_never_source",
        "effective_from/effective_to stay projections, never source truth"
    );
    assert_eq!(
        section_scalar(section, "invariant"),
        "INV-04",
        "the projection invariant pointer drifted"
    );
    let blocks = entity_blocks(CONTRACT_YAML);
    assert_eq!(
        entity_scalar(block_of(&blocks, "ForceIntervalSet"), "in_force_members"),
        "pairwise_disjoint",
        "InForce members must stay pairwise disjoint"
    );
    assert_eq!(
        entity_scalar(block_of(&blocks, "ForceIntervalSet"), "source"),
        "projection_of_op_f_events",
        "the OP-F event ledger, never the set, is source truth"
    );
}

#[test]
fn unknown_lives_only_in_the_point_query_outcomes() {
    // `Unknown` is the fail-closed point-query outcome: it lives in
    // point_query_outcomes, never in written_statuses (checked above) and
    // never in typed_non_success (checked above).
    let outcomes = inline_bracket_items(top_level_row("point_query_outcomes:"));
    assert_eq!(outcomes.len(), 2, "point_query_outcomes count drifted");
    assert!(
        outcomes.contains(&"resolved_status") && outcomes.contains(&"Unknown"),
        "point_query_outcomes lost resolved_status or Unknown"
    );
}
