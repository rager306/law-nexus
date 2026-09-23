//! M209-2yg6ix S02 T03 acceptance contract for the successor candidate-backed
//! admission generation (D545 / D546 / D548).
//!
//! The claim under test is *zero delta at a wider denominator*: the same
//! `hierarchy-registry-generator` binary, driven by the successor admission
//! source (`m209-candidate-backed` rows, 102 of them) over the 1901-identity
//! M209 candidate artifact, must render the *byte-identical* canonical
//! projection that the frozen M202 generation renders from its own 3
//! candidate-backed rows. Provenance is admission-source metadata and must
//! never reach the registry projection, so widening the evidence can only be
//! legitimate when the bytes do not move.
//!
//! What is pinned here:
//! - `--check` exits 0 on the successor pair and on the frozen pair, and the
//!   count-only heartbeat separates the two candidate-backed generations
//!   (`candidate-backed=102` vs `candidate-backed=3`) because both flow
//!   through `AdmissionProvenance::is_candidate_backed()`;
//! - the library render is byte-identical across generations and equal to the
//!   tracked `prd/architecture/kb-hierarchy-registry.yaml` bytes, admits 166
//!   rows, and admits no `punkt` row;
//! - `--write` is repeatable: two writes are byte-identical and equal to the
//!   canonical projection;
//! - swapping the source, reducing the candidate artifact, or narrowing the
//!   pinned identity digest fails closed with a named `drift=admission`
//!   refusal and no partial write.
//!
//! Only tracked inputs are read. Temp outputs live under `target/tmp/`, the
//! one writable `--out` class besides the canonical registry path, which this
//! suite never writes.
//!
//! Run: cargo test -p ln-product-cli --offline --test m209_s02_registry_regeneration

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

use ln_product_cli::hierarchy_registry_generation::{
    parse_generator_args, render_projection, GeneratorCli, GeneratorError, GeneratorMode,
    CANONICAL_REGISTRY_PATH,
};

/// Successor M209 admission source (102 `m209-candidate-backed` rows).
const M209_ADMISSIONS_PATH: &str =
    "prd/architecture/m209-s02-kb-hierarchy-registry-admissions.yaml";
/// Frozen M202 admission source (3 `m202-candidate-backed` rows).
const M202_ADMISSIONS_PATH: &str = "prd/architecture/kb-hierarchy-registry-admissions.yaml";
/// Successor M209 candidate artifact (1901 identities, D547 denominator).
const M209_ARTIFACT_PATH: &str =
    "prd/migration/rust-evidence/m209-s02-hierarchy-candidates-fz44.json";
/// Frozen M202 candidate artifact (6 identities).
const M202_ARTIFACT_PATH: &str = "prd/migration/rust-evidence/m202-s02-hierarchy-candidates.json";

/// Declared denominator components: 8 glava + 94 statya + 793 chast +
/// 997 punkt + 9 paragraph = 1901 extracted identities.
const DENOMINATOR_EXTRACTED: usize = 1901;
const DENOMINATOR_GLAVA: usize = 8;
const DENOMINATOR_STATYA: usize = 94;
const DENOMINATOR_CHAST: usize = 793;
const DENOMINATOR_PUNKT: usize = 997;
const DENOMINATOR_PARAGRAPH: usize = 9;
/// Identities the successor generation resolves into existing registry rows.
const DENOMINATOR_CANDIDATE_BACKED: usize = 102;
const DENOMINATOR_UNADMITTED: usize = DENOMINATOR_EXTRACTED - DENOMINATOR_CANDIDATE_BACKED;

/// Registry rows admitted from either generation (the row set is generation
/// independent: 166 rows, 163 legacy in M202 terms).
const ROWS_TOTAL: usize = 166;
const ROWS_LEGACY_M209: usize = 64;
const ROWS_CANDIDATE_BACKED_M209: usize = 102;
const ROWS_LEGACY_M202: usize = 163;
const ROWS_CANDIDATE_BACKED_M202: usize = 3;

static TMP_COUNTER: AtomicUsize = AtomicUsize::new(0);

/// The generator binary under test.
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

/// A unique repository-relative path under `target/tmp/`.
fn fresh_tmp_path(tag: &str) -> String {
    let counter = TMP_COUNTER.fetch_add(1, Ordering::Relaxed);
    let name = format!("m209-s02-{tag}-{}-{counter}.yaml", std::process::id());
    let path = repo_root().join("target").join("tmp").join(name);
    fs::create_dir_all(path.parent().expect("temp parent")).expect("create target/tmp");
    format!("target/tmp/{}", path.file_name().unwrap().to_string_lossy())
}

fn remove_quietly(relative: &str) {
    let _ = fs::remove_file(repo_root().join(relative));
}

fn read_repo_bytes(relative: &str) -> Vec<u8> {
    fs::read(repo_root().join(relative)).unwrap_or_else(|error| panic!("read {relative}: {error}"))
}

fn read_repo_text(relative: &str) -> String {
    String::from_utf8(read_repo_bytes(relative)).expect("tracked input is utf-8")
}

fn run_generator(args: &[String]) -> std::process::Output {
    Command::new(binary())
        .args(args)
        .current_dir(repo_root())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .expect("spawn hierarchy-registry-generator")
}

fn generator_args(artifact: &str, admissions: &str, out: &str, mode: &str) -> Vec<String> {
    vec![
        "--candidate-artifact".to_owned(),
        artifact.to_owned(),
        "--admissions".to_owned(),
        admissions.to_owned(),
        "--out".to_owned(),
        out.to_owned(),
        mode.to_owned(),
    ]
}

fn stderr_of(output: &std::process::Output) -> String {
    String::from_utf8(output.stderr.clone()).expect("stderr is utf-8")
}

/// stderr stays count-only: no raw legal text, every token carries `=`.
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
        assert!(shaped, "stderr must be key=value only; got {line:?}");
    }
}

fn heartbeat_line(admitted: usize, legacy: usize, candidate_backed: usize) -> String {
    format!("admitted={admitted} legacy={legacy} candidate-backed={candidate_backed} drift=0")
}

fn cli_for(artifact: &str, admissions: &str, out: &str, mode: GeneratorMode) -> GeneratorCli {
    GeneratorCli {
        candidate_artifact: PathBuf::from(artifact),
        admissions: PathBuf::from(admissions),
        out: PathBuf::from(out),
        mode,
    }
}

/// Binding rows of a rendered projection.
fn binding_rows(rendered: &str) -> Vec<&str> {
    rendered
        .lines()
        .filter(|line| line.starts_with("- {path_needle:"))
        .collect()
}

/// The denominator is asserted as a decomposition, never as a bare total
/// (D547): each level's count comes from the live artifact and must sum to
/// the declared extraction total.
#[test]
fn live_artifact_denominator_matches_the_declared_decomposition() {
    let artifact = read_repo_text(M209_ARTIFACT_PATH);
    let view = ln_decode::hierarchy_artifact::parse_candidate_artifact_view(&artifact)
        .expect("tracked M209 artifact parses");
    let counted = |token: &str| {
        view.candidates
            .iter()
            .filter(|candidate| candidate.catalog_token == token)
            .count()
    };
    let by_level = [
        ("glava", DENOMINATOR_GLAVA),
        ("statya", DENOMINATOR_STATYA),
        ("chast", DENOMINATOR_CHAST),
        ("punkt", DENOMINATOR_PUNKT),
        ("paragraph", DENOMINATOR_PARAGRAPH),
    ];
    let mut total = 0;
    for (token, expected) in by_level {
        assert_eq!(counted(token), expected, "{token} identities");
        total += expected;
    }
    assert_eq!(total, DENOMINATOR_EXTRACTED);
    assert_eq!(view.candidates.len(), DENOMINATOR_EXTRACTED);
    // Punkt stays unadmitted by construction: no row of any generation may
    // carry the level, so 0 of the 997 punkt identities are admitted.
    assert_eq!(DENOMINATOR_UNADMITTED, 1799);
}

#[test]
fn successor_m209_generation_regenerates_with_zero_delta() {
    let result = run_generator(&generator_args(
        M209_ARTIFACT_PATH,
        M209_ADMISSIONS_PATH,
        CANONICAL_REGISTRY_PATH,
        "--check",
    ));
    assert_eq!(
        result.status.code(),
        Some(0),
        "successor generation must regenerate cleanly: {}",
        stderr_of(&result)
    );
    assert!(
        result.stdout.is_empty(),
        "stdout stays empty; heartbeat is stderr-only"
    );
    let stderr = stderr_of(&result);
    assert_count_only_stderr(&stderr);
    assert_eq!(
        stderr.trim(),
        heartbeat_line(ROWS_TOTAL, ROWS_LEGACY_M209, ROWS_CANDIDATE_BACKED_M209),
        "successor heartbeat must declare 102 candidate-backed rows"
    );
}

#[test]
fn frozen_m202_generation_still_regenerates_unchanged() {
    let result = run_generator(&generator_args(
        M202_ARTIFACT_PATH,
        M202_ADMISSIONS_PATH,
        CANONICAL_REGISTRY_PATH,
        "--check",
    ));
    assert_eq!(
        result.status.code(),
        Some(0),
        "frozen generation must still regenerate cleanly: {}",
        stderr_of(&result)
    );
    let stderr = stderr_of(&result);
    assert_count_only_stderr(&stderr);
    assert_eq!(
        stderr.trim(),
        heartbeat_line(ROWS_TOTAL, ROWS_LEGACY_M202, ROWS_CANDIDATE_BACKED_M202),
        "the frozen generation keeps its own candidate-backed count"
    );
}

#[test]
fn both_candidate_backed_generations_count_and_render_identical_bytes() {
    let canonical = read_repo_bytes(CANONICAL_REGISTRY_PATH);

    let (m202_rendered, admitted, legacy, candidate_backed) = render_projection(&cli_for(
        M202_ARTIFACT_PATH,
        M202_ADMISSIONS_PATH,
        CANONICAL_REGISTRY_PATH,
        GeneratorMode::Check,
    ))
    .expect("frozen generation renders");
    assert_eq!(
        (admitted, legacy, candidate_backed),
        (ROWS_TOTAL, ROWS_LEGACY_M202, ROWS_CANDIDATE_BACKED_M202)
    );

    let (m209_rendered, admitted, legacy, candidate_backed) = render_projection(&cli_for(
        M209_ARTIFACT_PATH,
        M209_ADMISSIONS_PATH,
        CANONICAL_REGISTRY_PATH,
        GeneratorMode::Check,
    ))
    .expect("successor generation renders");
    assert_eq!(
        (admitted, legacy, candidate_backed),
        (ROWS_TOTAL, ROWS_LEGACY_M209, ROWS_CANDIDATE_BACKED_M209),
        "the heartbeat must count `m209-candidate-backed` rows as candidate-backed"
    );

    // Zero delta: widening the candidate-backed generation by 99 rows may not
    // move a single byte of the canonical projection.
    assert_eq!(
        m202_rendered.as_bytes(),
        canonical.as_slice(),
        "frozen generation renders the tracked registry byte-for-byte"
    );
    assert_eq!(
        m209_rendered.as_bytes(),
        canonical.as_slice(),
        "successor generation renders the same bytes as the frozen projection"
    );
    assert_eq!(binding_rows(&m209_rendered).len(), ROWS_TOTAL);
    assert!(!m209_rendered.contains("level: punkt"));
    // Provenance is admission-source metadata: it never reaches the registry.
    assert!(!m209_rendered.contains("provenance"));
    assert!(!m209_rendered.contains("key_path"));
    assert!(!m209_rendered.contains("m209-candidate-backed"));
}

#[test]
fn repeat_write_is_byte_identical_to_the_canonical_projection() {
    let canonical = read_repo_bytes(CANONICAL_REGISTRY_PATH);
    let out = fresh_tmp_path("write-repeat");
    remove_quietly(&out);

    for round in 0..2 {
        let result = run_generator(&generator_args(
            M209_ARTIFACT_PATH,
            M209_ADMISSIONS_PATH,
            &out,
            "--write",
        ));
        assert_eq!(
            result.status.code(),
            Some(0),
            "write round {round} must succeed: {}",
            stderr_of(&result)
        );
        assert_eq!(
            read_repo_bytes(&out),
            canonical,
            "write round {round} is byte-identical to the canonical projection"
        );
    }
    remove_quietly(&out);
}

#[test]
fn swapped_candidate_artifact_or_admissions_source_fails_closed() {
    // Successor admission source against the frozen (much smaller) artifact:
    // the pinned artifact path/sha cannot hold, so the run refuses instead of
    // admitting a narrowed denominator.
    let narrowed = fresh_tmp_path("swapped-artifact");
    remove_quietly(&narrowed);
    let result = run_generator(&generator_args(
        M202_ARTIFACT_PATH,
        M209_ADMISSIONS_PATH,
        &narrowed,
        "--write",
    ));
    assert_eq!(
        result.status.code(),
        Some(6),
        "narrowed denominator refuses"
    );
    let stderr = stderr_of(&result);
    assert_count_only_stderr(&stderr);
    assert!(
        stderr.starts_with("drift=admission"),
        "refusal is named as admission drift; got {stderr:?}"
    );
    assert!(
        !repo_root().join(&narrowed).exists(),
        "a refused run must not write a partial projection"
    );

    // Frozen admission source against the successor artifact: same refusal.
    let swapped = fresh_tmp_path("swapped-admissions");
    remove_quietly(&swapped);
    let result = run_generator(&generator_args(
        M209_ARTIFACT_PATH,
        M202_ADMISSIONS_PATH,
        &swapped,
        "--write",
    ));
    assert_eq!(result.status.code(), Some(6), "swapped source refuses");
    assert_count_only_stderr(&stderr_of(&result));
    assert!(
        !repo_root().join(&swapped).exists(),
        "a refused run must not write a partial projection"
    );
}

#[test]
fn narrowed_identity_digest_fails_closed_before_any_write() {
    // A source that pins an identity digest over fewer identities is the
    // "narrowed denominator" failure mode: it must be named, not partially
    // honoured.
    let source = read_repo_text(M209_ADMISSIONS_PATH);
    let narrowed = source.replace(
        "candidate_identity_digest: fnv1a64:778beb9832032d4e",
        "candidate_identity_digest: fnv1a64:0000000000000000",
    );
    assert_ne!(narrowed, source, "the identity digest pin must be present");

    let admissions = fresh_tmp_path("narrowed-identity");
    fs::write(repo_root().join(&admissions), narrowed).expect("write narrowed fixture");

    let out = fresh_tmp_path("narrowed-identity-out");
    remove_quietly(&out);
    let result = run_generator(&generator_args(
        M209_ARTIFACT_PATH,
        &admissions,
        &out,
        "--write",
    ));
    let stderr = stderr_of(&result);
    assert_eq!(
        result.status.code(),
        Some(6),
        "narrowed identity digest refuses: {stderr}"
    );
    assert_count_only_stderr(&stderr);
    assert!(
        stderr.contains("drift=admission") && stderr.contains("candidate_identity_digest"),
        "refusal names the drifted pin; got {stderr:?}"
    );
    assert!(
        !repo_root().join(&out).exists(),
        "a refused run must not write a partial projection"
    );

    remove_quietly(&admissions);
    remove_quietly(&out);
}

#[test]
fn parsed_successor_invocation_reports_the_same_counts_as_the_binary() {
    let cli = parse_generator_args(generator_args(
        M209_ARTIFACT_PATH,
        M209_ADMISSIONS_PATH,
        CANONICAL_REGISTRY_PATH,
        "--check",
    ))
    .expect("successor invocation parses");
    assert_eq!(cli.mode, GeneratorMode::Check);
    assert_eq!(cli.admissions, Path::new(M209_ADMISSIONS_PATH));
    let (_, admitted, legacy, candidate_backed) =
        render_projection(&cli).expect("parsed successor invocation renders");
    assert_eq!(
        (admitted, legacy, candidate_backed),
        (ROWS_TOTAL, ROWS_LEGACY_M209, ROWS_CANDIDATE_BACKED_M209)
    );

    // An unparsable mode still fails as a usage error, never as a partial run.
    let err = parse_generator_args(vec![
        "--candidate-artifact".to_owned(),
        M209_ARTIFACT_PATH.to_owned(),
        "--admissions".to_owned(),
        M209_ADMISSIONS_PATH.to_owned(),
        "--out".to_owned(),
        CANONICAL_REGISTRY_PATH.to_owned(),
    ])
    .expect_err("a mode flag is required");
    assert_eq!(err.exit_code(), 2);
    assert!(matches!(err, GeneratorError::Usage { .. }));
}
