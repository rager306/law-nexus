//! Contract test: two-edition structural chain replay over the materialized
//! cleaned-wire JSONL layer (M224/S06/T02).
//!
//! Covers the library surface (`replay_chain`) and the `edition-timeline` bin
//! in `--mode chain`: a synthetic two-edition chain over a synthetic registry
//! map, the historical re-bind proof (a removed `statya` cannot detach unless it
//! is locally re-bound), the counts-only `edition-chain/v1` payload
//! (determinism + ASCII posture), the fail-closed CLI refusals (row count /
//! unreadable seed / refused target wire / unimplemented `timeline`), the
//! empty-provenance refusal, and the skip-capable corpus-gated oracles
//! (`0080 -> 0081` drift=0 and `0001 -> 0002` text-only, no structural drafts).
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures and
//! the tracked corpus exports exercised here; never corpus coverage, never
//! source authenticity, never legal amendment correctness. R1000 stays active.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::edition_timeline::{
    AssemblyMode, CHAIN_NON_CLAIMS, CHAIN_SCHEMA, EXIT_INPUT_UNREADABLE, EXIT_USAGE,
    EXIT_WIRE_REFUSED, EditionTimelineCli, replay_chain, run_edition_timeline,
};
use ln_decode::cleaned_wire::{WireCompletion, WireLimits, render_cleaned_projection};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_kb_ontology::domain::{HierarchyBinding, HierarchyMap, HierarchyMarker};
use ln_temporal::domain::ComponentConceptId;

const BIN: &str = env!("CARGO_BIN_EXE_edition-timeline");

/// Corpus directory of the 44-FZ consolidated editions (gitignored [smoke]).
const CORPUS_44FZ_DIR: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz";
/// Seed edition of the control replay (`from-unknown` -> rev day 2021-12-30).
const EDITION_0080: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0080_rev-2021-12-30_from-unknown_6f39db7c.xml";
/// Target edition of the control replay (structural change in force 2022-01-01).
const EDITION_0081: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0081_rev-2021-12-30_from-2022-01-01_fd3945d5.xml";
/// First edition (rev-initial) of the text-only pair.
const EDITION_0001: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0001_rev-initial_from-unknown_19d3c051.xml";
/// Second edition of the text-only pair.
const EDITION_0002: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0002_rev-2013-07-02_from-unknown_f4bfa020.xml";

/// Corpus path of the 44-FZ registry subset used for the synthetic CLI chain.
/// The synthetic fixtures emit `glava 1` + `statya 1..3`, all present in the
/// embedded registry, so the CLI path binds and applies drafts.
const SYNTH_SEED_CORPUS: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml";
/// Same work, a later `from-` day so the replay drafts land on a distinct day.
const SYNTH_TARGET_CORPUS: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-08-01_6d1ba238.xml";

/// Seed: `glava 1` + `statya 1` + `statya 2`. Written on one line so no
/// inter-element whitespace creates residual text.
const SEED_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 1. Предмет</w:t></w:r></w:p><w:p><w:r><w:t>Статья 2. Сфера применения</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// Target: `glava 1` + `statya 1` + `statya 3` (statya 2 removed, statya 3 added).
const TARGET_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 1. Предмет</w:t></w:r></w:p><w:p><w:r><w:t>Статья 3. Новые правила</w:t></w:r></w:p></w:body></w:wordDocument>"#;

// ------------------------------------------------------------ preparation #

static TEMP_SEQ: AtomicU64 = AtomicU64::new(0);

struct TempDir {
    path: PathBuf,
}

impl TempDir {
    fn new(label: &str) -> Self {
        let seq = TEMP_SEQ.fetch_add(1, Ordering::Relaxed);
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or(0);
        let path = std::env::temp_dir().join(format!(
            "ln-edition-chain-{}-{}-{}-{label}",
            std::process::id(),
            nanos,
            seq
        ));
        fs::create_dir_all(&path).expect("create temp dir");
        Self { path }
    }

    fn path(&self) -> &Path {
        &self.path
    }
}

impl Drop for TempDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.path);
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Run the real producer pipeline (`capture` → `build_projection` →
/// `render_cleaned_projection`) and return the materialized JSONL string.
fn build_wire(xml: &[u8]) -> String {
    let package = capture(xml, &Limits::default()).expect("fixture must capture");
    let projection = build_projection(package.records()).expect("fixture must project");
    render_cleaned_projection(
        &package,
        &projection,
        &WireCompletion::Complete,
        &WireLimits::default(),
    )
    .expect("fixture must export")
}

fn export_wire(dir: &Path, name: &str, xml: &str) -> PathBuf {
    let artifact = build_wire(xml.as_bytes());
    let path = dir.join(name);
    fs::write(&path, artifact).expect("write cleaned wire fixture");
    path
}

/// Extract the decoded markers from a materialized wire artifact.
fn markers(wire: &Path) -> Vec<HierarchyMarker> {
    let bytes = fs::read(wire).expect("read wire");
    ln_consultant_parser::edition_timeline::markers_from_cleaned_wire(&bytes)
        .expect("markers")
        .markers
}

fn cli(tsv: &Path, mode: AssemblyMode) -> EditionTimelineCli {
    EditionTimelineCli {
        editions: tsv.display().to_string(),
        mode,
        ctv: false,
        out: None,
    }
}

/// Write a two-row (seed, target) chain TSV.
fn write_chain_tsv(dir: &Path, seed: (u32, &str, &Path), target: (u32, &str, &Path)) -> PathBuf {
    let tsv = dir.join("chain.tsv");
    fs::write(
        &tsv,
        format!(
            "{}\t{}\t{}\n{}\t{}\t{}\n",
            seed.0,
            seed.1,
            seed.2.display(),
            target.0,
            target.1,
            target.2.display()
        ),
    )
    .expect("write chain tsv");
    tsv
}

fn binding(level: &str, number: &str, cc: &str) -> HierarchyBinding {
    HierarchyBinding::try_new(
        None,
        level,
        number,
        ComponentConceptId::parse(cc).expect("cc"),
    )
    .expect("binding")
}

fn run_bin(args: &[&str]) -> std::process::Output {
    Command::new(BIN)
        .args(args)
        .output()
        .expect("bin must launch")
}

// ------------------------------------------------- synthetic replay oracle #

/// Base map without the seed-only `statya 2`: mirrors a snapshot registry that
/// only knows the target's article set. The historical re-bind is the fix.
fn base_map() -> HierarchyMap {
    let mut map = HierarchyMap::empty();
    map.register(binding("glava", "1", "cc:test:glava-1"))
        .expect("register glava");
    map.register(binding("statya", "1", "cc:test:statya-1"))
        .expect("register statya-1");
    map
}

#[test]
fn synthetic_chain_without_rebind_leaves_removed_statya_undetached() {
    let dir = TempDir::new("chain-norebind");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let target_wire = export_wire(dir.path(), "target.jsonl", TARGET_FIXTURE);
    let seed = markers(&seed_wire);
    let target = markers(&target_wire);
    assert!(seed.len() >= 3, "seed must extract glava+statya 1+statya 2");
    assert!(
        target.len() >= 3,
        "target must extract glava+statya 1+statya 3"
    );

    // No `statya 2` / `statya 3` bindings: the removed article was never
    // attached and the added article has no parent -> both are quarantined.
    let counts = replay_chain(
        &seed,
        &target,
        &base_map(),
        100,
        200,
        "amendingact:seed",
        "amendingact:target",
    )
    .expect("replay must still report its quarantine");
    assert_eq!(counts.added, 1, "statya 3 is added");
    assert_eq!(counts.removed, 1, "statya 2 is removed");
    assert_eq!(counts.drafts, 2);
    assert_eq!(counts.attach, 1);
    assert_eq!(counts.detach, 1);
    assert_eq!(
        counts.applied_detach, 0,
        "without the local re-bind the removed statya never detaches"
    );
    assert_eq!(counts.applied_attach, 0, "statya 3 is unbound too");
    assert_eq!(counts.quarantined, 2, "both diffs are quarantined");
    assert_eq!(
        counts.drift, 0,
        "an unbound diff is invisible on both sides"
    );
}

#[test]
fn synthetic_chain_with_rebind_applies_and_reconstructs_target() {
    let dir = TempDir::new("chain-rebind");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let target_wire = export_wire(dir.path(), "target.jsonl", TARGET_FIXTURE);
    let seed = markers(&seed_wire);
    let target = markers(&target_wire);

    // The local historical re-bind: the seed-only `statya 2` and the target-only
    // `statya 3` (the latter is the fixture's stand-in for a re-bindable diff).
    let mut map = base_map();
    map.register(binding("statya", "2", "cc:test:statya-2"))
        .expect("register statya-2");
    map.register(binding("statya", "3", "cc:test:statya-3"))
        .expect("register statya-3");

    let counts = replay_chain(
        &seed,
        &target,
        &map,
        100,
        200,
        "amendingact:seed",
        "amendingact:target",
    )
    .expect("replay must succeed");
    assert_eq!(counts.added, 1);
    assert_eq!(counts.removed, 1);
    assert_eq!(counts.drafts, 2);
    assert_eq!(counts.applied_attach, 1, "statya 3 attaches");
    assert_eq!(counts.applied_detach, 1, "statya 2 detaches");
    assert_eq!(counts.quarantined, 0);
    assert_eq!(counts.missing, 0);
    assert_eq!(counts.phantom, 0);
    assert_eq!(
        counts.drift, 0,
        "seed commit + diff drafts must reproduce the target snapshot"
    );
}

#[test]
fn chain_replay_refuses_empty_provenance() {
    let dir = TempDir::new("chain-prov");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let target_wire = export_wire(dir.path(), "target.jsonl", TARGET_FIXTURE);
    let seed = markers(&seed_wire);
    let target = markers(&target_wire);
    let error = replay_chain(
        &seed,
        &target,
        &base_map(),
        100,
        200,
        "",
        "amendingact:target",
    )
    .expect_err("empty seed provenance must fail closed");
    assert_eq!(error.exit_code(), EXIT_WIRE_REFUSED);
    let error = replay_chain(
        &seed,
        &target,
        &base_map(),
        100,
        200,
        "amendingact:seed",
        "",
    )
    .expect_err("empty target provenance must fail closed");
    assert_eq!(error.exit_code(), EXIT_WIRE_REFUSED);
}

// -------------------------------------------------------- CLI payload path #

#[test]
fn chain_payload_is_deterministic_and_ascii() {
    let dir = TempDir::new("chain-cli");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let target_wire = export_wire(dir.path(), "target.jsonl", TARGET_FIXTURE);
    let tsv = write_chain_tsv(
        dir.path(),
        (118, SYNTH_SEED_CORPUS, &seed_wire),
        (119, SYNTH_TARGET_CORPUS, &target_wire),
    );
    let cli = cli(&tsv, AssemblyMode::Chain);
    let (first_code, first) = run_edition_timeline(&cli);
    assert_eq!(first_code, 0, "{first}");
    let (second_code, second) = run_edition_timeline(&cli);
    assert_eq!(second_code, 0);
    assert_eq!(first, second, "render must be deterministic");
    assert!(first.is_ascii(), "payload must be ASCII");

    let payload: serde_json::Value = serde_json::from_str(&first).expect("payload is JSON");
    assert_eq!(payload["schema"], CHAIN_SCHEMA);
    assert_eq!(payload["kind"], "edition_chain");
    assert_eq!(payload["seed_edition"], 118);
    assert_eq!(payload["target_edition"], 119);
    assert_eq!(payload["r1000_status"], "active/unclosed");
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert_eq!(payload["seed_expression_id_present"], true);
    assert_eq!(payload["target_expression_id_present"], true);
    assert_eq!(payload["added"], 1);
    assert_eq!(payload["removed"], 1);
    assert_eq!(payload["drafts"], 2);
    assert_eq!(payload["applied_attach"], 1);
    assert_eq!(payload["applied_detach"], 1);
    assert_eq!(payload["quarantined"], 0);
    assert_eq!(
        payload["drift"], 0,
        "seed commit + drafts reconstruct target"
    );
    assert_eq!(
        payload["historical_rebinds"], 2,
        "statya 2 + statya 3 offered"
    );
    let seed_pin = payload["seed_cleaned_wire_sha256"].as_str().unwrap();
    assert!(seed_pin.starts_with("sha256:"));
    let target_pin = payload["target_cleaned_wire_sha256"].as_str().unwrap();
    assert!(target_pin.starts_with("sha256:"));
    assert_ne!(seed_pin, target_pin);
}

// ------------------------------------------------------- fail-closed CLI #

#[test]
fn chain_mode_requires_exactly_two_rows() {
    let dir = TempDir::new("chain-rows");
    let one = dir.path().join("one.tsv");
    fs::write(&one, format!("80\t{SYNTH_SEED_CORPUS}\t/a.jsonl\n")).expect("write tsv");
    let (code, _) = run_edition_timeline(&cli(&one, AssemblyMode::Chain));
    assert_eq!(code, EXIT_USAGE, "one row is a usage error");

    let three = dir.path().join("three.tsv");
    fs::write(
        &three,
        format!(
            "80\t{SYNTH_SEED_CORPUS}\t/a.jsonl\n81\t{SYNTH_TARGET_CORPUS}\t/b.jsonl\n82\t{SYNTH_TARGET_CORPUS}\t/c.jsonl\n"
        ),
    )
    .expect("write tsv");
    let (code, _) = run_edition_timeline(&cli(&three, AssemblyMode::Chain));
    assert_eq!(code, EXIT_USAGE, "three rows is a usage error");
}

#[test]
fn bin_chain_missing_seed_wire_is_unreadable() {
    let dir = TempDir::new("chain-missing");
    let tsv = dir.path().join("chain.tsv");
    fs::write(
        &tsv,
        format!(
            "80\t{SYNTH_SEED_CORPUS}\t/nonexistent/m224-s06/seed.jsonl\n81\t{SYNTH_TARGET_CORPUS}\t/nonexistent/m224-s06/target.jsonl\n"
        ),
    )
    .expect("write tsv");
    let output = run_bin(&["--editions", &tsv.display().to_string(), "--mode", "chain"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));
}

#[test]
fn bin_chain_broken_target_wire_is_refused() {
    let dir = TempDir::new("chain-broken");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let broken = dir.path().join("broken.jsonl");
    fs::write(&broken, "not a cleaned projection\n").expect("write broken wire");
    let tsv = write_chain_tsv(
        dir.path(),
        (80, SYNTH_SEED_CORPUS, &seed_wire),
        (81, SYNTH_TARGET_CORPUS, &broken),
    );
    let output = run_bin(&["--editions", &tsv.display().to_string(), "--mode", "chain"]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_WIRE_REFUSED)));
}

#[test]
fn bin_timeline_mode_still_fails_closed() {
    let dir = TempDir::new("chain-timeline");
    let seed_wire = export_wire(dir.path(), "seed.jsonl", SEED_FIXTURE);
    let tsv = write_chain_tsv(
        dir.path(),
        (80, SYNTH_SEED_CORPUS, &seed_wire),
        (81, SYNTH_TARGET_CORPUS, &seed_wire),
    );
    let output = run_bin(&[
        "--editions",
        &tsv.display().to_string(),
        "--mode",
        "timeline",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_USAGE)));
}

#[test]
fn chain_non_claims_are_declared() {
    assert!(
        CHAIN_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("cleaned_wire_jsonl"))
    );
    assert!(
        CHAIN_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("historical_rebind_is_a_local_fixture_decision"))
    );
    assert!(
        CHAIN_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("integrity_is_not_semantic_completeness"))
    );
}

// -------------------------------------------------- corpus-gated oracles #

/// Materialize a corpus edition to cleaned-wire JSONL under `dir` and return
/// the artifact path. Skip-capable: `None` when the source export is absent.
fn corpus_wire(dir: &Path, corpus_rel: &str, name: &str) -> Option<PathBuf> {
    let xml = fs::read(repo_root().join(corpus_rel)).ok()?;
    let artifact = build_wire(&xml);
    let path = dir.join(name);
    fs::write(&path, artifact).expect("write corpus wire");
    Some(path)
}

#[test]
fn corpus_44fz_0080_to_0081_chain_zero_drift() {
    let dir = TempDir::new("chain-0080");
    let Some(seed_wire) = corpus_wire(dir.path(), EDITION_0080, "0080.jsonl") else {
        eprintln!("SKIP: consru_export editions 0080/0081 not available");
        return;
    };
    let Some(target_wire) = corpus_wire(dir.path(), EDITION_0081, "0081.jsonl") else {
        eprintln!("SKIP: consru_export editions 0080/0081 not available");
        return;
    };
    let tsv = write_chain_tsv(
        dir.path(),
        (80, EDITION_0080, &seed_wire),
        (81, EDITION_0081, &target_wire),
    );
    let (code, message) = run_edition_timeline(&cli(&tsv, AssemblyMode::Chain));
    assert_eq!(code, 0, "chain replay must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["schema"], CHAIN_SCHEMA);
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert_eq!(payload["added"], 24, "476-FZ purge adds 24 markers");
    assert_eq!(payload["removed"], 57, "476-FZ purge removes 57 markers");
    assert_eq!(payload["drafts"], 81);
    assert_eq!(payload["attach"], 24);
    assert_eq!(payload["detach"], 57);
    assert_eq!(payload["applied_attach"], 0, "added markers are non-statya");
    assert_eq!(
        payload["applied_detach"], 40,
        "the 40 removed statya detach via the local re-bind"
    );
    assert_eq!(payload["quarantined"], 41);
    assert_eq!(
        payload["drift"], 0,
        "seed + diff must reproduce edition-0081"
    );
    assert_eq!(payload["missing"], 0);
    assert_eq!(payload["phantom"], 0);
    assert_eq!(payload["seed_expression_id_present"], true);
    assert_eq!(payload["target_expression_id_present"], true);
    // Non-vacuity: the seed/target wires are distinct artifacts.
    assert_ne!(
        payload["seed_cleaned_wire_sha256"],
        payload["target_cleaned_wire_sha256"]
    );
}

#[test]
fn corpus_44fz_0001_to_0002_chain_text_only_no_drafts() {
    let dir = TempDir::new("chain-0001");
    let Some(seed_wire) = corpus_wire(dir.path(), EDITION_0001, "0001.jsonl") else {
        eprintln!("SKIP: consru_export editions 0001/0002 not available");
        return;
    };
    let Some(target_wire) = corpus_wire(dir.path(), EDITION_0002, "0002.jsonl") else {
        eprintln!("SKIP: consru_export editions 0001/0002 not available");
        return;
    };
    let tsv = write_chain_tsv(
        dir.path(),
        (1, EDITION_0001, &seed_wire),
        (2, EDITION_0002, &target_wire),
    );
    let (code, message) = run_edition_timeline(&cli(&tsv, AssemblyMode::Chain));
    assert_eq!(code, 0, "text-only chain must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(
        payload["drafts"], 0,
        "0001 -> 0002 changed article text, not structure"
    );
    assert_eq!(payload["added"], 0);
    assert_eq!(payload["removed"], 0);
    assert_eq!(payload["applied_attach"], 0);
    assert_eq!(payload["applied_detach"], 0);
    assert_eq!(payload["quarantined"], 0);
    assert_eq!(payload["drift"], 0);
}

#[test]
fn corpus_dir_constant_matches_the_registry_needle() {
    // Guard: the synthetic CLI paths and the corpus-gated paths must keep the
    // `law_2013-04-05_44-fz` needle that grounds the 102-binding registry.
    for path in [
        EDITION_0080,
        EDITION_0081,
        EDITION_0001,
        EDITION_0002,
        SYNTH_SEED_CORPUS,
        SYNTH_TARGET_CORPUS,
    ] {
        assert!(
            path.starts_with(CORPUS_44FZ_DIR),
            "{path} must live under {CORPUS_44FZ_DIR}"
        );
    }
}
