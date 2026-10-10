//! Authoritative per-file hash manifest of the pinned Consultant XML corpus
//! (M223-d2q075 S02/T01; contract `intermediate-source-acceptance-contract.md`
//! §8.3 and §8.6).
//!
//! Behavior lives here; argv parsing and output wiring live in the thin
//! `src/bin/corpus-inventory.rs` (the thin-bin convention of `npa_sweep`), so
//! contract tests exercise library functions instead of shelling out. Stdlib
//! only: no clap, no walkdir, no serde.
//!
//! The walk is the shared deterministic [`crate::npa_sweep::walk_xml_files`]
//! (recursive, per-level sorted, `*.xml` case-insensitive, symlinked
//! directories kept as leaves so a cycle cannot recurse forever). Each file is
//! streamed through sha256 over its raw bytes; no decoded text ever reaches a
//! diagnostic or the manifest.
//!
//! `inventory_digest` is sha256 over the canonical stream of entries sorted by
//! `relative_path` byte order, one row per entry as
//! `relative_path "\n" sha256 "\n"` — the structural convention of
//! `npa_corpus_acceptance::CorpusSampleManifest` (deterministic sha256 over the
//! sorted per-file `(relative_path, hash)` inventory). A filesystem path cannot
//! contain a newline, so the form is unambiguous and freezes the algorithm.

use std::collections::BTreeMap;
use std::fmt::Write as _;
use std::fs;
use std::io::Read;
use std::path::{Component, Path, PathBuf};

use sha2::{Digest, Sha256};

use crate::npa_sweep::walk_xml_files;

/// Closed JSONL schema id for the S02 corpus inventory.
pub const INVENTORY_SCHEMA: &str = "m223-s02-corpus-inventory/v1";
/// Schema version carried in the header record.
pub const INVENTORY_SCHEMA_VERSION: u32 = 1;

/// §8.3 pinned XML file count for the pinned corpus root.
pub const PINNED_COUNT: u64 = 43_785;
/// §8.3 pinned total byte size of the pinned corpus.
pub const PINNED_TOTAL_BYTES: u64 = 3_789_431_364;
/// §8.3 pinned largest single-file byte size.
pub const PINNED_MAX_BYTES: u64 = 29_372_660;

/// Exit code: manifest completed (pins may match or drift; both are valid,
/// drift is recorded, never silent).
pub const EXIT_OK: u8 = 0;
/// Exit code: malformed argv.
pub const EXIT_USAGE: u8 = 2;
/// Exit code: `--out` could not be opened for writing.
pub const EXIT_OUT_UNWRITABLE: u8 = 3;
/// Exit code: the explicit or default root is absent or not a directory.
/// Fail-closed: no zeroed manifest is published for a missing corpus.
pub const EXIT_ROOT_MISSING: u8 = 4;
/// Exit code: the deterministic walk failed.
pub const EXIT_WALK_FAILED: u8 = 5;
/// Exit code: a discovered XML file could not be opened or read. Fail-closed:
/// no partial manifest is published as authoritative.
pub const EXIT_UNREADABLE_FILE: u8 = 6;

/// Parsed `corpus-inventory` argv.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct InventoryCli {
    /// Explicit root; default is the resolved Consultant export.
    pub root: Option<String>,
    /// Write the JSONL manifest here instead of stdout.
    pub out: Option<String>,
    /// Cap on XML files, applied after the deterministic sort; `0` is a valid
    /// empty walk (and a pin drift by construction).
    pub limit: Option<u64>,
}

/// Strict stdlib argv parser: `--root`, `--out`, `--limit`, each with a
/// following value; later occurrences override earlier ones. Unknown flags,
/// positionals, missing values, and non-numeric limits are usage errors.
pub fn parse_inventory_args<I>(args: I) -> Result<InventoryCli, String>
where
    I: IntoIterator<Item = String>,
{
    let mut cli = InventoryCli::default();
    let mut iter = args.into_iter();
    while let Some(arg) = iter.next() {
        match arg.as_str() {
            "--root" => cli.root = Some(next_value(&mut iter, "--root")?),
            "--out" => cli.out = Some(next_value(&mut iter, "--out")?),
            "--limit" => {
                let raw = next_value(&mut iter, "--limit")?;
                let parsed = raw
                    .parse::<u64>()
                    .map_err(|_| format!("--limit expects a non-negative integer, got '{raw}'"))?;
                cli.limit = Some(parsed);
            }
            other => return Err(format!("unexpected argument '{other}'")),
        }
    }
    Ok(cli)
}

fn next_value(iter: &mut impl Iterator<Item = String>, flag: &str) -> Result<String, String> {
    iter.next()
        .ok_or_else(|| format!("missing value for {flag}"))
}

/// One pinned file: repo-relative path, `sha256:`-prefixed content hash over
/// raw bytes, and byte length.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InventoryEntry {
    /// Path relative to the inventory root, `/`-joined (deterministic across
    /// platforms).
    pub relative_path: String,
    /// Content hash `sha256:<64 lowercase hex>` over the raw file bytes.
    pub sha256: String,
    /// Raw byte length of the file.
    pub bytes: u64,
}

/// Per-top-level-subdirectory accounting used for the header `subdirs` map.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct SubdirCount {
    /// Number of XML entries under this top-level component.
    pub entries: u64,
    /// Summed raw byte length of those entries.
    pub bytes: u64,
}

/// A complete, sorted corpus inventory.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Inventory {
    /// Root as given (display form).
    pub root: String,
    /// All entries, sorted by `relative_path` byte order.
    pub entries: Vec<InventoryEntry>,
}

impl Inventory {
    /// `(entries, total_bytes, max_bytes)`; empty inventory is `(0, 0, 0)`.
    pub fn counts(&self) -> (u64, u64, u64) {
        let entries = self.entries.len() as u64;
        let mut total: u64 = 0;
        let mut max: u64 = 0;
        for entry in &self.entries {
            total = total.saturating_add(entry.bytes);
            max = max.max(entry.bytes);
        }
        (entries, total, max)
    }

    /// Per-top-level-component counts, keyed by the first `/`-separated path
    /// component (a root-level file keys on its own name). `BTreeMap` keeps
    /// the header order deterministic.
    pub fn subdirs(&self) -> BTreeMap<String, SubdirCount> {
        let mut map: BTreeMap<String, SubdirCount> = BTreeMap::new();
        for entry in &self.entries {
            let key = entry
                .relative_path
                .split('/')
                .next()
                .unwrap_or_default()
                .to_owned();
            let slot = map.entry(key).or_default();
            slot.entries += 1;
            slot.bytes = slot.bytes.saturating_add(entry.bytes);
        }
        map
    }

    /// Explicit pin drift against §8.3, one human-readable row per mismatch;
    /// empty means the observed corpus matches the pinned values.
    pub fn pin_drift(&self) -> Vec<String> {
        let (entries, total, max) = self.counts();
        let mut drift = Vec::new();
        if entries != PINNED_COUNT {
            drift.push(format!(
                "count: observed {entries} vs pinned {PINNED_COUNT}"
            ));
        }
        if total != PINNED_TOTAL_BYTES {
            drift.push(format!(
                "total_bytes: observed {total} vs pinned {PINNED_TOTAL_BYTES}"
            ));
        }
        if max != PINNED_MAX_BYTES {
            drift.push(format!(
                "max_bytes: observed {max} vs pinned {PINNED_MAX_BYTES}"
            ));
        }
        drift
    }

    /// True when count, total bytes, and max bytes all match §8.3.
    pub fn pins_match(&self) -> bool {
        self.pin_drift().is_empty()
    }

    /// Canonical digest over the sorted `(relative_path, sha256)` inventory.
    pub fn inventory_digest(&self) -> String {
        inventory_digest(&self.entries)
    }

    /// Render the closed-schema JSONL manifest: one header record followed by
    /// one record per entry, in `relative_path` byte order.
    pub fn render_jsonl(&self) -> String {
        let (entries, total_bytes, max_bytes) = self.counts();
        let subdirs = self.subdirs();
        let drift = self.pin_drift();
        let mut out = String::with_capacity(96 + self.entries.len() * 128);

        let _ = write!(
            out,
            "{{\"schema\":{},\"version\":{},\"root\":{},\"counts\":{{\"entries\":{entries},\"total_bytes\":{total_bytes},\"max_bytes\":{max_bytes}}},\"subdirs\":{{",
            quote(INVENTORY_SCHEMA),
            INVENTORY_SCHEMA_VERSION,
            quote(&self.root),
        );
        let mut first = true;
        for (name, count) in &subdirs {
            if !first {
                out.push(',');
            }
            first = false;
            let _ = write!(
                out,
                "{}:{{\"entries\":{},\"bytes\":{}}}",
                quote(name),
                count.entries,
                count.bytes
            );
        }
        let _ = write!(
            out,
            "}},\"pins\":{{\"count\":{PINNED_COUNT},\"total_bytes\":{PINNED_TOTAL_BYTES},\"max_bytes\":{PINNED_MAX_BYTES},\"match\":{},\"drift\":[",
            drift.is_empty()
        );
        for (index, row) in drift.iter().enumerate() {
            if index > 0 {
                out.push(',');
            }
            out.push_str(&quote(row));
        }
        let _ = writeln!(
            out,
            "]}},\"inventory_digest\":{}}}",
            quote(&self.inventory_digest())
        );

        for entry in &self.entries {
            let _ = writeln!(
                out,
                "{{\"relative_path\":{},\"sha256\":{},\"bytes\":{}}}",
                quote(&entry.relative_path),
                quote(&entry.sha256),
                entry.bytes
            );
        }
        out
    }
}

/// Typed refusal from [`build_inventory`]. Both variants are fail-closed: the
/// caller must not publish a partial manifest.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InventoryError {
    /// The deterministic walk failed (unreadable directory, path outside root).
    Walk(String),
    /// A discovered XML file could not be opened or read.
    Unreadable {
        /// Path of the unreadable entry relative to the root.
        relative_path: String,
        /// Underlying I/O message.
        message: String,
    },
}

impl std::fmt::Display for InventoryError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InventoryError::Walk(message) => write!(formatter, "walk failed: {message}"),
            InventoryError::Unreadable {
                relative_path,
                message,
            } => write!(formatter, "unreadable file {relative_path}: {message}"),
        }
    }
}

/// Outcome of a library-level inventory run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InventoryRun {
    /// Process exit code for the binary.
    pub exit_code: u8,
    /// Rendered manifest when it goes to stdout; `None` when written to
    /// `--out` or when the run refused.
    pub jsonl: Option<String>,
    /// Whether `jsonl` belongs on stdout.
    pub to_stdout: bool,
    /// Counts/pins line for stderr — counts, paths, and hashes only, never
    /// decoded text (Q3).
    pub stderr: String,
}

/// Deterministic sha256 over the sorted `(relative_path, sha256)` inventory:
/// each entry becomes a `relative_path "\n" sha256` row, rows are sorted, and
/// every row is fed to the hasher followed by a newline.
pub fn inventory_digest(entries: &[InventoryEntry]) -> String {
    let mut rows: Vec<String> = entries
        .iter()
        .map(|entry| {
            format!(
                "{}\n{}",
                entry.relative_path,
                normalize_sha256(&entry.sha256)
            )
        })
        .collect();
    rows.sort();
    let mut hasher = Sha256::new();
    for row in &rows {
        hasher.update(row.as_bytes());
        hasher.update(b"\n");
    }
    format!("sha256:{}", hex_lower(&hasher.finalize()))
}

/// Streaming sha256 of an in-memory buffer, `sha256:`-prefixed lowercase hex.
pub fn sha256_bytes(bytes: &[u8]) -> String {
    format!("sha256:{}", hex_lower(&Sha256::digest(bytes)))
}

/// Build the inventory for `root`: deterministic XML walk, per-file streaming
/// sha256 over raw bytes, sorted by `relative_path` byte order. Any unreadable
/// file is a typed [`InventoryError::Unreadable`] and aborts the build.
pub fn build_inventory(root: &Path, limit: Option<u64>) -> Result<Inventory, InventoryError> {
    let files =
        walk_xml_files(root, limit).map_err(|error| InventoryError::Walk(error.to_string()))?;
    let mut entries = Vec::with_capacity(files.len());
    for path in files {
        let relative = path
            .strip_prefix(root)
            .map_err(|_| InventoryError::Walk(format!("path outside root: {}", path.display())))?;
        let relative_path = relative_path_string(relative);
        let (sha256, bytes) = sha256_file(&path).map_err(|error| InventoryError::Unreadable {
            relative_path: relative_path.clone(),
            message: error.to_string(),
        })?;
        entries.push(InventoryEntry {
            relative_path,
            sha256,
            bytes,
        });
    }
    entries.sort_by(|left, right| {
        left.relative_path
            .as_bytes()
            .cmp(right.relative_path.as_bytes())
    });
    Ok(Inventory {
        root: root.display().to_string(),
        entries,
    })
}

/// Library-level inventory runner: exactly what the binary does after argv
/// parsing. `default_root` is injected so tests never touch the live
/// `consru_export` corpus; the binary passes
/// [`crate::npa_sweep::default_sweep_root`].
pub fn run_inventory(cli: &InventoryCli, default_root: &Path) -> InventoryRun {
    let root = cli
        .root
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| default_root.to_path_buf());

    if !root.is_dir() {
        return InventoryRun {
            exit_code: EXIT_ROOT_MISSING,
            jsonl: None,
            to_stdout: false,
            stderr: format!("root not found: {}", root.display()),
        };
    }

    let inventory = match build_inventory(&root, cli.limit) {
        Ok(inventory) => inventory,
        Err(InventoryError::Walk(message)) => {
            return InventoryRun {
                exit_code: EXIT_WALK_FAILED,
                jsonl: None,
                to_stdout: false,
                stderr: format!("walk failed: {message}"),
            };
        }
        Err(error @ InventoryError::Unreadable { .. }) => {
            return InventoryRun {
                exit_code: EXIT_UNREADABLE_FILE,
                jsonl: None,
                to_stdout: false,
                stderr: error.to_string(),
            };
        }
    };

    let (entries, total_bytes, max_bytes) = inventory.counts();
    let pin_note = if inventory.pins_match() {
        "match"
    } else {
        "drift"
    };
    let stderr = format!(
        "entries={entries} total_bytes={total_bytes} max_bytes={max_bytes} pins={pin_note} digest={}",
        inventory.inventory_digest()
    );
    let jsonl = inventory.render_jsonl();

    match &cli.out {
        None => InventoryRun {
            exit_code: EXIT_OK,
            jsonl: Some(jsonl),
            to_stdout: true,
            stderr,
        },
        Some(out_path) => match fs::write(out_path, &jsonl) {
            Ok(()) => InventoryRun {
                exit_code: EXIT_OK,
                jsonl: None,
                to_stdout: false,
                stderr,
            },
            Err(error) => InventoryRun {
                exit_code: EXIT_OUT_UNWRITABLE,
                jsonl: None,
                to_stdout: false,
                stderr: format!("cannot open --out {out_path}: {error}"),
            },
        },
    }
}

/// Stream one file through sha256 and report `(hash, byte length)`.
fn sha256_file(path: &Path) -> std::io::Result<(String, u64)> {
    let mut file = fs::File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    let mut total: u64 = 0;
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
        total = total.saturating_add(read as u64);
    }
    Ok((format!("sha256:{}", hex_lower(&hasher.finalize())), total))
}

/// `relative_path` as `/`-joined components, deterministic across platforms.
fn relative_path_string(relative: &Path) -> String {
    let mut out = String::new();
    for (index, component) in relative.components().enumerate() {
        if index > 0 {
            out.push('/');
        }
        match component {
            Component::Normal(part) => out.push_str(&part.to_string_lossy()),
            other => out.push_str(&other.as_os_str().to_string_lossy()),
        }
    }
    out
}

/// Strip an optional `sha256:` prefix and lowercase (inventory convention).
fn normalize_sha256(value: &str) -> String {
    value
        .strip_prefix("sha256:")
        .unwrap_or(value)
        .to_ascii_lowercase()
}

fn hex_lower(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        let _ = write!(out, "{byte:02x}");
    }
    out
}

/// Minimal JSON string escaper matching the `npa_sweep` renderer: quotes,
/// backslashes, and control characters are the only escapes emitted.
fn quote(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    out.push('"');
    for ch in value.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            ch if (ch as u32) < 0x20 => {
                let _ = write!(out, "\\u{:04x}", ch as u32);
            }
            ch => out.push(ch),
        }
    }
    out.push('"');
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn entry(relative_path: &str, sha256: &str, bytes: u64) -> InventoryEntry {
        InventoryEntry {
            relative_path: relative_path.to_owned(),
            sha256: sha256.to_owned(),
            bytes,
        }
    }

    /// The digest algorithm is frozen: two explicitly-constructed entries must
    /// hash to the pinned value. Guards against silent canonical-form drift.
    #[test]
    fn inventory_digest_is_frozen() {
        let entries = [
            entry("b.xml", "sha256:BB", 2),
            entry("a.xml", "sha256:AA", 1),
        ];
        assert_eq!(
            inventory_digest(&entries),
            "sha256:c8beeb82cbf9b18d38980f38d800937ac9abe8761f6d2fe02a2488fb876cc2e0"
        );
    }

    #[test]
    fn sha256_bytes_is_frozen() {
        assert_eq!(
            sha256_bytes(b"hello"),
            "sha256:2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        );
    }

    #[test]
    fn empty_inventory_counts_and_digest() {
        let inventory = Inventory {
            root: "empty".to_owned(),
            entries: Vec::new(),
        };
        assert_eq!(inventory.counts(), (0, 0, 0));
        assert!(inventory.pin_drift().len() == 3, "empty drifts on all pins");
        assert_eq!(
            inventory.inventory_digest(),
            "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn subdirs_group_by_first_component() {
        let inventory = Inventory {
            root: "r".to_owned(),
            entries: vec![
                entry("fas/a.xml", "sha256:aa", 1),
                entry("fas/b.xml", "sha256:bb", 2),
                entry("npa/c.xml", "sha256:cc", 4),
                entry("loose.xml", "sha256:dd", 8),
            ],
        };
        let subdirs = inventory.subdirs();
        assert_eq!(
            subdirs["fas"],
            SubdirCount {
                entries: 2,
                bytes: 3
            }
        );
        assert_eq!(
            subdirs["npa"],
            SubdirCount {
                entries: 1,
                bytes: 4
            }
        );
        assert_eq!(
            subdirs["loose.xml"],
            SubdirCount {
                entries: 1,
                bytes: 8
            }
        );
    }

    #[test]
    fn parse_inventory_args_contract() {
        let cli = parse_inventory_args([
            "--root".to_owned(),
            "/tmp/x".to_owned(),
            "--out".to_owned(),
            "/tmp/out.jsonl".to_owned(),
            "--limit".to_owned(),
            "7".to_owned(),
        ])
        .unwrap();
        assert_eq!(cli.root.as_deref(), Some("/tmp/x"));
        assert_eq!(cli.out.as_deref(), Some("/tmp/out.jsonl"));
        assert_eq!(cli.limit, Some(7));

        assert!(parse_inventory_args(["--bogus".to_owned()]).is_err());
        assert!(parse_inventory_args(["--root".to_owned()]).is_err());
        assert!(parse_inventory_args(["--limit".to_owned(), "nope".to_owned()]).is_err());
    }

    #[test]
    fn render_header_reports_pins_and_digest() {
        let inventory = Inventory {
            root: "/corpus".to_owned(),
            entries: vec![entry("a.xml", "sha256:aa", 3)],
        };
        let rendered = inventory.render_jsonl();
        assert!(rendered.starts_with(
            "{\"schema\":\"m223-s02-corpus-inventory/v1\",\"version\":1,\"root\":\"/corpus\""
        ));
        assert!(rendered.contains("\"counts\":{\"entries\":1,\"total_bytes\":3,\"max_bytes\":3}"));
        assert!(rendered.contains("\"subdirs\":{\"a.xml\":{\"entries\":1,\"bytes\":3}}"));
        assert!(rendered.contains("\"pins\":{\"count\":43785,\"total_bytes\":3789431364,\"max_bytes\":29372660,\"match\":false,\"drift\":["));
        assert!(rendered
            .ends_with("{\"relative_path\":\"a.xml\",\"sha256\":\"sha256:aa\",\"bytes\":3}\n"));
    }
}
