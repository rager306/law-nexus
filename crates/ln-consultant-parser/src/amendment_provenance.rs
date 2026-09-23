//! M209/S03 amendment-provenance evidence model (D552 / D554).
//!
//! Count-only, ASCII-only, fail-closed. This module declares the S03 family
//! denominator for the named `cc:44-fz` Work chain: it counts records in the
//! four provider manifests, inventories the four provider export directories,
//! and reconciles the `law_2013-04-05_44-fz` edition directory.
//!
//! Nothing here reads legal text. Only record counts, repository-relative
//! paths, byte counts, SHA-256 pins and short categorical keys enter the
//! rendered artifact. A corpus title, an offline URI or an XML fragment in the
//! artifact is a `raw_text_leak`; a non-ASCII byte is `non_ascii_evidence`; a
//! declared total of zero is `zero_denominator`; a decomposition whose parts do
//! not sum to its declared total is `family_count_unsupported` (D552).
//!
//! The provider export is untracked and licensed (`consru_export/` is
//! gitignored), so a pinned count plus bytes plus SHA-256 is the only lawful
//! durable form of the denominator. Denominators are always re-derived live;
//! nothing is hardcoded. Byte counts and digests are recomputed on every run,
//! and `--check` re-renders in memory and compares whole-file bytes (D424).
//!
//! The SHA-256 implementation below is local and dependency-free so the
//! emitter stays deterministic offline and never spawns a helper binary
//! (contrast `crate::corpus_manifest`, which shells out to `sha256sum`). It is
//! pinned by the NIST test vectors in the unit tests.

use std::collections::BTreeMap;
use std::fmt;
use std::fs;
use std::io;
use std::path::{Component, Path, PathBuf};

/// Artifact schema for the S03 family denominator.
pub const SCHEMA: &str = "law-nexus/r070-family-denominator/v1";
/// Artifact kind discriminator.
pub const KIND: &str = "m209-s03-family-denominator";
/// Owning milestone.
pub const MILESTONE: &str = "M209-2yg6ix";
/// Owning slice.
pub const SLICE: &str = "S03";
/// Owning task.
pub const TASK: &str = "T01";
/// Lifecycle marker: bounded evidence only, never validated.
pub const LIFECYCLE: &str = "[bounded]";
/// Requirement under measurement.
pub const REQUIREMENT_ID: &str = "R070";
/// R070 disposition after this artifact (D416).
pub const DISPOSITION: &str = "active";
/// Decision that keeps R070 active.
pub const DISPOSITION_DECISION: &str = "D416";
/// Named Work chain this denominator is scoped to.
pub const CHAIN_ID: &str = "cc:44-fz";
/// Environment override for the export directory.
pub const EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
/// Default export directory, matching `tests/classifier_recall_test.rs`.
pub const EXPORT_DIR_DEFAULT: &str = "consru_export";
/// Inner provider-export directory name under the operator-supplied root.
pub const EXPORT_ROOT_TAIL: &str = "consru_export";
/// Edition directory of the named chain, relative to the provider export root.
pub const EDITION_DIR_TAIL: &str = "exports/npa/law_2013-04-05_44-fz";
/// Decomposition key for files that sit directly under the walked directory.
pub const ROOT_KEY: &str = "__root__";
/// Prefix of an admitted edition file name.
pub const EDITION_FILE_PREFIX: &str = "edition-";

/// Fail-closed codes the `families` mode can emit.
///
/// The node contract asserts that its documented code block equals this array,
/// which is also emitted verbatim as the artifact's `fail_closed_codes` field,
/// so a code can never be documented without being reachable and never be
/// reachable without being documented.
pub const FAMILY_DENOMINATOR_CODES: [&str; 7] = [
    "input_absent",
    "input_hash_mismatch",
    "family_count_unsupported",
    "zero_denominator",
    "non_ascii_evidence",
    "raw_text_leak",
    "edition_dir_unreadable",
];

/// Substrings that may only come from provider corpus prose. Their presence in
/// a rendered artifact is a leak, because the emitter counts records and never
/// copies field values other than validated categorical keys.
const CORPUS_TEXT_MARKERS: [&str; 3] = ["consultantplus://", "<w:", "screenTip"];

/// Longest categorical decomposition key the strict token rule accepts.
const MAX_KEY_LEN: usize = 64;

/// Typed failure surface. Variants carry identifiers, paths and details only —
/// never provider text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AmendmentProvenanceError {
    Usage {
        detail: String,
    },
    PathDrift {
        path: String,
    },
    OutUnwritable {
        path: String,
    },
    InputAbsent {
        path: String,
    },
    InputHashMismatch {
        family_id: String,
        path: String,
        detail: String,
    },
    FamilyCountUnsupported {
        family_id: String,
        detail: String,
    },
    ZeroDenominator {
        family_id: String,
    },
    NonAsciiEvidence {
        detail: String,
    },
    RawTextLeak {
        detail: String,
    },
    EditionDirUnreadable {
        path: String,
    },
}

impl AmendmentProvenanceError {
    /// Pinned CLI exit code per failure class.
    pub fn exit_code(&self) -> i32 {
        match self {
            Self::Usage { .. } | Self::PathDrift { .. } => 2,
            Self::InputAbsent { .. } | Self::EditionDirUnreadable { .. } => 3,
            Self::OutUnwritable { .. } => 4,
            Self::InputHashMismatch { .. }
            | Self::FamilyCountUnsupported { .. }
            | Self::ZeroDenominator { .. }
            | Self::NonAsciiEvidence { .. }
            | Self::RawTextLeak { .. } => 6,
        }
    }

    /// The named fail-closed code, or `None` for operator/IO failures that are
    /// not part of the documented evidence code set.
    pub fn code(&self) -> Option<&'static str> {
        match self {
            Self::Usage { .. } | Self::PathDrift { .. } | Self::OutUnwritable { .. } => None,
            Self::InputAbsent { .. } => Some("input_absent"),
            Self::InputHashMismatch { .. } => Some("input_hash_mismatch"),
            Self::FamilyCountUnsupported { .. } => Some("family_count_unsupported"),
            Self::ZeroDenominator { .. } => Some("zero_denominator"),
            Self::NonAsciiEvidence { .. } => Some("non_ascii_evidence"),
            Self::RawTextLeak { .. } => Some("raw_text_leak"),
            Self::EditionDirUnreadable { .. } => Some("edition_dir_unreadable"),
        }
    }

    /// Single count-only stderr line. Drift classes use the pinned
    /// `drift=<code>` shape; operational failures use `error=<class>`.
    pub fn cli_line(&self) -> String {
        match self {
            Self::Usage { detail } => format!("error=usage detail={detail}"),
            Self::PathDrift { path } => format!("error=path-drift path={path}"),
            Self::OutUnwritable { path } => format!("error=out-unwritable path={path}"),
            Self::InputAbsent { path } => format!("error=input-absent path={path}"),
            Self::EditionDirUnreadable { path } => {
                format!("error=edition-dir-unreadable path={path}")
            }
            other => {
                let code = other.code().unwrap_or("unknown");
                format!("drift={code} detail={other}")
            }
        }
    }
}

impl fmt::Display for AmendmentProvenanceError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Usage { detail } => write!(formatter, "usage error: {detail}"),
            Self::PathDrift { path } => write!(formatter, "path drift: {path}"),
            Self::OutUnwritable { path } => write!(formatter, "output unwritable: {path}"),
            Self::InputAbsent { path } => write!(formatter, "input absent: {path}"),
            Self::InputHashMismatch {
                family_id,
                path,
                detail,
            } => {
                write!(
                    formatter,
                    "input hash mismatch: family={family_id} path={path} {detail}"
                )
            }
            Self::FamilyCountUnsupported { family_id, detail } => {
                write!(
                    formatter,
                    "family count unsupported: family={family_id} {detail}"
                )
            }
            Self::ZeroDenominator { family_id } => {
                write!(formatter, "zero denominator: family={family_id}")
            }
            Self::NonAsciiEvidence { detail } => write!(formatter, "non-ascii evidence: {detail}"),
            Self::RawTextLeak { detail } => write!(formatter, "raw text leak: {detail}"),
            Self::EditionDirUnreadable { path } => {
                write!(formatter, "edition directory unreadable: {path}")
            }
        }
    }
}

impl std::error::Error for AmendmentProvenanceError {}

fn usage(detail: impl Into<String>) -> AmendmentProvenanceError {
    AmendmentProvenanceError::Usage {
        detail: detail.into(),
    }
}

fn input_absent(path: impl Into<String>) -> AmendmentProvenanceError {
    AmendmentProvenanceError::InputAbsent { path: path.into() }
}

fn family_unsupported(
    family_id: impl Into<String>,
    detail: impl Into<String>,
) -> AmendmentProvenanceError {
    AmendmentProvenanceError::FamilyCountUnsupported {
        family_id: family_id.into(),
        detail: detail.into(),
    }
}

// ---------------------------------------------------------------------------
// SHA-256 (local, dependency-free)
// ---------------------------------------------------------------------------

const SHA256_K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

const SHA256_H: [u32; 8] = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
];

/// SHA-256 digest of `bytes`.
pub fn sha256_digest(bytes: &[u8]) -> [u8; 32] {
    let mut state = SHA256_H;
    let bit_len = (bytes.len() as u64).wrapping_mul(8);
    let mut message = bytes.to_vec();
    message.push(0x80);
    while message.len() % 64 != 56 {
        message.push(0);
    }
    message.extend_from_slice(&bit_len.to_be_bytes());

    for chunk in message.as_chunks::<64>().0 {
        let mut w = [0u32; 64];
        for (index, word) in w.iter_mut().enumerate().take(16) {
            let base = index * 4;
            *word = u32::from_be_bytes([
                chunk[base],
                chunk[base + 1],
                chunk[base + 2],
                chunk[base + 3],
            ]);
        }
        for index in 16..64 {
            let s0 = w[index - 15].rotate_right(7)
                ^ w[index - 15].rotate_right(18)
                ^ (w[index - 15] >> 3);
            let s1 = w[index - 2].rotate_right(17)
                ^ w[index - 2].rotate_right(19)
                ^ (w[index - 2] >> 10);
            w[index] = w[index - 16]
                .wrapping_add(s0)
                .wrapping_add(w[index - 7])
                .wrapping_add(s1);
        }

        let [mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h] = state;
        for index in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = h
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(SHA256_K[index])
                .wrapping_add(w[index]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        state[0] = state[0].wrapping_add(a);
        state[1] = state[1].wrapping_add(b);
        state[2] = state[2].wrapping_add(c);
        state[3] = state[3].wrapping_add(d);
        state[4] = state[4].wrapping_add(e);
        state[5] = state[5].wrapping_add(f);
        state[6] = state[6].wrapping_add(g);
        state[7] = state[7].wrapping_add(h);
    }

    let mut out = [0u8; 32];
    for (index, word) in state.iter().enumerate() {
        out[index * 4..index * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

/// Lowercase hex SHA-256 of `bytes`.
pub fn sha256_hex(bytes: &[u8]) -> String {
    let mut out = String::with_capacity(64);
    for byte in sha256_digest(bytes) {
        out.push_str(&format!("{byte:02x}"));
    }
    out
}

// ---------------------------------------------------------------------------
// minimal flat JSONL field reader (no serde)
// ---------------------------------------------------------------------------

/// A scalar read from a flat manifest record.
#[derive(Debug, Clone, PartialEq, Eq)]
enum FlatValue<'a> {
    Str(&'a str),
    Bool(bool),
    Other,
}

/// Reads one flat field from a single JSONL line.
///
/// The provider manifests are flat objects of string/number/bool values. A
/// single left-to-right scan that honours string escapes is therefore exact and
/// allocation-free. It never returns a value the caller did not ask for, so
/// titles, offline URIs and other prose can never reach the artifact.
fn flat_field<'a>(line: &'a str, key: &str) -> Option<FlatValue<'a>> {
    let bytes = line.as_bytes();
    let mut index = 0usize;
    while index < bytes.len() {
        if bytes[index] != b'"' {
            index += 1;
            continue;
        }
        let start = index + 1;
        let mut cursor = start;
        let mut escaped = false;
        while cursor < bytes.len() {
            let byte = bytes[cursor];
            if escaped {
                escaped = false;
                cursor += 1;
                continue;
            }
            if byte == b'\\' {
                escaped = true;
                cursor += 1;
                continue;
            }
            if byte == b'"' {
                break;
            }
            cursor += 1;
        }
        if cursor >= bytes.len() {
            return None;
        }
        let token = &line[start..cursor];
        let mut after = cursor + 1;
        while after < bytes.len() && (bytes[after] == b' ' || bytes[after] == b'\t') {
            after += 1;
        }
        if after >= bytes.len() || bytes[after] != b':' {
            index = cursor + 1;
            continue;
        }
        after += 1;
        while after < bytes.len() && (bytes[after] == b' ' || bytes[after] == b'\t') {
            after += 1;
        }
        if token == key {
            return read_scalar(line, after);
        }
        index = cursor + 1;
    }
    None
}

fn read_scalar(line: &str, start: usize) -> Option<FlatValue<'_>> {
    let bytes = line.as_bytes();
    match *bytes.get(start)? {
        b'"' => {
            let from = start + 1;
            let mut cursor = from;
            let mut escaped = false;
            while cursor < bytes.len() {
                let byte = bytes[cursor];
                if escaped {
                    escaped = false;
                    cursor += 1;
                    continue;
                }
                if byte == b'\\' {
                    escaped = true;
                    cursor += 1;
                    continue;
                }
                if byte == b'"' {
                    return Some(FlatValue::Str(&line[from..cursor]));
                }
                cursor += 1;
            }
            None
        }
        b't' if line[start..].starts_with("true") => Some(FlatValue::Bool(true)),
        b'f' if line[start..].starts_with("false") => Some(FlatValue::Bool(false)),
        _ => Some(FlatValue::Other),
    }
}

// ---------------------------------------------------------------------------
// inventory model
// ---------------------------------------------------------------------------

/// Which family surface a declaration was read from.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FamilyKind {
    Manifest,
    Directory,
}

impl FamilyKind {
    fn as_json(self) -> &'static str {
        match self {
            Self::Manifest => "manifest",
            Self::Directory => "directory",
        }
    }
}

/// How a manifest row is assigned to a decomposition part.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ManifestPartRule {
    /// `is_core_act` true/false becomes `core_acts` / `amending_acts`.
    CoreAndAmending,
    /// A string field value becomes the part key verbatim.
    Field(&'static str),
}

/// One declared family: its pinned input, its record total and the parts that
/// must sum to that total.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FamilyDeclaration {
    pub family_id: String,
    pub kind: FamilyKind,
    pub input_relative_path: String,
    pub input_bytes: u64,
    pub input_sha256: String,
    pub records_total: u64,
    pub decomposition: BTreeMap<String, u64>,
    pub decomposition_rule: String,
    pub subdirectories: Vec<String>,
}

/// The named chain's edition-directory declaration.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ChainDeclaration {
    pub chain_id: String,
    pub edition_directory_relative_path: String,
    pub input_bytes: u64,
    pub input_sha256: String,
    pub editions_total: u64,
    pub decomposition: BTreeMap<String, u64>,
    pub decomposition_rule: String,
}

/// The whole S03 family denominator: eight declared families plus the named
/// chain.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FamilyDenominator {
    pub families: Vec<FamilyDeclaration>,
    pub chain: ChainDeclaration,
}

/// Fixed family table. Order is the emitted order and is part of the artifact
/// bytes.
struct FamilySpec {
    family_id: &'static str,
    source: FamilySource,
}

enum FamilySource {
    Manifest {
        path_tail: &'static str,
        rule: ManifestPartRule,
        decomposition_rule: &'static str,
    },
    Directory {
        path_tail: &'static str,
        decomposition_rule: &'static str,
    },
}

const FAMILY_SPECS: [FamilySpec; 8] = [
    FamilySpec {
        family_id: "manifest_layer1_44fz_and_amending_laws",
        source: FamilySource::Manifest {
            path_tail: "manifest_layer1_44fz_and_amending_laws.jsonl",
            rule: ManifestPartRule::CoreAndAmending,
            decomposition_rule: "by is_core_act: core_acts (true) plus amending_acts (false)",
        },
    },
    FamilySpec {
        family_id: "manifest_layer2_subordinate_normative_acts",
        source: FamilySource::Manifest {
            path_tail: "manifest_layer2_subordinate_normative_acts.jsonl",
            rule: ManifestPartRule::Field("category"),
            decomposition_rule: "by category field value",
        },
    },
    FamilySpec {
        family_id: "manifest_layer3_court_practice_2025_2026",
        source: FamilySource::Manifest {
            path_tail: "manifest_layer3_court_practice_2025_2026.jsonl",
            rule: ManifestPartRule::Field("bank"),
            decomposition_rule: "by bank field value",
        },
    },
    FamilySpec {
        family_id: "manifest_layer3_fas_practice_2025_2026",
        source: FamilySource::Manifest {
            path_tail: "manifest_layer3_fas_practice_2025_2026.jsonl",
            rule: ManifestPartRule::Field("document_type"),
            decomposition_rule: "by document_type field value",
        },
    },
    FamilySpec {
        family_id: "exports_npa",
        source: FamilySource::Directory {
            path_tail: "exports/npa",
            decomposition_rule: "__root__ counts single-act files directly under exports/npa; every other key counts the files of that edition subdirectory",
        },
    },
    FamilySpec {
        family_id: "exports_xml",
        source: FamilySource::Directory {
            path_tail: "exports/xml",
            decomposition_rule: "by immediate subdirectory of exports/xml",
        },
    },
    FamilySpec {
        family_id: "exports_courts",
        source: FamilySource::Directory {
            path_tail: "exports/courts",
            decomposition_rule: "by immediate subdirectory of exports/courts",
        },
    },
    FamilySpec {
        family_id: "exports_fas",
        source: FamilySource::Directory {
            path_tail: "exports/fas",
            decomposition_rule: "by immediate subdirectory of exports/fas",
        },
    },
];

// ---------------------------------------------------------------------------
// filesystem inventory (read-only)
// ---------------------------------------------------------------------------

/// One file found under a walked directory.
struct WalkedFile {
    relative: String,
    size: u64,
}

struct DirectoryInventory {
    files_total: u64,
    bytes_total: u64,
    listing_sha256: String,
    decomposition: BTreeMap<String, u64>,
    subdirectories: Vec<String>,
}

fn relative_slash(base: &Path, path: &Path) -> String {
    path.strip_prefix(base)
        .unwrap_or(path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn walk_files(directory: &Path, base: &Path, out: &mut Vec<WalkedFile>) -> io::Result<()> {
    let mut entries = fs::read_dir(directory)?.collect::<Result<Vec<_>, _>>()?;
    entries.sort_by_key(|entry| entry.file_name());
    for entry in entries {
        let file_type = entry.file_type()?;
        if file_type.is_dir() {
            walk_files(&entry.path(), base, out)?;
        } else if file_type.is_file() {
            let size = entry.metadata()?.len();
            out.push(WalkedFile {
                relative: relative_slash(base, &entry.path()),
                size,
            });
        }
    }
    Ok(())
}

/// Walks `directory` read-only and derives a total, a byte count, a
/// deterministic listing digest and a decomposition by immediate child.
///
/// The listing stream is `"{relative_path}\0{size}\n"` per file, sorted by
/// relative path. It pins the whole subtree, so a rename, an addition or a size
/// change is visible as `input_hash_mismatch` on the next `--check`.
fn inventory_directory(directory: &Path) -> Result<DirectoryInventory, io::Error> {
    let mut files = Vec::new();
    walk_files(directory, directory, &mut files)?;
    files.sort_by(|left, right| left.relative.cmp(&right.relative));

    let mut bytes_total = 0u64;
    let mut listing = String::new();
    let mut decomposition: BTreeMap<String, u64> = BTreeMap::new();
    let mut subdirectories = Vec::new();
    for file in &files {
        bytes_total = bytes_total.wrapping_add(file.size);
        listing.push_str(&file.relative);
        listing.push('\0');
        listing.push_str(&file.size.to_string());
        listing.push('\n');
        let key = match file.relative.split_once('/') {
            Some((head, _)) => head.to_owned(),
            None => ROOT_KEY.to_owned(),
        };
        *decomposition.entry(key).or_insert(0) += 1;
    }
    subdirectories.extend(
        decomposition
            .keys()
            .filter(|key| key.as_str() != ROOT_KEY)
            .cloned(),
    );
    subdirectories.sort();

    Ok(DirectoryInventory {
        files_total: files.len() as u64,
        bytes_total,
        listing_sha256: format!("sha256:{}", sha256_hex(listing.as_bytes())),
        decomposition,
        subdirectories,
    })
}

fn read_manifest(
    path: &Path,
    rule: ManifestPartRule,
) -> Result<(u64, BTreeMap<String, u64>), AmendmentProvenanceError> {
    let display = path.display().to_string();
    let text = fs::read_to_string(path).map_err(|_| input_absent(display.clone()))?;
    let mut records_total = 0u64;
    let mut decomposition: BTreeMap<String, u64> = BTreeMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        records_total += 1;
        let part = match rule {
            ManifestPartRule::CoreAndAmending => match flat_field(line, "is_core_act") {
                Some(FlatValue::Bool(true)) => "core_acts".to_owned(),
                Some(FlatValue::Bool(false)) => "amending_acts".to_owned(),
                _ => {
                    return Err(family_unsupported(
                        display.clone(),
                        format!("record {records_total} carries no boolean is_core_act"),
                    ))
                }
            },
            ManifestPartRule::Field(key) => match flat_field(line, key) {
                Some(FlatValue::Str(value)) => value.to_owned(),
                _ => {
                    return Err(family_unsupported(
                        display.clone(),
                        format!("record {records_total} carries no string {key}"),
                    ))
                }
            },
        };
        *decomposition.entry(part).or_insert(0) += 1;
    }
    Ok((records_total, decomposition))
}

// ---------------------------------------------------------------------------
// collection
// ---------------------------------------------------------------------------

/// Resolves the provider export root for an operator-supplied export directory.
///
/// Mirrors `tests/classifier_recall_test.rs`: the operator value names the outer
/// directory and the export payload lives one level below it in
/// `consru_export/`.
pub fn resolve_export_root(repo_root: &Path, export_dir: &str) -> PathBuf {
    repo_root.join(export_dir).join(EXPORT_ROOT_TAIL)
}

/// Repository-relative path of the provider export root, as recorded in the
/// artifact.
pub fn export_root_relative_path(export_dir: &str) -> String {
    let trimmed = export_dir.trim_end_matches('/');
    if trimmed.is_empty() {
        EXPORT_ROOT_TAIL.to_owned()
    } else {
        format!("{trimmed}/{EXPORT_ROOT_TAIL}")
    }
}

/// The export directory for this run: CLI value, else `CONSULTANT_EXPORT_DIR`
/// with empty-as-unset semantics, else the default.
pub fn effective_export_dir(cli_value: Option<&str>) -> String {
    if let Some(value) = cli_value {
        if !value.trim().is_empty() {
            return value.to_owned();
        }
    }
    match std::env::var(EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => EXPORT_DIR_DEFAULT.to_owned(),
    }
}

/// Re-derives the whole family denominator from the live provider export.
pub fn collect_family_denominator(
    repo_root: &Path,
    export_dir: &str,
) -> Result<FamilyDenominator, AmendmentProvenanceError> {
    let export_root_relative = export_root_relative_path(export_dir);
    let export_root = resolve_export_root(repo_root, export_dir);

    let mut families = Vec::with_capacity(FAMILY_SPECS.len());
    for spec in &FAMILY_SPECS {
        let (kind, tail, decomposition_rule) = match &spec.source {
            FamilySource::Manifest {
                path_tail,
                decomposition_rule,
                ..
            } => (FamilyKind::Manifest, *path_tail, *decomposition_rule),
            FamilySource::Directory {
                path_tail,
                decomposition_rule,
            } => (FamilyKind::Directory, *path_tail, *decomposition_rule),
        };
        let relative_path = format!("{export_root_relative}/{tail}");
        let absolute = export_root.join(tail);

        let (records_total, decomposition, input_bytes, input_sha256, subdirectories) = match &spec
            .source
        {
            FamilySource::Manifest { rule, .. } => {
                let text_bytes =
                    fs::read(&absolute).map_err(|_| input_absent(relative_path.clone()))?;
                let (records_total, decomposition) = read_manifest(&absolute, *rule)?;
                (
                    records_total,
                    decomposition,
                    text_bytes.len() as u64,
                    format!("sha256:{}", sha256_hex(&text_bytes)),
                    Vec::new(),
                )
            }
            FamilySource::Directory { .. } => {
                let inventory = inventory_directory(&absolute).map_err(|error| {
                    if error.kind() == io::ErrorKind::NotFound {
                        input_absent(relative_path.clone())
                    } else {
                        family_unsupported(spec.family_id, format!("directory unreadable: {error}"))
                    }
                })?;
                (
                    inventory.files_total,
                    inventory.decomposition,
                    inventory.bytes_total,
                    inventory.listing_sha256,
                    inventory.subdirectories,
                )
            }
        };

        families.push(FamilyDeclaration {
            family_id: spec.family_id.to_owned(),
            kind,
            input_relative_path: relative_path,
            input_bytes,
            input_sha256,
            records_total,
            decomposition,
            decomposition_rule: decomposition_rule.to_owned(),
            subdirectories,
        });
    }

    let chain_relative = format!("{export_root_relative}/{EDITION_DIR_TAIL}");
    let chain_absolute = export_root.join(EDITION_DIR_TAIL);
    let inventory = inventory_directory(&chain_absolute).map_err(|_| {
        AmendmentProvenanceError::EditionDirUnreadable {
            path: chain_relative.clone(),
        }
    })?;

    let mut chain_decomposition: BTreeMap<String, u64> = BTreeMap::new();
    let mut edition_matching = 0u64;
    let mut edition_unparsed = 0u64;
    // Re-walk only the immediate children: the chain decomposition is defined
    // over admitted edition file names, not over subdirectories.
    for entry in fs::read_dir(&chain_absolute)
        .map_err(|_| AmendmentProvenanceError::EditionDirUnreadable {
            path: chain_relative.clone(),
        })?
        .collect::<Result<Vec<_>, _>>()
        .map_err(|_| AmendmentProvenanceError::EditionDirUnreadable {
            path: chain_relative.clone(),
        })?
    {
        let file_type =
            entry
                .file_type()
                .map_err(|_| AmendmentProvenanceError::EditionDirUnreadable {
                    path: chain_relative.clone(),
                })?;
        if !file_type.is_file() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().to_string();
        if name.starts_with(EDITION_FILE_PREFIX) && name.ends_with(".xml") {
            edition_matching += 1;
        } else {
            edition_unparsed += 1;
        }
    }
    chain_decomposition.insert("edition_matching".to_owned(), edition_matching);
    chain_decomposition.insert("edition_unparsed".to_owned(), edition_unparsed);

    let chain = ChainDeclaration {
        chain_id: CHAIN_ID.to_owned(),
        edition_directory_relative_path: chain_relative,
        input_bytes: inventory.bytes_total,
        input_sha256: inventory.listing_sha256,
        editions_total: inventory.files_total,
        decomposition: chain_decomposition,
        decomposition_rule: "edition_matching counts edition-*.xml files, edition_unparsed counts every other file in the edition directory".to_owned(),
    };

    Ok(FamilyDenominator { families, chain })
}

// ---------------------------------------------------------------------------
// validation
// ---------------------------------------------------------------------------

fn is_allowed_key_token(key: &str) -> bool {
    !key.is_empty()
        && key.len() <= MAX_KEY_LEN
        && key
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'_' | b'-' | b'.' | b':'))
}

fn check_decomposition_keys(
    family_id: &str,
    decomposition: &BTreeMap<String, u64>,
) -> Result<(), AmendmentProvenanceError> {
    for key in decomposition.keys() {
        if !key.is_ascii() {
            return Err(AmendmentProvenanceError::NonAsciiEvidence {
                detail: format!("family {family_id} carries a non-ascii decomposition key"),
            });
        }
        if !is_allowed_key_token(key) {
            return Err(AmendmentProvenanceError::RawTextLeak {
                detail: format!(
                    "family {family_id} carries a decomposition key outside the count-only token rule"
                ),
            });
        }
    }
    Ok(())
}

fn check_repo_relative(path: &str) -> Result<(), AmendmentProvenanceError> {
    let candidate = Path::new(path);
    if path.is_empty() || candidate.is_absolute() {
        return Err(AmendmentProvenanceError::PathDrift {
            path: path.to_owned(),
        });
    }
    for component in candidate.components() {
        match component {
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                return Err(AmendmentProvenanceError::PathDrift {
                    path: path.to_owned(),
                })
            }
            _ => {}
        }
    }
    Ok(())
}

/// Fails closed on a zero total, a decomposition that does not sum to its
/// declared total, a non-ASCII or prose-shaped decomposition key, and an input
/// anchor that is not repository-relative (D552).
pub fn validate_family_denominator(
    denominator: &FamilyDenominator,
) -> Result<(), AmendmentProvenanceError> {
    if denominator.families.is_empty() {
        return Err(family_unsupported("<artifact>", "no family is declared"));
    }
    for family in &denominator.families {
        check_repo_relative(&family.input_relative_path)?;
        if family.records_total == 0 {
            return Err(AmendmentProvenanceError::ZeroDenominator {
                family_id: family.family_id.clone(),
            });
        }
        let sum: u64 = family.decomposition.values().sum();
        if family.decomposition.is_empty() || sum != family.records_total {
            return Err(family_unsupported(
                &family.family_id,
                format!(
                    "decomposition sums to {sum} but records_total is {}",
                    family.records_total
                ),
            ));
        }
        check_decomposition_keys(&family.family_id, &family.decomposition)?;
    }

    check_repo_relative(&denominator.chain.edition_directory_relative_path)?;
    if denominator.chain.editions_total == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: denominator.chain.chain_id.clone(),
        });
    }
    let chain_sum: u64 = denominator.chain.decomposition.values().sum();
    if denominator.chain.decomposition.is_empty() || chain_sum != denominator.chain.editions_total {
        return Err(family_unsupported(
            &denominator.chain.chain_id,
            format!(
                "decomposition sums to {chain_sum} but editions_total is {}",
                denominator.chain.editions_total
            ),
        ));
    }
    check_decomposition_keys(
        &denominator.chain.chain_id,
        &denominator.chain.decomposition,
    )?;
    Ok(())
}

/// Rejects a rendered artifact that is empty, non-ASCII or that carries a
/// corpus prose marker.
pub fn ensure_ascii_and_clean(rendered: &str) -> Result<(), AmendmentProvenanceError> {
    if rendered.is_empty() {
        return Err(AmendmentProvenanceError::NonAsciiEvidence {
            detail: "artifact is empty".to_owned(),
        });
    }
    if !rendered.is_ascii() {
        let offset = rendered.bytes().position(|byte| byte >= 0x80).unwrap_or(0);
        return Err(AmendmentProvenanceError::NonAsciiEvidence {
            detail: format!("artifact carries a non-ascii byte at offset {offset}"),
        });
    }
    for marker in CORPUS_TEXT_MARKERS {
        if rendered.contains(marker) {
            return Err(AmendmentProvenanceError::RawTextLeak {
                detail: format!("artifact carries the corpus marker {marker}"),
            });
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// canonical rendering (D424: compact, fixed key order, no timestamps)
// ---------------------------------------------------------------------------

fn json_escape(value: &str) -> String {
    let mut out = String::with_capacity(value.len() + 2);
    for character in value.chars() {
        match character {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            other if (other as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", other as u32)),
            other => out.push(other),
        }
    }
    out
}

/// Hand-rolled compact JSON object writer with a fixed field order.
struct ObjectWriter {
    buffer: String,
    empty: bool,
}

impl ObjectWriter {
    fn new() -> Self {
        Self {
            buffer: String::from("{"),
            empty: true,
        }
    }

    fn key(&mut self, key: &str) {
        if !self.empty {
            self.buffer.push(',');
        }
        self.empty = false;
        self.buffer.push('"');
        self.buffer.push_str(&json_escape(key));
        self.buffer.push_str("\":");
    }

    fn string(&mut self, key: &str, value: &str) {
        self.key(key);
        self.buffer.push('"');
        self.buffer.push_str(&json_escape(value));
        self.buffer.push('"');
    }

    fn number(&mut self, key: &str, value: u64) {
        self.key(key);
        self.buffer.push_str(&value.to_string());
    }

    fn boolean(&mut self, key: &str, value: bool) {
        self.key(key);
        self.buffer.push_str(if value { "true" } else { "false" });
    }

    fn counts(&mut self, key: &str, counts: &BTreeMap<String, u64>) {
        self.key(key);
        self.buffer.push('{');
        let mut first = true;
        for (part, count) in counts {
            if !first {
                self.buffer.push(',');
            }
            first = false;
            self.buffer.push('"');
            self.buffer.push_str(&json_escape(part));
            self.buffer.push_str("\":");
            self.buffer.push_str(&count.to_string());
        }
        self.buffer.push('}');
    }

    fn strings(&mut self, key: &str, values: &[String]) {
        self.key(key);
        self.buffer.push('[');
        for (index, value) in values.iter().enumerate() {
            if index > 0 {
                self.buffer.push(',');
            }
            self.buffer.push('"');
            self.buffer.push_str(&json_escape(value));
            self.buffer.push('"');
        }
        self.buffer.push(']');
    }

    fn fixed_strings(&mut self, key: &str, values: &[&str]) {
        self.key(key);
        self.buffer.push('[');
        for (index, value) in values.iter().enumerate() {
            if index > 0 {
                self.buffer.push(',');
            }
            self.buffer.push('"');
            self.buffer.push_str(&json_escape(value));
            self.buffer.push('"');
        }
        self.buffer.push(']');
    }

    fn finish(mut self) -> String {
        self.buffer.push('}');
        self.buffer
    }
}

/// Denominator definition prose. Counts only; no corpus content.
const COUNT_BASIS: &str = "The denominator is re-derived live on every run from one named corpus revision: the untracked, licensed provider export under consru_export/consru_export. Every family declares a repository-relative input path, its byte count, its sha256 pin, a record total and a decomposition whose parts must sum to that total. Nothing here is typed by hand and no zero total is a measurement.";

/// Claim bounds carried by every S03 family-denominator artifact.
const NON_CLAIMS: [&str; 6] = [
    "This is a scoped family denominator for the named cc:44-fz chain and its four provider manifest and export families; it is not every-edition coverage and not every amending act of the corpus.",
    "No corpus text is copied into this artifact: no XML bytes, no article text, no document titles, no offline URIs and no raw relation tooltips; only counts, repository-relative paths, byte counts, sha256 pins and validated categorical keys.",
    "The frozen M201 R070 proof gate is not widened, reopened or restated here, and the three frozen M201 pins stay byte-identical.",
    "A zero denominator is not a measurement and fails closed as zero_denominator; no declared total may be presented as a measurement when its decomposition does not sum to it.",
    "R070 stays active (D416); no promotion gate is promoted, satisfied or moved off unsatisfied by this artifact and no requirement record is mutated.",
    "No M202 inventory count may stand as a quantifier in this artifact (D539): every declared total is a live-derived count bound to a named input path, its byte count and its sha256 pin.",
];

/// Renders the canonical compact artifact. Deterministic and ASCII by
/// construction: no timestamps, no counters, no variable-width formatting.
pub fn render_family_denominator(denominator: &FamilyDenominator) -> String {
    let mut writer = ObjectWriter::new();
    writer.string("schema", SCHEMA);
    writer.number("schema_version", 1);
    writer.string("kind", KIND);
    writer.string("milestone", MILESTONE);
    writer.string("slice", SLICE);
    writer.string("task", TASK);
    writer.string("lifecycle", LIFECYCLE);
    writer.boolean("authoritative", false);
    writer.string("requirement_id", REQUIREMENT_ID);
    writer.string("disposition", DISPOSITION);
    writer.string("disposition_decision", DISPOSITION_DECISION);
    writer.boolean("count_only", true);
    writer.boolean("ascii_only", true);
    writer.string("count_basis", COUNT_BASIS);

    writer.key("families");
    writer.buffer.push('[');
    for (index, family) in denominator.families.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.string("family_id", &family.family_id);
        entry.string("kind", family.kind.as_json());
        entry.string("input_relative_path", &family.input_relative_path);
        entry.number("input_bytes", family.input_bytes);
        entry.string("input_sha256", &family.input_sha256);
        entry.number("records_total", family.records_total);
        entry.counts("decomposition", &family.decomposition);
        entry.string("decomposition_rule", &family.decomposition_rule);
        entry.strings("subdirectories", &family.subdirectories);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.key("chain");
    {
        let mut entry = ObjectWriter::new();
        entry.string("chain_id", &denominator.chain.chain_id);
        entry.string(
            "edition_directory_relative_path",
            &denominator.chain.edition_directory_relative_path,
        );
        entry.number("input_bytes", denominator.chain.input_bytes);
        entry.string("input_sha256", &denominator.chain.input_sha256);
        entry.number("editions_total", denominator.chain.editions_total);
        entry.counts("decomposition", &denominator.chain.decomposition);
        entry.string("decomposition_rule", &denominator.chain.decomposition_rule);
        writer.buffer.push_str(&entry.finish());
    }

    writer.fixed_strings("fail_closed_codes", &FAMILY_DENOMINATOR_CODES);
    writer.fixed_strings("non_claims", &NON_CLAIMS);
    writer.finish()
}

/// Count-only stderr heartbeat.
pub fn family_denominator_heartbeat(denominator: &FamilyDenominator) -> String {
    let manifests = denominator
        .families
        .iter()
        .filter(|family| family.kind == FamilyKind::Manifest)
        .count();
    format!(
        "families={} manifests={} chains=1 editions={} drift=0",
        denominator.families.len(),
        manifests,
        denominator.chain.editions_total
    )
}

// ---------------------------------------------------------------------------
// CLI surface
// ---------------------------------------------------------------------------

/// Evidence mode. Only `families` exists in T01; later S03 tasks add modes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProvenanceMode {
    Families,
}

impl ProvenanceMode {
    fn parse(value: &str) -> Result<Self, AmendmentProvenanceError> {
        match value {
            "families" => Ok(Self::Families),
            other => Err(usage(format!("unsupported --mode {other}"))),
        }
    }
}

/// Which artifact action the CLI should take.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProvenanceAction {
    Write,
    Check,
}

/// Parsed CLI invocation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProvenanceCli {
    pub mode: ProvenanceMode,
    pub export_dir: String,
    pub out: PathBuf,
    pub action: ProvenanceAction,
}

/// Outcome of a successful run.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProvenanceOutcome {
    pub heartbeat: String,
}

fn next_value(
    args: &mut impl Iterator<Item = String>,
    flag: &str,
) -> Result<String, AmendmentProvenanceError> {
    args.next()
        .ok_or_else(|| usage(format!("{flag} requires a value")))
}

/// Parses `--mode <mode> [--export-dir <dir>] --out <path> --write|--check`.
pub fn parse_provenance_args(args: Vec<String>) -> Result<ProvenanceCli, AmendmentProvenanceError> {
    let mut mode: Option<String> = None;
    let mut export_dir: Option<String> = None;
    let mut out: Option<String> = None;
    let mut write = false;
    let mut check = false;

    let mut iter = args.into_iter();
    while let Some(argument) = iter.next() {
        match argument.as_str() {
            "--mode" => mode = Some(next_value(&mut iter, "--mode")?),
            "--export-dir" => export_dir = Some(next_value(&mut iter, "--export-dir")?),
            "--out" => out = Some(next_value(&mut iter, "--out")?),
            "--write" => write = true,
            "--check" => check = true,
            other => return Err(usage(format!("unknown argument {other}"))),
        }
    }

    let mode = mode.ok_or_else(|| usage("--mode is required"))?;
    let mode = ProvenanceMode::parse(&mode)?;
    if write == check {
        return Err(usage("exactly one of --write or --check is required"));
    }
    let out = out.ok_or_else(|| usage("--out is required"))?;
    let out = PathBuf::from(out);
    if out.as_os_str().is_empty() {
        return Err(usage("--out must not be empty"));
    }

    Ok(ProvenanceCli {
        mode,
        export_dir: effective_export_dir(export_dir.as_deref()),
        out,
        action: if write {
            ProvenanceAction::Write
        } else {
            ProvenanceAction::Check
        },
    })
}

/// Refuses an `--out` that is absolute, traversing, symlinked or not inside the
/// canonicalised repository root.
pub fn ensure_out_containment(
    repo_root: &Path,
    out: &Path,
) -> Result<(), AmendmentProvenanceError> {
    let display = out.display().to_string();
    if display.is_empty() || out.is_absolute() {
        return Err(AmendmentProvenanceError::PathDrift { path: display });
    }
    for component in out.components() {
        match component {
            Component::ParentDir | Component::RootDir | Component::Prefix(_) => {
                return Err(AmendmentProvenanceError::PathDrift { path: display })
            }
            _ => {}
        }
    }

    let absolute = repo_root.join(out);
    if let Ok(metadata) = fs::symlink_metadata(&absolute) {
        if metadata.file_type().is_symlink() {
            return Err(AmendmentProvenanceError::PathDrift { path: display });
        }
    }

    let real_root =
        fs::canonicalize(repo_root).map_err(|_| AmendmentProvenanceError::OutUnwritable {
            path: display.clone(),
        })?;
    let parent = absolute.parent().unwrap_or(Path::new(""));
    let real_parent =
        fs::canonicalize(parent).map_err(|_| AmendmentProvenanceError::OutUnwritable {
            path: display.clone(),
        })?;
    if !real_parent.starts_with(&real_root) {
        return Err(AmendmentProvenanceError::PathDrift { path: display });
    }
    Ok(())
}

fn diagnose_check_drift(
    tracked: &[u8],
    denominator: &FamilyDenominator,
) -> AmendmentProvenanceError {
    if tracked.iter().any(|byte| *byte >= 0x80) {
        return AmendmentProvenanceError::NonAsciiEvidence {
            detail: "tracked artifact is not ascii".to_owned(),
        };
    }
    let tracked_text = String::from_utf8_lossy(tracked);
    let segments: Vec<&str> = tracked_text.split("\"family_id\"").collect();
    for family in &denominator.families {
        let marker = format!(":\"{}\"", family.family_id);
        let Some(segment) = segments.iter().find(|segment| segment.starts_with(&marker)) else {
            return family_unsupported(
                &family.family_id,
                "family is absent from the tracked artifact",
            );
        };
        if !segment.contains(&format!("\"input_sha256\":\"{}\"", family.input_sha256)) {
            return AmendmentProvenanceError::InputHashMismatch {
                family_id: family.family_id.clone(),
                path: family.input_relative_path.clone(),
                detail: "tracked pin differs from the live input pin".to_owned(),
            };
        }
        if !segment.contains(&format!("\"records_total\":{}", family.records_total)) {
            return family_unsupported(
                &family.family_id,
                "tracked record total differs from the live record total",
            );
        }
    }
    family_unsupported(
        "<artifact>",
        "artifact bytes differ from the live render while every declared pin matches",
    )
}

/// Renders the artifact for `mode`, then either writes it or byte-compares it
/// against the tracked file without writing (D424).
pub fn run_provenance(
    cli: &ProvenanceCli,
    repo_root: &Path,
) -> Result<ProvenanceOutcome, AmendmentProvenanceError> {
    match cli.mode {
        ProvenanceMode::Families => {}
    }
    ensure_out_containment(repo_root, &cli.out)?;

    let denominator = collect_family_denominator(repo_root, &cli.export_dir)?;
    validate_family_denominator(&denominator)?;
    let rendered = render_family_denominator(&denominator);
    ensure_ascii_and_clean(&rendered)?;
    let heartbeat = family_denominator_heartbeat(&denominator);

    let absolute_out = repo_root.join(&cli.out);
    let display = cli.out.display().to_string();
    match cli.action {
        ProvenanceAction::Write => {
            fs::write(&absolute_out, rendered.as_bytes())
                .map_err(|_| AmendmentProvenanceError::OutUnwritable { path: display })?;
            Ok(ProvenanceOutcome { heartbeat })
        }
        ProvenanceAction::Check => {
            let tracked =
                fs::read(&absolute_out).map_err(|_| input_absent(cli.out.display().to_string()))?;
            if tracked == rendered.as_bytes() {
                Ok(ProvenanceOutcome { heartbeat })
            } else {
                Err(diagnose_check_drift(&tracked, &denominator))
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU32, Ordering};

    const NIST_EMPTY: &str = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
    const NIST_ABC: &str = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
    const NIST_448: &str = "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1";

    #[test]
    fn sha256_matches_nist_vectors() {
        assert_eq!(sha256_hex(b""), NIST_EMPTY);
        assert_eq!(sha256_hex(b"abc"), NIST_ABC);
        assert_eq!(
            sha256_hex(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
            NIST_448
        );
    }

    #[test]
    fn flat_field_reads_only_the_requested_key() {
        let line = r#"{"bank": "LAW", "title": "a \"quoted\": title", "category": "amending_act", "is_core_act": false}"#;
        assert_eq!(flat_field(line, "bank"), Some(FlatValue::Str("LAW")));
        assert_eq!(
            flat_field(line, "category"),
            Some(FlatValue::Str("amending_act"))
        );
        assert_eq!(
            flat_field(line, "is_core_act"),
            Some(FlatValue::Bool(false))
        );
        assert_eq!(
            flat_field(line, "title"),
            Some(FlatValue::Str(r#"a \"quoted\": title"#))
        );
        assert_eq!(flat_field(line, "absent"), None);
    }

    fn specification_family() -> FamilyDeclaration {
        let mut decomposition = BTreeMap::new();
        decomposition.insert("core_acts".to_owned(), 1);
        decomposition.insert("amending_acts".to_owned(), 121);
        FamilyDeclaration {
            family_id: "manifest_layer1_44fz_and_amending_laws".to_owned(),
            kind: FamilyKind::Manifest,
            input_relative_path: "consru_export/consru_export/manifest.jsonl".to_owned(),
            input_bytes: 12,
            input_sha256: format!("sha256:{}", NIST_ABC),
            records_total: 122,
            decomposition,
            decomposition_rule: "by is_core_act".to_owned(),
            subdirectories: Vec::new(),
        }
    }

    fn specification_chain() -> ChainDeclaration {
        let mut decomposition = BTreeMap::new();
        decomposition.insert("edition_matching".to_owned(), 118);
        decomposition.insert("edition_unparsed".to_owned(), 0);
        ChainDeclaration {
            chain_id: CHAIN_ID.to_owned(),
            edition_directory_relative_path: "consru_export/consru_export/exports/npa/law"
                .to_owned(),
            input_bytes: 10,
            input_sha256: format!("sha256:{}", NIST_EMPTY),
            editions_total: 118,
            decomposition,
            decomposition_rule: "edition files".to_owned(),
        }
    }

    fn specification() -> FamilyDenominator {
        FamilyDenominator {
            families: vec![specification_family()],
            chain: specification_chain(),
        }
    }

    #[test]
    fn render_is_compact_ascii_and_deterministic() {
        let rendered = render_family_denominator(&specification());
        assert_eq!(rendered, render_family_denominator(&specification()));
        assert!(rendered.is_ascii());
        assert!(
            !rendered.ends_with('\n'),
            "canonical bytes carry no trailing newline"
        );
        assert!(!rendered.contains("\n"), "canonical bytes are single-line");
        assert!(ensure_ascii_and_clean(&rendered).is_ok());
        assert!(rendered.starts_with("{\"schema\":\"law-nexus/r070-family-denominator/v1\""));
        assert!(rendered.contains("\"fail_closed_codes\":[\"input_absent\""));
    }

    #[test]
    fn decomposition_sum_mismatch_fails_closed() {
        let mut denominator = specification();
        denominator.families[0].records_total = 999;
        assert_eq!(
            validate_family_denominator(&denominator),
            Err(family_unsupported(
                "manifest_layer1_44fz_and_amending_laws",
                "decomposition sums to 122 but records_total is 999"
            ))
        );
    }

    #[test]
    fn zero_totals_fail_closed() {
        let mut denominator = specification();
        denominator.families[0].records_total = 0;
        denominator.families[0].decomposition.clear();
        assert_eq!(
            validate_family_denominator(&denominator),
            Err(AmendmentProvenanceError::ZeroDenominator {
                family_id: "manifest_layer1_44fz_and_amending_laws".to_owned()
            })
        );

        let mut chain_zero = specification();
        chain_zero.chain.editions_total = 0;
        chain_zero.chain.decomposition.clear();
        assert_eq!(
            validate_family_denominator(&chain_zero),
            Err(AmendmentProvenanceError::ZeroDenominator {
                family_id: CHAIN_ID.to_owned()
            })
        );
    }

    #[test]
    fn non_ascii_and_prose_keys_fail_closed() {
        let mut non_ascii = specification();
        let core_count = non_ascii.families[0]
            .decomposition
            .remove("core_acts")
            .expect("core_acts part");
        non_ascii.families[0]
            .decomposition
            .insert("\u{0410}\u{0420}\u{0411}".to_owned(), core_count);
        assert!(matches!(
            validate_family_denominator(&non_ascii),
            Err(AmendmentProvenanceError::NonAsciiEvidence { .. })
        ));

        let mut prose = specification();
        let amending_count = prose.families[0]
            .decomposition
            .remove("amending_acts")
            .expect("amending_acts part");
        prose.families[0].decomposition.insert(
            "consultantplus://offline/ref=DEADBEEF".to_owned(),
            amending_count,
        );
        assert!(matches!(
            validate_family_denominator(&prose),
            Err(AmendmentProvenanceError::RawTextLeak { .. })
        ));

        assert!(ensure_ascii_and_clean("{\"a\":1}\u{0410}").is_err());
        assert!(ensure_ascii_and_clean("{\"a\":\"consultantplus://x\"}").is_err());
        assert!(ensure_ascii_and_clean("").is_err());
    }

    #[test]
    fn absolute_and_traversing_paths_fail_closed() {
        let mut absolute = specification();
        absolute.families[0].input_relative_path = "/tmp/manifest.jsonl".to_owned();
        assert!(matches!(
            validate_family_denominator(&absolute),
            Err(AmendmentProvenanceError::PathDrift { .. })
        ));

        let mut traversing = specification();
        traversing.families[0].input_relative_path = "../../etc/passwd".to_owned();
        assert!(matches!(
            validate_family_denominator(&traversing),
            Err(AmendmentProvenanceError::PathDrift { .. })
        ));

        let root = Path::new("/root/law-nexus");
        assert!(matches!(
            ensure_out_containment(root, Path::new("/etc/passwd")),
            Err(AmendmentProvenanceError::PathDrift { .. })
        ));
        assert!(matches!(
            ensure_out_containment(root, Path::new("../outside.json")),
            Err(AmendmentProvenanceError::PathDrift { .. })
        ));
    }

    #[test]
    fn exit_codes_and_codes_are_pinned() {
        assert_eq!(usage("x").exit_code(), 2);
        assert_eq!(input_absent("x").exit_code(), 3);
        assert_eq!(
            AmendmentProvenanceError::EditionDirUnreadable {
                path: "x".to_owned()
            }
            .exit_code(),
            3
        );
        assert_eq!(
            AmendmentProvenanceError::OutUnwritable {
                path: "x".to_owned()
            }
            .exit_code(),
            4
        );
        assert_eq!(
            AmendmentProvenanceError::InputHashMismatch {
                family_id: "f".to_owned(),
                path: "p".to_owned(),
                detail: "d".to_owned()
            }
            .exit_code(),
            6
        );
        assert_eq!(
            AmendmentProvenanceError::RawTextLeak {
                detail: "d".to_owned()
            }
            .exit_code(),
            6
        );

        let emitted: Vec<&str> = [
            input_absent("x"),
            AmendmentProvenanceError::InputHashMismatch {
                family_id: "f".to_owned(),
                path: "p".to_owned(),
                detail: "d".to_owned(),
            },
            family_unsupported("f", "d"),
            AmendmentProvenanceError::ZeroDenominator {
                family_id: "f".to_owned(),
            },
            AmendmentProvenanceError::NonAsciiEvidence {
                detail: "d".to_owned(),
            },
            AmendmentProvenanceError::RawTextLeak {
                detail: "d".to_owned(),
            },
            AmendmentProvenanceError::EditionDirUnreadable {
                path: "p".to_owned(),
            },
        ]
        .iter()
        .filter_map(AmendmentProvenanceError::code)
        .collect();
        assert_eq!(emitted, FAMILY_DENOMINATOR_CODES.to_vec());
    }

    #[test]
    fn argument_parsing_is_closed_and_requires_one_action() {
        let parsed = parse_provenance_args(vec![
            "--mode".to_owned(),
            "families".to_owned(),
            "--out".to_owned(),
            "prd/x.json".to_owned(),
            "--write".to_owned(),
        ])
        .expect("valid invocation");
        assert_eq!(parsed.action, ProvenanceAction::Write);
        assert_eq!(parsed.export_dir, effective_export_dir(None));

        assert!(matches!(
            parse_provenance_args(vec![
                "--mode".to_owned(),
                "ledger".to_owned(),
                "--out".to_owned(),
                "x".to_owned(),
                "--write".to_owned()
            ]),
            Err(AmendmentProvenanceError::Usage { .. })
        ));
        assert!(matches!(
            parse_provenance_args(vec![
                "--mode".to_owned(),
                "families".to_owned(),
                "--out".to_owned(),
                "x".to_owned()
            ]),
            Err(AmendmentProvenanceError::Usage { .. })
        ));
        assert!(matches!(
            parse_provenance_args(vec![
                "--mode".to_owned(),
                "families".to_owned(),
                "--out".to_owned(),
                "x".to_owned(),
                "--write".to_owned(),
                "--check".to_owned()
            ]),
            Err(AmendmentProvenanceError::Usage { .. })
        ));
        assert!(matches!(
            parse_provenance_args(vec![
                "--mode".to_owned(),
                "families".to_owned(),
                "--write".to_owned()
            ]),
            Err(AmendmentProvenanceError::Usage { .. })
        ));
    }

    #[test]
    fn manifest_and_directory_reads_are_live() {
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let unique = COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir().join(format!(
            "ln-consultant-parser-m209-{}-{unique}",
            std::process::id()
        ));
        let manifest = dir.join("manifest.jsonl");
        let export = dir.join("exports").join("npa");
        fs::create_dir_all(&export).expect("create fixture tree");
        fs::write(
            &manifest,
            concat!(
                r#"{"bank":"LAW","is_core_act":true,"title":"core"}"#,
                "\n",
                r#"{"bank":"LAW","is_core_act":false,"title":"a \"quoted\": one"}"#,
                "\n",
                r#"{"bank":"LAW","is_core_act":false,"title":"amending"}"#,
                "\n"
            ),
        )
        .expect("write manifest fixture");
        fs::write(export.join("single.xml"), b"<x/>").expect("write single-act fixture");
        fs::create_dir_all(export.join("chain")).expect("create chain fixture");
        fs::write(export.join("chain").join("edition-0001_a.xml"), b"<x/>")
            .expect("write edition fixture");
        fs::write(export.join("chain").join("notes.txt"), b"n").expect("write stray fixture");

        let (total, decomposition) =
            read_manifest(&manifest, ManifestPartRule::CoreAndAmending).expect("manifest read");
        assert_eq!(total, 3);
        assert_eq!(decomposition.get("core_acts"), Some(&1));
        assert_eq!(decomposition.get("amending_acts"), Some(&2));

        let inventory = inventory_directory(&export).expect("directory read");
        assert_eq!(inventory.files_total, 3);
        assert_eq!(inventory.decomposition.get(ROOT_KEY), Some(&1));
        assert_eq!(inventory.decomposition.get("chain"), Some(&2));
        assert_eq!(inventory.subdirectories, vec!["chain".to_owned()]);
        assert!(inventory.listing_sha256.starts_with("sha256:"));
        assert_eq!(
            inventory.listing_sha256,
            inventory_directory(&export)
                .expect("repeat read")
                .listing_sha256
        );

        fs::remove_dir_all(&dir).expect("clean fixture tree");
    }

    #[test]
    fn malformed_manifest_records_fail_closed() {
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let unique = COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir().join(format!(
            "ln-consultant-parser-m209-bad-{}-{unique}",
            std::process::id()
        ));
        fs::create_dir_all(&dir).expect("create fixture dir");
        let missing_flag = dir.join("no-flag.jsonl");
        fs::write(&missing_flag, r#"{"bank":"LAW","title":"x"}"#).expect("write fixture");
        let missing_field = dir.join("no-category.jsonl");
        fs::write(&missing_field, r#"{"bank":"LAW","category":7}"#).expect("write fixture");

        assert!(matches!(
            read_manifest(&missing_flag, ManifestPartRule::CoreAndAmending),
            Err(AmendmentProvenanceError::FamilyCountUnsupported { .. })
        ));
        assert!(matches!(
            read_manifest(&missing_field, ManifestPartRule::Field("category")),
            Err(AmendmentProvenanceError::FamilyCountUnsupported { .. })
        ));

        fs::remove_dir_all(&dir).expect("clean fixture dir");
    }

    #[test]
    fn absent_export_root_fails_closed_as_input_absent() {
        let missing = std::env::temp_dir().join(format!(
            "ln-consultant-parser-m209-absent-{}",
            std::process::id()
        ));
        assert!(!missing.exists(), "fixture root must not exist");
        let error = collect_family_denominator(&missing, "consru_export").unwrap_err();
        assert_eq!(error.code(), Some("input_absent"));
        assert_eq!(error.exit_code(), 3);
    }

    #[test]
    fn missing_edition_directory_fails_closed_as_edition_dir_unreadable() {
        static COUNTER: AtomicU32 = AtomicU32::new(0);
        let unique = COUNTER.fetch_add(1, Ordering::SeqCst);
        let repo = std::env::temp_dir().join(format!(
            "ln-consultant-parser-m209-repo-{}-{unique}",
            std::process::id()
        ));
        let export_root = repo.join(EXPORT_DIR_DEFAULT).join(EXPORT_ROOT_TAIL);
        fs::create_dir_all(&export_root).expect("create export root");
        for spec in &FAMILY_SPECS {
            let (tail, is_manifest) = match &spec.source {
                FamilySource::Manifest { path_tail, .. } => (*path_tail, true),
                FamilySource::Directory { path_tail, .. } => (*path_tail, false),
            };
            let target = export_root.join(tail);
            if is_manifest {
                fs::write(
                    &target,
                    r#"{"bank":"LAW","is_core_act":true,"category":"c","document_type":"decision"}"#,
                )
                .expect("write manifest fixture");
            } else {
                fs::create_dir_all(&target).expect("create directory fixture");
                fs::write(target.join("one.xml"), b"<x/>").expect("write file fixture");
            }
        }

        let error = collect_family_denominator(&repo, EXPORT_DIR_DEFAULT).unwrap_err();
        assert_eq!(error.code(), Some("edition_dir_unreadable"));
        assert_eq!(error.exit_code(), 3);

        fs::remove_dir_all(&repo).expect("clean fixture repo");
    }
}
