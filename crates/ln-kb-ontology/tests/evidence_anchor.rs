//! D222/D241 pin-suite for the review-26 P0-7 evidence anchor contract
//! (design-doc-as-data).
//!
//! `prd/architecture/evidence-anchor-contract.yaml` (owner: ADR-0010
//! alone; ADR-0013 and ADR-0017 are related_adr homonym surfaces only,
//! never owners) is embedded via `include_str!` and pinned with plain
//! text/section assertions, mirroring `reference_binding.rs` (E.2.2) and
//! `assertion_lifecycle.rs` (E.2.7). Per D222/D241/MEM949 the contract
//! carries neither `rust_path` nor `rust_enum`, is not a
//! `closed_vocabularies` row and is not parsed by `OntologyCatalog`, so
//! this suite stays parser-free string/section work and adds no yaml
//! dependency (Cargo.toml stays untouched; tests auto-discover).
//!
//! There is deliberately exactly one embed: a second embed (kb-ontology
//! "for alignment" or the ln-decode crate "for homonym checks") would
//! import a second canon or the decoder homonym into these pins. The
//! single-embed invariant itself is pinned by counting the embed-macro
//! invocations in this very source file at test time (MEM990) — a
//! counter, never a substring scan over the contract.
//!
//! This suite deliberately contains no `use` items at all: it imports
//! neither `ln_kb_ontology` nor `ln_temporal` nor any other crate, and
//! the living `ln-decode::EvidenceAnchor` decoder homonym stays prose in
//! the YAML non_claims — coupling this suite to the runtime types it
//! guards would invert the D222 boundary.
//!
//! Negative surface (Q7): inventing a seventh selector scheme
//! (`LineRange`/`PdfRect`), minting a third PascalCase entity key
//! (`EvidenceSpan:`, `SourceBlock:`, `TextAnchor:`,
//! `CoverageCertificate:`, PROV-O `Entity:`/`Activity:`), promoting
//! lifecycle past `[proposed]` or flipping `authoritative`, moving
//! ownership off ADR-0010 (including onto ADR-0017), dropping, widening
//! or reordering the 8+5 review-26 required fields, moving
//! `runtime_today` past `none`, losing the ln-decode homonym /
//! no-Rust-types / PROV-O non-claims, or adding a second embed all turn
//! pins red on the tracked files themselves — no tmp fixtures, no
//! runtime dependency. Absence pins over `selector_scheme` run on parsed
//! items, not raw substrings, because the contract's own comments and
//! non_claims legitimately name the excluded tokens (MEM951).

/// Embedded contract (T01): the P0-7 EvidenceAnchor/EvidenceBundle layer.
/// Path is relative to `crates/ln-kb-ontology/tests/`.
const CONTRACT_YAML: &str = include_str!("../../../prd/architecture/evidence-anchor-contract.yaml");

/// Closed six-scheme selector set (review-26 P0-7), canonical order.
const SELECTOR_SCHEMES: [&str; 6] = [
    "ByteRange",
    "CharacterRange",
    "XPath",
    "JsonPointer",
    "PageRegion",
    "TokenRange",
];

/// Tokens that must never join the closed scheme set (seventh-scheme guard).
const REJECTED_SCHEMES: [&str; 2] = ["LineRange", "PdfRect"];

/// Review-26 P0-7 required-field canon for EvidenceAnchor, declaration order.
const EVIDENCE_ANCHOR_FIELDS: [&str; 8] = [
    "artifact_id",
    "artifact_hash",
    "rendition_id",
    "selector_scheme",
    "selector",
    "quoted_hash",
    "capture_method",
    "extractor_version",
];

/// Review-26 P0-7 required-field canon for EvidenceBundle, declaration order.
const EVIDENCE_BUNDLE_FIELDS: [&str; 5] = [
    "supporting_anchors",
    "contradicting_anchors",
    "qualifying_anchors",
    "primary_source_anchor",
    "source_authority_classes",
];

/// Neighbor names that must never appear at entity depth: the crosswalk
/// alias, the still-deferred glossary rows, the G0(e) identity floor, the
/// P0-8 neighbor and the two PROV-O projections (MEM947-style isolation).
const NEIGHBOR_ENTITY_KEYS: [&str; 6] = [
    "EvidenceSpan",
    "SourceBlock",
    "TextAnchor",
    "CoverageCertificate",
    "Entity",
    "Activity",
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

/// Line indices of two-space-indented PascalCase-colon lines — exactly the
/// shape of an entity entry under `entities:`. Deeper field lines, folded
/// scalar continuations, dash items and lowercase keys never match, so a
/// stray `EvidenceSpan:` or PROV-O `Entity:` entity key would be caught
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
/// key line (or EOF — the last body spans into `non_claims:`). Every
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

/// Field keys inside the `required_fields:` subsection of an entity body
/// (six-space mapping form, D244/MEM986). The subsection ends at the next
/// four-space key (`runtime_today`); eight-space folded-scalar
/// continuations are skipped, so prose colons cannot masquerade as field
/// keys.
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

#[test]
fn contract_embeds_as_data_and_pins_schema_identity() {
    assert!(!CONTRACT_YAML.is_empty(), "contract failed to embed");
    assert!(
        CONTRACT_YAML.contains("schema_version: law-nexus-evidence-anchor-contract/v1"),
        "contract schema identity drifted"
    );
}

#[test]
fn contract_lifecycle_stays_proposed_and_non_authoritative() {
    assert!(CONTRACT_YAML.contains("lifecycle: \"[proposed]\""));
    assert!(CONTRACT_YAML.contains("authoritative: false"));
    // Authority-laundering guards: promotion of the design contract to
    // bounded/runtime authority must break this pin before any consumer
    // exists (mirrors reference_binding.rs).
    assert!(!CONTRACT_YAML.contains("authoritative: true"));
    assert!(!CONTRACT_YAML.contains("[bounded]"));
}

#[test]
fn header_points_at_owner_adr_0010_with_related_homonym_adrs() {
    assert!(
        CONTRACT_YAML.contains("owner_adr: ADR-0010"),
        "ADR-0010 must stay the sole owner"
    );
    assert!(
        CONTRACT_YAML.contains("related_adr: [ADR-0013, ADR-0017]"),
        "related homonym surfaces drifted"
    );
    assert!(
        !CONTRACT_YAML.contains("owner_adr: ADR-0017"),
        "ADR-0017 is a related G0(a) homonym surface, never the owner"
    );
    assert!(
        !CONTRACT_YAML.contains("owner_adr: ADR-0013"),
        "ADR-0013 is a related emission surface, never the owner"
    );
}

#[test]
fn selector_scheme_is_the_closed_six_set_in_canon_order() {
    let schemes = top_level_dash_items(CONTRACT_YAML, "selector_scheme:");
    assert_eq!(schemes.len(), 6, "selector_scheme cardinality drifted");
    assert_eq!(
        schemes,
        SELECTOR_SCHEMES.to_vec(),
        "selector_scheme set/order drifted"
    );
    // Parsed-item checks, not raw substrings: the contract's comments and
    // non_claims legitimately name excluded tokens (MEM951).
    for token in REJECTED_SCHEMES {
        assert!(
            !schemes.contains(&token),
            "seventh selector scheme {token} minted"
        );
    }
}

#[test]
fn two_entities_are_declared_exactly_once_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    assert_eq!(
        names,
        vec!["EvidenceAnchor", "EvidenceBundle"],
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
fn every_entity_carries_its_review26_required_fields() {
    let blocks = entity_blocks(CONTRACT_YAML);
    assert_eq!(
        required_field_keys(block_of(&blocks, "EvidenceAnchor")),
        EVIDENCE_ANCHOR_FIELDS.to_vec(),
        "EvidenceAnchor: required_fields drifted"
    );
    assert_eq!(
        required_field_keys(block_of(&blocks, "EvidenceBundle")),
        EVIDENCE_BUNDLE_FIELDS.to_vec(),
        "EvidenceBundle: required_fields drifted"
    );
}

#[test]
fn both_entities_stay_design_only_runtime_none() {
    for block in entity_blocks(CONTRACT_YAML) {
        assert_eq!(
            entity_scalar(&block, "runtime_today"),
            "none",
            "{} must stay design-only",
            block.name
        );
    }
}

#[test]
fn non_claims_carry_homonymy_no_rust_types_and_prov_o_projection() {
    let claims = top_level_dash_items(CONTRACT_YAML, "non_claims:");
    let has_claim = |needle: &str| claims.iter().any(|claim| claim.contains(needle));
    assert!(
        has_claim("No Rust types are minted"),
        "no-Rust-types non-claim lost (D216 / D098)"
    );
    assert!(
        has_claim("ln-decode EvidenceAnchor"),
        "ln-decode decode-homonymy non-claim lost"
    );
    assert!(
        has_claim("crosswalk alias"),
        "EvidenceSpan alias non-claim lost"
    );
    assert!(
        has_claim("TextAnchor identity floor"),
        "G0(e) floor separation non-claim lost"
    );
    assert!(
        has_claim("merkle section root"),
        "quoted_hash/merkle separation non-claim lost"
    );
    assert!(
        has_claim("may coexist"),
        "coexisting-anchor non-claim lost (review-26 [11])"
    );
    assert!(
        has_claim("PROV-O is an external projection"),
        "PROV-O external-projection non-claim lost"
    );
    assert!(
        has_claim("deferred-undefined"),
        "SourceBlock stays-deferred non-claim lost"
    );
    assert!(has_claim("E.2.7"), "not-the-assertion-FSM non-claim lost");
    assert!(has_claim("P0-8"), "not-CoverageCertificate non-claim lost");
    assert!(
        has_claim("review-case extractor_version"),
        "review-case field separation non-claim lost"
    );
}

#[test]
fn no_third_entity_is_minted_at_entity_depth() {
    let blocks = entity_blocks(CONTRACT_YAML);
    let names: Vec<&str> = blocks.iter().map(|block| block.name.as_str()).collect();
    for key in NEIGHBOR_ENTITY_KEYS {
        assert!(!names.contains(&key), "{key} minted as an entity key");
        assert!(
            !CONTRACT_YAML.contains(&format!("\n  {key}:")),
            "two-space `{key}:` entity-depth key detected"
        );
    }
}

#[test]
fn exactly_one_embed_exists_in_this_suite() {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let source_path = format!("{manifest_dir}/tests/evidence_anchor.rs");
    let source = std::fs::read_to_string(&source_path)
        .unwrap_or_else(|error| panic!("suite source unreadable: {error}"));
    let embed_invocation = concat!("include_str", "!(");
    assert_eq!(
        source.matches(embed_invocation).count(),
        1,
        "exactly one embed is allowed; a second YAML embed (kb-ontology or \
         ln-decode \"for alignment\") would import sibling homonyms into \
         these pins"
    );
}
