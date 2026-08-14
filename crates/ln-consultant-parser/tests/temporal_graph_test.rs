//! Full 118-edition temporal graph: process all editions of 44-ФЗ
//! and track cross-act edge evolution over 12 years.

use ln_consultant_parser::multi_edition::process_editions_directory;

fn editions_dir() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../")
        .join("consru_export/consru_export/exports/npa/law_2013-04-05_44-fz")
}

#[test]
fn full_44fz_temporal_evolution() {
    let dir = editions_dir();
    if !dir.exists() {
        eprintln!("SKIP: consru_export not available");
        return;
    }

    let summaries = process_editions_directory(&dir);
    assert!(
        summaries.len() > 100,
        "expected 100+ editions; got {}",
        summaries.len()
    );

    println!(
        "=== 44-ФЗ temporal edge evolution ({} editions) ===",
        summaries.len()
    );
    println!(
        "{:>4} {:>12} {:>7} {:>7} {:>7} {:>7} {:>7}",
        "Ed#", "Date", "Links", "Amends", "Cites", "Impl", "Unknown"
    );

    // Print every 10th edition to show trend
    for s in summaries.iter().step_by(10) {
        println!(
            "{:>4} {:>12} {:>7} {:>7} {:>7} {:>7} {:>7}",
            s.edition_number,
            s.revision_date,
            s.hyperlink_count,
            s.amends_count,
            s.cites_count,
            s.implements_count,
            s.unknown_count
        );
    }
    // Always print first and last
    let last = summaries.last().unwrap();
    println!(
        "{:>4} {:>12} {:>7} {:>7} {:>7} {:>7} {:>7}",
        last.edition_number,
        last.revision_date,
        last.hyperlink_count,
        last.amends_count,
        last.cites_count,
        last.implements_count,
        last.unknown_count
    );

    // Find the biggest jump (edition with largest amends increase)
    let mut biggest_jump = 0i64;
    let mut jump_edition = 0;
    for w in summaries.windows(2) {
        let d = (w[1].amends_count as i64) - (w[0].amends_count as i64);
        if d > biggest_jump {
            biggest_jump = d;
            jump_edition = w[1].edition_number;
        }
    }
    println!(
        "\nBiggest amends jump: edition {} (+{} amends)",
        jump_edition, biggest_jump
    );

    // Verify overall trend (not monotonic — some amendments can be repealed)
    let first = summaries.first().unwrap();
    assert!(
        last.amends_count > first.amends_count,
        "overall amends should grow: edition 1 has {} but edition {} has {}",
        first.amends_count,
        last.edition_number,
        last.amends_count
    );

    // Count how many editions had amends decreases (repeals)
    let decreases = summaries
        .windows(2)
        .filter(|w| w[1].amends_count < w[0].amends_count)
        .count();
    println!("\nEditions with amends decreases (repeals): {}", decreases);
}
