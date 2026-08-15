//! Registry binding generator for the 44-FZ corpus (M169 S02 T01).
//!
//! Manual helper: decode a real consru_export edition, extract hierarchy
//! markers and print `kb-hierarchy-registry.yaml` binding lines. The output
//! is pasted into the registry by a human — never auto-applied.
//!
//! Run: cargo test -p ln-decode --test registry_bindings_generator -- --nocapture

use std::fs;
use std::path::PathBuf;

use ln_decode::{
    adapters::ConsultantWordMlBlockDecoder,
    domain::{DecodeRequest, FamilyFormat, PayloadRef},
    hierarchy::extract_hierarchy,
    ports::BlockDecoderPort,
};

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
    let request = DecodeRequest::new(
        PayloadRef::parse("payload:m169-registry-generator").unwrap(),
        FamilyFormat::parse("family:consultant-wordml").unwrap(),
        &bytes,
    );
    let blocks = ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("edition-0118 must decode");

    // Dedupe (level, number) preserving document order.
    // Scope: glava + statya only (KBO-R042 / 402-ФЗ precedent). Chast/Punkt
    // stay Unknown until their own bounded wave.
    let mut seen: Vec<(String, String)> = Vec::new();
    let mut glavas = 0usize;
    let mut statyas = 0usize;
    let mut skipped_levels: Vec<String> = Vec::new();
    for block in &blocks {
        if let Some(node) = extract_hierarchy(block) {
            let level = match node.level().as_str() {
                "Glava" => "glava",
                "Statya" => "statya",
                other => {
                    if !skipped_levels.iter().any(|l| l == other) {
                        skipped_levels.push(other.to_owned());
                    }
                    continue;
                }
            };
            let key = (level.to_owned(), node.number().to_owned());
            if seen.contains(&key) {
                continue;
            }
            seen.push(key.clone());
            match key.0.as_str() {
                "glava" => glavas += 1,
                "statya" => statyas += 1,
                _ => unreachable!(),
            }
        }
    }

    eprintln!("# 44-FZ edition-0118 bindings: glava={glavas} statya={statyas}");
    eprintln!("# skipped levels: {skipped_levels:?}");
    eprintln!("# path_needle matches law_2013-04-05_44-fz (real corpus paths)");
    for (level, number) in &seen {
        eprintln!(
            "  - {{path_needle: law_2013-04-05_44-fz, level: {level}, number: \"{number}\", cc: cc:44-fz:{level}-{number}}}"
        );
    }
    eprintln!("TOTAL bindings: {}", seen.len());

    // Bounded sanity: 8 chapters; the consolidated 2025 edition carries
    // 94 unique article markers across the 1..114 numbering range (gaps are
    // repealed or restructured articles — honest, not a parser failure).
    assert_eq!(glavas, 8, "expected exactly 8 glava markers, got {glavas}");
    assert!(statyas >= 80, "expected 80+ statya, got {statyas}");
}
