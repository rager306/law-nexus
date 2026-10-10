//! T02 completion-capture contract (M221-wbslul S04).
//!
//! Additive capture of the per-entry analysis completion, basis, incomplete
//! reasons and family yields, driven over the real S01-S03 pipeline:
//!
//! - a plain WordML entry renders `complete`/`bounded_analysis_complete` with
//!   non-empty `family_yields`;
//! - a heading carrying a this-ref surface without a letterhead stays
//!   `verified_ok` but records `incomplete`/`context_incomplete` (§8B.3);
//! - a historical tracked JSONL line without the new fields still loads with
//!   typed defaults and round-trips byte-stable (no new keys are invented).
//!
//! Non-claims: fixtures are synthetic; count/hash only; no decoded corpus text
//! enters any artifact or this test's assertions.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::npa_corpus_acceptance::{
    AcceptanceEntry, AcceptanceRun, DECLARED_SAMPLE_SIZE, build_sample, declared_sample_roots,
    run_acceptance,
};

const WORDML_NS: &str = "http://schemas.microsoft.com/office/word/2003/wordml";

/// Plain body with no this-document reference surface.
const PLAIN_BODY: &str = "<w:p><w:r><w:t>Статья 1. Общие положения</w:t></w:r></w:p>";

/// The S03 context fixture (`crates/ln-decode/tests/npa_analysis_context_contract.rs`):
/// a heading with a this-ref surface and no letterhead, so the §8C.2 trigger
/// emits a `current_document_requisites` request that stays `unavailable`.
const CONTEXT_BODY: &str = "<w:p><w:r><w:t>Статья 1. Настоящего Федерального закона</w:t></w:r></w:p>\
     <w:p><w:r><w:t>Федерального закона от 01.01.2020 N 1-ФЗ,</w:t></w:r></w:p>\
     <w:p><w:r><w:t>от 02.02.2021 N 2-ФЗ</w:t></w:r></w:p>";

const ENTRIES_REL: &str = "prd/migration/rust-evidence/m214-s04-corpus-acceptance.jsonl";

fn wordml(body: &str) -> String {
    format!("<w:wordDocument xmlns:w=\"{WORDML_NS}\"><w:body>{body}</w:body></w:wordDocument>")
}

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock is after the epoch")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!(
        "m221-s04-completion-{tag}-{}-{nanos}",
        std::process::id()
    ));
    fs::create_dir_all(&dir).expect("temp dir is creatable");
    dir
}

/// Write exactly `DECLARED_SAMPLE_SIZE` families so the frozen draw includes
/// every one; the first two carry the completion-contract fixtures.
fn write_corpus(consultant: &Path, families: u64) {
    for index in 0..families {
        let dir = consultant.join("npa").join(format!("law_{index:04}"));
        fs::create_dir_all(&dir).expect("family dir is creatable");
        let body = match index {
            0 => PLAIN_BODY.to_string(),
            1 => CONTEXT_BODY.to_string(),
            _ => format!("<w:p><w:r><w:t>Проба {index:04}</w:t></w:r></w:p>"),
        };
        fs::write(dir.join("edition-0001.xml"), wordml(&body)).expect("fixture is writable");
    }
}

struct Fixture {
    /// Kept alive so the shared synthetic corpus outlives the tests.
    _base: PathBuf,
    run: AcceptanceRun,
}

fn shared() -> &'static Fixture {
    static SHARED: OnceLock<Fixture> = OnceLock::new();
    SHARED.get_or_init(|| {
        let base = unique_dir("shared");
        let consultant = base.join("consru_export/consru_export/exports");
        let garant = base.join("law-source/garant");
        fs::create_dir_all(&consultant).expect("consultant root is creatable");
        fs::create_dir_all(&garant).expect("garant root is creatable");
        write_corpus(&consultant, DECLARED_SAMPLE_SIZE);
        let roots = declared_sample_roots(consultant, garant).expect("declared roots are valid");
        let sample = build_sample(&roots).expect("shared sample builds");
        let run = run_acceptance(&sample, &roots).expect("shared acceptance run succeeds");
        Fixture { _base: base, run }
    })
}

fn entry_for<'a>(run: &'a AcceptanceRun, fragment: &str) -> &'a AcceptanceEntry {
    run.entries
        .iter()
        .find(|entry| entry.relative_path.contains(fragment))
        .unwrap_or_else(|| panic!("entry {fragment} is present in the sample"))
}

fn tracked_first_line() -> String {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .join(ENTRIES_REL);
    let text = fs::read_to_string(&path).expect("the tracked JSONL is readable");
    text.lines()
        .next()
        .expect("the tracked JSONL is non-empty")
        .to_string()
}

// --------------------------------------------------- additive capture #

#[test]
fn plain_entry_captures_complete_completion_and_family_yields() {
    let run = &shared().run;
    let entry = entry_for(run, "law_0000/");
    assert_eq!(entry.outcome.as_str(), "verified_ok");
    assert_eq!(entry.completion.as_deref(), Some("complete"));
    assert_eq!(
        entry.completion_basis.as_deref(),
        Some("bounded_analysis_complete")
    );
    assert!(
        entry.incomplete_reasons.is_empty(),
        "a complete analysis carries no incomplete_reasons"
    );
    assert!(
        !entry.family_yields.is_empty(),
        "a rendered envelope yields at least one family"
    );
}

#[test]
fn this_ref_without_letterhead_captures_context_incomplete() {
    let run = &shared().run;
    let entry = entry_for(run, "law_0001/");
    assert_eq!(entry.outcome.as_str(), "verified_ok");
    assert_eq!(entry.completion.as_deref(), Some("incomplete"));
    assert_eq!(
        entry.completion_basis.as_deref(),
        Some("context_incomplete")
    );
    assert!(
        entry
            .incomplete_reasons
            .iter()
            .any(|reason| reason == "context_incomplete"),
        "the incomplete reasons carry the context basis"
    );
}

// --------------------------------------------- historical compatibility #

#[test]
fn historical_line_without_new_fields_loads_with_defaults() {
    let line = tracked_first_line();
    let entry = AcceptanceEntry::load_line(&line).expect("the historical line loads fail-closed");
    assert_eq!(entry.outcome.as_str(), "verified_ok");
    assert!(
        entry.completion.is_none(),
        "missing completion defaults to None"
    );
    assert!(
        entry.completion_basis.is_none(),
        "missing completion_basis defaults to None"
    );
    assert!(
        entry.incomplete_reasons.is_empty(),
        "missing incomplete_reasons defaults to empty"
    );
    assert!(
        entry.family_yields.is_empty(),
        "missing family_yields defaults to empty"
    );
}

#[test]
fn historical_line_round_trips_without_new_keys() {
    let line = tracked_first_line();
    let entry = AcceptanceEntry::load_line(&line).expect("the historical line loads");
    let rendered = entry.to_json_line().expect("the entry renders");
    assert_eq!(
        rendered, line,
        "a historical line must round-trip byte-stable"
    );
    for key in [
        "\"completion\"",
        "\"completion_basis\"",
        "\"incomplete_reasons\"",
        "\"family_yields\"",
    ] {
        assert!(
            !rendered.contains(key),
            "the additive key {key} must not appear on a historical line"
        );
    }
}
