//! T05 bounded-run evidence contract (M221-wbslul S04).
//!
//! Closes the bounded emitter loop: it reads the *tracked* `m221-s04-acceptance`
//! report/JSONL (produced by the `npa-corpus-acceptance-v2` CLI) and, without
//! re-running the corpus, asserts that the three independent verdicts coexist
//! (`transport_integrity=pass`, `analysis_completion=incomplete`,
//! `semantic_acceptance=not_attempted`), that `garant` is surfaced
//! `uncovered/no_candidates`, that the JSONL counters converge with the report,
//! that the artifacts stay count/hash-only, and that the CLI refuses an
//! `--out`/`--entries` collision, an existing target without `--force`, and a
//! symlinked target.
//!
//! Non-claims: count/hash only; no decoded corpus text enters the artifacts or
//! this test's assertions.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::npa_corpus_acceptance::AcceptanceEntry;
use ln_consultant_parser::npa_corpus_acceptance_v2::{
    AcceptanceReportV2, CompletionVerdict, ExpectationGateOutcome, SemanticVerdict, UncoveredReason,
};
use serde_json::Value;

const REPORT_REL: &str = "prd/migration/rust-evidence/m221-s04-acceptance.json";
const ENTRIES_REL: &str = "prd/migration/rust-evidence/m221-s04-acceptance.jsonl";
const FIXTURE_REL: &str = "crates/ln-consultant-parser/tests/fixtures/m221-bounded";
const GARANT_REL: &str = "law-source/garant";
const MAX_METADATA_STRING: usize = 512;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

fn read_str(rel: &str) -> String {
    let path = repo_root().join(rel);
    fs::read_to_string(&path).unwrap_or_else(|error| panic!("read {}: {error}", path.display()))
}

fn tracked_report() -> AcceptanceReportV2 {
    let text = read_str(REPORT_REL);
    AcceptanceReportV2::load(&text).expect("the tracked v2 report loads fail-closed")
}

fn loaded_entries() -> Vec<AcceptanceEntry> {
    read_str(ENTRIES_REL)
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| AcceptanceEntry::load_line(line).expect("each tracked JSONL line loads"))
        .collect()
}

// --------------------------------------------------- tracked evidence #

#[test]
fn tracked_bounded_evidence_carries_three_independent_verdicts() {
    let report = tracked_report();
    assert_eq!(report.verdicts.transport_integrity.as_str(), "pass");
    assert_eq!(
        report.verdicts.analysis_completion,
        CompletionVerdict::Incomplete
    );
    assert_eq!(
        report.verdicts.semantic_acceptance,
        SemanticVerdict::NotAttempted
    );
    // Integrity passes while completion stays incomplete: the two are separate.
    assert!(report.structural_integrity.pass);
    assert_eq!(report.structural_integrity.entries_total, 2);
    assert_eq!(report.structural_integrity.verified_ok, 2);
    assert!(
        report.analysis_completion.entries_incomplete >= 1,
        "the bounded run keeps a genuinely incomplete entry"
    );
    assert_eq!(
        report.expectation_gate,
        ExpectationGateOutcome::BelowDeclared,
        "an incomplete producer cannot satisfy the declared completion floor"
    );
}

#[test]
fn tracked_bounded_evidence_makes_garant_explicitly_uncovered() {
    let report = tracked_report();
    assert_eq!(
        report.provider_coverage.declared,
        vec!["consultant_export", "garant"]
    );
    assert_eq!(report.provider_coverage.covered, vec!["consultant_export"]);
    assert_eq!(report.provider_coverage.uncovered.len(), 1);
    assert_eq!(report.provider_coverage.uncovered[0].provider, "garant");
    assert_eq!(
        report.provider_coverage.uncovered[0].uncovered_reason,
        UncoveredReason::NoCandidates
    );
}

#[test]
fn tracked_entries_converge_with_the_report() {
    let report = tracked_report();
    let entries = loaded_entries();
    assert_eq!(
        entries.len() as u64,
        report.structural_integrity.entries_total
    );
    assert_eq!(
        entries.len() as u64,
        report.analysis_completion.entries_total
    );

    let verified = entries
        .iter()
        .filter(|entry| {
            entry.outcome == ln_consultant_parser::npa_corpus_acceptance::EntryOutcome::VerifiedOk
        })
        .count() as u64;
    assert_eq!(verified, report.structural_integrity.verified_ok);

    let mut complete = 0u64;
    let mut incomplete = 0u64;
    let mut family_totals: BTreeMap<String, u64> = BTreeMap::new();
    let mut reason_totals: BTreeMap<String, u64> = BTreeMap::new();
    let mut context_totals: BTreeMap<String, u64> = BTreeMap::new();
    for entry in &entries {
        match entry.completion.as_deref() {
            Some("complete") => complete += 1,
            Some("incomplete") => incomplete += 1,
            other => panic!("unexpected completion token {other:?}"),
        }
        for (family, count) in &entry.family_yields {
            *family_totals.entry(family.clone()).or_default() += count;
        }
        for reason in &entry.incomplete_reasons {
            *reason_totals.entry(reason.clone()).or_default() += 1;
        }
        if let Some(token) = entry.this_document_reference {
            *context_totals
                .entry(token.as_str().to_string())
                .or_default() += 1;
        }
    }
    assert_eq!(complete, report.analysis_completion.entries_complete);
    assert_eq!(incomplete, report.analysis_completion.entries_incomplete);
    assert_eq!(family_totals, report.analysis_completion.per_family_yields);
    assert_eq!(reason_totals, report.analysis_completion.incomplete_reasons);
    assert_eq!(
        context_totals,
        report.analysis_completion.context_result_distribution
    );
}

#[test]
fn tracked_report_is_count_hash_only() {
    let text = read_str(REPORT_REL);
    let value: Value = serde_json::from_str(&text).expect("valid JSON");
    assert_count_hash_only(&value);

    // Every JSONL line is also count/hash-only.
    for line in text_jsonl_lines() {
        let value: Value = serde_json::from_str(&line).expect("valid JSON line");
        assert_count_hash_only(&value);
    }
}

fn text_jsonl_lines() -> Vec<String> {
    read_str(ENTRIES_REL)
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(str::to_string)
        .collect()
}

fn assert_count_hash_only(value: &Value) {
    match value {
        Value::String(text) => {
            assert!(text.is_ascii(), "non-ASCII string: {text:?}");
            assert!(
                !text.bytes().any(|byte| byte.is_ascii_control()),
                "control character in string: {text:?}"
            );
            assert!(
                text.len() <= MAX_METADATA_STRING,
                "string over {MAX_METADATA_STRING} bytes: {text:?}"
            );
        }
        Value::Object(members) => {
            for (key, child) in members {
                assert!(key.is_ascii(), "non-ASCII key: {key:?}");
                assert_count_hash_only(child);
            }
        }
        Value::Array(items) => {
            for child in items {
                assert_count_hash_only(child);
            }
        }
        _ => {}
    }
}

// ------------------------------------------------------ CLI guards #

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock is after the epoch")
        .as_nanos();
    let dir = std::env::temp_dir().join(format!(
        "m221-s04-bounded-{tag}-{}-{nanos}",
        std::process::id()
    ));
    fs::create_dir_all(&dir).expect("temp dir is creatable");
    dir
}

fn as_str(path: &Path) -> &str {
    path.to_str().expect("temporary paths are utf-8")
}

fn fixture_root() -> PathBuf {
    repo_root().join(FIXTURE_REL)
}

fn garant_root() -> PathBuf {
    repo_root().join(GARANT_REL)
}

fn run_bin(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_npa-corpus-acceptance-v2"))
        .args(args)
        .output()
        .expect("the v2 acceptance binary should run")
}

fn assert_refused(output: &std::process::Output, expected_fragment: &str) {
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert_eq!(
        output.status.code(),
        Some(1),
        "expected a refusal exit 1, stderr: {stderr}"
    );
    assert!(
        !stderr.contains("panicked"),
        "a refusal must not panic: {stderr}"
    );
    assert!(
        stderr.contains(expected_fragment),
        "stderr must name the reason {expected_fragment:?}: {stderr}"
    );
}

#[test]
fn bounded_bin_refuses_out_equal_to_entries() {
    let work = unique_dir("out-eq-entries");
    let consultant = fixture_root();
    let garant = garant_root();
    let same = work.join("report.json");
    let args = [
        "--consultant-root",
        as_str(&consultant),
        "--garant-root",
        as_str(&garant),
        "--out",
        as_str(&same),
        "--entries",
        as_str(&same),
    ];
    let output = run_bin(&args);
    assert_refused(&output, "collides");
    assert!(!same.exists(), "a refused run must publish nothing");
    fs::remove_dir_all(&work).ok();
}

#[test]
fn bounded_bin_refuses_existing_output_without_force() {
    let work = unique_dir("existing");
    let consultant = fixture_root();
    let garant = garant_root();
    let out = work.join("report.json");
    let entries = work.join("entries.jsonl");
    fs::write(&out, b"stale-report").expect("seed existing output");

    let args = [
        "--consultant-root",
        as_str(&consultant),
        "--garant-root",
        as_str(&garant),
        "--out",
        as_str(&out),
        "--entries",
        as_str(&entries),
    ];
    let output = run_bin(&args);
    assert_refused(&output, "already exists");
    assert_eq!(fs::read(&out).expect("out readable"), b"stale-report");
    assert!(!entries.exists(), "a refused run must publish no sibling");
    fs::remove_dir_all(&work).ok();
}

#[cfg(unix)]
#[test]
fn bounded_bin_refuses_symlink_target_and_leaves_destination() {
    use std::os::unix::fs::symlink;
    let work = unique_dir("symlink-target");
    let consultant = fixture_root();
    let garant = garant_root();
    let destination = work.join("destination.json");
    fs::write(&destination, b"untouched").expect("destination");
    let link = work.join("out-link.json");
    symlink(&destination, &link).expect("symlink target");
    let entries = work.join("entries.jsonl");

    let args = [
        "--consultant-root",
        as_str(&consultant),
        "--garant-root",
        as_str(&garant),
        "--out",
        as_str(&link),
        "--entries",
        as_str(&entries),
        "--force",
    ];
    let output = run_bin(&args);
    assert_refused(&output, "symlink");
    assert_eq!(fs::read(&destination).expect("readable"), b"untouched");
    assert!(fs::symlink_metadata(&link)
        .expect("metadata")
        .file_type()
        .is_symlink());
    assert!(!entries.exists());
    fs::remove_dir_all(&work).ok();
}

#[test]
fn bounded_bin_force_replaces_and_emits_a_v2_report() {
    // End-to-end CLI run over the tracked fixture corpus: `--force` replaces an
    // existing target and the published report is the v2 split schema with the
    // garant provider explicitly uncovered.
    let work = unique_dir("force");
    let consultant = fixture_root();
    let garant = garant_root();
    let out = work.join("report.json");
    let entries = work.join("entries.jsonl");
    fs::write(&out, b"stale-report").expect("seed existing output");

    let args = [
        "--consultant-root",
        as_str(&consultant),
        "--garant-root",
        as_str(&garant),
        "--out",
        as_str(&out),
        "--entries",
        as_str(&entries),
        "--force",
    ];
    let output = run_bin(&args);
    assert!(
        output.status.success(),
        "the forced run should succeed, stderr: {}",
        String::from_utf8_lossy(&output.stderr)
    );
    let text = fs::read_to_string(&out).expect("out readable");
    let report = AcceptanceReportV2::load(&text).expect("the emitted report loads");
    assert_eq!(report.verdicts.transport_integrity.as_str(), "pass");
    assert_eq!(
        report.verdicts.analysis_completion,
        CompletionVerdict::Incomplete
    );
    assert_eq!(
        report.verdicts.semantic_acceptance,
        SemanticVerdict::NotAttempted
    );
    assert!(entries.exists(), "the entries companion is published");
    fs::remove_dir_all(&work).ok();
}
