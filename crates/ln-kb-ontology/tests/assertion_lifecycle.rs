//! D222/D233 pin-suite for the E.2.7 assertion-lifecycle contract
//! (design-doc-as-data).
//!
//! `prd/architecture/assertion-lifecycle-contract.yaml` (data owner:
//! ADR-0017 G0(a) alone; ADR-0008 D116 corpus promotion and ADR-0010 C10
//! process gates are related_adr for the authority/gates homonyms only,
//! never owners; the ADR-0013 G0 note anchors parser emission as
//! emit_source, never a fourth owner) is embedded via `include_str!` and
//! pinned with plain text/section assertions, mirroring `merkle_roots.rs`
//! (E.2.6), `scope_aware_completeness.rs` (E.2.5), `pending_effects.rs`
//! (E.2.3), `force_interval_set.rs` (E.2.4), `reference_binding.rs`
//! (E.2.2) and `operation_registry.rs` (E.2.1). Per
//! D222/D233/MEM938/MEM939 the contract carries neither `rust_path` nor
//! `rust_enum`, is not a `closed_vocabularies` row and is not parsed by
//! `OntologyCatalog`, so this suite stays parser-free string/section work
//! and adds no yaml/serde dependency (Cargo.toml stays untouched).
//!
//! There is deliberately exactly one embed and no alignment file: unlike
//! E.2.3 there is no registry YAML to align with, and a second embed of
//! the E.2.6 merkle YAML "for alignment" would import its `root_hash`
//! sibling homonym into these pins. Snapshot-fold membership is cited by
//! name (`fold_filter_ref` points at the E.2.6 rebuild_equivalence /
//! MC-CHECKOUT fold), never re-canonicalized here as a second formula.
//! The single-embed invariant itself is pinned by counting the
//! embed-macro invocations in this very source file at test time — a
//! counter, never a substring scan over the contract.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor any other crate, and never references
//! `LegalEventAssertion`, `AssertionTransition`, `AssertionStatus`,
//! `has_publication_authority` or `InputDigest` as code identifiers —
//! the entity names appear only as string data, exactly the shape every
//! neighbor pin suite already uses; coupling this suite to runtime types
//! would invert the D222 boundary.
//!
//! Negative surface (Q7): minting a fourth promotion-path rung, shrinking
//! statuses to the three rungs (dropping Rejected / Superseded), widening
//! statuses with a sixth member (Draft / Published / Promoted / Confirmed
//! / Admitted / Bound), moving ownership off ADR-0017 G0(a) (including
//! onto ADR-0008 / ADR-0010 / ADR-0013), promoting lifecycle past
//! `[proposed]`, flipping `authoritative`, adding a third entity key
//! (Assertion / Lifecycle / Promotion / neighbor tokens) at entity depth,
//! moving `runtime_today` past `none`, dropping or widening required
//! fields (`binding_status` / `component_id` / `root_hash`), adding a
//! sixth FSM row, a rung-skipping Proposed -> AuthoritativeInternal
//! edge, a demotion edge, a reject-from-Validated edge or a `supersedes`
//! trigger, retargeting a transition owner, widening `typed_non_success`
//! with DirectPromotionRejected / CompetingWriterRejected / Applied /
//! Bound / Confirmed / OrderingConflict, admitting Proposed / Rejected /
//! Superseded into `fold_statuses`, copying the E.2.6 fold formula as a
//! brace block, or adding a second embed all turn pins red on the tracked
//! files themselves — no tmp fixtures, no runtime dependency. Absence
//! pins over the vocabulary lists run on extracted items, not raw
//! substrings, because the contract's own comments and non_claims
//! legitimately name every excluded token (MEM951); entity-depth
//! isolation excludes the non_claims section (MEM947).

/// Embedded contract (T01): the E.2.7 assertion-lifecycle layer. Path is
/// relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str =
    include_str!("../../../prd/architecture/assertion-lifecycle-contract.yaml");

/// The only runtime contour this design-only contract accepts: neither
/// entity exists at runtime.
const RUNTIME_TODAY_VALUE: &str = "none";

/// Publication / D098-tag / binding-vocabulary homonyms that must stay out
/// of the parsed `statuses` list (extracted-item checks, not substrings —
/// MEM951).
const NON_STATUS_TOKENS: [&str; 6] = [
    "Draft",
    "Published",
    "Promoted",
    "Confirmed",
    "Admitted",
    "Bound",
];

/// Terminal statuses that are legal `statuses` members but never
/// promotion-path rungs.
const NON_PROMOTION_TOKENS: [&str; 2] = ["Rejected", "Superseded"];

/// ADR-0008 tokens, MC-RES apply results and binding statuses that must
/// stay out of `typed_non_success` (parsed-item checks, not substrings).
const NON_TYPED_NON_SUCCESS_TOKENS: [&str; 6] = [
    "DirectPromotionRejected",
    "CompetingWriterRejected",
    "Bound",
    "Applied",
    "Confirmed",
    "OrderingConflict",
];

/// S01/S02-family tokens that must never become a third entity key at
/// entity depth.
const NEIGHBOR_ENTITY_KEYS: [&str; 10] = [
    "Assertion",
    "Lifecycle",
    "Promotion",
    "QueryScope",
    "CompletenessReport",
    "MaterializedSection",
    "ProjectionRoots",
    "PendingEffect",
    "ForceInterval",
    "ReferenceMention",
];

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
/// Every closed-vocabulary row carries a long inline comment naming the
/// excluded tokens, so row pins must never compare the raw value text
/// (MEM986).
fn row_value(raw: &str) -> &str {
    raw.split('#').next().unwrap_or_default().trim()
}

/// The top-of-file authority block: everything before the first closed-set
/// key (`statuses:`). Absence pins for `authoritative: true` /
/// `[bounded]` run here, not over the whole file, because body comments
/// may legitimately discuss authority and promotion.
fn header_block() -> String {
    let cut = contract_marker_line(CONTRACT_YAML, "statuses:");
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
/// shape of an entity entry under `entities:` (MEM968: the two-space
/// entity scanner, never the six-space operation scanner). Deeper field
/// lines, FSM dash rows and their four-space continuations and
/// folded-scalar prose continuations never match, so a stray third entity
/// key would be caught here.
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
/// `transition_owners:` / `skip_lifecycle:` / `non_claims:`). Every
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

/// Field keys of an entity's `required_fields` list. Like the neighbors
/// this contract carries the fields as one inline `[a, b, c]` row, so the
/// keys are extracted from the bracket list itself.
fn required_field_keys(block: &EntityBlock) -> Vec<&str> {
    inline_bracket_items(entity_scalar(block, "required_fields"))
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

/// Rows of the admission-path FSM under `transitions:`:
/// (trigger, from_status, to_status), parsed as dash items with four-space
/// continuations — a section parser, never raw substrings (copied shape
/// from `pending_effects.rs`). The section ends at the next zero-indent
/// line.
fn transition_rows() -> Vec<[&'static str; 3]> {
    let start = contract_marker_line(CONTRACT_YAML, "transitions:");
    let mut rows = Vec::new();
    let (mut trigger, mut from, mut to) = ("", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - trigger: ") {
            if !trigger.is_empty() {
                rows.push([trigger, from, to]);
            }
            (trigger, from, to) = (row_value(value), "", "");
        } else if let Some(value) = line.strip_prefix("    from: ") {
            from = row_value(value);
        } else if let Some(value) = line.strip_prefix("    to: ") {
            to = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !trigger.is_empty() {
        rows.push([trigger, from, to]);
    }
    rows
}

/// Rows of `transition_owners`: (trigger, owner), parsed as dash items
/// with four-space continuations — a section parser, never raw substrings
/// (mirror of `canonical_form_rows`). The section ends at the next
/// zero-indent line; inline comments are cut so the pinned values stay
/// exact.
fn transition_owner_rows() -> Vec<[&'static str; 2]> {
    let start = contract_marker_line(CONTRACT_YAML, "transition_owners:");
    let mut rows = Vec::new();
    let (mut trigger, mut owner) = ("", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - trigger: ") {
            if !trigger.is_empty() {
                rows.push([trigger, owner]);
            }
            (trigger, owner) = (row_value(value), "");
        } else if let Some(value) = line.strip_prefix("    owner: ") {
            owner = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !trigger.is_empty() {
        rows.push([trigger, owner]);
    }
    rows
}

/// Rows of the `skip_lifecycle` table: (attempt, would_produce, outcome),
/// parsed as dash items with four-space continuations — a section parser,
/// never raw substrings (mirror of `scope_gap_rows`). The section ends at
/// the next zero-indent line; inline comments are cut so the pinned
/// values stay exact.
fn skip_rows() -> Vec<[&'static str; 3]> {
    let start = contract_marker_line(CONTRACT_YAML, "skip_lifecycle:");
    let mut rows = Vec::new();
    let (mut attempt, mut produces, mut outcome) = ("", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - attempt: ") {
            if !attempt.is_empty() {
                rows.push([attempt, produces, outcome]);
            }
            (attempt, produces, outcome) = (row_value(value), "", "");
        } else if let Some(value) = line.strip_prefix("    would_produce: ") {
            produces = row_value(value);
        } else if let Some(value) = line.strip_prefix("    outcome: ") {
            outcome = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !attempt.is_empty() {
        rows.push([attempt, produces, outcome]);
    }
    rows
}

#[test]
fn contract_embeds_as_data_and_pins_schema_identity() {
    assert!(!CONTRACT_YAML.is_empty(), "contract failed to embed");
    assert!(
        CONTRACT_YAML.contains("schema_version: law-nexus-assertion-lifecycle-contract/v1"),
        "contract schema identity drifted"
    );
}

#[test]
fn contract_lifecycle_stays_proposed_and_non_authoritative() {
    assert_eq!(
        top_level_row("lifecycle:"),
        "lifecycle: \"[proposed]\"",
        "lifecycle drifted past the proposed design stage"
    );
    assert_eq!(
        top_level_row("authoritative:"),
        "authoritative: false",
        "authoritative flag drifted"
    );
    // Authority-laundering guards, scoped to the header block: body
    // comments may legitimately discuss bounded promotion; the authority
    // rows themselves may never carry it.
    let header = header_block();
    assert!(!header.contains("authoritative: true"));
    assert!(!header.contains("[bounded]"));
}

#[test]
fn header_points_at_owner_adr_0017_g0a_and_the_related_homonym_adrs() {
    assert_eq!(
        top_level_row("owner_adr:"),
        "owner_adr: ADR-0017",
        "ADR-0017 G0(a) must stay the data owner (D233)"
    );
    let related = inline_bracket_items(top_level_row("related_adr:"));
    assert!(
        related.contains(&"ADR-0008") && related.contains(&"ADR-0010"),
        "related_adr lost ADR-0008 or ADR-0010 (authority/gates homonyms)"
    );
    assert!(
        !related.contains(&"ADR-0017"),
        "ADR-0017 is the owner, never a related ADR of its own contract"
    );
    // The owner row may never be laundered onto a related source.
    let header = header_block();
    assert!(!header.contains("owner_adr: ADR-0008"));
    assert!(!header.contains("owner_adr: ADR-0010"));
    assert!(!header.contains("owner_adr: ADR-0013"));
    let ledger_source = top_level_row("ledger_source:");
    assert!(
        ledger_source.contains("G0(a)") && ledger_source.contains("LegalEventAssertion"),
        "ledger_source must name G0(a) and the assertion ledger records"
    );
    let emit_source = top_level_row("emit_source:");
    assert!(
        emit_source.contains("ADR-0013") && emit_source.contains("Proposed"),
        "emit_source must anchor parser emission in the ADR-0013 G0 note"
    );
}

#[test]
fn statuses_are_the_closed_five_set_without_homonyms() {
    let statuses = inline_bracket_items(top_level_row("statuses:"));
    assert_eq!(
        statuses,
        vec![
            "Proposed",
            "Validated",
            "AuthoritativeInternal",
            "Rejected",
            "Superseded",
        ],
        "closed status set or order drifted"
    );
    for token in NON_STATUS_TOKENS {
        assert!(
            !statuses.contains(&token),
            "{token} is a publication / D098-tag / binding homonym, never an assertion status here"
        );
    }
}

#[test]
fn promotion_path_is_the_closed_three_rungs() {
    let path = inline_bracket_items(top_level_row("promotion_path:"));
    assert_eq!(
        path,
        vec!["Proposed", "Validated", "AuthoritativeInternal"],
        "promotion rungs or order drifted"
    );
    for token in NON_PROMOTION_TOKENS {
        assert!(
            !path.contains(&token),
            "{token} is a legal terminal status, never a promotion rung"
        );
    }
}

#[test]
fn fold_statuses_are_the_closed_two_set() {
    let folds = inline_bracket_items(top_level_row("fold_statuses:"));
    assert_eq!(
        folds,
        vec!["Validated", "AuthoritativeInternal"],
        "fold status set or order drifted"
    );
    for token in ["Proposed", "Rejected", "Superseded"] {
        assert!(
            !folds.contains(&token),
            "{token} never enters the snapshot fold"
        );
    }
}

#[test]
fn typed_non_success_is_the_closed_three_set() {
    let failures = inline_bracket_items(top_level_row("typed_non_success:"));
    assert_eq!(
        failures,
        vec!["SkipLifecycle", "DirectAuthoritativeMint", "InPlaceRewrite"],
        "typed non-success set or order drifted"
    );
    for token in NON_TYPED_NON_SUCCESS_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is an ADR-0008 token, an MC-RES apply result or a binding status, never an assertion typed non-success"
        );
    }
}

#[test]
fn two_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["LegalEventAssertion", "AssertionTransition"],
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
            "LegalEventAssertion",
            &["evidence_span", "recorded_at", "asserted_by", "status"],
        ),
        (
            "AssertionTransition",
            &["trigger", "from_status", "to_status"],
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
    // Reference-binding and projection payload fields stay out of the
    // ledger record identity (parsed-list checks, not substrings):
    // binding_status is the E.2.2 homonym, component_id / root_hash are
    // E.2.6 projection payload.
    let record_fields = required_field_keys(block_of(&blocks, "LegalEventAssertion"));
    for token in ["binding_status", "component_id", "root_hash"] {
        assert!(
            !record_fields.contains(&token),
            "{token} must never become a ledger record field"
        );
    }
}

#[test]
fn runtime_today_stays_design_only_for_both_entities() {
    let blocks = entity_blocks(CONTRACT_YAML);
    for name in ["LegalEventAssertion", "AssertionTransition"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            RUNTIME_TODAY_VALUE,
            "{name} must stay design-only"
        );
    }
}

#[test]
fn transitions_are_the_closed_five_fsm_rows() {
    let rows = transition_rows();
    assert_eq!(rows.len(), 5, "transition count drifted");
    assert_eq!(rows[0], ["parser_emit", "none", "Proposed"]);
    assert_eq!(rows[1], ["validate", "Proposed", "Validated"]);
    assert_eq!(rows[2], ["authorize", "Validated", "AuthoritativeInternal"]);
    assert_eq!(rows[3], ["reject", "Proposed", "Rejected"]);
    assert_eq!(rows[4], ["supersede_append", "none", "Superseded"]);
    // Invariants over the parsed rows: no rung-skipping shortcut, no
    // demotion, reject only from Proposed, and the G0(c) DAG-edge name
    // never becomes a trigger.
    for row in &rows {
        assert!(
            !(row[1] == "Proposed" && row[2] == "AuthoritativeInternal"),
            "a rung-skipping Proposed -> AuthoritativeInternal edge appeared"
        );
        assert!(
            row[1] != "AuthoritativeInternal",
            "a demotion edge out of AuthoritativeInternal appeared"
        );
        assert!(
            !(row[1] == "Validated" && row[2] == "Proposed"),
            "a demotion edge Validated -> Proposed appeared"
        );
    }
    assert!(
        rows.iter()
            .all(|row| !(row[0] == "reject" && row[1] != "Proposed")),
        "reject exists only from Proposed"
    );
    assert!(
        rows.iter().all(|row| row[0] != "supersedes"),
        "the G0(c) supersedes DAG-edge name is never a lifecycle trigger"
    );
}

#[test]
fn transition_owners_are_the_closed_five_trigger_map() {
    let rows = transition_owner_rows();
    assert_eq!(rows.len(), 5, "transition-owner row count drifted");
    assert_eq!(rows[0], ["parser_emit", "ADR-0013"]);
    assert_eq!(rows[1], ["validate", "ADR-0010"]);
    assert_eq!(rows[2], ["authorize", "ADR-0008"]);
    assert_eq!(rows[3], ["reject", "ADR-0010"]);
    assert_eq!(rows[4], ["supersede_append", "ADR-0017"]);
}

#[test]
fn skip_lifecycle_is_the_closed_six_row_table() {
    let rows = skip_rows();
    assert_eq!(rows.len(), 6, "skip-table row count drifted");
    let outcome_of = |attempt: &str| {
        rows.iter()
            .find(|row| row[0] == attempt)
            .map(|row| row[2])
            .unwrap_or_else(|| panic!("skip_lifecycle row missing: {attempt}"))
    };
    assert_eq!(
        outcome_of("parser_emit_of_Validated"),
        "SkipLifecycle",
        "the parser never mints a Validated record directly"
    );
    assert_eq!(
        outcome_of("Proposed_to_AuthoritativeInternal"),
        "SkipLifecycle",
        "no rung-skipping shortcut may exist"
    );
    assert_eq!(
        outcome_of("parser_emit_of_AuthoritativeInternal"),
        "DirectAuthoritativeMint"
    );
    assert_eq!(
        outcome_of("adapter_mint_AuthoritativeInternal"),
        "DirectAuthoritativeMint"
    );
    assert_eq!(
        outcome_of("in_place_status_mutation"),
        "InPlaceRewrite",
        "in-place status mutation is the INV-05 violation token"
    );
    assert_eq!(
        outcome_of("fold_of_Proposed_or_Rejected_or_Superseded"),
        "excluded_by_fold_filter",
        "folding a non-fold status is filtered out, never a typed non-success"
    );
    // Every outcome is either a typed_non_success member (parsed list)
    // or the fold-filter-owned exclusion token — nothing else.
    let failures = inline_bracket_items(top_level_row("typed_non_success:"));
    for row in &rows {
        assert!(
            failures.contains(&row[2]) || row[2] == "excluded_by_fold_filter",
            "unknown skip outcome `{}` for attempt `{}`",
            row[2],
            row[0]
        );
    }
    assert!(
        !failures.contains(&"excluded_by_fold_filter"),
        "excluded_by_fold_filter belongs to the E.2.6 fold filter, never typed_non_success"
    );
}

#[test]
fn correction_invariant_and_fold_filter_stay_name_citations() {
    // Folded scalars wrap prose across lines; collapse whitespace so
    // phrase pins stay independent of line breaks (MEM990).
    let invariant = section_between(CONTRACT_YAML, "correction_invariant:", "fold_filter_ref:");
    let invariant = invariant.split_whitespace().collect::<Vec<_>>().join(" ");
    for phrase in [
        "INV-05",
        "never rewrites the known_as_of past",
        "appends a new assertion record",
        "committed statuses are never rewritten in place",
        "no demotion transition exists",
    ] {
        assert!(
            invariant.contains(phrase),
            "correction-invariant lost phrase `{phrase}`"
        );
    }
    let filter = section_between(CONTRACT_YAML, "fold_filter_ref:", "non_claims:");
    let normalized = filter.split_whitespace().collect::<Vec<_>>().join(" ");
    assert!(
        filter.contains("rebuild_equivalence")
            && filter.contains("merkle-roots-contract.yaml")
            && filter.contains("MC-CHECKOUT"),
        "fold_filter_ref must cite the E.2.6 fold filter by name: {filter}"
    );
    assert!(
        normalized.contains("never copied into this file"),
        "the by-name-only citation statement drifted"
    );
    // The fold formula is never re-minted as a brace block here.
    assert!(
        !filter.contains('{'),
        "a brace-block fold formula was copied in; fold membership stays cited by name"
    );
    assert!(
        !CONTRACT_YAML.contains("status in {"),
        "the E.2.6 fold formula must never be copied as a second canon"
    );
}

#[test]
fn non_claims_carry_the_boundary_disclaimers() {
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    let has_claim = |needle: &str| claims.iter().any(|claim| claim.contains(needle));
    assert!(
        has_claim("No Rust types are minted"),
        "no-Rust-types non-claim lost"
    );
    assert!(
        has_claim("The data owner is ADR-0017 G0(a)")
            && has_claim("not ADR-0008 D116 corpus promotion")
            && has_claim("not ADR-0010 C10 process gates"),
        "owner-homonymy non-claims lost (G0(a) not D116/C10)"
    );
    assert!(
        has_claim("exactly five"),
        "five-statuses-not-three non-claim lost"
    );
    assert!(
        has_claim("are the promotion_path, not the closed status set"),
        "three-names-vs-closed-set non-claim lost"
    );
    assert!(
        has_claim("[proposed] is not the assertion status Proposed"),
        "D098-tag-vs-status non-claim lost"
    );
    assert!(
        has_claim("(E.2.2) are not assertion statuses"),
        "binding-statuses non-claim lost"
    );
    assert!(has_claim("is not this FSM"), "C10-vs-FSM non-claim lost");
    assert!(
        has_claim("D116 corpus promotion is not an AuthoritativeInternal mint"),
        "D116-vs-mint non-claim lost"
    );
    assert!(has_claim("Not a Review Case"), "Review Case non-claim lost");
    assert!(
        has_claim("G0(c) supersedes DAG edge") && has_claim("never appears as a trigger"),
        "G0(c)-supersedes non-claim lost"
    );
    assert!(
        has_claim("Not the E.2.6 Merkle roots")
            && has_claim("E.2.5 scope-aware completeness outcomes"),
        "Merkle/completeness boundary non-claims lost"
    );
    assert!(
        has_claim("may emit only Proposed"),
        "parser-emits-Proposed-only non-claim lost"
    );
    assert!(
        has_claim("Status is immutable after append"),
        "append-only-immutability non-claim lost"
    );
    assert!(
        has_claim("ln-promote / ln-publish"),
        "promote-publish-homonymy non-claim lost"
    );
    assert!(
        has_claim("Demotion") && has_claim("is not a transition"),
        "demotion-is-not-a-transition non-claim lost"
    );
}

#[test]
fn neighbor_contract_tokens_never_mint_entity_keys() {
    // MEM947: raw-token isolation excludes the non_claims section — the
    // boundary prose there may legitimately name S01/S02 tokens (the
    // not-Merkle and not-completeness claims).
    let body = contract_without_non_claims();
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in NEIGHBOR_ENTITY_KEYS {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !body.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected in the contract body"
        );
    }
}

#[test]
fn exactly_one_embed_exists_in_this_suite() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let source_path = format!("{manifest_dir}/tests/assertion_lifecycle.rs");
    let source = std::fs::read_to_string(&source_path)
        .unwrap_or_else(|error| panic!("suite source unreadable: {error}"));
    let embed_invocation = concat!("include_str", "!(");
    assert_eq!(
        source.matches(embed_invocation).count(),
        1,
        "exactly one embed is allowed; a second YAML embed (merkle \"for \
         alignment\") would import sibling homonyms into these pins"
    );
}
