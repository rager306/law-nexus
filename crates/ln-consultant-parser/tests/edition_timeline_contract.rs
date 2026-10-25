//! Contract test: multi-edition structural timeline over the materialized
//! cleaned-wire JSONL layer (M224/S06/T03).
//!
//! Exercises the library surface (`replay_timeline`) and the `edition-timeline`
//! bin in `--mode timeline`: an ascending three-edition chain over inline
//! WordML fixtures and a synthetic registry map (an article appears in the
//! middle edition and disappears in the last), the historical re-bind proof
//! (without it the removed article never detaches), the counts-only
//! `edition-timeline/v1` payload (determinism + ASCII posture + ascending
//! order), the inverted-day clamp (`max(previous applied day, effect day)`),
//! the fail-closed CLI refusals (empty list / unreadable input / refused wire),
//! and a skip-capable corpus-gated 118-edition oracle (all drift zero, exactly
//! one documented non-monotonic transition 0036 -> 0037, no same-day
//! collisions).
//!
//! Non-claims: `[bounded]` to the self-authored non-legal synthetic fixtures and
//! the tracked corpus exports exercised here; never corpus coverage, never
//! source authenticity, never legal amendment correctness. R1000 stays active.

use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use ln_consultant_parser::edition_timeline::{
    AssemblyMode, EXIT_INPUT_UNREADABLE, EXIT_USAGE, EXIT_WIRE_REFUSED, EditionSnapshot,
    EditionTimelineCli, TIMELINE_NON_CLAIMS, TIMELINE_SCHEMA, replay_timeline,
    run_edition_timeline,
};
use ln_decode::cleaned_wire::{WireCompletion, WireLimits, render_cleaned_projection};
use ln_decode::reader_projection::build_projection;
use ln_decode::source_package::{Limits, capture};
use ln_kb_ontology::domain::{HierarchyBinding, HierarchyMap, HierarchyMarker};
use ln_temporal::domain::ComponentConceptId;

const BIN: &str = env!("CARGO_BIN_EXE_edition-timeline");

/// Corpus directory of the 44-FZ consolidated editions (gitignored [smoke]).
const CORPUS_44FZ_DIR: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz";
/// Bounded corpus window around the 476-FZ purge (0079 -> 0080 -> 0081).
const EDITION_0079: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0079_rev-2021-07-02_from-unknown_d04df1f4.xml";
const EDITION_0080: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0080_rev-2021-12-30_from-unknown_6f39db7c.xml";
const EDITION_0081: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0081_rev-2021-12-30_from-2022-01-01_fd3945d5.xml";

/// Corpus path of the 44-FZ registry subset used for the synthetic CLI chain.
/// `from-2026-07-01` grounds one effect day; the fixture markers stay synthetic.
const SYNTH_EARLY_CORPUS: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-07-01_6d1ba238.xml";
/// Same work, a later `from-` day so the middle transition lands later.
const SYNTH_LATE_CORPUS: &str = "consru_export/consru_export/exports/npa/law_2013-04-05_44-fz/edition-0118_rev-2025-12-28_from-2026-08-01_6d1ba238.xml";

/// Edition one: `glava 1` + `statya 1`. Written on one line so no
/// inter-element whitespace creates residual text.
const EDITION_ONE_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 1. Предмет</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// Edition two: `statya 2` is inserted (the article that appears mid-timeline).
const EDITION_TWO_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 1. Предмет</w:t></w:r></w:p><w:p><w:r><w:t>Статья 2. Сфера применения</w:t></w:r></w:p></w:body></w:wordDocument>"#;

/// Edition three: `statya 2` disappears again.
const EDITION_THREE_FIXTURE: &str = r#"<w:wordDocument xmlns:w="http://schemas.microsoft.com/office/word/2003/wordml"><w:body><w:p><w:r><w:t>Глава 1. Общие положения</w:t></w:r></w:p><w:p><w:r><w:t>Статья 1. Предмет</w:t></w:r></w:p></w:body></w:wordDocument>"#;

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
            "ln-edition-timeline-{}-{}-{}-{label}",
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

fn write_timeline_tsv(dir: &Path, rows: &[(u32, &str, &Path)]) -> PathBuf {
    let tsv = dir.join("timeline.tsv");
    let mut body = String::new();
    for (number, corpus, wire) in rows {
        body.push_str(&format!("{number}\t{corpus}\t{}\n", wire.display()));
    }
    fs::write(&tsv, body).expect("write timeline tsv");
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

// ------------------------------------------------- synthetic timeline oracle #

/// Base map binding `glava 1` + `statya 1`; `statya 2` is the mid-timeline
/// article the growing map must (or must not) know about.
fn base_map() -> HierarchyMap {
    let mut map = HierarchyMap::empty();
    map.register(binding("glava", "1", "cc:test:glava-1"))
        .expect("register glava");
    map.register(binding("statya", "1", "cc:test:statya-1"))
        .expect("register statya-1");
    map
}

#[test]
fn synthetic_timeline_three_editions_reconstructs_each_snapshot() {
    let dir = TempDir::new("timeline-synth");
    let one = markers(&export_wire(dir.path(), "one.jsonl", EDITION_ONE_FIXTURE));
    let two = markers(&export_wire(dir.path(), "two.jsonl", EDITION_TWO_FIXTURE));
    let three = markers(&export_wire(
        dir.path(),
        "three.jsonl",
        EDITION_THREE_FIXTURE,
    ));

    let mut map = base_map();
    map.register(binding("statya", "2", "cc:test:statya-2"))
        .expect("register statya-2");

    let snapshots = [
        EditionSnapshot {
            edition_number: 1,
            effect_day: 100,
            provenance: "amendingact:test",
            markers: &one,
        },
        EditionSnapshot {
            edition_number: 2,
            effect_day: 200,
            provenance: "amendingact:test",
            markers: &two,
        },
        EditionSnapshot {
            edition_number: 3,
            effect_day: 300,
            provenance: "amendingact:test",
            markers: &three,
        },
    ];
    let timeline = replay_timeline(&snapshots, &map, "test", 2, 1).expect("timeline must succeed");

    assert_eq!(timeline.totals.editions, 3);
    assert_eq!(timeline.totals.drift, 0, "every edition must reconstruct");
    assert_eq!(timeline.totals.missing, 0);
    assert_eq!(timeline.totals.phantom, 0);
    assert!(timeline.totals.applied > 0, "the mid article must move");
    assert_eq!(timeline.totals.applied_attach, 1, "statya 2 attaches");
    assert_eq!(timeline.totals.applied_detach, 1, "statya 2 detaches");
    assert_eq!(timeline.totals.quarantined, 0);
    assert!(
        timeline.non_monotonic_transitions.is_empty(),
        "these days are monotonic"
    );
    assert_eq!(timeline.points[0].drafts, 0, "the seed ofprints nothing");
    assert_eq!(timeline.points[1].drafts, 1);
    assert_eq!(timeline.points[2].drafts, 1);
    for point in &timeline.points {
        assert_eq!(point.drift, 0);
        assert_eq!(point.applied_day, point.effect_day, "monotonic window");
        assert_eq!(point.roots, 1, "only glava 1 is a forest root");
    }
    assert_eq!(timeline.points[1].nodes, 3, "glava + statya 1 + statya 2");
    assert_eq!(timeline.points[2].nodes, 2, "statya 2 is gone");
}

#[test]
fn synthetic_timeline_without_rebind_quarantines_the_mid_article() {
    let dir = TempDir::new("timeline-norebind");
    let one = markers(&export_wire(dir.path(), "one.jsonl", EDITION_ONE_FIXTURE));
    let two = markers(&export_wire(dir.path(), "two.jsonl", EDITION_TWO_FIXTURE));
    let three = markers(&export_wire(
        dir.path(),
        "three.jsonl",
        EDITION_THREE_FIXTURE,
    ));

    let snapshots = [
        EditionSnapshot {
            edition_number: 1,
            effect_day: 100,
            provenance: "amendingact:test",
            markers: &one,
        },
        EditionSnapshot {
            edition_number: 2,
            effect_day: 200,
            provenance: "amendingact:test",
            markers: &two,
        },
        EditionSnapshot {
            edition_number: 3,
            effect_day: 300,
            provenance: "amendingact:test",
            markers: &three,
        },
    ];
    // No `statya 2` binding: both its attach and detach are quarantined.
    let timeline =
        replay_timeline(&snapshots, &base_map(), "test", 1, 0).expect("quarantine is a report");
    assert_eq!(timeline.totals.applied, 0);
    assert_eq!(timeline.totals.applied_attach, 0);
    assert_eq!(timeline.totals.applied_detach, 0);
    assert_eq!(
        timeline.totals.quarantined, 2,
        "attach + detach quarantined"
    );
    assert_eq!(timeline.points[1].quarantined, 1);
    assert_eq!(timeline.points[2].quarantined, 1);
    assert_eq!(
        timeline.totals.drift, 0,
        "an unbound diff is invisible on both sides"
    );
}

#[test]
fn inverted_day_order_is_clamped_and_never_drifts() {
    let dir = TempDir::new("timeline-clamp");
    let one = markers(&export_wire(dir.path(), "one.jsonl", EDITION_ONE_FIXTURE));
    let two = markers(&export_wire(dir.path(), "two.jsonl", EDITION_TWO_FIXTURE));
    let three = markers(&export_wire(
        dir.path(),
        "three.jsonl",
        EDITION_THREE_FIXTURE,
    ));

    let mut map = base_map();
    map.register(binding("statya", "2", "cc:test:statya-2"))
        .expect("register statya-2");

    // The third edition's grounded day goes *backwards* (300 -> 200).
    let snapshots = [
        EditionSnapshot {
            edition_number: 1,
            effect_day: 100,
            provenance: "amendingact:test",
            markers: &one,
        },
        EditionSnapshot {
            edition_number: 2,
            effect_day: 300,
            provenance: "amendingact:test",
            markers: &two,
        },
        EditionSnapshot {
            edition_number: 3,
            effect_day: 200,
            provenance: "amendingact:test",
            markers: &three,
        },
    ];
    let timeline = replay_timeline(&snapshots, &map, "test", 2, 1).expect("clamp must not panic");

    assert_eq!(timeline.non_monotonic_transitions.len(), 1);
    let transition = &timeline.non_monotonic_transitions[0];
    assert_eq!(transition.from_edition, 2);
    assert_eq!(transition.from_day, 300);
    assert_eq!(transition.to_edition, 3);
    assert_eq!(transition.to_day, 200);
    assert_eq!(transition.applied_day, 300, "clamped to the previous day");

    let mut previous_day = i64::MIN;
    for point in &timeline.points {
        assert!(
            point.applied_day >= point.effect_day,
            "relative day must never be negative"
        );
        assert!(
            point.applied_day >= previous_day,
            "the applied day must not go backwards"
        );
        previous_day = point.applied_day;
        assert_eq!(point.drift, 0, "the clamp must not change the result");
    }
    assert_eq!(timeline.points[2].applied_day, 300);
}

#[test]
fn empty_snapshot_list_fails_closed() {
    let error = replay_timeline(&[], &base_map(), "test", 0, 0)
        .expect_err("an empty timeline must fail closed");
    assert_eq!(error.exit_code(), EXIT_INPUT_UNREADABLE);
}

// -------------------------------------------------------- CLI payload path #

#[test]
fn timeline_payload_is_deterministic_ascii_and_ascending() {
    let dir = TempDir::new("timeline-cli");
    let one = export_wire(dir.path(), "one.jsonl", EDITION_ONE_FIXTURE);
    let two = export_wire(dir.path(), "two.jsonl", EDITION_TWO_FIXTURE);
    let three = export_wire(dir.path(), "three.jsonl", EDITION_THREE_FIXTURE);
    // Rows are deliberately out of order: the bin must fold ascending.
    let tsv = write_timeline_tsv(
        dir.path(),
        &[
            (3, SYNTH_EARLY_CORPUS, &three),
            (1, SYNTH_EARLY_CORPUS, &one),
            (2, SYNTH_LATE_CORPUS, &two),
        ],
    );
    let cli = cli(&tsv, AssemblyMode::Timeline);
    let (first_code, first) = run_edition_timeline(&cli);
    assert_eq!(first_code, 0, "{first}");
    let (second_code, second) = run_edition_timeline(&cli);
    assert_eq!(second_code, 0);
    assert_eq!(first, second, "render must be deterministic");
    assert!(first.is_ascii(), "payload must be ASCII");

    let payload: serde_json::Value = serde_json::from_str(&first).expect("payload is JSON");
    assert_eq!(payload["schema"], TIMELINE_SCHEMA);
    assert_eq!(payload["kind"], "edition_timeline");
    assert_eq!(payload["r1000_status"], "active/unclosed");
    assert_eq!(payload["slug"], "44-fz");
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert_eq!(
        payload["historical_rebinds"], 2,
        "statya 1 + statya 2 offered"
    );
    assert_eq!(payload["editions"], 3);
    assert_eq!(payload["totals"]["drift"], 0);
    assert_eq!(payload["totals"]["drafts"], 2);
    assert_eq!(payload["totals"]["applied_attach"], 1);
    assert_eq!(payload["totals"]["applied_detach"], 1);
    assert_eq!(payload["totals"]["quarantined"], 0);

    let points = payload["per_edition"].as_array().expect("per_edition");
    let numbers: Vec<u64> = points
        .iter()
        .map(|point| point["edition_number"].as_u64().unwrap())
        .collect();
    assert_eq!(numbers, vec![1, 2, 3], "ascending edition_number order");
    for point in points {
        assert_eq!(point["drift"], 0);
    }
    assert_eq!(points[0]["drafts"], 0);
    assert_eq!(points[1]["drafts"], 1);
    assert_eq!(points[2]["drafts"], 1);

    // Row 3 shares the early effect day but is clamped past row 2.
    let transitions = payload["non_monotonic_transitions"]
        .as_array()
        .expect("transitions");
    assert_eq!(transitions.len(), 1);
    assert_eq!(transitions[0]["from_edition"], 2);
    assert_eq!(transitions[0]["to_edition"], 3);
    assert!(
        transitions[0]["applied_day"].as_i64().unwrap()
            > transitions[0]["to_day"].as_i64().unwrap(),
        "the backwards day is clamped forward"
    );
}

// ------------------------------------------------------- fail-closed CLI #

#[test]
fn bin_empty_edition_list_is_input_error() {
    let dir = TempDir::new("timeline-empty");
    let tsv = dir.path().join("empty.tsv");
    fs::write(&tsv, "").expect("write empty tsv");
    let output = run_bin(&[
        "--editions",
        &tsv.display().to_string(),
        "--mode",
        "timeline",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));

    let (code, _) = run_edition_timeline(&cli(&tsv, AssemblyMode::Timeline));
    assert_eq!(code, EXIT_INPUT_UNREADABLE);
}

#[test]
fn bin_timeline_missing_wire_is_unreadable() {
    let dir = TempDir::new("timeline-missing");
    let tsv = write_timeline_tsv(
        dir.path(),
        &[(
            1,
            SYNTH_EARLY_CORPUS,
            Path::new("/nonexistent/m224-s06/timeline.jsonl"),
        )],
    );
    let output = run_bin(&[
        "--editions",
        &tsv.display().to_string(),
        "--mode",
        "timeline",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_INPUT_UNREADABLE)));
}

#[test]
fn bin_timeline_broken_wire_is_refused() {
    let dir = TempDir::new("timeline-broken");
    let broken = dir.path().join("broken.jsonl");
    fs::write(&broken, "not a cleaned projection\n").expect("write broken wire");
    let tsv = write_timeline_tsv(dir.path(), &[(1, SYNTH_EARLY_CORPUS, &broken)]);
    let output = run_bin(&[
        "--editions",
        &tsv.display().to_string(),
        "--mode",
        "timeline",
    ]);
    assert_eq!(output.status.code(), Some(i32::from(EXIT_WIRE_REFUSED)));
}

#[test]
fn bin_timeline_duplicate_edition_is_usage_error() {
    let dir = TempDir::new("timeline-duplicate");
    let one = export_wire(dir.path(), "one.jsonl", EDITION_ONE_FIXTURE);
    let tsv = write_timeline_tsv(
        dir.path(),
        &[(1, SYNTH_EARLY_CORPUS, &one), (1, SYNTH_LATE_CORPUS, &one)],
    );
    let (code, _) = run_edition_timeline(&cli(&tsv, AssemblyMode::Timeline));
    assert_eq!(code, EXIT_USAGE);
}

#[test]
fn timeline_non_claims_are_declared() {
    assert!(
        TIMELINE_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("cleaned_wire_jsonl"))
    );
    assert!(
        TIMELINE_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("historical_rebind_is_a_local_fixture_decision"))
    );
    assert!(
        TIMELINE_NON_CLAIMS
            .iter()
            .any(|claim| claim.contains("non_monotonic_rev_dates_are_clamped"))
    );
    assert!(
        TIMELINE_NON_CLAIMS
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
fn corpus_44fz_0079_to_0081_timeline_zero_drift() {
    let dir = TempDir::new("timeline-0079");
    let Some(seed) = corpus_wire(dir.path(), EDITION_0079, "0079.jsonl") else {
        eprintln!("SKIP: consru_export editions 0079-0081 not available");
        return;
    };
    let Some(middle) = corpus_wire(dir.path(), EDITION_0080, "0080.jsonl") else {
        eprintln!("SKIP: consru_export editions 0079-0081 not available");
        return;
    };
    let Some(target) = corpus_wire(dir.path(), EDITION_0081, "0081.jsonl") else {
        eprintln!("SKIP: consru_export editions 0079-0081 not available");
        return;
    };
    let tsv = write_timeline_tsv(
        dir.path(),
        &[
            (79, EDITION_0079, &seed),
            (80, EDITION_0080, &middle),
            (81, EDITION_0081, &target),
        ],
    );
    let (code, message) = run_edition_timeline(&cli(&tsv, AssemblyMode::Timeline));
    assert_eq!(code, 0, "bounded corpus timeline must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["schema"], TIMELINE_SCHEMA);
    assert_eq!(payload["editions"], 3);
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert!(payload["historical_rebinds"].as_u64().unwrap() > 94);
    assert_eq!(
        payload["totals"]["drift"], 0,
        "all three editions reconstruct"
    );
    assert!(payload["totals"]["applied"].as_u64().unwrap() > 0);
    assert_eq!(
        payload["non_monotonic_transitions"]
            .as_array()
            .unwrap()
            .len(),
        0
    );
    for point in payload["per_edition"].as_array().unwrap() {
        assert_eq!(point["drift"], 0);
    }
}

/// Parse `edition-NNNN_...xml` into its sequence number, else `None`.
fn parse_edition_number(name: &str) -> Option<u32> {
    let rest = name.strip_prefix("edition-")?;
    if !name.ends_with(".xml") {
        return None;
    }
    rest.get(..4)?.parse().ok()
}

/// Materialize all 118 44-FZ editions and write a timeline TSV. Expensive
/// (~0.8 GB, minutes); only used when the full run is explicitly opted in.
fn materialize_44fz_timeline(dir: &Path) -> Option<PathBuf> {
    let corpus_dir = repo_root().join(CORPUS_44FZ_DIR);
    let mut entries: Vec<(u32, PathBuf)> = Vec::new();
    for entry in fs::read_dir(&corpus_dir).ok()? {
        let entry = entry.ok()?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if let Some(number) = parse_edition_number(&name) {
            entries.push((number, entry.path()));
        }
    }
    if entries.len() != 118 {
        return None;
    }
    entries.sort_by_key(|(number, _)| *number);

    let mut tsv = String::new();
    for (number, xml_path) in &entries {
        let xml = fs::read(xml_path).ok()?;
        let artifact = build_wire(&xml);
        let wire_path = dir.join(format!("edition-{number:04}.jsonl"));
        fs::write(&wire_path, artifact).ok()?;
        let file_name = xml_path.file_name()?.to_string_lossy();
        tsv.push_str(&format!(
            "{number}\t{CORPUS_44FZ_DIR}/{file_name}\t{}\n",
            wire_path.display()
        ));
    }
    let tsv_path = dir.join("timeline.tsv");
    fs::write(&tsv_path, tsv).ok()?;
    Some(tsv_path)
}

#[test]
fn corpus_44fz_full_118_edition_timeline_zero_drift() {
    // Skip-capable: producing the 118 JSONL artifacts is the T05 driver's job.
    // Opt in with `M224_S06_TIMELINE_TSV=<driver tsv>` (fast) or
    // `M224_S06_TIMELINE_CORPUS=1` (materialize on the fly, minutes).
    let explicit = std::env::var("M224_S06_TIMELINE_TSV").ok();
    let auto_materialize = std::env::var("M224_S06_TIMELINE_CORPUS").as_deref() == Ok("1");
    if explicit.is_none() && !auto_materialize {
        eprintln!(
            "SKIP: set M224_S06_TIMELINE_TSV or M224_S06_TIMELINE_CORPUS=1 for the 118-edition run"
        );
        return;
    }
    let dir = TempDir::new("timeline-118");
    let tsv = match explicit {
        Some(path) => PathBuf::from(path),
        None => {
            let Some(tsv) = materialize_44fz_timeline(dir.path()) else {
                eprintln!("SKIP: consru_export 44-FZ editions not available");
                return;
            };
            tsv
        }
    };
    let (code, message) = run_edition_timeline(&cli(&tsv, AssemblyMode::Timeline));
    assert_eq!(code, 0, "the 118-edition timeline must succeed: {message}");
    let payload: serde_json::Value = serde_json::from_str(&message).expect("payload is JSON");
    assert_eq!(payload["schema"], TIMELINE_SCHEMA);
    assert_eq!(payload["editions"], 118);
    assert_eq!(payload["registry_bindings"], 102, "8 glava + 94 statya");
    assert_eq!(
        payload["totals"]["drift"], 0,
        "every edition must reconstruct its own snapshot"
    );
    assert_eq!(payload["totals"]["missing"], 0);
    assert_eq!(payload["totals"]["phantom"], 0);

    let points = payload["per_edition"].as_array().expect("per_edition");
    assert_eq!(points.len(), 118);
    let mut effect_days = HashSet::new();
    for point in points {
        assert_eq!(point["drift"], 0, "per-edition drift must be zero");
        effect_days.insert(point["effect_day"].as_i64().expect("effect_day"));
    }
    assert_eq!(
        effect_days.len(),
        118,
        "118 distinct grounded effect days, no same-day collision"
    );

    // Exactly one documented non-monotonic transition: 0036 -> 0037.
    let transitions = payload["non_monotonic_transitions"]
        .as_array()
        .expect("transitions");
    assert_eq!(
        transitions.len(),
        1,
        "exactly one non-monotonic transition is documented"
    );
    assert_eq!(transitions[0]["from_edition"], 36);
    assert_eq!(transitions[0]["to_edition"], 37);
    assert!(
        transitions[0]["applied_day"].as_i64().unwrap()
            >= transitions[0]["to_day"].as_i64().unwrap()
    );
    assert!(
        payload["historical_rebinds"].as_u64().unwrap() > 94,
        "the union of historical statya numbers is re-bound locally"
    );
}

#[test]
fn corpus_dir_constant_matches_the_registry_needle() {
    for path in [
        EDITION_0079,
        EDITION_0080,
        EDITION_0081,
        SYNTH_EARLY_CORPUS,
        SYNTH_LATE_CORPUS,
    ] {
        assert!(
            path.starts_with(CORPUS_44FZ_DIR),
            "{path} must live under {CORPUS_44FZ_DIR}"
        );
    }
}
