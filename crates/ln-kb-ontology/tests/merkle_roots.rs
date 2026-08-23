//! D222/D232 pin-suite for the E.2.6 merkle-roots contract
//! (design-doc-as-data).
//!
//! `prd/architecture/merkle-roots-contract.yaml` (data owner: ADR-0017
//! G0(d); ADR-0013 and ADR-0009 are related_adr for the
//! parser-records-are-not-a-CST note and the not-a-sixth-clock note
//! only, never owners) is embedded via `include_str!` and pinned with
//! plain text/section assertions, mirroring `scope_aware_completeness.rs`
//! (E.2.5), `pending_effects.rs` (E.2.3), `force_interval_set.rs`
//! (E.2.4), `reference_binding.rs` (E.2.2) and `operation_registry.rs`
//! (E.2.1). Per D222/D232/MEM938/MEM939 the contract carries neither
//! `rust_path` nor `rust_enum`, is not a `closed_vocabularies` row and
//! is not parsed by `OntologyCatalog`, so this suite stays parser-free
//! string/section work and adds no yaml/serde/sha2/blake3 dependency
//! (Cargo.toml stays untouched).
//!
//! There is deliberately exactly one embed and no alignment file: unlike
//! the registry family there is no second YAML to align with, and a
//! second embed of the E.2.5 completeness YAML would import its
//! `root_hash` sibling homonym into these pins. Cross-contract
//! references stay by-name scalar refs (`scope_kind_ref` /
//! `view_mode_ref`) and the single-embed invariant itself is pinned by
//! counting the embed-macro invocations in this very source file at
//! test time — a counter, never a substring scan over the contract.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor any other crate, and never references
//! `MaterializedSection`, `ProjectionRoots`, `CstRoot`,
//! `edition_ast_at`, `fold_expression_presence`, `InputDigest` or
//! `digest_pair` as code identifiers — the entity/root names appear
//! only as string data, exactly the shape every neighbor pin suite
//! already uses; coupling this suite to runtime types would invert the
//! D222 boundary.
//!
//! Negative surface (Q7): minting a fourth root kind (PresenceRoot /
//! ArtifactHash / QuotedHash / ComposedCheckoutRoot /
//! NormalizedSemanticHash / InputDigest / CommitDigest), promoting
//! `composed_checkout_root` into the parsed `root_kinds`, widening
//! `typed_non_success` (Applied / OrderingConflict / InScopeBlocked /
//! MissingAnchor / Bound / AlreadyApplied), minting a third entity key
//! (MerkleRoot / QueryScope / CompletenessReport / Assertion /
//! PendingEffect / ForceInterval / ReferenceMention /
//! AddressableTextUnit) at entity depth, moving ownership off ADR-0017,
//! dropping a related_adr, promoting lifecycle past `[proposed]`,
//! flipping `authoritative`, setting `runtime_today` past `none`,
//! adding `root_hash` / `quoted_hash` / `artifact_hash` or an algorithm
//! name (sha256 / blake3 / fnv) to the required fields, re-minting the
//! E.2.5 closed-set tables as a second canon, or adding a second embed
//! all turn pins red on the tracked files themselves — no tmp fixtures,
//! no runtime dependency. Absence pins over the vocabulary lists run on
//! extracted items, not raw substrings, because the contract's own
//! comments and non_claims legitimately name every excluded token
//! (MEM951); entity-depth isolation excludes the non_claims section
//! (MEM947).

/// Embedded contract (T01): the E.2.6 merkle-roots layer. Path is
/// relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str = include_str!("../../../prd/architecture/merkle-roots-contract.yaml");

/// The only runtime contour this design-only contract accepts: neither
/// entity exists at runtime.
const RUNTIME_TODAY_VALUE: &str = "none";

/// Review-24 precursor / sibling tokens that must stay out of the parsed
/// `root_kinds` list (extracted-item checks, not substrings — MEM951).
/// `DocumentaryPresence` appears in `canonical_form` only as an excluded
/// row, and the composed payload root rides as a ProjectionRoots *field*
/// spelled `composed_checkout_root`, never as a CamelCase kind.
const NON_ROOT_KIND_TOKENS: [&str; 8] = [
    "PresenceRoot",
    "DocumentaryPresence",
    "ArtifactHash",
    "QuotedHash",
    "ComposedCheckoutRoot",
    "NormalizedSemanticHash",
    "InputDigest",
    "CommitDigest",
];

/// Successes, MC-RES apply results, completeness outcomes and anchor
/// errors that must stay out of `typed_non_success` (INV-03 is named in
/// non_claims; InScopeBlocked projects, it never becomes a Merkle token).
const NON_TYPED_NON_SUCCESS_TOKENS: [&str; 6] = [
    "Applied",
    "OrderingConflict",
    "InScopeBlocked",
    "MissingAnchor",
    "Bound",
    "AlreadyApplied",
];

/// S01/S03/G0(e)-family tokens that must never become a third entity key
/// at entity depth.
const NEIGHBOR_ENTITY_KEYS: [&str; 8] = [
    "MerkleRoot",
    "QueryScope",
    "CompletenessReport",
    "Assertion",
    "PendingEffect",
    "ForceInterval",
    "ReferenceMention",
    "AddressableTextUnit",
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
/// Both closed-vocabulary rows carry long inline comments naming every
/// excluded token, so row pins must never compare the raw value text
/// (MEM986).
fn row_value(raw: &str) -> &str {
    raw.split('#').next().unwrap_or_default().trim()
}

/// The top-of-file authority block: everything before the first closed-set
/// key (`root_kinds:`). Absence pins for `authoritative: true` /
/// `[bounded]` run here, not over the whole file, because body comments
/// may legitimately discuss authority and promotion.
fn header_block() -> String {
    let cut = contract_marker_line(CONTRACT_YAML, "root_kinds:");
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
/// lines, `canonical_form` dash rows and their four-space continuations,
/// lowercase two-space section keys (`checkout_projection:`) and
/// folded-scalar prose continuations never match, so a stray `MerkleRoot:`
/// entity key would be caught here.
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
/// key line (or EOF — the last body spans into `canonical_form:` /
/// `rebuild_equivalence:` / `checkout_projection:` / `non_claims:`). Every
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

/// Field keys of an entity's `required_fields` list. Like the E.2.5
/// neighbor this contract carries the fields as one inline `[a, b, c]`
/// row, so the keys are extracted from the bracket list itself.
fn required_field_keys(block: &EntityBlock) -> Vec<&str> {
    inline_bracket_items(entity_scalar(block, "required_fields"))
}

/// Rows of the `canonical_form` table: (root, serializes, never_as),
/// parsed as dash items with four-space continuations — a section parser,
/// never raw substrings (mirror of `scope_gap_rows`). The section ends at
/// the next zero-indent line; inline comments are cut so the pinned
/// values stay exact.
fn canonical_form_rows() -> Vec<[&'static str; 3]> {
    let start = contract_marker_line(CONTRACT_YAML, "canonical_form:");
    let mut rows = Vec::new();
    let (mut root, mut serializes, mut never_as) = ("", "", "");
    for line in CONTRACT_YAML.lines().skip(start + 1) {
        if let Some(value) = line.strip_prefix("  - root: ") {
            if !root.is_empty() {
                rows.push([root, serializes, never_as]);
            }
            (root, serializes, never_as) = (row_value(value), "", "");
        } else if let Some(value) = line.strip_prefix("    serializes: ") {
            serializes = row_value(value);
        } else if let Some(value) = line.strip_prefix("    never_as: ") {
            never_as = row_value(value);
        } else if !line.starts_with(' ') {
            break;
        }
    }
    if !root.is_empty() {
        rows.push([root, serializes, never_as]);
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
        CONTRACT_YAML.contains("schema_version: law-nexus-merkle-roots-contract/v1"),
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
fn header_points_at_owner_adr_0017_g0d_and_the_related_homonym_adrs() {
    assert_eq!(
        top_level_row("owner_adr:"),
        "owner_adr: ADR-0017",
        "ADR-0017 must stay the data owner (D232)"
    );
    let related = inline_bracket_items(top_level_row("related_adr:"));
    assert!(
        related.contains(&"ADR-0013") && related.contains(&"ADR-0009"),
        "related_adr lost ADR-0013 or ADR-0009 (parser-not-CST / sixth-clock notes)"
    );
    assert!(
        !related.contains(&"ADR-0017"),
        "ADR-0017 is the owner, never a related ADR of its own contract"
    );
    let checkout_source = top_level_row("checkout_source:");
    assert!(
        checkout_source.contains("G0(d)") && checkout_source.contains("checkout("),
        "checkout_source must name G0(d) and the checkout( projection"
    );
}

#[test]
fn root_kinds_are_the_closed_three_set_without_precursor_tokens() {
    // Size plus membership pins the exact set; the canon list itself is
    // never restated here (MEM951 — this contract owns it).
    let kinds = inline_bracket_items(top_level_row("root_kinds:"));
    assert_eq!(kinds.len(), 3, "root kind count drifted");
    assert!(kinds.contains(&"CstRoot"), "CstRoot lost");
    assert!(kinds.contains(&"AstRoot"), "AstRoot lost");
    assert!(
        kinds.contains(&"OracleExamBinding"),
        "OracleExamBinding (the third G0(d) root) lost"
    );
    for token in NON_ROOT_KIND_TOKENS {
        assert!(
            !kinds.contains(&token),
            "{token} is a precursor or sibling token, never a root kind here"
        );
    }
    // The composed payload root is a ProjectionRoots field (snake_case),
    // never a member of the parsed root-kind list either way it is
    // spelled.
    assert!(
        !kinds.contains(&"composed_checkout_root"),
        "composed_checkout_root is a field, not a root_kinds member"
    );
}

#[test]
fn typed_non_success_is_the_closed_two_set() {
    let failures = inline_bracket_items(top_level_row("typed_non_success:"));
    assert_eq!(failures.len(), 2, "typed non-success count drifted");
    assert!(
        failures.contains(&"IncompleteProjection"),
        "IncompleteProjection lost"
    );
    assert!(
        failures.contains(&"CanonicalFormUnspecified"),
        "CanonicalFormUnspecified lost"
    );
    for token in NON_TYPED_NON_SUCCESS_TOKENS {
        assert!(
            !failures.contains(&token),
            "{token} is a success, an MC-RES apply result, a completeness outcome or an anchor error, never a merkle typed non-success"
        );
    }
}

#[test]
fn two_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["MaterializedSection", "ProjectionRoots"],
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
            "MaterializedSection",
            &[
                "work",
                "legal_as_of",
                "known_as_of",
                "view_mode",
                "scope_kind",
            ],
        ),
        (
            "ProjectionRoots",
            &[
                "section",
                "cst_root",
                "ast_root",
                "oracle_exam_binding",
                "composed_checkout_root",
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
    // Sibling payload hashes stay out of the section identity: root_hash
    // is the composed checkout projection, quoted_hash is the G0(e)
    // TextAnchor, artifact_hash is ingest pipeline step 1.
    let section_fields = required_field_keys(block_of(&blocks, "MaterializedSection"));
    for token in ["root_hash", "quoted_hash", "artifact_hash"] {
        assert!(
            !section_fields.contains(&token),
            "{token} must never become a MaterializedSection field"
        );
    }
    // composed_checkout_root rides as the fifth ProjectionRoots field,
    // never as a root kind (checked against the parsed list elsewhere).
    let roots_fields = required_field_keys(block_of(&blocks, "ProjectionRoots"));
    assert!(
        roots_fields.contains(&"composed_checkout_root"),
        "ProjectionRoots lost the composed checkout root field"
    );
    // No hash-algorithm name is a required field of any entity (P2).
    for fields in [&section_fields, &roots_fields] {
        for algorithm in ["sha256", "blake3", "fnv"] {
            assert!(
                !fields.contains(&algorithm),
                "{algorithm} is a P2 decision, never a required field"
            );
        }
    }
}

#[test]
fn runtime_today_stays_design_only_for_both_entities() {
    let blocks = entity_blocks(CONTRACT_YAML);
    for name in ["MaterializedSection", "ProjectionRoots"] {
        assert_eq!(
            entity_scalar(block_of(&blocks, name), "runtime_today"),
            RUNTIME_TODAY_VALUE,
            "{name} must stay design-only"
        );
    }
}

#[test]
fn canonical_form_is_the_closed_six_row_table() {
    let roots: Vec<&str> = canonical_form_rows().iter().map(|row| row[0]).collect();
    assert_eq!(
        roots,
        vec![
            "CstRoot",
            "AstRoot",
            "OracleExamBinding",
            "composed_checkout_root",
            "DocumentaryPresence",
            "artifact_hash",
        ],
        "canonical form row count or root sequence drifted"
    );
}

#[test]
fn canonical_form_rows_pin_serialization_boundaries() {
    let rows = canonical_form_rows();
    let row_of = |root: &str| {
        rows.iter()
            .find(|row| row[0] == root)
            .unwrap_or_else(|| panic!("canonical_form row missing: {root}"))
    };
    // Green CST: the only exact-text contour (INV-09); never an identity,
    // ingest artifact or parser records (ADR-0013).
    let cst = row_of("CstRoot");
    assert_eq!(cst[1], "lossless_green_tree_of_the_section");
    for needle in ["component_id", "ingest", "parser"] {
        assert!(
            cst[2].contains(needle),
            "CstRoot never_as lost {needle}: {}",
            cst[2]
        );
    }
    // Red AST: semantic facade, never an exact-text proof (review-25 B.2
    // stage 6 ban).
    let ast = row_of("AstRoot");
    assert_eq!(ast[1], "semantic_red_tree_of_the_section");
    assert_eq!(ast[2], "exact_text_proof");
    // Oracle binding: fold approximates the oracle snapshot; drift heals
    // forward, never by writing the oracle tree back as canon.
    let oracle = row_of("OracleExamBinding");
    assert_eq!(oracle[1], "fold_vs_oracle_checksum");
    assert!(
        oracle[2].contains("canon") && oracle[2].contains("oracle_tree_back"),
        "OracleExamBinding never_as lost canon/oracle_tree_back: {}",
        oracle[2]
    );
    // Composed payload root: a field-level composition, never a fourth
    // root kind or a report field.
    let composed = row_of("composed_checkout_root");
    assert_eq!(composed[1], "composition_of_three_plus_checkout_key");
    assert!(
        composed[2].contains("fourth_root_kind")
            && composed[2].contains("completeness_report_field"),
        "composed_checkout_root never_as lost fourth-root/report boundaries: {}",
        composed[2]
    );
    // G0(f) repeal axis and ingest artifact hash: named only to be
    // excluded.
    let presence = row_of("DocumentaryPresence");
    assert_eq!(presence[1], "not_a_root");
    assert_eq!(presence[2], "root_kinds_member");
    let artifact = row_of("artifact_hash");
    assert_eq!(artifact[1], "pipeline_step_1_source_artifact");
    assert_eq!(artifact[2], "section_root");
}

#[test]
fn rebuild_equivalence_is_a_contract_property_not_a_hasher_test() {
    let section = section_between(
        CONTRACT_YAML,
        "rebuild_equivalence:",
        "checkout_projection:",
    );
    // The folded scalar wraps prose across lines; collapse whitespace so
    // phrase pins stay independent of line breaks.
    let normalized = section.split_whitespace().collect::<Vec<_>>().join(" ");
    for phrase in [
        "INV-01",
        // INV-11 pins the projection protocol determinism clause
        // (protocol version, view policy, ledger cut, source set, request).
        "INV-11",
        "identical ProjectionRoots",
        "repeated replay returns the same root hash",
        "pure function of the ledger prefix",
        "never of wall-clock time or insertion order",
        "not a runtime hasher test",
    ] {
        assert!(
            normalized.contains(phrase),
            "rebuild-equivalence lost phrase `{phrase}`"
        );
    }
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
        has_claim("The data owner is ADR-0017 G0(d)")
            && has_claim("not G0(e) AddressableTextUnit")
            && has_claim("not G0(f) DocumentaryPresence"),
        "owner-homonymy non-claims lost (G0(d) not G0(e)/G0(f))"
    );
    assert!(
        has_claim("third root is OracleExamBinding")
            && has_claim("not PresenceRoot")
            && has_claim("not artifact_hash"),
        "third-root non-claims lost"
    );
    assert!(
        has_claim("A hash is not a ComponentId"),
        "Git-inequalities non-claim lost"
    );
    assert!(
        has_claim("never an exact-text proof"),
        "AstRoot exact-text ban non-claim lost"
    );
    assert!(
        has_claim("not a fourth root_kind") && has_claim("not a CompletenessReport field"),
        "composed-root boundary non-claims lost"
    );
    assert!(
        has_claim("not a section Merkle root"),
        "quoted_hash boundary non-claim lost"
    );
    assert!(
        has_claim("Parser records are not a CST"),
        "parser-not-CST non-claim lost (ADR-0013)"
    );
    assert!(
        has_claim("Not a sixth clock"),
        "sixth-clock non-claim lost (ADR-0009)"
    );
    assert!(
        has_claim("Not the assertion lifecycle") && has_claim("not completeness outcomes"),
        "assertion/completeness boundary non-claims lost"
    );
    assert!(
        has_claim("InputDigest") && has_claim("FNV"),
        "digest homonymy non-claim lost"
    );
    assert!(
        has_claim("are P2") && has_claim("required field of any entity"),
        "hash-algorithm-stays-P2 non-claim lost"
    );
    assert!(
        has_claim("INV-02") && has_claim("never in insertion order"),
        "INV-02 canonical-order non-claim lost"
    );
    assert!(
        has_claim("OrderingConflict") && has_claim("never launders the conflict away"),
        "INV-03 non-laundering non-claim lost"
    );
    assert!(
        has_claim("no partial hash"),
        "IncompleteProjection no-partial-hash non-claim lost (R068 / INV-10)"
    );
    assert!(
        has_claim("Future effects never enter a historical section"),
        "INV-04 pending-effects non-claim lost"
    );
}

#[test]
fn neighbor_contract_tokens_never_mint_entity_keys() {
    // MEM947: raw-token isolation excludes the non_claims section — the
    // boundary prose there may legitimately name S01/S03 tokens (the
    // not-a-CompletenessReport-field and not-the-assertion-lifecycle
    // claims).
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
fn scope_and_view_refs_name_the_e25_contract_instead_of_copying_it() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let scope_ref = entity_scalar(block_of(&blocks, "MaterializedSection"), "scope_kind_ref");
    assert!(
        scope_ref.contains("QueryScope.scope")
            && scope_ref.contains("scope-aware-completeness-contract.yaml")
            && scope_ref.contains("E.2.5"),
        "scope_kind_ref must point at the E.2.5 QueryScope by name: {scope_ref}"
    );
    let view_ref = entity_scalar(block_of(&blocks, "MaterializedSection"), "view_mode_ref");
    assert!(
        view_ref.contains("view_modes")
            && view_ref.contains("scope-aware-completeness-contract.yaml")
            && view_ref.contains("MC-CHECKOUT"),
        "view_mode_ref must point at the MC-CHECKOUT view list by name: {view_ref}"
    );
    // The referenced closed sets are never re-minted as a second canon
    // table here: no zero-indent closed-set key of the E.2.5 contract may
    // appear in this YAML (the ref prose legitimately names them inline).
    for borrowed_set in [
        "query_scope_kinds:",
        "view_modes:",
        "completeness_outcomes:",
        "in_scope_block_reasons:",
        "scope_gap_outcomes:",
    ] {
        assert!(
            CONTRACT_YAML
                .lines()
                .all(|line| !line.starts_with(borrowed_set)),
            "second-canon table `{borrowed_set}` re-minted; the E.2.5 YAML owns it"
        );
    }
}

#[test]
fn checkout_projection_names_the_sibling_singular_root_hash() {
    let section = section_between(CONTRACT_YAML, "checkout_projection:", "non_claims:");
    assert_eq!(
        section_scalar(section, "report_root_hash_sibling"),
        "ProjectionRoots.composed_checkout_root",
        "the sibling pointer must stay the composed checkout root"
    );
    // MC-CHECKOUT carries the singular root_hash (review-25 B.3) — said
    // in the row's inline comment, which section_scalar cuts, so the
    // phrase is pinned on the raw section slice instead.
    assert!(
        section.contains("MC-CHECKOUT singular root_hash"),
        "the MC-CHECKOUT singular root_hash statement drifted"
    );
    assert_eq!(
        section_scalar(section, "three_roots_placement"),
        "beside_the_completeness_report_in_the_same_payload_contour"
    );
    assert_eq!(
        section_scalar(section, "never_inside"),
        "CompletenessReport_fields",
        "root hashing never moves into the CompletenessReport"
    );
    assert_eq!(
        section_scalar(section, "blocked_projection"),
        "IncompleteProjection_no_partial_hash",
        "a blocked projection emits no partial hash (INV-10 / R068)"
    );
}

#[test]
fn exactly_one_embed_exists_in_this_suite() {
    // D222: a second embed (the E.2.5 completeness YAML "for alignment")
    // would import the root_hash sibling homonym into these pins. Count
    // the embed-macro invocations in this very source file at test time —
    // a counter, never a raw-substring presence scan over the contract.
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let source_path = format!("{manifest_dir}/tests/merkle_roots.rs");
    let source = std::fs::read_to_string(&source_path)
        .unwrap_or_else(|error| panic!("suite source unreadable: {error}"));
    // The search term is assembled from pieces so this source file does
    // not contain the contiguous substring it counts.
    let embed_invocation = concat!("include_str", "!(");
    assert_eq!(
        source.matches(embed_invocation).count(),
        1,
        "the suite must keep exactly one embedded contract"
    );
}
