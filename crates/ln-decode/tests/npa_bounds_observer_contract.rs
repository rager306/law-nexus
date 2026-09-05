//! T02 contract (M200-8s4kwq S01): the decoder observation seam.
//!
//! The seam ([`SweepObserver`] + [`walk_and_observe`] +
//! [`run_sweep_observed`]) wraps the existing deterministic walker and the
//! production Consultant decode path so a sibling measurement profile
//! (`npa-bounds-scan/v1`, T03) can inspect per-file terminal outcome and
//! decoded fragment-local blocks without copying walk/decode logic. Pinned
//! here: success, malformed atomic failure, unreadable file, `limit = 0`,
//! missing root (seam error / explicit-root exit / skip-mode), and
//! deterministic path order. The `npa-corpus-sweep/v1` byte-stability side
//! lives in `npa_corpus_sweep_contract.rs`.

use std::fs;
use std::path::{Path, PathBuf};

use ln_decode::adapters::ConsultantWordMlBlockDecoder;
use ln_decode::domain::{DecodeRequest, FamilyFormat, ParsedBlock};
use ln_decode::npa_sweep::{
    self, payload_ref_for_path, run_sweep_observed, walk_and_observe, walk_xml_files, FileTerminal,
    SweepCli, SweepObserver, EXIT_OK, EXIT_ROOT_MISSING,
};
use ln_decode::ports::BlockDecoderPort;

const ABSENT: &str = "/npa-bounds-obs-t02-absent-root";

/// Minimal Consultant WordML fixture, byte-for-byte the corpus-sweep
/// contract shape (one paragraph, one text run).
fn wordml_document(text: &str) -> String {
    format!(
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:wordDocument>"#
    )
}

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_root(tag: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("npa-bounds-obs-t02-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp observer root must be creatable");
    dir
}

fn write_xml(root: &Path, relative: &str, text: &str) -> PathBuf {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("relative parent exists")).expect("fixture dir");
    fs::write(&path, wordml_document(text)).expect("fixture xml");
    path
}

/// Recording sink: one row per observed file — path, terminal outcome, and
/// the handed-off block texts (the fragment-local view a T03 bounds
/// accumulator will consume). A test stand-in, not product code.
struct Recording {
    events: Vec<(String, FileTerminal, Vec<String>)>,
}

impl Recording {
    fn new() -> Self {
        Self { events: Vec::new() }
    }

    fn paths(&self) -> Vec<String> {
        self.events.iter().map(|(path, ..)| path.clone()).collect()
    }

    /// The exactly-once event for `path`; asserts the atomicity invariant
    /// (a `Failed` file hands off zero blocks) on the way out.
    fn event_of(&self, path: &Path) -> (FileTerminal, &[String]) {
        let want = path.to_string_lossy().into_owned();
        let mut hit: Option<&(String, FileTerminal, Vec<String>)> = None;
        for event in &self.events {
            if event.0 == want {
                assert!(hit.is_none(), "a file is observed exactly once: {want}");
                hit = Some(event);
            }
        }
        let (_, terminal, blocks) = hit.unwrap_or_else(|| panic!("path never observed: {want}"));
        if *terminal == FileTerminal::Failed {
            assert!(blocks.is_empty(), "Failed hands off zero blocks (atomic)");
        }
        (*terminal, blocks)
    }
}

impl SweepObserver for Recording {
    fn observe_file(&mut self, path: &Path, terminal: FileTerminal, blocks: &[ParsedBlock]) {
        self.events.push((
            path.to_string_lossy().into_owned(),
            terminal,
            blocks.iter().map(|block| block.text().to_owned()).collect(),
        ));
    }
}

/// Production-decoder oracle over the same fixture bytes: the seam must
/// hand off exactly what `ConsultantWordMlBlockDecoder` produces directly.
fn oracle_blocks(path: &Path) -> Vec<String> {
    let bytes = fs::read(path).expect("oracle reads the same fixture");
    let request = DecodeRequest::new(
        payload_ref_for_path(path),
        FamilyFormat::parse("family:consultant-wordml").expect("static family format"),
        &bytes,
    );
    ConsultantWordMlBlockDecoder
        .decode_blocks(&request)
        .expect("fixture decodes through the production decoder")
        .iter()
        .map(|block| block.text().to_owned())
        .collect()
}

/// T02: the success contour — a decoded file reaches the observer exactly
/// once as `Decoded`, with the same fragment-local block texts the
/// production decoder produces directly (production-path reuse, Q3).
#[test]
fn t02_observer_success_reports_decoded_blocks_matching_the_production_decoder() {
    let root = temp_root("success");
    let ok = write_xml(&root, "exports/npa/ok.xml", "ст. 15.1");

    let mut seen = Recording::new();
    let observed = walk_and_observe(&root, None, &mut seen).expect("walk must succeed");

    assert_eq!(observed, 1);
    let (terminal, blocks) = seen.event_of(&ok);
    assert_eq!(terminal, FileTerminal::Decoded);
    assert_eq!(blocks, oracle_blocks(&ok).as_slice());
    assert!(
        !blocks.is_empty(),
        "fragment-local decoded blocks reach the sink"
    );

    fs::remove_dir_all(&root).ok();
}

/// T02: malformed atomic failure — a truncated WordML file is one `Failed`
/// event with zero blocks (no partial measurement ever reaches the sink),
/// while its decoded sibling is unaffected (Q5/Q7).
#[test]
fn t02_observer_malformed_file_is_an_atomic_failed_event() {
    let root = temp_root("malformed");
    let ok = write_xml(&root, "exports/npa/ok.xml", "ст. 1");
    let broken = root.join("exports/npa/broken.xml");
    fs::write(
        &broken,
        r#"<w:wordDocument xmlns:w="urn:word"><w:p><w:r><w:t>Сломан"#,
    )
    .expect("truncated fixture");

    let mut seen = Recording::new();
    let observed = walk_and_observe(&root, None, &mut seen).expect("walk must succeed");

    assert_eq!(observed, 2);
    let (ok_terminal, ok_blocks) = seen.event_of(&ok);
    assert_eq!(ok_terminal, FileTerminal::Decoded);
    assert_eq!(ok_blocks, oracle_blocks(&ok).as_slice());
    let (broken_terminal, broken_blocks) = seen.event_of(&broken);
    assert_eq!(broken_terminal, FileTerminal::Failed);
    assert!(broken_blocks.is_empty(), "atomic failure: zero blocks");

    fs::remove_dir_all(&root).ok();
}

/// T02: an unreadable file (dangling `*.xml` symlink — the walker treats
/// symlinks as leaves) is a `Failed` event, never a walk error: a per-file
/// read failure is accounting, not a corpus abort (Q5).
#[test]
#[cfg(unix)]
fn t02_observer_unreadable_file_is_a_failed_event() {
    let root = temp_root("unreadable");
    let dir = root.join("exports/xml");
    fs::create_dir_all(&dir).expect("exports/xml dir");
    let dead = dir.join("dead.xml");
    std::os::unix::fs::symlink("/npa-bounds-obs-t02-no-such-target", &dead)
        .expect("dangling symlink fixture");

    let mut seen = Recording::new();
    let observed = walk_and_observe(&root, None, &mut seen).expect("walk must succeed");

    assert_eq!(observed, 1);
    let (terminal, blocks) = seen.event_of(&dead);
    assert_eq!(terminal, FileTerminal::Failed);
    assert!(blocks.is_empty());

    fs::remove_dir_all(&root).ok();
}

/// T02: `limit = 0` is a valid empty walk — the observer sees nothing and
/// the seam still reports success (Q7 boundary).
#[test]
fn t02_observer_limit_zero_observes_nothing() {
    let root = temp_root("limit0");
    write_xml(&root, "exports/npa/a.xml", "ст. 2");
    write_xml(&root, "exports/npa/b.xml", "ст. 3");

    let mut seen = Recording::new();
    let observed = walk_and_observe(&root, Some(0), &mut seen).expect("walk must succeed");

    assert_eq!(observed, 0);
    assert!(
        seen.events.is_empty(),
        "no file reaches the sink at limit 0"
    );

    fs::remove_dir_all(&root).ok();
}

/// T02: missing-root surfaces — the seam propagates the walk error; an
/// explicit missing `--root` stays `EXIT_ROOT_MISSING` with no events; a
/// missing default root stays skip-mode with a zeroed closed aggregate and
/// no events (Q5).
#[test]
fn t02_observer_missing_root_error_explicit_and_skip_mode() {
    let absent = Path::new(ABSENT);

    let mut seen = Recording::new();
    assert!(
        walk_and_observe(absent, None, &mut seen).is_err(),
        "the seam propagates a missing root"
    );
    assert!(seen.events.is_empty());

    let mut seen = Recording::new();
    let cli = SweepCli {
        root: Some(ABSENT.to_owned()),
        ..SweepCli::default()
    };
    let run = run_sweep_observed(&cli, absent, &mut seen);
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.jsonl.is_none());
    assert!(seen.events.is_empty(), "no file is observed without a root");

    let mut seen = Recording::new();
    let run = run_sweep_observed(&SweepCli::default(), absent, &mut seen);
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    let jsonl = run.jsonl.expect("skip-mode still renders the aggregate");
    assert!(jsonl.contains("\"files_seen\":0"));
    npa_sweep::validate_jsonl(&jsonl).expect("zeroed aggregate stays closed");
    assert!(seen.events.is_empty());

    fs::remove_dir_all(absent).ok();
}

/// T02: deterministic path order — the observer sees files in exactly the
/// walker's full-path sorted order, twice in a row and independent of tree
/// shape; the `limit` cut happens after the sort, so partial observation
/// stays ordered too (Q7 determinism).
#[test]
fn t02_observer_walk_order_is_deterministic() {
    let root = temp_root("order");
    write_xml(&root, "exports/npa/sub/m.xml", "ст. 4");
    write_xml(&root, "exports/npa/a.xml", "ст. 5");
    write_xml(&root, "exports/xml/b.XML", "ст. 6");
    write_xml(&root, "exports/npa/z.xml", "ст. 7");

    let expected: Vec<String> = walk_xml_files(&root, None)
        .expect("walk must succeed")
        .iter()
        .map(|path| path.to_string_lossy().into_owned())
        .collect();
    assert_eq!(
        expected.len(),
        4,
        "nested tree, `.txt` skipped, `.XML` kept"
    );

    let mut first = Recording::new();
    walk_and_observe(&root, None, &mut first).expect("walk must succeed");
    let mut second = Recording::new();
    walk_and_observe(&root, None, &mut second).expect("walk must succeed");

    assert_eq!(first.paths(), expected, "observer order == walker order");
    assert_eq!(second.paths(), expected, "twice identical");

    let mut limited = Recording::new();
    walk_and_observe(&root, Some(2), &mut limited).expect("walk must succeed");
    assert_eq!(limited.paths(), expected[..2], "limit cuts after the sort");

    fs::remove_dir_all(&root).ok();
}
