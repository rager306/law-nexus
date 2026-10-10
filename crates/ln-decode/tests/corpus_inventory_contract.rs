//! Contract tests for the authoritative corpus hash manifest
//! (M223-d2q075 S02/T01; contract §8.3/§8.6).
//!
//! Everything is hermetic: temp dirs and inline fixtures only. The live
//! `consru_export` corpus is never read by `cargo test` (the real pinned run is
//! the tracked `prd/migration/rust-evidence/m223-s02-corpus-manifest.jsonl`).
//!
//! Proofs cover: deterministic `relative_path` byte ordering; per-file sha256
//! over raw bytes; digest stability across runs; digest sensitivity to a single
//! changed byte; fail-closed refusal on an unreadable entry with no published
//! manifest; empty-tree authority; non-xml exclusion; missing-root fail-closed;
//! the `--limit` boundary; and one thin-binary smoke over `--out`.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;

use ln_decode::corpus_inventory::{
    self, EXIT_OK, EXIT_OUT_UNWRITABLE, EXIT_ROOT_MISSING, EXIT_UNREADABLE_FILE, EXIT_USAGE,
    INVENTORY_SCHEMA, InventoryCli, build_inventory, run_inventory, sha256_bytes,
};

/// Unique per-test temp root; pre-cleaned so reruns start empty.
fn temp_root(tag: &str) -> PathBuf {
    let dir =
        std::env::temp_dir().join(format!("corpus-inventory-t01-{}-{tag}", std::process::id()));
    let _ = fs::remove_dir_all(&dir);
    fs::create_dir_all(&dir).expect("temp inventory root must be creatable");
    dir
}

fn write_file(root: &Path, relative: &str, content: &[u8]) -> PathBuf {
    let path = root.join(relative);
    fs::create_dir_all(path.parent().expect("relative parent exists")).expect("fixture dir");
    fs::write(&path, content).expect("fixture file");
    path
}

fn cli_root(root: &Path) -> InventoryCli {
    InventoryCli {
        root: Some(root.display().to_string()),
        out: None,
        limit: None,
    }
}

/// T01 proof 1: entries are sorted by `relative_path` byte order regardless of
/// write order, each carries a `sha256:`-prefixed 64-hex hash over its raw
/// bytes, and `bytes` matches the actual length.
#[test]
fn t01_entries_are_sorted_and_hashed_over_raw_bytes() {
    let root = temp_root("sorted");
    write_file(&root, "z/last.xml", b"zzz");
    write_file(&root, "a/first.xml", b"alpha");
    write_file(&root, "m/mid.xml", b"1234567");

    let inventory = build_inventory(&root, None).unwrap();
    let paths: Vec<&str> = inventory
        .entries
        .iter()
        .map(|entry| entry.relative_path.as_str())
        .collect();
    assert_eq!(paths, ["a/first.xml", "m/mid.xml", "z/last.xml"]);

    let first = &inventory.entries[0];
    assert_eq!(first.sha256, sha256_bytes(b"alpha"));
    assert_eq!(first.bytes, 5);
    assert!(first.sha256.starts_with("sha256:"));
    assert_eq!(first.sha256.len(), 7 + 64);

    let (entries, total, max) = inventory.counts();
    assert_eq!((entries, total, max), (3, 15, 7));

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 2: the digest is stable across independent runs over the same
/// bytes; the header carries it and the §8.3 pins (drift expected for a
/// fixture corpus).
#[test]
fn t01_digest_is_stable_across_runs() {
    let root = temp_root("stable");
    write_file(&root, "a.xml", b"one");
    write_file(&root, "b.xml", b"two");

    let first = build_inventory(&root, None).unwrap();
    let second = build_inventory(&root, None).unwrap();
    assert_eq!(first.inventory_digest(), second.inventory_digest());
    assert!(first.inventory_digest().starts_with("sha256:"));

    let rendered = first.render_jsonl();
    assert!(rendered.starts_with(&format!(
        "{{\"schema\":\"{INVENTORY_SCHEMA}\",\"version\":1,"
    )));
    assert!(rendered.contains(&format!(
        "\"inventory_digest\":\"{}\"",
        first.inventory_digest()
    )));
    assert!(
        !first.pins_match(),
        "fixture cannot match the pinned corpus"
    );
    assert_eq!(first.pin_drift().len(), 3);

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 3: changing a single byte of a same-length file changes the
/// digest (the manifest is content-bound, not size-bound).
#[test]
fn t01_digest_changes_when_a_byte_changes() {
    let root = temp_root("sensitivity");
    write_file(&root, "a.xml", b"abc");

    let before = build_inventory(&root, None).unwrap();
    write_file(&root, "a.xml", b"abd");
    let after = build_inventory(&root, None).unwrap();

    assert_eq!(before.counts(), after.counts(), "length unchanged");
    assert_ne!(before.inventory_digest(), after.inventory_digest());

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 4: an unreadable entry is a typed refusal. The run exits non-zero
/// and publishes nothing to stdout, and `--out` is not written (no partial
/// manifest as authoritative).
#[test]
#[cfg(unix)]
fn t01_unreadable_file_refuses_and_publishes_nothing() {
    let root = temp_root("unreadable");
    write_file(&root, "good.xml", b"ok");
    std::os::unix::fs::symlink(root.join("does-not-exist.xml"), root.join("bad.xml"))
        .expect("dangling symlink fixture");

    let direct = build_inventory(&root, None).unwrap_err();
    match &direct {
        corpus_inventory::InventoryError::Unreadable { relative_path, .. } => {
            assert_eq!(relative_path, "bad.xml");
        }
        other => panic!("expected typed unreadable error, got {other:?}"),
    }

    let out_path = root.join("manifest.jsonl");
    let mut cli = cli_root(&root);
    cli.out = Some(out_path.display().to_string());
    let run = run_inventory(&cli, Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_UNREADABLE_FILE);
    assert!(run.jsonl.is_none());
    assert!(!run.to_stdout);
    assert!(
        !out_path.exists(),
        "fail-closed: no partial manifest is written on refusal"
    );

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 5: an existing-but-empty tree is an authoritative zero inventory
/// (exit 0, empty-stream digest), distinct from a missing root.
#[test]
fn t01_empty_tree_is_authoritative_zero_inventory() {
    let root = temp_root("empty");
    let run = run_inventory(&cli_root(&root), Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_OK);
    assert!(run.to_stdout);
    let jsonl = run.jsonl.expect("stdout manifest");
    assert!(jsonl.contains("\"counts\":{\"entries\":0,\"total_bytes\":0,\"max_bytes\":0}"));
    assert!(jsonl.contains(
        "\"inventory_digest\":\"sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\""
    ));
    assert!(run.stderr.contains("entries=0"));

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 6: only `*.xml` (case-insensitive) is inventoried; `.txt`/`.odt`
/// neighbours are skipped.
#[test]
fn t01_non_xml_is_ignored() {
    let root = temp_root("nonxml");
    write_file(&root, "keep.xml", b"k");
    write_file(&root, "shout.XML", b"s");
    write_file(&root, "drop.txt", b"t");
    write_file(&root, "drop.odt", b"o");

    let inventory = build_inventory(&root, None).unwrap();
    let mut paths: Vec<&str> = inventory
        .entries
        .iter()
        .map(|entry| entry.relative_path.as_str())
        .collect();
    paths.sort_unstable();
    assert_eq!(paths, ["keep.xml", "shout.XML"]);

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 7: an absent root is fail-closed (no zeroed manifest published).
#[test]
fn t01_missing_root_is_fail_closed() {
    let missing = Path::new("/corpus-inventory-t01-absent-root");
    let run = run_inventory(&cli_root(missing), Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_ROOT_MISSING);
    assert!(run.jsonl.is_none());
    assert!(!run.to_stdout);
}

/// T01 proof 8: `--limit` truncates after the deterministic sort and is visible
/// as pin drift in the header, never swallowed.
#[test]
fn t01_limit_zero_is_empty_walk_with_drift() {
    let root = temp_root("limit");
    write_file(&root, "a.xml", b"a");
    write_file(&root, "b.xml", b"b");

    let mut cli = cli_root(&root);
    cli.limit = Some(0);
    let run = run_inventory(&cli, Path::new("/unused-default"));
    assert_eq!(run.exit_code, EXIT_OK);
    let jsonl = run.jsonl.expect("stdout manifest");
    assert!(jsonl.contains("\"counts\":{\"entries\":0,"));
    assert!(jsonl.contains("\"match\":false"));
    assert!(jsonl.contains("drift"));
    assert!(run.stderr.contains("pins=drift"));

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 9: the thin binary writes the manifest to `--out`, prints
/// counts/pins to stderr, and exits 0; usage errors exit 2 and an unwritable
/// `--out` exits 3.
#[test]
fn t01_bin_smoke_out_and_errors() {
    let root = temp_root("bin");
    write_file(&root, "a.xml", b"alpha");
    let out_path = root.join("manifest.jsonl");

    let output = Command::new(env!("CARGO_BIN_EXE_corpus-inventory"))
        .arg("--root")
        .arg(&root)
        .arg("--out")
        .arg(&out_path)
        .output()
        .expect("binary must run");
    assert!(output.status.success(), "inventory run must exit 0");
    assert!(
        output.stdout.is_empty(),
        "manifest goes to --out, not stdout"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("entries=1"), "counts on stderr: {stderr}");
    assert!(stderr.contains("pins=drift"), "pin verdict on stderr");
    let written = fs::read_to_string(&out_path).expect("manifest written");
    assert!(written.starts_with('{'));
    assert!(written.contains(&format!("\"schema\":\"{INVENTORY_SCHEMA}\"")));
    assert!(written.contains(&format!("\"sha256\":\"{}\"", sha256_bytes(b"alpha"))));

    let usage = Command::new(env!("CARGO_BIN_EXE_corpus-inventory"))
        .arg("--bogus")
        .output()
        .expect("binary must run");
    assert_eq!(usage.status.code(), Some(i32::from(EXIT_USAGE)));

    let unwritable = Command::new(env!("CARGO_BIN_EXE_corpus-inventory"))
        .arg("--root")
        .arg(&root)
        .arg("--out")
        .arg(root.join("missing-dir/manifest.jsonl"))
        .output()
        .expect("binary must run");
    assert_eq!(
        unwritable.status.code(),
        Some(i32::from(EXIT_OUT_UNWRITABLE))
    );

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 10: the renderer emits exactly one header line plus one record per
/// entry (closed shape; no dropped or duplicated rows).
#[test]
fn t01_render_has_one_line_per_entry_plus_header() {
    let root = temp_root("lines");
    write_file(&root, "a.xml", b"a");
    write_file(&root, "b/c.xml", b"bc");

    let inventory = build_inventory(&root, None).unwrap();
    let rendered = inventory.render_jsonl();
    let lines: Vec<&str> = rendered.lines().collect();
    assert_eq!(lines.len(), 1 + inventory.entries.len());
    assert!(lines[0].contains("\"schema\":\"m223-s02-corpus-inventory/v1\""));
    assert!(lines[1].starts_with("{\"relative_path\":\"a.xml\""));
    assert!(lines[2].starts_with("{\"relative_path\":\"b/c.xml\""));

    fs::remove_dir_all(&root).ok();
}

/// T01 proof 11: redaction — the manifest carries paths, counts, and hashes
/// only; raw file bytes never appear in the rendered evidence.
#[test]
fn t01_render_never_contains_raw_content() {
    let root = temp_root("redaction");
    let raw = b"RAW-CONTENT-MARKER-do-not-leak";
    write_file(&root, "a.xml", raw);

    let inventory = build_inventory(&root, None).unwrap();
    let rendered = inventory.render_jsonl();
    assert!(
        !rendered.contains("RAW-CONTENT-MARKER"),
        "raw bytes must never reach the manifest"
    );
    assert!(
        rendered.contains(&sha256_bytes(raw)),
        "hash present instead"
    );

    fs::remove_dir_all(&root).ok();
}
