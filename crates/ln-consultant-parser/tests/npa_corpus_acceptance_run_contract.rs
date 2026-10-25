//! T03 run-contract test (M214-es3jvw S04): the corpus acceptance runner over a
//! synthetic corpus.
//!
//! The battery drives the real S01-S03 pipeline over an in-memory synthetic
//! WordML corpus and asserts: a manifest pin mismatch is a closed
//! `manifest_pin_mismatch` (never a silent re-pin), declared `AnalysisLimits`
//! pressure is recorded as closed `LimitKind` events, decode/gate refusals are
//! closed outcomes, the declared tamper probe detects every injected
//! resealed substitution (no false negative), the report sections stay
//! separated, and the report is byte-stable apart from the observed timing.
//!
//! Non-claims: synthetic fixtures only; count/hash only; no decoded corpus text
//! enters any artifact. The real run over the pinned corpus sample is T04.

use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::OnceLock;
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::npa_corpus_acceptance::{
    AcceptanceEntry, AcceptanceOptions, AcceptanceReport, AdjudicationPacket, CorpusSampleManifest,
    DECLARED_SAMPLE_SIZE, DECLARED_TAMPER_PROBE_ENTRIES, M208_STATUS_PARKED, R1000_STATUS_ACTIVE,
    SEMANTIC_REFERENCE_STATUS_ABSENT, SampleRoot, build_sample, declared_sample_roots,
    manifest_content_sha256, run_acceptance, run_acceptance_with,
};
use ln_decode::npa_analysis_wire::AnalysisLimits;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};

const WORDML_NS: &str = "http://schemas.microsoft.com/office/word/2003/wordml";
const LEAK_PROBE: &str = "LEAKPROBE";

// --------------------------------------------------------------- fixtures #

fn unique_dir(tag: &str) -> PathBuf {
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock is after the epoch")
        .as_nanos();
    let dir =
        std::env::temp_dir().join(format!("m214-s04-run-{tag}-{}-{nanos}", std::process::id()));
    fs::create_dir_all(&dir).expect("temp dir is creatable");
    dir
}

fn sha256_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut out = String::with_capacity(digest.len() * 2);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

fn wordml_doc(marker: &str) -> String {
    format!(
        "<w:wordDocument xmlns:w=\"{WORDML_NS}\"><w:body><w:p><w:r><w:t>{marker}</w:t></w:r></w:p></w:body></w:wordDocument>"
    )
}

/// Write `families` distinct WordML families, each with a unique in-body marker.
fn write_families(consultant: &Path, families: usize) {
    for index in 0..families {
        let dir = consultant.join("npa").join(format!("law_{index:04}"));
        fs::create_dir_all(&dir).expect("family dir is creatable");
        let marker = format!("{LEAK_PROBE}-{index:04}-abcdefghijklmnopqrstuvwxyz012345");
        fs::write(dir.join("edition-0001.xml"), wordml_doc(&marker))
            .expect("fixture file is writable");
    }
}

fn build_fixture(tag: &str, families: usize) -> (PathBuf, PathBuf, PathBuf) {
    let base = unique_dir(tag);
    let consultant = base.join("consru_export/consru_export/exports");
    let garant = base.join("law-source/garant");
    fs::create_dir_all(&consultant).expect("consultant root is creatable");
    fs::create_dir_all(&garant).expect("garant root is creatable");
    write_families(&consultant, families);
    (base, consultant, garant)
}

fn sample_roots(consultant: &Path, garant: &Path) -> Vec<SampleRoot> {
    declared_sample_roots(consultant.to_path_buf(), garant.to_path_buf())
        .expect("declared roots are valid")
}

struct Fixture {
    /// Kept alive so the shared synthetic corpus outlives the tests.
    _base: PathBuf,
    consultant: PathBuf,
    garant: PathBuf,
    sample: CorpusSampleManifest,
}

fn shared_fixture() -> &'static Fixture {
    static SHARED: OnceLock<Fixture> = OnceLock::new();
    SHARED.get_or_init(|| {
        let (base, consultant, garant) = build_fixture("shared", DECLARED_SAMPLE_SIZE as usize);
        let sample =
            build_sample(&sample_roots(&consultant, &garant)).expect("shared sample builds");
        Fixture {
            _base: base,
            consultant,
            garant,
            sample,
        }
    })
}

fn roots_of(fixture: &Fixture) -> Vec<SampleRoot> {
    sample_roots(&fixture.consultant, &fixture.garant)
}

fn sha_only(sha256: &str) -> &str {
    sha256.strip_prefix("sha256:").unwrap_or(sha256)
}

/// Normalize the observed timing out of a rendered report for byte-stability.
fn normalized_report(report: &AcceptanceReport) -> Value {
    let mut value: Value = serde_json::from_str(&report.to_json_string().expect("report renders"))
        .expect("report JSON");
    value["resources"] = json!({
        "peak_memory_bytes": null,
        "peak_memory_available": false,
        "total_wall_ms": 0,
        "mean_wall_ms": 0,
        "max_wall_ms": 0,
        "within_budget": true,
    });
    value
}

// ------------------------------------------------------ separated sections #

#[test]
fn acceptance_run_separates_sections_and_verdicts_pass() {
    let fixture = shared_fixture();
    let run = run_acceptance(&fixture.sample, &roots_of(fixture)).expect("acceptance run succeeds");
    let report = &run.report;

    // The reload path is the same fail-closed validator used by the report test.
    let rendered = report.to_json_string().expect("report renders");
    assert!(rendered.is_ascii(), "the report must stay ascii-only");
    assert!(!rendered.contains(LEAK_PROBE), "no decoded corpus text");

    // Every entry verified, no limits, no refusals.
    assert_eq!(
        report.structural_integrity.entries_total,
        DECLARED_SAMPLE_SIZE
    );
    assert_eq!(
        report.structural_integrity.verified_ok,
        DECLARED_SAMPLE_SIZE
    );
    assert_eq!(report.structural_integrity.structural_failures, 0);
    assert!(report.structural_integrity.pass);
    assert_eq!(report.structural_integrity.verify_codes, BTreeMap::new());
    assert_eq!(report.limits.limit_events_total, 0);
    assert!(report.limits.within_threshold);
    assert_eq!(report.verdict.as_str(), "pass");

    // The tamper probe runs the declared subset and never false-negatives.
    assert_eq!(
        report.structural_integrity.tamper_probe_entries,
        DECLARED_TAMPER_PROBE_ENTRIES
    );
    assert_eq!(
        report.structural_integrity.tamper_probe_detected,
        DECLARED_TAMPER_PROBE_ENTRIES
    );
    assert_eq!(report.structural_integrity.tamper_probe_false_negative, 0);

    // Section separation: semantic is structural-only, breadth makes no claim,
    // the horizon stays open.
    assert_eq!(
        report.semantic_adjudication.semantic_reference_status,
        SEMANTIC_REFERENCE_STATUS_ABSENT
    );
    assert!(!report.semantic_adjudication.promotion);
    assert_eq!(report.semantic_adjudication.adjudicated_entries, 0);
    assert!(report.corpus_breadth.coverage_claim.is_none());
    assert!(report.corpus_breadth.not_year_type_stratified);
    assert_eq!(report.horizon.r1000_status, R1000_STATUS_ACTIVE);
    assert_eq!(report.horizon.m208_status, M208_STATUS_PARKED);
    assert!(!report.non_claims.is_empty());
    assert!(report.resources.peak_memory_available == report.resources.peak_memory_bytes.is_some());

    // The report binds the canonical manifest hash and the packet it references.
    assert_eq!(
        report.sample_manifest_sha256,
        manifest_content_sha256(&fixture.sample).expect("manifest hashes")
    );
    assert!(!run.packet.promotion);
    assert_eq!(run.packet.items.len(), DECLARED_SAMPLE_SIZE as usize);
    let packet_text = run.packet.to_json_string().expect("packet renders");
    assert_eq!(
        report.semantic_adjudication.adjudication_packet_sha256,
        format!("sha256:{}", sha256_hex(packet_text.as_bytes()))
    );

    // Both artifacts round-trip through their fail-closed loaders.
    AcceptanceReport::load(&rendered).expect("report reloads");
    AdjudicationPacket::load(&packet_text).expect("packet reloads");

    // Per-entry JSONL carries only closed tokens and count/hash fields.
    let jsonl = run.entries_jsonl().expect("entries render");
    assert_eq!(jsonl.lines().count(), DECLARED_SAMPLE_SIZE as usize);
    assert!(!jsonl.contains(LEAK_PROBE));
    for line in jsonl.lines() {
        let entry = AcceptanceEntry::load_line(line).expect("entry reloads");
        assert_eq!(line.matches("\"wall_ms\"").count(), 1);
        assert_eq!(entry.outcome.as_str(), "verified_ok");
    }
    assert_eq!(
        report
            .corpus_breadth
            .provider_counts
            .get("consultant_export"),
        Some(&DECLARED_SAMPLE_SIZE)
    );
}

// -------------------------------------------------------- pin mismatch #

#[test]
fn manifest_pin_mismatch_is_a_closed_outcome() {
    let fixture = shared_fixture();
    let mut tampered = fixture.sample.clone();
    let first = &mut tampered.entries[0];
    let original = sha_only(&first.sha256).to_string();
    let flipped = format!(
        "{}{}",
        if original.starts_with('a') { "b" } else { "a" },
        &original[1..]
    );
    first.sha256 = format!("sha256:{flipped}");

    let options = AcceptanceOptions::default();
    let manifest_sha = manifest_content_sha256(&tampered).expect("manifest hashes");
    let run = run_acceptance_with(&tampered, &manifest_sha, &roots_of(fixture), &options)
        .expect("a pin mismatch is reported, not an abort");

    assert_eq!(run.report.structural_integrity.manifest_pin_mismatch, 1);
    assert_eq!(
        run.report.structural_integrity.structural_failures, 1,
        "exactly the tampered entry fails"
    );
    assert!(!run.report.structural_integrity.pass);
    assert_eq!(run.report.verdict.as_str(), "fail");
    assert_eq!(
        run.report.structural_integrity.tamper_probe_false_negative,
        0
    );

    // The tampered pin is reported verbatim; it is never silently re-pinned.
    let tampered_entry = run
        .entries
        .iter()
        .find(|entry| entry.outcome.as_str() == "manifest_pin_mismatch")
        .expect("the tampered entry is reported");
    assert_eq!(sha_only(&tampered_entry.sha256), flipped);
}

// -------------------------------------------------------------- limits #

#[test]
fn declared_limits_are_recorded_as_closed_events() {
    let fixture = shared_fixture();
    let manifest_sha = manifest_content_sha256(&fixture.sample).expect("manifest hashes");

    let line_limited = AcceptanceOptions {
        limits: AnalysisLimits {
            max_line_bytes: 1,
            max_records: 4_000_000,
        },
        tamper_probe_entries: DECLARED_TAMPER_PROBE_ENTRIES,
    };
    let run = run_acceptance_with(
        &fixture.sample,
        &manifest_sha,
        &roots_of(fixture),
        &line_limited,
    )
    .expect("limit run succeeds");
    assert_eq!(
        run.report.structural_integrity.limit_line_bytes,
        DECLARED_SAMPLE_SIZE
    );
    assert_eq!(run.report.limits.limit_events_total, DECLARED_SAMPLE_SIZE);
    assert_eq!(
        run.report.limits.limit_events.get("line_bytes"),
        Some(&DECLARED_SAMPLE_SIZE)
    );
    assert!(!run.report.limits.within_threshold);
    assert_eq!(run.report.verdict.as_str(), "needs_attention");
    assert!(run.report.structural_integrity.verify_codes.is_empty());
    // No entry rendered, so the probe falls back to the synthetic fixture and
    // still detects every injected tamper.
    assert_eq!(
        run.report.structural_integrity.tamper_probe_entries,
        DECLARED_TAMPER_PROBE_ENTRIES
    );
    assert_eq!(
        run.report.structural_integrity.tamper_probe_false_negative,
        0
    );

    let record_limited = AcceptanceOptions {
        limits: AnalysisLimits {
            max_line_bytes: 64 * 1024 * 1024,
            max_records: 1,
        },
        tamper_probe_entries: DECLARED_TAMPER_PROBE_ENTRIES,
    };
    let run = run_acceptance_with(
        &fixture.sample,
        &manifest_sha,
        &roots_of(fixture),
        &record_limited,
    )
    .expect("record-limit run succeeds");
    assert_eq!(
        run.report.structural_integrity.limit_records,
        DECLARED_SAMPLE_SIZE
    );
    assert_eq!(
        run.report.limits.limit_events.get("records"),
        Some(&DECLARED_SAMPLE_SIZE)
    );
    assert_eq!(run.report.verdict.as_str(), "needs_attention");
}

// --------------------------------------------------- decode/gate refusal #

#[test]
fn decode_and_gate_refusals_are_closed_outcomes() {
    let (base, consultant, garant) = build_fixture("refusals", (DECLARED_SAMPLE_SIZE - 2) as usize);
    fs::create_dir_all(consultant.join("npa/law_bad")).expect("bad family dir");
    fs::write(
        consultant.join("npa/law_bad/edition.xml"),
        b"this is not xml <<<",
    )
    .expect("malformed file is writable");
    fs::create_dir_all(consultant.join("npa/law_foreign")).expect("foreign family dir");
    fs::write(
        consultant.join("npa/law_foreign/edition.xml"),
        b"<note xmlns=\"urn:example:not-a-word-document\"><p>hi</p></note>",
    )
    .expect("foreign file is writable");

    let sample = build_sample(&sample_roots(&consultant, &garant)).expect("sample builds");
    let run =
        run_acceptance(&sample, &sample_roots(&consultant, &garant)).expect("refusal run succeeds");

    assert_eq!(run.report.structural_integrity.decode_refused, 1);
    assert_eq!(run.report.structural_integrity.gate_refused, 1);
    assert_eq!(run.report.structural_integrity.structural_failures, 2);
    assert!(!run.report.structural_integrity.pass);
    assert_eq!(run.report.verdict.as_str(), "needs_attention");

    let jsonl = run.entries_jsonl().expect("entries render");
    assert!(jsonl.contains("\"outcome\":\"decode_refused\""));
    assert!(jsonl.contains("\"outcome\":\"gate_refused\""));
    assert!(!jsonl.contains(LEAK_PROBE));
    fs::remove_dir_all(&base).ok();
}

// ----------------------------------------------------------- determinism #

#[test]
fn report_is_deterministic_apart_from_observed_timing() {
    let fixture = shared_fixture();
    let first = run_acceptance(&fixture.sample, &roots_of(fixture)).expect("first run");
    let second = run_acceptance(&fixture.sample, &roots_of(fixture)).expect("second run");

    assert_eq!(
        normalized_report(&first.report),
        normalized_report(&second.report),
        "the separated sections and verdict are byte-stable"
    );
    assert_eq!(
        first.packet, second.packet,
        "the adjudication packet is stable"
    );
    let mut first_entries = first.entries.clone();
    let mut second_entries = second.entries.clone();
    for entry in &mut first_entries {
        entry.wall_ms = 0;
    }
    for entry in &mut second_entries {
        entry.wall_ms = 0;
    }
    assert_eq!(
        first_entries, second_entries,
        "the per-entry outcomes are stable apart from the observed wall time"
    );
}

// ------------------------------------------------------- runner refusals #

#[test]
fn runner_rejects_zero_probe_budget_and_malformed_manifest_hash() {
    let fixture = shared_fixture();
    let manifest_sha = manifest_content_sha256(&fixture.sample).expect("manifest hashes");
    let zero = AcceptanceOptions {
        tamper_probe_entries: 0,
        ..AcceptanceOptions::default()
    };
    let error = run_acceptance_with(&fixture.sample, &manifest_sha, &roots_of(fixture), &zero)
        .expect_err("a zero probe budget must be refused");
    assert!(
        error.contains("tamper_probe_entries"),
        "unexpected: {error}"
    );

    let error = run_acceptance_with(
        &fixture.sample,
        "not-a-hash",
        &roots_of(fixture),
        &AcceptanceOptions::default(),
    )
    .expect_err("a malformed manifest hash must be refused");
    assert!(error.contains("sha256"), "unexpected: {error}");
}

// -------------------------------------------- fail-closed output paths #
//
// The S04 CLIs must never publish through a symlink or silently replace an
// existing artifact. These tests drive the real binaries over the shared
// synthetic corpus and assert a closed refusal (exit 1, no panic) before the
// pipeline runs, plus the explicit `--force` replacement path.

fn as_str(path: &Path) -> &str {
    path.to_str().expect("temporary paths are utf-8")
}

fn write_sample_manifest(dir: &Path, fixture: &Fixture) -> PathBuf {
    let path = dir.join("sample.json");
    fs::write(
        &path,
        fixture.sample.to_json_string().expect("sample renders"),
    )
    .expect("sample manifest is writable");
    path
}

fn run_acceptance_bin(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_npa-corpus-acceptance"))
        .args(args)
        .output()
        .expect("acceptance binary should run")
}

fn run_sample_bin(args: &[&str]) -> std::process::Output {
    Command::new(env!("CARGO_BIN_EXE_npa-corpus-sample"))
        .args(args)
        .output()
        .expect("sample binary should run")
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
fn acceptance_bin_refuses_existing_output_without_force_and_replaces_with_force() {
    let fixture = shared_fixture();
    let work = unique_dir("bin-existing");
    let sample = write_sample_manifest(&work, fixture);
    let out = work.join("report.json");
    let packet = work.join("packet.json");
    let entries = work.join("entries.jsonl");
    fs::write(&out, b"stale-report").expect("seed existing output");

    let args = [
        "--sample",
        as_str(&sample),
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&out),
        "--packet",
        as_str(&packet),
        "--entries",
        as_str(&entries),
    ];
    let refused = run_acceptance_bin(&args);
    assert_refused(&refused, "already exists");
    assert_eq!(fs::read(&out).expect("out readable"), b"stale-report");
    assert!(!packet.exists(), "refused run must not publish siblings");
    assert!(!entries.exists(), "refused run must not publish siblings");

    let mut forced = args.to_vec();
    forced.push("--force");
    let replaced = run_acceptance_bin(&forced);
    assert!(
        replaced.status.success(),
        "forced run should succeed, stderr: {}",
        String::from_utf8_lossy(&replaced.stderr)
    );
    let report = fs::read_to_string(&out).expect("out readable");
    assert!(
        report.contains("npa-analysis-corpus-acceptance/v1"),
        "the forced run must republish the report"
    );
    assert!(packet.exists());
    assert!(entries.exists());
    fs::remove_dir_all(&work).ok();
}

#[cfg(unix)]
#[test]
fn acceptance_bin_refuses_symlink_target_and_leaves_destination() {
    use std::os::unix::fs::symlink;
    let fixture = shared_fixture();
    let work = unique_dir("bin-symlink-target");
    let sample = write_sample_manifest(&work, fixture);
    let destination = work.join("destination.json");
    fs::write(&destination, b"untouched").expect("destination");
    let link = work.join("out-link.json");
    symlink(&destination, &link).expect("symlink target");
    let packet = work.join("packet.json");
    let entries = work.join("entries.jsonl");

    let args = [
        "--sample",
        as_str(&sample),
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&link),
        "--packet",
        as_str(&packet),
        "--entries",
        as_str(&entries),
        "--force",
    ];
    let output = run_acceptance_bin(&args);
    assert_refused(&output, "symlink");
    assert_eq!(fs::read(&destination).expect("readable"), b"untouched");
    assert!(
        fs::symlink_metadata(&link)
            .expect("metadata")
            .file_type()
            .is_symlink()
    );
    assert!(!packet.exists());
    fs::remove_dir_all(&work).ok();
}

#[cfg(unix)]
#[test]
fn acceptance_bin_refuses_symlinked_output_parent() {
    use std::os::unix::fs::symlink;
    let fixture = shared_fixture();
    let work = unique_dir("bin-symlink-parent");
    let sample = write_sample_manifest(&work, fixture);
    let real_dir = work.join("real-out");
    fs::create_dir_all(&real_dir).expect("real output dir");
    let link_dir = work.join("link-out");
    symlink(&real_dir, &link_dir).expect("symlink parent");
    let out = link_dir.join("report.json");
    let packet = work.join("packet.json");
    let entries = work.join("entries.jsonl");

    let args = [
        "--sample",
        as_str(&sample),
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&out),
        "--packet",
        as_str(&packet),
        "--entries",
        as_str(&entries),
    ];
    let output = run_acceptance_bin(&args);
    assert_refused(&output, "symlink");
    assert!(!real_dir.join("report.json").exists());
    fs::remove_dir_all(&work).ok();
}

#[test]
fn acceptance_bin_refuses_out_equal_to_sample() {
    let fixture = shared_fixture();
    let work = unique_dir("bin-out-eq-sample");
    let sample = write_sample_manifest(&work, fixture);
    let packet = work.join("packet.json");
    let entries = work.join("entries.jsonl");
    let before = fs::read(&sample).expect("sample readable");

    let args = [
        "--sample",
        as_str(&sample),
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&sample),
        "--packet",
        as_str(&packet),
        "--entries",
        as_str(&entries),
    ];
    let output = run_acceptance_bin(&args);
    assert_refused(&output, "sample");
    assert_eq!(fs::read(&sample).expect("sample readable"), before);
    assert!(!packet.exists());
    assert!(!entries.exists());
    fs::remove_dir_all(&work).ok();
}

#[test]
fn acceptance_bin_refuses_colliding_outputs() {
    let fixture = shared_fixture();
    let work = unique_dir("bin-collision");
    let sample = write_sample_manifest(&work, fixture);
    let shared_path = work.join("shared.json");
    let entries = work.join("entries.jsonl");

    let args = [
        "--sample",
        as_str(&sample),
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&shared_path),
        "--packet",
        as_str(&shared_path),
        "--entries",
        as_str(&entries),
    ];
    let output = run_acceptance_bin(&args);
    assert_refused(&output, "collides");
    assert!(!shared_path.exists());
    assert!(!entries.exists());
    fs::remove_dir_all(&work).ok();
}

#[test]
fn sample_bin_refuses_existing_manifest_without_force_and_replaces_with_force() {
    let fixture = shared_fixture();
    let work = unique_dir("sample-bin-existing");
    let out = work.join("manifest.json");
    fs::write(&out, b"stale-manifest").expect("seed existing manifest");

    let args = [
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&out),
    ];
    let refused = run_sample_bin(&args);
    assert_refused(&refused, "already exists");
    assert_eq!(fs::read(&out).expect("readable"), b"stale-manifest");

    let mut forced = args.to_vec();
    forced.push("--force");
    let replaced = run_sample_bin(&forced);
    assert!(
        replaced.status.success(),
        "forced sample run should succeed, stderr: {}",
        String::from_utf8_lossy(&replaced.stderr)
    );
    let text = fs::read_to_string(&out).expect("readable");
    assert!(text.contains("npa-analysis-corpus-sample/v1"));
    fs::remove_dir_all(&work).ok();
}

#[test]
fn sample_bin_refuses_out_equal_to_declared_root() {
    let fixture = shared_fixture();
    let args = [
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&fixture.consultant),
    ];
    let output = run_sample_bin(&args);
    assert_refused(&output, "declared root");
    assert!(fixture.consultant.is_dir());
}

#[cfg(unix)]
#[test]
fn sample_bin_refuses_symlink_target() {
    use std::os::unix::fs::symlink;
    let fixture = shared_fixture();
    let work = unique_dir("sample-bin-symlink");
    let destination = work.join("destination.json");
    fs::write(&destination, b"untouched").expect("destination");
    let link = work.join("manifest.json");
    symlink(&destination, &link).expect("symlink target");
    let args = [
        "--consultant-root",
        as_str(&fixture.consultant),
        "--garant-root",
        as_str(&fixture.garant),
        "--out",
        as_str(&link),
        "--force",
    ];
    let output = run_sample_bin(&args);
    assert_refused(&output, "symlink");
    assert_eq!(fs::read(&destination).expect("readable"), b"untouched");
    fs::remove_dir_all(&work).ok();
}
