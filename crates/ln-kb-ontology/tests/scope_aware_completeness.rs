//! D222/D231 pin-suite for the E.2.5 scope-aware completeness contract
//! (design-doc-as-data).
//!
//! `prd/architecture/scope-aware-completeness-contract.yaml` (owner:
//! ADR-0017 §4, specialized by the G0(d) checkout scope parameter;
//! ADR-0018 and ADR-0019 are related_adr for the Unknown/Conflict
//! homonyms only, never owners) is embedded via `include_str!` and pinned
//! with plain text/section assertions, mirroring `pending_effects.rs`
//! (E.2.3), `force_interval_set.rs` (E.2.4), `reference_binding.rs`
//! (E.2.2) and `operation_registry.rs` (E.2.1). Per D222/MEM938/MEM939
//! the contract carries neither `rust_path` nor `rust_enum`, is not a
//! `closed_vocabularies` row and is not parsed by `OntologyCatalog`, so
//! this suite stays parser-free string/section work and adds no YAML
//! crate dependency.
//!
//! There is deliberately exactly one embed and no alignment file: unlike
//! E.2.2/E.2.3/E.2.4 this contract has no operation-registry family to
//! align with — QueryScope is not the per-operation registry scope — so
//! the closed vocabularies are owned by the contract itself and pinned by
//! size plus membership, never restated as a second canon list (MEM951).
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor `ln_temporal`, and never references the
//! checkout runtime, `resolve_ctv` or `CtvIndustrialOpKind` in code. The
//! three entity names appear only as string data, exactly the shape every
//! neighbor pin suite already uses; coupling this suite to runtime types
//! would invert the D222 boundary, and the Unknown/Conflict homonymy
//! stays prose in the YAML non_claims.
//!
//! Negative surface (Q7): minting a third query scope kind, a fifth view
//! mode (`CaseApplicable`), a fourth outcome, widening
//! `in_scope_block_reasons` (`OrderingConflict` / `IncompleteSource` /
//! `AmbiguousTarget`) or `typed_non_success` (success/force/neighbor
//! tokens), moving ownership off ADR-0017, promoting lifecycle beyond
//! `[proposed]`, flipping `authoritative`, minting a fourth entity key or
//! a neighbor-contract token (`MerkleRoot:`, `CompleteFor:`,
//! `PendingEffect:`, ...) at entity depth, widening `runtime_today` past
//! `none`, stating a percentage (`97%`) as a coverage verdict, embedding
//! a second artifact, or adding `root_hash` to the CompletenessReport or
//! CoverageCertificate required fields all turn pins red on the tracked
//! file itself — no tmp fixtures, no runtime dependency. Absence pins
//! over the vocabulary lists run on extracted items, not raw substrings,
//! because the contract's own comments and non_claims legitimately name
//! every excluded token (MEM951); entity-depth isolation excludes the
//! non_claims section (MEM947).

/// Embedded contract (T01): the E.2.5 scope/outcome layer. Path is
/// relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str =
    include_str!("../../../prd/architecture/scope-aware-completeness-contract.yaml");

/// The only runtime contour this design-only contract accepts: neither
/// entity exists at runtime.
const RUNTIME_TODAY_VALUE: &str = "none";

/// Report-shaped tokens that must stay out of `completeness_outcomes`
/// (extracted-item checks, not substrings — MEM951; INV-10).
const NON_OUTCOME_TOKENS: [&str; 4] = ["PartialSuccess", "Degraded", "None", "Ok"];

/// MC-RES apply results that must stay out of `in_scope_block_reasons`.
const NON_BLOCK_REASON_TOKENS: [&str; 3] =
    ["OrderingConflict", "IncompleteSource", "AmbiguousTarget"];

/// Tokens that must stay out of `closure_dimensions`: the illustrative
/// `{Text, Membership, Force}` example set is not the closed seven, and
/// `StructuralClosure` is never a dimension token.
const NON_CLOSURE_DIMENSION_TOKENS: [&str; 4] =
    ["Text", "Membership", "Force", "StructuralClosure"];

/// Report outcomes and percentage words that must stay out of
/// `coverage_verdicts` (a percentage is never a verdict).
const NON_COVERAGE_VERDICT_TOKENS: [&str; 4] =
    ["InScopeComplete", "PartialSuccess", "Ok", "Percent"];

/// Successes, force states and neighbor-contract tokens that must stay
/// out of `typed_non_success`.
const NON_FAILURE_TOKENS: [&str; 6] = [
    "Applied",
    "Bound",
    "AlreadyApplied",
    "Suspended",
    "Transitional",
    "UnknownEffect",
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
/// The scope x gap table carries inline comments on its kind and gap
/// rows, so row pins must never compare the raw value text.
fn row_value(raw: &str) -> &str {
    raw.split('#').next().unwrap_or_default().trim()
}

/// The top-of-file authority block: everything before the first closed-set
/// key. Absence pins for `authoritative: true` / `[bounded]` / a wrong
/// `owner_adr` run here, not over the whole file, because body comments
/// may legitimately name them.
fn header_block() -> String {
    let cut = contract_marker_line(CONTRACT_YAML, "query_scope_kinds:");
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
/// lines, scope x gap rows (dash items and their four-space continuations),
/// lowercase two-space section keys and folded-scalar prose continuations
/// never match, so a stray `MerkleRoot:` or `Suspend:` entity key would be
/// caught here.
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
/// key line (or EOF — the last body spans into `scope_gap_outcomes:` /
/// `scope_gap_invariant:` / `checkout_projection:` / `non_claims:`). Every
/// assertion below is anchored on exact keys or exact values, so the
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

/// Field keys of an entity's `required_fields` list. Unlike the neighbor
/// contracts (six-space subsection keys) this contract carries the fields
/// as one inline `[a, b, c]` row, so the keys are extracted from the
/// bracket list itself.
fn required_field_keys(block: &EntityBlock) -> Vec<&str> {
    inline_bracket_items(entity_scalar(block, "required_fields"))
}

/// Rows of the `scope_gap_outcomes` table: (kind, in_scope_gap,
/// out_of_scope_gap, outcome), parsed as dash items with four-space
/// continuations — a section parser, never raw substrings. The section
/// ends at the next zero-indent line; inline comments are cut so the
/// pinned kind/gap/outcome values stay exact.
fn scope_gap_rows() -> Vec<[&'static str; 4]> {
    let start = contract_marker_line(CONTRACT_YAML, "scope_gap_outcomes:");
    let mut rows = Vec::new();
    let (mut kind, mut in_scope, mut out_of_scope, mut outcome) = ("", "", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - kind: ") {
            if !kind.is_empty() {
                rows.push([kind, in_scope, out_of_scope, outcome]);
            }
            (kind, in_scope, out_of_scope, outcome) = (row_value(value), "", "", "");
        } else if let Some(value) = line.strip_prefix("    in_scope_gap: ") {
            in_scope = row_value(value);
        } else if let Some(value) = line.strip_prefix("    out_of_scope_gap: ") {
            out_of_scope = row_value(value);
        } else if let Some(value) = line.strip_prefix("    outcome: ") {
            outcome = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !kind.is_empty() {
        rows.push([kind, in_scope, out_of_scope, outcome]);
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
        CONTRACT_YAML.contains("schema_version: law-nexus-scope-aware-completeness-contract/v1"),
        "contract schema identity drifted"
    );
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
fn header_points_at_owner_adr_0017_and_the_g0d_checkout_source() {
    assert!(
        CONTRACT_YAML.contains("owner_adr: ADR-0017"),
        "ADR-0017 must stay the data owner (D231)"
    );
    let related = inline_bracket_items(top_level_row("related_adr:"));
    assert!(
        related.contains(&"ADR-0018") && related.contains(&"ADR-0019"),
        "related_adr lost ADR-0018 or ADR-0019 (Unknown/Conflict homonyms)"
    );
    assert!(
        !related.contains(&"ADR-0017"),
        "ADR-0017 is the owner, never a related ADR of its own contract"
    );
    // Ownership may never drift onto a homonym owner: the related_adr row
    // legitimately names both, so the substring is header-scoped.
    let header = header_block();
    assert!(!header.contains("owner_adr: ADR-0018"));
    assert!(!header.contains("owner_adr: ADR-0019"));
    let checkout_source = top_level_row("checkout_source:");
    assert!(
        checkout_source.contains("G0(d)") && checkout_source.contains("checkout("),
        "checkout_source must name G0(d) and the checkout( projection"
    );
}

#[test]
fn query_scope_kinds_are_the_closed_two_set() {
    // Size plus membership pins the exact set; the canon list itself is
    // never restated here (MEM951 — this contract owns it).
    let kinds = inline_bracket_items(top_level_row("query_scope_kinds:"));
    assert_eq!(kinds.len(), 2, "query scope kind count drifted");
    assert!(kinds.contains(&"WholeAct"), "WholeAct kind lost");
    assert!(
        kinds.contains(&"ComponentSubgraph"),
        "ComponentSubgraph kind lost"
    );
}

#[test]
fn view_modes_are_the_closed_four_set_without_case_applicable() {
    let modes = inline_bracket_items(top_level_row("view_modes:"));
    assert_eq!(modes.len(), 4, "view mode count drifted");
    for mode in [
        "Promulgated",
        "Operative",
        "HistoricalCitation",
        "Reference",
    ] {
        assert!(modes.contains(&mode), "view mode {mode} lost");
    }
    // Parsed-list absence, not a substring: the row's own comment and the
    // non_claims legitimately name CaseApplicable (ADR-0023) (MEM951).
    assert!(
        !modes.contains(&"CaseApplicable"),
        "CaseApplicable is an ADR-0023 view, never part of this contract"
    );
}

#[test]
fn completeness_outcomes_are_the_closed_three_set() {
    let outcomes = inline_bracket_items(top_level_row("completeness_outcomes:"));
    assert_eq!(outcomes.len(), 3, "completeness outcome count drifted");
    for outcome in [
        "InScopeComplete",
        "InScopeBlocked",
        "OutOfScopeUnknownReported",
    ] {
        assert!(outcomes.contains(&outcome), "outcome {outcome} lost");
    }
    for token in NON_OUTCOME_TOKENS {
        assert!(
            !outcomes.contains(&token),
            "{token} is never a completeness outcome (INV-10)"
        );
    }
}

#[test]
fn in_scope_block_reasons_are_the_closed_three_set() {
    let reasons = inline_bracket_items(top_level_row("in_scope_block_reasons:"));
    assert_eq!(reasons.len(), 3, "in-scope block reason count drifted");
    for reason in ["Unknown", "Conflict", "MissingAnchor"] {
        assert!(reasons.contains(&reason), "block reason {reason} lost");
    }
    for token in NON_BLOCK_REASON_TOKENS {
        assert!(
            !reasons.contains(&token),
            "{token} is an MC-RES apply result, never an in-scope block reason"
        );
    }
}

#[test]
fn typed_non_success_is_the_closed_two_set() {
    let failures = inline_bracket_items(top_level_row("typed_non_success:"));
    assert_eq!(failures.len(), 2, "typed non-success count drifted");
    assert!(
        failures.contains(&"UnderspecifiedScope"),
        "UnderspecifiedScope lost"
    );
    assert!(failures.contains(&"SeedNotFound"), "SeedNotFound lost");
    for token in NON_FAILURE_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is a success, a force state or a neighbor-contract token, never a completeness typed non-success"
        );
    }
}

#[test]
fn closure_dimensions_are_the_closed_seven_set() {
    // Review-26 L677-683: exactly seven snake_case dimension names; the
    // canon lives once in the contract and is pinned by size plus
    // membership, never restated here (MEM951).
    let dims = inline_bracket_items(top_level_row("closure_dimensions:"));
    assert_eq!(dims.len(), 7, "closure dimension count drifted");
    for dim in [
        "structural",
        "causal",
        "temporal_anchor",
        "evidence",
        "force",
        "reference",
        "oracle_coverage",
    ] {
        assert!(dims.contains(&dim), "closure dimension {dim} lost");
    }
    // Parsed-list absence, not substrings: the illustrative {Text,
    // Membership, Force} sample set and the PascalCase StructuralClosure
    // token legitimately live in comments and non_claims (MEM951), but
    // never in this list.
    for token in NON_CLOSURE_DIMENSION_TOKENS {
        assert!(
            !dims.contains(&token),
            "{token} is never a closure dimension"
        );
    }
}

#[test]
fn coverage_verdicts_are_the_closed_two_set() {
    let verdicts = inline_bracket_items(top_level_row("coverage_verdicts:"));
    assert_eq!(verdicts.len(), 2, "coverage verdict count drifted");
    assert!(verdicts.contains(&"CompleteFor"), "CompleteFor lost");
    assert!(
        verdicts.contains(&"IncompleteBecause"),
        "IncompleteBecause lost"
    );
    // Parsed-list absence: InScopeComplete stays a completeness outcome,
    // PartialSuccess/Ok stay out everywhere, and Percent is never a
    // verdict (MEM951).
    for token in NON_COVERAGE_VERDICT_TOKENS {
        assert!(
            !verdicts.contains(&token),
            "{token} is never a coverage verdict"
        );
    }
}

#[test]
fn three_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["QueryScope", "CompletenessReport", "CoverageCertificate"],
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
            "QueryScope",
            &[
                "kind",
                "seed_component_ids",
                "include_dependency_subgraph",
                "view_mode",
            ],
        ),
        (
            "CompletenessReport",
            &[
                "query_scope",
                "outcome",
                "in_scope_unknowns",
                "out_of_scope_unknowns",
                "in_scope_conflicts",
                "coverage",
                "provenance",
            ],
        ),
        (
            "CoverageCertificate",
            &[
                "requested_scope",
                "structural_closure",
                "causal_closure",
                "temporal_anchor_closure",
                "evidence_closure",
                "force_closure",
                "reference_closure",
                "oracle_coverage",
                "unresolved_components",
                "unresolved_effects",
                "unresolved_references",
                "excluded_sources",
                "compiler_protocol_version",
                "source_set_hash",
                "verdict",
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
    // root_hash is the E.2.6 sibling payload projection, never a report
    // field and never a certificate field — INV-22: the hash without the
    // certificate is not a completeness claim (checked against the parsed
    // lists, not prose).
    for name in ["CompletenessReport", "CoverageCertificate"] {
        let fields = required_field_keys(block_of(&blocks, name));
        assert!(
            !fields.contains(&"root_hash"),
            "root_hash must never become a {name} field (E.2.6 is a sibling contract)"
        );
    }
}

#[test]
fn coverage_certificate_is_proof_not_assembly_metric() {
    // P0-8 metric/proof split: CompletenessReport.coverage stays the
    // Bound-CC / Oracle-CC assembly metric; the certificate carries the
    // proof and closes with a verdict, never the coverage field.
    let blocks = entity_blocks(CONTRACT_YAML);
    let report_fields = required_field_keys(block_of(&blocks, "CompletenessReport"));
    assert!(
        report_fields.contains(&"coverage"),
        "CompletenessReport.coverage must remain the assembly metric"
    );
    let cert_fields = required_field_keys(block_of(&blocks, "CoverageCertificate"));
    assert!(
        cert_fields.contains(&"verdict"),
        "CoverageCertificate must close with a coverage_verdicts verdict"
    );
    // Exact-element absence: oracle_coverage shares only a substring, so
    // the parsed list decides (MEM951).
    assert!(
        !cert_fields.contains(&"coverage"),
        "the certificate is the proof, never a rename of the coverage metric"
    );
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    assert!(
        claims.iter().any(|claim| claim.contains("not a rename")),
        "metric-vs-proof not-a-rename non-claim lost"
    );
}

#[test]
fn runtime_today_stays_design_only_for_all_three_entities() {
    let blocks = entity_blocks(CONTRACT_YAML);
    for name in ["QueryScope", "CompletenessReport", "CoverageCertificate"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            RUNTIME_TODAY_VALUE,
            "{name} must stay design-only"
        );
    }
}

#[test]
fn scope_gap_outcomes_are_the_closed_five_row_table() {
    let rows = scope_gap_rows();
    assert_eq!(rows.len(), 5, "scope x gap row count drifted");
    assert_eq!(rows[0], ["WholeAct", "any", "impossible", "InScopeBlocked"]);
    assert_eq!(
        rows[1],
        ["WholeAct", "none", "impossible", "InScopeComplete"]
    );
    assert_eq!(
        rows[2],
        [
            "ComponentSubgraph",
            "any",
            "ignored_for_blocking",
            "InScopeBlocked"
        ]
    );
    assert_eq!(
        rows[3],
        [
            "ComponentSubgraph",
            "none",
            "any",
            "OutOfScopeUnknownReported"
        ]
    );
    assert_eq!(
        rows[4],
        ["ComponentSubgraph", "none", "none", "InScopeComplete"]
    );
    // E.2.5: blocking only ever comes from an in-scope gap, and a real
    // out-of-scope gap must never yield InScopeBlocked — an out-of-scope
    // unknown is reported, never blocking.
    for row in &rows {
        assert!(
            row[3] != "InScopeBlocked" || row[1] == "any",
            "a row blocks without an in-scope gap: {row:?}"
        );
        if row[2] == "any" {
            assert_ne!(
                row[3], "InScopeBlocked",
                "an out-of-scope gap must never produce InScopeBlocked (E.2.5)"
            );
        }
    }
    assert!(
        CONTRACT_YAML.contains("scope_gap_invariant:"),
        "scope_gap_invariant section lost"
    );
    assert!(
        CONTRACT_YAML.contains("an out-of-scope unknown is reported, never blocking"),
        "E.2.5 invariant prose lost"
    );
}

#[test]
fn whole_act_preserves_the_s4_any_gap_blocks_rule() {
    // ADR-0017 §4 whole-act fail-closed is preserved as table rows and a
    // non-claim, not deleted (R068 anti-smoothing).
    let rows = scope_gap_rows();
    let whole_act: Vec<_> = rows.iter().filter(|row| row[0] == "WholeAct").collect();
    assert_eq!(whole_act.len(), 2, "WholeAct must own exactly two rows");
    for row in &whole_act {
        assert_eq!(
            row[2], "impossible",
            "every component is in scope under WholeAct; out-of-scope is impossible"
        );
    }
    assert!(
        whole_act
            .iter()
            .any(|row| row[1] == "any" && row[3] == "InScopeBlocked"),
        "WholeAct + any in-scope gap must block (ADR-0017 §4)"
    );
    assert!(
        whole_act
            .iter()
            .any(|row| row[1] == "none" && row[3] == "InScopeComplete"),
        "WholeAct + no in-scope gap must complete"
    );
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    assert!(
        claims
            .iter()
            .any(|claim| claim.contains("whole-act fail-closed row is preserved")),
        "the §4-preserved non-claim lost (R068)"
    );
}

#[test]
fn checkout_projection_stays_a_projection_never_the_payload() {
    let section = section_between(CONTRACT_YAML, "checkout_projection:", "non_claims:");
    assert_eq!(
        section_scalar(section, "coverage"),
        "projection_of_completeness_report",
        "coverage is a projection of the report"
    );
    assert_eq!(
        section_scalar(section, "coverage_certificate"),
        "projection_of_coverage_certificate",
        "the CoverageCertificate proof projects additively beside the metric"
    );
    assert_eq!(
        section_scalar(section, "unknowns"),
        "in_scope_union_out_of_scope_distinguishable",
        "in-scope and out-of-scope unknowns must stay distinguishable (INV-08)"
    );
    assert_eq!(
        section_scalar(section, "conflicts"),
        "in_scope_ctv_conflicts_only",
        "only in-scope CTV conflicts reach the projection"
    );
    assert_eq!(
        section_scalar(section, "root_hash"),
        "sibling_payload_checkout",
        "root hashing belongs to the E.2.6 sibling, never this report"
    );
    for key in ["applied_effects", "excluded_future_effects"] {
        assert_eq!(
            section_scalar(section, key),
            "owned_by_pending_effects_e23",
            "{key} stays owned by the E.2.3 contract, never completeness"
        );
    }
    assert_eq!(
        section_scalar(section, "node_provenance"),
        "INV-08",
        "the node-provenance invariant pointer drifted"
    );
    assert_eq!(
        section_scalar(section, "no_none_outcomes"),
        "INV-10",
        "the no-None-outcomes invariant pointer drifted"
    );
    assert_eq!(
        section_scalar(section, "whole_act_fail_closed"),
        "ADR-0017_s4_preserved_as_wholeact_row",
        "the §4 whole-act row stays preserved, not deleted (R068)"
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
        has_claim("whole-act fail-closed row is preserved"),
        "§4-preserved non-claim lost (R068)"
    );
    assert!(
        has_claim("out-of-scope unknown does not block"),
        "E.2.5 out-of-scope non-blocking non-claim lost"
    );
    assert!(
        has_claim("not a NormativeState Unknown"),
        "completeness-Unknown homonymy non-claim lost"
    );
    assert!(
        has_claim("not the ADR-0019 maxim Conflict"),
        "coverage-Conflict homonymy non-claim lost"
    );
    assert!(
        has_claim("not the per-operation registry scope"),
        "registry-scope homonymy non-claim lost"
    );
    assert!(
        has_claim("view_mode is not QueryScope"),
        "view-vs-scope orthogonality non-claim lost"
    );
    assert!(
        has_claim("CaseApplicable is an ADR-0023 view"),
        "CaseApplicable boundary non-claim lost"
    );
    assert!(
        has_claim("Not Merkle root hashing"),
        "not-Merkle non-claim lost"
    );
    assert!(
        has_claim("not the assertion lifecycle"),
        "not-assertion-lifecycle non-claim lost"
    );
    assert!(
        has_claim("Not the pending-effects excluded_future rule"),
        "not-pending-effects non-claim lost"
    );
    assert!(
        has_claim("not the force interval set"),
        "not-force-interval-set non-claim lost"
    );
    assert!(
        has_claim("Not publication completeness"),
        "not-publication-completeness non-claim lost"
    );
    assert!(
        has_claim("Not a sixth clock"),
        "no-sixth-clock non-claim lost"
    );
    assert!(
        has_claim("closure algorithm is not minted here"),
        "closure-algorithm-stays-P2 non-claim lost"
    );
    assert!(
        has_claim("not a rename"),
        "coverage-metric-not-renamed-into-the-certificate non-claim lost"
    );
    assert!(
        has_claim("A percentage is never a verdict"),
        "percentage-is-never-a-verdict non-claim lost"
    );
    assert!(
        has_claim("compiler_protocol_version is not projection_protocol_version"),
        "INV-11 compiler-protocol homonymy non-claim lost"
    );
    assert!(
        has_claim("not a completeness claim (INV-22)"),
        "hash-without-certificate INV-22 non-claim lost"
    );
    assert!(
        has_claim("not a fourth merkle root_kind"),
        "source_set_hash root-kind separation non-claim lost"
    );
}

#[test]
fn neighbor_contract_tokens_never_mint_entity_keys() {
    // MEM947: raw-token isolation excludes the non_claims section — the
    // boundary prose there may legitimately name S02/S03 tokens (the
    // not-Merkle and not-assertion-lifecycle claims).
    let body = contract_without_non_claims();
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in [
        "MerkleRoot",
        "Assertion",
        "PendingEffect",
        "ForceInterval",
        "ReferenceMention",
        "CausalEdge",
        "ReplaceText",
        "Suspend",
        "CompleteFor",
        "IncompleteBecause",
        "ProjectionRoots",
        "MaterializedSection",
        "ValidationReceipt",
        "PercentCoverage",
    ] {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !body.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected in the contract body"
        );
    }
}

#[test]
fn exactly_one_embed_exists_in_this_suite() {
    // MEM990: the needle is assembled so this assertion adds no textual
    // occurrence, and the suite source is read back from disk at test
    // time — a second include_str! would import a sibling homonym into
    // these pins.
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let source_path = format!("{manifest_dir}/tests/scope_aware_completeness.rs");
    let source = std::fs::read_to_string(&source_path)
        .unwrap_or_else(|error| panic!("suite source unreadable: {error}"));
    let embed_invocation = concat!("include_str", "!(");
    assert_eq!(
        source.matches(embed_invocation).count(),
        1,
        "exactly one embed is allowed; a second YAML embed (merkle or \
         assertion-lifecycle \"for alignment\") would import sibling \
         homonyms into these pins"
    );
}
