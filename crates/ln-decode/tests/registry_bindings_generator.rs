//! Registry binding generator for the 44-FZ corpus (M169 S02 T01) with
//! ladder paths (M171 S02 T03).
//!
//! Manual helper: decode a real consru_export edition (or the inline WordML
//! fixture), extract hierarchy markers with their ladder path and print
//! `kb-hierarchy-registry.yaml` binding lines. The output is pasted into the
//! registry by a human — never auto-applied.
//!
//! Ladder (R8-11 / D192): each node's effective path is the slash-joined
//! ladder of non-container segments from the unit down (`statya-93/punkt-4`).
//! Container levels (razdel/glava/paragraph) never enter a CC path. A
//! single-segment path is flat — printed without `path:` so the registry
//! key defaults to `number` (D192). Dedupe key is `(level, key_path)`, not
//! `(level, number)` — two `punkt-4` under different statya stay distinct.
//!
//! Only identifiers (level, number, path, cc) are printed — never raw text.
//!
//! Run: cargo test -p ln-decode --test registry_bindings_generator -- --nocapture

use std::collections::HashSet;
use std::fs;
use std::path::PathBuf;

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, HierarchyLevel, ParsedBlock, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};

/// One ladder node with its effective CC path.
#[derive(Debug, Clone, PartialEq, Eq)]
struct LadderNode {
    level: String,
    number: String,
    /// Slash-joined non-container segments (`statya-93/punkt-4`);
    /// `None` when flat (single segment or container-only, D192).
    path: Option<String>,
}

impl LadderNode {
    fn key_path(&self) -> &str {
        self.path.as_deref().unwrap_or(&self.number)
    }
}

fn token(level: HierarchyLevel) -> &'static str {
    match level {
        HierarchyLevel::Razdel => "razdel",
        HierarchyLevel::Glava => "glava",
        HierarchyLevel::Paragraph => "paragraph",
        HierarchyLevel::Statya => "statya",
        HierarchyLevel::Chast => "chast",
        HierarchyLevel::Punkt => "punkt",
        HierarchyLevel::Podpunkt => "podpunkt",
    }
}

/// Container levels never enter a CC path (R8-11: `statya-93/punkt-4` has no
/// `glava-3/...` prefix).
fn is_container(level: &str) -> bool {
    matches!(level, "razdel" | "glava" | "paragraph")
}

/// Enum order = nesting depth (Razdel < Glava < Paragraph < Statya < Chast
/// < Punkt < Podpunkt). Unknown levels behave as deepest (fail-closed reset).
fn depth(level: &str) -> usize {
    HierarchyLevel::all()
        .iter()
        .position(|candidate| token(*candidate) == level)
        .unwrap_or(usize::MAX)
}

/// Collect document-order hierarchy nodes with their ladder paths.
///
/// Pop-while-top-depth >= own-depth keeps the ladder nested: `statya-4` then
/// `punkt-1` then `punkt-4.1` then a new `punkt` replaces the previous punkt.
/// A container (glava) resets the ladder; its own path is flat (`None`).
fn collect_ladder(blocks: &[ParsedBlock]) -> Vec<LadderNode> {
    let mut ladder: Vec<(String, String)> = Vec::new();
    let mut out = Vec::new();
    for block in blocks {
        let Some(node) = extract_hierarchy(block) else {
            continue;
        };
        let level = token(node.level()).to_owned();
        let number = node.number().to_owned();
        let own_depth = depth(&level);
        while ladder
            .last()
            .is_some_and(|(top, _)| depth(top) >= own_depth)
        {
            ladder.pop();
        }
        ladder.push((level.clone(), number.clone()));
        let path = ladder
            .iter()
            .filter(|(top, _)| !is_container(top))
            .map(|(top, num)| format!("{top}-{num}"))
            .collect::<Vec<_>>()
            .join("/");
        let path = (path.split('/').count() >= 2).then_some(path);
        out.push(LadderNode {
            level,
            number,
            path,
        });
    }
    out
}

/// Print YAML binding lines for the flat scope (glava + statya, D192) and
/// return (glava, statya) counts. Nested levels are out of scope for the
/// 44-FZ flat registry — their ladder paths are reported separately by the
/// caller. Identifiers only, never raw text.
fn print_flat_bindings(nodes: &[LadderNode], needle: &str) -> (usize, usize) {
    let mut seen: Vec<(String, String)> = Vec::new();
    let mut glavas = 0usize;
    let mut statyas = 0usize;
    for node in nodes {
        if !matches!(node.level.as_str(), "glava" | "statya") {
            continue;
        }
        let key = (node.level.clone(), node.key_path().to_owned());
        if seen.contains(&key) {
            continue;
        }
        seen.push(key);
        match node.level.as_str() {
            "glava" => glavas += 1,
            "statya" => statyas += 1,
            _ => unreachable!(),
        }
        eprintln!(
            "  - {{path_needle: {needle}, level: {}, number: \"{}\", cc: cc:44-fz:{}-{}}}",
            node.level, node.number, node.level, node.number
        );
    }
    (glavas, statyas)
}

fn decode(xml: &[u8]) -> Vec<ParsedBlock> {
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m169-registry-generator").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        xml,
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("WordML must decode")
}

/// Inline WordML fixture: glava container, two statya units, nested punkt
/// ladders (one duplicate punkt-1 in statya-4, one punkt-1 under statya-5).
/// Git-tracked inline fixture — the ladder contract runs without the
/// consru_export corpus.
const INLINE_FIXTURE: &str = r#"<w:wordDocument xmlns:w="urn:word"><w:body>
<w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p>
<w:p><w:r><w:t>Статья 4. Требования к участникам</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый</w:t></w:r></w:p>
<w:p><w:r><w:t>4.1) пункт четыре точка один</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый дубль</w:t></w:r></w:p>
<w:p><w:r><w:t>Статья 5. Сфера применения</w:t></w:r></w:p>
<w:p><w:r><w:t>1) пункт первый в статье пять</w:t></w:r></w:p>
</w:body></w:wordDocument>"#;

#[test]
fn ladder_paths_and_flat_registry_inline_fixture() {
    let blocks = decode(INLINE_FIXTURE.as_bytes());
    let ladder = collect_ladder(&blocks);

    let by_level_number = |level: &str, number: &str| {
        ladder
            .iter()
            .filter(|n| n.level == level && n.number == number)
            .collect::<Vec<_>>()
    };

    // Containers stay flat: glava-1 has no CC path (key defaults to "1").
    let glava = by_level_number("glava", "1");
    assert_eq!(glava.len(), 1);
    assert_eq!(glava[0].path, None, "glava is a container, flat key");
    assert_eq!(glava[0].key_path(), "1");

    // Single-segment statya paths are flat too (D192: default key = number).
    let statya4 = by_level_number("statya", "4");
    assert_eq!(statya4.len(), 1);
    assert_eq!(statya4[0].path, None);
    assert_eq!(statya4[0].key_path(), "4");

    // punkt-1 under statya-4 gets the two-segment ladder path.
    let punkt1 = by_level_number("punkt", "1");
    assert_eq!(
        punkt1.len(),
        3,
        "punkt-1 appears in statya-4 (twice) and statya-5"
    );
    assert_eq!(punkt1[0].path.as_deref(), Some("statya-4/punkt-1"));

    // Compound numbers keep their ladder slot: punkt-4.1 under statya-4.
    let punkt41 = by_level_number("punkt", "4.1");
    assert_eq!(punkt41.len(), 1);
    assert_eq!(punkt41[0].path.as_deref(), Some("statya-4/punkt-4.1"));

    // Same number under a different statya → distinct path (R8-11):
    // punkt-1 under statya-5 is not the statya-4 punkt-1.
    let st5 = punkt1
        .iter()
        .find(|n| n.path.as_deref() == Some("statya-5/punkt-1"))
        .expect("punkt-1 under statya-5");
    assert_eq!(st5.path.as_deref(), Some("statya-5/punkt-1"));
    assert_ne!(punkt1[0].path, st5.path, "ladders must not collide");

    // Dedupe key is (level, key_path): the duplicate punkt-1 collapses.
    let mut seen: HashSet<(String, String)> = HashSet::new();
    let unique: Vec<&LadderNode> = ladder
        .iter()
        .filter(|n| seen.insert((n.level.clone(), n.key_path().to_owned())))
        .collect();
    assert_eq!(ladder.len(), 7, "7 nodes in the inline fixture");
    assert_eq!(unique.len(), 6, "one duplicate (punkt-1 twice in statya-4)");

    // Flat scope print: glava + statya only, never punkt (D192).
    let (glavas, statyas) = print_flat_bindings(&ladder, "law_2013-04-05_44-fz");
    assert_eq!(glavas, 1);
    assert_eq!(statyas, 2);
}

fn edition_path() -> Option<PathBuf> {
    let dir = std::env::var("CONSULTANT_EXPORT_DIR").unwrap_or_else(|_| "consru_export".to_owned());
    let p = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(dir)
        .join("consru_export/exports/npa/law_2013-04-05_44-fz")
        .join("edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml");
    if p.exists() {
        Some(p)
    } else {
        None
    }
}

#[test]
fn print_44fz_binding_lines() {
    let Some(path) = edition_path() else {
        eprintln!("SKIP: consru_export not available");
        return;
    };
    let bytes = fs::read(&path).expect("read edition-0118");
    let blocks = decode(&bytes);
    let ladder = collect_ladder(&blocks);

    // Ladder paths for out-of-scope nested levels (44-FZ flat registry):
    // reported as identifiers only, never raw text (D192 — punkt bindings
    // arrive in a later bounded wave).
    let mut seen_paths: HashSet<(String, String)> = HashSet::new();
    let mut nested = 0usize;
    for node in &ladder {
        if matches!(node.level.as_str(), "glava" | "statya") {
            continue;
        }
        if seen_paths.insert((node.level.clone(), node.key_path().to_owned())) {
            nested += 1;
        }
    }
    eprintln!("# nested levels out of scope: {nested} unique (level, path) keys");

    let (glavas, statyas) = print_flat_bindings(&ladder, "law_2013-04-05_44-fz");
    eprintln!("# 44-FZ edition-0118 bindings: glava={glavas} statya={statyas}");

    // Bounded sanity anchor (D192 / R8-14): 8 chapters; the consolidated
    // 2025 edition carries 94 unique article markers across the 1..114
    // numbering range (gaps are repealed or restructured articles — honest,
    // not a parser failure). Flat key: number.
    assert_eq!(glavas, 8, "expected exactly 8 glava markers, got {glavas}");
    assert_eq!(
        statyas, 94,
        "expected exactly 94 statya markers, got {statyas}"
    );
}
