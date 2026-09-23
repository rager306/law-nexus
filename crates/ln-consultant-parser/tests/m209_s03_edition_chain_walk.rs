//! M209/S03 T04: the edition-delta leg of R070 for the named `cc:44-fz` chain,
//! measured live against the licensed provider export.
//!
//! The suite is skip-capable exactly like `tests/m209_s03_amends_provision_edges.rs`:
//! `CONSULTANT_EXPORT_DIR` (empty-as-unset) with the default `consru_export`,
//! and `SKIP` plus an early return when the named chain edition directory
//! `consru_export/consru_export/exports/npa/law_2013-04-05_44-fz` is absent.
//!
//! What is asserted when the corpus is present:
//! - the declared inventory reconciles: the 118-edition figure is a live
//!   measurement, and `processed + unreadable + unparsed == total`;
//! - the 117 consecutive windows are one fewer than the processed editions and
//!   every window reproduces the counted delta of its own two adjacent rows;
//! - every per-edition digest and the chain digest recompute independently in
//!   the test over the fixed tuple, and the frozen T01 declaration still
//!   reconciles with the live listing digest;
//! - the tracked artifact is byte-identical to the live render, proven through
//!   `run_provenance` in `--check` mode without a second walk;
//! - a missing chain directory fails closed as `edition_dir_unreadable` (exit 3)
//!   and an out-of-repo `--out` fails as path drift (exit 2).
//!
//! Echo discipline: counts, edition numbers, revision labels and codes only. No
//! link destination, no link text and no XML byte is printed or asserted on.

use std::fs;
use std::path::{Path, PathBuf};

use ln_consultant_parser::amendment_provenance::{
    collect_edition_delta, render_edition_delta, run_provenance, validate_edition_delta,
    EditionDeltaRow, ProvenanceAction, ProvenanceCli, ProvenanceMode,
    EDITION_DELTA_FAIL_CLOSED_CODES, EDITION_DELTA_SCHEMA, EDITION_DELTA_TOP_N,
};

const CONSULTANT_EXPORT_DIR_ENV: &str = "CONSULTANT_EXPORT_DIR";
const CONSULTANT_EXPORT_DIR_DEFAULT: &str = "consru_export";

/// The one multi-edition chain of the corpus, relative to the export root.
const CHAIN_DIR_SUFFIX: &str = "consru_export/exports/npa/law_2013-04-05_44-fz";
/// The tracked artifact this leg emits, relative to the repository root.
const ARTIFACT_RELATIVE: &str = "prd/migration/rust-evidence/m209-s03-edition-delta-evidence.json";
/// The frozen T01 declaration the inventory reconciles against.
const T01_ARTIFACT_RELATIVE: &str = "prd/migration/rust-evidence/m209-s03-family-denominator.json";

/// Grounding pin of the accepted revision (T01/T04 plan).
const EXPECTED_EDITIONS: u64 = 118;

fn consultant_export_dir() -> String {
    match std::env::var(CONSULTANT_EXPORT_DIR_ENV) {
        Ok(value) if !value.trim().is_empty() => value,
        _ => CONSULTANT_EXPORT_DIR_DEFAULT.to_owned(),
    }
}

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// The named chain edition directory, or `None` when the export is absent.
fn chain_dir() -> Option<PathBuf> {
    let directory = repo_root()
        .join(consultant_export_dir())
        .join(CHAIN_DIR_SUFFIX);
    directory.is_dir().then_some(directory)
}

/// FNV-1a (64-bit), the emitter's determinism fingerprint, re-implemented here
/// so the suite never trusts the emitter to check its own digest.
fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325_u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x0000_0100_0000_01b3_u64);
    }
    hash
}

/// The fixed per-edition tuple the digest must cover, in the emitter's order.
fn row_tuple(row: &EditionDeltaRow) -> String {
    format!(
        "{}|{}|{}|{}|{}|{}|{}|{}",
        row.edition_number,
        row.revision_label,
        row.hyperlink_count,
        row.classified_count,
        row.amends_count,
        row.cites_count,
        row.implements_count,
        row.unknown_count
    )
}

/// Brace- and string-aware reader of one named top-level object, so a nested
/// object never truncates the scan (mirrors the emitter's own reader).
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

/// One flat string field out of an already-isolated object body.
fn flat_str(body: &str, key: &str) -> Option<String> {
    let marker = format!("\"{key}\":\"");
    let start = body.find(&marker)? + marker.len();
    let rest = &body[start..];
    let end = rest.find('"')?;
    Some(rest[..end].to_owned())
}

#[test]
fn the_walk_reconciles_the_declared_chain_inventory() {
    let Some(_) = chain_dir() else {
        eprintln!("SKIP: consru_export 44-fz edition chain directory not available");
        return;
    };
    let root = repo_root();
    let evidence =
        collect_edition_delta(&root, &consultant_export_dir()).expect("live edition-delta leg");
    validate_edition_delta(&evidence).expect("the leg validates");

    // (a) the declared inventory of the named chain.
    assert_eq!(evidence.editions_total, EXPECTED_EDITIONS);
    assert_eq!(evidence.editions_unparsed_filename, 0);
    assert_eq!(evidence.edition_dir_files_total, evidence.editions_total);

    // (b) the declared counts reconcile.
    assert_eq!(
        evidence.editions_processed
            + evidence.editions_unreadable
            + evidence.editions_unparsed_filename,
        evidence.editions_total
    );
    assert_eq!(evidence.windows_total, evidence.editions_processed - 1);
    assert_eq!(evidence.windows.len() as u64, evidence.windows_total);
    assert_eq!(evidence.rows.len() as u64, evidence.editions_processed);
    assert_eq!(
        evidence.top_amends_windows.len() as u64,
        evidence.windows_total.min(EDITION_DELTA_TOP_N as u64)
    );

    // (c) every digest covers its own row, and the chain digest covers them all.
    for row in &evidence.rows {
        let expected = format!("fnv1a64:{:016x}", fnv1a64(row_tuple(row).as_bytes()));
        assert_eq!(
            row.digest, expected,
            "edition {} digest must cover its own tuple",
            row.edition_number
        );
    }
    let mut stream = String::new();
    for row in &evidence.rows {
        stream.push_str(&row.digest);
        stream.push('\n');
    }
    assert_eq!(
        evidence.chain_digest,
        format!("fnv1a64:{:016x}", fnv1a64(stream.as_bytes())),
        "the chain digest must cover the ordered per-edition digests"
    );

    // (d) every window reproduces the delta of its own two adjacent rows.
    for (index, window) in evidence.windows.iter().enumerate() {
        let from = &evidence.rows[index];
        let to = &evidence.rows[index + 1];
        assert_eq!(window.from_edition, from.edition_number);
        assert_eq!(window.to_edition, to.edition_number);
        assert_eq!(window.revision_from, from.revision_label);
        assert_eq!(window.revision_to, to.revision_label);
        assert_eq!(
            window.amends_change,
            to.amends_count as i64 - from.amends_count as i64
        );
        assert_eq!(
            window.cites_change,
            to.cites_count as i64 - from.cites_count as i64
        );
        assert_eq!(
            window.implements_change,
            to.implements_count as i64 - from.implements_count as i64
        );
        assert_eq!(
            window.unknown_change,
            to.unknown_count as i64 - from.unknown_count as i64
        );
    }

    // (e) the frozen T01 declaration still reconciles with the live listing.
    assert_eq!(evidence.t01_editions_total, evidence.editions_total);
    assert_eq!(evidence.t01_edition_matching, evidence.editions_total);
    let t01_path = root.join(T01_ARTIFACT_RELATIVE);
    let t01_text = fs::read_to_string(&t01_path).expect("the frozen T01 artifact");
    let t01_chain = object_body(&t01_text, "chain").expect("the T01 chain block");
    assert_eq!(
        flat_str(t01_chain, "input_sha256").expect("the T01 chain listing digest"),
        evidence.edition_dir_listing_sha256,
        "the live listing digest must equal the frozen T01 pin"
    );

    // The render is count-only and ASCII by construction, and every declared
    // fail-closed code is present in it.
    let rendered = render_edition_delta(&evidence);
    assert!(rendered.is_ascii(), "the artifact must be pure ascii");
    assert!(!rendered.contains('\n'), "canonical bytes are single-line");
    assert!(rendered.contains(EDITION_DELTA_SCHEMA));
    for code in EDITION_DELTA_FAIL_CLOSED_CODES {
        assert!(
            rendered.contains(&format!("\"{code}\"")),
            "every fail-closed code is declared in the artifact: {code}"
        );
    }
    for marker in ["consultantplus://", "<w:", "screenTip"] {
        assert!(
            !rendered.contains(marker),
            "no corpus prose marker may reach the artifact: {marker}"
        );
    }
    assert_eq!(rendered, render_edition_delta(&evidence));

    // (f) determinism without a second walk: `--check` re-walks once and
    // byte-compares against the tracked artifact.
    let cli = ProvenanceCli {
        mode: ProvenanceMode::EditionChain,
        export_dir: consultant_export_dir(),
        out: PathBuf::from(ARTIFACT_RELATIVE),
        action: ProvenanceAction::Check,
    };
    let outcome = run_provenance(&cli, &root)
        .expect("the tracked artifact must be byte-identical to the live render");
    assert!(
        outcome.heartbeat.contains("drift=0"),
        "the check heartbeat must declare zero drift: {}",
        outcome.heartbeat
    );

    eprintln!(
        "[edition-chain] editions={} processed={} unreadable={} unparsed={} windows={} t01_editions={} t01_matching={}",
        evidence.editions_total,
        evidence.editions_processed,
        evidence.editions_unreadable,
        evidence.editions_unparsed_filename,
        evidence.windows_total,
        evidence.t01_editions_total,
        evidence.t01_edition_matching
    );
}

#[test]
fn absent_chain_directory_and_out_of_repo_artifact_fail_closed() {
    let root = repo_root();

    // A missing chain directory is an absence, not an empty measurement.
    let absent = collect_edition_delta(&root, "consru_export-does-not-exist")
        .expect_err("an absent chain directory must fail closed");
    assert_eq!(absent.code(), Some("edition_dir_unreadable"));
    assert_eq!(absent.exit_code(), 3);

    // An `--out` outside the canonicalised repository root is path drift.
    for out in ["/etc/passwd", "../outside.json"] {
        let cli = ProvenanceCli {
            mode: ProvenanceMode::EditionChain,
            export_dir: consultant_export_dir(),
            out: PathBuf::from(out),
            action: ProvenanceAction::Check,
        };
        let drift =
            run_provenance(&cli, &root).expect_err("an out-of-repo artifact path must fail closed");
        assert_eq!(drift.exit_code(), 2, "path drift pins exit code 2");
        assert!(
            drift.cli_line().starts_with("error=path-drift"),
            "the drift must name its class: {}",
            drift.cli_line()
        );
    }
}

/// Guard the declared fail-closed code set: the artifact, the node contract and
/// this array must carry the same set, and the chain absence code is reachable.
#[test]
fn the_declared_fail_closed_codes_are_bounded() {
    assert_eq!(EDITION_DELTA_FAIL_CLOSED_CODES.len(), 7);
    for code in [
        "input_absent",
        "input_hash_mismatch",
        "family_count_unsupported",
        "zero_denominator",
        "non_ascii_evidence",
        "raw_text_leak",
        "edition_dir_unreadable",
    ] {
        assert!(
            EDITION_DELTA_FAIL_CLOSED_CODES.contains(&code),
            "the declared set must carry {code}"
        );
    }
}

/// The suite must stay a sibling of the established skip-capable pattern.
#[test]
fn the_suite_binds_the_named_chain_and_path_drift_contract() {
    assert!(Path::new(ARTIFACT_RELATIVE).is_relative());
    assert!(!Path::new(ARTIFACT_RELATIVE)
        .components()
        .any(|component| matches!(component, std::path::Component::ParentDir)));
    assert!(T01_ARTIFACT_RELATIVE.starts_with("prd/migration/rust-evidence/"));
    assert_eq!(EXPECTED_EDITIONS, 118);
}
