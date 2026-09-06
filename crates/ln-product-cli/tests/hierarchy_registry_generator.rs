//! TDD red contract for the thin cross-crate `hierarchy-registry-generator`
//! (M202-9qf3ta S03 T03): explicit `--candidate-artifact` / `--admissions` /
//! `--out` with mutually exclusive `--write` / `--check`, driving ln-decode
//! candidate evidence plus the ln-kb-ontology sibling admission boundary.
//!
//! Pins for the future T04 generator:
//! - subprocess binary is `CARGO_BIN_EXE_hierarchy-registry-generator`;
//! - `--check` is the stale acceptance: it renders in memory, byte-compares,
//!   never writes, exits 0 on match with bytes unchanged, and exits 6 on
//!   stale output with bytes unchanged (`--write` can never prove stale
//!   rejection);
//! - conflict, digest mismatch, authority escalation, missing input,
//!   absolute/path-escape outputs, and non-registry production writes all
//!   fail before any output mutation;
//! - stderr is count-only (`drift=` / `error=` / `key=value` counters) and
//!   carries no raw legal text;
//! - fixture strings bind only the already-existing D426 CC identifiers
//!   `cc:44-fz:glava-1`, `cc:44-fz:statya-4`, `cc:44-fz:statya-5`; punkt
//!   candidates stay unadmitted.
//!
//! Non-claims: no `--write` against a tracked YAML path, no corpus walk, no
//! ComponentConcept minting. The registry stays `[proposed]` with
//! `authoritative: false`; R035 stays active for S04.
//!
//! RED: T04 owns the binary and the library orchestration, so this target
//! currently fails to compile on the missing
//! `CARGO_BIN_EXE_hierarchy-registry-generator` variable. That single
//! missing-bin error is the whole red signal.

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

/// Tracked S02 candidate artifact every generator invocation must bind.
const CANDIDATE_ARTIFACT_PATH: &str =
    "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";
/// Closed admission-source schema the future generator must accept.
const ADMISSION_SCHEMA_V1: &str = "law-nexus-kb-hierarchy-admission/v1";
/// Exact SHA-256 of the tracked S02 artifact (binding pin, mirrors T01).
const S02_ARTIFACT_SHA256: &str =
    "50946d813412315632214bdfe6f6300e5d5fa8372ab14900002ade2ded5adef6";
/// Closed `source_digest` pin from the tracked S02 artifact.
const S02_SOURCE_DIGEST: &str = "fnv1a64:5ec57029f2ff9d05";
/// Closed `identity_digest` pin from the tracked S02 artifact.
const S02_IDENTITY_DIGEST: &str = "fnv1a64:aff2a32522ccb77f";

/// Future T04 binary under test. RED: no `[[bin]]` registers this name yet,
/// so this target fails to compile on the missing build variable. That
/// single missing-bin error is the whole red signal.
fn binary() -> &'static str {
    env!("CARGO_BIN_EXE_hierarchy-registry-generator")
}

/// Repository root: this crate sits two levels below it.
fn repo_root() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .ancestors()
        .nth(2)
        .expect("ln-product-cli lives two levels below the repo root")
        .to_path_buf()
}

/// Cargo target temp tree: the only writable `--out` class for tests besides
/// the canonical tracked registry path (which this suite never writes).
fn target_tmp_dir() -> PathBuf {
    let dir = repo_root().join("target").join("tmp");
    fs::create_dir_all(&dir).expect("create Cargo target tmp dir");
    dir
}

/// Repository-relative rendering of a temp path, the form passed as `--out`
/// / `--admissions` so the generator resolves it against the repo root.
fn repo_relative(path: &Path) -> String {
    path.strip_prefix(repo_root())
        .expect("temp path lives under the repo root")
        .to_string_lossy()
        .into_owned()
}

fn fresh_tmp_file(tag: &str) -> PathBuf {
    target_tmp_dir().join(format!("m202-s03-{tag}-{}", std::process::id()))
}

fn remove_quietly(path: &Path) {
    let _ = fs::remove_file(path);
}

fn read_bytes(path: &Path) -> Vec<u8> {
    fs::read(path).expect("read temp output bytes")
}

fn stderr_of(output: &std::process::Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn run_generator(args: &[String]) -> std::process::Output {
    Command::new(binary())
        .args(args)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn hierarchy-registry-generator")
}

/// Minimal closed admission fixture: only the three D426 candidate-backed
/// rows (glava-1/statya-4/statya-5) bound to already-existing CC
/// identifiers. Punkt candidates stay unadmitted; no CC is minted.
fn fixture_admissions_text() -> String {
    format!(
        "schema: {ADMISSION_SCHEMA_V1}\n\
         lifecycle: \"[proposed]\"\n\
         authoritative: false\n\
         candidate_artifact_path: {CANDIDATE_ARTIFACT_PATH}\n\
         candidate_artifact_sha256: {S02_ARTIFACT_SHA256}\n\
         candidate_source_digest: {S02_SOURCE_DIGEST}\n\
         candidate_identity_digest: {S02_IDENTITY_DIGEST}\n\
         admissions:\n\
         \u{20}\u{20}- {{path_needle: law_2013-04-05_44-fz, level: statya, number: \"5\", key_path: \"5\", cc: cc:44-fz:statya-5, provenance: m202-candidate-backed}}\n\
         \u{20}\u{20}- {{path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\", key_path: \"1\", cc: cc:44-fz:glava-1, provenance: m202-candidate-backed}}\n\
         \u{20}\u{20}- {{path_needle: law_2013-04-05_44-fz, level: statya, number: \"4\", key_path: \"4\", cc: cc:44-fz:statya-4, provenance: m202-candidate-backed}}\n"
    )
}

fn write_fixture_admissions(tag: &str) -> PathBuf {
    let path = fresh_tmp_file(&format!("{tag}-admissions.yaml"));
    fs::write(&path, fixture_admissions_text()).expect("write fixture admissions");
    path
}

/// Same registry key bound to two different CC identifiers: must fail
/// before any output mutation.
fn conflicting_admissions_text() -> String {
    format!(
        "schema: {ADMISSION_SCHEMA_V1}\n\
         lifecycle: \"[proposed]\"\n\
         authoritative: false\n\
         candidate_artifact_path: {CANDIDATE_ARTIFACT_PATH}\n\
         candidate_artifact_sha256: {S02_ARTIFACT_SHA256}\n\
         candidate_source_digest: {S02_SOURCE_DIGEST}\n\
         candidate_identity_digest: {S02_IDENTITY_DIGEST}\n\
         admissions:\n\
         \u{20}\u{20}- {{path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\", key_path: \"1\", cc: cc:44-fz:glava-1, provenance: m202-candidate-backed}}\n\
         \u{20}\u{20}- {{path_needle: law_2013-04-05_44-fz, level: glava, number: \"1\", key_path: \"1\", cc: cc:44-fz:glava-2, provenance: m202-candidate-backed}}\n"
    )
}

fn base_args(admissions: &Path, out: &Path, mode: &str) -> Vec<String> {
    vec![
        "--candidate-artifact".to_owned(),
        CANDIDATE_ARTIFACT_PATH.to_owned(),
        "--admissions".to_owned(),
        repo_relative(admissions),
        "--out".to_owned(),
        repo_relative(out),
        mode.to_owned(),
    ]
}

/// stderr must be count-only: ASCII, blank or `key=value`-token lines, no
/// raw legal text. T04 detail values stay single-token (dashes, not spaces)
/// so every token carries `=`.
fn assert_count_only_stderr(stderr: &str) {
    assert!(
        stderr.is_ascii(),
        "stderr must be ASCII-only (no raw legal text); got: {stderr:?}"
    );
    for line in stderr.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        let shaped = line.starts_with("drift=")
            || line.starts_with("error=")
            || line.split_whitespace().all(|token| token.contains('='));
        assert!(
            shaped,
            "stderr must be count-only key=value lines; got: {line:?}"
        );
    }
    assert_no_raw_legal_text(stderr);
}

fn assert_no_raw_legal_text(text: &str) {
    for needle in [
        "Federalnyi-zakon",
        "Obshchie-polozheniya",
        "Predmet-regulirovaniya",
        "Statya-",
        "Glava-",
    ] {
        assert!(
            !text.contains(needle),
            "output must not carry raw legal text ({needle:?})"
        );
    }
}

/// Seed a temp `--out` through `--write` (Cargo target tmp tree only, never
/// a tracked path) and return its rendered bytes.
fn seed_temp_output(admissions: &Path, out: &Path) -> Vec<u8> {
    remove_quietly(out);
    let written = run_generator(&base_args(admissions, out, "--write"));
    assert!(
        written.status.success(),
        "--write to the Cargo target tmp tree must exit 0; stderr={}",
        stderr_of(&written)
    );
    assert_count_only_stderr(&stderr_of(&written));
    let bytes = read_bytes(out);
    assert!(
        !bytes.is_empty(),
        "--write must render a non-empty projection"
    );
    bytes
}

#[test]
fn explicit_args_are_required_before_any_mutation() {
    let admissions = write_fixture_admissions("explicit-args");
    let out = fresh_tmp_file("explicit-args-expected.yaml");
    let sentinel = b"sentinel: explicit-args\n";
    fs::write(&out, sentinel).expect("write sentinel expected output");

    // --check without --out.
    let missing_out = vec![
        "--candidate-artifact".to_owned(),
        CANDIDATE_ARTIFACT_PATH.to_owned(),
        "--admissions".to_owned(),
        repo_relative(&admissions),
        "--check".to_owned(),
    ];
    let result = run_generator(&missing_out);
    assert_eq!(
        result.status.code(),
        Some(2),
        "--check without --out must exit 2; stderr={}",
        stderr_of(&result)
    );

    // Missing --candidate-artifact and missing --admissions, each with a
    // sentinel --out that must stay byte-identical.
    for (label, args) in [
        (
            "candidate-artifact",
            vec![
                "--admissions".to_owned(),
                repo_relative(&admissions),
                "--out".to_owned(),
                repo_relative(&out),
                "--check".to_owned(),
            ],
        ),
        (
            "admissions",
            vec![
                "--candidate-artifact".to_owned(),
                CANDIDATE_ARTIFACT_PATH.to_owned(),
                "--out".to_owned(),
                repo_relative(&out),
                "--check".to_owned(),
            ],
        ),
    ] {
        let bytes_before = read_bytes(&out);
        let result = run_generator(&args);
        assert_eq!(
            result.status.code(),
            Some(2),
            "missing --{label} must exit 2; stderr={}",
            stderr_of(&result)
        );
        assert_eq!(
            read_bytes(&out),
            bytes_before,
            "missing --{label} must not mutate --out bytes"
        );
    }
    assert_eq!(
        read_bytes(&out),
        sentinel,
        "sentinel --out bytes must survive every usage refusal"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn write_and_check_are_mutually_exclusive_and_never_mutate() {
    let admissions = write_fixture_admissions("exclusive");
    let out = fresh_tmp_file("exclusive-expected.yaml");
    let sentinel = b"sentinel: exclusive\n";
    fs::write(&out, sentinel).expect("write sentinel expected output");
    let bytes_before = read_bytes(&out);

    let mut args = base_args(&admissions, &out, "--write");
    args.push("--check".to_owned());
    let result = run_generator(&args);
    assert_eq!(
        result.status.code(),
        Some(2),
        "--write with --check must exit 2; stderr={}",
        stderr_of(&result)
    );
    assert_count_only_stderr(&stderr_of(&result));
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "--write/--check conflict must not mutate --out bytes"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn matching_check_exits_zero_and_leaves_bytes_unchanged() {
    let admissions = write_fixture_admissions("matching");
    let out = fresh_tmp_file("matching-expected.yaml");
    let bytes_before = seed_temp_output(&admissions, &out);

    // Acceptance: --check renders in memory, byte-compares, never writes.
    let checked = run_generator(&base_args(&admissions, &out, "--check"));
    assert_eq!(
        checked.status.code(),
        Some(0),
        "matching --check must exit 0; stderr={}",
        stderr_of(&checked)
    );
    assert_count_only_stderr(&stderr_of(&checked));
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "matching --check must leave --out bytes unchanged"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn stale_check_exits_six_and_leaves_bytes_unchanged() {
    let admissions = write_fixture_admissions("stale");
    let out = fresh_tmp_file("stale-expected.yaml");
    seed_temp_output(&admissions, &out);

    // Corrupt one ASCII byte (case flip keeps the temp file valid UTF-8).
    let mut stale = read_bytes(&out);
    let pos = stale
        .iter()
        .position(|byte| byte.is_ascii_alphabetic())
        .expect("rendered projection must carry ASCII binding text");
    stale[pos] ^= 0x20;
    fs::write(&out, &stale).expect("write corrupted stale expected output");
    let bytes_before = read_bytes(&out);

    // Stale acceptance: --check rejects with typed exit 6, no mutation.
    // --write could never prove this rejection.
    let checked = run_generator(&base_args(&admissions, &out, "--check"));
    assert_eq!(
        checked.status.code(),
        Some(6),
        "stale --check must exit 6; stderr={}",
        stderr_of(&checked)
    );
    let stderr = stderr_of(&checked);
    assert!(
        stderr.contains("drift="),
        "stale --check stderr must carry a drift= line; got: {stderr:?}"
    );
    assert_count_only_stderr(&stderr);
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "stale --check must leave --out bytes unchanged"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn conflicting_cc_fails_before_output_mutation() {
    let admissions = fresh_tmp_file("conflict-admissions.yaml");
    fs::write(&admissions, conflicting_admissions_text()).expect("write conflict fixture");
    let out = fresh_tmp_file("conflict-expected.yaml");
    let sentinel = b"sentinel: conflict\n";
    fs::write(&out, sentinel).expect("write sentinel expected output");
    let bytes_before = read_bytes(&out);

    let result = run_generator(&base_args(&admissions, &out, "--check"));
    assert_eq!(
        result.status.code(),
        Some(6),
        "conflicting CC must exit 6; stderr={}",
        stderr_of(&result)
    );
    assert!(
        stderr_of(&result).contains("drift="),
        "conflict stderr must carry a drift= line"
    );
    assert_count_only_stderr(&stderr_of(&result));
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "conflict must fail before any output mutation"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn digest_mismatch_fails_before_output_mutation() {
    let admissions = fresh_tmp_file("digest-admissions.yaml");
    let drifted =
        fixture_admissions_text().replace(S02_IDENTITY_DIGEST, "fnv1a64:0000000000000000");
    assert_ne!(drifted, fixture_admissions_text());
    fs::write(&admissions, drifted).expect("write drifted fixture");
    let out = fresh_tmp_file("digest-expected.yaml");
    let sentinel = b"sentinel: digest\n";
    fs::write(&out, sentinel).expect("write sentinel expected output");
    let bytes_before = read_bytes(&out);

    let result = run_generator(&base_args(&admissions, &out, "--check"));
    assert_eq!(
        result.status.code(),
        Some(6),
        "digest mismatch must exit 6; stderr={}",
        stderr_of(&result)
    );
    assert!(
        stderr_of(&result).contains("drift="),
        "digest-mismatch stderr must carry a drift= line"
    );
    assert_count_only_stderr(&stderr_of(&result));
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "digest mismatch must fail before any output mutation"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn authority_escalation_fails_before_output_mutation() {
    let admissions = fresh_tmp_file("authority-admissions.yaml");
    let escalated =
        fixture_admissions_text().replace("authoritative: false", "authoritative: true");
    assert_ne!(escalated, fixture_admissions_text());
    fs::write(&admissions, escalated).expect("write escalated fixture");
    let out = fresh_tmp_file("authority-expected.yaml");
    let sentinel = b"sentinel: authority\n";
    fs::write(&out, sentinel).expect("write sentinel expected output");
    let bytes_before = read_bytes(&out);

    let result = run_generator(&base_args(&admissions, &out, "--check"));
    assert_eq!(
        result.status.code(),
        Some(6),
        "authority escalation must exit 6; stderr={}",
        stderr_of(&result)
    );
    assert!(
        stderr_of(&result).contains("drift="),
        "authority-escalation stderr must carry a drift= line"
    );
    assert_count_only_stderr(&stderr_of(&result));
    assert_eq!(
        read_bytes(&out),
        bytes_before,
        "authority escalation must fail before any output mutation"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn missing_candidate_artifact_fails_without_creating_output() {
    let admissions = write_fixture_admissions("missing-input");
    let out = fresh_tmp_file("missing-input-expected.yaml");
    remove_quietly(&out);

    let mut args = base_args(&admissions, &out, "--check");
    let position = args
        .iter()
        .position(|arg| arg == CANDIDATE_ARTIFACT_PATH)
        .expect("base args carry --candidate-artifact");
    args[position] = "prd/migration/rust-evidence/m202-s02-DOES-NOT-EXIST.json".to_owned();
    let result = run_generator(&args);
    assert_eq!(
        result.status.code(),
        Some(4),
        "missing candidate artifact must exit 4; stderr={}",
        stderr_of(&result)
    );
    assert_count_only_stderr(&stderr_of(&result));
    assert!(
        !out.exists(),
        "missing input must fail before creating --out"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn absolute_and_parent_escape_outputs_are_refused() {
    let admissions = write_fixture_admissions("escape");

    // Absolute escape: must exit 2 and must not create the target.
    let absolute =
        std::env::temp_dir().join(format!("m202-s03-escape-{}.yaml", std::process::id()));
    remove_quietly(&absolute);
    let absolute_args = vec![
        "--candidate-artifact".to_owned(),
        CANDIDATE_ARTIFACT_PATH.to_owned(),
        "--admissions".to_owned(),
        repo_relative(&admissions),
        "--out".to_owned(),
        absolute.to_string_lossy().into_owned(),
        "--check".to_owned(),
    ];
    let absolute_result = run_generator(&absolute_args);
    assert_eq!(
        absolute_result.status.code(),
        Some(2),
        "absolute --out must exit 2; stderr={}",
        stderr_of(&absolute_result)
    );
    assert!(
        !absolute.exists(),
        "absolute --out must be refused before any write"
    );

    // Parent escape: repository-relative `..` must exit 2 as well.
    let parent_args = vec![
        "--candidate-artifact".to_owned(),
        CANDIDATE_ARTIFACT_PATH.to_owned(),
        "--admissions".to_owned(),
        repo_relative(&admissions),
        "--out".to_owned(),
        format!("../m202-s03-escape-{}.yaml", std::process::id()),
        "--check".to_owned(),
    ];
    let parent_result = run_generator(&parent_args);
    assert_eq!(
        parent_result.status.code(),
        Some(2),
        "parent-escape --out must exit 2; stderr={}",
        stderr_of(&parent_result)
    );

    remove_quietly(&admissions);
}

#[test]
fn non_registry_production_write_is_refused() {
    let admissions = write_fixture_admissions("non-registry-write");
    // Non-canonical tracked-tree target: --write is allowed only for the
    // canonical registry projection (T05 owns it) and the Cargo target tmp
    // tree used by the other tests in this suite.
    let refused = repo_root().join(format!(
        "prd/architecture/m202-s03-refused-{}.yaml",
        std::process::id()
    ));
    remove_quietly(&refused);
    let mut args = base_args(&admissions, &refused, "--write");
    let position = args
        .iter()
        .position(|arg| arg == &repo_relative(&refused))
        .expect("base args carry --out");
    args[position] = format!(
        "prd/architecture/m202-s03-refused-{}.yaml",
        std::process::id()
    );
    let result = run_generator(&args);
    assert_eq!(
        result.status.code(),
        Some(2),
        "non-registry production --write must exit 2; stderr={}",
        stderr_of(&result)
    );
    assert!(
        !refused.exists(),
        "non-registry production --write must be refused before any write"
    );

    remove_quietly(&admissions);
    remove_quietly(&refused);
}

#[test]
fn generator_stderr_is_count_only_without_raw_legal_text() {
    let admissions = write_fixture_admissions("stderr-counts");
    let out = fresh_tmp_file("stderr-counts-expected.yaml");
    seed_temp_output(&admissions, &out);

    let checked = run_generator(&base_args(&admissions, &out, "--check"));
    assert!(
        checked.status.success(),
        "matching --check must exit 0; stderr={}",
        stderr_of(&checked)
    );
    let stderr = stderr_of(&checked);
    assert!(
        stderr.contains("drift=0") || stderr.contains("drift=no"),
        "success stderr must carry an explicit zero-drift heartbeat; got: {stderr:?}"
    );
    assert_count_only_stderr(&stderr);

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn fixture_binds_only_existing_d426_cc_and_leaves_punkt_unadmitted() {
    let text = fixture_admissions_text();
    // Only the three already-existing D426 CC identifiers are bound.
    for cc in ["cc:44-fz:glava-1", "cc:44-fz:statya-4", "cc:44-fz:statya-5"] {
        assert!(
            text.contains(cc),
            "fixture must bind the existing D426 CC {cc}"
        );
    }
    // Punkt candidates stay unadmitted: no punkt row, no minting language.
    assert!(
        !text.contains("level: punkt"),
        "punkt candidates must stay unadmitted"
    );
    assert!(
        !text.contains("mint"),
        "fixture must never mint a ComponentConcept"
    );
    // Registry stays [proposed] with authoritative: false.
    assert!(
        text.contains("[proposed]"),
        "fixture must pin lifecycle [proposed]"
    );
    assert!(
        text.contains("authoritative: false"),
        "fixture must pin authoritative: false"
    );
    // Every candidate-backed row carries an explicit flat D426 key_path.
    for key_path in ["key_path: \"1\"", "key_path: \"4\"", "key_path: \"5\""] {
        assert!(
            text.contains(key_path),
            "fixture must carry the explicit D426 binding {key_path}"
        );
    }
    assert_no_raw_legal_text(&text);
}
