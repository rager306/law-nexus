//! Multi-edition pipeline: run consultant-parser on multiple editions
//! of the same act and track how cross-act edges evolve over time.

use crate::{classify_all_scored, extract_hyperlinks};

/// Summary of one edition's parser output.
#[derive(Debug, Clone)]
pub struct EditionSummary {
    pub edition_number: u32,
    pub revision_date: String,
    pub hyperlink_count: usize,
    pub classified_count: usize,
    pub amends_count: usize,
    pub cites_count: usize,
    pub implements_count: usize,
    pub unknown_count: usize,
}

/// Run the full pipeline on a single edition file.
pub fn process_edition(xml: &[u8], edition_number: u32, revision_date: &str) -> EditionSummary {
    let links = extract_hyperlinks(xml);
    let classified = classify_all_scored(&links);

    let count_kind = |k: &str| classified.iter().filter(|c| c.kind == k).count();

    EditionSummary {
        edition_number,
        revision_date: revision_date.to_owned(),
        hyperlink_count: links.len(),
        classified_count: classified.len(),
        amends_count: count_kind("amends"),
        cites_count: count_kind("cites"),
        implements_count: count_kind("implements"),
        unknown_count: count_kind("unknown"),
    }
}

/// Extract edition number and revision date from a filename like
/// `edition-0050_rev-2020-01-01_from-..._hash.xml`.
pub fn parse_edition_filename(filename: &str) -> Option<(u32, String)> {
    let num = filename
        .strip_prefix("edition-")?
        .split('_')
        .next()?
        .parse()
        .ok()?;
    let rev = filename
        .split("_rev-")
        .nth(1)?
        .split('_')
        .next()?
        .trim_start_matches("from-")
        .to_owned();
    Some((num, rev))
}

/// Compare two edition summaries — how edges changed.
pub struct EditionDelta {
    pub amends_change: i64,
    pub cites_change: i64,
    pub implements_change: i64,
    pub unknown_change: i64,
}

pub fn delta(from: &EditionSummary, to: &EditionSummary) -> EditionDelta {
    EditionDelta {
        amends_change: to.amends_count as i64 - from.amends_count as i64,
        cites_change: to.cites_count as i64 - from.cites_count as i64,
        implements_change: to.implements_count as i64 - from.implements_count as i64,
        unknown_change: to.unknown_count as i64 - from.unknown_count as i64,
    }
}
