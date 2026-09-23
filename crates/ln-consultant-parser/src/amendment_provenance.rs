//! M209/S03 amendment-provenance evidence model (D552 / D554).
//!
//! Count-only, ASCII-only, fail-closed. Four legs of R070 for the named
//! `cc:44-fz` Work chain live here:
//!
//! - `families` (T01) declares the S03 family denominator: it counts records in
//!   the four provider manifests, inventories the four provider export
//!   directories, and reconciles the `law_2013-04-05_44-fz` edition directory.
//! - `amends-provisions` (T02) walks the amending-act and affected-provision
//!   leg: the explicit `amends` edges of the catalog relation run rooted at
//!   `cp:LAW:508812`, joined by `document_key` to the layer1 manifest and by the
//!   declared identity pair (act number, act date from the layer1 title) to the
//!   act exports under `exports/npa`, with the catalog `edition_id` hash as the
//!   corroborating field. Every hyperlink of a pinned act export that names the
//!   44-FZ Work is resolved at statya level against the chain needle of the
//!   frozen hierarchy registry using the `(level, number)` identity pair. Each
//!   edge lands in exactly one outcome code and the outcome partition sums to
//!   the declared denominator.
//! - `commencement` (T03) records the applicable commencement and transitional
//!   leg as a source-bound absence: one slot per layer1 record of the T02
//!   amending-act denominator, each carrying a closed-vocabulary evidence class,
//!   slot verdict, reason code and transitional value, with the single frozen
//!   M201 boundary carried verbatim and never upgraded (D415/D416/D553).
//! - `edition-chain` (T04) walks the one multi-edition chain of the corpus
//!   (`exports/npa/law_2013-04-05_44-fz`, 118 edition files) with the unmodified
//!   admitted `multi_edition` runtime, reconciles the declared edition
//!   inventory against the live directory listing and the frozen T01
//!   declaration, and declares the resulting link-topology delta windows
//!   between consecutive editions plus a per-edition and chain determinism
//!   digest.
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

use crate::catalog_sqlite::SqliteCatalog;
use crate::multi_edition::{
    delta, parse_edition_filename, process_editions_directory, EditionSummary,
};

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
    /// An outcome code recorded for an edge whose own counts do not justify it,
    /// or an undocumented outcome. The named code is the emitted one.
    ReasonCodeInconsistent {
        code: &'static str,
        detail: String,
    },
    /// A commencement slot tries to carry the string `legislative` as a value.
    /// A Legislative evidence class is corpus-scale evidence this boundary does
    /// not have and must not be minted (D415).
    LegislativeUpgradeAttempt {
        detail: String,
    },
    /// The artifact mints one of the M208 vocabulary identifiers this boundary
    /// must never create (D216).
    VocabularyMinted {
        detail: String,
    },
    /// A commencement slot reads an enactment date, an edition date or a file
    /// name as a commencement source (D289).
    DateAsCommencement {
        detail: String,
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
            | Self::RawTextLeak { .. }
            | Self::ReasonCodeInconsistent { .. }
            | Self::LegislativeUpgradeAttempt { .. }
            | Self::VocabularyMinted { .. }
            | Self::DateAsCommencement { .. } => 6,
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
            Self::ReasonCodeInconsistent { code, .. } => Some(code),
            Self::LegislativeUpgradeAttempt { .. } => Some("legislative_upgrade_attempt"),
            Self::VocabularyMinted { .. } => Some("vocabulary_minted"),
            Self::DateAsCommencement { .. } => Some("date-as-commencement"),
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
            Self::ReasonCodeInconsistent { code, detail } => {
                write!(formatter, "outcome not justified: code={code} {detail}")
            }
            Self::LegislativeUpgradeAttempt { detail } => {
                write!(formatter, "legislative upgrade attempted: {detail}")
            }
            Self::VocabularyMinted { detail } => {
                write!(formatter, "m208 vocabulary minted: {detail}")
            }
            Self::DateAsCommencement { detail } => {
                write!(formatter, "date read as commencement: {detail}")
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

    /// Signed count: a JSON number by magnitude and sign, never a string and
    /// never routed through a float.
    fn signed(&mut self, key: &str, value: i64) {
        self.key(key);
        self.buffer.push_str(&value.to_string());
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

/// Evidence mode. T01 ships `families`; T02 adds `amends-provisions`; T03 adds
/// `commencement`; T04 adds `edition-chain`. Later S03 tasks add the remaining
/// modes.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProvenanceMode {
    Families,
    AmendsProvisions,
    Commencement,
    EditionChain,
}

impl ProvenanceMode {
    fn parse(value: &str) -> Result<Self, AmendmentProvenanceError> {
        match value {
            "families" => Ok(Self::Families),
            "amends-provisions" => Ok(Self::AmendsProvisions),
            "commencement" => Ok(Self::Commencement),
            "edition-chain" => Ok(Self::EditionChain),
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
    ensure_out_containment(repo_root, &cli.out)?;

    let (rendered, heartbeat, drift) = match cli.mode {
        ProvenanceMode::Families => {
            let denominator = collect_family_denominator(repo_root, &cli.export_dir)?;
            validate_family_denominator(&denominator)?;
            let rendered = render_family_denominator(&denominator);
            let heartbeat = family_denominator_heartbeat(&denominator);
            (rendered, heartbeat, DriftSubject::Families(denominator))
        }
        ProvenanceMode::AmendsProvisions => {
            let evidence = collect_amends_provisions(repo_root, &cli.export_dir)?;
            validate_amends_provisions(&evidence)?;
            let rendered = render_amends_provisions(&evidence);
            let heartbeat = amends_provision_heartbeat(&evidence);
            (
                rendered,
                heartbeat,
                DriftSubject::Amends(Box::new(evidence)),
            )
        }
        ProvenanceMode::Commencement => {
            let evidence = collect_commencement_transition(repo_root, &cli.export_dir)?;
            validate_commencement_transition(&evidence)?;
            let rendered = render_commencement_transition(&evidence);
            let heartbeat = commencement_heartbeat(&evidence);
            (
                rendered,
                heartbeat,
                DriftSubject::Commencement(Box::new(evidence)),
            )
        }
        ProvenanceMode::EditionChain => {
            let evidence = collect_edition_delta(repo_root, &cli.export_dir)?;
            validate_edition_delta(&evidence)?;
            let rendered = render_edition_delta(&evidence);
            let heartbeat = edition_delta_heartbeat(&evidence);
            (
                rendered,
                heartbeat,
                DriftSubject::EditionChain(Box::new(evidence)),
            )
        }
    };
    ensure_ascii_and_clean(&rendered)?;

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
                Err(match &drift {
                    DriftSubject::Families(denominator) => {
                        diagnose_check_drift(&tracked, denominator)
                    }
                    DriftSubject::Amends(evidence) => {
                        diagnose_amends_check_drift(&tracked, evidence)
                    }
                    DriftSubject::Commencement(evidence) => {
                        diagnose_commencement_check_drift(&tracked, evidence)
                    }
                    DriftSubject::EditionChain(evidence) => {
                        diagnose_edition_delta_check_drift(&tracked, evidence)
                    }
                })
            }
        }
    }
}

/// Which live render the `--check` byte compare is diagnosing.
enum DriftSubject {
    Families(FamilyDenominator),
    Amends(Box<AmendsProvisionEvidence>),
    Commencement(Box<CommencementTransitionEvidence>),
    EditionChain(Box<EditionDeltaEvidence>),
}

// ---------------------------------------------------------------------------
// amends-provisions mode (T02)
//
// The amending-act and affected-provision leg of R070 for the named chain.
// Everything below is count-only, ASCII-only, fail-closed and re-derived live
// from one named corpus revision: the licensed provider export, the catalog
// relation database and the frozen hierarchy registry are read, never written.
// ---------------------------------------------------------------------------

/// Artifact schema for the S03 amending-act and affected-provision leg.
pub const AMENDS_SCHEMA: &str = "law-nexus/r070-amending-act-provision/v1";
/// Artifact kind discriminator.
pub const AMENDS_KIND: &str = "m209-s03-amending-act-provision";
/// Task discriminator of this artifact.
pub const AMENDS_TASK: &str = "T02";
/// Repository-relative path of the frozen hierarchy registry.
pub const REGISTRY_RELATIVE_PATH: &str = "prd/architecture/kb-hierarchy-registry.yaml";
/// The registry needle that names the chain Work (`cc:44-fz`).
pub const REGISTRY_NEEDLE: &str = "law_2013-04-05_44-fz";
/// Substrings that mark a reference as naming the 44-FZ Work. Two needles only:
/// the act number and the chain's own short name. Both are declared, so the
/// reference rule is reproducible and can always be re-derived.
pub const FZ44_REFERENCE_NEEDLES: [&str; 2] = ["44-ФЗ", "О контрактной системе"];
/// File-name prefix of the catalog relation database under the export root.
pub const CATALOG_LINKS_PREFIX: &str = "catalog-links-";
/// File-name suffix of the catalog relation database.
pub const CATALOG_LINKS_SUFFIX: &str = ".sqlite";
/// Tail of the layer1 manifest under the export root.
pub const LAYER1_MANIFEST_TAIL: &str = "manifest_layer1_44fz_and_amending_laws.jsonl";
/// Tail of the single-act export directory under the export root.
pub const NPA_EXPORTS_TAIL: &str = "exports/npa";
/// Bound on the catalog edge read. A read that reaches the bound fails closed
/// (`family_count_unsupported`) rather than silently truncating the family.
pub const AMENDS_EDGE_LIMIT: u32 = 4096;
/// Maximum distinct statya references a single act may declare before the count
/// is treated as a parsing blow-up rather than a measurement.
const MAX_STATYA_REFS_PER_ACT: u64 = 512;

/// Outcome vocabulary of the amends-provisions partition. Every catalog edge
/// lands in exactly one of these, so the by-outcome counts always sum to the
/// declared denominator (D552).
pub const AMENDS_PROVISION_REASON_CODES: [&str; 7] = [
    "resolved-provision",
    "provision-not-in-registry",
    "no-statya-reference",
    "target-not-44fz",
    "unparsed-act",
    "no-export-file",
    "no-layer1-record",
];

/// Fail-closed codes this mode can emit: the six structural codes shared with
/// the families mode plus every outcome code, because an outcome whose recorded
/// counts do not justify it is itself a refusal.
pub const AMENDS_PROVISION_FAIL_CLOSED_CODES: [&str; 13] = [
    "input_absent",
    "input_hash_mismatch",
    "family_count_unsupported",
    "zero_denominator",
    "non_ascii_evidence",
    "raw_text_leak",
    "no-layer1-record",
    "no-export-file",
    "unparsed-act",
    "target-not-44fz",
    "provision-not-in-registry",
    "no-statya-reference",
    "resolved-provision",
];

// Grounding pins of the accepted corpus revision. They are re-derived live on
// every run and compared; a mismatch is `family_count_unsupported`, never a
// silent re-baseline (the emitter measures, it does not inventory).
const EXPECTED_CHAIN_ROOT_SOURCE_ID: &str = "cp:LAW:508812";
const EXPECTED_CHAIN_PROFILE: &str = "procurement-core";
const EXPECTED_CHAIN_STATUS: &str = "complete";
const EXPECTED_RUNS_TOTAL: i64 = 1;
const EXPECTED_AMENDS_EDGES_TOTAL: u64 = 120;
const EXPECTED_LAYER1_RECORDS_TOTAL: u64 = 122;
const EXPECTED_LAYER1_CORE_ACTS: u64 = 1;
const EXPECTED_LAYER1_AMENDING_ACTS: u64 = 121;
const EXPECTED_REGISTRY_STATYA_BINDINGS: u64 = 94;
const EXPECTED_REGISTRY_BINDINGS_TOTAL: u64 = 102;

/// One pinned input of the amending-act leg.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsInputPin {
    pub input_id: String,
    pub relative_path: String,
    pub input_bytes: u64,
    pub input_sha256: String,
}

/// The relation run that roots the edge set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsRunPins {
    pub run_id: i64,
    pub profile: String,
    pub root_source_id: String,
    pub status: String,
    pub source_artifact_sha256: String,
    pub table_artifact_sha256: String,
}

/// One `amends` edge of the named chain, joined to its layer1 record and its
/// exported act file, carrying counts, catalog identifiers and one outcome
/// code only. No prose, no XML, no tooltip and no article text.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsProvisionRow {
    pub item_id: i64,
    pub document_key: i64,
    pub act_number: String,
    pub act_date: String,
    pub layer1_record_present: bool,
    pub candidate_files: u64,
    pub edition_id_corroborated: bool,
    pub export_file_bytes: u64,
    pub export_links_total: u64,
    pub export_links_naming_44fz: u64,
    pub admitted_hyperlink_count: u64,
    pub admitted_amends_count: u64,
    pub admitted_cites_count: u64,
    pub admitted_implements_count: u64,
    pub admitted_unknown_count: u64,
    pub statya_refs_distinct: u64,
    pub statya_refs_resolved: u64,
    pub outcome: &'static str,
}

/// The whole amending-act and affected-provision leg.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AmendsProvisionEvidence {
    pub run: AmendsRunPins,
    pub runs_total: i64,
    pub layer1_records_total: u64,
    pub layer1_core_acts: u64,
    pub layer1_amending_acts: u64,
    pub amends_edges_total: u64,
    pub registry_needle: String,
    pub registry_statya_bindings: u64,
    pub registry_glava_bindings: u64,
    pub registry_bindings_total: u64,
    pub npa_relative_path: String,
    pub npa_files_total: u64,
    pub npa_bytes_total: u64,
    pub npa_listing_sha256: String,
    pub inputs: Vec<AmendsInputPin>,
    pub rows: Vec<AmendsProvisionRow>,
    pub by_outcome: BTreeMap<String, u64>,
    pub by_layer1_coverage: BTreeMap<String, u64>,
    pub distinct_statya_refs: u64,
    pub distinct_statya_refs_resolved: u64,
}

fn reason_unsupported(code: &'static str, detail: impl Into<String>) -> AmendmentProvenanceError {
    AmendmentProvenanceError::ReasonCodeInconsistent {
        code,
        detail: detail.into(),
    }
}

fn join_relative(export_root_relative: &str, name: &str) -> String {
    format!("{export_root_relative}/{name}")
}

/// Reads `DD.MM.YYYY` out of a manifest title and normalises it to
/// `YYYY-MM-DD`. The title itself never leaves this function.
fn act_date_from_title(title: &str) -> Option<String> {
    let needle = "от ";
    let mut search = 0usize;
    while let Some(offset) = title[search..].find(needle) {
        let start = search + offset + needle.len();
        search = start;
        let candidate: String = title[start..].chars().take(10).collect();
        let bytes = candidate.as_bytes();
        if bytes.len() == 10
            && bytes[2] == b'.'
            && bytes[5] == b'.'
            && bytes[0..2].iter().all(u8::is_ascii_digit)
            && bytes[3..5].iter().all(u8::is_ascii_digit)
            && bytes[6..10].iter().all(u8::is_ascii_digit)
        {
            return Some(format!(
                "{}-{}-{}",
                &candidate[6..10],
                &candidate[3..5],
                &candidate[0..2]
            ));
        }
    }
    None
}

/// Reads the digits of a `N 188-ФЗ` law number. The `ФЗ` tail is never kept.
fn act_number_from_law_number(law_number: &str) -> Option<String> {
    let after = law_number.split('N').nth(1)?;
    let digits: String = after
        .trim_start()
        .chars()
        .take_while(char::is_ascii_digit)
        .collect();
    if digits.is_empty() {
        None
    } else {
        Some(digits)
    }
}

/// Sorted `(revision, hash, bytes)` candidates of one act under `exports/npa`.
///
/// The join key is the declared pair (the chain's act number and the act date
/// carried by the layer1 title); the `edition_id` hash is the corroborating
/// field, mirroring the S02 candidate-identity rule (D548/D550) where the pair
/// is authoritative and `key_path` only corroborates.
fn npa_export_candidates(
    npa_dir: &Path,
    act_date: &str,
    act_number: &str,
) -> Result<Vec<(String, String, u64)>, AmendmentProvenanceError> {
    let prefix = format!("law_{act_date}_{act_number}-fz_rev-");
    let entries = fs::read_dir(npa_dir).map_err(|_| input_absent(npa_dir.display().to_string()))?;
    let mut found: Vec<(String, String, u64)> = Vec::new();
    for entry in entries.flatten() {
        let metadata = match entry.metadata() {
            Ok(metadata) => metadata,
            Err(_) => continue,
        };
        if !metadata.is_file() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        let Some(rest) = name.strip_prefix(&prefix) else {
            continue;
        };
        let Some(stem) = rest.strip_suffix(".xml") else {
            continue;
        };
        let Some((revision, hash)) = stem.split_once('_') else {
            continue;
        };
        if hash.len() != 8 || !hash.bytes().all(|byte| byte.is_ascii_hexdigit()) {
            continue;
        }
        found.push((revision.to_owned(), hash.to_owned(), metadata.len()));
    }
    found.sort();
    Ok(found)
}

fn is_word_char(character: char) -> bool {
    character.is_alphanumeric()
}

/// Reads an unsigned integer field from a flat JSONL line.
///
/// These manifests carry the requested numeric keys as bare integers, so a
/// bounded digit scan is exact. A value that is not a digit run reads as
/// `None`, which means prose can never be read as a number.
fn flat_integer(line: &str, key: &str) -> Option<i64> {
    let needle = format!("\"{key}\":");
    let start = line.find(&needle)? + needle.len();
    let rest = line[start..].trim_start();
    let digits: String = rest.chars().take_while(char::is_ascii_digit).collect();
    if digits.is_empty() {
        None
    } else {
        digits.parse().ok()
    }
}

/// Consumes one Russian statya suffix after the stem `стат`.
fn strip_statya_suffix(rest: &str) -> Option<&str> {
    const SUFFIXES: [&str; 14] = [
        "ьями", "ьям", "ьях", "ьей", "ья", "ьи", "ье", "ью", "ей", "я", "е", "и", "ю", "ь",
    ];
    for suffix in SUFFIXES {
        if let Some(tail) = rest.strip_prefix(suffix) {
            return Some(tail);
        }
    }
    None
}

/// Consumes `\s*<digits>[.<digits>]` after a statya suffix.
fn read_statya_number(rest: &str) -> Option<String> {
    let trimmed = rest.trim_start();
    if trimmed.len() == rest.len() {
        return None;
    }
    let mut number = String::new();
    let mut seen_dot = false;
    for character in trimmed.chars() {
        if character.is_ascii_digit() {
            number.push(character);
            continue;
        }
        if character == '.' && !seen_dot && !number.is_empty() {
            seen_dot = true;
            number.push(character);
            continue;
        }
        break;
    }
    while number.ends_with('.') {
        number.pop();
    }
    if number.is_empty() {
        None
    } else {
        Some(number)
    }
}

/// First full-word statya reference of a link text: the leading locator of the
/// amendment instruction, for example `в статье 8:` yields `8`.
fn first_statya_reference(text: &str) -> Option<String> {
    let stem = "стат";
    let mut search = 0usize;
    while let Some(offset) = text[search..].find(stem) {
        let start = search + offset;
        search = start + stem.len();
        if text[..start].chars().next_back().is_some_and(is_word_char) {
            continue;
        }
        let Some(rest) = strip_statya_suffix(&text[start + stem.len()..]) else {
            continue;
        };
        if let Some(number) = read_statya_number(rest) {
            return Some(number);
        }
    }
    None
}

/// Parses the chain's `(level, number)` bindings out of the flat registry YAML.
///
/// Only lines that carry all four of `path_needle`, `level`, `number` and `cc`
/// are bindings; the expression and works entries further down the file carry
/// different keys and are skipped. A repeated `(level, number)` pair for the
/// chain needle is an identity conflict and fails closed (D548/D550).
fn parse_registry_bindings(
    text: &str,
) -> Result<BTreeMap<(String, String), String>, AmendmentProvenanceError> {
    let mut bindings: BTreeMap<(String, String), String> = BTreeMap::new();
    for line in text.lines() {
        let Some(body) = line.trim().strip_prefix("- {") else {
            continue;
        };
        let body = body.strip_suffix('}').unwrap_or(body);
        let mut path_needle: Option<String> = None;
        let mut level: Option<String> = None;
        let mut number: Option<String> = None;
        let mut cc: Option<String> = None;
        for part in body.split(',') {
            let Some((key, value)) = part.split_once(':') else {
                continue;
            };
            let value = value.trim().trim_matches('"').trim();
            match key.trim() {
                "path_needle" => path_needle = Some(value.to_owned()),
                "level" => level = Some(value.to_owned()),
                "number" => number = Some(value.to_owned()),
                "cc" => cc = Some(value.to_owned()),
                _ => {}
            }
        }
        let (Some(path_needle), Some(level), Some(number), Some(cc)) =
            (path_needle, level, number, cc)
        else {
            continue;
        };
        if path_needle != REGISTRY_NEEDLE {
            continue;
        }
        if bindings
            .insert((level.clone(), number.clone()), cc)
            .is_some()
        {
            return Err(family_unsupported(
                "kb-hierarchy-registry",
                format!("the chain needle repeats the {level} {number} identity"),
            ));
        }
    }
    Ok(bindings)
}

fn find_single_catalog_links(
    export_root: &Path,
) -> Result<(String, PathBuf), AmendmentProvenanceError> {
    let entries =
        fs::read_dir(export_root).map_err(|_| input_absent(export_root.display().to_string()))?;
    let mut names: Vec<String> = Vec::new();
    for entry in entries.flatten() {
        let name = entry.file_name().to_string_lossy().into_owned();
        if name.starts_with(CATALOG_LINKS_PREFIX) && name.ends_with(CATALOG_LINKS_SUFFIX) {
            names.push(name);
        }
    }
    names.sort();
    match names.len() {
        0 => Err(input_absent(
            "catalog-links-*.sqlite under the export root".to_owned(),
        )),
        1 => {
            let name = names.remove(0);
            let path = export_root.join(&name);
            Ok((name, path))
        }
        _ => Err(family_unsupported(
            "catalog-links",
            "the export root carries more than one catalog relation database",
        )),
    }
}

fn pin_of(
    input_id: &str,
    path: &Path,
    relative_path: String,
) -> Result<AmendsInputPin, AmendmentProvenanceError> {
    let bytes = fs::read(path).map_err(|_| input_absent(path.display().to_string()))?;
    Ok(AmendsInputPin {
        input_id: input_id.to_owned(),
        relative_path,
        input_bytes: bytes.len() as u64,
        input_sha256: format!("sha256:{}", sha256_hex(&bytes)),
    })
}

/// Re-derives the amending-act and affected-provision leg from the live corpus.
pub fn collect_amends_provisions(
    repo_root: &Path,
    export_dir: &str,
) -> Result<AmendsProvisionEvidence, AmendmentProvenanceError> {
    let export_root_relative = export_root_relative_path(export_dir);
    let export_root = resolve_export_root(repo_root, export_dir);

    // 1. Catalog relation run plus the explicit `amends` edge set (read-only).
    let (sqlite_name, sqlite_path) = find_single_catalog_links(&export_root)?;
    let sqlite_relative = join_relative(&export_root_relative, &sqlite_name);
    let catalog = SqliteCatalog::open_read_only(&sqlite_path)
        .map_err(|_| input_absent(sqlite_relative.clone()))?;
    if !catalog.is_read_only().unwrap_or(false) {
        return Err(family_unsupported(
            "catalog-links",
            "the catalog relation database did not open read-only",
        ));
    }
    let edge_set = catalog
        .amends_edge_set(AMENDS_EDGE_LIMIT)
        .map_err(|_| family_unsupported("catalog-links", "the amends edge set is unreadable"))?
        .ok_or_else(|| input_absent(sqlite_relative.clone()))?;
    if edge_set.edges.len() as u32 >= AMENDS_EDGE_LIMIT {
        return Err(family_unsupported(
            "amends-edges",
            "the edge read reached its declared bound, so the family is not measured",
        ));
    }

    // 2. Layer1 manifest: documents keyed by the declared identity pair.
    let manifest_relative = join_relative(&export_root_relative, LAYER1_MANIFEST_TAIL);
    let manifest_path = export_root.join(LAYER1_MANIFEST_TAIL);
    let manifest_text =
        fs::read_to_string(&manifest_path).map_err(|_| input_absent(manifest_relative.clone()))?;
    let mut layer1_records_total = 0u64;
    let mut layer1_core_acts = 0u64;
    let mut layer1_amending_acts = 0u64;
    let mut layer1: BTreeMap<i64, (String, String)> = BTreeMap::new();
    let mut layer1_amending_keys: Vec<i64> = Vec::new();
    let mut layer1_present_keys: Vec<i64> = Vec::new();
    for line in manifest_text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        layer1_records_total += 1;
        let key = flat_integer(line, "document_key").ok_or_else(|| {
            family_unsupported(
                LAYER1_MANIFEST_TAIL,
                "a layer1 record carries no numeric document_key",
            )
        })?;
        let law_number = match flat_field(line, "law_number") {
            Some(FlatValue::Str(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no string law_number",
                ))
            }
        };
        let title = match flat_field(line, "title") {
            Some(FlatValue::Str(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no string title",
                ))
            }
        };
        let core = match flat_field(line, "is_core_act") {
            Some(FlatValue::Bool(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no boolean is_core_act",
                ))
            }
        };
        layer1_present_keys.push(key);
        if core {
            layer1_core_acts += 1;
        } else {
            layer1_amending_acts += 1;
            layer1_amending_keys.push(key);
        }
        // The family counts every layer1 record, but only a record that carries
        // the declared law identity pair can join an act export. A record such
        // as a Constitutional Court ruling carries a case-style `law_number`
        // and therefore contributes to the denominators without entering the
        // join map; an edge that did reference it records `no-export-file`.
        let (Some(date), Some(number)) = (
            act_date_from_title(title),
            act_number_from_law_number(law_number),
        ) else {
            continue;
        };
        layer1.insert(key, (date, number));
    }

    // 3. Registry: the statya level of the chain needle is the admitted identity
    //    vocabulary for candidate provision targets.
    let registry_path = repo_root.join(REGISTRY_RELATIVE_PATH);
    let registry_text = fs::read_to_string(&registry_path)
        .map_err(|_| input_absent(REGISTRY_RELATIVE_PATH.to_owned()))?;
    let bindings = parse_registry_bindings(&registry_text)?;
    let registry_statya_bindings = bindings
        .keys()
        .filter(|(level, _)| level == "statya")
        .count() as u64;
    let registry_glava_bindings = bindings
        .keys()
        .filter(|(level, _)| level == "glava")
        .count() as u64;
    let registry_bindings_total = bindings.len() as u64;

    // 4. The single-act export directory inventory (join surface, pinned).
    let npa_relative = join_relative(&export_root_relative, NPA_EXPORTS_TAIL);
    let npa_dir = export_root.join(NPA_EXPORTS_TAIL);
    let npa_inventory = inventory_directory(&npa_dir).map_err(|_| {
        AmendmentProvenanceError::EditionDirUnreadable {
            path: npa_relative.clone(),
        }
    })?;

    // 5. Per-edge join and resolution.
    let mut rows: Vec<AmendsProvisionRow> = Vec::with_capacity(edge_set.edges.len());
    let mut by_outcome: BTreeMap<String, u64> = AMENDS_PROVISION_REASON_CODES
        .iter()
        .map(|code| ((*code).to_owned(), 0u64))
        .collect();
    let mut distinct_refs: BTreeMap<String, u64> = BTreeMap::new();
    let mut edges_with_layer1: Vec<i64> = Vec::new();

    for edge in &edge_set.edges {
        let edition = edge.edition_id.clone().unwrap_or_default();
        let corroborating_hash = edition
            .strip_prefix("edition-")
            .and_then(|value| value.get(..8))
            .map(str::to_owned);

        let identity = layer1.get(&edge.document_key).cloned();
        if identity.is_none() && !layer1_present_keys.contains(&edge.document_key) {
            *by_outcome.entry("no-layer1-record".to_owned()).or_insert(0) += 1;
            rows.push(AmendsProvisionRow {
                item_id: edge.item_id,
                document_key: edge.document_key,
                act_number: String::new(),
                act_date: String::new(),
                layer1_record_present: false,
                candidate_files: 0,
                edition_id_corroborated: false,
                export_file_bytes: 0,
                export_links_total: 0,
                export_links_naming_44fz: 0,
                admitted_hyperlink_count: 0,
                admitted_amends_count: 0,
                admitted_cites_count: 0,
                admitted_implements_count: 0,
                admitted_unknown_count: 0,
                statya_refs_distinct: 0,
                statya_refs_resolved: 0,
                outcome: "no-layer1-record",
            });
            continue;
        }
        let act_date = identity
            .as_ref()
            .map(|(date, _)| date.clone())
            .unwrap_or_default();
        let act_number = identity
            .as_ref()
            .map(|(_, number)| number.clone())
            .unwrap_or_default();
        edges_with_layer1.push(edge.document_key);
        let candidates = npa_export_candidates(&npa_dir, &act_date, &act_number)?;
        let corroborated: Vec<(String, String, u64)> = candidates
            .iter()
            .filter(|(_, hash, _)| Some(hash) == corroborating_hash.as_ref())
            .cloned()
            .collect();
        let corroborated_flag = !corroborated.is_empty();
        let selected: Vec<(String, String, u64)> = if corroborated_flag {
            corroborated
        } else {
            candidates.clone()
        };
        let candidate_files = candidates.len() as u64;

        if selected.is_empty() {
            *by_outcome.entry("no-export-file".to_owned()).or_insert(0) += 1;
            rows.push(AmendsProvisionRow {
                item_id: edge.item_id,
                document_key: edge.document_key,
                act_number,
                act_date,
                layer1_record_present: true,
                candidate_files,
                edition_id_corroborated: false,
                export_file_bytes: 0,
                export_links_total: 0,
                export_links_naming_44fz: 0,
                admitted_hyperlink_count: 0,
                admitted_amends_count: 0,
                admitted_cites_count: 0,
                admitted_implements_count: 0,
                admitted_unknown_count: 0,
                statya_refs_distinct: 0,
                statya_refs_resolved: 0,
                outcome: "no-export-file",
            });
            continue;
        }
        let mut export_file_bytes = 0u64;
        let mut links_total = 0u64;
        let mut naming = 0u64;
        let mut admitted_hyperlink_count = 0u64;
        let mut admitted_amends_count = 0u64;
        let mut admitted_cites_count = 0u64;
        let mut admitted_implements_count = 0u64;
        let mut admitted_unknown_count = 0u64;
        let mut refs: BTreeMap<String, u64> = BTreeMap::new();
        for (revision, hash, bytes) in &selected {
            let file_name = format!("law_{act_date}_{act_number}-fz_rev-{revision}_{hash}.xml");
            let file_path = npa_dir.join(&file_name);
            let xml = fs::read(&file_path).map_err(|_| input_absent(file_name.clone()))?;
            export_file_bytes += *bytes;
            let source_path = file_path.to_string_lossy().into_owned();
            let admitted =
                crate::multi_edition::process_edition_for_path(&xml, 0, revision, &source_path);
            admitted_hyperlink_count += admitted.hyperlink_count as u64;
            admitted_amends_count += admitted.amends_count as u64;
            admitted_cites_count += admitted.cites_count as u64;
            admitted_implements_count += admitted.implements_count as u64;
            admitted_unknown_count += admitted.unknown_count as u64;
            let links = crate::hyperlink::extract_hyperlinks(&xml);
            links_total += links.len() as u64;
            for link in &links {
                let names_44fz = FZ44_REFERENCE_NEEDLES
                    .iter()
                    .any(|needle| link.text.contains(needle) || link.context.contains(needle));
                if !names_44fz {
                    continue;
                }
                naming += 1;
                if let Some(number) = first_statya_reference(&link.text) {
                    *refs.entry(number).or_insert(0) += 1;
                }
            }
        }

        let statya_refs_distinct = refs.len() as u64;
        if statya_refs_distinct > MAX_STATYA_REFS_PER_ACT {
            return Err(family_unsupported(
                "amends-provisions",
                "a single act declares more statya references than the declared bound",
            ));
        }
        let mut statya_refs_resolved = 0u64;
        for number in refs.keys() {
            distinct_refs.entry(number.clone()).or_insert(0);
            if bindings.contains_key(&("statya".to_owned(), number.clone())) {
                statya_refs_resolved += 1;
            }
        }

        let outcome: &'static str = if links_total == 0 {
            "unparsed-act"
        } else if naming == 0 {
            "target-not-44fz"
        } else if statya_refs_distinct == 0 {
            "no-statya-reference"
        } else if statya_refs_resolved == 0 {
            "provision-not-in-registry"
        } else {
            "resolved-provision"
        };
        *by_outcome.entry(outcome.to_owned()).or_insert(0) += 1;

        rows.push(AmendsProvisionRow {
            item_id: edge.item_id,
            document_key: edge.document_key,
            act_number,
            act_date,
            layer1_record_present: true,
            candidate_files,
            edition_id_corroborated: corroborated_flag,
            export_file_bytes,
            export_links_total: links_total,
            export_links_naming_44fz: naming,
            admitted_hyperlink_count,
            admitted_amends_count,
            admitted_cites_count,
            admitted_implements_count,
            admitted_unknown_count,
            statya_refs_distinct,
            statya_refs_resolved,
            outcome,
        });
    }

    let mut distinct_statya_refs_resolved = 0u64;
    for number in distinct_refs.keys() {
        if bindings.contains_key(&("statya".to_owned(), number.clone())) {
            distinct_statya_refs_resolved += 1;
        }
    }

    let edges_without_layer1 = layer1_amending_keys
        .iter()
        .filter(|key| !edges_with_layer1.contains(key))
        .count() as u64;
    let mut by_layer1_coverage: BTreeMap<String, u64> = BTreeMap::new();
    by_layer1_coverage.insert(
        "with-amends-edge".to_owned(),
        layer1_amending_keys.len() as u64 - edges_without_layer1,
    );
    by_layer1_coverage.insert("without-amends-edge".to_owned(), edges_without_layer1);

    let inputs = vec![
        pin_of("catalog_links_sqlite", &sqlite_path, sqlite_relative)?,
        pin_of("layer1_manifest", &manifest_path, manifest_relative.clone())?,
        pin_of(
            "kb_hierarchy_registry",
            &registry_path,
            REGISTRY_RELATIVE_PATH.to_owned(),
        )?,
    ];

    Ok(AmendsProvisionEvidence {
        run: AmendsRunPins {
            run_id: edge_set.run_id,
            profile: edge_set.profile.clone(),
            root_source_id: edge_set.root_source_id.clone(),
            status: edge_set.status.clone(),
            source_artifact_sha256: format!("sha256:{}", edge_set.source_artifact_sha256),
            table_artifact_sha256: format!("sha256:{}", edge_set.table_artifact_sha256),
        },
        runs_total: edge_set.runs_total,
        layer1_records_total,
        layer1_core_acts,
        layer1_amending_acts,
        amends_edges_total: edge_set.edges.len() as u64,
        registry_needle: REGISTRY_NEEDLE.to_owned(),
        registry_statya_bindings,
        registry_glava_bindings,
        registry_bindings_total,
        npa_relative_path: npa_relative,
        npa_files_total: npa_inventory.files_total,
        npa_bytes_total: npa_inventory.bytes_total,
        npa_listing_sha256: npa_inventory.listing_sha256,
        inputs,
        rows,
        by_outcome,
        by_layer1_coverage,
        distinct_statya_refs: distinct_refs.len() as u64,
        distinct_statya_refs_resolved,
    })
}

/// Fails closed when the artifact does not measure what it declares: a zero
/// denominator, a partition that does not sum to its total, a grounding pin
/// that drifted, an outcome whose recorded counts do not justify it, or an
/// anchor that is not repository-relative.
pub fn validate_amends_provisions(
    evidence: &AmendsProvisionEvidence,
) -> Result<(), AmendmentProvenanceError> {
    if evidence.amends_edges_total == 0 || evidence.layer1_amending_acts == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: "amends-provisions".to_owned(),
        });
    }
    if evidence.registry_statya_bindings == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: "kb-hierarchy-registry".to_owned(),
        });
    }
    if evidence.runs_total != EXPECTED_RUNS_TOTAL {
        return Err(family_unsupported(
            "catalog-links",
            format!(
                "the catalog carries {} relation runs but one is declared",
                evidence.runs_total
            ),
        ));
    }
    if evidence.run.root_source_id != EXPECTED_CHAIN_ROOT_SOURCE_ID
        || evidence.run.profile != EXPECTED_CHAIN_PROFILE
        || evidence.run.status != EXPECTED_CHAIN_STATUS
    {
        return Err(family_unsupported(
            "catalog-links",
            "the relation run no longer roots the declared chain",
        ));
    }
    if evidence.amends_edges_total != EXPECTED_AMENDS_EDGES_TOTAL
        || evidence.layer1_records_total != EXPECTED_LAYER1_RECORDS_TOTAL
        || evidence.layer1_core_acts != EXPECTED_LAYER1_CORE_ACTS
        || evidence.layer1_amending_acts != EXPECTED_LAYER1_AMENDING_ACTS
    {
        return Err(family_unsupported(
            "amends-provisions",
            "the declared denominators drifted from the accepted revision",
        ));
    }
    if evidence.registry_bindings_total != EXPECTED_REGISTRY_BINDINGS_TOTAL
        || evidence.registry_statya_bindings != EXPECTED_REGISTRY_STATYA_BINDINGS
    {
        return Err(family_unsupported(
            "kb-hierarchy-registry",
            "the chain needle binding count drifted from the accepted revision",
        ));
    }
    if evidence.rows.len() as u64 != evidence.amends_edges_total {
        return Err(family_unsupported(
            "amends-provisions",
            "the per-edge rows do not cover the declared denominator",
        ));
    }

    for row in &evidence.rows {
        if !AMENDS_PROVISION_REASON_CODES.contains(&row.outcome) {
            return Err(reason_unsupported(
                "no-layer1-record",
                format!("edge {} carries an undocumented outcome", row.item_id),
            ));
        }
        if row.document_key <= 0 || row.item_id <= 0 {
            return Err(reason_unsupported(
                row.outcome,
                "a row carries a non-positive catalog identifier",
            ));
        }
        if row.layer1_record_present {
            if !row.act_number.is_empty()
                && (!row.act_number.bytes().all(|byte| byte.is_ascii_digit())
                    || row.act_date.len() != 10
                    || !row
                        .act_date
                        .bytes()
                        .all(|byte| byte.is_ascii_digit() || byte == b'-'))
            {
                return Err(reason_unsupported(
                    row.outcome,
                    "a joined row carries a non-token act identity",
                ));
            }
            if row.act_number.is_empty() && row.outcome != "no-export-file" {
                return Err(reason_unsupported(
                    row.outcome,
                    "a row without a law identity pair must record no-export-file",
                ));
            }
        } else if row.outcome != "no-layer1-record" {
            return Err(reason_unsupported(
                row.outcome,
                "a row without a layer1 record must record no-layer1-record",
            ));
        }
        if row.outcome == "no-layer1-record" && row.layer1_record_present {
            return Err(reason_unsupported(
                "no-layer1-record",
                "no-layer1-record is recorded for a joined row",
            ));
        }
        if row.outcome == "no-export-file" && row.candidate_files != 0 {
            return Err(reason_unsupported(
                "no-export-file",
                "no-export-file is recorded while candidate files exist",
            ));
        }
        if row.outcome == "unparsed-act" && row.export_links_total != 0 {
            return Err(reason_unsupported(
                "unparsed-act",
                "unparsed-act is recorded while links were parsed",
            ));
        }
        if row.outcome == "target-not-44fz"
            && (row.export_links_naming_44fz != 0 || row.export_links_total == 0)
        {
            return Err(reason_unsupported(
                "target-not-44fz",
                "target-not-44fz is recorded while a 44-FZ reference is present",
            ));
        }
        if row.outcome == "no-statya-reference"
            && (row.export_links_naming_44fz == 0 || row.statya_refs_distinct != 0)
        {
            return Err(reason_unsupported(
                "no-statya-reference",
                "no-statya-reference is recorded while a statya reference is present",
            ));
        }
        if row.outcome == "provision-not-in-registry"
            && (row.statya_refs_distinct == 0 || row.statya_refs_resolved != 0)
        {
            return Err(reason_unsupported(
                "provision-not-in-registry",
                "provision-not-in-registry is recorded while a target resolved",
            ));
        }
        if row.outcome == "resolved-provision" && row.statya_refs_resolved == 0 {
            return Err(reason_unsupported(
                "resolved-provision",
                "resolved-provision is recorded with zero resolved targets",
            ));
        }
        if row.statya_refs_resolved > row.statya_refs_distinct {
            return Err(reason_unsupported(
                row.outcome,
                "a row resolves more targets than it declares",
            ));
        }
    }

    let outcome_total: u64 = evidence.by_outcome.values().sum();
    if evidence
        .by_outcome
        .keys()
        .any(|code| !AMENDS_PROVISION_REASON_CODES.contains(&code.as_str()))
        || outcome_total != evidence.amends_edges_total
    {
        return Err(family_unsupported(
            "amends-provisions",
            format!(
                "the outcome partition sums to {outcome_total} but the denominator is {}",
                evidence.amends_edges_total
            ),
        ));
    }
    let coverage_total: u64 = evidence.by_layer1_coverage.values().sum();
    if coverage_total != evidence.layer1_amending_acts {
        return Err(family_unsupported(
            "amends-provisions",
            format!(
                "the layer1 coverage partition sums to {coverage_total} but the amending family is {}",
                evidence.layer1_amending_acts
            ),
        ));
    }
    if evidence.distinct_statya_refs_resolved > evidence.distinct_statya_refs {
        return Err(family_unsupported(
            "amends-provisions",
            "more distinct targets resolved than were declared",
        ));
    }
    check_repo_relative(&evidence.npa_relative_path)?;
    for pin in &evidence.inputs {
        check_repo_relative(&pin.relative_path)?;
        if !pin.input_sha256.starts_with("sha256:") || pin.input_sha256.len() != 71 {
            return Err(AmendmentProvenanceError::InputHashMismatch {
                family_id: pin.input_id.clone(),
                path: pin.relative_path.clone(),
                detail: "a declared input pin is not a sha256 digest".to_owned(),
            });
        }
    }
    Ok(())
}

/// Canonical compact render. Fixed top-level key order, no timestamps, ASCII by
/// construction: every scalar is a count, a catalog identifier, a validated
/// token or a named reason code (D424).
pub fn render_amends_provisions(evidence: &AmendsProvisionEvidence) -> String {
    let mut writer = ObjectWriter::new();
    writer.string("schema", AMENDS_SCHEMA);
    writer.number("schema_version", 2);
    writer.string("kind", AMENDS_KIND);
    writer.string("milestone", MILESTONE);
    writer.string("slice", SLICE);
    writer.string("task", AMENDS_TASK);
    writer.string("lifecycle", LIFECYCLE);
    writer.boolean("authoritative", false);
    writer.string("requirement_id", REQUIREMENT_ID);
    writer.string("disposition", DISPOSITION);
    writer.string("disposition_decision", DISPOSITION_DECISION);
    writer.boolean("count_only", true);
    writer.boolean("ascii_only", true);
    writer.string("count_basis", AMENDS_COUNT_BASIS);

    writer.key("relation_run");
    {
        let mut entry = ObjectWriter::new();
        entry.number("run_id", evidence.run.run_id as u64);
        entry.string("profile", &evidence.run.profile);
        entry.string("root_source_id", &evidence.run.root_source_id);
        entry.string("status", &evidence.run.status);
        entry.string(
            "source_artifact_sha256",
            &evidence.run.source_artifact_sha256,
        );
        entry.string("table_artifact_sha256", &evidence.run.table_artifact_sha256);
        entry.number("runs_total", evidence.runs_total as u64);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("denominator");
    {
        let mut entry = ObjectWriter::new();
        entry.number("amends_edges_total", evidence.amends_edges_total);
        entry.number("layer1_records_total", evidence.layer1_records_total);
        entry.number("layer1_core_acts", evidence.layer1_core_acts);
        entry.number("layer1_amending_acts", evidence.layer1_amending_acts);
        entry.number("rows_total", evidence.rows.len() as u64);
        entry.counts("by_outcome", &evidence.by_outcome);
        entry.counts("by_layer1_coverage", &evidence.by_layer1_coverage);
        entry.number("distinct_statya_refs", evidence.distinct_statya_refs);
        entry.number(
            "distinct_statya_refs_resolved",
            evidence.distinct_statya_refs_resolved,
        );
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("registry");
    {
        let mut entry = ObjectWriter::new();
        entry.string("relative_path", REGISTRY_RELATIVE_PATH);
        entry.string("needle", &evidence.registry_needle);
        entry.number("statya_bindings", evidence.registry_statya_bindings);
        entry.number("glava_bindings", evidence.registry_glava_bindings);
        entry.number("bindings_total", evidence.registry_bindings_total);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("npa_exports");
    {
        let mut entry = ObjectWriter::new();
        entry.string("relative_path", &evidence.npa_relative_path);
        entry.number("files_total", evidence.npa_files_total);
        entry.number("bytes_total", evidence.npa_bytes_total);
        entry.string("listing_sha256", &evidence.npa_listing_sha256);
        entry.string("file_name_pattern", AMENDS_EXPORT_PATTERN);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("inputs");
    writer.buffer.push('[');
    for (index, pin) in evidence.inputs.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.string("input_id", &pin.input_id);
        entry.string("relative_path", &pin.relative_path);
        entry.number("input_bytes", pin.input_bytes);
        entry.string("input_sha256", &pin.input_sha256);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.key("edges");
    writer.buffer.push('[');
    for (index, row) in evidence.rows.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.number("item_id", row.item_id as u64);
        entry.number("document_key", row.document_key as u64);
        entry.string("act_number", &row.act_number);
        entry.string("act_date", &row.act_date);
        entry.boolean("layer1_record_present", row.layer1_record_present);
        entry.number("candidate_files", row.candidate_files);
        entry.boolean("edition_id_corroborated", row.edition_id_corroborated);
        entry.number("export_file_bytes", row.export_file_bytes);
        entry.number("export_links_total", row.export_links_total);
        entry.number("export_links_naming_44fz", row.export_links_naming_44fz);
        entry.number("admitted_hyperlink_count", row.admitted_hyperlink_count);
        entry.number("admitted_amends_count", row.admitted_amends_count);
        entry.number("admitted_cites_count", row.admitted_cites_count);
        entry.number("admitted_implements_count", row.admitted_implements_count);
        entry.number("admitted_unknown_count", row.admitted_unknown_count);
        entry.number("statya_refs_distinct", row.statya_refs_distinct);
        entry.number("statya_refs_resolved", row.statya_refs_resolved);
        entry.string("outcome", row.outcome);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.fixed_strings("reason_codes", &AMENDS_PROVISION_REASON_CODES);
    writer.fixed_strings("fail_closed_codes", &AMENDS_PROVISION_FAIL_CLOSED_CODES);
    writer.fixed_strings("non_claims", &AMENDS_NON_CLAIMS);
    writer.finish()
}

/// Count-only stderr heartbeat for the amends-provisions leg.
pub fn amends_provision_heartbeat(evidence: &AmendsProvisionEvidence) -> String {
    let resolved = evidence
        .by_outcome
        .get("resolved-provision")
        .copied()
        .unwrap_or(0);
    let unresolved = evidence.amends_edges_total.saturating_sub(resolved);
    format!(
        "amends={} resolved={} unresolved={} layer1={} rows={} drift=0",
        evidence.amends_edges_total,
        resolved,
        unresolved,
        evidence.layer1_amending_acts,
        evidence.rows.len()
    )
}

/// File-name pattern of the act exports the join rule accepts.
pub const AMENDS_EXPORT_PATTERN: &str = "law_<act-date>_<act-number>-fz_rev-<rev>_<hash8>.xml";

/// Denominator definition prose for the amending-act leg.
const AMENDS_COUNT_BASIS: &str = "The denominator is re-derived live on every run: the explicit amends edges of the catalog relation run rooted at cp:LAW:508812, joined by document_key to the layer1 manifest and by the declared pair (act number, act date) to the act exports under exports/npa, with the catalog edition_id hash as the corroborating field. Every edge lands in exactly one outcome, the outcome partition sums to the declared denominator, and candidate provision targets are resolved at statya level against the chain needle of prd/architecture/kb-hierarchy-registry.yaml using the (level, number) identity pair. Nothing here is typed by hand and no zero denominator is a measurement.";

/// Claim bounds carried by the amending-act and affected-provision artifact.
const AMENDS_NON_CLAIMS: [&str; 9] = [
    "This leg is scoped to the named cc:44-fz chain and the amending family rooted at its catalog document cp:LAW:508812; it is not every amending act of the corpus and not every-edition coverage.",
    "Candidate provision targets are candidates, not legal determinations: a resolved statya identity means the reference could be bound to an admitted ComponentConcept of the chain needle, not that any provision was legally amended.",
    "No commencement is inferred from this leg: an act date, a revision date and a file name are not commencement evidence, and no commencement or transitional rule is stated here (D289/D406).",
    "No corpus text is copied into this artifact: no XML bytes, no article text, no document titles, no offline URIs and no raw relation tooltips; only counts, catalog identifiers, repository-relative paths, byte counts, sha256 pins and named reason codes.",
    "The frozen M201 R070 proof gate is not widened, reopened or restated here, and the three frozen M201 pins stay byte-identical.",
    "A zero denominator is not a measurement and fails closed as zero_denominator; no declared total may be presented as a measurement when its partition does not sum to it (D552).",
    "R070 stays active (D416); no promotion gate is promoted, satisfied or moved off unsatisfied by this artifact and no requirement record is mutated.",
    "No M202 inventory count may stand as a quantifier in this artifact (D539); every declared total is a live-derived count bound to a named input path, its byte count and its sha256 pin.",
    "The catalog destination_json column is carried only as a bounded catalog identifier and is not treated as an affected provision: it does not resolve to a 44-FZ ComponentConcept.",
];

fn diagnose_amends_check_drift(
    tracked: &[u8],
    evidence: &AmendsProvisionEvidence,
) -> AmendmentProvenanceError {
    if tracked.iter().any(|byte| *byte >= 0x80) {
        return AmendmentProvenanceError::NonAsciiEvidence {
            detail: "tracked artifact is not ascii".to_owned(),
        };
    }
    let tracked_text = String::from_utf8_lossy(tracked);
    for pin in &evidence.inputs {
        if !tracked_text.contains(&pin.input_sha256) {
            return AmendmentProvenanceError::InputHashMismatch {
                family_id: pin.input_id.clone(),
                path: pin.relative_path.clone(),
                detail: "tracked pin differs from the live input pin".to_owned(),
            };
        }
    }
    if !tracked_text.contains(&format!(
        "\"amends_edges_total\":{}",
        evidence.amends_edges_total
    )) {
        return family_unsupported(
            "amends-provisions",
            "tracked denominator differs from the live denominator",
        );
    }
    family_unsupported(
        "<artifact>",
        "artifact bytes differ from the live render while every declared pin matches",
    )
}

// ---------------------------------------------------------------------------
// commencement mode (T03)
//
// The third leg of R070 for the named chain: applicable commencement and
// transitional rules. No admitted commencement source exists — the M208/S03
// commencement admission checkpoint stands at `not-adopted` with
// `owner_admission_ref: none`, the M208/S04 checkpoint stands the same way, and
// the M207/S04 C4 human pilot was not run — so this mode records the absence
// explicitly instead of inferring commencement from a date, a file name or an
// edition (D289 / D406 / D415). Every emitted slot is a count, a categorical
// code and a catalog identifier.
// ---------------------------------------------------------------------------

/// Artifact schema for the S03 commencement and transitional leg.
pub const COMMENCEMENT_SCHEMA: &str = "law-nexus/r070-commencement-transition/v1";
/// Artifact kind discriminator.
pub const COMMENCEMENT_KIND: &str = "m209-s03-commencement-transition";
/// Task discriminator of this artifact.
pub const COMMENCEMENT_TASK: &str = "T03";
/// The T02 artifact whose amending-act denominator this leg must reproduce.
pub const T02_EVIDENCE_RELATIVE_PATH: &str =
    "prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json";
/// The frozen M201 R070 proof gate that carries the bounded commencement boundary.
pub const M201_R070_GATE_RELATIVE_PATH: &str =
    "prd/migration/rust-evidence/m201-s04-r070-proof-gate.json";
/// The M208/S03 admission checkpoint that governs the commencement surface.
pub const M208_S03_ADMISSION_RELATIVE_PATH: &str =
    "prd/architecture/m208-s03-admission-commencement.md";
/// The M208/S04 admission checkpoint that governs the replay surface.
pub const M208_S04_ADMISSION_RELATIVE_PATH: &str =
    "prd/architecture/m208-s04-admission-bounded-replay.md";
/// The M207/S04 C4 protocol: delivered as a protocol, never as accepted annotation.
pub const M207_C4_PROTOCOL_RELATIVE_PATH: &str = "prd/annotation/m207-s04-c4-protocol.md";
/// The M207/S04 C4 operational receipt pinned as the human-pilot-absent witness.
pub const M207_C4_RECEIPT_RELATIVE_PATH: &str =
    "prd/migration/rust-evidence/m207-s04-c4-operational-receipt.json";

/// The declared admission value the two M208 checkpoints must still carry.
pub const M208_DECLARED_NOT_ADOPTED: &str = "not-adopted";
/// The declared owner admission reference both checkpoints must still carry.
pub const M208_DECLARED_NO_OWNER: &str = "none";
/// The declared runtime work value both checkpoints must still carry.
pub const M208_DECLARED_RUNTIME_NOT_STARTED: &str = "not-started";
/// The declared operational acceptance the M207/S04 C4 receipt carries.
pub const M207_DECLARED_C4_NON_PASS: &str = "non-pass";
/// The declared human-pilot status of the M207/S04 C4 contour.
pub const M207_DECLARED_HUMAN_PILOT_ABSENT: &str = "absent";
/// The declared pilot rate status of the M207/S04 C4 contour.
pub const M207_DECLARED_RATE_NOT_MEASURED: &str = "not-measured";
/// Declared marker text the M208/S04 checkpoint must still carry verbatim.
pub const M207_DECLARED_PILOT_MARKER: &str = "the human pilot was not run";
/// Declared marker text for the unmeasured pilot rates.
pub const M207_DECLARED_RATE_MARKER: &str = "rates are `not-measured`";
/// Declared marker text for the non-pass operational acceptance.
pub const M207_DECLARED_ACCEPTANCE_MARKER: &str = "`operational_acceptance=non-pass`";

/// Evidence class vocabulary of one commencement slot. `absent` is the only
/// class this leg may derive for itself; the two unproven classes are carried
/// only from the frozen M201 boundary and are never minted here (D415).
pub const COMMENCEMENT_EVIDENCE_CLASSES: [&str; 3] =
    ["hypothesized_from_oracle_diff", "editorial_hint", "absent"];

/// Slot verdict vocabulary. `slot-filled-not-proven` is a slot filled with an
/// unproven class; `explicitly-absent` is an affirmative boundary record.
pub const COMMENCEMENT_SLOT_VERDICTS: [&str; 2] = ["slot-filled-not-proven", "explicitly-absent"];

/// Proximate per-slot reason vocabulary, in declaration order. The two gate
/// codes are global admission facts recorded once in `admission_gate`; a slot's
/// own proximate cause is never the global gate.
pub const COMMENCEMENT_REASON_CODES: [&str; 4] = [
    "no-legislative-commencement-source",
    "m207-human-pilot-absent",
    "m208-s03-not-adopted",
    "act-text-not-admitted",
];

/// Transitional slot vocabulary: an affirmative source-bound absence, or an
/// unresolved slot. Neither value is a chronology-only default (ADR-0021).
pub const COMMENCEMENT_TRANSITIONAL_VALUES: [&str; 2] = ["explicitly_absent", "unresolved"];

/// Slot kind vocabulary: the named chain itself, or one amending act of the
/// T02 amending-act denominator.
pub const COMMENCEMENT_SLOT_KINDS: [&str; 2] = ["named-chain", "amending-act"];

/// M208 vocabulary this artifact must never mint (D216 / D457).
pub const MINTED_VOCABULARY_TOKENS: [&str; 4] = [
    "ActivationTrigger",
    "TransitionalResolver",
    "EvidenceAnchor",
    "LegislativeEffect",
];

/// The declared evidence class this leg requires and does not have.
pub const COMMENCEMENT_REQUIRED_EVIDENCE_CLASS: &str = "human-annotation";
/// The declared status of the required evidence class.
pub const COMMENCEMENT_REQUIRED_EVIDENCE_STATUS: &str = "absent";

/// Stable identifier of the single source-bound absence justification.
pub const COMMENCEMENT_TRANSITIONAL_JUSTIFICATION_ID: &str = "m201-frozen-commencement-boundary";

/// Fail-closed codes this mode can emit: the six structural codes shared with
/// the families mode, the three commencement guards, and the four per-slot
/// reason codes, because a slot whose recorded counts do not justify it is
/// itself a refusal.
pub const COMMENCEMENT_FAIL_CLOSED_CODES: [&str; 13] = [
    "input_absent",
    "input_hash_mismatch",
    "family_count_unsupported",
    "zero_denominator",
    "non_ascii_evidence",
    "raw_text_leak",
    "legislative_upgrade_attempt",
    "vocabulary_minted",
    "date-as-commencement",
    "no-legislative-commencement-source",
    "m207-human-pilot-absent",
    "m208-s03-not-adopted",
    "act-text-not-admitted",
];

/// One commencement slot of the named chain or of one amending act.
///
/// Identity is the catalog `document_key`; `slot_kind` says whether it is the
/// named chain itself or one amending act of the T02 denominator. The
/// categorical codes are all closed vocabularies, and `commencement_rule_ref`
/// is empty unless the frozen M201 boundary fills the slot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommencementSlot {
    pub document_key: i64,
    pub slot_kind: &'static str,
    pub act_number: String,
    pub act_date: String,
    pub act_text_admitted: bool,
    pub evidence_class: String,
    pub slot_verdict: &'static str,
    pub reason_code: &'static str,
    pub transitional: &'static str,
    pub commencement_rule_ref: String,
    pub transitional_basis_id: String,
}

/// Live-read admission gate facts. Every field is re-derived on each run from a
/// named tracked document, and any drift fails closed rather than silently
/// re-baselining the boundary.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommencementAdmissionGate {
    pub m208_s03_admission: String,
    pub m208_s03_owner_admission_ref: String,
    pub m208_s03_runtime_work: String,
    pub m208_s04_admission: String,
    pub m208_s04_owner_admission_ref: String,
    pub m208_s04_runtime_work: String,
    pub m207_human_pilot: &'static str,
    pub m207_c4_operational_acceptance: String,
    pub m207_c4_rate_status: &'static str,
    pub m207_c4_protocol_relative_path: String,
    pub m207_c4_receipt_relative_path: String,
}

/// The whole commencement and transitional leg.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommencementTransitionEvidence {
    pub admission_gate: CommencementAdmissionGate,
    pub slots_total: u64,
    pub named_chain_slots: u64,
    pub amending_act_slots: u64,
    pub t02_layer1_records_total: u64,
    pub t02_layer1_amending_acts: u64,
    pub t02_amends_edges_total: u64,
    pub t02_input_sha256: String,
    pub frozen_gate_evidence_class: String,
    pub frozen_gate_commencement_rule_ref: String,
    pub frozen_gate_transitional: String,
    pub inputs: Vec<AmendsInputPin>,
    pub slots: Vec<CommencementSlot>,
    pub by_evidence_class: BTreeMap<String, u64>,
    pub by_slot_verdict: BTreeMap<String, u64>,
    pub by_reason_code: BTreeMap<String, u64>,
    pub by_transitional: BTreeMap<String, u64>,
    pub class_matched_ids: Vec<String>,
}

/// Every closed vocabulary of this mode, pre-seeded to zero so a code that no
/// slot realises is still a measured zero rather than an absent key.
fn seed_counts(codes: &[&'static str]) -> BTreeMap<String, u64> {
    codes
        .iter()
        .map(|code| ((*code).to_owned(), 0u64))
        .collect()
}

/// Reads a `**name: value**` or `**name:** value` declaration out of a tracked
/// admission document. Only the first match is returned, and the character
/// after `name` must be a separator so a longer key never matches by prefix.
fn star_field<'a>(text: &'a str, name: &str) -> Option<&'a str> {
    for line in text.lines() {
        let line = line.trim();
        let Some(rest) = line.strip_prefix("**") else {
            continue;
        };
        let Some(after) = rest.strip_prefix(name) else {
            continue;
        };
        if !after.starts_with([':', '*']) {
            continue;
        }
        let after = after.trim_start_matches([':', '*', ' ']);
        let value = after.split("**").next().unwrap_or(after).trim();
        if !value.is_empty() {
            return Some(value);
        }
    }
    None
}

/// True when a value looks like a date or a corpus file name (including an
/// `edition-` identity hash) rather than an admitted rule reference. Such a
/// value may never be a commencement source.
fn is_date_or_filename(value: &str) -> bool {
    let bytes = value.as_bytes();
    let date_shaped = bytes.len() == 10
        && bytes[4] == b'-'
        && bytes[7] == b'-'
        && bytes[0..4].iter().all(u8::is_ascii_digit)
        && bytes[5..7].iter().all(u8::is_ascii_digit)
        && bytes[8..10].iter().all(u8::is_ascii_digit);
    date_shaped
        || value.starts_with("law_")
        || value.starts_with("edition-")
        || value.ends_with(".xml")
        || value.contains("rev-unknown")
}

/// Re-derives the commencement and transitional leg from the live repository.
pub fn collect_commencement_transition(
    repo_root: &Path,
    export_dir: &str,
) -> Result<CommencementTransitionEvidence, AmendmentProvenanceError> {
    let export_root_relative = export_root_relative_path(export_dir);
    let export_root = resolve_export_root(repo_root, export_dir);

    // 1. The frozen M201 R070 proof gate: the only filled commencement slot.
    let gateway_path = repo_root.join(M201_R070_GATE_RELATIVE_PATH);
    let gate_text = fs::read_to_string(&gateway_path)
        .map_err(|_| input_absent(M201_R070_GATE_RELATIVE_PATH.to_owned()))?;
    let frozen_gate_evidence_class = match flat_field(&gate_text, "evidence_class") {
        Some(FlatValue::Str(value)) => value.to_owned(),
        _ => {
            return Err(family_unsupported(
                "m201-r070-proof-gate",
                "the frozen gate carries no string evidence_class in its commencement boundary",
            ))
        }
    };
    let frozen_gate_commencement_rule_ref = match flat_field(&gate_text, "commencement_rule_ref") {
        Some(FlatValue::Str(value)) => value.to_owned(),
        _ => {
            return Err(family_unsupported(
                "m201-r070-proof-gate",
                "the frozen gate carries no string commencement_rule_ref",
            ))
        }
    };
    let frozen_gate_transitional = match flat_field(&gate_text, "transitional") {
        Some(FlatValue::Str(value)) => value.to_owned(),
        _ => {
            return Err(family_unsupported(
                "m201-r070-proof-gate",
                "the frozen gate carries no string transitional slot value",
            ))
        }
    };
    if !COMMENCEMENT_EVIDENCE_CLASSES.contains(&frozen_gate_evidence_class.as_str()) {
        return Err(AmendmentProvenanceError::LegislativeUpgradeAttempt {
            detail: format!(
                "the frozen gate carries the evidence class {} outside the declared vocabulary",
                frozen_gate_evidence_class
            ),
        });
    }
    if !COMMENCEMENT_TRANSITIONAL_VALUES.contains(&frozen_gate_transitional.as_str()) {
        return Err(family_unsupported(
            "m201-r070-proof-gate",
            "the frozen gate carries a transitional value outside the declared vocabulary",
        ));
    }

    // 2. The M208/S03 and M208/S04 admission checkpoints must still be
    //    not-adopted with no owner admission; an adopted premise changes the
    //    boundary, so it fails closed instead of silently re-baselining.
    let s03_path = repo_root.join(M208_S03_ADMISSION_RELATIVE_PATH);
    let s03_text = fs::read_to_string(&s03_path)
        .map_err(|_| input_absent(M208_S03_ADMISSION_RELATIVE_PATH.to_owned()))?;
    let s04_path = repo_root.join(M208_S04_ADMISSION_RELATIVE_PATH);
    let s04_text = fs::read_to_string(&s04_path)
        .map_err(|_| input_absent(M208_S04_ADMISSION_RELATIVE_PATH.to_owned()))?;
    let mut declared = Vec::new();
    for (label, text) in [
        (M208_S03_ADMISSION_RELATIVE_PATH, s03_text.as_str()),
        (M208_S04_ADMISSION_RELATIVE_PATH, s04_text.as_str()),
    ] {
        let admission = star_field(text, "admission");
        let owner = star_field(text, "owner_admission_ref");
        let runtime_work = star_field(text, "runtime_work");
        if admission != Some(M208_DECLARED_NOT_ADOPTED) {
            return Err(reason_unsupported(
                "m208-s03-not-adopted",
                format!("{label} no longer declares admission: not-adopted"),
            ));
        }
        if owner != Some(M208_DECLARED_NO_OWNER) {
            return Err(reason_unsupported(
                "m208-s03-not-adopted",
                format!("{label} no longer declares owner_admission_ref: none"),
            ));
        }
        if runtime_work != Some(M208_DECLARED_RUNTIME_NOT_STARTED) {
            return Err(reason_unsupported(
                "m208-s03-not-adopted",
                format!("{label} no longer declares runtime_work: not-started"),
            ));
        }
        declared.push((
            admission.unwrap_or_default().to_owned(),
            owner.unwrap_or_default().to_owned(),
            runtime_work.unwrap_or_default().to_owned(),
        ));
    }

    // 3. The M207/S04 human pilot: the protocol is delivered, the pilot was not
    //    run, the rates stay not-measured and the operational acceptance is a
    //    non-pass. Every leg is asserted against a named tracked document.
    let protocol_path = repo_root.join(M207_C4_PROTOCOL_RELATIVE_PATH);
    if !protocol_path.is_file() {
        return Err(input_absent(M207_C4_PROTOCOL_RELATIVE_PATH.to_owned()));
    }
    for marker in [
        M207_DECLARED_PILOT_MARKER,
        M207_DECLARED_RATE_MARKER,
        M207_DECLARED_ACCEPTANCE_MARKER,
    ] {
        if !s04_text.contains(marker) {
            return Err(reason_unsupported(
                "m207-human-pilot-absent",
                format!(
                    "{M208_S04_ADMISSION_RELATIVE_PATH} no longer declares the marker {marker}"
                ),
            ));
        }
    }
    let receipt_path = repo_root.join(M207_C4_RECEIPT_RELATIVE_PATH);
    let receipt_text = fs::read_to_string(&receipt_path)
        .map_err(|_| input_absent(M207_C4_RECEIPT_RELATIVE_PATH.to_owned()))?;
    let mut acceptance = String::new();
    for line in receipt_text.lines() {
        if let Some(FlatValue::Str(value)) = flat_field(line, "operational_acceptance") {
            acceptance = value.to_owned();
            break;
        }
    }
    if acceptance != M207_DECLARED_C4_NON_PASS {
        return Err(reason_unsupported(
            "m207-human-pilot-absent",
            "the C4 operational receipt no longer claims a non-pass acceptance",
        ));
    }

    // 4. The T02 artifact is the declared amending-act denominator of this leg.
    let t02_path = repo_root.join(T02_EVIDENCE_RELATIVE_PATH);
    let t02_text = fs::read_to_string(&t02_path)
        .map_err(|_| input_absent(T02_EVIDENCE_RELATIVE_PATH.to_owned()))?;
    let t02_layer1_records_total = flat_integer(&t02_text, "layer1_records_total")
        .and_then(|value| u64::try_from(value).ok())
        .ok_or_else(|| {
            family_unsupported(
                "m209-s03-amending-act-provision-evidence",
                "the T02 artifact declares no layer1 record total",
            )
        })?;
    let t02_layer1_amending_acts = flat_integer(&t02_text, "layer1_amending_acts")
        .and_then(|value| u64::try_from(value).ok())
        .ok_or_else(|| {
            family_unsupported(
                "m209-s03-amending-act-provision-evidence",
                "the T02 artifact declares no amending-act total",
            )
        })?;
    let t02_amends_edges_total = flat_integer(&t02_text, "amends_edges_total")
        .and_then(|value| u64::try_from(value).ok())
        .ok_or_else(|| {
            family_unsupported(
                "m209-s03-amending-act-provision-evidence",
                "the T02 artifact declares no amends edge total",
            )
        })?;
    let t02_input_sha256 = format!("sha256:{}", sha256_hex(t02_text.as_bytes()));

    // 5. The layer1 manifest: one slot per record, the core record being the
    //    named chain and every other record an amending act.
    let manifest_relative = join_relative(&export_root_relative, LAYER1_MANIFEST_TAIL);
    let manifest_path = export_root.join(LAYER1_MANIFEST_TAIL);
    let manifest_text =
        fs::read_to_string(&manifest_path).map_err(|_| input_absent(manifest_relative.clone()))?;
    let npa_dir = export_root.join(NPA_EXPORTS_TAIL);
    let mut slots: Vec<CommencementSlot> = Vec::new();
    let mut named_chain_slots = 0u64;
    let mut amending_act_slots = 0u64;
    let mut by_evidence_class = seed_counts(&COMMENCEMENT_EVIDENCE_CLASSES);
    let mut by_slot_verdict = seed_counts(&COMMENCEMENT_SLOT_VERDICTS);
    let mut by_reason_code = seed_counts(&COMMENCEMENT_REASON_CODES);
    let mut by_transitional = seed_counts(&COMMENCEMENT_TRANSITIONAL_VALUES);
    for line in manifest_text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let document_key = flat_integer(line, "document_key").ok_or_else(|| {
            family_unsupported(
                LAYER1_MANIFEST_TAIL,
                "a layer1 record carries no numeric document_key",
            )
        })?;
        let core = match flat_field(line, "is_core_act") {
            Some(FlatValue::Bool(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no boolean is_core_act",
                ))
            }
        };
        let law_number = match flat_field(line, "law_number") {
            Some(FlatValue::Str(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no string law_number",
                ))
            }
        };
        let title = match flat_field(line, "title") {
            Some(FlatValue::Str(value)) => value,
            _ => {
                return Err(family_unsupported(
                    LAYER1_MANIFEST_TAIL,
                    "a layer1 record carries no string title",
                ))
            }
        };
        let act_date = act_date_from_title(title).unwrap_or_default();
        let act_number = act_number_from_law_number(law_number).unwrap_or_default();
        // A slot is "act text admitted" when its declared identity pair
        // resolves to act text in the evaluated revision: either a single-act
        // export under exports/npa, or the numbered chain edition directory of
        // that same declared pair. That is an identity question only: an act
        // date and a file name are never read as commencement evidence.
        let act_text_admitted = if act_date.is_empty() || act_number.is_empty() {
            false
        } else {
            let chain_directory = npa_dir.join(format!("law_{act_date}_{act_number}-fz"));
            !npa_export_candidates(&npa_dir, &act_date, &act_number)?.is_empty()
                || chain_directory.is_dir()
        };
        let (slot_kind, evidence_class, slot_verdict, reason_code, transitional, rule_ref, basis) =
            if core {
                named_chain_slots += 1;
                (
                    "named-chain",
                    frozen_gate_evidence_class.clone(),
                    COMMENCEMENT_SLOT_VERDICTS[0],
                    COMMENCEMENT_REASON_CODES[0],
                    COMMENCEMENT_TRANSITIONAL_VALUES[0],
                    frozen_gate_commencement_rule_ref.clone(),
                    COMMENCEMENT_TRANSITIONAL_JUSTIFICATION_ID.to_owned(),
                )
            } else {
                amending_act_slots += 1;
                let reason = if act_text_admitted {
                    COMMENCEMENT_REASON_CODES[0]
                } else {
                    COMMENCEMENT_REASON_CODES[3]
                };
                (
                    "amending-act",
                    COMMENCEMENT_EVIDENCE_CLASSES[2].to_owned(),
                    COMMENCEMENT_SLOT_VERDICTS[1],
                    reason,
                    COMMENCEMENT_TRANSITIONAL_VALUES[1],
                    String::new(),
                    String::new(),
                )
            };
        *by_evidence_class
            .entry(evidence_class.to_owned())
            .or_insert(0) += 1;
        *by_slot_verdict.entry(slot_verdict.to_owned()).or_insert(0) += 1;
        *by_reason_code.entry(reason_code.to_owned()).or_insert(0) += 1;
        *by_transitional.entry(transitional.to_owned()).or_insert(0) += 1;
        slots.push(CommencementSlot {
            document_key,
            slot_kind,
            act_number,
            act_date,
            act_text_admitted,
            evidence_class,
            slot_verdict,
            reason_code,
            transitional,
            commencement_rule_ref: rule_ref,
            transitional_basis_id: basis,
        });
    }

    // 6. Input pins: the manifest plus every tracked document this leg reads.
    let inputs = vec![
        pin_of("layer1_manifest", &manifest_path, manifest_relative.clone())?,
        pin_of(
            "t02_amending_act_evidence",
            &t02_path,
            T02_EVIDENCE_RELATIVE_PATH.to_owned(),
        )?,
        pin_of(
            "m201_r070_proof_gate",
            &gateway_path,
            M201_R070_GATE_RELATIVE_PATH.to_owned(),
        )?,
        pin_of(
            "m208_s03_admission",
            &s03_path,
            M208_S03_ADMISSION_RELATIVE_PATH.to_owned(),
        )?,
        pin_of(
            "m208_s04_admission",
            &s04_path,
            M208_S04_ADMISSION_RELATIVE_PATH.to_owned(),
        )?,
        pin_of(
            "m207_c4_protocol",
            &protocol_path,
            M207_C4_PROTOCOL_RELATIVE_PATH.to_owned(),
        )?,
        pin_of(
            "m207_c4_receipt",
            &receipt_path,
            M207_C4_RECEIPT_RELATIVE_PATH.to_owned(),
        )?,
    ];

    let slots_total = slots.len() as u64;
    Ok(CommencementTransitionEvidence {
        admission_gate: CommencementAdmissionGate {
            m208_s03_admission: declared[0].0.clone(),
            m208_s03_owner_admission_ref: declared[0].1.clone(),
            m208_s03_runtime_work: declared[0].2.clone(),
            m208_s04_admission: declared[1].0.clone(),
            m208_s04_owner_admission_ref: declared[1].1.clone(),
            m208_s04_runtime_work: declared[1].2.clone(),
            m207_human_pilot: M207_DECLARED_HUMAN_PILOT_ABSENT,
            m207_c4_operational_acceptance: acceptance,
            m207_c4_rate_status: M207_DECLARED_RATE_NOT_MEASURED,
            m207_c4_protocol_relative_path: M207_C4_PROTOCOL_RELATIVE_PATH.to_owned(),
            m207_c4_receipt_relative_path: M207_C4_RECEIPT_RELATIVE_PATH.to_owned(),
        },
        slots_total,
        named_chain_slots,
        amending_act_slots,
        t02_layer1_records_total,
        t02_layer1_amending_acts,
        t02_amends_edges_total,
        t02_input_sha256,
        frozen_gate_evidence_class,
        frozen_gate_commencement_rule_ref,
        frozen_gate_transitional,
        inputs,
        slots,
        by_evidence_class,
        by_slot_verdict,
        by_reason_code,
        by_transitional,
        class_matched_ids: Vec::new(),
    })
}

/// Fails closed on any drift of the declared boundary, any minted vocabulary
/// and any attempt to read a date or a file name as a commencement source.
pub fn validate_commencement_transition(
    evidence: &CommencementTransitionEvidence,
) -> Result<(), AmendmentProvenanceError> {
    if evidence.slots_total == 0 || evidence.amending_act_slots == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: "commencement".to_owned(),
        });
    }
    if evidence.named_chain_slots != 1 {
        return Err(family_unsupported(
            "commencement",
            "the named chain must contribute exactly one slot",
        ));
    }

    // 0. The two global premises this boundary is premised on. When either stops
    //    holding, the declared reason code itself is what changed.
    let gate = &evidence.admission_gate;
    if gate.m208_s03_admission != M208_DECLARED_NOT_ADOPTED
        || gate.m208_s03_owner_admission_ref != M208_DECLARED_NO_OWNER
        || gate.m208_s03_runtime_work != M208_DECLARED_RUNTIME_NOT_STARTED
        || gate.m208_s04_admission != M208_DECLARED_NOT_ADOPTED
        || gate.m208_s04_owner_admission_ref != M208_DECLARED_NO_OWNER
        || gate.m208_s04_runtime_work != M208_DECLARED_RUNTIME_NOT_STARTED
    {
        return Err(reason_unsupported(
            "m208-s03-not-adopted",
            "the M208 commencement gate no longer carries an unadopted premise",
        ));
    }
    if gate.m207_human_pilot != M207_DECLARED_HUMAN_PILOT_ABSENT
        || gate.m207_c4_operational_acceptance != M207_DECLARED_C4_NON_PASS
        || gate.m207_c4_rate_status != M207_DECLARED_RATE_NOT_MEASURED
    {
        return Err(reason_unsupported(
            "m207-human-pilot-absent",
            "the M207 human pilot absence no longer holds",
        ));
    }

    // 1. Whole-artifact guards, checked on the canonical render so a prohibited
    //    token cannot hide behind a field the checks below do not enumerate.
    let rendered = render_commencement_transition(evidence);
    if rendered.contains("\"legislative\"") {
        return Err(AmendmentProvenanceError::LegislativeUpgradeAttempt {
            detail: "the artifact carries the string legislative as a value".to_owned(),
        });
    }
    for token in MINTED_VOCABULARY_TOKENS {
        if rendered.contains(token) {
            return Err(AmendmentProvenanceError::VocabularyMinted {
                detail: format!("the artifact mints the identifier {token}"),
            });
        }
    }
    for slot in &evidence.slots {
        for value in [
            slot.commencement_rule_ref.as_str(),
            slot.transitional_basis_id.as_str(),
        ] {
            if !value.is_empty() && is_date_or_filename(value) {
                return Err(AmendmentProvenanceError::DateAsCommencement {
                    detail: "a commencement slot reads a date or a file name as a rule reference"
                        .to_owned(),
                });
            }
        }
        if slot.evidence_class != COMMENCEMENT_EVIDENCE_CLASSES[2]
            && slot.commencement_rule_ref.trim().is_empty()
        {
            return Err(AmendmentProvenanceError::DateAsCommencement {
                detail: "a filled commencement class carries no declared rule reference".to_owned(),
            });
        }
    }

    // 2. The declared denominator: the T02 amending-act denominator, unchanged.
    if evidence.t02_layer1_records_total != EXPECTED_LAYER1_RECORDS_TOTAL
        || evidence.t02_layer1_amending_acts != EXPECTED_LAYER1_AMENDING_ACTS
        || evidence.t02_amends_edges_total != EXPECTED_AMENDS_EDGES_TOTAL
    {
        return Err(family_unsupported(
            "commencement",
            "the T02 amending-act denominator drifted from the accepted revision",
        ));
    }
    if evidence.slots_total != evidence.t02_layer1_records_total
        || evidence.amending_act_slots != evidence.t02_layer1_amending_acts
    {
        return Err(family_unsupported(
            "commencement",
            "the commencement slots do not reproduce the T02 amending-act denominator",
        ));
    }
    if evidence.named_chain_slots + evidence.amending_act_slots != evidence.slots_total {
        return Err(family_unsupported(
            "commencement",
            "the declared slot kinds do not sum to the declared denominator",
        ));
    }
    if evidence.slots.len() as u64 != evidence.slots_total {
        return Err(family_unsupported(
            "commencement",
            "the per-slot rows do not cover the declared denominator",
        ));
    }

    // 3. Closed vocabularies, per slot.
    let mut named_chain_seen = 0u64;
    let mut amending_seen = 0u64;
    for slot in &evidence.slots {
        if !COMMENCEMENT_SLOT_KINDS.contains(&slot.slot_kind) {
            return Err(reason_unsupported(
                slot.reason_code,
                "a slot carries an undocumented slot kind",
            ));
        }
        if !COMMENCEMENT_EVIDENCE_CLASSES.contains(&slot.evidence_class.as_str()) {
            return Err(AmendmentProvenanceError::LegislativeUpgradeAttempt {
                detail: "a slot carries an evidence class outside the declared vocabulary"
                    .to_owned(),
            });
        }
        if !COMMENCEMENT_SLOT_VERDICTS.contains(&slot.slot_verdict) {
            return Err(reason_unsupported(
                slot.reason_code,
                "a slot carries an undocumented slot verdict",
            ));
        }
        if !COMMENCEMENT_REASON_CODES.contains(&slot.reason_code) {
            return Err(reason_unsupported(
                "no-legislative-commencement-source",
                "a slot carries an undocumented reason code",
            ));
        }
        if !COMMENCEMENT_TRANSITIONAL_VALUES.contains(&slot.transitional) {
            return Err(reason_unsupported(
                slot.reason_code,
                "a slot carries an undocumented transitional value",
            ));
        }
        if slot.document_key <= 0 {
            return Err(reason_unsupported(
                slot.reason_code,
                "a slot carries a non-positive catalog identifier",
            ));
        }
        match slot.slot_kind {
            "named-chain" => {
                named_chain_seen += 1;
                if slot.evidence_class != evidence.frozen_gate_evidence_class
                    || slot.commencement_rule_ref != evidence.frozen_gate_commencement_rule_ref
                    || slot.transitional != evidence.frozen_gate_transitional
                {
                    return Err(family_unsupported(
                        "commencement",
                        "the named-chain slot drifted from the frozen M201 boundary",
                    ));
                }
            }
            "amending-act" => {
                amending_seen += 1;
                if slot.evidence_class != COMMENCEMENT_EVIDENCE_CLASSES[2]
                    || !slot.commencement_rule_ref.is_empty()
                    || !slot.transitional_basis_id.is_empty()
                {
                    return Err(AmendmentProvenanceError::LegislativeUpgradeAttempt {
                        detail: "an amending-act slot claims commencement evidence".to_owned(),
                    });
                }
                let expected = if slot.act_text_admitted {
                    COMMENCEMENT_REASON_CODES[0]
                } else {
                    COMMENCEMENT_REASON_CODES[3]
                };
                if slot.reason_code != expected {
                    return Err(reason_unsupported(
                        slot.reason_code,
                        "an amending-act slot does not justify its own reason code",
                    ));
                }
            }
            _ => {}
        }
    }
    if named_chain_seen != evidence.named_chain_slots
        || amending_seen != evidence.amending_act_slots
    {
        return Err(family_unsupported(
            "commencement",
            "the per-kind slot counts do not reproduce the declared denominators",
        ));
    }

    // 4. The partitions must sum to the declared denominator, and the required
    //    evidence class must be an explicit empty set.
    for (label, partition) in [
        ("by_evidence_class", &evidence.by_evidence_class),
        ("by_slot_verdict", &evidence.by_slot_verdict),
        ("by_reason_code", &evidence.by_reason_code),
        ("by_transitional", &evidence.by_transitional),
    ] {
        let sum: u64 = partition.values().sum();
        if sum != evidence.slots_total {
            return Err(family_unsupported(
                "commencement",
                format!("the {label} partition sums to {sum}, not the declared denominator"),
            ));
        }
        for key in partition.keys() {
            if key.bytes().any(|byte| !byte.is_ascii()) {
                return Err(AmendmentProvenanceError::NonAsciiEvidence {
                    detail: format!("a {label} key is not ascii"),
                });
            }
            if !is_allowed_key_token(key) {
                return Err(AmendmentProvenanceError::RawTextLeak {
                    detail: format!("a {label} key is outside the count-only token rule"),
                });
            }
        }
    }
    if !evidence.class_matched_ids.is_empty() {
        return Err(family_unsupported(
            "commencement",
            "class_matched_ids must be an explicit empty set on this boundary",
        ));
    }
    Ok(())
}

/// Source-bound justification of the single affirmative absence claim.
pub const COMMENCEMENT_TRANSITIONAL_JUSTIFICATION: &str = "The named chain's bounded 484-FZ to cc:44-fz:statya-93 edge carries the transitional value explicitly_absent verbatim from the frozen M201 R070 proof gate (prd/migration/rust-evidence/m201-s04-r070-proof-gate.json, commencement_boundary.transitional), whose own non-claim states that it is an affirmative fixture slot and not an ADR-0021 resolver. This is a boundary record of that frozen gate: it is not a determination that no transitional rule exists, and no transitional-rule source is admitted for any slot of this leg.";

/// Denominator definition prose for the commencement and transitional leg.
const COMMENCEMENT_COUNT_BASIS: &str = "The denominator is re-derived live on every run: one slot for the named cc:44-fz chain (the core layer1 record) plus one slot per amending act of the T02 amending-act denominator, declared equal to layer1_records_total of prd/migration/rust-evidence/m209-s03-amending-act-provision-evidence.json. act_text_admitted records whether the slot's declared identity pair resolves to act text in the evaluated revision, either as a single-act export under exports/npa or as its numbered chain edition directory; it is an identity field and never a commencement source. reason_code is the proximate per-slot cause and is drawn from a closed four-code vocabulary; the two global gate codes are never a per-slot cause and are recorded once in admission_gate with their live values. evidence_class is absent for every slot this leg derives for itself: the frozen M201 boundary is the only filled slot and it is carried verbatim, never upgraded. Nothing here is typed by hand and no zero denominator is a measurement.";

/// Claim bounds carried by the commencement and transitional artifact.
const COMMENCEMENT_NON_CLAIMS: [&str; 9] = [
    "This leg is scoped to the named cc:44-fz chain and its amending family; it is not every edition of the chain and not every commencement question of the corpus.",
    "No Legislative upgrade (D415): no slot carries a legislative evidence class, the frozen M201 boundary is carried verbatim as an unproven class, and no class is upgraded by this artifact.",
    "The single explicitly_absent transitional value is an affirmative boundary slot carried from the frozen M201 gate and is not an ADR-0021 resolver; ADR-0021 stays [proposed] and every other slot stays unresolved rather than defaulted (D406/TSG-009).",
    "No resolver runtime exists: no effect-selector token, no transitional-resolver runtime, no evidence-anchor and no legislative-effect identifier is minted by this artifact, and the D252 selector vocabulary stays YAML-only (D216).",
    "No commencement is inferred from a date, a file name or an edition: an act date and a file name are act-identity fields for the export join, not commencement evidence (D289).",
    "No corpus text is copied into this artifact: no XML bytes, no article text, no document titles, no offline URIs and no raw relation tooltips; only counts, catalog identifiers, repository-relative paths, byte counts, sha256 pins and named categorical codes.",
    "The frozen M201 R070 proof gate and the three frozen M201 pins are not widened, reopened or restated here, and the declared M208 startup surfaces stay absent.",
    "A zero denominator is not a measurement and fails closed as zero_denominator; no declared total may be presented as a measurement when its partition does not sum to it (D552).",
    "R070 stays active (D416): no promotion gate is promoted, satisfied or moved off unsatisfied by this artifact, no requirement record is mutated, and class_matched_ids is an explicit empty set because the required human-annotation evidence class is absent.",
];

/// Canonical compact render. Fixed top-level key order, no timestamps, ASCII by
/// construction: every scalar is a count, a catalog identifier, a validated
/// categorical code or a repository-relative path (D424).
pub fn render_commencement_transition(evidence: &CommencementTransitionEvidence) -> String {
    let mut writer = ObjectWriter::new();
    writer.string("schema", COMMENCEMENT_SCHEMA);
    writer.number("schema_version", 3);
    writer.string("kind", COMMENCEMENT_KIND);
    writer.string("milestone", MILESTONE);
    writer.string("slice", SLICE);
    writer.string("task", COMMENCEMENT_TASK);
    writer.string("lifecycle", LIFECYCLE);
    writer.boolean("authoritative", false);
    writer.string("requirement_id", REQUIREMENT_ID);
    writer.string("disposition", DISPOSITION);
    writer.string("disposition_decision", DISPOSITION_DECISION);
    writer.boolean("count_only", true);
    writer.boolean("ascii_only", true);
    writer.string("count_basis", COMMENCEMENT_COUNT_BASIS);

    writer.key("admission_gate");
    {
        let gate = &evidence.admission_gate;
        let mut entry = ObjectWriter::new();
        entry.string("m208_s03_admission", &gate.m208_s03_admission);
        entry.string(
            "m208_s03_owner_admission_ref",
            &gate.m208_s03_owner_admission_ref,
        );
        entry.string("m208_s03_runtime_work", &gate.m208_s03_runtime_work);
        entry.string("m208_s04_admission", &gate.m208_s04_admission);
        entry.string(
            "m208_s04_owner_admission_ref",
            &gate.m208_s04_owner_admission_ref,
        );
        entry.string("m208_s04_runtime_work", &gate.m208_s04_runtime_work);
        entry.string("m207_human_pilot", gate.m207_human_pilot);
        entry.string(
            "m207_c4_operational_acceptance",
            &gate.m207_c4_operational_acceptance,
        );
        entry.string("m207_c4_rate_status", gate.m207_c4_rate_status);
        entry.string(
            "m207_c4_protocol_relative_path",
            &gate.m207_c4_protocol_relative_path,
        );
        entry.string(
            "m207_c4_receipt_relative_path",
            &gate.m207_c4_receipt_relative_path,
        );
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("frozen_m201_boundary");
    {
        let mut entry = ObjectWriter::new();
        entry.string("gate_relative_path", M201_R070_GATE_RELATIVE_PATH);
        entry.string("evidence_class", &evidence.frozen_gate_evidence_class);
        entry.string(
            "commencement_rule_ref",
            &evidence.frozen_gate_commencement_rule_ref,
        );
        entry.string("transitional", &evidence.frozen_gate_transitional);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("denominator");
    {
        let mut entry = ObjectWriter::new();
        entry.number("slots_total", evidence.slots_total);
        entry.number("named_chain_slots", evidence.named_chain_slots);
        entry.number("amending_act_slots", evidence.amending_act_slots);
        entry.number("rows_total", evidence.slots.len() as u64);
        entry.number(
            "t02_layer1_records_total",
            evidence.t02_layer1_records_total,
        );
        entry.number(
            "t02_layer1_amending_acts",
            evidence.t02_layer1_amending_acts,
        );
        entry.number("t02_amends_edges_total", evidence.t02_amends_edges_total);
        entry.counts("by_evidence_class", &evidence.by_evidence_class);
        entry.counts("by_slot_verdict", &evidence.by_slot_verdict);
        entry.counts("by_reason_code", &evidence.by_reason_code);
        entry.counts("by_transitional", &evidence.by_transitional);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("required_evidence");
    {
        let mut entry = ObjectWriter::new();
        entry.string(
            "required_evidence_class",
            COMMENCEMENT_REQUIRED_EVIDENCE_CLASS,
        );
        entry.string(
            "required_evidence_status",
            COMMENCEMENT_REQUIRED_EVIDENCE_STATUS,
        );
        entry.strings("class_matched_ids", &evidence.class_matched_ids);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("transitional_basis");
    {
        let mut entry = ObjectWriter::new();
        entry.string("basis_id", COMMENCEMENT_TRANSITIONAL_JUSTIFICATION_ID);
        entry.string("source_relative_path", M201_R070_GATE_RELATIVE_PATH);
        entry.string("justification", COMMENCEMENT_TRANSITIONAL_JUSTIFICATION);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("inputs");
    writer.buffer.push('[');
    for (index, pin) in evidence.inputs.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.string("input_id", &pin.input_id);
        entry.string("relative_path", &pin.relative_path);
        entry.number("input_bytes", pin.input_bytes);
        entry.string("input_sha256", &pin.input_sha256);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.key("slots");
    writer.buffer.push('[');
    for (index, slot) in evidence.slots.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.number("document_key", slot.document_key as u64);
        entry.string("slot_kind", slot.slot_kind);
        entry.string("act_number", &slot.act_number);
        entry.string("act_date", &slot.act_date);
        entry.boolean("act_text_admitted", slot.act_text_admitted);
        entry.string("evidence_class", &slot.evidence_class);
        entry.string("slot_verdict", slot.slot_verdict);
        entry.string("reason_code", slot.reason_code);
        entry.string("transitional", slot.transitional);
        entry.string("commencement_rule_ref", &slot.commencement_rule_ref);
        entry.string("transitional_basis_id", &slot.transitional_basis_id);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.fixed_strings("slot_kinds", &COMMENCEMENT_SLOT_KINDS);
    writer.fixed_strings("evidence_classes", &COMMENCEMENT_EVIDENCE_CLASSES);
    writer.fixed_strings("slot_verdicts", &COMMENCEMENT_SLOT_VERDICTS);
    writer.fixed_strings("transitional_values", &COMMENCEMENT_TRANSITIONAL_VALUES);
    writer.fixed_strings("reason_codes", &COMMENCEMENT_REASON_CODES);
    writer.fixed_strings("fail_closed_codes", &COMMENCEMENT_FAIL_CLOSED_CODES);
    writer.fixed_strings("non_claims", &COMMENCEMENT_NON_CLAIMS);
    writer.finish()
}

/// Count-only stderr heartbeat for the commencement and transitional leg.
pub fn commencement_heartbeat(evidence: &CommencementTransitionEvidence) -> String {
    let filled = evidence
        .by_slot_verdict
        .get(COMMENCEMENT_SLOT_VERDICTS[0])
        .copied()
        .unwrap_or(0);
    let absent = evidence
        .by_slot_verdict
        .get(COMMENCEMENT_SLOT_VERDICTS[1])
        .copied()
        .unwrap_or(0);
    format!(
        "commencement={} named={} amending={} filled={} absent={} class_matched={} drift=0",
        evidence.slots_total,
        evidence.named_chain_slots,
        evidence.amending_act_slots,
        filled,
        absent,
        evidence.class_matched_ids.len()
    )
}

fn diagnose_commencement_check_drift(
    tracked: &[u8],
    evidence: &CommencementTransitionEvidence,
) -> AmendmentProvenanceError {
    if tracked.iter().any(|byte| *byte >= 0x80) {
        return AmendmentProvenanceError::NonAsciiEvidence {
            detail: "tracked artifact is not ascii".to_owned(),
        };
    }
    let tracked_text = String::from_utf8_lossy(tracked);
    for pin in &evidence.inputs {
        if !tracked_text.contains(&pin.input_sha256) {
            return AmendmentProvenanceError::InputHashMismatch {
                family_id: pin.input_id.clone(),
                path: pin.relative_path.clone(),
                detail: "tracked pin differs from the live input pin".to_owned(),
            };
        }
    }
    if !tracked_text.contains(&format!("\"slots_total\":{}", evidence.slots_total)) {
        return family_unsupported(
            "commencement",
            "tracked denominator differs from the live denominator",
        );
    }
    family_unsupported(
        "<artifact>",
        "artifact bytes differ from the live render while every declared pin matches",
    )
}

// ---------------------------------------------------------------------------
// edition-chain mode (T04)
//
// The fourth leg of R070 for the named chain: the resulting edition delta. The
// corpus carries exactly one multi-edition chain, the tracked 44-FZ Work under
// `exports/npa/law_2013-04-05_44-fz` (118 `edition-*.xml` files), so this leg
// walks that one chain with the unmodified admitted `multi_edition` runtime and
// declares the link-topology delta between consecutive editions. The declared
// inventory is re-derived from the directory listing and reconciled against the
// frozen T01 declaration, so the 118-edition figure is a measurement and never
// a carried-over number. Every parser count here is a link classification of
// the admitted runtime, never a normative text delta and never legal effect.
// ---------------------------------------------------------------------------

/// Artifact schema for the S03 edition-delta leg.
pub const EDITION_DELTA_SCHEMA: &str = "law-nexus/r070-edition-delta/v1";
/// Artifact kind discriminator.
pub const EDITION_DELTA_KIND: &str = "m209-s03-edition-delta";
/// Task discriminator of this artifact.
pub const EDITION_DELTA_TASK: &str = "T04";
/// The frozen T01 declaration whose edition inventory this leg reconciles.
pub const T01_EVIDENCE_RELATIVE_PATH: &str =
    "prd/migration/rust-evidence/m209-s03-family-denominator.json";
/// Declared bound on the reported top-N windows by absolute amends change.
pub const EDITION_DELTA_TOP_N: usize = 10;

/// Fail-closed codes this mode can emit. The node contract asserts its
/// documented code block equals this array, which is also emitted verbatim as
/// the artifact's `fail_closed_codes` field, so a code can never be documented
/// without being reachable and never be reachable without being documented.
pub const EDITION_DELTA_FAIL_CLOSED_CODES: [&str; 7] = [
    "input_absent",
    "input_hash_mismatch",
    "family_count_unsupported",
    "zero_denominator",
    "non_ascii_evidence",
    "raw_text_leak",
    "edition_dir_unreadable",
];

/// One edition of the named chain, as measured by the admitted runtime. Every
/// field is a count or a validated categorical label; no link destination, no
/// link text and no XML byte is carried.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionDeltaRow {
    pub edition_number: u32,
    pub revision_label: String,
    pub hyperlink_count: u64,
    pub classified_count: u64,
    pub amends_count: u64,
    pub cites_count: u64,
    pub implements_count: u64,
    pub unknown_count: u64,
    /// FNV-1a diagnostic digest over the canonical summary tuple. It is a
    /// determinism fingerprint, never integrity or authority evidence (D424).
    pub digest: String,
}

/// One consecutive-edition delta window: the admitted `delta()` of two adjacent
/// editions of the sorted summary list.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionWindowRow {
    pub from_edition: u32,
    pub to_edition: u32,
    pub revision_from: String,
    pub revision_to: String,
    pub amends_change: i64,
    pub cites_change: i64,
    pub implements_change: i64,
    pub unknown_change: i64,
}

/// Sum of every declared window's change, per classification.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionDeltaAggregate {
    pub amends_change: i64,
    pub cites_change: i64,
    pub implements_change: i64,
    pub unknown_change: i64,
}

/// The whole edition-delta leg of R070.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EditionDeltaEvidence {
    pub edition_directory_relative_path: String,
    pub editions_total: u64,
    pub editions_processed: u64,
    pub editions_unreadable: u64,
    pub editions_unparsed_filename: u64,
    pub windows_total: u64,
    pub edition_dir_files_total: u64,
    pub edition_dir_bytes_total: u64,
    pub edition_dir_listing_sha256: String,
    pub t01_editions_total: u64,
    pub t01_edition_matching: u64,
    pub t01_input_sha256: String,
    pub chain_digest: String,
    pub rows: Vec<EditionDeltaRow>,
    pub windows: Vec<EditionWindowRow>,
    pub aggregate: EditionDeltaAggregate,
    pub top_amends_windows: Vec<EditionWindowRow>,
    pub inputs: Vec<AmendsInputPin>,
}

/// FNV-1a (64-bit) over bytes. A deterministic diagnostic fingerprint used only
/// to prove determinism by byte compare; it is not an integrity digest and not
/// authority evidence, and the artifact says so.
fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3_u64);
    }
    hash
}

/// Canonical tuple the per-edition digest is taken over. Field order and
/// separators are fixed here, so a digest change means a summary change.
fn edition_digest_tuple(summary: &EditionSummary) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}|{}|{}",
        summary.edition_number,
        summary.revision_date,
        summary.hyperlink_count,
        summary.classified_count,
        summary.amends_count,
        summary.cites_count,
        summary.implements_count,
        summary.unknown_count
    )
}

fn edition_summary_digest(summary: &EditionSummary) -> String {
    format!(
        "fnv1a64:{:016x}",
        fnv1a64(edition_digest_tuple(summary).as_bytes())
    )
}

/// Chain digest over the ordered per-edition digests: one fingerprint for the
/// whole walk, so `--check` can prove determinism without a second walk.
fn edition_chain_digest(rows: &[EditionDeltaRow]) -> String {
    let mut stream = String::new();
    for row in rows {
        stream.push_str(&row.digest);
        stream.push('\n');
    }
    format!("fnv1a64:{:016x}", fnv1a64(stream.as_bytes()))
}

/// Reads one flat field out of a named top-level object of a compact artifact.
/// Brace- and string-aware, so a nested object never truncates the scan and a
/// field of the first family can never be mistaken for a field of the chain
/// block.
fn object_body<'a>(text: &'a str, block: &str) -> Option<&'a str> {
    let marker = format!("\"{block}\":{{");
    let start = text.find(&marker)? + marker.len();
    let bytes = text.as_bytes();
    let mut depth = 0usize;
    let mut in_string = false;
    let mut escaped = false;
    let mut index = start;
    while index < bytes.len() {
        let byte = bytes[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
        } else if byte == b'"' {
            in_string = true;
        } else if byte == b'{' {
            depth += 1;
        } else if byte == b'}' {
            if depth == 0 {
                return Some(&text[start..index]);
            }
            depth -= 1;
        }
        index += 1;
    }
    None
}

/// The admitted edition files of one chain directory, listed read-only.
struct EditionListing {
    /// File names that parse as an edition, sorted, and therefore reachable by
    /// the admitted walk.
    names: Vec<String>,
    /// File names the filter admits but `parse_edition_filename` rejects.
    unparsed: u64,
}

impl EditionListing {
    fn parsed_total(&self) -> u64 {
        self.names.len() as u64
    }

    fn total(&self) -> u64 {
        self.names.len() as u64 + self.unparsed
    }
}

/// Lists the admitted edition files of one chain directory read-only.
///
/// The filter mirrors `multi_edition::process_editions_directory` exactly: an
/// immediate child whose extension is `xml` and whose name starts with
/// `edition-`. A file whose name does not parse as an edition is counted as
/// `edition_unparsed_filename` and is never read.
fn list_edition_files(directory: &Path) -> Result<EditionListing, AmendmentProvenanceError> {
    let display = directory.display().to_string();
    let unreadable = || AmendmentProvenanceError::EditionDirUnreadable {
        path: display.clone(),
    };
    let entries = fs::read_dir(directory).map_err(|_| unreadable())?;
    let mut candidates: Vec<String> = Vec::new();
    for entry in entries {
        let entry = entry.map_err(|_| unreadable())?;
        let path = entry.path();
        if !path.is_file() || !path.extension().is_some_and(|ext| ext == "xml") {
            continue;
        }
        let name = entry.file_name().to_string_lossy().into_owned();
        if !name.starts_with(EDITION_FILE_PREFIX) {
            continue;
        }
        candidates.push(name);
    }
    candidates.sort();
    let mut names = Vec::with_capacity(candidates.len());
    let mut unparsed = 0u64;
    for name in candidates {
        if parse_edition_filename(&name).is_none() {
            unparsed += 1;
        } else {
            names.push(name);
        }
    }
    Ok(EditionListing { names, unparsed })
}

/// Re-derives the edition-delta leg from the live repository: the declared
/// inventory from the directory listing, the walk from the unmodified admitted
/// runtime, the consecutive windows, and the determinism digests.
pub fn collect_edition_delta(
    repo_root: &Path,
    export_dir: &str,
) -> Result<EditionDeltaEvidence, AmendmentProvenanceError> {
    let export_root_relative = export_root_relative_path(export_dir);
    let export_root = resolve_export_root(repo_root, export_dir);
    let chain_relative = join_relative(&export_root_relative, EDITION_DIR_TAIL);
    let chain_dir = export_root.join(EDITION_DIR_TAIL);

    // 1. The declared inventory, re-derived from the live directory listing.
    let listing = list_edition_files(&chain_dir)?;
    let editions_total = listing.total();
    let editions_unparsed_filename = listing.unparsed;
    if editions_total == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: CHAIN_ID.to_owned(),
        });
    }
    let inventory = inventory_directory(&chain_dir).map_err(|_| {
        AmendmentProvenanceError::EditionDirUnreadable {
            path: chain_relative.clone(),
        }
    })?;
    if inventory.files_total != editions_total {
        return Err(family_unsupported(
            CHAIN_ID,
            "the directory subtree and the admitted edition filter disagree on the edition count",
        ));
    }

    // 2. The admitted runtime walks the chain, unmodified.
    let summaries = process_editions_directory(&chain_dir);
    let editions_processed = summaries.len() as u64;
    if editions_processed > listing.parsed_total() {
        return Err(family_unsupported(
            CHAIN_ID,
            "the admitted walk returned more summaries than the listing declares",
        ));
    }
    // An edition the runtime could not read is a declared count, never a silent
    // gap. It is the residual of the parsed listing, corroborated by an
    // independent readability probe (an open, not a second payload read).
    let editions_unreadable = listing.parsed_total() - editions_processed;
    let unreadable_probe = listing
        .names
        .iter()
        .filter(|name| fs::File::open(chain_dir.join(name)).is_err())
        .count() as u64;
    if unreadable_probe != editions_unreadable {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared unreadable count does not reproduce the independent readability probe",
        ));
    }

    // 3. Per-edition rows plus the determinism block.
    let mut rows = Vec::with_capacity(summaries.len());
    let mut previous_number: Option<u32> = None;
    for summary in &summaries {
        if summary.revision_date.is_empty() || !is_allowed_key_token(&summary.revision_date) {
            return Err(AmendmentProvenanceError::RawTextLeak {
                detail: "an edition revision label is outside the count-only token rule".to_owned(),
            });
        }
        if previous_number.is_some_and(|previous| summary.edition_number <= previous) {
            return Err(family_unsupported(
                CHAIN_ID,
                "the admitted walk is not ordered by a strictly increasing edition number",
            ));
        }
        previous_number = Some(summary.edition_number);
        rows.push(EditionDeltaRow {
            edition_number: summary.edition_number,
            revision_label: summary.revision_date.clone(),
            hyperlink_count: summary.hyperlink_count as u64,
            classified_count: summary.classified_count as u64,
            amends_count: summary.amends_count as u64,
            cites_count: summary.cites_count as u64,
            implements_count: summary.implements_count as u64,
            unknown_count: summary.unknown_count as u64,
            digest: edition_summary_digest(summary),
        });
    }

    // 4. Consecutive delta windows over the sorted summary list.
    let mut windows = Vec::with_capacity(summaries.len().saturating_sub(1));
    for pair in summaries.windows(2) {
        let change = delta(&pair[0], &pair[1]);
        windows.push(EditionWindowRow {
            from_edition: pair[0].edition_number,
            to_edition: pair[1].edition_number,
            revision_from: pair[0].revision_date.clone(),
            revision_to: pair[1].revision_date.clone(),
            amends_change: change.amends_change,
            cites_change: change.cites_change,
            implements_change: change.implements_change,
            unknown_change: change.unknown_change,
        });
    }
    let windows_total = windows.len() as u64;
    let aggregate = EditionDeltaAggregate {
        amends_change: windows.iter().map(|window| window.amends_change).sum(),
        cites_change: windows.iter().map(|window| window.cites_change).sum(),
        implements_change: windows.iter().map(|window| window.implements_change).sum(),
        unknown_change: windows.iter().map(|window| window.unknown_change).sum(),
    };

    // Bounded declared top-N by absolute amends change, ties broken by the
    // earlier window so the order is total and reproducible.
    let mut order: Vec<usize> = (0..windows.len()).collect();
    order.sort_by(|left, right| {
        windows[*right]
            .amends_change
            .unsigned_abs()
            .cmp(&windows[*left].amends_change.unsigned_abs())
            .then_with(|| {
                windows[*left]
                    .from_edition
                    .cmp(&windows[*right].from_edition)
            })
    });
    let top_amends_windows: Vec<EditionWindowRow> = order
        .into_iter()
        .take(EDITION_DELTA_TOP_N)
        .map(|index| windows[index].clone())
        .collect();

    // 5. The frozen T01 declaration must still reconcile with the live listing,
    //    so the 118-edition inventory is a measurement and not a carried number.
    let t01_path = repo_root.join(T01_EVIDENCE_RELATIVE_PATH);
    let t01_text = fs::read_to_string(&t01_path)
        .map_err(|_| input_absent(T01_EVIDENCE_RELATIVE_PATH.to_owned()))?;
    let chain_body = object_body(&t01_text, "chain").ok_or_else(|| {
        family_unsupported(
            "m209-s03-family-denominator",
            "the T01 artifact declares no chain block",
        )
    })?;
    let t01_editions_total = flat_integer(chain_body, "editions_total")
        .and_then(|value| u64::try_from(value).ok())
        .ok_or_else(|| {
            family_unsupported(
                "m209-s03-family-denominator",
                "the T01 chain block declares no editions_total",
            )
        })?;
    let t01_edition_matching = flat_integer(chain_body, "edition_matching")
        .and_then(|value| u64::try_from(value).ok())
        .ok_or_else(|| {
            family_unsupported(
                "m209-s03-family-denominator",
                "the T01 chain block declares no edition_matching count",
            )
        })?;
    let t01_chain_sha256 = match flat_field(chain_body, "input_sha256") {
        Some(FlatValue::Str(value)) => value.to_owned(),
        _ => {
            return Err(family_unsupported(
                "m209-s03-family-denominator",
                "the T01 chain block declares no listing digest",
            ))
        }
    };
    if t01_editions_total != editions_total || t01_edition_matching != editions_total {
        return Err(family_unsupported(
            CHAIN_ID,
            "the live edition inventory no longer reproduces the frozen T01 declaration",
        ));
    }
    if t01_chain_sha256 != inventory.listing_sha256 {
        return Err(AmendmentProvenanceError::InputHashMismatch {
            family_id: CHAIN_ID.to_owned(),
            path: chain_relative.clone(),
            detail: "the live edition-directory listing digest differs from the frozen T01 pin"
                .to_owned(),
        });
    }
    let t01_input_sha256 = format!("sha256:{}", sha256_hex(t01_text.as_bytes()));

    let inputs = vec![pin_of(
        "t01_family_denominator",
        &t01_path,
        T01_EVIDENCE_RELATIVE_PATH.to_owned(),
    )?];
    let chain_digest = edition_chain_digest(&rows);

    Ok(EditionDeltaEvidence {
        edition_directory_relative_path: chain_relative,
        editions_total,
        editions_processed,
        editions_unreadable,
        editions_unparsed_filename,
        windows_total,
        edition_dir_files_total: inventory.files_total,
        edition_dir_bytes_total: inventory.bytes_total,
        edition_dir_listing_sha256: inventory.listing_sha256,
        t01_editions_total,
        t01_edition_matching,
        t01_input_sha256,
        chain_digest,
        rows,
        windows,
        aggregate,
        top_amends_windows,
        inputs,
    })
}

/// Fails closed on any inventory that does not reconcile, any digest that does
/// not cover its own rows, and any window that does not reproduce the admitted
/// delta of its own two editions.
pub fn validate_edition_delta(
    evidence: &EditionDeltaEvidence,
) -> Result<(), AmendmentProvenanceError> {
    if evidence.editions_total == 0 || evidence.editions_processed == 0 {
        return Err(AmendmentProvenanceError::ZeroDenominator {
            family_id: CHAIN_ID.to_owned(),
        });
    }
    check_repo_relative(&evidence.edition_directory_relative_path)?;
    if !evidence
        .edition_directory_relative_path
        .ends_with(EDITION_DIR_TAIL)
    {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared edition directory is not the named chain directory",
        ));
    }
    if evidence.edition_dir_files_total != evidence.editions_total {
        return Err(family_unsupported(
            CHAIN_ID,
            "the walked subtree total does not reproduce the declared edition total",
        ));
    }
    if evidence.editions_processed
        + evidence.editions_unreadable
        + evidence.editions_unparsed_filename
        != evidence.editions_total
    {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared edition counts do not reconcile to the declared edition total",
        ));
    }
    if evidence.t01_editions_total != evidence.editions_total
        || evidence.t01_edition_matching != evidence.editions_total
    {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared edition total does not reconcile with the frozen T01 declaration",
        ));
    }
    if evidence.rows.len() as u64 != evidence.editions_processed {
        return Err(family_unsupported(
            CHAIN_ID,
            "the per-edition rows do not cover the declared processed total",
        ));
    }
    if evidence.windows_total != evidence.editions_processed - 1
        || evidence.windows.len() as u64 != evidence.windows_total
    {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared windows are not one fewer than the processed editions",
        ));
    }

    // Every window must reproduce the ordered pair of the rows around it, so a
    // window can never be detached from the editions it claims to compare.
    for (index, window) in evidence.windows.iter().enumerate() {
        let from = evidence
            .rows
            .get(index)
            .ok_or_else(|| family_unsupported(CHAIN_ID, "a window has no preceding edition row"))?;
        let to = evidence
            .rows
            .get(index + 1)
            .ok_or_else(|| family_unsupported(CHAIN_ID, "a window has no following edition row"))?;
        if window.from_edition != from.edition_number
            || window.to_edition != to.edition_number
            || window.revision_from != from.revision_label
            || window.revision_to != to.revision_label
        {
            return Err(family_unsupported(
                CHAIN_ID,
                "a declared window does not name its own two adjacent editions",
            ));
        }
        let expected_amends = to.amends_count as i64 - from.amends_count as i64;
        let expected_cites = to.cites_count as i64 - from.cites_count as i64;
        let expected_implements = to.implements_count as i64 - from.implements_count as i64;
        let expected_unknown = to.unknown_count as i64 - from.unknown_count as i64;
        if window.amends_change != expected_amends
            || window.cites_change != expected_cites
            || window.implements_change != expected_implements
            || window.unknown_change != expected_unknown
        {
            return Err(family_unsupported(
                CHAIN_ID,
                "a declared window does not reproduce the counted change of its two editions",
            ));
        }
    }

    // The aggregate is the sum of the windows, and the top-N is a bounded,
    // ordered prefix of exactly them.
    let aggregate = EditionDeltaAggregate {
        amends_change: evidence.windows.iter().map(|w| w.amends_change).sum(),
        cites_change: evidence.windows.iter().map(|w| w.cites_change).sum(),
        implements_change: evidence.windows.iter().map(|w| w.implements_change).sum(),
        unknown_change: evidence.windows.iter().map(|w| w.unknown_change).sum(),
    };
    if evidence.aggregate != aggregate {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared aggregate is not the sum of the declared windows",
        ));
    }
    let expected_top = evidence.windows.len().min(EDITION_DELTA_TOP_N);
    if evidence.top_amends_windows.len() != expected_top {
        return Err(family_unsupported(
            CHAIN_ID,
            "the declared top-N is not a bounded prefix of the declared windows",
        ));
    }

    // Determinism block: every per-edition digest must cover its own row, and
    // the chain digest must cover the ordered per-edition digests.
    for row in &evidence.rows {
        let tuple = format!(
            "{}|{}|{}|{}|{}|{}|{}|{}",
            row.edition_number,
            row.revision_label,
            row.hyperlink_count,
            row.classified_count,
            row.amends_count,
            row.cites_count,
            row.implements_count,
            row.unknown_count
        );
        let expected = format!("fnv1a64:{:016x}", fnv1a64(tuple.as_bytes()));
        if row.digest != expected {
            return Err(family_unsupported(
                CHAIN_ID,
                "a per-edition digest does not cover its own row",
            ));
        }
        if !is_allowed_key_token(&row.revision_label) {
            return Err(AmendmentProvenanceError::RawTextLeak {
                detail: "an edition revision label is outside the count-only token rule".to_owned(),
            });
        }
    }
    if evidence.chain_digest != edition_chain_digest(&evidence.rows) {
        return Err(family_unsupported(
            CHAIN_ID,
            "the chain digest does not cover the ordered per-edition digests",
        ));
    }
    Ok(())
}

/// Denominator and metric definition prose for the edition-delta leg.
const EDITION_DELTA_COUNT_BASIS: &str = "The declared inventory is re-derived live on every run from the immediate children of the named chain edition directory that the admitted runtime admits: extension xml and name prefix edition-. editions_processed is the number of summaries the unmodified admitted multi_edition::process_editions_directory returned, editions_unreadable is the residual of the parsed listing, corroborated by an independent open probe, and editions_unparsed_filename counts admitted names whose edition number and revision do not parse. windows_total is editions_processed minus one, because the leg reports one consecutive delta per adjacent pair of the sorted summary list. The per-edition digest is an FNV-1a fingerprint over the fixed tuple (edition_number, revision label, hyperlink, classified, amends, cites, implements, unknown counts) and the chain digest is the same fingerprint over the ordered per-edition digests; both are determinism fingerprints used to prove re-render equality by byte compare, never integrity or authority digests. Nothing here is typed by hand and no zero denominator is a measurement.";

/// Claim bounds carried by the edition-delta artifact.
const EDITION_DELTA_NON_CLAIMS: [&str; 9] = [
    "This leg measures link-topology deltas of the admitted multi-edition runtime over the one multi-edition chain of the corpus; it is not a normative text delta, not commencement evidence and not a determination that any provision became applicable.",
    "The parser counts are link classifications of the admitted runtime, not legal effect: an amends, cites, implements or unknown count is a classification outcome and never an amendment, an obligation or an applicability finding.",
    "This leg is scoped to the named cc:44-fz chain and its 118 admitted editions; it is not every-edition coverage beyond the reconciled counts and it is not another chain.",
    "No corpus text is copied into this artifact: no XML bytes, no article text, no document titles, no link destinations, no link text, no offline URIs and no raw relation tooltips; only counts, edition numbers, revision labels, repository-relative paths, byte counts, sha256 pins and named categorical codes.",
    "The edition delta is bounded supporting evidence for the named chain only and does not close R070: no promotion gate is promoted, satisfied or moved off unsatisfied (D416).",
    "The frozen M201 R070 proof gate and the three frozen M201 pins are not widened, reopened or restated here, and the declared M208 startup surfaces stay absent.",
    "A zero denominator is not a measurement and fails closed as zero_denominator; no declared total may be presented as a measurement when its counts do not reconcile to it (D552).",
    "No new runtime vocabulary is minted: no effect-selector token, no transitional-resolver runtime, no evidence-anchor and no legislative-effect identifier (D216).",
    "The declared top-N by absolute amends change is a bounded report of the largest absolute windows, not a ranking of legal significance and not a claim about the remaining windows.",
];

/// Canonical compact render. Fixed top-level key order, no timestamps, ASCII by
/// construction: every scalar is a count, a validated categorical label, a
/// repository-relative path or a declared digest (D424).
pub fn render_edition_delta(evidence: &EditionDeltaEvidence) -> String {
    let mut writer = ObjectWriter::new();
    writer.string("schema", EDITION_DELTA_SCHEMA);
    writer.number("schema_version", 4);
    writer.string("kind", EDITION_DELTA_KIND);
    writer.string("milestone", MILESTONE);
    writer.string("slice", SLICE);
    writer.string("task", EDITION_DELTA_TASK);
    writer.string("lifecycle", LIFECYCLE);
    writer.boolean("authoritative", false);
    writer.string("requirement_id", REQUIREMENT_ID);
    writer.string("disposition", DISPOSITION);
    writer.string("disposition_decision", DISPOSITION_DECISION);
    writer.boolean("count_only", true);
    writer.boolean("ascii_only", true);
    writer.string("count_basis", EDITION_DELTA_COUNT_BASIS);

    writer.key("chain");
    {
        let mut entry = ObjectWriter::new();
        entry.string("chain_id", CHAIN_ID);
        entry.string(
            "edition_directory_relative_path",
            &evidence.edition_directory_relative_path,
        );
        entry.string(
            "admitted_runtime",
            "multi_edition::process_editions_directory",
        );
        entry.string(
            "delta_metric",
            "multi_edition::delta of adjacent sorted editions",
        );
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("denominator");
    {
        let mut entry = ObjectWriter::new();
        entry.number("editions_total", evidence.editions_total);
        entry.number("editions_processed", evidence.editions_processed);
        entry.number("editions_unreadable", evidence.editions_unreadable);
        entry.number(
            "editions_unparsed_filename",
            evidence.editions_unparsed_filename,
        );
        entry.number("windows_total", evidence.windows_total);
        entry.number("edition_dir_files_total", evidence.edition_dir_files_total);
        entry.number("edition_dir_bytes_total", evidence.edition_dir_bytes_total);
        entry.string(
            "edition_dir_listing_sha256",
            &evidence.edition_dir_listing_sha256,
        );
        entry.number("t01_editions_total", evidence.t01_editions_total);
        entry.number("t01_edition_matching", evidence.t01_edition_matching);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("determinism");
    {
        let mut entry = ObjectWriter::new();
        entry.string("per_edition_digest", "fnv1a64 over the fixed summary tuple");
        entry.string(
            "chain_digest_basis",
            "fnv1a64 over the ordered per-edition digests",
        );
        entry.string("chain_digest", &evidence.chain_digest);
        entry.boolean("diagnostic_only", true);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("aggregate");
    {
        let mut entry = ObjectWriter::new();
        entry.signed("amends_change", evidence.aggregate.amends_change);
        entry.signed("cites_change", evidence.aggregate.cites_change);
        entry.signed("implements_change", evidence.aggregate.implements_change);
        entry.signed("unknown_change", evidence.aggregate.unknown_change);
        writer.buffer.push_str(&entry.finish());
    }

    writer.key("windows");
    writer.buffer.push('[');
    for (index, window) in evidence.windows.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        writer.buffer.push_str(&render_window(window));
    }
    writer.buffer.push(']');

    writer.key("top_amends_windows");
    writer.buffer.push('[');
    for (index, window) in evidence.top_amends_windows.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        writer.buffer.push_str(&render_window(window));
    }
    writer.buffer.push(']');

    writer.key("editions");
    writer.buffer.push('[');
    for (index, row) in evidence.rows.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.number("edition_number", u64::from(row.edition_number));
        entry.string("revision_label", &row.revision_label);
        entry.number("hyperlink_count", row.hyperlink_count);
        entry.number("classified_count", row.classified_count);
        entry.number("amends_count", row.amends_count);
        entry.number("cites_count", row.cites_count);
        entry.number("implements_count", row.implements_count);
        entry.number("unknown_count", row.unknown_count);
        entry.string("digest", &row.digest);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.key("inputs");
    writer.buffer.push('[');
    for (index, pin) in evidence.inputs.iter().enumerate() {
        if index > 0 {
            writer.buffer.push(',');
        }
        let mut entry = ObjectWriter::new();
        entry.string("input_id", &pin.input_id);
        entry.string("relative_path", &pin.relative_path);
        entry.number("input_bytes", pin.input_bytes);
        entry.string("input_sha256", &pin.input_sha256);
        writer.buffer.push_str(&entry.finish());
    }
    writer.buffer.push(']');

    writer.fixed_strings("fail_closed_codes", &EDITION_DELTA_FAIL_CLOSED_CODES);
    writer.fixed_strings("non_claims", &EDITION_DELTA_NON_CLAIMS);
    writer.finish()
}

/// One delta window, rendered identically in both window blocks.
fn render_window(window: &EditionWindowRow) -> String {
    let mut entry = ObjectWriter::new();
    entry.number("from_edition", u64::from(window.from_edition));
    entry.number("to_edition", u64::from(window.to_edition));
    entry.string("revision_from", &window.revision_from);
    entry.string("revision_to", &window.revision_to);
    entry.signed("amends_change", window.amends_change);
    entry.signed("cites_change", window.cites_change);
    entry.signed("implements_change", window.implements_change);
    entry.signed("unknown_change", window.unknown_change);
    entry.finish()
}

/// Count-only stderr heartbeat for the edition-delta leg.
pub fn edition_delta_heartbeat(evidence: &EditionDeltaEvidence) -> String {
    format!(
        "edition-chain={} processed={} unreadable={} unparsed={} windows={} drift=0",
        evidence.editions_total,
        evidence.editions_processed,
        evidence.editions_unreadable,
        evidence.editions_unparsed_filename,
        evidence.windows_total
    )
}

fn diagnose_edition_delta_check_drift(
    tracked: &[u8],
    evidence: &EditionDeltaEvidence,
) -> AmendmentProvenanceError {
    if tracked.iter().any(|byte| *byte >= 0x80) {
        return AmendmentProvenanceError::NonAsciiEvidence {
            detail: "tracked artifact is not ascii".to_owned(),
        };
    }
    let tracked_text = String::from_utf8_lossy(tracked);
    for pin in &evidence.inputs {
        if !tracked_text.contains(&pin.input_sha256) {
            return AmendmentProvenanceError::InputHashMismatch {
                family_id: pin.input_id.clone(),
                path: pin.relative_path.clone(),
                detail: "tracked pin differs from the live input pin".to_owned(),
            };
        }
    }
    if !tracked_text.contains(&evidence.chain_digest) {
        return AmendmentProvenanceError::InputHashMismatch {
            family_id: CHAIN_ID.to_owned(),
            path: evidence.edition_directory_relative_path.clone(),
            detail: "tracked chain digest differs from the live chain digest".to_owned(),
        };
    }
    family_unsupported(
        "<artifact>",
        "artifact bytes differ from the live render while every declared pin matches",
    )
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

    #[test]
    fn act_identity_is_derived_from_title_and_law_number_only() {
        assert_eq!(
            act_date_from_title("Федеральный закон от 02.07.2013 N 188-ФЗ \"О внесении\""),
            Some("2013-07-02".to_owned())
        );
        assert_eq!(act_date_from_title("Постановление без даты"), None);
        assert_eq!(
            act_number_from_law_number("N 188-ФЗ"),
            Some("188".to_owned())
        );
        assert_eq!(act_number_from_law_number("Постановлением"), None);
        assert_eq!(act_number_from_law_number(""), None);
    }

    #[test]
    fn first_statya_reference_reads_full_word_locators_only() {
        assert_eq!(
            first_statya_reference("статье 8: а) в части 14").as_deref(),
            Some("8")
        );
        assert_eq!(
            first_statya_reference("в абзаце втором подпункта 31 статьи 5").as_deref(),
            Some("5")
        );
        assert_eq!(
            first_statya_reference("статью 110.1").as_deref(),
            Some("110.1")
        );
        assert_eq!(
            first_statya_reference("статьями 93, 95").as_deref(),
            Some("93")
        );
        assert_eq!(first_statya_reference("закон"), None);
        assert_eq!(first_statya_reference("статью"), None);
    }

    #[test]
    fn registry_bindings_are_scoped_to_the_chain_needle() {
        let text = concat!(
            "bindings:\n",
            "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"93\", cc: cc:44-fz:statya-93}\n",
            "- {path_needle: n-44-fz, level: statya, number: \"31\", cc: n-44-fz:statya-31}\n",
            "  - {path_needle: law_2024-12-26_484-fz, authority: federal, enactment_date: \"2024-12-26\"}\n",
        );
        let bindings = parse_registry_bindings(text).expect("bindings");
        assert_eq!(bindings.len(), 1);
        assert_eq!(
            bindings
                .get(&("statya".to_owned(), "93".to_owned()))
                .map(String::as_str),
            Some("cc:44-fz:statya-93")
        );
    }

    #[test]
    fn duplicate_registry_identity_fails_closed() {
        let text = concat!(
            "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"93\", cc: cc:44-fz:statya-93}\n",
            "- {path_needle: law_2013-04-05_44-fz, level: statya, number: \"93\", cc: cc:44-fz:statya-93-again}\n",
        );
        assert!(matches!(
            parse_registry_bindings(text),
            Err(AmendmentProvenanceError::FamilyCountUnsupported { .. })
        ));
    }

    #[test]
    fn amends_code_sets_are_documented_ascii_and_nested() {
        for code in AMENDS_PROVISION_FAIL_CLOSED_CODES {
            assert!(code.is_ascii());
            assert!(is_allowed_key_token(code), "code shape: {code}");
        }
        for code in AMENDS_PROVISION_REASON_CODES {
            assert!(AMENDS_PROVISION_FAIL_CLOSED_CODES.contains(&code));
        }
        assert_eq!(AMENDS_PROVISION_REASON_CODES.len(), 7);
        assert_eq!(AMENDS_PROVISION_FAIL_CLOSED_CODES.len(), 13);
        assert!(!AMENDS_EXPORT_PATTERN.is_empty());
    }

    #[test]
    fn an_unjustified_outcome_carries_its_own_reason_code() {
        let error = reason_unsupported("no-export-file", "counts do not justify the outcome");
        assert_eq!(error.code(), Some("no-export-file"));
        assert_eq!(error.exit_code(), 6);
        assert!(error.cli_line().starts_with("drift=no-export-file"));
        let flat = flat_integer(
            "{\"document_key\": 148498, \"bank\": \"LAW\"}",
            "document_key",
        );
        assert_eq!(flat, Some(148498));
        assert_eq!(
            flat_integer("{\"document_key\": \"text\"}", "document_key"),
            None
        );
        assert_eq!(flat_integer("{\"other\": 1}", "document_key"), None);
    }

    // ----------------------------------------------------------------------
    // T03 commencement guards
    // ----------------------------------------------------------------------

    /// A boundary-shaped fixture that reproduces the live partition exactly:
    /// one filled named-chain slot plus the T02 amending-act denominator.
    fn commencement_fixture() -> CommencementTransitionEvidence {
        let mut by_evidence_class = seed_counts(&COMMENCEMENT_EVIDENCE_CLASSES);
        let mut by_slot_verdict = seed_counts(&COMMENCEMENT_SLOT_VERDICTS);
        let mut by_reason_code = seed_counts(&COMMENCEMENT_REASON_CODES);
        let mut by_transitional = seed_counts(&COMMENCEMENT_TRANSITIONAL_VALUES);
        let mut slots = Vec::new();
        slots.push(CommencementSlot {
            document_key: 508_812,
            slot_kind: "named-chain",
            act_number: "44".to_owned(),
            act_date: "2013-04-05".to_owned(),
            act_text_admitted: true,
            evidence_class: "hypothesized_from_oracle_diff".to_owned(),
            slot_verdict: "slot-filled-not-proven",
            reason_code: "no-legislative-commencement-source",
            transitional: "explicitly_absent",
            commencement_rule_ref: "rec:commencement:484-93:hypothesized".to_owned(),
            transitional_basis_id: COMMENCEMENT_TRANSITIONAL_JUSTIFICATION_ID.to_owned(),
        });
        *by_evidence_class
            .get_mut("hypothesized_from_oracle_diff")
            .unwrap() += 1;
        *by_slot_verdict.get_mut("slot-filled-not-proven").unwrap() += 1;
        *by_reason_code
            .get_mut("no-legislative-commencement-source")
            .unwrap() += 1;
        *by_transitional.get_mut("explicitly_absent").unwrap() += 1;
        for index in 0..EXPECTED_LAYER1_AMENDING_ACTS {
            let admitted = index + 1 < EXPECTED_LAYER1_AMENDING_ACTS;
            let reason = if admitted {
                "no-legislative-commencement-source"
            } else {
                "act-text-not-admitted"
            };
            slots.push(CommencementSlot {
                document_key: 100_000 + index as i64,
                slot_kind: "amending-act",
                act_number: (index + 1).to_string(),
                act_date: "2014-01-01".to_owned(),
                act_text_admitted: admitted,
                evidence_class: "absent".to_owned(),
                slot_verdict: "explicitly-absent",
                reason_code: reason,
                transitional: "unresolved",
                commencement_rule_ref: String::new(),
                transitional_basis_id: String::new(),
            });
            *by_evidence_class.get_mut("absent").unwrap() += 1;
            *by_slot_verdict.get_mut("explicitly-absent").unwrap() += 1;
            *by_reason_code.get_mut(reason).unwrap() += 1;
            *by_transitional.get_mut("unresolved").unwrap() += 1;
        }
        CommencementTransitionEvidence {
            admission_gate: CommencementAdmissionGate {
                m208_s03_admission: "not-adopted".to_owned(),
                m208_s03_owner_admission_ref: "none".to_owned(),
                m208_s03_runtime_work: "not-started".to_owned(),
                m208_s04_admission: "not-adopted".to_owned(),
                m208_s04_owner_admission_ref: "none".to_owned(),
                m208_s04_runtime_work: "not-started".to_owned(),
                m207_human_pilot: "absent",
                m207_c4_operational_acceptance: "non-pass".to_owned(),
                m207_c4_rate_status: "not-measured",
                m207_c4_protocol_relative_path: M207_C4_PROTOCOL_RELATIVE_PATH.to_owned(),
                m207_c4_receipt_relative_path: M207_C4_RECEIPT_RELATIVE_PATH.to_owned(),
            },
            slots_total: EXPECTED_LAYER1_RECORDS_TOTAL,
            named_chain_slots: 1,
            amending_act_slots: EXPECTED_LAYER1_AMENDING_ACTS,
            t02_layer1_records_total: EXPECTED_LAYER1_RECORDS_TOTAL,
            t02_layer1_amending_acts: EXPECTED_LAYER1_AMENDING_ACTS,
            t02_amends_edges_total: EXPECTED_AMENDS_EDGES_TOTAL,
            t02_input_sha256: format!("sha256:{NIST_ABC}"),
            frozen_gate_evidence_class: "hypothesized_from_oracle_diff".to_owned(),
            frozen_gate_commencement_rule_ref: "rec:commencement:484-93:hypothesized".to_owned(),
            frozen_gate_transitional: "explicitly_absent".to_owned(),
            inputs: vec![AmendsInputPin {
                input_id: "layer1_manifest".to_owned(),
                relative_path: "consru_export/consru_export/manifest.jsonl".to_owned(),
                input_bytes: 12,
                input_sha256: format!("sha256:{NIST_ABC}"),
            }],
            slots,
            by_evidence_class,
            by_slot_verdict,
            by_reason_code,
            by_transitional,
            class_matched_ids: Vec::new(),
        }
    }

    #[test]
    fn the_commencement_fixture_is_a_valid_boundary() {
        let evidence = commencement_fixture();
        validate_commencement_transition(&evidence).expect("a boundary-shaped fixture validates");
        let rendered = render_commencement_transition(&evidence);
        assert!(rendered.is_ascii());
        assert!(!rendered.contains("\"legislative\""));
        for token in MINTED_VOCABULARY_TOKENS {
            assert!(
                !rendered.contains(token),
                "the render must not mint {token}"
            );
        }
        assert_eq!(
            commencement_heartbeat(&evidence),
            "commencement=122 named=1 amending=121 filled=1 absent=121 class_matched=0 drift=0"
        );
        assert!(validate_commencement_transition(&evidence).is_ok());
        assert!(ensure_ascii_and_clean(&rendered).is_ok());
    }

    #[test]
    fn a_legislative_slot_value_fails_closed_as_a_legislative_upgrade_attempt() {
        let mut evidence = commencement_fixture();
        evidence.slots[0].evidence_class = "legislative".to_owned();
        let error = validate_commencement_transition(&evidence)
            .expect_err("a legislative value must not be emitted");
        assert_eq!(error.code(), Some("legislative_upgrade_attempt"));
        assert_eq!(error.exit_code(), 6);
    }

    #[test]
    fn a_minted_m208_identifier_fails_closed_as_vocabulary_minted() {
        for token in MINTED_VOCABULARY_TOKENS {
            let mut evidence = commencement_fixture();
            evidence.slots[1].slot_kind = token;
            let error = validate_commencement_transition(&evidence)
                .expect_err("a minted identifier must fail closed");
            assert_eq!(error.code(), Some("vocabulary_minted"), "token {token}");
        }
    }

    #[test]
    fn a_date_or_a_file_name_as_a_rule_reference_fails_closed() {
        for value in [
            "2013-04-05",
            "law_2013-04-05_44-fz_rev-unknown_1a599b98.xml",
            "law_2013-04-05_44-fz",
        ] {
            let mut evidence = commencement_fixture();
            evidence.slots[0].commencement_rule_ref = value.to_owned();
            let error = validate_commencement_transition(&evidence)
                .expect_err("a date is not a commencement source");
            assert_eq!(error.code(), Some("date-as-commencement"), "value {value}");
        }
    }

    #[test]
    fn a_filled_class_without_a_rule_reference_fails_closed() {
        let mut evidence = commencement_fixture();
        evidence.slots[0].commencement_rule_ref = String::new();
        let error = validate_commencement_transition(&evidence)
            .expect_err("a filled class needs a declared reference");
        assert_eq!(error.code(), Some("date-as-commencement"));
    }

    #[test]
    fn an_amending_act_slot_may_not_claim_commencement_evidence() {
        let mut evidence = commencement_fixture();
        evidence.slots[1].evidence_class = "hypothesized_from_oracle_diff".to_owned();
        evidence.slots[1].commencement_rule_ref = "rec:commencement:1".to_owned();
        let error = validate_commencement_transition(&evidence)
            .expect_err("only the named chain may carry the frozen boundary");
        assert_eq!(error.code(), Some("legislative_upgrade_attempt"));
    }

    #[test]
    fn an_amending_act_slot_must_justify_its_own_reason_code() {
        let mut evidence = commencement_fixture();
        evidence.slots[1].act_text_admitted = false;
        let error = validate_commencement_transition(&evidence)
            .expect_err("the reason code must follow the admitted act text");
        assert_eq!(error.code(), Some("no-legislative-commencement-source"));
    }

    #[test]
    fn a_denominator_that_does_not_reproduce_t02_fails_closed() {
        let mut evidence = commencement_fixture();
        evidence.amending_act_slots += 1;
        let error = validate_commencement_transition(&evidence)
            .expect_err("the T02 denominator is not negotiable");
        assert_eq!(error.code(), Some("family_count_unsupported"));

        let mut evidence = commencement_fixture();
        evidence.t02_layer1_records_total += 1;
        let error =
            validate_commencement_transition(&evidence).expect_err("T02 drift is a refusal");
        assert_eq!(error.code(), Some("family_count_unsupported"));
    }

    #[test]
    fn a_partition_that_does_not_sum_fails_closed() {
        let mut evidence = commencement_fixture();
        evidence
            .by_reason_code
            .insert("act-text-not-admitted".to_owned(), 7);
        let error = validate_commencement_transition(&evidence)
            .expect_err("a partition must sum to the denominator");
        assert_eq!(error.code(), Some("family_count_unsupported"));
    }

    #[test]
    fn class_matched_ids_must_stay_an_explicit_empty_set() {
        let mut evidence = commencement_fixture();
        evidence.class_matched_ids.push("annotation:1".to_owned());
        let error = validate_commencement_transition(&evidence)
            .expect_err("class-matched evidence is absent on this boundary");
        assert_eq!(error.code(), Some("family_count_unsupported"));
    }

    #[test]
    fn star_field_reads_a_declared_admission_line_only() {
        let text = "**admission: not-adopted**\n**admission_basis:** prose\n**owner_admission_ref:** none\n**runtime_work:** not-started";
        assert_eq!(star_field(text, "admission"), Some("not-adopted"));
        assert_eq!(star_field(text, "owner_admission_ref"), Some("none"));
        assert_eq!(star_field(text, "runtime_work"), Some("not-started"));
        assert_eq!(star_field(text, "absent"), None);
        assert_eq!(star_field("admission: not-adopted", "admission"), None);
    }

    #[test]
    fn a_date_or_a_file_name_is_refused_as_a_rule_reference() {
        for value in [
            "2013-04-05",
            "law_2013-04-05_44-fz",
            "law_2013-04-05_44-fz_rev-unknown_1a599b98.xml",
            "edition-abc",
        ] {
            assert!(
                is_date_or_filename(value),
                "{value} must read as a date or file name"
            );
        }
        for value in [
            "rec:commencement:484-93:hypothesized",
            "m201-frozen-commencement-boundary",
        ] {
            assert!(!is_date_or_filename(value), "{value} is a rule reference");
        }
    }

    #[test]
    fn an_adopted_m208_premise_fails_closed_as_the_declared_reason_code() {
        for mutate in [
            (|gate: &mut CommencementAdmissionGate| gate.m208_s03_admission = "adopted".to_owned())
                as fn(&mut CommencementAdmissionGate),
            |gate: &mut CommencementAdmissionGate| {
                gate.m208_s03_owner_admission_ref = "owner:1".to_owned()
            },
            |gate: &mut CommencementAdmissionGate| {
                gate.m208_s03_runtime_work = "started".to_owned()
            },
            |gate: &mut CommencementAdmissionGate| gate.m208_s04_admission = "adopted".to_owned(),
            |gate: &mut CommencementAdmissionGate| {
                gate.m208_s04_owner_admission_ref = "owner:1".to_owned()
            },
            |gate: &mut CommencementAdmissionGate| {
                gate.m208_s04_runtime_work = "started".to_owned()
            },
        ] {
            let mut evidence = commencement_fixture();
            mutate(&mut evidence.admission_gate);
            let error = validate_commencement_transition(&evidence)
                .expect_err("an adopted premise invalidates the declared reason");
            assert_eq!(error.code(), Some("m208-s03-not-adopted"));
        }
    }

    #[test]
    fn a_present_m207_pilot_fails_closed_as_the_declared_reason_code() {
        for mutate in [
            (|gate: &mut CommencementAdmissionGate| gate.m207_human_pilot = "present")
                as fn(&mut CommencementAdmissionGate),
            |gate: &mut CommencementAdmissionGate| {
                gate.m207_c4_operational_acceptance = "pass".to_owned()
            },
            |gate: &mut CommencementAdmissionGate| gate.m207_c4_rate_status = "measured",
        ] {
            let mut evidence = commencement_fixture();
            mutate(&mut evidence.admission_gate);
            let error = validate_commencement_transition(&evidence)
                .expect_err("a measured pilot invalidates the declared reason");
            assert_eq!(error.code(), Some("m207-human-pilot-absent"));
        }
    }
}
