//! D222/D273 pin-suite for the review-26 section 10 golden corpus
//! catalog (design-doc-as-data).
//!
//! `prd/architecture/golden-corpus-catalog.yaml` (owner:
//! review-26-section-10; the temporal model and model-crystal stay
//! `related` prose) is embedded via `include_str!` and pinned with plain
//! text/section assertions, mirroring `operation_registry.rs` (whose
//! `dash_items` / `section_between` helpers are copied here),
//! `evidence_anchor.rs` and `scope_aware_completeness.rs` (the
//! single-embed MEM990 twins). Per D222 the catalog mints no Rust
//! types, is not parsed by `OntologyCatalog` and is not a
//! closed_vocabularies row, so this suite stays parser-free line-shape
//! work: no YAML dependency, no Cargo.toml change (tests auto-discover).
//!
//! There is deliberately exactly one embed: a second embed (a P1
//! companion contract "for alignment" or the S02 sibling series) would
//! import a second canon into these pins. The single-embed invariant is
//! pinned by counting embed-macro invocations in this very source file
//! at test time (MEM990) — the needle is assembled so this comment adds
//! no textual occurrence.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor serde/serde_yaml and never references
//! the runtime crates it guards — coupling a catalog pin suite to
//! runtime types would invert the D222 boundary (see the
//! `operation_registry.rs` header).
//!
//! Case blocks are parsed by line shape (the bare two-space dash item
//! marker, then four-space snake_case field keys), never by a YAML
//! parser, and the forty Russian summaries are never restated here —
//! only their presence is pinned; ids, anchors, groups, tiers, statuses
//! and deps carry the actual pins.
//!
//! Negative surface (Q7): a 41st case or a missing GC-040, a duplicate
//! or reordered id, an anchor that stops matching its id digits, a tier
//! G4 or an emptied tier, a group outside the closed six, coverage
//! drift, flipping `authoritative`, promoting `lifecycle` off proposed,
//! laundering the bracketed bounded authority token, a second embed in
//! this suite, empty deps or a dep outside `allowed_deps`, an S02-owned
//! `related_tl_gc` key or sibling-series token, and collapsing the
//! three G0 homonyms all turn pins red on the tracked file itself — no
//! tmp fixtures, no runtime dependency (the pytest broken-catalog
//! fixture is S03-owned).

/// Embedded catalog (T01): the forty review-26 section 10 cases. Path
/// is relative to `crates/ln-kb-ontology/tests/`.
const CATALOG_YAML: &str = include_str!("../../../prd/architecture/golden-corpus-catalog.yaml");

/// Closed four-tier set per D273 (G0 Shape / G1 Official / G2 Hostile /
/// G3 End-to-end), declaration order.
const TIERS: [&str; 4] = ["G0", "G1", "G2", "G3"];

/// Closed six-group set, declaration order.
const GROUPS: [&str; 6] = [
    "assertion-bitemporal",
    "pending-effects",
    "structure-identity",
    "source-cst",
    "references",
    "procurement",
];

/// Per-group case counts in `GROUPS` order (review-26 section 10
/// grouping; 8+6+6+5+9+6 = 40).
const COVERAGE: [usize; 6] = [8, 6, 6, 5, 9, 6];

/// The eight P1-companion contract paths that are the only legal deps.
const ALLOWED_DEPS: [&str; 8] = [
    "prd/architecture/assertion-lifecycle-contract.yaml",
    "prd/architecture/pending-effects-contract.yaml",
    "prd/architecture/operation-registry.yaml",
    "prd/architecture/reference-binding-contract.yaml",
    "prd/architecture/evidence-anchor-contract.yaml",
    "prd/architecture/merkle-roots-contract.yaml",
    "prd/architecture/force-interval-set-contract.yaml",
    "prd/architecture/scope-aware-completeness-contract.yaml",
];

/// D273 G0 Shape set: the twenty synthetic-form case ids.
const TIER_G0_IDS: [&str; 20] = [
    "GC-001", "GC-002", "GC-006", "GC-008", "GC-009", "GC-010", "GC-011", "GC-012", "GC-013",
    "GC-014", "GC-016", "GC-017", "GC-019", "GC-020", "GC-025", "GC-027", "GC-028", "GC-029",
    "GC-031", "GC-032",
];

/// D273 G1 Official set: the two verified-official-act case ids.
const TIER_G1_IDS: [&str; 2] = ["GC-021", "GC-022"];

/// D273 G2 Hostile set: the twelve conflict/incompleteness/correction
/// case ids.
const TIER_G2_IDS: [&str; 12] = [
    "GC-003", "GC-004", "GC-005", "GC-007", "GC-015", "GC-018", "GC-023", "GC-024", "GC-026",
    "GC-030", "GC-033", "GC-034",
];

/// D273 G3 End-to-end set: the six temporal-QA/procurement trace ids.
const TIER_G3_IDS: [&str; 6] = ["GC-035", "GC-036", "GC-037", "GC-038", "GC-039", "GC-040"];

/// One parsed catalog case. The Russian `summary` value is deliberately
/// not captured — only its presence is pinned, never its text.
struct CaseBlock {
    id: String,
    review_anchor: usize,
    group: String,
    tier: String,
    status: String,
    deps: Vec<String>,
    summary_seen: bool,
}

/// Parse the `cases:` section by line shape: the bare two-space dash
/// item marker opens a block, four-space snake_case keys fill it, and
/// six-space dash items extend the `deps:` list. Panics when a field or
/// dash item appears outside a block; a missing `cases:` header fails
/// closed.
fn case_blocks(yaml: &str) -> Vec<CaseBlock> {
    let start = yaml
        .lines()
        .position(|line| line == "cases:")
        .unwrap_or_else(|| panic!("catalog cases section missing"));
    let mut blocks: Vec<CaseBlock> = Vec::new();
    let mut in_deps = false;
    for line in yaml.lines().skip(start + 1) {
        if !line.starts_with(' ') {
            // The next zero-indent key (or EOF) ends the case list.
            break;
        }
        if line.starts_with("  -") && line.trim() == "-" {
            blocks.push(CaseBlock {
                id: String::new(),
                review_anchor: 0,
                group: String::new(),
                tier: String::new(),
                status: String::new(),
                deps: Vec::new(),
                summary_seen: false,
            });
            in_deps = false;
            continue;
        }
        let Some(block) = blocks.last_mut() else {
            panic!("case field outside a case block: {line:?}");
        };
        if let Some(dep) = line.strip_prefix("      - ") {
            assert!(in_deps, "dash item outside a deps list: {line:?}");
            block.deps.push(dep.trim().to_owned());
            continue;
        }
        let Some(rest) = line.strip_prefix("    ") else {
            continue;
        };
        in_deps = false;
        if let Some(value) = rest.strip_prefix("id: ") {
            block.id = value.trim().to_owned();
        } else if let Some(value) = rest.strip_prefix("review_anchor: ") {
            block.review_anchor = value
                .trim()
                .parse()
                .unwrap_or_else(|_| panic!("review_anchor is not an integer: {value}"));
        } else if let Some(value) = rest.strip_prefix("group: ") {
            block.group = value.trim().to_owned();
        } else if let Some(value) = rest.strip_prefix("tier: ") {
            block.tier = value.trim().to_owned();
        } else if let Some(value) = rest.strip_prefix("status: ") {
            block.status = value.trim().to_owned();
        } else if rest.trim() == "deps:" {
            in_deps = true;
        } else if rest.starts_with("summary:") {
            block.summary_seen = true;
        }
    }
    blocks
}

/// Dash-list items of a section slice, trimmed. Copy of the
/// `operation_registry.rs` helper (kept local per the no-import rule).
fn dash_items(section: &str) -> Vec<&str> {
    section
        .lines()
        .filter_map(|line| line.trim().strip_prefix("- "))
        .map(str::trim)
        .collect()
}

/// Slice from `start_marker` to the pinned `end_marker` (exclusive;
/// missing end markers fall back to end-of-file). Panics when the
/// catalog loses a pinned section entirely. End markers are the next
/// sibling key so the slice cannot swallow a later closed set (the
/// MEM1044 `effect_selector_modes` lesson).
fn section_between<'a>(yaml: &'a str, start_marker: &str, end_marker: &str) -> &'a str {
    let start = yaml
        .find(start_marker)
        .unwrap_or_else(|| panic!("catalog section missing: {start_marker}"));
    let tail = &yaml[start..];
    let end = tail.find(end_marker).unwrap_or(tail.len());
    &tail[..end]
}

/// The `coverage:` mapping rows as (group, count) pairs, declaration
/// order. Only two-space `key: integer` rows parse; anything else in
/// the slice is ignored rather than guessed.
fn coverage_rows(yaml: &str) -> Vec<(&str, usize)> {
    section_between(yaml, "coverage:", "allowed_deps:")
        .lines()
        .filter_map(|line| {
            let rest = line.strip_prefix("  ")?;
            if rest.starts_with(' ') || rest.starts_with('-') {
                return None;
            }
            let (key, value) = rest.split_once(':')?;
            let count: usize = value.split('#').next()?.trim().parse().ok()?;
            Some((key.trim(), count))
        })
        .collect()
}

/// The quoted `non_claims:` dash items with their quotes stripped.
fn non_claims(yaml: &str) -> Vec<String> {
    section_between(yaml, "non_claims:", "tiers:")
        .lines()
        .filter_map(|line| line.trim().strip_prefix("- "))
        .map(|item| item.trim().trim_matches('"').to_owned())
        .collect()
}

#[test]
fn catalog_embeds_as_data_and_pins_schema_identity() {
    assert!(!CATALOG_YAML.is_empty(), "catalog failed to embed");
    assert!(
        CATALOG_YAML.contains("schema_version: law-nexus-golden-corpus-catalog/v1"),
        "catalog schema identity drifted"
    );
    assert!(
        CATALOG_YAML.contains("owner: review-26-section-10"),
        "catalog owner drifted off review-26 section 10"
    );
}

#[test]
fn catalog_lifecycle_stays_proposed_and_non_authoritative() {
    // Parsed-row pins (not substring promotion talk): every
    // lifecycle/authoritative row anywhere in the file must keep its
    // design-only value, and exactly one of each row may exist.
    let mut lifecycle_rows = 0;
    let mut authority_rows = 0;
    for line in CATALOG_YAML.lines() {
        let row = line.trim_start();
        if row.starts_with("lifecycle:") {
            lifecycle_rows += 1;
            assert_eq!(
                row, "lifecycle: \"[proposed]\"",
                "lifecycle row drifted off proposed"
            );
        }
        if row.starts_with("authoritative:") {
            authority_rows += 1;
            assert_eq!(row, "authoritative: false", "authoritative row flipped");
        }
    }
    assert_eq!(lifecycle_rows, 1, "exactly one lifecycle row is expected");
    assert_eq!(
        authority_rows, 1,
        "exactly one authoritative row is expected"
    );
    // Authority-laundering guard (MEM1111): the bracketed bounded
    // lifecycle token must not appear anywhere in the catalog. The
    // needle is assembled so this suite never spells the token out,
    // even in negations.
    let bounded_token = concat!("[", "bounded", "]");
    assert!(
        !CATALOG_YAML.contains(bounded_token),
        "the catalog must never launder runtime authority"
    );
}

#[test]
fn tiers_are_the_closed_four_set_in_d273_order() {
    assert_eq!(
        dash_items(section_between(CATALOG_YAML, "tiers:", "groups:")),
        TIERS.to_vec(),
        "tier closed set or order drifted"
    );
}

#[test]
fn groups_are_the_closed_six_set_in_canonical_order() {
    assert_eq!(
        dash_items(section_between(CATALOG_YAML, "groups:", "statuses:")),
        GROUPS.to_vec(),
        "group closed set or order drifted"
    );
}

#[test]
fn statuses_section_stays_exactly_design_only() {
    assert_eq!(
        dash_items(section_between(CATALOG_YAML, "statuses:", "coverage:")),
        vec!["design-only"],
        "status closed set drifted"
    );
}

#[test]
fn coverage_map_pins_the_six_group_counts() {
    let rows = coverage_rows(CATALOG_YAML);
    let expected: Vec<(&str, usize)> = GROUPS
        .iter()
        .zip(COVERAGE)
        .map(|(group, count)| (*group, count))
        .collect();
    assert_eq!(rows, expected, "coverage mapping drifted");
    assert_eq!(
        rows.iter().map(|&(_, count)| count).sum::<usize>(),
        40,
        "coverage rows must sum to the forty cases"
    );
}

#[test]
fn allowed_deps_are_the_eight_companion_paths_once_each() {
    let allowed = dash_items(section_between(CATALOG_YAML, "allowed_deps:", "cases:"));
    assert_eq!(allowed.len(), 8, "allowed_deps cardinality drifted");
    assert_eq!(
        allowed,
        ALLOWED_DEPS.to_vec(),
        "allowed_deps must equal the eight P1-companion paths, once each"
    );
}

#[test]
fn exactly_forty_cases_are_anchored_in_order() {
    let blocks = case_blocks(CATALOG_YAML);
    assert_eq!(blocks.len(), 40, "the catalog must carry exactly 40 cases");
    // Positional pins cover order, uniqueness, the 1..=40 anchor
    // sequence, and id trailing digits == review anchor at once.
    for (position, block) in blocks.iter().enumerate() {
        let number = position + 1;
        assert_eq!(
            block.id,
            format!("GC-{number:03}"),
            "case #{number} id drifted"
        );
        assert_eq!(
            block.review_anchor, number,
            "case #{number} review_anchor drifted"
        );
        assert!(block.summary_seen, "case {} lost its summary row", block.id);
    }
}

#[test]
fn every_case_group_is_closed_and_counts_match_coverage() {
    let blocks = case_blocks(CATALOG_YAML);
    for block in &blocks {
        assert!(
            GROUPS.contains(&block.group.as_str()),
            "case {} group {} is outside the closed six",
            block.id,
            block.group
        );
    }
    for (group, declared) in coverage_rows(CATALOG_YAML) {
        let actual = blocks.iter().filter(|block| block.group == group).count();
        assert_eq!(
            actual, declared,
            "group {group} case count drifted from the coverage map"
        );
    }
}

#[test]
fn every_case_tier_is_closed_and_all_four_tiers_are_exercised() {
    let blocks = case_blocks(CATALOG_YAML);
    for block in &blocks {
        assert!(
            TIERS.contains(&block.tier.as_str()),
            "case {} tier {} is outside the closed four",
            block.id,
            block.tier
        );
    }
    for tier in TIERS {
        assert!(
            blocks.iter().any(|block| block.tier == tier),
            "tier {tier} must carry at least one case"
        );
    }
}

#[test]
fn every_case_status_is_design_only() {
    for block in case_blocks(CATALOG_YAML) {
        assert_eq!(
            block.status, "design-only",
            "case {} status drifted off design-only",
            block.id
        );
    }
}

#[test]
fn every_case_has_nonempty_deps_within_allowed_deps() {
    // Parsed-list membership only (MEM951/MEM1074): never a substring
    // scan over the whole file — boundary prose and non-claims may
    // legitimately name companion paths.
    let allowed = dash_items(section_between(CATALOG_YAML, "allowed_deps:", "cases:"));
    for block in case_blocks(CATALOG_YAML) {
        assert!(
            !block.deps.is_empty(),
            "case {} must exercise at least one companion contract",
            block.id
        );
        for dep in &block.deps {
            assert!(
                allowed.contains(&dep.as_str()),
                "case {} dep {dep} is outside allowed_deps",
                block.id
            );
        }
    }
}

#[test]
fn s02_sibling_series_stays_out_of_the_catalog() {
    assert!(
        !CATALOG_YAML
            .lines()
            .any(|line| line.trim_start().starts_with("related_tl_gc:")),
        "related_tl_gc is S02-owned and must never become a catalog key"
    );
    assert!(
        !CATALOG_YAML.contains("TL-GC"),
        "the S02 sibling-series token must stay out of the catalog"
    );
}

#[test]
fn boundary_and_non_claims_keep_the_three_g0_homonyms_distinct() {
    // MEM990: the boundary is a folded scalar — whitespace-normalize
    // before phrase pins so line wrapping can never fake or break a
    // pin.
    let boundary = section_between(CATALOG_YAML, "boundary: >", "non_claims:");
    let collapsed: String = boundary.split_whitespace().collect();
    for phrase in [
        "Three G0 homonyms are distinct and must never be collapsed",
        "the parser evidence-ladder G0 of \
         prd/parser/representative_golden_corpus_acceptance_protocol.md",
        "the disposition/ADR labels G0(a-g) of the P1 dispositions",
        "the corpus-tier G0 Shape of this catalog",
    ] {
        let phrase = phrase.split_whitespace().collect::<String>();
        assert!(
            collapsed.contains(&phrase),
            "boundary lost the three-G0-homonyms phrase `{phrase}`"
        );
    }
    let claims = non_claims(CATALOG_YAML);
    for needle in [
        "stay distinct and are never collapsed",
        "No case execution",
        "never runs them",
        "No Rust enum",
        "Not OntologyCatalog input",
        "closed_vocabularies row",
        "stays proposed and non-authoritative",
    ] {
        assert!(
            claims.iter().any(|claim| claim.contains(needle)),
            "non_claims lost the `{needle}` disclaimer"
        );
    }
}

#[test]
fn d273_tier_sets_pin_the_exact_forty_ids() {
    let blocks = case_blocks(CATALOG_YAML);
    let ids_of = |tier: &str| -> Vec<String> {
        blocks
            .iter()
            .filter(|block| block.tier == tier)
            .map(|block| block.id.clone())
            .collect()
    };
    assert_eq!(
        ids_of("G0"),
        TIER_G0_IDS.to_vec(),
        "D273 G0 Shape id set drifted"
    );
    assert_eq!(
        ids_of("G1"),
        TIER_G1_IDS.to_vec(),
        "D273 G1 Official id set drifted"
    );
    assert_eq!(
        ids_of("G2"),
        TIER_G2_IDS.to_vec(),
        "D273 G2 Hostile id set drifted"
    );
    assert_eq!(
        ids_of("G3"),
        TIER_G3_IDS.to_vec(),
        "D273 G3 End-to-end id set drifted"
    );
}

#[test]
fn exactly_one_embed_exists_in_this_suite() {
    // MEM990: the needle is assembled so this assertion adds no textual
    // occurrence, and the suite source is read back from disk at test
    // time — a second embed would import a companion contract or the
    // S02 sibling series into these pins.
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let source_path = format!("{manifest_dir}/tests/golden_corpus_catalog.rs");
    let source = std::fs::read_to_string(&source_path)
        .unwrap_or_else(|error| panic!("suite source unreadable: {error}"));
    let embed_invocation = concat!("include_str", "!(");
    assert_eq!(
        source.matches(embed_invocation).count(),
        1,
        "exactly one embed is allowed; a second YAML embed (a companion \
         contract or the S02 sibling series \"for alignment\") would \
         import a second canon into these pins"
    );
}
