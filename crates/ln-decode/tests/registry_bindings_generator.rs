//! Registry binding generator for the 44-FZ corpus (M169 S02 T01, ladder
//! paths M171 S02 T03), retargeted onto the public candidate API
//! (M202-9qf3ta S01 T03).
//!
//! Manual helper: decode a real consru_export edition (or the inline WordML
//! fixture), run the public `extract_hierarchy_candidates` extraction and
//! print `kb-hierarchy-registry.yaml` binding lines. The output is pasted
//! into the registry by a human — never auto-applied. The extraction
//! boundary is carried by the report type itself
//! (`HierarchyCandidateReport::HIERARCHY_CANDIDATE_NON_CLAIMS`): candidates
//! mint no ComponentConcept, are never auto-applied as YAML and are never
//! registry legal truth.
//!
//! The private ladder algorithm is gone: ladder semantics (R8-11 / D192) now
//! have one implementation in `extract_hierarchy_candidates` — catalog-token
//! non-container ladder paths (`statya-93/punkt-4`), container levels
//! (razdel/glava/paragraph) never enter a path, single-segment paths stay
//! flat with the registry key defaulting to `number` (D192), and
//! `(level, key_path)` first-wins dedupe with typed `DuplicateKey`
//! diagnostics. `ProviderComment` blocks are skipped by style and never
//! inflate counts.
//!
//! Only identifiers (level, number, path, cc) are printed — never raw text.
//!
//! Run: cargo test -p ln-decode --test registry_bindings_generator -- --nocapture

use std::fs;
use std::path::PathBuf;

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, HierarchyLevel, ParsedBlock, PayloadRef},
    hierarchy::{extract_hierarchy_candidates, HierarchyCandidate, HierarchyExtractDiagnostic},
    ports::BlockDecoderPort,
};

/// Print YAML binding lines for the flat scope (glava + statya, D192) and
/// return (glava, statya) counts. Candidates arrive already unique
/// first-wins by `(level, key_path)` from `extract_hierarchy_candidates` —
/// no second dedupe here; every skipped repeat lives in the report's typed
/// diagnostics. Nested levels are out of scope for the 44-FZ flat registry.
/// Identifiers only, never raw text.
fn print_flat_bindings(candidates: &[HierarchyCandidate], needle: &str) -> (usize, usize) {
    let mut glavas = 0usize;
    let mut statyas = 0usize;
    for candidate in candidates {
        let level = candidate.catalog_token();
        match level {
            "glava" => glavas += 1,
            "statya" => statyas += 1,
            _ => continue,
        }
        eprintln!(
            "  - {{path_needle: {needle}, level: {}, number: \"{}\", cc: cc:44-fz:{}-{}}}",
            level,
            candidate.number(),
            level,
            candidate.number()
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
/// Git-tracked inline fixture — same bytes as `hierarchy_candidates`; the
/// retargeted contract runs without the consru_export corpus.
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
    let report = extract_hierarchy_candidates(&blocks);

    // Raw hits (duplicates included) vs first-wins unique candidates: the
    // duplicate punkt-1 under statya-4 collapses into one typed diagnostic.
    assert_eq!(report.extracted_count(), 7, "7 marker hits in the fixture");
    assert_eq!(report.unique_count(), 6, "duplicate punkt-1 collapses");
    assert_eq!(report.candidates().len(), report.unique_count());
    assert_eq!(
        report.diagnostics().len(),
        1,
        "exactly one DuplicateKey diagnostic"
    );
    match &report.diagnostics()[0] {
        HierarchyExtractDiagnostic::DuplicateKey {
            level,
            key_path,
            first_index,
            later_index,
        } => {
            assert_eq!(*level, HierarchyLevel::Punkt);
            assert_eq!(key_path, "statya-4/punkt-1");
            // Indices address the raw document-order hit stream (7 hits).
            assert_eq!(*first_index, 2);
            assert_eq!(*later_index, 4);
        }
    }

    // Deterministic document order preserved through the generator path.
    let keys: Vec<&str> = report
        .candidates()
        .iter()
        .map(|candidate| candidate.key_path())
        .collect();
    assert_eq!(
        keys,
        vec![
            "1",
            "4",
            "statya-4/punkt-1",
            "statya-4/punkt-4.1",
            "5",
            "statya-5/punkt-1",
        ],
        "document order with catalog-token ladder paths"
    );

    let by_key_path = |key_path: &str| -> &HierarchyCandidate {
        report
            .candidates()
            .iter()
            .find(|candidate| candidate.key_path() == key_path)
            .unwrap_or_else(|| panic!("candidate {key_path} must exist"))
    };

    // Containers stay flat: glava-1 has no CC path (key defaults to "1").
    let glava = by_key_path("1");
    assert_eq!(glava.level(), HierarchyLevel::Glava);
    assert_eq!(glava.catalog_token(), "glava");
    assert_eq!(glava.number(), "1");
    assert_eq!(glava.path(), None, "glava is a container, flat key");
    assert_eq!(glava.key_path(), "1");

    // Single-segment statya paths are flat too (D192: default key = number).
    let statya4 = by_key_path("4");
    assert_eq!(statya4.level(), HierarchyLevel::Statya);
    assert_eq!(statya4.catalog_token(), "statya");
    assert_eq!(statya4.path(), None);
    assert_eq!(statya4.key_path(), "4");

    // punkt-1 under statya-4 gets the two-segment ladder path.
    let punkt1 = by_key_path("statya-4/punkt-1");
    assert_eq!(punkt1.level(), HierarchyLevel::Punkt);
    assert_eq!(punkt1.catalog_token(), "punkt");
    assert_eq!(punkt1.number(), "1");
    assert_eq!(punkt1.path(), Some("statya-4/punkt-1"));

    // Same number under a different statya → distinct ladder key (R8-11).
    let st5 = by_key_path("statya-5/punkt-1");
    assert_eq!(st5.path(), Some("statya-5/punkt-1"));
    assert_ne!(punkt1.path(), st5.path(), "ladders must not collide");

    // Compound numbers keep their ladder slot: punkt-4.1 under statya-4.
    let punkt41 = by_key_path("statya-4/punkt-4.1");
    assert_eq!(punkt41.number(), "4.1");
    assert_eq!(punkt41.path(), Some("statya-4/punkt-4.1"));

    // Flat scope print: glava + statya only, never punkt (D192). The
    // duplicate punkt-1 emits no second binding line.
    let (glavas, statyas) = print_flat_bindings(report.candidates(), "law_2013-04-05_44-fz");
    assert_eq!(glavas, 1);
    assert_eq!(statyas, 2);
}

const CONSULTANT_EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
const CONSULTANT_EXPORT_DIR_DEFAULT: &str = "consru_export";

/// CONSULTANT_EXPORT_DIR with empty-as-unset semantics (M185 S03): unset,
/// empty, or whitespace-only values fall back to the default export dir.
fn consultant_export_dir() -> String {
    match std::env::var(CONSULTANT_EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => CONSULTANT_EXPORT_DIR_DEFAULT.to_owned(),
    }
}

fn edition_path() -> Option<PathBuf> {
    let dir = consultant_export_dir();
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
    let report = extract_hierarchy_candidates(&blocks);

    // Honest dedupe reporting: every skipped repeat is a typed diagnostic.
    eprintln!(
        "# duplicate (level, key_path) hits skipped: {} (extracted={} unique={})",
        report.diagnostics().len(),
        report.extracted_count(),
        report.unique_count()
    );

    // Ladder paths for out-of-scope nested levels (44-FZ flat registry):
    // reported as identifiers only, never raw text (D192 — punkt bindings
    // arrive in a later bounded wave). Candidates are already unique by
    // `(level, key_path)`, so this count needs no second dedupe.
    let nested = report
        .candidates()
        .iter()
        .filter(|candidate| {
            !matches!(
                candidate.level(),
                HierarchyLevel::Glava | HierarchyLevel::Statya
            )
        })
        .count();
    eprintln!("# nested levels out of scope: {nested} unique (level, path) keys");

    let (glavas, statyas) = print_flat_bindings(report.candidates(), "law_2013-04-05_44-fz");
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
